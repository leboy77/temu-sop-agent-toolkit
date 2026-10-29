#!/usr/bin/env python3
"""Calculate the normalized EU Y2 supplier price-card model."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ProductPricing:
    weight_kg: Decimal
    purchase_cost: Decimal
    return_rate: Decimal


@dataclass(frozen=True)
class CountryRate:
    country_name: str
    country_code: str
    weight_band: str
    weight_low: Decimal | None
    weight_high: Decimal | None
    current_freight_per_kg: Decimal
    current_handling_fee: Decimal
    subsidy_amount: Decimal
    sale_price: Decimal
    minimum_sale_price: Decimal | None
    new_freight_per_kg: Decimal | None
    new_handling_fee: Decimal | None


def decimal_value(value: str) -> Decimal:
    text = value.strip().replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal value: {value!r}") from exc


def optional_decimal(value: str) -> Decimal | None:
    return decimal_value(value) if value and value.strip() else None


def parse_weight_band(text: str) -> tuple[Decimal | None, Decimal | None]:
    cleaned = text.upper().replace("KG", "").replace(" ", "")
    if "W" in cleaned:
        numbers = re.findall(r"\d+(?:\.\d+)?", cleaned)
        if len(numbers) == 2:
            return decimal_value(numbers[0]), decimal_value(numbers[1])
    match = re.fullmatch(r"(\d+(?:\.\d+)?)?-(\d+(?:\.\d+)?)?", cleaned)
    if match:
        return (
            decimal_value(match.group(1)) if match.group(1) else None,
            decimal_value(match.group(2)) if match.group(2) else None,
        )
    return None, None


def band_contains(rate: CountryRate, weight: Decimal) -> bool:
    lower_ok = rate.weight_low is None or weight >= rate.weight_low
    upper_ok = rate.weight_high is None or weight <= rate.weight_high
    return lower_ok and upper_ok


def load_rates(path: Path) -> list[CountryRate]:
    rates: list[CountryRate] = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            low, high = parse_weight_band(row["weight_band"])
            rates.append(
                CountryRate(
                    country_name=" ".join(row["country_name"].split()),
                    country_code=row["country_code"].strip(),
                    weight_band=" ".join(row["weight_band"].split()),
                    weight_low=low,
                    weight_high=high,
                    current_freight_per_kg=decimal_value(row["current_freight_per_kg_cny"]),
                    current_handling_fee=decimal_value(row["current_handling_fee_cny"]),
                    subsidy_amount=decimal_value(row["subsidy_amount_cny"] or "0"),
                    sale_price=decimal_value(row["sale_price_cny"]),
                    minimum_sale_price=optional_decimal(row["minimum_sale_price_cny"]),
                    new_freight_per_kg=optional_decimal(row["new_freight_per_kg_cny"]),
                    new_handling_fee=optional_decimal(row["new_handling_fee_cny"]),
                )
            )
    return rates


def select_rates(rates: Iterable[CountryRate], weight: Decimal) -> tuple[list[CountryRate], list[str]]:
    by_country: dict[tuple[str, str], list[CountryRate]] = {}
    for rate in rates:
        by_country.setdefault((rate.country_name, rate.country_code), []).append(rate)

    selected: list[CountryRate] = []
    warnings: list[str] = []
    for (country, code), choices in by_country.items():
        matches = [rate for rate in choices if band_contains(rate, weight)]
        if not matches:
            warnings.append(f"NO_WEIGHT_BAND: {country} ({code}) for {weight} kg")
            continue

        def width(rate: CountryRate) -> Decimal:
            if rate.weight_low is None or rate.weight_high is None:
                return Decimal("Infinity")
            return rate.weight_high - rate.weight_low

        selected.append(min(matches, key=width))
    return selected, warnings


def calculate_rate(product: ProductPricing, rate: CountryRate) -> dict[str, str]:
    current_logistics = (
        product.weight_kg * rate.current_freight_per_kg + rate.current_handling_fee
    )
    landed_cost = current_logistics + product.purchase_cost
    cost_after_returns = landed_cost * (1 + product.return_rate)
    declared_price = rate.sale_price / Decimal("0.9")
    launch_price = declared_price * Decimal("1.8")
    traffic_price = rate.sale_price * Decimal("1.1")
    normal_profit = rate.sale_price + rate.subsidy_amount - cost_after_returns
    normal_roi = normal_profit / landed_cost

    result = {
        "country_name": rate.country_name,
        "country_code": rate.country_code,
        "weight_band": rate.weight_band,
        "current_logistics_cny": f"{current_logistics:.2f}",
        "landed_cost_cny": f"{landed_cost:.2f}",
        "cost_after_returns_cny": f"{cost_after_returns:.2f}",
        "declared_price_cny": f"{declared_price:.2f}",
        "launch_price_cny": f"{launch_price:.2f}",
        "traffic_acceleration_price_cny": f"{traffic_price:.2f}",
        "normal_profit_cny": f"{normal_profit:.2f}",
        "normal_roi_pct": f"{normal_roi * 100:.2f}",
        "minimum_profit_cny": "",
        "minimum_roi_pct": "",
        "new_logistics_cost_cny": "",
        "new_cost_after_returns_cny": "",
        "new_logistics_profit_cny": "",
        "new_logistics_roi_pct": "",
        "warning": "",
    }

    if rate.minimum_sale_price is not None:
        minimum_profit = rate.minimum_sale_price + rate.subsidy_amount - cost_after_returns
        result["minimum_profit_cny"] = f"{minimum_profit:.2f}"
        result["minimum_roi_pct"] = f"{minimum_profit / landed_cost * 100:.2f}"

    if rate.new_freight_per_kg is None or rate.new_handling_fee is None:
        result["warning"] = "NEW_LOGISTICS_NOT_CALCULATED"
        return result

    new_logistics = product.weight_kg * rate.new_freight_per_kg + rate.new_handling_fee
    new_cost = (new_logistics + product.purchase_cost) * (1 + product.return_rate)
    new_profit = rate.sale_price + rate.subsidy_amount - new_cost
    new_roi = new_profit / (new_logistics + product.purchase_cost)
    result.update(
        {
            "new_logistics_cost_cny": f"{new_logistics:.2f}",
            "new_cost_after_returns_cny": f"{new_cost:.2f}",
            "new_logistics_profit_cny": f"{new_profit:.2f}",
            "new_logistics_roi_pct": f"{new_roi * 100:.2f}",
        }
    )
    return result


def calculate_all(
    product: ProductPricing,
    rates: list[CountryRate],
) -> tuple[list[dict[str, str]], list[str]]:
    selected, warnings = select_rates(rates, product.weight_kg)
    calculated = []
    for rate in selected:
        result = calculate_rate(product, rate)
        if result["warning"]:
            warnings.append(f"{rate.country_name}: {result['warning']}")
        calculated.append(result)
    return calculated, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rates", required=True, type=Path)
    parser.add_argument("--weight-kg", required=True, type=Decimal)
    parser.add_argument("--purchase-cost", required=True, type=Decimal)
    parser.add_argument("--return-rate-pct", required=True, type=Decimal)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    product = ProductPricing(
        weight_kg=args.weight_kg,
        purchase_cost=args.purchase_cost,
        return_rate=args.return_rate_pct / 100,
    )
    calculated, warnings = calculate_all(product, load_rates(args.rates))
    if not calculated:
        raise SystemExit("No country weight bands matched")

    print(
        "country\tband\tlanded\tnormal_profit\tnormal_roi\tminimum_profit\t"
        "new_logistics_profit\tnew_roi"
    )
    for row in calculated:
        print(
            "\t".join(
                row[key]
                for key in (
                    "country_name",
                    "weight_band",
                    "landed_cost_cny",
                    "normal_profit_cny",
                    "normal_roi_pct",
                    "minimum_profit_cny",
                    "new_logistics_profit_cny",
                    "new_logistics_roi_pct",
                )
            )
        )
    for warning in warnings:
        print(f"WARN {warning}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(calculated[0]))
            writer.writeheader()
            writer.writerows(calculated)
        print(f"Wrote {len(calculated)} rows to {args.output}")


if __name__ == "__main__":
    main()
