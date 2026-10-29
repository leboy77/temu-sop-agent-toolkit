#!/usr/bin/env python3
"""Generate deterministic synthetic Temu category samples for testing."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


def dirty_number(value: float | int, rng: random.Random, currency: str) -> str:
    style = rng.choice(("plain", "currency", "comma"))
    if style == "plain":
        return str(value)
    if style == "currency":
        symbol = "$" if currency == "USD" else "€"
        return f"{symbol}{value:,.2f}"
    return f"{value:,.2f}"


def generate_us(path: Path) -> None:
    rng = random.Random(20261029)
    anchors = [
        (18.0, 70),
        (20.0, 180),
        (22.0, 360),
        (24.0, 540),
        (26.0, 420),
        (28.0, 250),
        (30.0, 120),
        (32.0, 55),
    ]
    themes = ["Floral", "Winter animal", "Nordic", "Abstract", "Minimal"]
    styles = ["Regular vest", "Longline vest", "Cropped vest"]
    brands = ["Unbranded"] * 44 + ["BrandA"] * 8 + ["BrandB"] * 6 + ["BrandC"] * 4
    sellers = ["SellerA"] * 8 + ["SellerB"] * 7 + ["SellerC"] * 6 + [
        f"Small{i:02d}" for i in range(1, 26)
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "商品名称",
                "当前售价",
                "原价",
                "近30天销量",
                "月销售额",
                "店铺",
                "品牌",
                "评分",
                "评价数",
                "上架天数",
                "图案主题",
                "款式",
                "颜色数",
                "SKU数量",
                "商品状态",
                "商品链接",
            ]
        )
        for index in range(80):
            price_anchor, sales_anchor = anchors[(index + rng.randint(0, 2)) % len(anchors)]
            price = round(price_anchor + rng.uniform(-0.8, 0.8), 2)
            sales = max(0, int(rng.gauss(sales_anchor, sales_anchor * 0.35)))
            if index % 19 == 0:
                sales = int(sales * 1.8)
            theme = themes[index % len(themes)]
            style = styles[index % len(styles)]
            color_count = 2 + (index % 6)
            sku_count = color_count * 6
            age = rng.randint(14, 500)
            revenue = round(price * sales, 2)
            writer.writerow(
                [
                    f"Women's {theme} Print Fleece Vest, {style}",
                    dirty_number(price, rng, "USD"),
                    dirty_number(round(price * rng.uniform(1.1, 1.35), 2), rng, "USD"),
                    f"{sales:,}" if rng.random() < 0.4 else sales,
                    dirty_number(revenue, rng, "USD") if rng.random() > 0.2 else "",
                    sellers[index % len(sellers)],
                    brands[index % len(brands)],
                    round(rng.uniform(4.1, 5.0), 1),
                    max(0, int(sales * rng.uniform(0.2, 0.7))),
                    f"{age}天" if rng.random() < 0.7 else f"2025-{(age % 12) + 1:02d}-15",
                    theme,
                    style,
                    color_count,
                    sku_count,
                    "在售",
                    f"https://example.invalid/temu/us/{1000 + index}",
                ]
            )


def generate_eu(path: Path) -> None:
    rng = random.Random(20261030)
    anchors = [
        (24.0, 45),
        (28.0, 100),
        (32.0, 210),
        (36.0, 350),
        (40.0, 280),
        (44.0, 160),
        (48.0, 60),
    ]
    fits = ["Wide leg", "Straight leg", "Relaxed fit"]
    materials = ["Fleece-look", "Cotton blend", "Sherpa-look"]
    sellers = ["ShopA"] * 8 + ["ShopB"] * 6 + [
        f"Vendor{i:02d}" for i in range(1, 28)
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "商品名称",
                "售价",
                "近30天销量",
                "月销售额",
                "店铺",
                "品牌",
                "评分",
                "评价数",
                "上架时间",
                "版型",
                "材质",
                "颜色数",
                "SKU数",
                "商品状态",
                "商品链接",
            ]
        )
        for index in range(70):
            anchor, sales_anchor = anchors[index % len(anchors)]
            price = round(anchor + rng.uniform(-1.2, 1.2), 2)
            sales = max(0, int(rng.gauss(sales_anchor, sales_anchor * 0.4)))
            fit = fits[index % len(fits)]
            material = materials[index % len(materials)]
            age = rng.randint(20, 420)
            writer.writerow(
                [
                    f"Women's Plush {fit} Lounge Pants, {material}",
                    dirty_number(price, rng, "EUR"),
                    sales,
                    dirty_number(round(price * sales, 2), rng, "EUR") if rng.random() > 0.25 else "",
                    sellers[index % len(sellers)],
                    "Unbranded" if index % 3 else "Generic",
                    round(rng.uniform(4.0, 5.0), 1),
                    max(0, int(sales * rng.uniform(0.15, 0.65))),
                    f"{age}天" if rng.random() < 0.7 else f"2026-{(age % 9) + 1:02d}-10",
                    fit,
                    material,
                    1 + index % 5,
                    (1 + index % 5) * 5,
                    "在售",
                    f"https://example.invalid/temu/eu/{2000 + index}",
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "samples",
    )
    args = parser.parse_args()
    us_path = args.output_dir / "us-y1-pod-listings.csv"
    eu_path = args.output_dir / "eu-y2-listings.csv"
    generate_us(us_path)
    generate_eu(eu_path)
    print(f"Wrote {us_path}")
    print(f"Wrote {eu_path}")


if __name__ == "__main__":
    main()
