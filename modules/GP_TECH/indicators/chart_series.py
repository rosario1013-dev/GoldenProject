"""Build chart-ready indicator series from KDB OHLC (same scale as FDK chart)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from GP_KDB import KDB
from GP_KDB.ohlc_resample import normalize_adjustment, normalize_period

from .calc import add_technical_indicators

INDICATOR_KINDS = ("macd", "rsi", "kdj", "boll", "obv")

_KIND_COLUMNS: dict[str, list[str]] = {
    "macd": ["macd_dif", "macd_dea", "macd"],
    "rsi": ["rsi_6", "rsi_12", "rsi_24"],
    "kdj": ["kdj_k", "kdj_d", "kdj_j"],
    "boll": ["boll_mid", "boll_upper", "boll_lower"],
    "obv": ["obv"],
}


def _to_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "DT": "date",
        "O": "open",
        "H": "high",
        "L": "low",
        "C": "close",
        "V": "volume",
    }
    cols = [c for c in rename if c in df.columns]
    out = df[cols].rename(columns=rename).copy()
    if "volume" not in out.columns:
        out["volume"] = 0.0
    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["date", "open", "high", "low", "close"]).reset_index(drop=True)
    return out


def _points(times: pd.Series, values: pd.Series) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for dt, value in zip(times, values, strict=False):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            continue
        try:
            num = float(value)
        except (TypeError, ValueError):
            continue
        if not pd.notna(num):
            continue
        result.append({"time": str(dt)[:10], "value": num})
    return result


def parse_indicator_kinds(raw: str | None) -> tuple[str, ...]:
    if not raw or not str(raw).strip():
        return ("macd", "rsi", "kdj", "boll")
    kinds = []
    for part in str(raw).split(","):
        key = part.strip().lower()
        if key in INDICATOR_KINDS and key not in kinds:
            kinds.append(key)
    return tuple(kinds) if kinds else ("macd", "rsi", "kdj", "boll")


def compute_indicator_frame(
    ohlcv: pd.DataFrame,
    kinds: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Compute selected indicators on an OHLCV frame."""
    include = kinds if kinds is not None else INDICATOR_KINDS
    return add_technical_indicators(ohlcv, include=include)


def indicators_payload_from_ohlcv(
    ohlcv: pd.DataFrame,
    *,
    kinds: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Return API-shaped series dict from OHLCV (columns date/open/high/low/close/volume)."""
    wanted = kinds if kinds is not None else ("macd", "rsi", "kdj", "boll")
    frame = compute_indicator_frame(ohlcv, wanted)
    times = frame["date"]
    series: dict[str, Any] = {}

    if "macd" in wanted:
        series["macd"] = {
            "dif": _points(times, frame["macd_dif"]),
            "dea": _points(times, frame["macd_dea"]),
            "hist": _points(times, frame["macd"]),
        }
    if "rsi" in wanted:
        series["rsi"] = {
            "rsi_6": _points(times, frame["rsi_6"]),
            "rsi_12": _points(times, frame["rsi_12"]),
            "rsi_24": _points(times, frame["rsi_24"]),
        }
    if "kdj" in wanted:
        series["kdj"] = {
            "k": _points(times, frame["kdj_k"]),
            "d": _points(times, frame["kdj_d"]),
            "j": _points(times, frame["kdj_j"]),
        }
    if "boll" in wanted:
        series["boll"] = {
            "mid": _points(times, frame["boll_mid"]),
            "upper": _points(times, frame["boll_upper"]),
            "lower": _points(times, frame["boll_lower"]),
        }
    if "obv" in wanted:
        series["obv"] = {"obv": _points(times, frame["obv"])}

    return {
        "kinds": list(wanted),
        "series": series,
        "count": len(frame),
    }


def stock_indicators(
    kdb: KDB,
    ide: str,
    *,
    period: str = "daily",
    adjustment: str = "forward",
    kinds: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Compute indicators on the same OHLC bars used by the FDK chart API."""
    period = normalize_period(period)
    adjustment = normalize_adjustment(adjustment)
    df = kdb.STOCK_OHLC_PERIOD(ide, period, adjustment=adjustment)
    if df is None or df.empty:
        return {
            "ide": ide,
            "period": period,
            "adjustment": adjustment,
            "kinds": list(kinds or ()),
            "series": {},
            "count": 0,
        }

    ohlcv = _to_ohlcv(df)
    payload = indicators_payload_from_ohlcv(ohlcv, kinds=kinds)
    payload.update(
        {
            "ide": ide,
            "period": period,
            "adjustment": adjustment,
        }
    )
    return payload


__all__ = [
    "INDICATOR_KINDS",
    "_KIND_COLUMNS",
    "compute_indicator_frame",
    "indicators_payload_from_ohlcv",
    "parse_indicator_kinds",
    "stock_indicators",
]
