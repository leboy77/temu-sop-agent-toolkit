import sys
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "agents/01_market_research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from temu_market_metrics import (  # noqa: E402
    concentration,
    market_capacity,
    new_listing_signal,
    output_paths,
    price_bands,
)
from temu_parser import (  # noqa: E402
    build_column_map,
    normalize,
    read_rows,
    to_age_days,
    to_number,
)


class TemuParserTests(unittest.TestCase):
    def test_numeric_formats(self) -> None:
        self.assertEqual(to_number("$1,234.50"), 1234.5)
        self.assertEqual(to_number("1.2万"), 12000)
        self.assertEqual(to_number("€ 29,90"), 29.9)

    def test_age_formats(self) -> None:
        self.assertEqual(to_age_days("2个月", date(2026, 10, 29)), 60)
        self.assertEqual(to_age_days("2026-10-01", date(2026, 10, 29)), 28)

    def test_sample_is_parseable(self) -> None:
        path = ROOT / "agents/01_market_research/samples/us-y1-pod-listings.csv"
        rows = read_rows(path)
        column_map = build_column_map(list(rows[0]))
        items, stats = normalize(rows, column_map, date(2026, 10, 29))
        self.assertEqual(len(items), len(rows))
        self.assertEqual(stats["dropped"], 0)
        self.assertIn("listing_age_days", items[0])


class TemuMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.items = [
            {"price": 10, "sales": 10, "revenue": 100, "seller": "A", "brand": "X", "listing_age_days": 20},
            {"price": 11, "sales": 20, "revenue": 220, "seller": "A", "brand": "X", "listing_age_days": 40},
            {"price": 12, "sales": 30, "revenue": 360, "seller": "B", "brand": "Y", "listing_age_days": 200},
            {"price": 13, "sales": 15, "revenue": 195, "seller": "C", "brand": "UNKNOWN", "listing_age_days": 300},
            {"price": 14, "sales": 5, "revenue": 70, "seller": "D", "brand": "UNKNOWN", "listing_age_days": 350},
            {"price": 15, "sales": 4, "revenue": 60, "seller": "E", "brand": "UNKNOWN", "listing_age_days": 400},
        ]

    def test_capacity(self) -> None:
        result = market_capacity(self.items)
        self.assertEqual(result["listing_count"], 6)
        self.assertEqual(result["total_sales"], 84)
        self.assertEqual(result["total_revenue"], 1005)

    def test_concentration(self) -> None:
        result = concentration(self.items, "seller", top_n=3)
        self.assertEqual(result["subject_count"], 5)
        self.assertEqual(result["top_list"][0]["name"], "B")

    def test_new_listing_signal(self) -> None:
        result = new_listing_signal(self.items, 90)
        self.assertEqual(result["new_listing_count"], 2)
        self.assertEqual(result["status"], "SMALL_NEW_SAMPLE")

    def test_price_bands_return_structure(self) -> None:
        result = price_bands(self.items, bins_count=4, valley_min_drop=0.05, max_bands=3)
        self.assertTrue(result["bins"])
        self.assertIn("suggested_bands", result)

    def test_output_paths_do_not_overwrite_input(self) -> None:
        json_path, md_path = output_paths(Path("items.normalized"))
        self.assertEqual(json_path.name, "items.normalized.metrics.json")
        self.assertEqual(md_path.name, "items.normalized.metrics.md")


if __name__ == "__main__":
    unittest.main()
