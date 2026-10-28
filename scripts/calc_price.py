#!/usr/bin/env python3
"""Calculate transparent unit economics from a price sheet CSV."""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = [
    "product_brief_id",
    "sku_id",
    "cost_currency",
    "sale_currency",
    "fx_sale_to_cost",
    "product_cost",
    "freight_per_kg",
    "weight_kg",
    "freight_fixed",
    "return_rate_pct",
    "platform_fee_pct",
    "ad_cost_pct",
    "target_margin_pct",
    "target_sale_price",
]

NUMERIC_FIELDS = [
    "fx_sale_to_cost",
    "product_cost",
    "freight_per_kg",
    "weight_kg",
    "freight_fixed",
    "return_rate_pct",
    "platform_fee_pct",
    "ad_cost_pct",
    "target_margin_pct",
    "target_sale_price",
]


def decimal_value(row: dict[str, str], field: str) -> Decimal:
    try:
        return Decimal(row.get(field, "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"{row.get('sku_id', '<unknown>')}: invalid {field}") from exc


def calculate(row: dict[str, str]) -> dict[str, str]:
    missing = [field for field in REQUIRED_FIELDS if not row.get(field, "").strip()]
    if missing:
        raise ValueError(f"{row.get('sku_id', '<unknown>')}: missing {', '.join(missing)}")

    fx_sale_to_cost = decimal_value(row, "fx_sale_to_cost")
    product_cost = decimal_value(row, "product_cost")
    freight_per_kg = decimal_value(row, "freight_per_kg")
    weight_kg = decimal_value(row, "weight_kg")
    freight_fixed = decimal_value(row, "freight_fixed")
    return_rate = decimal_value(row, "return_rate_pct") / 100
    platform_fee = decimal_value(row, "platform_fee_pct") / 100
    ad_cost = decimal_value(row, "ad_cost_pct") / 100
    target_margin = decimal_value(row, "target_margin_pct") / 100
    target_sale_price = decimal_value(row, "target_sale_price")

    if weight_kg <= 0:
        raise ValueError(f"{row['sku_id']}: weight_kg must be positive")
    if any(value < 0 for value in (product_cost, freight_per_kg, freight_fixed, return_rate)):
        raise ValueError(f"{row['sku_id']}: costs and return rate cannot be negative")
    if fx_sale_to_cost <= 0:
        raise ValueError(f"{row['sku_id']}: fx_sale_to_cost must be positive")
    if target_sale_price <= 0:
        raise ValueError(f"{row['sku_id']}: target_sale_price must be positive")

    variable_fee_rate = platform_fee + ad_cost
    target_floor_fee_rate = variable_fee_rate + target_margin
    if variable_fee_rate >= 1:
        raise ValueError(f"{row['sku_id']}: platform_fee_pct + ad_cost_pct must be below 100")
    if target_floor_fee_rate >= 1:
        raise ValueError(
            f"{row['sku_id']}: platform_fee_pct + ad_cost_pct + target_margin_pct must be below 100"
        )

    freight = freight_per_kg * weight_kg + freight_fixed
    base_cost = product_cost + freight
    expected_cost = base_cost * (1 + return_rate)
    break_even_cost = expected_cost / (1 - variable_fee_rate)
    target_floor_cost = expected_cost / (1 - target_floor_fee_rate)
    target_price_cost = target_sale_price * fx_sale_to_cost
    profit = target_price_cost - expected_cost - target_price_cost * variable_fee_rate
    profit_margin_pct = profit / target_price_cost * 100

    if target_price_cost < break_even_cost:
        status = "BLOCKED"
    elif target_price_cost < target_floor_cost:
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    result = dict(row)
    result.update(
        {
            "freight": f"{freight:.2f}",
            "expected_unit_cost": f"{expected_cost:.2f}",
            "break_even_price_base": f"{break_even_cost:.2f}",
            "break_even_price_sale": f"{break_even_cost / fx_sale_to_cost:.2f}",
            "target_floor_price_base": f"{target_floor_cost:.2f}",
            "target_floor_price_sale": f"{target_floor_cost / fx_sale_to_cost:.2f}",
            "target_price_base": f"{target_price_cost:.2f}",
            "profit": f"{profit:.2f}",
            "profit_margin_pct": f"{profit_margin_pct:.2f}",
            "computed_status": status,
        }
    )
    return result


def print_table(rows: list[dict[str, str]]) -> None:
    headers = [
        "sku_id",
        "cost_currency",
        "sale_currency",
        "expected_unit_cost",
        "break_even_price_sale",
        "target_floor_price_sale",
        "target_sale_price",
        "profit",
        "profit_margin_pct",
        "computed_status",
    ]
    print("\t".join(headers))
    for row in rows:
        print("\t".join(row[field] for field in headers))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--output", type=Path, help="Optional computed CSV output")
    args = parser.parse_args()

    with args.input_csv.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise SystemExit("No rows found")

    computed = [calculate(row) for row in rows]
    print_table(computed)

    if args.output:
        fieldnames = list(computed[0].keys())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(computed)
        print(f"\nWrote {len(computed)} rows to {args.output}")


if __name__ == "__main__":
    main()
