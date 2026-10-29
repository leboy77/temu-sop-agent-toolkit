#!/usr/bin/env python3
"""Normalize a Temu category-data export into the market research JSON contract."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_MAPPING: dict[str, list[str]] = {
    "title": ["商品名称", "商品标题", "标题", "product name", "product title", "title"],
    "price": ["当前售价", "前端售价", "页面价格", "售价", "价格", "sale price", "price"],
    "list_price": ["原价", "划线价", "list price", "original price"],
    "activity_price": ["活动价", "流量加速价", "activity price"],
    "sales": [
        "近30天销量",
        "30天销量",
        "月销量",
        "窗口销量",
        "销量",
        "monthly sales",
        "sales",
        "sold",
    ],
    "revenue": ["近30天销售额", "月销售额", "窗口销售额", "销售额", "revenue", "gmv"],
    "seller": ["店铺名称", "卖家名称", "店铺", "卖家", "seller", "store"],
    "brand": ["品牌名称", "品牌", "brand"],
    "rating": ["商品评分", "评分", "rating"],
    "review_count": ["评价数量", "评价数", "评论数", "review count", "reviews"],
    "listing_age_days": ["上架天数", "已上架天数", "上架时间", "listing age", "listed at"],
    "url": ["商品链接", "链接", "url", "link"],
    "category": ["类目", "分类", "category"],
    "status": ["商品状态", "状态", "status"],
    "sku_count": ["SKU数量", "SKU数", "变体数量", "SKU count", "variant count"],
    "color_count": ["颜色数量", "颜色数", "color count"],
    "print_theme": ["图案主题", "印花主题", "print theme"],
    "style": ["款式", "版型", "style", "fit"],
    "material": ["材质", "material"],
}

NUMERIC_FIELDS = {
    "price",
    "list_price",
    "activity_price",
    "sales",
    "revenue",
    "rating",
    "review_count",
    "listing_age_days",
    "sku_count",
    "color_count",
}

EMPTY_VALUES = {"", "-", "--", "n/a", "na", "null", "none", "无", "暂无"}


def normalize_key(value: str) -> str:
    value = str(value).replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"[\s()\[\]【】（）:：]", "", value).lower()


def to_number(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)

    text = str(raw).strip()
    if text.lower() in EMPTY_VALUES:
        return None
    text = re.sub(r"(?i)(CNY|RMB|USD|EUR|GBP|R\$|\$|€|£|¥|元)", "", text)
    text = text.replace("%", "").replace(" ", "")

    multiplier = 1.0
    for suffix, factor in (("万", 10_000), ("亿", 100_000_000), ("K", 1_000), ("M", 1_000_000)):
        if text.upper().endswith(suffix.upper()):
            multiplier = float(factor)
            text = text[: -len(suffix)]
            break

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        head, _, tail = text.rpartition(",")
        text = head.replace(",", "") + "." + tail if len(tail) in {1, 2} else text.replace(",", "")
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def to_age_days(raw: Any, as_of: date) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if text.lower() in EMPTY_VALUES:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)\s*(天|日)", text)
    if match:
        return int(float(match.group(1)))
    match = re.search(r"(\d+(?:\.\d+)?)\s*个?\s*月", text)
    if match:
        return int(float(match.group(1)) * 30)
    match = re.search(r"(\d+(?:\.\d+)?)\s*年", text)
    if match:
        return int(float(match.group(1)) * 365)
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if match:
        listed = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return max((as_of - listed).days, 0)

    value = to_number(text)
    return int(value) if value is not None else None


def read_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        try:
            import openpyxl  # type: ignore
        except ImportError as exc:
            raise SystemExit(
                "XLSX input requires openpyxl. Export to CSV or install openpyxl."
            ) from exc
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet = workbook.active
        iterator = sheet.iter_rows(values_only=True)
        header = [str(value) if value is not None else "" for value in next(iterator, [])]
        rows = [
            {header[index]: row[index] for index in range(len(header))}
            for row in iterator
            if row and any(value not in (None, "") for value in row)
        ]
        workbook.close()
        return rows

    text = None
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            text = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise SystemExit(f"Unable to decode input: {path}")
    delimiter = "\t" if text[:4096].count("\t") > text[:4096].count(",") else ","
    return list(csv.DictReader(text.splitlines(), delimiter=delimiter))


def build_column_map(
    header: list[str],
    custom: dict[str, str | list[str]] | None = None,
) -> dict[str, str]:
    mapping = {key: list(values) for key, values in DEFAULT_MAPPING.items()}
    if custom:
        for field, aliases in custom.items():
            mapping[field] = aliases if isinstance(aliases, list) else [aliases]

    normalized_header = {normalize_key(name): name for name in header if name}
    resolved: dict[str, str] = {}
    for field, aliases in mapping.items():
        for alias in aliases:
            if normalize_key(alias) in normalized_header:
                resolved[field] = normalized_header[normalize_key(alias)]
                break
        else:
            for alias in aliases:
                key = normalize_key(alias)
                match = next(
                    (original for normalized, original in normalized_header.items() if key in normalized),
                    None,
                )
                if match:
                    resolved[field] = match
                    break
    return resolved


def normalize(
    rows: list[dict[str, Any]],
    column_map: dict[str, str],
    as_of: date,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    items: list[dict[str, Any]] = []
    stats = {"dropped": 0, "revenue_derived": 0, "age_parsed": 0}

    for row in rows:
        item: dict[str, Any] = {}
        for field, source in column_map.items():
            raw = row.get(source)
            if field in NUMERIC_FIELDS:
                value = to_age_days(raw, as_of) if field == "listing_age_days" else to_number(raw)
            else:
                value = str(raw).strip() if raw is not None else None
                value = value or None
            item[field] = value

        if item.get("price") is None or item.get("sales") is None:
            stats["dropped"] += 1
            continue
        if item.get("revenue") is None:
            item["revenue"] = round(item["price"] * item["sales"], 2)
            item["revenue_derived"] = True
            stats["revenue_derived"] += 1
        else:
            item["revenue_derived"] = False

        if item.get("listing_age_days") is not None:
            stats["age_parsed"] += 1
        if item.get("list_price") and item["list_price"] > 0:
            item["discount_rate"] = round(
                max((item["list_price"] - item["price"]) / item["list_price"], 0),
                4,
            )
        else:
            item["discount_rate"] = None
        items.append(item)
    return items, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--mapping", type=Path)
    parser.add_argument("--market-id", required=True)
    parser.add_argument("--target-market", default="")
    parser.add_argument("--currency", required=True)
    parser.add_argument("--sales-window-days", type=int, default=30)
    parser.add_argument("--data-date", default=date.today().isoformat())
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--profile", action="store_true")
    args = parser.parse_args()

    rows = read_rows(args.input)
    if not rows:
        raise SystemExit("No data rows found")

    custom = json.loads(args.mapping.read_text(encoding="utf-8")) if args.mapping else None
    column_map = build_column_map(list(rows[0]), custom)
    if args.profile:
        print(json.dumps({"available_columns": list(rows[0]), "column_map": column_map}, ensure_ascii=False, indent=2))
        return

    missing = [field for field in ("title", "price", "sales", "seller") if field not in column_map]
    if missing:
        raise SystemExit(
            f"Required fields not mapped: {missing}. Use --profile and --mapping."
        )

    as_of = date.fromisoformat(args.as_of)
    items, stats = normalize(rows, column_map, as_of)
    payload = {
        "meta": {
            "market_id": args.market_id,
            "target_market": args.target_market,
            "platform": "temu",
            "currency": args.currency.upper(),
            "sales_window_days": args.sales_window_days,
            "data_date": args.data_date,
            "source_file": args.input.name,
            "row_count_raw": len(rows),
            "row_count_kept": len(items),
            "column_map": column_map,
            "parse_stats": stats,
        },
        "items": items,
    }
    output = args.output or args.input.with_suffix(".normalized.json")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "rows": len(items), "stats": stats}, ensure_ascii=False))


if __name__ == "__main__":
    main()
