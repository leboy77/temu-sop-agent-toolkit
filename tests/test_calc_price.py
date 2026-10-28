import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from calc_price import calculate  # noqa: E402


class PriceCalculationTests(unittest.TestCase):
    def base_row(self) -> dict[str, str]:
        return {
            "product_brief_id": "TEST-001",
            "sku_id": "SKU-1",
            "currency": "CNY",
            "product_cost": "50",
            "freight_per_kg": "70",
            "weight_kg": "0.6",
            "freight_fixed": "5",
            "return_rate_pct": "7",
            "platform_fee_pct": "10",
            "ad_cost_pct": "5",
            "target_margin_pct": "20",
            "target_price": "150",
        }

    def test_break_even_price(self) -> None:
        result = calculate(self.base_row())
        self.assertEqual(result["break_even_price"], "122.11")

    def test_target_floor_price(self) -> None:
        result = calculate(self.base_row())
        self.assertEqual(result["target_floor_price"], "159.68")

    def test_between_break_even_and_target_is_review(self) -> None:
        result = calculate(self.base_row())
        self.assertEqual(result["computed_status"], "REVIEW_REQUIRED")

    def test_below_break_even_is_blocked(self) -> None:
        row = self.base_row()
        row["target_price"] = "90"
        result = calculate(row)
        self.assertEqual(result["computed_status"], "BLOCKED")

    def test_missing_cost_is_rejected(self) -> None:
        row = self.base_row()
        row["product_cost"] = ""
        with self.assertRaises(ValueError):
            calculate(row)


if __name__ == "__main__":
    unittest.main()
