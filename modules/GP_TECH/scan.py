"""Batch technical scans over stocks stored in GP_KDB."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from GP_KDB import KDB
from GP_KDB.utils import security_type

from .channel.entered import CHANNEL_MODES, detect_channel_state
from .config import (
    DEFAULT_CHANNEL_CONFIG,
    DEFAULT_INDEPENDENT_STRONG_CONFIG,
    DEFAULT_INDUSTRY_RELATIVE_CONFIG,
)
from .data.quotes import load_forward_ohlc
from .relative import closes_series, relative_metrics


def _unique_ides(values: Iterable[str] | None) -> list[str]:
    return list(
        dict.fromkeys(
            str(value).strip()
            for value in (values or [])
            if str(value).strip()
        )
    )


def _candidate_ides(
    kdb: KDB,
    *,
    ides: list[str] | None,
    industries: list[str] | None,
) -> list[str]:
    requested = _unique_ides(ides)
    if requested:
        candidates = requested
    else:
        names = _unique_ides(industries)
        # 「全部行业」means scan the full stock universe.
        if names and any(name in {"全部行业", "*"} for name in names):
            names = []
        if names:
            candidates = kdb.ides_for_industries(names) or []
        else:
            candidates = kdb.stocksIDEs()
    return [ide for ide in candidates if security_type(ide) == "stock"]


def _industry_name(value) -> str:
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    return ""


def _serialize_match(
    ide: str,
    info: dict,
    result: dict,
    adjustment: str,
) -> dict:
    return {
        "ide": ide,
        "name": info.get("IDS") or ide,
        "hy1": _industry_name(info.get("HY1")),
        "hy2": _industry_name(info.get("HY2")),
        "score": int(result.get("score") or 0),
        "score_text": result.get("score_text") or "0/7",
        "mode": result.get("mode"),
        "is_match": bool(result.get("is_match")),
        "as_of": result.get("as_of"),
        "adjustment": adjustment,
        "conditions": result.get("conditions") or {},
        "metrics": result.get("metrics") or {},
        "previous_is_channel": result.get("previous_is_channel"),
        "previous_score": result.get("previous_score"),
    }


def scan_channel_stocks(
    kdb: KDB,
    *,
    ides: list[str] | None = None,
    industries: list[str] | None = None,
    mode: str = "in",
    lookback: int = DEFAULT_CHANNEL_CONFIG.lookback,
    pivot_window: int = DEFAULT_CHANNEL_CONFIG.pivot_window,
    min_score: int = DEFAULT_CHANNEL_CONFIG.min_score,
    history_days: int = DEFAULT_CHANNEL_CONFIG.history_days,
    limit: int = 500,
) -> list[dict]:
    """Scan stocks for an ascending channel and return matching rows."""
    if mode not in CHANNEL_MODES:
        raise ValueError(f"mode must be one of {sorted(CHANNEL_MODES)}")

    lookback = max(60, min(int(lookback), 500))
    pivot_window = max(3, min(int(pivot_window), 31))
    history_days = max(lookback + 1, min(int(history_days), 1500))
    limit = max(1, min(int(limit), 2000))

    rows: list[dict] = []
    for ide in _candidate_ides(kdb, ides=ides, industries=industries):
        data = load_forward_ohlc(kdb, ide, days=history_days)
        if data.empty:
            continue
        result = detect_channel_state(
            data,
            mode=mode,
            lookback=lookback,
            pivot_window=pivot_window,
            min_score=min_score,
        )
        if not result.get("is_match"):
            continue
        info = kdb.StockInfo(ide) or {}
        rows.append(
            _serialize_match(
                ide,
                info,
                result,
                data.attrs.get("adjustment", "none"),
            )
        )

    rows.sort(
        key=lambda row: (
            -row["score"],
            -(row["metrics"].get("下轨R²") or 0),
            row["ide"],
        )
    )
    return rows[:limit]


def scan_independent_strong_stocks(
    kdb: KDB,
    *,
    ides: list[str] | None = None,
    industries: list[str] | None = None,
    benchmark_ide: str = DEFAULT_INDEPENDENT_STRONG_CONFIG.benchmark_ide,
    mode: str = "in",
    lookback: int = DEFAULT_INDEPENDENT_STRONG_CONFIG.lookback,
    pivot_window: int = DEFAULT_INDEPENDENT_STRONG_CONFIG.pivot_window,
    min_score: int = DEFAULT_INDEPENDENT_STRONG_CONFIG.min_score,
    history_days: int = DEFAULT_INDEPENDENT_STRONG_CONFIG.history_days,
    corr_window: int = DEFAULT_INDEPENDENT_STRONG_CONFIG.corr_window,
    excess_window: int = DEFAULT_INDEPENDENT_STRONG_CONFIG.excess_window,
    max_corr: float = DEFAULT_INDEPENDENT_STRONG_CONFIG.max_corr,
    min_excess: float = DEFAULT_INDEPENDENT_STRONG_CONFIG.min_excess,
    limit: int = 500,
) -> list[dict]:
    """Scan for ascending-channel stocks with positive excess and low index corr.

    Pipeline order: channel match → excess filter → correlation filter.
    """
    if mode not in CHANNEL_MODES:
        raise ValueError(f"mode must be one of {sorted(CHANNEL_MODES)}")

    lookback = max(60, min(int(lookback), 500))
    pivot_window = max(3, min(int(pivot_window), 31))
    history_days = max(lookback + 1, min(int(history_days), 1500))
    corr_window = max(20, min(int(corr_window), 250))
    excess_window = max(5, min(int(excess_window), 120))
    max_corr = float(max_corr)
    min_excess = float(min_excess)
    limit = max(1, min(int(limit), 2000))
    benchmark_ide = str(benchmark_ide or DEFAULT_INDEPENDENT_STRONG_CONFIG.benchmark_ide).strip()

    index_ohlc = load_forward_ohlc(
        kdb,
        benchmark_ide,
        days=history_days,
        require_amount=False,
    )
    index_closes = closes_series(index_ohlc)
    if index_closes.empty:
        raise ValueError(f"无法加载基准指数行情: {benchmark_ide}")

    rows: list[dict] = []
    for ide in _candidate_ides(kdb, ides=ides, industries=industries):
        data = load_forward_ohlc(kdb, ide, days=history_days)
        if data.empty:
            continue

        channel = detect_channel_state(
            data,
            mode=mode,
            lookback=lookback,
            pivot_window=pivot_window,
            min_score=min_score,
        )
        if not channel.get("is_match"):
            continue

        rel = relative_metrics(
            closes_series(data),
            index_closes,
            corr_window=corr_window,
            excess_window=excess_window,
        )
        excess = rel.get("excess")
        corr = rel.get("corr")
        if excess is None or excess <= min_excess:
            continue
        if corr is None or corr >= max_corr:
            continue

        info = kdb.StockInfo(ide) or {}
        row = _serialize_match(
            ide,
            info,
            channel,
            data.attrs.get("adjustment", "none"),
        )
        row.update(
            {
                "benchmark": benchmark_ide,
                "corr": corr,
                "beta": rel.get("beta"),
                "excess": excess,
                "corr_window": corr_window,
                "excess_window": excess_window,
                "sample_days": rel.get("sample_days") or 0,
            }
        )
        rows.append(row)

    rows.sort(
        key=lambda row: (
            -row["score"],
            -(row.get("excess") or 0),
            row.get("corr") if row.get("corr") is not None else 99,
            row["ide"],
        )
    )
    return rows[:limit]


def _parse_hy_child(item) -> dict | None:
    if not isinstance(item, (list, tuple)) or len(item) < 2:
        return None
    name = str(item[0] or "").strip()
    ide = str(item[1] or "").strip()
    if not name or not ide:
        return None
    return {
        "name": name,
        "ide": ide,
        "code": str(item[2] or "").strip() if len(item) > 2 else "",
    }


def _hy1_parent_map(kdb: KDB) -> dict[str, str]:
    """Map HY2/HY3 IDE → parent HY1 name via BKHY children links."""
    mapping: dict[str, str] = {}
    roots = kdb.HYchildren("全部行业", level="1").get("children") or []
    for root in roots:
        parent = _parse_hy_child(root)
        if not parent:
            continue
        children = kdb.HYchildren(parent["name"]).get("children") or []
        for child in children:
            entry = _parse_hy_child(child)
            if entry:
                mapping[entry["ide"]] = parent["name"]
    return mapping


def _industry_candidates(
    kdb: KDB,
    *,
    level: str,
    parents: list[str] | None,
    ides: list[str] | None,
) -> list[dict]:
    """Resolve industry index rows to scan (default: all HY2)."""
    requested = _unique_ides(ides)
    if requested:
        by_ide = {
            row["ide"]: row
            for row in (kdb.HYList() or [])
            if row.get("ide")
        }
        rows = []
        for ide in requested:
            meta = by_ide.get(ide) or {}
            rows.append(
                {
                    "name": meta.get("name") or ide,
                    "ide": ide,
                    "code": meta.get("code") or "",
                    "level": str(meta.get("level") or level),
                    "parent": "",
                }
            )
        return rows

    parent_names = _unique_ides(parents)
    if parent_names:
        rows = []
        seen: set[str] = set()
        for parent in parent_names:
            children = kdb.HYchildren(parent).get("children") or []
            for child in children:
                entry = _parse_hy_child(child)
                if not entry or entry["ide"] in seen:
                    continue
                seen.add(entry["ide"])
                entry["parent"] = parent
                entry["level"] = level
                rows.append(entry)
        return rows

    children = kdb.HYchildren("全部行业", level=level).get("children") or []
    parent_map = _hy1_parent_map(kdb) if str(level) == "2" else {}
    rows = []
    for child in children:
        entry = _parse_hy_child(child)
        if not entry:
            continue
        entry["parent"] = parent_map.get(entry["ide"], "")
        entry["level"] = str(level)
        rows.append(entry)
    return rows


def scan_industry_relative(
    kdb: KDB,
    *,
    level: str = DEFAULT_INDUSTRY_RELATIVE_CONFIG.level,
    parents: list[str] | None = None,
    ides: list[str] | None = None,
    benchmark_ide: str = DEFAULT_INDUSTRY_RELATIVE_CONFIG.benchmark_ide,
    history_days: int = DEFAULT_INDUSTRY_RELATIVE_CONFIG.history_days,
    corr_window: int = DEFAULT_INDUSTRY_RELATIVE_CONFIG.corr_window,
    excess_window: int = DEFAULT_INDUSTRY_RELATIVE_CONFIG.excess_window,
    max_corr: float | None = None,
    min_corr: float | None = None,
    min_excess: float | None = None,
    limit: int = 500,
) -> list[dict]:
    """Compute correlation / beta / excess for industry indices vs a benchmark.

    Default universe is BKHY level-2 (二级行业) index quotes (``sh881xxx``).
    """
    level = str(level or "2").strip() or "2"
    if level not in {"1", "2", "3"}:
        raise ValueError("level must be '1', '2', or '3'")

    history_days = max(60, min(int(history_days), 1500))
    corr_window = max(20, min(int(corr_window), 250))
    excess_window = max(5, min(int(excess_window), 120))
    limit = max(1, min(int(limit), 2000))
    benchmark_ide = str(benchmark_ide or DEFAULT_INDUSTRY_RELATIVE_CONFIG.benchmark_ide).strip()

    index_ohlc = load_forward_ohlc(
        kdb,
        benchmark_ide,
        days=history_days,
        require_amount=False,
    )
    index_closes = closes_series(index_ohlc)
    if index_closes.empty:
        raise ValueError(f"无法加载基准指数行情: {benchmark_ide}")

    rows: list[dict] = []
    for sector in _industry_candidates(kdb, level=level, parents=parents, ides=ides):
        data = load_forward_ohlc(
            kdb,
            sector["ide"],
            days=history_days,
            require_amount=False,
        )
        if data.empty:
            continue

        rel = relative_metrics(
            closes_series(data),
            index_closes,
            corr_window=corr_window,
            excess_window=excess_window,
        )
        corr = rel.get("corr")
        excess = rel.get("excess")
        if corr is None:
            continue
        if max_corr is not None and corr >= float(max_corr):
            continue
        if min_corr is not None and corr <= float(min_corr):
            continue
        if min_excess is not None and (excess is None or excess <= float(min_excess)):
            continue

        as_of = ""
        if "date" in data.columns and not data.empty:
            as_of = str(pd.Timestamp(data["date"].iloc[-1]).date())

        rows.append(
            {
                "ide": sector["ide"],
                "name": sector["name"],
                "code": sector.get("code") or "",
                "level": sector.get("level") or level,
                "parent": sector.get("parent") or "",
                "benchmark": benchmark_ide,
                "corr": corr,
                "beta": rel.get("beta"),
                "excess": excess,
                "corr_window": corr_window,
                "excess_window": excess_window,
                "sample_days": rel.get("sample_days") or 0,
                "as_of": as_of,
                "adjustment": data.attrs.get("adjustment", "none"),
            }
        )

    rows.sort(
        key=lambda row: (
            row.get("corr") if row.get("corr") is not None else 99,
            -(row.get("excess") or 0),
            row["ide"],
        )
    )
    return rows[:limit]
