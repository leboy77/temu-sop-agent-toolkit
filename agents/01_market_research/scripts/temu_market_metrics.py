#!/usr/bin/env python3
"""Compute deterministic Temu category metrics and a human-readable report."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def money(value: float, currency: str) -> str:
    return f"{currency} {value:,.2f}"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def market_capacity(items: list[dict[str, Any]]) -> dict[str, Any]:
    prices = [float(item["price"]) for item in items if item.get("price") is not None]
    sales = [float(item.get("sales") or 0) for item in items]
    revenue = [float(item.get("revenue") or 0) for item in items]
    total_sales = sum(sales)
    total_revenue = sum(revenue)
    return {
        "listing_count": len(items),
        "total_sales": int(total_sales),
        "total_revenue": round(total_revenue, 2),
        "average_price": round(statistics.mean(prices), 2) if prices else 0,
        "median_price": round(statistics.median(prices), 2) if prices else 0,
        "min_price": round(min(prices), 2) if prices else 0,
        "max_price": round(max(prices), 2) if prices else 0,
        "implied_average_price": round(safe_div(total_revenue, total_sales), 2),
        "average_sales_per_listing": round(safe_div(total_sales, len(items)), 2),
    }


def concentration(items: list[dict[str, Any]], field: str, top_n: int = 10) -> dict[str, Any]:
    groups: dict[str, dict[str, float]] = {}
    missing = 0
    for item in items:
        name = str(item.get(field) or "").strip()
        if not name:
            name = "UNKNOWN"
            missing += 1
        group = groups.setdefault(name, {"revenue": 0.0, "sales": 0.0, "items": 0})
        group["revenue"] += float(item.get("revenue") or 0)
        group["sales"] += float(item.get("sales") or 0)
        group["items"] += 1

    total_revenue = sum(group["revenue"] for group in groups.values())
    total_sales = sum(group["sales"] for group in groups.values())
    total_items = sum(group["items"] for group in groups.values())
    ranked = sorted(groups.items(), key=lambda pair: (-pair[1]["revenue"], pair[0]))
    cr3 = safe_div(sum(value["revenue"] for _, value in ranked[:3]), total_revenue)
    cr_n = safe_div(sum(value["revenue"] for _, value in ranked[:top_n]), total_revenue)
    hhi = sum((safe_div(value["revenue"], total_revenue) ** 2) for _, value in ranked) * 10000

    warning = None
    if len(groups) <= top_n:
        warning = (
            f"Subject count {len(groups)} <= {top_n}; CR{top_n} is not informative. "
            "Use CR3 and HHI."
        )

    rows = []
    for rank, (name, value) in enumerate(ranked[:top_n], start=1):
        rows.append(
            {
                "rank": rank,
                "name": name,
                "revenue": round(value["revenue"], 2),
                "revenue_share": round(safe_div(value["revenue"], total_revenue), 4),
                "sales": int(value["sales"]),
                "sales_share": round(safe_div(value["sales"], total_sales), 4),
                "item_count": int(value["items"]),
                "item_share": round(safe_div(value["items"], total_items), 4),
            }
        )

    return {
        "subject_count": len(groups),
        "missing_items": missing,
        "cr3": round(cr3, 4),
        f"cr{top_n}": round(cr_n, 4),
        f"cr{top_n}_by_sales": round(
            safe_div(sum(value["sales"] for _, value in ranked[:top_n]), total_sales), 4
        ),
        "hhi": round(hhi, 1),
        "warning": warning,
        "top_list": rows,
    }


def price_bands(
    items: list[dict[str, Any]],
    bins_count: int,
    valley_min_drop: float,
    max_bands: int,
) -> dict[str, Any]:
    points = [
        (float(item["price"]), float(item.get("sales") or 0), float(item.get("revenue") or 0))
        for item in items
        if item.get("price") is not None
    ]
    if not points:
        return {"bins": [], "valleys": [], "suggested_bands": []}

    prices = sorted(price for price, _, _ in points)
    low, high = prices[0], prices[-1]
    if high <= low:
        return {"bins": [], "valleys": [], "suggested_bands": [], "note": "No price variance"}

    width = (high - low) / bins_count
    bins = []
    for index in range(bins_count):
        bin_low = low + index * width
        bin_high = bin_low + width if index < bins_count - 1 else high + 1e-9
        selected = [point for point in points if bin_low <= point[0] < bin_high]
        bins.append(
            {
                "index": index + 1,
                "price_low": round(bin_low, 2),
                "price_high": round(bin_high, 2),
                "item_count": len(selected),
                "sales": int(sum(point[1] for point in selected)),
                "revenue": round(sum(point[2] for point in selected), 2),
                "average_sales": round(
                    safe_div(sum(point[1] for point in selected), len(selected)), 2
                ),
            }
        )

    sales_curve = [bucket["sales"] for bucket in bins]
    valleys = []
    for index in range(1, len(sales_curve) - 1):
        current, left, right = sales_curve[index - 1 : index + 2]
        if current >= left or current >= right:
            continue
        drops = [
            safe_div(left - current, left) if left else 0,
            safe_div(right - current, right) if right else 0,
        ]
        drop = min(drops)
        if drop >= valley_min_drop:
            valleys.append(
                {
                    "bin_index": index + 1,
                    "price": round(bins[index]["price_high"], 2),
                    "drop": round(drop, 4),
                }
            )

    if len(valleys) > max_bands - 1:
        valleys = sorted(valleys, key=lambda item: -item["drop"])[: max_bands - 1]
    valleys.sort(key=lambda item: item["bin_index"])
    boundaries = [low] + [valley["price"] for valley in valleys] + [high]

    configured = []
    for index in range(len(boundaries) - 1):
        band_low, band_high = boundaries[index], boundaries[index + 1]
        selected = [
            point
            for point in points
            if band_low <= point[0] and (point[0] < band_high or index == len(boundaries) - 2)
        ]
        configured.append(
            {
                "band_index": index + 1,
                "price_low": round(band_low, 2),
                "price_high": round(band_high, 2),
                "item_count": len(selected),
                "sales": int(sum(point[1] for point in selected)),
                "revenue": round(sum(point[2] for point in selected), 2),
                "average_sales": round(
                    safe_div(sum(point[1] for point in selected), len(selected)), 2
                ),
            }
        )

    return {
        "price_range": [round(low, 2), round(high, 2)],
        "bin_width": round(width, 2),
        "bins": bins,
        "valleys": valleys,
        "suggested_bands": configured,
        "valley_min_drop": valley_min_drop,
        "max_bands": max_bands,
    }


def config_matrix(items: list[dict[str, Any]], fields: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    total_items = len(items)
    for field in fields:
        groups: dict[str, dict[str, float]] = {}
        missing = 0
        for item in items:
            raw = item.get(field)
            value = str(raw).strip() if raw not in (None, "") else ""
            if not value:
                missing += 1
                continue
            group = groups.setdefault(value, {"items": 0, "sales": 0.0, "revenue": 0.0})
            group["items"] += 1
            group["sales"] += float(item.get("sales") or 0)
            group["revenue"] += float(item.get("revenue") or 0)

        total_sales = sum(group["sales"] for group in groups.values())
        total_revenue = sum(group["revenue"] for group in groups.values())
        average_sales = safe_div(total_sales, max(total_items - missing, 1))
        equal_share = safe_div(1, len(groups))
        rows = []
        for value, group in groups.items():
            item_share = safe_div(group["items"], total_items)
            sales_share = safe_div(group["sales"], total_sales)
            avg_sales = safe_div(group["sales"], group["items"])
            flags = []
            if sales_share >= 0.30:
                flags.append("HIGH_SALES_SHARE")
            if average_sales and avg_sales >= average_sales * 1.2:
                flags.append("HIGH_ITEM_EFFICIENCY")
            if item_share >= equal_share * 1.5:
                flags.append("MAINSTREAM_AND_CROWDED")
            if (
                equal_share
                and item_share <= equal_share * 0.6
                and average_sales
                and avg_sales >= average_sales * 1.2
            ):
                flags.append("POTENTIAL_OPPORTUNITY")
            rows.append(
                {
                    "value": value,
                    "item_count": int(group["items"]),
                    "item_share": round(item_share, 4),
                    "sales": int(group["sales"]),
                    "sales_share": round(sales_share, 4),
                    "revenue": round(group["revenue"], 2),
                    "revenue_share": round(safe_div(group["revenue"], total_revenue), 4),
                    "average_sales": round(avg_sales, 2),
                    "flags": flags,
                }
            )
        rows.sort(key=lambda row: (-row["sales"], row["value"]))
        result[field] = {
            "value_count": len(groups),
            "missing_items": missing,
            "average_sales_per_listing": round(average_sales, 2),
            "rows": rows,
        }
    return result


def new_listing_signal(items: list[dict[str, Any]], new_days: int) -> dict[str, Any]:
    aged = [item for item in items if item.get("listing_age_days") is not None]
    if len(aged) < 5:
        return {
            "status": "DATA_INSUFFICIENT",
            "aged_listing_count": len(aged),
            "reason": "Fewer than five listings have reliable listing age.",
        }

    new_items = [item for item in aged if item["listing_age_days"] <= new_days]
    old_items = [item for item in aged if item["listing_age_days"] > new_days]
    total_sales = sum(float(item.get("sales") or 0) for item in aged)
    avg_all = safe_div(total_sales, len(aged))
    avg_new = safe_div(sum(float(item.get("sales") or 0) for item in new_items), len(new_items))
    avg_old = safe_div(sum(float(item.get("sales") or 0) for item in old_items), len(old_items))
    return {
        "status": "OK" if len(new_items) >= 5 else "SMALL_NEW_SAMPLE",
        "new_listing_days": new_days,
        "aged_listing_count": len(aged),
        "new_listing_count": len(new_items),
        "new_listing_item_share": round(safe_div(len(new_items), len(aged)), 4),
        "new_listing_sales_share": round(
            safe_div(sum(float(item.get("sales") or 0) for item in new_items), total_sales), 4
        ),
        "new_listing_average_sales": round(avg_new, 2),
        "old_listing_average_sales": round(avg_old, 2),
        "all_listing_average_sales": round(avg_all, 2),
        "new_vs_all_efficiency": round(safe_div(avg_new, avg_all), 2),
    }


def discount_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    discounts = [
        float(item["discount_rate"])
        for item in items
        if item.get("discount_rate") is not None
    ]
    if not discounts:
        return {"status": "NO_DATA", "listing_count": 0}
    return {
        "status": "OK",
        "listing_count": len(discounts),
        "average_discount_rate": round(statistics.mean(discounts), 4),
        "median_discount_rate": round(statistics.median(discounts), 4),
        "share_with_discount": round(sum(value > 0 for value in discounts) / len(discounts), 4),
    }


def render_report(payload: dict[str, Any]) -> str:
    meta = payload["meta"]
    capacity = payload["market_capacity"]
    currency = meta["currency"]
    lines = [
        "# Temu 类目指标报告",
        "",
        f"- 市场：{meta.get('market_id')}",
        f"- 数据日期：{meta.get('data_date')}",
        f"- 销量窗口：{meta.get('sales_window_days')} 天",
        f"- 币种：{currency}",
        f"- 样本：{capacity['listing_count']} 个商品",
        f"- 数据源：`{meta.get('source_file', '')}`",
        "",
        "## 市场容量",
        "",
        f"- 窗口总销量：{capacity['total_sales']:,}",
        f"- 窗口总销售额：{money(capacity['total_revenue'], currency)}",
        f"- 均价：{money(capacity['average_price'], currency)}",
        f"- 中位价：{money(capacity['median_price'], currency)}",
        f"- 隐含均价：{money(capacity['implied_average_price'], currency)}",
        f"- 单商品平均销量：{capacity['average_sales_per_listing']:.2f}",
    ]

    for key, title in (
        ("brand_concentration", "品牌集中度"),
        ("seller_concentration", "卖家集中度"),
    ):
        concentration_data = payload[key]
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                f"- 主体数：{concentration_data['subject_count']}",
                f"- CR3：{pct(concentration_data['cr3'])}",
                f"- CR10：{pct(concentration_data['cr10'])}",
                f"- HHI：{concentration_data['hhi']}",
            ]
        )
        if concentration_data.get("warning"):
            lines.append(f"- 警告：{concentration_data['warning']}")
        if concentration_data.get("missing_items"):
            lines.append(f"- 未填写商品：{concentration_data['missing_items']}")

    bands = payload["price_bands"]
    lines.extend(["", "## 价格带", ""])
    if bands.get("suggested_bands"):
        lines.append("| 区间 | 商品数 | 销量 | 均销 | 销售额 |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for band in bands["suggested_bands"]:
            lines.append(
                f"| {money(band['price_low'], currency)} - {money(band['price_high'], currency)} | "
                f"{band['item_count']} | {band['sales']:,} | {band['average_sales']:.2f} | "
                f"{money(band['revenue'], currency)} |"
            )
    else:
        lines.append("未检测到可用价格带。")

    signal = payload["new_listing_signal"]
    lines.extend(
        [
            "",
            "## 新上架信号",
            "",
            f"- 状态：{signal['status']}",
            f"- 新链接数量：{signal.get('new_listing_count', 0)}",
            f"- 新链接销量份额：{pct(signal.get('new_listing_sales_share', 0))}",
            f"- 新链接相对全部链接效率：{signal.get('new_vs_all_efficiency', 0)}",
        ]
    )

    comparisons = payload.get("config_matrix", {})
    if comparisons:
        lines.extend(["", "## 配置组合", ""])
        for field, matrix in comparisons.items():
            lines.append(f"### {field}")
            lines.append("")
            lines.append("| 值 | 商品数 | 数量占比 | 销量占比 | 均销 | 标记 |")
            lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
            for row in matrix["rows"]:
                lines.append(
                    f"| {row['value']} | {row['item_count']} | {pct(row['item_share'])} | "
                    f"{pct(row['sales_share'])} | {row['average_sales']:.2f} | "
                    f"{', '.join(row['flags']) or '-'} |"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def output_paths(prefix: Path) -> tuple[Path, Path]:
    return Path(f"{prefix}.metrics.json"), Path(f"{prefix}.metrics.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--config-fields", default="")
    parser.add_argument("--bins", type=int)
    parser.add_argument("--valley-min-drop-pct", type=float)
    parser.add_argument("--max-bands", type=int)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--format", choices=["md", "json", "both"], default="both")
    parser.add_argument("--output-prefix", type=Path)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not items:
        raise SystemExit("No items found")
    config = json.loads(args.config.read_text(encoding="utf-8")) if args.config else {}

    bins = args.bins or int(config.get("price_bins", 10))
    valley_pct = (
        args.valley_min_drop_pct
        if args.valley_min_drop_pct is not None
        else float(config.get("valley_min_drop_pct", 15))
    )
    max_bands = args.max_bands or int(config.get("max_price_bands", 5))
    new_days = int(config.get("new_listing_days", 90))
    fields = [field.strip() for field in args.config_fields.split(",") if field.strip()]

    payload = {
        "meta": data["meta"],
        "market_capacity": market_capacity(items),
        "brand_concentration": concentration(items, "brand", args.top),
        "seller_concentration": concentration(items, "seller", args.top),
        "price_bands": price_bands(items, bins, valley_pct / 100, max_bands),
        "new_listing_signal": new_listing_signal(items, new_days),
        "discount_summary": discount_summary(items),
        "config_matrix": config_matrix(items, fields),
    }

    prefix = args.output_prefix or args.input.with_suffix("").with_suffix("")
    json_path, md_path = output_paths(prefix)
    if args.format in {"json", "both"}:
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON: {json_path}")
    if args.format in {"md", "both"}:
        report = render_report(payload)
        md_path.write_text(report, encoding="utf-8")
        print(report)
        print(f"Markdown: {md_path}")


if __name__ == "__main__":
    main()
