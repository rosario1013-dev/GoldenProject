"""API helpers for industry profit growth analysis."""

from __future__ import annotations

from typing import Any

from GP_KDB import KDB
from GP_KDB.industry_profit.aggregate import (
    available_years,
    load_yearly_rows,
    rows_for_metrics,
)
from GP_KDB.industry_profit.metrics import (
    build_industry_metrics,
    rank_industries,
    safe_float,
    sort_key_for_period,
)

from . import heatmap_cache

CACHE_TTL_SECONDS = 600
CACHE_PREFIX = "industry_profit_growth:"


def _ensure_kdb() -> KDB:
    kdb = KDB()
    if not kdb.is_configured:
        from django.conf import settings

        kdb.setting(uri=getattr(settings, "GP_TDX_MONGO_URI", None))
    return kdb


def _normalize_level(level: str | None) -> str:
    raw = str(level or "1").strip().upper().replace("HY", "")
    if raw not in {"1", "2", "3"}:
        return "1"
    return raw


def _normalize_period(period: str | None) -> str:
    key = str(period or "yoy").strip().lower()
    mapping = {
        "yoy": "yoy",
        "1y": "yoy",
        "3y": "3y",
        "cagr_3y": "3y",
        "3y_cagr": "3y",
        "5y": "5y",
        "cagr_5y": "5y",
        "5y_cagr": "5y",
    }
    return mapping.get(key, "yoy")


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "industry": row.get("industry"),
        "ide": row.get("ide") or "",
        "code": row.get("code") or "",
        "level": row.get("level") or "",
        "company_count": int(row.get("company_count") or 0),
        "low_sample_size": bool(row.get("low_sample_size")),
        "current_profit": safe_float(row.get("current_profit")),
        "previous_profit": safe_float(row.get("previous_profit")),
        "profit_growth_yoy": safe_float(row.get("profit_growth_yoy")),
        "profit_cagr_3y": safe_float(row.get("profit_cagr_3y")),
        "profit_cagr_5y": safe_float(row.get("profit_cagr_5y")),
        "added_profit": safe_float(row.get("added_profit")),
        "profit_contribution": safe_float(row.get("profit_contribution")),
        "growth_stability_score": safe_float(row.get("growth_stability_score")),
        "growth_score": safe_float(row.get("growth_score")),
        "growth_confidence": safe_float(row.get("growth_confidence")),
        "profit_status": row.get("profit_status"),
        "valuation_score": safe_float(row.get("valuation_score")),
        "yoy_percentile": safe_float(row.get("yoy_percentile")),
        "cagr_3y_percentile": safe_float(row.get("cagr_3y_percentile")),
        "cagr_5y_percentile": safe_float(row.get("cagr_5y_percentile")),
        "contribution_percentile": safe_float(row.get("contribution_percentile")),
        "yearly_series": row.get("yearly_series") or [],
    }


def get_profit_growth(
    *,
    year: int | None = None,
    period: str = "yoy",
    level: str = "1",
    industry: str | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Build full profit-growth payload for the dashboard API."""
    period_key = _normalize_period(period)
    level_key = _normalize_level(level)
    industry_key = (industry or "").strip() or None

    kdb = _ensure_kdb()
    years = available_years(kdb)
    # Prefer pre-aggregated collection years if present
    agg_years = sorted(
        {
            int(doc["year"])
            for doc in kdb.col_TDX_INDUSTRY_PROFIT_YEARLY.find(
                {"level": level_key},
                {"_id": 0, "year": 1},
            )
            if doc.get("year") is not None
        }
    )
    year_options = agg_years or years
    if not year_options:
        return {
            "error": "暂无行业利润预聚合数据，请先在数据中心执行「行业利润预聚合」。",
            "year": year,
            "period": period_key,
            "level": level_key,
            "years": [],
            "industries": [],
        }

    selected_year = int(year) if year else year_options[-1]
    if selected_year not in year_options:
        selected_year = year_options[-1]

    cache_key = (
        f"{CACHE_PREFIX}{selected_year}:{period_key}:{level_key}:{industry_key or 'ALL'}"
    )
    if use_cache:
        cached = heatmap_cache.get_cached(cache_key, ttl_seconds=CACHE_TTL_SECONDS)
        if cached is not None:
            return cached

    yearly_rows = load_yearly_rows(kdb, level=level_key, industry=industry_key)
    if not yearly_rows:
        # Fallback: maybe collection empty for this level
        return {
            "error": "暂无行业利润预聚合数据，请先在数据中心执行「行业利润预聚合」。",
            "year": selected_year,
            "period": period_key,
            "level": level_key,
            "years": year_options,
            "industries": [],
        }

    metric_inputs = rows_for_metrics(yearly_rows, year=selected_year)
    enriched = build_industry_metrics(metric_inputs, year=selected_year, period=period_key)
    public_rows = [_public_row(r) for r in enriched]

    # Default sort for table: growth_score DESC
    def score_key(row: dict[str, Any]) -> tuple[int, float]:
        value = safe_float(row.get("growth_score"))
        if value is None:
            return (1, 0.0)
        return (0, -value)

    public_rows.sort(key=score_key)

    top10 = rank_industries(public_rows, period=period_key, limit=10)
    # Attach ranks
    for idx, row in enumerate(top10, start=1):
        row["rank"] = idx

    ranked_for_table = list(public_rows)
    for idx, row in enumerate(ranked_for_table, start=1):
        row["rank"] = idx

    positive_added = 0.0
    net_change = 0.0
    if enriched:
        positive_added = float(enriched[0].get("_market_positive_added") or 0)
        net_change = float(enriched[0].get("_net_market_profit_change") or 0)

    sort_field = sort_key_for_period(period_key)
    payload = {
        "year": selected_year,
        "period": period_key,
        "level": level_key,
        "market": "CN",
        "industry": industry_key,
        "years": year_options,
        "sort_field": sort_field,
        "net_market_profit_change": net_change,
        "market_positive_added_profit": positive_added,
        "industry_count": len(public_rows),
        "top10": top10,
        "industries": ranked_for_table,
    }

    if use_cache:
        heatmap_cache.set_cached(cache_key, payload)
    return payload
