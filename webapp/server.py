#!/usr/bin/env python3
"""Local web dashboard and OpenAI Responses API bridge for Temu market research."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import tempfile
import threading
import traceback
import urllib.error
import urllib.request
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "agents/01_market_research"
STATIC_DIR = Path(__file__).resolve().parent / "static"
CONFIG_DIR = AGENT_DIR / "configs"
MAX_BODY_BYTES = 20 * 1024 * 1024


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file(Path(__file__).resolve().parent / ".env")
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-6.1-sol")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com").rstrip("/")
LATEST_CAPTURE: dict[str, Any] | None = None
LATEST_LOCK = threading.Lock()


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PARSER = load_module("temu_parser", AGENT_DIR / "scripts/temu_parser.py")
METRICS = load_module("temu_market_metrics", AGENT_DIR / "scripts/temu_market_metrics.py")
SYSTEM_PROMPT = (AGENT_DIR / "prompts/00_system.md").read_text(encoding="utf-8")
ANALYSIS_PROMPT = (AGENT_DIR / "prompts/02_market_analysis.md").read_text(encoding="utf-8")


def load_config(market_id: str) -> dict[str, Any]:
    allowed = {"eu-y2", "us-y1-pod"}
    if market_id not in allowed:
        raise ValueError("Unsupported market_id")
    return json.loads((CONFIG_DIR / f"{market_id}.json").read_text(encoding="utf-8"))


def build_metrics(
    items: list[dict[str, Any]],
    meta: dict[str, Any],
    config: dict[str, Any],
    config_fields: list[str],
) -> dict[str, Any]:
    if not items:
        raise ValueError("No valid listing rows found")
    return {
        "meta": meta,
        "market_capacity": METRICS.market_capacity(items),
        "brand_concentration": METRICS.concentration(items, "brand"),
        "seller_concentration": METRICS.concentration(items, "seller"),
        "price_bands": METRICS.price_bands(
            items,
            int(config.get("price_bins", 10)),
            float(config.get("valley_min_drop_pct", 15)) / 100,
            int(config.get("max_price_bands", 5)),
        ),
        "new_listing_signal": METRICS.new_listing_signal(
            items, int(config.get("new_listing_days", 90))
        ),
        "discount_summary": METRICS.discount_summary(items),
        "config_matrix": METRICS.config_matrix(items, config_fields),
    }


def normalize_csv_payload(payload: dict[str, Any]) -> dict[str, Any]:
    csv_text = str(payload.get("csv", ""))
    if not csv_text.strip():
        raise ValueError("CSV content is empty")

    market_id = str(payload.get("market_id", ""))
    config = load_config(market_id)
    currency = str(payload.get("currency") or config["default_currency"]).upper()
    sales_window_days = int(payload.get("sales_window_days") or config["sales_window_days"])
    data_date = str(payload.get("data_date") or date.today().isoformat())
    as_of = date.fromisoformat(str(payload.get("as_of") or data_date))
    filename = str(payload.get("filename") or "upload.csv")

    with tempfile.TemporaryDirectory(prefix="temu-market-") as temp_dir:
        source = Path(temp_dir) / "upload.csv"
        source.write_text(csv_text, encoding="utf-8-sig")
        rows = PARSER.read_rows(source)
        if not rows:
            raise ValueError("No rows found in CSV")
        column_map = PARSER.build_column_map(list(rows[0]))
        missing = [field for field in ("title", "price", "sales", "seller") if field not in column_map]
        if missing:
            raise ValueError(f"Required columns not mapped: {', '.join(missing)}")
        items, stats = PARSER.normalize(rows, column_map, as_of)

    meta = {
        "market_id": market_id,
        "target_market": payload.get("target_market", ""),
        "platform": "temu",
        "currency": currency,
        "sales_window_days": sales_window_days,
        "data_date": data_date,
        "source_file": filename,
        "row_count_raw": len(rows),
        "row_count_kept": len(items),
        "column_map": column_map,
        "parse_stats": stats,
    }
    fields = payload.get("config_fields") or config.get("config_fields") or []
    return {
        "items": items,
        "metrics": build_metrics(items, meta, config, list(fields)),
    }


def normalize_capture_payload(payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("items", [])
    if not isinstance(items, list):
        raise ValueError("items must be an array")
    market_id = str(payload.get("market_id", ""))
    config = load_config(market_id)
    currency = str(payload.get("currency") or config["default_currency"]).upper()
    sales_window_days = int(payload.get("sales_window_days") or 0)
    if sales_window_days <= 0:
        raise ValueError(
            "sales_window_days must be known. Visible lifetime sales cannot be treated as monthly sales."
        )

    cleaned: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        copied = dict(item)
        copied["price"] = PARSER.to_number(copied.get("price"))
        copied["sales"] = PARSER.to_number(copied.get("sales"))
        for field in ("list_price", "rating", "review_count", "listing_age_days", "sku_count", "color_count"):
            if field in copied:
                copied[field] = PARSER.to_number(copied.get(field))
        if copied["price"] is None or copied["sales"] is None:
            continue
        if not copied.get("revenue"):
            copied["revenue"] = round(copied["price"] * copied["sales"], 2)
            copied["revenue_derived"] = True
        cleaned.append(copied)

    meta = {
        "market_id": market_id,
        "target_market": payload.get("target_market", ""),
        "platform": "temu",
        "currency": currency,
        "sales_window_days": sales_window_days,
        "data_date": payload.get("data_date", date.today().isoformat()),
        "source_file": "browser-extension-capture",
        "row_count_raw": len(items),
        "row_count_kept": len(cleaned),
        "column_map": {},
        "parse_stats": {"dropped": len(items) - len(cleaned)},
    }
    fields = payload.get("config_fields") or config.get("config_fields") or []
    return {
        "items": cleaned,
        "metrics": build_metrics(cleaned, meta, config, list(fields)),
    }


def call_responses_api(metrics: dict[str, Any], business_context: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the local server")

    request_payload = {
        "model": DEFAULT_MODEL,
        "instructions": SYSTEM_PROMPT + "\n\n" + ANALYSIS_PROMPT,
        "input": json.dumps(
            {
                "metrics_report": metrics,
                "business_context": business_context,
            },
            ensure_ascii=False,
        ),
        "reasoning": {"effort": "low"},
        "max_output_tokens": 5000,
        "store": False,
    }
    request = urllib.request.Request(
        f"{OPENAI_BASE_URL}/v1/responses",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "temu-market-dashboard/0.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:1000]
        raise RuntimeError(f"OpenAI API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Unable to reach OpenAI API: {exc.reason}") from exc

    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    parts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(content["text"])
    if not parts:
        raise RuntimeError("OpenAI response did not contain output text")
    return "\n".join(parts)


class Handler(BaseHTTPRequestHandler):
    server_version = "TemuMarketDashboard/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} {format % args}")

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("Invalid request size")
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        if path == "/api/health":
            self.send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "openai_configured": bool(os.environ.get("OPENAI_API_KEY")),
                    "model": DEFAULT_MODEL,
                },
            )
            return
        if path == "/api/capture/latest":
            with LATEST_LOCK:
                payload = LATEST_CAPTURE
            if payload is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "No captured dataset"})
            else:
                self.send_json(HTTPStatus.OK, payload)
            return
        if path == "/api/sample":
            from urllib.parse import parse_qs

            market_id = parse_qs(parsed_url.query).get("market", [""])[0]
            sample = AGENT_DIR / "samples" / f"{market_id}-listings.csv"
            if market_id not in {"eu-y2", "us-y1-pod"} or not sample.is_file():
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Sample not found"})
            else:
                self.send_json(
                    HTTPStatus.OK,
                    {"filename": sample.name, "csv": sample.read_text(encoding="utf-8-sig")},
                )
            return
        if path == "/":
            path = "/index.html"
        target = (STATIC_DIR / path.lstrip("/")).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(target.suffix.lower(), "application/octet-stream")
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self.read_json()
            if path == "/api/analyze":
                result = normalize_csv_payload(payload)
            elif path == "/api/capture":
                result = normalize_capture_payload(payload)
                with LATEST_LOCK:
                    global LATEST_CAPTURE
                    LATEST_CAPTURE = result
            elif path == "/api/ai-analysis":
                metrics = payload.get("metrics")
                if not isinstance(metrics, dict):
                    raise ValueError("metrics is required")
                result = {
                    "analysis": call_responses_api(
                        metrics, str(payload.get("business_context", ""))
                    )
                }
            else:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return
            self.send_json(HTTPStatus.OK, result)
        except ValueError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except RuntimeError as exc:
            self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(exc)})
        except Exception:
            traceback.print_exc()
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Unexpected server error"})


class TemuHTTPServer(ThreadingHTTPServer):
    # Windows can otherwise allow two local apps to listen on the same port,
    # making requests silently go to whichever server the kernel picks.
    allow_reuse_address = False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    server = TemuHTTPServer((args.host, args.port), Handler)
    print(f"Temu Market Dashboard: http://{args.host}:{args.port}")
    print(f"OpenAI model: {DEFAULT_MODEL}")
    print(
        "OpenAI API: configured"
        if os.environ.get("OPENAI_API_KEY")
        else "OpenAI API: not configured (set OPENAI_API_KEY to enable AI analysis)"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
