from __future__ import annotations

import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "webapp" / "server.py"
SAMPLE_PATH = ROOT / "agents" / "01_market_research" / "samples" / "us-y1-pod-listings.csv"


def load_server_module():
    spec = importlib.util.spec_from_file_location("temu_webapp_server_test", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SERVER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class WebappServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server_module()

    def test_csv_normalization_keeps_sample_rows_and_metrics(self):
        result = self.server.normalize_csv_payload(
            {
                "csv": SAMPLE_PATH.read_text(encoding="utf-8-sig"),
                "filename": SAMPLE_PATH.name,
                "market_id": "us-y1-pod",
                "currency": "USD",
                "sales_window_days": 30,
                "data_date": "2026-10-29",
                "as_of": "2026-10-29",
            }
        )
        metrics = result["metrics"]
        self.assertEqual(metrics["meta"]["row_count_raw"], 80)
        self.assertEqual(metrics["meta"]["row_count_kept"], 80)
        self.assertEqual(metrics["market_capacity"]["total_sales"], 21539)
        self.assertAlmostEqual(metrics["seller_concentration"]["cr3"], 0.4887)

    def test_capture_requires_known_sales_window(self):
        with self.assertRaisesRegex(ValueError, "sales_window_days"):
            self.server.normalize_capture_payload(
                {
                    "market_id": "us-y1-pod",
                    "sales_window_days": 0,
                    "items": [{"title": "A", "price": 10, "sales": 4}],
                }
            )

    def test_missing_seller_is_preserved_as_missing_data(self):
        result = self.server.normalize_capture_payload(
            {
                "market_id": "us-y1-pod",
                "currency": "USD",
                "sales_window_days": 30,
                "data_date": "2026-10-29",
                "items": [{"title": "A", "price": 10, "sales": 4}],
            }
        )
        self.assertEqual(result["metrics"]["seller_concentration"]["missing_items"], 1)

    def test_openai_call_requires_server_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                self.server.call_responses_api({"meta": {}}, "context")

    def test_openai_request_uses_responses_shape_and_disables_storage(self):
        captured: dict[str, Request] = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            self.assertEqual(timeout, 120)
            return FakeResponse(
                {
                    "output": [
                        {
                            "content": [
                                {"type": "output_text", "text": "测试分析"}
                            ]
                        }
                    ]
                }
            )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch.object(self.server.urllib.request, "urlopen", fake_urlopen):
                analysis = self.server.call_responses_api({"meta": {}}, "业务补充")

        self.assertEqual(analysis, "测试分析")
        request = captured["request"]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(body["model"], "gpt-6.1-sol")
        self.assertIn("instructions", body)
        self.assertIn("input", body)
        self.assertEqual(body["reasoning"], {"effort": "low"})
        self.assertFalse(body["store"])
        self.assertNotIn("test-key", request.full_url)


if __name__ == "__main__":
    unittest.main()
