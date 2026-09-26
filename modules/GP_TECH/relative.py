"""Relative strength vs a benchmark index (correlation / beta / excess)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

DEFAULT_BENCHMARK_IDE = "sh000001"


def daily_returns(closes: pd.Series) -> pd.Series:
    """Close-to-close simple returns; index should be trading dates."""
    closes = pd.to_numeric(closes, errors="coerce")
    returns = closes.pct_change()
    return returns.replace([np.inf, -np.inf], np.nan).dropna()


def align_returns(
    stock_closes: pd.Series,
    index_closes: pd.Series,
) -> pd.DataFrame:
    """Align stock/index daily returns on common dates."""
    stock_r = daily_returns(stock_closes)
    index_r = daily_returns(index_closes)
    aligned = pd.concat(
        [stock_r.rename("stock"), index_r.rename("index")],
        axis=1,
        join="inner",
    ).dropna()
    return aligned


def pearson_corr(aligned: pd.DataFrame) -> float | None:
    if aligned is None or len(aligned) < 10:
        return None
    corr = float(aligned["stock"].corr(aligned["index"]))
    if not math.isfinite(corr):
        return None
    return round(corr, 4)


def beta(aligned: pd.DataFrame) -> float | None:
    if aligned is None or len(aligned) < 10:
        return None
    var = float(aligned["index"].var())
    if not math.isfinite(var) or var <= 0:
        return None
    value = float(aligned["stock"].cov(aligned["index"]) / var)
    if not math.isfinite(value):
        return None
    return round(value, 4)


def excess_return(aligned: pd.DataFrame, window: int | None = None) -> float | None:
    """Cumulative excess return over the last ``window`` aligned days.

    ``prod(1+r_stock) - prod(1+r_index)``, as a fraction (not percent).
    """
    if aligned is None or aligned.empty:
        return None
    data = aligned.tail(int(window)) if window else aligned
    if len(data) < 2:
        return None
    stock_cum = float((1.0 + data["stock"]).prod() - 1.0)
    index_cum = float((1.0 + data["index"]).prod() - 1.0)
    if not math.isfinite(stock_cum) or not math.isfinite(index_cum):
        return None
    return round(stock_cum - index_cum, 6)


def relative_metrics(
    stock_closes: pd.Series,
    index_closes: pd.Series,
    *,
    corr_window: int = 60,
    excess_window: int = 21,
) -> dict:
    """Compute correlation, beta and excess return for one stock vs index."""
    aligned = align_returns(stock_closes, index_closes)
    if aligned.empty:
        return {
            "corr": None,
            "beta": None,
            "excess": None,
            "sample_days": 0,
        }

    corr_aligned = aligned.tail(max(10, int(corr_window)))
    excess_aligned = aligned.tail(max(2, int(excess_window)))
    return {
        "corr": pearson_corr(corr_aligned),
        "beta": beta(corr_aligned),
        "excess": excess_return(excess_aligned),
        "sample_days": int(len(corr_aligned)),
    }


def closes_series(ohlc: pd.DataFrame) -> pd.Series:
    """Extract a date-indexed close series from OHLC frame."""
    if ohlc is None or ohlc.empty or "close" not in ohlc.columns:
        return pd.Series(dtype=float)
    frame = ohlc.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    return (
        frame.dropna(subset=["date", "close"])
        .set_index("date")["close"]
        .astype(float)
        .sort_index()
    )
