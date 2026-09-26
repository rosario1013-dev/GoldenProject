"""Channel-state transitions."""

from __future__ import annotations

import pandas as pd

from .ascending import detect_ascending_channel

CHANNEL_MODES = {"in", "entered"}


def detect_channel_state(
    df: pd.DataFrame,
    *,
    mode: str = "in",
    lookback: int = 80,
    pivot_window: int = 5,
    min_score: int = 6,
) -> dict:
    """Detect current channel state or a new entry on the latest bar.

    ``mode="in"`` matches any stock currently in a channel.
    ``mode="entered"`` requires the prior bar not to match and the latest bar
    to match.
    """
    if mode not in CHANNEL_MODES:
        raise ValueError(f"Unknown channel mode: {mode}")

    current = detect_ascending_channel(
        df,
        lookback=lookback,
        pivot_window=pivot_window,
        min_score=min_score,
    )
    current["mode"] = mode

    if mode == "in":
        current["is_match"] = bool(current.get("is_channel"))
        return current

    previous = detect_ascending_channel(
        df.iloc[:-1],
        lookback=lookback,
        pivot_window=pivot_window,
        min_score=min_score,
    )
    current["previous_is_channel"] = bool(previous.get("is_channel"))
    current["previous_score"] = int(previous.get("score") or 0)
    current["is_match"] = bool(
        current.get("is_channel") and not previous.get("is_channel")
    )
    return current
