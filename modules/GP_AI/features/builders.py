"""Build per-stock feature rows from OHLC + FSA + relative strength."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from GP_TECH.data.quotes import load_forward_ohlc
from GP_TECH.relative import closes_series, relative_metrics

from ..config import DEFAULT_FEATURE_CONFIG, FEATURE_COLUMNS, FeatureConfig

__all__ = ["FEATURE_COLUMNS", "build_feature_row", "features_frame_for_ides"]


def _pct_change(closes: pd.Series, offset: int) -> float | None:
    if closes is None or len(closes) <= offset:
        return None
    last = float(closes.iloc[-1])
    base = float(closes.iloc[-(offset + 1)])
    if not math.isfinite(last) or not math.isfinite(base) or base == 0:
        return None
    return round((last / base - 1.0) * 100.0, 4)


def _volatility(closes: pd.Series, window: int) -> float | None:
    if closes is None or len(closes) < window + 1:
        return None
    rets = closes.pct_change().dropna().tail(window)
    if len(rets) < max(5, window // 2):
        return None
    value = float(rets.std() * 100.0)
    return round(value, 4) if math.isfinite(value) else None


def _ma_dev(closes: pd.Series, window: int) -> float | None:
    if closes is None or len(closes) < window:
        return None
    ma = float(closes.tail(window).mean())
    last = float(closes.iloc[-1])
    if not math.isfinite(ma) or not math.isfinite(last) or ma == 0:
        return None
    return round((last / ma - 1.0) * 100.0, 4)


def build_feature_row(
    stock_closes: pd.Series,
    index_closes: pd.Series,
    fsa: dict | None = None,
    *,
    cfg: FeatureConfig = DEFAULT_FEATURE_CONFIG,
) -> dict:
    """Build one feature dict from close series + optional FSA snapshot."""
    fsa = fsa or {}
    rel = relative_metrics(
        stock_closes,
        index_closes,
        corr_window=cfg.corr_window,
        excess_window=cfg.excess_window,
    )
    row = {
        "chg_1d": _pct_change(stock_closes, 1),
        "chg_3d": _pct_change(stock_closes, 3),
        "chg_5d": _pct_change(stock_closes, 5),
        "chg_1m": _pct_change(stock_closes, 21),
        "volatility_20": _volatility(stock_closes, cfg.vol_window),
        "ma20_dev": _ma_dev(stock_closes, cfg.ma_window),
        "corr_60": rel.get("corr"),
        "beta_60": rel.get("beta"),
        "excess_21": None if rel.get("excess") is None else round(float(rel["excess"]) * 100.0, 4),
        "ROE": fsa.get("ROE"),
        "ROA": fsa.get("ROA"),
        "归母净利润同比": fsa.get("归母净利润同比"),
        "营业总收入同比": fsa.get("营业总收入同比"),
        "毛利率": fsa.get("毛利率"),
        "BPS": fsa.get("BPS"),
    }
    return row


def features_frame_for_ides(
    kdb,
    ides: list[str],
    *,
    cfg: FeatureConfig = DEFAULT_FEATURE_CONFIG,
    index_closes: pd.Series | None = None,
) -> pd.DataFrame:
    """Build a feature DataFrame indexed by IDE for the latest available bars."""
    if index_closes is None:
        index_ohlc = load_forward_ohlc(
            kdb,
            cfg.benchmark_ide,
            days=cfg.history_days,
            require_amount=False,
        )
        index_closes = closes_series(index_ohlc)
    if index_closes.empty:
        raise ValueError(f"无法加载基准指数行情: {cfg.benchmark_ide}")

    fsa_map = {}
    if hasattr(kdb, "fsa_latest_for_ides"):
        fsa_map = kdb.fsa_latest_for_ides(ides) or {}

    rows: list[dict] = []
    for ide in ides:
        ohlc = load_forward_ohlc(kdb, ide, days=cfg.history_days)
        closes = closes_series(ohlc)
        if closes.empty or len(closes) < 30:
            continue
        feat = build_feature_row(closes, index_closes, fsa_map.get(ide), cfg=cfg)
        feat["ide"] = ide
        rows.append(feat)

    if not rows:
        return pd.DataFrame(columns=["ide", *FEATURE_COLUMNS])
    frame = pd.DataFrame(rows).set_index("ide")
    return frame.reindex(columns=list(FEATURE_COLUMNS))


def matrix_from_frame(frame: pd.DataFrame) -> np.ndarray:
    """Convert feature frame to float matrix with NaN → column median → 0."""
    data = frame.reindex(columns=list(FEATURE_COLUMNS)).astype(float)
    for col in data.columns:
        median = data[col].median(skipna=True)
        if pd.isna(median):
            median = 0.0
        data[col] = data[col].fillna(median)
    return data.to_numpy(dtype=float)
