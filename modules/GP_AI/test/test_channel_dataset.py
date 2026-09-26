"""Unit tests for channel sample label helpers (no Mongo)."""

from __future__ import annotations

import unittest

import pandas as pd

from GP_AI.features.channel_dataset import broke_lower_rail, peak_mdd


class PeakMddTests(unittest.TestCase):
    def test_flat_path(self):
        path = pd.Series([10.0, 10.0, 10.0])
        self.assertEqual(peak_mdd(path, 10.0), 0.0)

    def test_rise_then_drawdown(self):
        # 10 -> 12 -> 9 : peak 12, trough 9 => (12-9)/12 = 0.25
        path = pd.Series([12.0, 9.0])
        self.assertAlmostEqual(peak_mdd(path, 10.0) or 0, 0.25, places=5)

    def test_broke_lower(self):
        path = pd.Series([10.0, 9.5, 8.0])
        self.assertTrue(broke_lower_rail(path, lower_0=9.0, buffer=0.98))
        self.assertFalse(broke_lower_rail(path, lower_0=7.0, buffer=0.98))


if __name__ == "__main__":
    unittest.main()
