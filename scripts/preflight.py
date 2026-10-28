#!/usr/bin/env python3
"""Run deterministic checks before advancing a product lifecycle state."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from calc_price import calculate


STATES = [
    "DRAFT",
    "PRICED",
    "ASSETS_READY",
    "COMPLIANCE_READY",
    "PUBLISH_READY",
    "PUBLISHED",
    "LIVE",
    "OPTIMIZING",
    "ARCHIVED",
]

NEXT_ACTION = {
    "PRICED": "03_assets",
    "ASSETS_READY": "05_compliance",
    "COMPLIANCE_READY": "04_listing",
    "PUBLISH_READY": "human_publish_approval",
}


def blocker_module(blocker: str) -> str:
    if blocker.startswith(("PRICE_", "APPROVAL_MISSING: pricing")):
        return "02_pricing"
    if blocker.startswith(("ASSET_", "APPROVAL_MISSING: assets")):
        return "03_assets"
    if "main images" in blocker or "final title" in blocker or "selling point" in blocker:
        return "03_assets"
    if "rights evidence" in blocker:
        return "03_assets"
    if blocker.startswith(("COMPLIANCE_", "APPROVAL_MISSING: compliance")):
        return "05_compliance"
    return "00_orchestrator"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level value must be an object")
    return data


def load_price_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return {row.get("sku_id", "").strip(): calculate(row) for row in rows}


def is_nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def run_preflight(
    brief: dict[str, Any],
    market: dict[str, Any],
    price_rows: dict[str, dict[str, str]],
    target_state: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    meta = brief.get("meta", {})
    product = brief.get("product", {})
    specs = brief.get("specs", {})
    skus = brief.get("skus", [])
    assets = brief.get("assets", {})
    compliance = brief.get("compliance", {})
    approvals = brief.get("approvals", {})

    if market.get("market_id") != meta.get("market_id"):
        blockers.append("MARKET_MISMATCH: brief.market_id does not match market profile")
    if not meta.get("product_brief_id"):
        blockers.append("INPUT_MISSING: meta.product_brief_id")
    if not product.get("internal_name") or not product.get("target_name"):
        blockers.append("INPUT_MISSING: product names")
    if not product.get("category") or not product.get("business_mode"):
        blockers.append("INPUT_MISSING: product category or business_mode")
    if not specs.get("material") or "待" in str(specs.get("material")):
        blockers.append("INPUT_MISSING: confirmed material")
    if not isinstance(specs.get("weight_kg"), (int, float)) or specs["weight_kg"] <= 0:
        blockers.append("INPUT_MISSING: positive spec weight_kg")
    if not specs.get("size_chart_id"):
        blockers.append("INPUT_MISSING: size_chart_id")

    sku_ids: set[str] = set()
    for index, sku in enumerate(skus):
        sku_id = str(sku.get("sku_id", "")).strip()
        if not sku_id:
            blockers.append(f"INPUT_MISSING: skus[{index}].sku_id")
            continue
        if sku_id in sku_ids:
            blockers.append(f"ASSET_MISMATCH: duplicate sku_id {sku_id}")
        sku_ids.add(sku_id)
        if sku_id not in price_rows:
            blockers.append(f"INPUT_MISSING: no price row for {sku_id}")
        if not sku.get("price_ref"):
            blockers.append(f"INPUT_MISSING: price_ref for {sku_id}")
        if not isinstance(sku.get("inventory"), int) or sku["inventory"] < 0:
            blockers.append(f"INPUT_MISSING: valid inventory for {sku_id}")

    if not skus:
        blockers.append("INPUT_MISSING: at least one SKU")

    for sku_id in sorted(sku_ids):
        result = price_rows.get(sku_id)
        if not result:
            continue
        if result["computed_status"] == "BLOCKED":
            blockers.append(f"PRICE_BELOW_FLOOR: {sku_id}")
        elif result["computed_status"] == "REVIEW_REQUIRED":
            warnings.append(f"PRICE_BELOW_TARGET_MARGIN: {sku_id}")

    target_rank = STATES.index(target_state) if target_state in STATES else -1
    if target_rank < 0:
        raise ValueError(f"Unsupported target state: {target_state}")

    if target_rank >= STATES.index("PRICED"):
        if approvals.get("selection") is not True:
            blockers.append("APPROVAL_MISSING: selection")
        if approvals.get("pricing") is not True:
            blockers.append("APPROVAL_MISSING: pricing")
        if any(
            price_rows.get(sku_id, {}).get("computed_status") != "PASS"
            for sku_id in sku_ids
        ):
            blockers.append("PRICE_NOT_APPROVABLE: all SKUs must pass or need explicit exception")

    if target_rank >= STATES.index("ASSETS_READY"):
        if not assets.get("main_images"):
            blockers.append("INPUT_MISSING: main images")
        if not assets.get("title_final"):
            blockers.append("INPUT_MISSING: final title")
        if not assets.get("core_selling_point"):
            blockers.append("INPUT_MISSING: core selling point")
        if not assets.get("rights_evidence"):
            blockers.append("INPUT_MISSING: image/artwork rights evidence")
        if approvals.get("assets") is not True:
            blockers.append("APPROVAL_MISSING: assets")

    if target_rank >= STATES.index("COMPLIANCE_READY"):
        if not compliance.get("pack_ref"):
            blockers.append("INPUT_MISSING: compliance pack")
        if compliance.get("status") != "PASSED":
            blockers.append("COMPLIANCE_REJECTED: compliance status is not PASSED")
        if approvals.get("compliance") is not True:
            blockers.append("APPROVAL_MISSING: compliance")
        if not market.get("compliance", {}).get("required"):
            blockers.append("INPUT_MISSING: market compliance requirements")

    if target_rank >= STATES.index("PUBLISH_READY"):
        for sku in skus:
            if not sku.get("image_refs"):
                blockers.append(f"ASSET_MISMATCH: image_refs missing for {sku.get('sku_id')}")
        required_modes = market.get("business_modes", [])
        if required_modes and product.get("business_mode") not in required_modes:
            blockers.append("INPUT_MISSING: unsupported business_mode for market")

    status = "PASS"
    if blockers:
        status = "REVIEW_REQUIRED" if target_rank <= STATES.index("PRICED") else "BLOCKED"
    elif warnings:
        status = "REVIEW_REQUIRED"

    current_state = str(meta.get("status", "DRAFT"))
    next_state = target_state if not blockers else current_state
    next_action = (
        NEXT_ACTION.get(target_state, "manual_review")
        if not blockers
        else blocker_module(blockers[0])
    )
    return {
        "status": status,
        "current_state": current_state,
        "target_state": target_state,
        "next_state": next_state,
        "next_action": next_action,
        "product_brief_id": meta.get("product_brief_id", ""),
        "market_id": meta.get("market_id", ""),
        "blockers": blockers,
        "warnings": warnings,
        "price_results": {
            sku_id: {
                "break_even_price_base": row["break_even_price_base"],
                "break_even_price_sale": row["break_even_price_sale"],
                "target_floor_price_base": row["target_floor_price_base"],
                "target_floor_price_sale": row["target_floor_price_sale"],
                "target_price_base": row["target_price_base"],
                "target_sale_price": row["target_sale_price"],
                "profit": row["profit"],
                "profit_margin_pct": row["profit_margin_pct"],
                "computed_status": row["computed_status"],
            }
            for sku_id, row in price_rows.items()
            if sku_id in sku_ids
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--brief", required=True, type=Path)
    parser.add_argument("--price-sheet", type=Path)
    parser.add_argument(
        "--target-state",
        default="PRICED",
        choices=["PRICED", "ASSETS_READY", "COMPLIANCE_READY", "PUBLISH_READY"],
    )
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    market = load_json(args.market)
    brief = load_json(args.brief)
    price_path = args.price_sheet or Path(brief["meta"]["price_sheet_path"])
    price_rows = load_price_rows(price_path)
    report = run_preflight(brief, market, price_rows, args.target_state)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text + "\n", encoding="utf-8")

    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
