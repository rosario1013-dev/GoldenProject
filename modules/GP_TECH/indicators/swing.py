"""Swing High / Swing Low turning points (historically confirmed)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from GP_KDB import KDB
from GP_KDB.ohlc_resample import normalize_adjustment, normalize_period

DEFAULT_SWING_N = 2
DEFAULT_SWING_MIN_DISTANCE = 3
DEFAULT_SWING_MIN_CHANGE = 0.03


def resolve_min_change(
    ohlcv: pd.DataFrame,
    min_change: float | None = None,
    *,
    adaptive: bool = True,
) -> float:
    """Pick a usable min move.

    Prompt default is 3%, but low-volatility names (e.g. Moutai FDK ~4% span)
    need a smaller threshold. When ``min_change`` is omitted and ``adaptive``
    is True, use ~1/4 of the sample high/low span, clamped to [0.8%, 3%].
    """
    if min_change is not None:
        return float(min_change)
    if not adaptive or ohlcv.empty:
        return DEFAULT_SWING_MIN_CHANGE

    lo = float(pd.to_numeric(ohlcv["low"], errors="coerce").min())
    hi = float(pd.to_numeric(ohlcv["high"], errors="coerce").max())
    if not (lo > 0 and hi > lo):
        return DEFAULT_SWING_MIN_CHANGE
    span = hi / lo - 1.0
    return float(min(DEFAULT_SWING_MIN_CHANGE, max(0.008, span * 0.25)))


def detect_swing_turning_points(
    data: pd.DataFrame,
    *,
    n: int = DEFAULT_SWING_N,
    min_change: float = DEFAULT_SWING_MIN_CHANGE,
    min_distance: int = DEFAULT_SWING_MIN_DISTANCE,
) -> pd.DataFrame:
    """Detect confirmed swing highs/lows on OHLCV with a ``date`` column.

    A bar is a swing low if its low is strictly lower than the previous N and
    next N lows (same idea for swing high with highs). Confirmation needs the
    next N bars, so the last N bars never produce a signal.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    if min_change < 0:
        raise ValueError("min_change must be >= 0")
    if min_distance < 0:
        raise ValueError("min_distance must be >= 0")

    highs = data["high"].to_numpy(dtype=float)
    lows = data["low"].to_numpy(dtype=float)
    dates = data["date"].to_numpy()
    length = len(data)

    raw: list[dict[str, Any]] = []
    for i in range(n, length - n):
        left_h = highs[i - n : i]
        right_h = highs[i + 1 : i + n + 1]
        left_l = lows[i - n : i]
        right_l = lows[i + 1 : i + n + 1]

        if highs[i] > left_h.max() and highs[i] > right_h.max():
            raw.append(
                {
                    "index": i,
                    "date": dates[i],
                    "kind": "high",
                    "price": float(highs[i]),
                    "confirmed_at": i + n,
                }
            )
        if lows[i] < left_l.min() and lows[i] < right_l.min():
            raw.append(
                {
                    "index": i,
                    "date": dates[i],
                    "kind": "low",
                    "price": float(lows[i]),
                    "confirmed_at": i + n,
                }
            )

    raw.sort(key=lambda row: (row["index"], 0 if row["kind"] == "low" else 1))

    filtered: list[dict[str, Any]] = []
    for point in raw:
        if not filtered:
            filtered.append(point)
            continue

        prev = filtered[-1]
        gap = point["index"] - prev["index"]
        if gap < min_distance:
            if point["kind"] == prev["kind"]:
                better = (
                    point["price"] > prev["price"]
                    if point["kind"] == "high"
                    else point["price"] < prev["price"]
                )
                if better:
                    filtered[-1] = point
            continue

        if point["kind"] == prev["kind"]:
            better = (
                point["price"] > prev["price"]
                if point["kind"] == "high"
                else point["price"] < prev["price"]
            )
            if better:
                filtered[-1] = point
            continue

        rel = abs(point["price"] - prev["price"]) / prev["price"]
        if rel < min_change:
            continue

        filtered.append(point)

    out = pd.DataFrame(filtered)
    if out.empty:
        return pd.DataFrame(columns=["index", "date", "kind", "price", "confirmed_at"])
    return out.reset_index(drop=True)


def swings_payload_from_ohlcv(
    ohlcv: pd.DataFrame,
    *,
    n: int = DEFAULT_SWING_N,
    min_change: float | None = None,
    min_distance: int = DEFAULT_SWING_MIN_DISTANCE,
    adaptive: bool = True,
) -> dict[str, Any]:
    """Return chart-ready swing markers from an OHLCV frame."""
    resolved = resolve_min_change(ohlcv, min_change, adaptive=adaptive)
    points = detect_swing_turning_points(
        ohlcv,
        n=n,
        min_change=resolved,
        min_distance=min_distance,
    )
    markers: list[dict[str, Any]] = []
    for row in points.itertuples(index=False):
        markers.append(
            {
                "time": str(row.date)[:10],
                "kind": row.kind,
                "price": float(row.price),
            }
        )
    return {
        "params": {
            "n": int(n),
            "min_change": resolved,
            "min_distance": int(min_distance),
            "adaptive": bool(adaptive and min_change is None),
        },
        "markers": markers,
        "count": len(markers),
    }


def stock_swings(
    kdb: KDB,
    ide: str,
    *,
    period: str = "daily",
    adjustment: str = "forward",
    n: int = DEFAULT_SWING_N,
    min_change: float | None = None,
    min_distance: int = DEFAULT_SWING_MIN_DISTANCE,
    adaptive: bool = True,
) -> dict[str, Any]:
    """Compute swing markers on the same OHLC bars used by the FDK chart API."""
    from .chart_series import _to_ohlcv

    period = normalize_period(period)
    adjustment = normalize_adjustment(adjustment)
    df = kdb.STOCK_OHLC_PERIOD(ide, period, adjustment=adjustment)
    empty = {
        "ide": ide,
        "period": period,
        "adjustment": adjustment,
        "params": {
            "n": int(n),
            "min_change": float(min_change) if min_change is not None else DEFAULT_SWING_MIN_CHANGE,
            "min_distance": int(min_distance),
            "adaptive": bool(adaptive and min_change is None),
        },
        "markers": [],
        "count": 0,
    }
    if df is None or df.empty:
        return empty

    ohlcv = _to_ohlcv(df)
    if ohlcv.empty:
        return empty

    payload = swings_payload_from_ohlcv(
        ohlcv,
        n=n,
        min_change=min_change,
        min_distance=min_distance,
        adaptive=adaptive,
    )
    payload.update(
        {
            "ide": ide,
            "period": period,
            "adjustment": adjustment,
        }
    )
    return payload


def recent_swings_from_ohlcv(
    ohlcv: pd.DataFrame,
    *,
    lookback: int = 3,
    recent_days: int | None = None,
    n: int = DEFAULT_SWING_N,
    min_change: float | None = None,
    min_distance: int = DEFAULT_SWING_MIN_DISTANCE,
    adaptive: bool = True,
) -> dict[str, Any]:
    """Swing markers that became visible within the last ``lookback`` bars.

    ``recent_days`` is accepted as an alias for ``lookback`` (pool API naming).
    Confirmation needs the next ``n`` bars, so a signal "appears" on
    ``confirmed_at`` rather than on the swing bar itself.
    """
    if recent_days is not None:
        lookback = int(recent_days)
    if lookback < 1:
        raise ValueError("lookback must be >= 1")

    empty = {
        "lookback": int(lookback),
        "buy": False,
        "sell": False,
        "markers": [],
        "count": 0,
    }
    if ohlcv is None or ohlcv.empty:
        return empty

    resolved = resolve_min_change(ohlcv, min_change, adaptive=adaptive)
    points = detect_swing_turning_points(
        ohlcv,
        n=n,
        min_change=resolved,
        min_distance=min_distance,
    )
    params = {
        "n": int(n),
        "min_change": resolved,
        "min_distance": int(min_distance),
        "adaptive": bool(adaptive and min_change is None),
    }
    if points.empty:
        empty["params"] = params
        return empty

    min_confirmed = len(ohlcv) - lookback
    recent = points[points["confirmed_at"] >= min_confirmed]
    markers: list[dict[str, Any]] = []
    for row in recent.itertuples(index=False):
        markers.append(
            {
                "time": str(row.date)[:10],
                "kind": row.kind,
                "price": float(row.price),
            }
        )
    buy = any(m["kind"] == "low" for m in markers)
    sell = any(m["kind"] == "high" for m in markers)
    return {
        "lookback": int(lookback),
        "params": params,
        "buy": buy,
        "sell": sell,
        "markers": markers,
        "count": len(markers),
    }


def stock_recent_swings(
    kdb: KDB,
    ide: str,
    *,
    lookback: int = 3,
    recent_days: int | None = None,
    period: str = "daily",
    adjustment: str = "forward",
    n: int = DEFAULT_SWING_N,
    min_change: float | None = None,
    min_distance: int = DEFAULT_SWING_MIN_DISTANCE,
    adaptive: bool = True,
) -> dict[str, Any]:
    """Swing markers that became visible within the last ``lookback`` bars.

    Confirmation needs the next ``n`` bars, so a signal "appears" on
    ``confirmed_at`` rather than on the swing bar itself. Pool tables use
    this to flag names with fresh buy/sell points.
    """
    from .chart_series import _to_ohlcv

    if recent_days is not None:
        lookback = int(recent_days)
    if lookback < 1:
        raise ValueError("lookback must be >= 1")

    period = normalize_period(period)
    adjustment = normalize_adjustment(adjustment)
    empty = {
        "ide": ide,
        "period": period,
        "adjustment": adjustment,
        "lookback": int(lookback),
        "buy": False,
        "sell": False,
        "markers": [],
        "count": 0,
    }
    df = kdb.STOCK_OHLC_PERIOD(ide, period, adjustment=adjustment)
    if df is None or df.empty:
        return empty

    ohlcv = _to_ohlcv(df)
    if ohlcv.empty:
        return empty

    summary = recent_swings_from_ohlcv(
        ohlcv,
        lookback=lookback,
        n=n,
        min_change=min_change,
        min_distance=min_distance,
        adaptive=adaptive,
    )
    empty.update(summary)
    return empty


def recent_swings_for_ides(
    kdb: KDB,
    ides: list[str],
    *,
    recent_days: int = 3,
    period: str = "daily",
    adjustment: str = "forward",
    max_workers: int = 8,
) -> dict[str, dict[str, Any]]:
    """Batch recent swing summaries keyed by ``ide`` (for pool recent-swings API)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    unique = list(dict.fromkeys(str(ide).strip() for ide in ides if str(ide).strip()))
    if not unique:
        return {}

    def _one(ide: str) -> tuple[str, dict[str, Any]]:
        try:
            return ide, stock_recent_swings(
                kdb,
                ide,
                lookback=recent_days,
                period=period,
                adjustment=adjustment,
            )
        except Exception:
            return ide, {
                "ide": ide,
                "lookback": int(recent_days),
                "buy": False,
                "sell": False,
                "markers": [],
                "count": 0,
            }

    out: dict[str, dict[str, Any]] = {}
    workers = max(1, min(int(max_workers), len(unique)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, ide) for ide in unique]
        for fut in as_completed(futures):
            ide, payload = fut.result()
            out[ide] = payload
    return out


__all__ = [
    "DEFAULT_SWING_MIN_CHANGE",
    "DEFAULT_SWING_MIN_DISTANCE",
    "DEFAULT_SWING_N",
    "detect_swing_turning_points",
    "recent_swings_for_ides",
    "recent_swings_from_ohlcv",
    "resolve_min_change",
    "stock_recent_swings",
    "stock_swings",
    "swings_payload_from_ohlcv",
]
