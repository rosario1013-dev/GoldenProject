from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from GP_TECH.channel.ascending import detect_ascending_channel, fit_line
from GP_TECH.channel.entered import detect_channel_state


def ascending_sample(size: int = 100) -> pd.DataFrame:
    x = np.arange(size, dtype=float)
    close = 10 + 0.1 * x + 0.5 * np.sin(2 * np.pi * x / 10)
    return pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=size, freq="B"),
            "open": close - 0.05,
            "close": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "volume": np.full(size, 1_000_000),
        }
    )


class AscendingChannelTests(unittest.TestCase):
    def test_fit_line(self):
        x = np.arange(10, dtype=float)
        slope, intercept, r_squared = fit_line(x, 2 * x + 3)
        self.assertAlmostEqual(slope, 2.0)
        self.assertAlmostEqual(intercept, 3.0)
        self.assertAlmostEqual(r_squared, 1.0)

    def test_detects_clean_ascending_channel(self):
        result = detect_ascending_channel(ascending_sample(), lookback=80)
        self.assertTrue(result["is_channel"])
        self.assertGreaterEqual(result["score"], 6)
        self.assertEqual(result["as_of"], "2025-05-20")

    def test_entered_requires_transition(self):
        df = ascending_sample()
        with patch(
            "GP_TECH.channel.entered.detect_ascending_channel",
            side_effect=[
                {"is_channel": True, "score": 6, "score_text": "6/7"},
                {"is_channel": False, "score": 5, "score_text": "5/7"},
            ],
        ):
            result = detect_channel_state(df, mode="entered")
        self.assertTrue(result["is_match"])
        self.assertFalse(result["previous_is_channel"])
        self.assertEqual(result["previous_score"], 5)

    def test_in_mode_uses_current_state(self):
        with patch(
            "GP_TECH.channel.entered.detect_ascending_channel",
            return_value={"is_channel": True, "score": 7, "score_text": "7/7"},
        ):
            result = detect_channel_state(ascending_sample(), mode="in")
        self.assertTrue(result["is_match"])


if __name__ == "__main__":
    unittest.main()
