from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from GP_TECH.relative import align_returns, excess_return, pearson_corr, relative_metrics


class RelativeMetricsTests(unittest.TestCase):
    def test_perfect_correlation_and_zero_excess(self):
        dates = pd.date_range("2025-01-01", periods=80, freq="B")
        index = pd.Series(100 + np.arange(80) * 0.2, index=dates)
        stock = index * 1.05
        aligned = align_returns(stock, index)
        self.assertAlmostEqual(pearson_corr(aligned), 1.0, places=3)
        self.assertAlmostEqual(excess_return(aligned, window=21) or 0, 0.0, places=5)

    def test_positive_excess_with_low_corr(self):
        dates = pd.date_range("2025-01-01", periods=80, freq="B")
        rng = np.random.default_rng(7)
        index = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, size=80)), index=dates)
        # Independent drift upward vs flat-ish index noise
        stock = pd.Series(50 * np.cumprod(1 + 0.008 + rng.normal(0, 0.005, size=80)), index=dates)
        metrics = relative_metrics(stock, index, corr_window=60, excess_window=21)
        self.assertIsNotNone(metrics["corr"])
        self.assertIsNotNone(metrics["excess"])
        self.assertGreater(metrics["excess"], 0)
        self.assertLess(abs(metrics["corr"]), 0.6)

    def test_relative_metrics_handles_short_series(self):
        dates = pd.date_range("2025-01-01", periods=5, freq="B")
        stock = pd.Series([10, 11, 12, 13, 14], index=dates)
        index = pd.Series([100, 101, 102, 103, 104], index=dates)
        metrics = relative_metrics(stock, index, corr_window=60, excess_window=21)
        self.assertIsNone(metrics["corr"])
        self.assertEqual(metrics["sample_days"], 4)


if __name__ == "__main__":
    unittest.main()
