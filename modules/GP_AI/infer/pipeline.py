"""Online buy-advice inference pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd

from GP_KDB.utils import security_type
from GP_TECH.channel.entered import detect_channel_state
from GP_TECH.data.quotes import load_forward_ohlc

from ..config import DEFAULT_ADVICE_CONFIG, DEFAULT_FEATURE_CONFIG, AdviceConfig, FeatureConfig
from ..features.builders import FEATURE_COLUMNS, features_frame_for_ides, matrix_from_frame
from ..scoring import anomaly_norm, composite_score, normalize_rank_scores, trend_score
from .models import ModelBundle, load_models


def _unique(values: Iterable[str] | None) -> list[str]:
    return list(dict.fromkeys(str(v).strip() for v in (values or []) if str(v).strip()))


def resolve_universe(
    kdb,
    *,
    ides: list[str] | None = None,
    industries: list[str] | None = None,
    pool_category: str | None = None,
    username: str = "default",
) -> list[str]:
    requested = _unique(ides)
    if requested:
        return [ide for ide in requested if security_type(ide) == "stock"]

    industry_names = _unique(industries)
    # 「全部行业」means the full stock universe (optionally intersected with pool).
    scan_all = any(name in {"全部行业", "*"} for name in industry_names)
    if scan_all:
        industry_names = []

    pool_ides: list[str] = []
    if pool_category and hasattr(kdb, "pool_stocks"):
        rows = kdb.pool_stocks(pool_category, username) or []
        pool_ides = [
            row["ide"]
            for row in rows
            if row.get("ide") and security_type(row["ide"]) == "stock"
        ]

    industry_ides: list[str] | None = None
    if industry_names and hasattr(kdb, "ides_for_industries"):
        found = kdb.ides_for_industries(industry_names) or []
        industry_ides = [ide for ide in found if security_type(ide) == "stock"]
    elif scan_all:
        industry_ides = None  # no industry filter

    if pool_ides and industry_ides is not None:
        allowed = set(industry_ides)
        return [ide for ide in pool_ides if ide in allowed]
    if pool_ides:
        return pool_ides
    if industry_ides is not None:
        return industry_ides

    return [ide for ide in (kdb.stocksIDEs() or []) if security_type(ide) == "stock"]


def _predict_rank(model, X: np.ndarray) -> np.ndarray:
    return np.asarray(model.predict(X), dtype=float)


def _predict_proba(model, X: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)
        return np.asarray(proba[:, 1] if proba.ndim == 2 else proba, dtype=float)
    raw = np.asarray(model.predict(X), dtype=float)
    # LightGBM binary raw / probability depending on version
    if len(raw) and raw.min() >= 0 and raw.max() <= 1:
        return raw
    return 1.0 / (1.0 + np.exp(-raw))


def _channel_for_ide(kdb, ide: str, cfg: AdviceConfig, feature_cfg: FeatureConfig) -> dict:
    data = load_forward_ohlc(kdb, ide, days=feature_cfg.history_days)
    if data.empty:
        return {"is_match": False, "score": 0, "score_text": "0/7"}
    return detect_channel_state(
        data,
        mode="in",
        lookback=cfg.channel_lookback,
        pivot_window=cfg.channel_pivot_window,
        min_score=cfg.min_channel_score,
    )


def _candidate_indices(rank_raw: np.ndarray, signal_prob: np.ndarray, top_k: int) -> list[int]:
    """Union of top-K by ranker and top-K by buy probability."""
    n = len(rank_raw)
    k = max(1, min(int(top_k), n))
    by_rank = np.argsort(-rank_raw)[:k]
    by_signal = np.argsort(-signal_prob)[:k]
    return list(dict.fromkeys([*by_rank.tolist(), *by_signal.tolist()]))


def run_buy_advice(
    kdb,
    *,
    ides: list[str] | None = None,
    industries: list[str] | None = None,
    pool_category: str | None = None,
    username: str = "default",
    limit: int | None = None,
    p_min: float | None = None,
    require_channel: bool | None = None,
    top_k: int | None = None,
    drop_anomaly: bool | None = None,
    artifacts_dir: Path | None = None,
    advice_cfg: AdviceConfig = DEFAULT_ADVICE_CONFIG,
    feature_cfg: FeatureConfig = DEFAULT_FEATURE_CONFIG,
    models: ModelBundle | None = None,
    return_stats: bool = False,
):
    """Run ranker → signal → trend → anomaly → score and return advice rows.

    If ``return_stats`` is True, returns ``(rows, stats)``.
    """
    cfg = AdviceConfig(
        top_k=top_k if top_k is not None else advice_cfg.top_k,
        p_min=p_min if p_min is not None else advice_cfg.p_min,
        require_channel=advice_cfg.require_channel if require_channel is None else require_channel,
        min_channel_score=advice_cfg.min_channel_score,
        channel_lookback=advice_cfg.channel_lookback,
        channel_pivot_window=advice_cfg.channel_pivot_window,
        drop_anomaly=advice_cfg.drop_anomaly if drop_anomaly is None else drop_anomaly,
        limit=limit if limit is not None else advice_cfg.limit,
        rank_weight=advice_cfg.rank_weight,
        signal_weight=advice_cfg.signal_weight,
        trend_weight=advice_cfg.trend_weight,
        anomaly_weight=advice_cfg.anomaly_weight,
    )

    bundle = models or load_models(artifacts_dir)
    if not bundle.ready:
        missing = ", ".join(bundle.missing())
        raise ValueError(f"模型未就绪，缺少: {missing}。请先运行 python -m GP_AI train-ranker/train-signal/train-anomaly")

    universe = resolve_universe(
        kdb,
        ides=ides,
        industries=industries,
        pool_category=pool_category,
        username=username,
    )
    stats = {
        "universe": len(universe),
        "with_features": 0,
        "candidates": 0,
        "after_signal": 0,
        "after_anomaly": 0,
        "after_channel": 0,
        "returned": 0,
        "require_channel": cfg.require_channel,
        "p_min": cfg.p_min,
    }
    if not universe:
        return ([], stats) if return_stats else []

    feats = features_frame_for_ides(kdb, universe, cfg=feature_cfg)
    stats["with_features"] = int(len(feats))
    if feats.empty:
        return ([], stats) if return_stats else []

    X = matrix_from_frame(feats)
    id_list = list(feats.index)

    rank_raw = _predict_rank(bundle.ranker, X)
    signal_prob = _predict_proba(bundle.signal_lgb, X)
    keep_idx = _candidate_indices(rank_raw, signal_prob, cfg.top_k)
    stats["candidates"] = len(keep_idx)

    xgb_prob = (
        _predict_proba(bundle.signal_xgb, X)
        if bundle.signal_xgb is not None
        else np.full(len(id_list), np.nan)
    )

    anomaly_pred = np.asarray(bundle.anomaly.predict(X), dtype=int)
    anomaly_scores = None
    if hasattr(bundle.anomaly, "score_samples"):
        anomaly_scores = np.asarray(bundle.anomaly.score_samples(X), dtype=float)

    rank_norm_all = normalize_rank_scores(rank_raw.tolist())

    rows: list[dict] = []
    for i in keep_idx:
        ide = id_list[i]
        prob = float(signal_prob[i])
        if prob < cfg.p_min:
            continue
        stats["after_signal"] += 1

        decision = int(anomaly_pred[i])
        a_score = float(anomaly_scores[i]) if anomaly_scores is not None else None
        a_risk = anomaly_norm(decision, a_score)
        is_anomaly = decision < 0
        if cfg.drop_anomaly and is_anomaly:
            continue
        stats["after_anomaly"] += 1

        channel = _channel_for_ide(kdb, ide, cfg, feature_cfg)
        ch_score = int(channel.get("score") or 0)
        t_score = trend_score(ch_score, cfg.min_channel_score)
        if cfg.require_channel and not channel.get("is_match"):
            continue
        stats["after_channel"] += 1

        non_null = int(feats.loc[ide].notna().sum())
        risk_gate = 0.0 if non_null < 5 else 1.0
        score = composite_score(
            rank_score=rank_norm_all[i],
            signal_prob=prob,
            trend=t_score,
            anomaly_risk=a_risk,
            risk_gate=risk_gate,
            cfg=cfg,
        )
        if score <= 0:
            continue

        info = kdb.StockInfo(ide) or {}
        reasons = [
            f"Ranker分位 {rank_norm_all[i]:.2f}",
            f"买入概率 {prob:.2f}",
        ]
        if channel.get("is_match"):
            reasons.append(f"上升通道 {channel.get('score_text')}")
        else:
            reasons.append(f"通道评分 {channel.get('score_text') or '—'}")
        if is_anomaly:
            reasons.append("异常标记")
        if bundle.signal_xgb is not None and np.isfinite(xgb_prob[i]):
            reasons.append(f"XGB对照 {float(xgb_prob[i]):.2f}")

        rows.append(
            {
                "ide": ide,
                "name": info.get("IDS") or ide,
                "score": score,
                "rank_score": round(rank_norm_all[i], 4),
                "rank_raw": round(float(rank_raw[i]), 6),
                "signal_prob": round(prob, 4),
                "xgb_prob": None if not np.isfinite(xgb_prob[i]) else round(float(xgb_prob[i]), 4),
                "trend_score": round(t_score, 4),
                "channel_score": ch_score,
                "channel_score_text": channel.get("score_text"),
                "channel_match": bool(channel.get("is_match")),
                "is_anomaly": is_anomaly,
                "anomaly_risk": round(a_risk, 4),
                "reasons": reasons,
                "features": {
                    col: None if pd.isna(feats.loc[ide, col]) else float(feats.loc[ide, col])
                    for col in FEATURE_COLUMNS
                    if col in feats.columns
                },
            }
        )

    rows.sort(key=lambda row: (-row["score"], -row["signal_prob"], row["ide"]))
    rows = rows[: max(1, int(cfg.limit))]
    stats["returned"] = len(rows)
    return (rows, stats) if return_stats else rows
