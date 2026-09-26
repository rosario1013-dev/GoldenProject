"""Resample forward-adjusted FDK OHLCV to weekly / monthly / quarterly / yearly bars."""

from __future__ import annotations

import pandas as pd

PERIOD_ALIASES = {
    "daily": "daily",
    "d": "daily",
    "day": "daily",
    "weekly": "weekly",
    "w": "weekly",
    "week": "weekly",
    "monthly": "monthly",
    "m": "monthly",
    "month": "monthly",
    "quarterly": "quarterly",
    "q": "quarterly",
    "quarter": "quarterly",
    "yearly": "yearly",
    "y": "yearly",
    "year": "yearly",
}

# Pandas offset aliases: bar time = last calendar bucket end (Fri / month-end / quarter-end / year-end).
PERIOD_RULES = {
    "weekly": "W-FRI",
    "monthly": "ME",
    "quarterly": "QE-DEC",
    "yearly": "YE-DEC",
}

OHLCV_COLUMNS = ("O", "H", "L", "C", "V")

ADJUSTMENT_ALIASES = {
    "forward": "forward",
    "fq": "forward",
    "adjusted": "forward",
    "fdk": "forward",
    "none": "none",
    "raw": "none",
    "dk": "none",
    "unadjusted": "none",
}


def normalize_adjustment(adjustment: str) -> str:
    key = (adjustment or "forward").strip().lower()
    normalized = ADJUSTMENT_ALIASES.get(key)
    if normalized is None:
        allowed = ", ".join(sorted({k for k in ADJUSTMENT_ALIASES if k == ADJUSTMENT_ALIASES[k]}))
        raise ValueError(f"Unknown adjustment: {adjustment}. Allowed: {allowed}")
    return normalized


def normalize_period(period: str) -> str:
    key = (period or "daily").strip().lower()
    normalized = PERIOD_ALIASES.get(key)
    if normalized is None:
        allowed = ", ".join(sorted({k for k in PERIOD_ALIASES if k == PERIOD_ALIASES[k]}))
        raise ValueError(f"Unknown period: {period}. Allowed: {allowed}")
    return normalized


def resample_fdk_ohlc(df: pd.DataFrame, period: str, extra_agg: dict | None = None) -> pd.DataFrame:
    """
    Aggregate daily OHLCV rows (FDK forward-adjusted or raw DK).

    Rules (standard OHLCV):
    - Open: first open in bucket
    - High: max high in bucket
    - Low: min low in bucket
    - Close: last close in bucket
    - Volume: sum volume in bucket

    ``extra_agg`` maps extra column names to pandas agg funcs, e.g.
    ``{"A": "sum", "ZGB": "last"}``.

    ``DT`` label uses the last trading day that falls in each bucket.
    """
    normalized = normalize_period(period)
    if normalized == "daily":
        return df.copy()

    if df is None or df.empty:
        base_cols = ["DT", *OHLCV_COLUMNS]
        if extra_agg:
            base_cols.extend(extra_agg.keys())
        return pd.DataFrame(columns=base_cols)

    extra_agg = extra_agg or {}
    use_cols = ["DT", *OHLCV_COLUMNS, *extra_agg.keys()]
    missing = [col for col in use_cols if col not in df.columns]
    if missing:
        raise ValueError(f"OHLC dataframe missing columns: {missing}")

    work = df[use_cols].copy()
    work["DT"] = pd.to_datetime(work["DT"])
    work = work.dropna(subset=["DT"]).sort_values("DT").set_index("DT")

    agg = {
        "O": "first",
        "H": "max",
        "L": "min",
        "C": "last",
        "V": "sum",
        **extra_agg,
    }
    grouped = work.resample(PERIOD_RULES[normalized]).agg(agg)
    grouped = grouped.dropna(subset=["O", "C"], how="any")

    result = grouped.reset_index()
    result["DT"] = result["DT"].dt.strftime("%Y-%m-%d")
    return result
