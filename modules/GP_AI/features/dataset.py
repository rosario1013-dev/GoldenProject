"""Construct labeled training frames from Mongo quotes."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from GP_KDB.utils import security_type
from GP_TECH.data.quotes import load_forward_ohlc
from GP_TECH.relative import closes_series

from ..config import DEFAULT_FEATURE_CONFIG, DEFAULT_TRAIN_CONFIG, FEATURE_COLUMNS, FeatureConfig, TrainConfig
from .builders import build_feature_row


def _candidate_ides(kdb, max_ides: int) -> list[str]:
    ides = [ide for ide in (kdb.stocksIDEs() or []) if security_type(ide) == "stock"]
    return ides[: max(1, int(max_ides))]


def _as_of_dates(index_closes: pd.Series, count: int, horizon: int, min_history: int) -> list[pd.Timestamp]:
    if index_closes.empty:
        return []
    usable = index_closes.index[:-horizon] if horizon > 0 else index_closes.index
    if len(usable) <= min_history:
        return []
    usable = usable[min_history:]
    if len(usable) == 0:
        return []
    count = max(1, min(int(count), len(usable)))
    positions = np.linspace(0, len(usable) - 1, num=count, dtype=int)
    return [pd.Timestamp(usable[i]) for i in dict.fromkeys(positions)]


def _forward_excess(
    stock_closes: pd.Series,
    index_closes: pd.Series,
    as_of: pd.Timestamp,
    horizon: int,
) -> float | None:
    stock = stock_closes.loc[:as_of]
    index = index_closes.loc[:as_of]
    if stock.empty or index.empty:
        return None
    # Need future points after as_of
    stock_future = stock_closes.loc[stock_closes.index > as_of]
    index_future = index_closes.loc[index_closes.index > as_of]
    if len(stock_future) < horizon or len(index_future) < horizon:
        return None
    s0 = float(stock.iloc[-1])
    i0 = float(index.iloc[-1])
    s1 = float(stock_future.iloc[horizon - 1])
    i1 = float(index_future.iloc[horizon - 1])
    if min(s0, i0, s1, i1) <= 0 or not all(math.isfinite(x) for x in (s0, i0, s1, i1)):
        return None
    return (s1 / s0 - 1.0) - (i1 / i0 - 1.0)


def build_training_frame(
    kdb,
    *,
    feature_cfg: FeatureConfig = DEFAULT_FEATURE_CONFIG,
    train_cfg: TrainConfig = DEFAULT_TRAIN_CONFIG,
    ides: list[str] | None = None,
) -> pd.DataFrame:
    """Return rows with features + labels ``fwd_excess`` / ``buy_label`` / ``as_of``."""
    index_ohlc = load_forward_ohlc(
        kdb,
        feature_cfg.benchmark_ide,
        days=feature_cfg.history_days + train_cfg.horizon + 50,
        require_amount=False,
    )
    index_closes = closes_series(index_ohlc)
    if index_closes.empty:
        raise ValueError(f"无法加载基准指数行情: {feature_cfg.benchmark_ide}")

    candidates = ides or _candidate_ides(kdb, train_cfg.max_ides)
    as_ofs = _as_of_dates(
        index_closes,
        train_cfg.sample_as_of_count,
        train_cfg.horizon,
        train_cfg.min_history,
    )
    if not as_ofs:
        raise ValueError("基准指数历史不足以构造训练样本")

    fsa_map = kdb.fsa_latest_for_ides(candidates) if hasattr(kdb, "fsa_latest_for_ides") else {}

    rows: list[dict] = []
    for ide in candidates:
        ohlc = load_forward_ohlc(
            kdb,
            ide,
            days=feature_cfg.history_days + train_cfg.horizon + 50,
        )
        closes = closes_series(ohlc)
        if closes.empty or len(closes) < train_cfg.min_history + train_cfg.horizon:
            continue
        for as_of in as_ofs:
            hist = closes.loc[:as_of]
            idx_hist = index_closes.loc[:as_of]
            if len(hist) < train_cfg.min_history or len(idx_hist) < train_cfg.min_history:
                continue
            excess = _forward_excess(closes, index_closes, as_of, train_cfg.horizon)
            if excess is None:
                continue
            feat = build_feature_row(hist, idx_hist, fsa_map.get(ide), cfg=feature_cfg)
            feat.update(
                {
                    "ide": ide,
                    "as_of": str(pd.Timestamp(as_of).date()),
                    "fwd_excess": float(excess),
                    "buy_label": int(excess > train_cfg.buy_threshold),
                }
            )
            rows.append(feat)

    if not rows:
        return pd.DataFrame(columns=["ide", "as_of", "fwd_excess", "buy_label", *FEATURE_COLUMNS])
    return pd.DataFrame(rows)
