"""TongDaXin-style helper transforms used by technical indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd


def tdx_sma(series: pd.Series, n: int, m: int = 1) -> pd.Series:
    """通达信 SMA(X, N, M): Y = (M*X + (N-M)*Y') / N"""
    values = series.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    if len(values) == 0:
        return pd.Series(out, index=series.index)

    prev = values[0]
    out[0] = prev
    for i in range(1, len(values)):
        x = values[i]
        if np.isnan(x):
            out[i] = prev
        else:
            prev = (m * x + (n - m) * prev) / n
            out[i] = prev
    return pd.Series(out, index=series.index)


def tdx_ema(series: pd.Series, n: int) -> pd.Series:
    """通达信 EMA(X, N): Y = (2*X + (N-1)*Y') / (N+1)"""
    values = series.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    if len(values) == 0:
        return pd.Series(out, index=series.index)

    prev = values[0]
    out[0] = prev
    alpha = 2.0 / (n + 1)
    for i in range(1, len(values)):
        x = values[i]
        if np.isnan(x):
            out[i] = prev
        else:
            prev = alpha * x + (1 - alpha) * prev
            out[i] = prev
    return pd.Series(out, index=series.index)


def tdx_ma(series: pd.Series, n: int) -> pd.Series:
    """简单移动平均 MA(X, N)"""
    return series.rolling(window=n, min_periods=n).mean()


def tdx_std(series: pd.Series, n: int) -> pd.Series:
    """总体标准差 STD(X, N) — 与通达信一致用 ddof=0"""
    return series.rolling(window=n, min_periods=n).std(ddof=0)


def tdx_llv(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(window=n, min_periods=n).min()


def tdx_hhv(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(window=n, min_periods=n).max()
