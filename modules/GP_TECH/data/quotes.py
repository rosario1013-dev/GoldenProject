"""Load OHLC data from GP_KDB for technical analysis."""

from __future__ import annotations

import pandas as pd

from GP_KDB import KDB

STANDARD_COLUMNS = ["date", "open", "close", "high", "low", "volume"]


def _recent_raw_quotes(
    kdb: KDB,
    ide: str,
    days: int,
    *,
    require_amount: bool = True,
) -> pd.DataFrame:
    """Read the latest raw daily bars without depending on KDB.EDTs."""
    days = max(1, int(days))
    match: dict = {"IDE": ide}
    if require_amount:
        # Indices sometimes store A=0; callers can disable this filter.
        match["A"] = {"$gt": 0}
    docs = list(
        kdb.col_TDX_QUATE.find(
            match,
            {"_id": 0, "DT": 1, "O": 1, "C": 1, "H": 1, "L": 1, "V": 1},
        )
        .sort([("DT", -1)])
        .limit(days)
    )
    if not docs:
        return pd.DataFrame(columns=["DT", "O", "C", "H", "L", "V"])
    return pd.DataFrame(docs).sort_values("DT").reset_index(drop=True)


def _adjustment_factors(kdb: KDB, ide: str) -> pd.DataFrame:
    """Read cumulative share-change factors (PKV) for one stock."""
    docs = list(
        kdb.col_STOCK_PKVZGB.find(
            {"IDE": ide},
            {"_id": 0, "DT": 1, "PKV": 1},
        ).sort([("DT", 1)])
    )
    if not docs:
        return pd.DataFrame(columns=["DT", "PKV"])
    factors = pd.DataFrame(docs)
    factors["PKV"] = pd.to_numeric(factors["PKV"], errors="coerce")
    return factors.dropna(subset=["DT", "PKV"]).sort_values("DT")


def _attach_pkv(raw: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    """Merge PKV onto raw OHLC rows (one PKV per bar, as-of that date)."""
    out = raw.copy()
    if factors.empty:
        out["PKV"] = 1.0
        return out

    factors = factors.copy()
    factors["DT"] = pd.to_datetime(factors["DT"])
    out = pd.merge_asof(
        out.sort_values("DT"),
        factors.sort_values("DT"),
        on="DT",
        direction="backward",
    )
    out["PKV"] = out["PKV"].ffill().fillna(1.0)
    return out


def _to_standard_ohlc(raw: pd.DataFrame, adjustment: str) -> pd.DataFrame:
    result = (
        raw.rename(
            columns={
                "DT": "date",
                "O": "open",
                "C": "close",
                "H": "high",
                "L": "low",
                "V": "volume",
            }
        )[STANDARD_COLUMNS]
        .copy()
        .reset_index(drop=True)
    )
    result["date"] = pd.to_datetime(result["date"])
    result.attrs["adjustment"] = adjustment
    return result


def load_raw_ohlc(
    kdb: KDB,
    ide: str,
    days: int = 400,
    *,
    require_amount: bool = True,
) -> pd.DataFrame:
    """Return unadjusted daily OHLC (不复权, yuan prices from TDX)."""
    raw = _recent_raw_quotes(kdb, ide, days, require_amount=require_amount)
    if raw.empty:
        result = pd.DataFrame(columns=STANDARD_COLUMNS)
        result.attrs["adjustment"] = "none"
        return result

    for col in ("O", "C", "H", "L", "V"):
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    raw = raw.dropna(subset=["DT", "O", "C", "H", "L", "V"]).sort_values("DT")
    raw["DT"] = pd.to_datetime(raw["DT"])
    return _to_standard_ohlc(raw, "none")


def load_forward_ohlc(
    kdb: KDB,
    ide: str,
    days: int = 400,
    *,
    require_amount: bool = True,
) -> pd.DataFrame:
    """Return arithmetic forward-adjusted daily OHLC in yuan.

    Formula: ``raw_price * PKV(date) / PKV(latest)``. Latest bar equals the
    unadjusted market price. Used by channel / AI feature pipelines.

    This is **not** the chart Y-axis scale. The frontend K-line uses
    ``load_fdk_ohlc`` / ``KDB.FDK_STOCK``: ``logfcn(raw * PKV)``.
    """
    raw = _recent_raw_quotes(kdb, ide, days, require_amount=require_amount)
    if raw.empty:
        result = pd.DataFrame(columns=STANDARD_COLUMNS)
        result.attrs["adjustment"] = "none"
        return result

    for col in ("O", "C", "H", "L", "V"):
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    raw = raw.dropna(subset=["DT", "O", "C", "H", "L", "V"]).sort_values("DT")
    raw["DT"] = pd.to_datetime(raw["DT"])

    factors = _adjustment_factors(kdb, ide)
    if factors.empty:
        return _to_standard_ohlc(raw, "none")

    raw = _attach_pkv(raw, factors)
    pkv_latest = float(raw["PKV"].iloc[-1])
    if pkv_latest <= 0:
        pkv_latest = 1.0
    factor = raw["PKV"] / pkv_latest
    for col in ("O", "C", "H", "L"):
        raw[col] = raw[col] * factor

    return _to_standard_ohlc(raw, "forward")


def load_fdk_ohlc(
    kdb: KDB,
    ide: str,
    days: int = 400,
) -> pd.DataFrame:
    """Return the same adjusted OHLC scale as the project K-line chart.

    Uses ``KDB.FDK_STOCK``: ``logfcn(raw_price * PKV)`` (log-1.01 space).
    Latest Moutai close is ~885, matching ``/api/stock/<ide>/fdk/``.
    """
    days = max(1, int(days))
    fdk = kdb.FDK_STOCK(ide)
    if fdk is None or fdk.empty:
        result = pd.DataFrame(columns=STANDARD_COLUMNS)
        result.attrs["adjustment"] = "fdk"
        return result

    out = fdk.copy()
    for col in ("O", "C", "H", "L", "V"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["DT", "O", "C", "H", "L"]).sort_values("DT")
    if "V" not in out.columns:
        out["V"] = 0.0
    out = out.tail(days).reset_index(drop=True)
    return _to_standard_ohlc(out, "fdk")
