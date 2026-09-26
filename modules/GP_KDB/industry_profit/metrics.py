"""Pure functions for industry profit growth analysis.

All growth / score helpers are side-effect free and safe against
NULL / NaN / Inf / non-positive base profits.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Iterable, Sequence

CAGR_PERIOD_3 = 3
CAGR_PERIOD_5 = 5
MIN_COMPANY_COUNT_CONFIDENT = 5

STATUS_PROFITABLE = "PROFITABLE"
STATUS_BASE_PROFIT_NON_POSITIVE = "BASE_PROFIT_NON_POSITIVE"
STATUS_TURNED_PROFITABLE = "TURNED_PROFITABLE"
STATUS_PROFIT_TO_LOSS = "PROFIT_TO_LOSS"
STATUS_LOSS_TO_LOSS = "LOSS_TO_LOSS"


def safe_float(value: Any) -> float | None:
    """Coerce to finite float; return None for missing / non-finite."""
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(num) or math.isinf(num):
        return None
    return num


def industry_profit_sum(company_profits: Iterable[Any]) -> float | None:
    """Sum company profits; ignore null/non-finite; return None if empty."""
    total = 0.0
    count = 0
    for raw in company_profits:
        num = safe_float(raw)
        if num is None:
            continue
        total += num
        count += 1
    if count == 0:
        return None
    return total


def calc_yoy_growth(
    current_profit: Any,
    previous_profit: Any,
) -> tuple[float | None, str]:
    """YoY growth as percent points (e.g. 20.0 for +20%).

    Returns (growth_pct_or_None, status).
    """
    current = safe_float(current_profit)
    previous = safe_float(previous_profit)

    if current is None or previous is None:
        return None, STATUS_BASE_PROFIT_NON_POSITIVE

    if previous < 0 and current > 0:
        return None, STATUS_TURNED_PROFITABLE
    if previous > 0 and current < 0:
        return None, STATUS_PROFIT_TO_LOSS
    if previous < 0 and current < 0:
        return None, STATUS_LOSS_TO_LOSS
    if previous <= 0:
        return None, STATUS_BASE_PROFIT_NON_POSITIVE

    growth = (current / previous - 1.0) * 100.0
    if math.isnan(growth) or math.isinf(growth):
        return None, STATUS_BASE_PROFIT_NON_POSITIVE
    return growth, STATUS_PROFITABLE


def calc_cagr(
    current_profit: Any,
    past_profit: Any,
    *,
    period: int,
) -> float | None:
    """CAGR as percent points for a given period length."""
    if period <= 0:
        raise ValueError("period must be positive")
    current = safe_float(current_profit)
    past = safe_float(past_profit)
    if current is None or past is None:
        return None
    if past <= 0 or current <= 0:
        return None
    try:
        ratio = current / past
        if ratio <= 0:
            return None
        cagr = (ratio ** (1.0 / period) - 1.0) * 100.0
    except (OverflowError, ZeroDivisionError, ValueError):
        return None
    if math.isnan(cagr) or math.isinf(cagr):
        return None
    return cagr


def added_profit(current_profit: Any, previous_profit: Any) -> float | None:
    current = safe_float(current_profit)
    previous = safe_float(previous_profit)
    if current is None or previous is None:
        return None
    return current - previous


def contribution_shares(
    added_profits: Sequence[float | None],
) -> tuple[list[float | None], float, float]:
    """Contribution % using positive added profits as denominator.

    Returns (shares_pct, positive_sum, net_market_change).
    Negative added -> 0% contribution (not None when value known).
    """
    cleaned: list[float | None] = [safe_float(v) for v in added_profits]
    positive_sum = sum(v for v in cleaned if v is not None and v > 0)
    net = sum(v for v in cleaned if v is not None)

    shares: list[float | None] = []
    for value in cleaned:
        if value is None:
            shares.append(None)
        elif value <= 0 or positive_sum <= 0:
            shares.append(0.0)
        else:
            shares.append((value / positive_sum) * 100.0)
    return shares, positive_sum, net


def percentile_ranks(values: Sequence[float | None]) -> list[float | None]:
    """Percentile rank 0–100 among finite values (average rank for ties)."""
    indexed = [(i, v) for i, v in enumerate(values) if safe_float(v) is not None]
    n = len(values)
    out: list[float | None] = [None] * n
    if not indexed:
        return out
    if len(indexed) == 1:
        out[indexed[0][0]] = 50.0
        return out

    indexed.sort(key=lambda pair: pair[1])  # type: ignore[arg-type]
    m = len(indexed)
    i = 0
    while i < m:
        j = i
        while j + 1 < m and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j) / 2.0
        pct = (avg_rank / (m - 1)) * 100.0
        for k in range(i, j + 1):
            out[indexed[k][0]] = pct
        i = j + 1
    return out


def calc_growth_stability(
    growth_rates: Sequence[float | None],
    *,
    max_years: int = 5,
) -> float | None:
    """Stability score 0–100 from positive-growth ratio and volatility."""
    valid = [safe_float(g) for g in growth_rates]
    valid = [g for g in valid if g is not None][-max_years:]
    if not valid:
        return None

    positive_ratio = sum(1 for g in valid if g > 0) / len(valid)
    if len(valid) == 1:
        vol_score = 70.0
    else:
        std = statistics.pstdev(valid)
        # Soft cap: 0 std -> 100, 80+ pct-point std -> ~0
        vol_score = max(0.0, 100.0 - min(std, 100.0) * 1.25)

    score = positive_ratio * 60.0 + (vol_score / 100.0) * 40.0
    return max(0.0, min(100.0, score))


def calc_growth_confidence(
    *,
    company_count: int,
    years_available: int,
    years_expected: int = 5,
    loss_company_ratio: float | None = None,
    extreme_change: bool = False,
) -> float:
    """Confidence 0–100 from sample size, history coverage, loss share."""
    count = max(0, int(company_count))
    if count <= 0:
        return 0.0

    # Sample size: 1 firm ~35, 5 ~60, 20+ ~90, 50+ ~95
    if count < MIN_COMPANY_COUNT_CONFIDENT:
        sample_score = 25.0 + count * 7.0
    elif count < 20:
        sample_score = 60.0 + (count - 5) * 2.0
    elif count < 50:
        sample_score = 90.0 + (count - 20) * 0.15
    else:
        sample_score = 95.0

    expected = max(1, int(years_expected))
    coverage = max(0, min(int(years_available), expected)) / expected
    coverage_score = coverage * 100.0

    loss_ratio = safe_float(loss_company_ratio)
    if loss_ratio is None:
        loss_penalty = 0.0
    else:
        loss_penalty = max(0.0, min(1.0, loss_ratio)) * 25.0

    extreme_penalty = 15.0 if extreme_change else 0.0

    score = sample_score * 0.55 + coverage_score * 0.35 + 10.0
    score -= loss_penalty + extreme_penalty
    if count < MIN_COMPANY_COUNT_CONFIDENT:
        score = min(score, 55.0)
    return max(0.0, min(100.0, score))


def calc_growth_score(
    *,
    yoy_percentile: float | None,
    cagr_3y_percentile: float | None,
    contribution_percentile: float | None,
    stability_score: float | None,
    period: str = "yoy",
) -> float | None:
    """Composite growth score 0–100 with period-aware weights."""
    yoy = safe_float(yoy_percentile)
    cagr3 = safe_float(cagr_3y_percentile)
    contrib = safe_float(contribution_percentile)
    stab = safe_float(stability_score)

    period_key = (period or "yoy").lower()
    if period_key in {"3y", "cagr_3y", "3y_cagr"}:
        weights = {"primary": 0.50, "secondary": 0.20, "contrib": 0.20, "stab": 0.10}
        primary, secondary = cagr3, yoy
    elif period_key in {"5y", "cagr_5y", "5y_cagr"}:
        # 5Y CAGR percentile should be passed as yoy_percentile slot via caller remap,
        # or as cagr_3y_percentile — support both via primary=cagr3 first then yoy.
        weights = {"primary": 0.50, "secondary": 0.20, "contrib": 0.20, "stab": 0.10}
        primary, secondary = cagr3 if cagr3 is not None else yoy, yoy
    else:
        weights = {"primary": 0.40, "secondary": 0.30, "contrib": 0.20, "stab": 0.10}
        primary, secondary = yoy, cagr3

    parts: list[tuple[float, float]] = []
    if primary is not None:
        parts.append((primary, weights["primary"]))
    if secondary is not None:
        parts.append((secondary, weights["secondary"]))
    if contrib is not None:
        parts.append((contrib, weights["contrib"]))
    if stab is not None:
        parts.append((stab, weights["stab"]))

    if not parts:
        return None

    total_w = sum(w for _, w in parts)
    if total_w <= 0:
        return None
    score = sum(v * w for v, w in parts) / total_w
    return max(0.0, min(100.0, score))


def _is_extreme_change(current: float | None, previous: float | None) -> bool:
    if current is None or previous is None or previous == 0:
        return False
    if previous > 0 and current > 0:
        return abs(current / previous - 1.0) > 3.0
    return abs(current - previous) > abs(previous) * 3


def build_industry_metrics(
    industries: Sequence[dict[str, Any]],
    *,
    year: int,
    period: str = "yoy",
    cagr_period_3: int = CAGR_PERIOD_3,
    cagr_period_5: int = CAGR_PERIOD_5,
) -> list[dict[str, Any]]:
    """Enrich industry yearly profit rows with growth metrics and scores.

    Each input dict should provide at least:
      industry, company_count, current_profit, previous_profit,
      profit_3y_ago, profit_5y_ago, yearly_profits (dict year->profit),
      loss_company_ratio (optional), yearly_series (optional list)
    """
    rows: list[dict[str, Any]] = []
    added_list: list[float | None] = []

    for raw in industries:
        industry = raw.get("industry") or raw.get("name") or ""
        current = safe_float(raw.get("current_profit"))
        previous = safe_float(raw.get("previous_profit"))
        past_3 = safe_float(raw.get("profit_3y_ago"))
        past_5 = safe_float(raw.get("profit_5y_ago"))
        company_count = int(raw.get("company_count") or 0)

        growth, status = calc_yoy_growth(current, previous)
        cagr_3 = calc_cagr(current, past_3, period=cagr_period_3)
        cagr_5 = calc_cagr(current, past_5, period=cagr_period_5)
        added = added_profit(current, previous)
        added_list.append(added)

        yearly_profits = raw.get("yearly_profits") or {}
        history_growth: list[float | None] = []
        years_sorted = sorted(int(y) for y in yearly_profits.keys())
        for y in years_sorted:
            if y > year:
                continue
            g, _ = calc_yoy_growth(yearly_profits.get(y), yearly_profits.get(y - 1))
            history_growth.append(g)

        stability = calc_growth_stability(history_growth)
        years_available = sum(
            1 for y in range(year - 4, year + 1) if safe_float(yearly_profits.get(y)) is not None
        )
        confidence = calc_growth_confidence(
            company_count=company_count,
            years_available=years_available,
            years_expected=5,
            loss_company_ratio=raw.get("loss_company_ratio"),
            extreme_change=_is_extreme_change(current, previous),
        )

        rows.append(
            {
                "industry": industry,
                "ide": raw.get("ide") or "",
                "code": raw.get("code") or "",
                "level": raw.get("level") or "",
                "company_count": company_count,
                "low_sample_size": company_count < MIN_COMPANY_COUNT_CONFIDENT,
                "current_profit": current,
                "previous_profit": previous,
                "profit_growth_yoy": growth,
                "profit_cagr_3y": cagr_3,
                "profit_cagr_5y": cagr_5,
                "added_profit": added,
                "profit_contribution": None,  # filled below
                "growth_stability_score": stability,
                "growth_score": None,
                "growth_confidence": confidence,
                "profit_status": status,
                "valuation_score": safe_float(raw.get("valuation_score")),
                "yearly_series": raw.get("yearly_series")
                or [
                    {"year": y, "net_income": safe_float(yearly_profits.get(y))}
                    for y in range(year - 4, year + 1)
                ],
            }
        )

    shares, positive_sum, net_change = contribution_shares(added_list)
    for row, share in zip(rows, shares):
        row["profit_contribution"] = share

    yoy_pct = percentile_ranks([r["profit_growth_yoy"] for r in rows])
    cagr3_pct = percentile_ranks([r["profit_cagr_3y"] for r in rows])
    cagr5_pct = percentile_ranks([r["profit_cagr_5y"] for r in rows])
    contrib_pct = percentile_ranks([r["profit_contribution"] for r in rows])

    period_key = (period or "yoy").lower()
    for i, row in enumerate(rows):
        if period_key in {"5y", "cagr_5y", "5y_cagr"}:
            primary_pct = cagr5_pct[i]
            secondary_pct = cagr3_pct[i]
        elif period_key in {"3y", "cagr_3y", "3y_cagr"}:
            primary_pct = cagr3_pct[i]
            secondary_pct = yoy_pct[i]
        else:
            primary_pct = yoy_pct[i]
            secondary_pct = cagr3_pct[i]

        row["yoy_percentile"] = yoy_pct[i]
        row["cagr_3y_percentile"] = cagr3_pct[i]
        row["cagr_5y_percentile"] = cagr5_pct[i]
        row["contribution_percentile"] = contrib_pct[i]
        row["growth_score"] = calc_growth_score(
            yoy_percentile=primary_pct if period_key.startswith(("3", "5")) else yoy_pct[i],
            cagr_3y_percentile=secondary_pct if period_key.startswith("5") else (
                primary_pct if period_key.startswith("3") else cagr3_pct[i]
            ),
            contribution_percentile=contrib_pct[i],
            stability_score=row["growth_stability_score"],
            period=period_key,
        )
        # For 5Y: put 5Y percentile into the primary weight via calc_growth_score remap
        if period_key in {"5y", "cagr_5y", "5y_cagr"}:
            row["growth_score"] = calc_growth_score(
                yoy_percentile=cagr5_pct[i],
                cagr_3y_percentile=cagr3_pct[i],
                contribution_percentile=contrib_pct[i],
                stability_score=row["growth_stability_score"],
                period="5y",
            )

    # Attach market summary on each call site via return metadata — keep rows clean;
    # callers can read positive_sum / net_change from build_market_summary.
    for row in rows:
        row["_market_positive_added"] = positive_sum
        row["_net_market_profit_change"] = net_change

    return rows


def sort_key_for_period(period: str) -> str:
    key = (period or "yoy").lower()
    if key in {"3y", "cagr_3y", "3y_cagr"}:
        return "profit_cagr_3y"
    if key in {"5y", "cagr_5y", "5y_cagr"}:
        return "profit_cagr_5y"
    return "profit_growth_yoy"


def rank_industries(
    rows: Sequence[dict[str, Any]],
    *,
    period: str = "yoy",
    limit: int | None = 10,
) -> list[dict[str, Any]]:
    """Rank by selected growth metric DESC; nulls last."""
    field = sort_key_for_period(period)

    def key_fn(row: dict[str, Any]) -> tuple[int, float]:
        value = safe_float(row.get(field))
        if value is None:
            return (1, 0.0)
        return (0, -value)

    ordered = sorted(rows, key=key_fn)
    if limit is None:
        return list(ordered)
    return ordered[: max(0, int(limit))]
