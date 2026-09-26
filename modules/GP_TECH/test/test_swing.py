from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from GP_TECH.indicators.swing import (
    detect_swing_turning_points,
    recent_swings_from_ohlcv,
    resolve_min_change,
    swings_payload_from_ohlcv,
)


def _zigzag_ohlcv(n: int = 60) -> pd.DataFrame:
    """Synthetic path with clear alternating swings every ~10 bars."""
    close = []
    price = 100.0
    direction = 1
    for i in range(n):
        if i and i % 10 == 0:
            direction *= -1
        price += direction * 1.2
        close.append(price)
    close = np.asarray(close, dtype=float)
    return pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=n, freq="B"),
            "open": close,
            "high": close + 0.3,
            "low": close - 0.3,
            "close": close,
            "volume": np.full(n, 1e5),
        }
    )


class SwingDetectionTests(unittest.TestCase):
    def test_detects_alternating_highs_and_lows(self):
        df = _zigzag_ohlcv()
        swings = detect_swing_turning_points(df, n=2, min_change=0.01, min_distance=3)
        self.assertGreaterEqual(len(swings), 4)
        kinds = swings["kind"].tolist()
        for prev, cur in zip(kinds, kinds[1:]):
            self.assertNotEqual(prev, cur)
        # Last n bars cannot be confirmed.
        self.assertTrue((swings["index"] < len(df) - 2).all())

    def test_adaptive_min_change_for_low_span(self):
        df = _zigzag_ohlcv()
        # Compress range so fixed 3% would wipe most swings.
        df = df.copy()
        mid = df["close"].mean()
        df["close"] = mid + (df["close"] - mid) * 0.05
        df["open"] = df["close"]
        df["high"] = df["close"] + 0.05
        df["low"] = df["close"] - 0.05
        resolved = resolve_min_change(df, None, adaptive=True)
        self.assertLess(resolved, 0.03)
        payload = swings_payload_from_ohlcv(df, n=2, min_distance=3)
        self.assertGreater(payload["count"], 0)
        self.assertTrue(payload["params"]["adaptive"])
        self.assertEqual(payload["markers"][0]["kind"] in ("high", "low"), True)
        self.assertIn("time", payload["markers"][0])

    def test_fixed_min_change_disables_adaptive_flag(self):
        df = _zigzag_ohlcv()
        payload = swings_payload_from_ohlcv(df, min_change=0.02, adaptive=True)
        self.assertFalse(payload["params"]["adaptive"])
        self.assertAlmostEqual(payload["params"]["min_change"], 0.02)

    def test_recent_swings_filters_by_confirmed_at_lookback(self):
        df = _zigzag_ohlcv(80)
        all_markers = swings_payload_from_ohlcv(df, n=2, min_change=0.01, min_distance=3)["markers"]
        self.assertGreater(len(all_markers), 0)
        lookback = 3
        n = 2
        recent = recent_swings_from_ohlcv(df, lookback=lookback, n=n, min_change=0.01, min_distance=3)
        points = detect_swing_turning_points(df, n=n, min_change=0.01, min_distance=3)
        min_confirmed = len(df) - lookback
        expected = points[points["confirmed_at"] >= min_confirmed]
        self.assertEqual(recent["count"], len(expected))
        for row in recent["markers"]:
            self.assertIn(row["kind"], ("high", "low"))
        self.assertEqual(recent["buy"], any(m["kind"] == "low" for m in recent["markers"]))
        self.assertEqual(recent["sell"], any(m["kind"] == "high" for m in recent["markers"]))


if __name__ == "__main__":
    unittest.main()
