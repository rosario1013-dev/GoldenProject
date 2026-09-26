"""Composite score and risk gates."""

from __future__ import annotations

from ..config import DEFAULT_ADVICE_CONFIG, AdviceConfig


def trend_score(channel_score: int | None, min_score: int) -> float:
    if channel_score is None:
        return 0.0
    return max(0.0, min(1.0, float(channel_score) / max(1, min_score)))


def normalize_rank_scores(raw_scores: list[float]) -> list[float]:
    if not raw_scores:
        return []
    lo = min(raw_scores)
    hi = max(raw_scores)
    if hi <= lo:
        return [0.5 for _ in raw_scores]
    return [(value - lo) / (hi - lo) for value in raw_scores]


def anomaly_norm(decision: int, score: float | None) -> float:
    """Map IsolationForest decision (-1 anomaly) into [0,1] riskiness."""
    if decision < 0:
        return 1.0
    # Inliers: keep a small residual risk; score_samples scale varies by sklearn version.
    if score is None:
        return 0.1
    # Higher score_samples => more normal => lower risk.
    risk = max(0.0, min(0.4, 0.15 - 0.2 * float(score)))
    return float(risk)


def composite_score(
    *,
    rank_score: float,
    signal_prob: float,
    trend: float,
    anomaly_risk: float,
    risk_gate: float = 1.0,
    cfg: AdviceConfig = DEFAULT_ADVICE_CONFIG,
) -> float:
    raw = (
        cfg.rank_weight * rank_score
        + cfg.signal_weight * signal_prob
        + cfg.trend_weight * trend
        + cfg.anomaly_weight * (1.0 - anomaly_risk)
    )
    return round(float(raw) * float(risk_gate), 4)
