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


if __name__ == "__main__":
    unittest.main()
