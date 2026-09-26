"""Aggregate company CW net income into industry + year facts."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from ..connection import KDB
from .metrics import CAGR_PERIOD_3, CAGR_PERIOD_5, safe_float

# 归属于母公司股东的净利润
NET_INCOME_COL = "col96"
REVENUE_COL = "col74"

COLLECTION_NAME = "INDUSTRY_PROFIT_YEARLY"


def _year_end_date(year: int) -> str:
    return f"{int(year)}-12-31"


def _parse_year(report_date: Any) -> int | None:
    text = str(report_date or "")
    if len(text) < 10:
        return None
    if not text.endswith("12-31"):
        return None
    try:
        return int(text[:4])
    except ValueError:
        return None


def _stock_ides(stocks: list) -> list[str]:
    ides: list[str] = []
    seen: set[str] = set()
    for item in stocks or []:
        ide = None
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            ide = item[1]
        elif isinstance(item, dict):
            ide = item.get("IDE") or item.get("ide")
        elif isinstance(item, str):
            ide = item
        if not ide or ide in seen:
            continue
        seen.add(ide)
        ides.append(str(ide))
    return ides


def list_year_end_report_dates(kdb: KDB | None = None) -> list[str]:
    db = kdb or KDB()
    dates = db.col_TDX_CW.distinct("REPORTDATE")
    year_ends = sorted(
        {str(d) for d in dates if str(d).endswith("12-31")},
    )
    return year_ends


def available_years(kdb: KDB | None = None) -> list[int]:
    years: list[int] = []
    for date in list_year_end_report_dates(kdb):
        year = _parse_year(date)
        if year is not None:
            years.append(year)
    return sorted(set(years))


def _load_year_end_profits(
    kdb: KDB,
    report_dates: list[str],
) -> dict[str, dict[int, dict[str, float | None]]]:
    """IDE -> year -> {net_income, revenue}."""
    if not report_dates:
        return {}
    cursor = kdb.col_TDX_CW.find(
        {"REPORTDATE": {"$in": report_dates}},
        {"_id": 0, "IDE": 1, "REPORTDATE": 1, NET_INCOME_COL: 1, REVENUE_COL: 1},
    )
    out: dict[str, dict[int, dict[str, float | None]]] = defaultdict(dict)
    for doc in cursor:
        ide = doc.get("IDE")
        year = _parse_year(doc.get("REPORTDATE"))
        if not ide or year is None:
            continue
        out[ide][year] = {
            "net_income": safe_float(doc.get(NET_INCOME_COL)),
            "revenue": safe_float(doc.get(REVENUE_COL)),
        }
    return out


def _iter_industries(kdb: KDB, level: str) -> list[dict[str, Any]]:
    level_key = str(level).replace("HY", "").strip() or "1"
    if level_key not in {"1", "2", "3"}:
        level_key = "1"
    cursor = kdb.col_TDX_BKHY.find(
        {"L": level_key},
        {"_id": 0, "IDS": 1, "IDE": 1, "code": 1, "L": 1, "stocks": 1},
    ).sort([("code", 1)])
    return list(cursor)


def aggregate_industry_year(
    kdb: KDB | None = None,
    *,
    levels: tuple[str, ...] = ("1", "2"),
    years: list[int] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    """Build industry-year profit rows (not yet written)."""
    db = kdb or KDB()
    all_years = years or available_years(db)
    if not all_years:
        return []

    report_dates = [_year_end_date(y) for y in all_years]
    if on_progress:
        on_progress(f"loading CW year-end profits for {len(report_dates)} years")
    profits_by_ide = _load_year_end_profits(db, report_dates)

    rows: list[dict[str, Any]] = []
    for level in levels:
        industries = _iter_industries(db, level)
        if on_progress:
            on_progress(f"aggregating HY{level}: {len(industries)} industries")
        for hy in industries:
            name = hy.get("IDS") or ""
            if not name:
                continue
            ides = _stock_ides(hy.get("stocks") or [])
            for year in all_years:
                net_sum = 0.0
                rev_sum = 0.0
                net_count = 0
                rev_count = 0
                loss_count = 0
                with_data = 0
                for ide in ides:
                    cell = profits_by_ide.get(ide, {}).get(year)
                    if not cell:
                        continue
                    with_data += 1
                    ni = cell.get("net_income")
                    rv = cell.get("revenue")
                    if ni is not None:
                        net_sum += ni
                        net_count += 1
                        if ni < 0:
                            loss_count += 1
                    if rv is not None:
                        rev_sum += rv
                        rev_count += 1

                rows.append(
                    {
                        "industry": name,
                        "ide": hy.get("IDE") or "",
                        "code": hy.get("code") or "",
                        "level": str(hy.get("L") or level),
                        "year": int(year),
                        "report_date": _year_end_date(year),
                        "net_income": net_sum if net_count else None,
                        "revenue": rev_sum if rev_count else None,
                        "company_count": len(ides),
                        "companies_with_data": with_data,
                        "loss_company_count": loss_count,
                        "loss_company_ratio": (loss_count / with_data) if with_data else None,
                    }
                )
    return rows


def write_industry_profit_yearly(
    rows: list[dict[str, Any]],
    kdb: KDB | None = None,
    *,
    replace_levels: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Upsert rows into tdx.INDUSTRY_PROFIT_YEARLY."""
    db = kdb or KDB()
    col = db.col_TDX_INDUSTRY_PROFIT_YEARLY

    if replace_levels:
        col.delete_many({"level": {"$in": list(replace_levels)}})

    upserted = 0
    for row in rows:
        key = {
            "industry": row["industry"],
            "level": str(row["level"]),
            "year": int(row["year"]),
        }
        col.update_one(key, {"$set": row}, upsert=True)
        upserted += 1

    return {
        "collection": f"tdx.{COLLECTION_NAME}",
        "rows": len(rows),
        "upserted": upserted,
        "years": sorted({int(r["year"]) for r in rows}) if rows else [],
        "levels": sorted({str(r["level"]) for r in rows}) if rows else [],
    }


def build_industry_profit_yearly(
    kdb: KDB | None = None,
    *,
    levels: tuple[str, ...] = ("1", "2"),
    years: list[int] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Aggregate + write industry yearly profits."""
    db = kdb or KDB()
    rows = aggregate_industry_year(
        db,
        levels=levels,
        years=years,
        on_progress=on_progress,
    )
    result = write_industry_profit_yearly(rows, db, replace_levels=levels)
    if on_progress:
        on_progress(f"done: {result}")
    return result


def load_yearly_rows(
    kdb: KDB | None = None,
    *,
    level: str = "1",
    industry: str | None = None,
) -> list[dict[str, Any]]:
    db = kdb or KDB()
    level_key = str(level).replace("HY", "").strip() or "1"
    query: dict[str, Any] = {"level": level_key}
    if industry and industry not in {"", "All", "全部行业", "All Industries"}:
        query["industry"] = industry
    cursor = db.col_TDX_INDUSTRY_PROFIT_YEARLY.find(query, {"_id": 0}).sort(
        [("industry", 1), ("year", 1)]
    )
    return list(cursor)


def rows_for_metrics(
    yearly_rows: list[dict[str, Any]],
    *,
    year: int,
    cagr_period_3: int = CAGR_PERIOD_3,
    cagr_period_5: int = CAGR_PERIOD_5,
) -> list[dict[str, Any]]:
    """Pivot INDUSTRY_PROFIT_YEARLY docs into build_industry_metrics inputs."""
    by_industry: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in yearly_rows:
        by_industry[row.get("industry") or ""].append(row)

    out: list[dict[str, Any]] = []
    for name, items in by_industry.items():
        if not name:
            continue
        by_year = {int(r["year"]): r for r in items if r.get("year") is not None}
        current = by_year.get(year)
        if not current:
            continue
        yearly_profits = {
            y: safe_float(r.get("net_income")) for y, r in by_year.items()
        }
        series = [
            {"year": y, "net_income": safe_float(by_year[y].get("net_income")) if y in by_year else None}
            for y in range(year - 4, year + 1)
        ]
        out.append(
            {
                "industry": name,
                "ide": current.get("ide") or "",
                "code": current.get("code") or "",
                "level": current.get("level") or "",
                "company_count": int(current.get("company_count") or 0),
                "current_profit": safe_float(current.get("net_income")),
                "previous_profit": safe_float((by_year.get(year - 1) or {}).get("net_income")),
                "profit_3y_ago": safe_float(
                    (by_year.get(year - cagr_period_3) or {}).get("net_income")
                ),
                "profit_5y_ago": safe_float(
                    (by_year.get(year - cagr_period_5) or {}).get("net_income")
                ),
                "yearly_profits": yearly_profits,
                "yearly_series": series,
                "loss_company_ratio": safe_float(current.get("loss_company_ratio")),
            }
        )
    return out
