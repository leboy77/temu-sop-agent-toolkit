import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from preflight import load_json, load_price_rows, run_preflight  # noqa: E402


class PreflightTests(unittest.TestCase):
    def test_us_priced_example_advances(self) -> None:
        market = load_json(ROOT / "markets/us-y1-pod/market_profile.json")
        brief = load_json(ROOT / "examples/us-y1-pod/pilot-product.json")
        prices = load_price_rows(ROOT / "examples/us-y1-pod/pilot-price-sheet.csv")
        report = run_preflight(brief, market, prices, "PRICED")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["next_state"], "PRICED")
        self.assertEqual(report["next_action"], "03_assets")

    def test_us_assets_gate_blocks_without_assets(self) -> None:
        market = load_json(ROOT / "markets/us-y1-pod/market_profile.json")
        brief = load_json(ROOT / "examples/us-y1-pod/pilot-product.json")
        prices = load_price_rows(ROOT / "examples/us-y1-pod/pilot-price-sheet.csv")
        report = run_preflight(brief, market, prices, "ASSETS_READY")
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["next_action"], "03_assets")
        self.assertIn("INPUT_MISSING: main images", report["blockers"])
        self.assertIn("INPUT_MISSING: final title", report["blockers"])

    def test_market_mismatch_is_blocked(self) -> None:
        market = load_json(ROOT / "markets/eu-y2/market_profile.json")
        brief = load_json(ROOT / "examples/us-y1-pod/pilot-product.json")
        prices = load_price_rows(ROOT / "examples/us-y1-pod/pilot-price-sheet.csv")
        report = run_preflight(brief, market, prices, "PRICED")
        self.assertIn(
            "MARKET_MISMATCH: brief.market_id does not match market profile",
            report["blockers"],
        )

    def test_incomplete_price_row_is_reported(self) -> None:
        market = load_json(ROOT / "markets/us-y1-pod/market_profile.json")
        brief = load_json(ROOT / "examples/us-y1-pod/pilot-product.json")
        prices = load_price_rows(ROOT / "examples/us-y1-pod/pilot-price-sheet.csv")
        sku_id = brief["skus"][0]["sku_id"]
        prices[sku_id] = {
            "computed_status": "INVALID",
            "validation_error": "missing product_cost",
        }
        report = run_preflight(brief, market, prices, "PRICED")
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["next_action"], "02_pricing")
        self.assertTrue(
            any(item.startswith("PRICE_INPUT_INVALID:") for item in report["blockers"])
        )

    def test_complete_pilot_reaches_publish_ready(self) -> None:
        market = load_json(ROOT / "markets/us-y1-pod/market_profile.json")
        brief = load_json(ROOT / "examples/us-y1-pod/pilot-product.json")
        prices = load_price_rows(ROOT / "examples/us-y1-pod/pilot-price-sheet.csv")
        brief["assets"] = {
            "main_images": ["demo-front.svg", "demo-back.svg"],
            "skc_images": ["demo-color.svg"],
            "title_candidates": ["Demo title"],
            "title_final": "Demo title",
            "core_selling_point": "Verified demo selling point",
            "secondary_points": ["Verified point"],
            "rights_evidence": ["demo-rights.txt"]
        }
        brief["compliance"] = {
            "pack_ref": "demo-compliance.md",
            "status": "PASSED",
            "manufacturer_profile_id": "demo",
            "market_requirements": ["manufacturer_information"]
        }
        brief["approvals"] = {
            "selection": True,
            "pricing": True,
            "assets": True,
            "compliance": True
        }
        brief["skus"][0]["image_refs"] = ["demo-front.svg"]

        report = run_preflight(brief, market, prices, "PUBLISH_READY")

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["next_action"], "human_publish_approval")
        self.assertEqual(report["blockers"], [])


if __name__ == "__main__":
    unittest.main()
