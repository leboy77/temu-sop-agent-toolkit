import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from calc_eu_y2_pricing import (  # noqa: E402
    CountryRate,
    ProductPricing,
    calculate_rate,
    parse_weight_band,
    select_rates,
)


class EuY2PricingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.product = ProductPricing(
            weight_kg=Decimal("0.5"),
            purchase_cost=Decimal("38"),
            return_rate=Decimal("0.15"),
        )
        self.germany = CountryRate(
            country_name="德国",
            country_code="DE",
            weight_band="0.301-30KG",
            weight_low=Decimal("0.301"),
            weight_high=Decimal("30"),
            current_freight_per_kg=Decimal("46"),
            current_handling_fee=Decimal("28"),
            subsidy_amount=Decimal("19"),
            sale_price=Decimal("115"),
            minimum_sale_price=Decimal("95"),
            new_freight_per_kg=Decimal("49"),
            new_handling_fee=Decimal("28"),
        )

    def test_weight_band_parser(self) -> None:
        self.assertEqual(
            parse_weight_band("0.001-0.1KG"),
            (Decimal("0.001"), Decimal("0.1")),
        )
        self.assertEqual(
            parse_weight_band("0<W≤0.5"),
            (Decimal("0"), Decimal("0.5")),
        )

    def test_most_specific_overlapping_band_is_selected(self) -> None:
        narrow = self.germany
        wide = CountryRate(
            country_name="德国",
            country_code="DE",
            weight_band="0-30KG",
            weight_low=Decimal("0"),
            weight_high=Decimal("30"),
            current_freight_per_kg=Decimal("46"),
            current_handling_fee=Decimal("28"),
            subsidy_amount=Decimal("19"),
            sale_price=Decimal("115"),
            minimum_sale_price=Decimal("95"),
            new_freight_per_kg=Decimal("49"),
            new_handling_fee=Decimal("28"),
        )
        selected, warnings = select_rates([wide, narrow], Decimal("0.5"))
        self.assertEqual(warnings, [])
        self.assertEqual(selected[0].weight_band, "0.301-30KG")

    def test_sheet_formula_results(self) -> None:
        result = calculate_rate(self.product, self.germany)
        self.assertEqual(result["current_logistics_cny"], "51.00")
        self.assertEqual(result["landed_cost_cny"], "89.00")
        self.assertEqual(result["cost_after_returns_cny"], "102.35")
        self.assertEqual(result["launch_price_cny"], "230.00")
        self.assertEqual(result["traffic_acceleration_price_cny"], "126.50")
        self.assertEqual(result["normal_profit_cny"], "31.65")
        self.assertEqual(result["minimum_profit_cny"], "11.65")
        self.assertEqual(result["new_logistics_profit_cny"], "29.92")
        self.assertEqual(result["new_logistics_roi_pct"], "33.07")


if __name__ == "__main__":
    unittest.main()
