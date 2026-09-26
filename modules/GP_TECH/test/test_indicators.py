from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from GP_TECH.indicators import add_technical_indicators, calc_macd, calc_rsi


class IndicatorCalcTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        n = 80
        close = 100 + np.cumsum(rng.normal(0, 1, n))
        self.df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-01", periods=n, freq="B"),
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": rng.integers(1e5, 5e5, n),
            }
        )

    def test_macd_columns(self):
        macd = calc_macd(self.df["close"])
        self.assertListEqual(list(macd.columns), ["macd_dif", "macd_dea", "macd"])
        self.assertEqual(len(macd), len(self.df))
        self.assertTrue(np.isfinite(macd["macd"].iloc[-1]))

    def test_rsi_bounds(self):
        rsi = calc_rsi(self.df["close"], 14)
        self.assertTrue(((rsi.dropna() >= 0) & (rsi.dropna() <= 100)).all())

    def test_add_technical_indicators_include(self):
        out = add_technical_indicators(self.df, include=("macd", "kdj"))
        self.assertIn("macd_dif", out.columns)
        self.assertIn("kdj_k", out.columns)
        self.assertNotIn("rsi_6", out.columns)
        self.assertNotIn("boll_mid", out.columns)


if __name__ == "__main__":
    unittest.main()
