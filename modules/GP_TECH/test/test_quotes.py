from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from GP_TECH.data.quotes import _attach_pkv, load_fdk_ohlc, load_forward_ohlc, load_raw_ohlc


class QuotesAdjustmentTests(unittest.TestCase):
    def test_forward_adjustment_latest_equals_raw(self):
        quotes = pd.DataFrame(
            {
                "DT": pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]),
                "O": [100.0, 110.0, 120.0],
                "H": [101.0, 111.0, 121.0],
                "L": [99.0, 109.0, 119.0],
                "C": [100.0, 110.0, 120.0],
                "V": [1000, 1000, 1000],
            }
        )
        factors = pd.DataFrame(
            {
                "DT": pd.to_datetime(["1990-01-01", "2025-01-03"]),
                "PKV": [1.0, 2.0],
            }
        )
        kdb = object()

        with patch("GP_TECH.data.quotes._recent_raw_quotes", return_value=quotes.copy()), patch(
            "GP_TECH.data.quotes._adjustment_factors", return_value=factors.copy()
        ):
            raw = load_raw_ohlc(kdb, "sh600519", days=10, require_amount=False)
            forward = load_forward_ohlc(kdb, "sh600519", days=10, require_amount=False)

        self.assertAlmostEqual(forward["close"].iloc[-1], raw["close"].iloc[-1])
        self.assertAlmostEqual(forward["close"].iloc[0], 50.0)
        self.assertAlmostEqual(forward["close"].iloc[1], 110.0)
        self.assertEqual(forward.attrs["adjustment"], "forward")

    def test_attach_pkv_asof(self):
        raw = pd.DataFrame(
            {
                "DT": pd.to_datetime(["2025-01-02", "2025-01-06"]),
                "O": [1.0, 2.0],
                "C": [1.0, 2.0],
                "H": [1.0, 2.0],
                "L": [1.0, 2.0],
                "V": [1.0, 2.0],
            }
        )
        factors = pd.DataFrame(
            {
                "DT": pd.to_datetime(["1990-01-01", "2025-01-03"]),
                "PKV": [1.0, 2.0],
            }
        )
        merged = _attach_pkv(raw, factors)
        self.assertEqual(merged["PKV"].tolist(), [1.0, 2.0])

    def test_load_fdk_ohlc_uses_fdk_stock(self):
        class FakeKDB:
            def FDK_STOCK(self, ide):
                del ide
                return pd.DataFrame(
                    {
                        "DT": ["2025-01-02", "2025-01-03", "2025-01-06"],
                        "O": [800.0, 810.0, 820.0],
                        "H": [805.0, 815.0, 825.0],
                        "L": [795.0, 805.0, 815.0],
                        "C": [801.0, 811.0, 885.0],
                        "V": [1.0, 2.0, 3.0],
                    }
                )

        out = load_fdk_ohlc(FakeKDB(), "sh600519", days=2)
        self.assertEqual(len(out), 2)
        self.assertAlmostEqual(out["close"].iloc[-1], 885.0)
        self.assertEqual(out.attrs["adjustment"], "fdk")
        self.assertListEqual(list(out.columns), ["date", "open", "close", "high", "low", "volume"])


if __name__ == "__main__":
    unittest.main()
