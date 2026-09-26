"""Technical indicator formulas (TongDaXin conventions)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .tdx_base import tdx_ema, tdx_hhv, tdx_llv, tdx_ma, tdx_sma, tdx_std


def calc_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """DIF / DEA / MACD histogram (柱 = (DIF-DEA)*2)."""
    dif = tdx_ema(close, fast) - tdx_ema(close, slow)
    dea = tdx_ema(dif, signal)
    macd = (dif - dea) * 2
    return pd.DataFrame(
        {"macd_dif": dif, "macd_dea": dea, "macd": macd},
        index=close.index,
    )


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI via TDX SMA(MAX(C-LC,0),N,1) / SMA(ABS(C-LC),N,1)*100."""
    lc = close.shift(1)
    gain = (close - lc).clip(lower=0)
    abs_move = (close - lc).abs()
    avg_gain = tdx_sma(gain.fillna(0), period, 1)
    avg_abs = tdx_sma(abs_move.fillna(0), period, 1)
    rsi = avg_gain / avg_abs.replace(0, np.nan) * 100
    return rsi.rename(f"rsi_{period}")


def calc_rsi_multi(close: pd.Series, periods: tuple[int, ...] = (6, 12, 24)) -> pd.DataFrame:
    return pd.concat([calc_rsi(close, p) for p in periods], axis=1)


def calc_kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> pd.DataFrame:
    """KDJ with RSV / K / D / J."""
    llv = tdx_llv(low, n)
    hhv = tdx_hhv(high, n)
    denom = (hhv - llv).replace(0, np.nan)
    rsv = (close - llv) / denom * 100
    k = tdx_sma(rsv.fillna(50), m1, 1)
    d = tdx_sma(k, m2, 1)
    j = 3 * k - 2 * d
    return pd.DataFrame({"kdj_k": k, "kdj_d": d, "kdj_j": j}, index=close.index)


def calc_boll(
    close: pd.Series,
    n: int = 20,
    p: float = 2.0,
) -> pd.DataFrame:
    mid = tdx_ma(close, n)
    std = tdx_std(close, n)
    return pd.DataFrame(
        {
            "boll_mid": mid,
            "boll_upper": mid + p * std,
            "boll_lower": mid - p * std,
        },
        index=close.index,
    )


def calc_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff().fillna(0))
    return (direction * volume.fillna(0)).cumsum().rename("obv")


def add_technical_indicators(
    ohlcv: pd.DataFrame,
    *,
    macd_params: tuple[int, int, int] = (12, 26, 9),
    rsi_periods: tuple[int, ...] = (6, 12, 24),
    kdj_params: tuple[int, int, int] = (9, 3, 3),
    boll_params: tuple[int, float] = (20, 2.0),
    include: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Append indicator columns onto an OHLCV DataFrame.

    ``include`` selects groups: ``macd``, ``rsi``, ``kdj``, ``boll``, ``obv``.
    Default: all groups.
    """
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(ohlcv.columns)
    if missing:
        raise ValueError(f"缺少列: {sorted(missing)}")

    wanted = set(include) if include is not None else {"macd", "rsi", "kdj", "boll", "obv"}
    out = ohlcv.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]
    volume = out["volume"]

    parts: list[pd.DataFrame | pd.Series] = [out]
    if "macd" in wanted:
        parts.append(calc_macd(close, *macd_params))
    if "rsi" in wanted:
        parts.append(calc_rsi_multi(close, rsi_periods))
    if "kdj" in wanted:
        parts.append(calc_kdj(high, low, close, *kdj_params))
    if "boll" in wanted:
        parts.append(calc_boll(close, *boll_params))
    if "obv" in wanted:
        parts.append(calc_obv(close, volume))

    return pd.concat(parts, axis=1)
