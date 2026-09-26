"""Stock screening — filter by industry, report date, and FSA ratios."""

from __future__ import annotations

from .connection import KDB
from .functions_stock import FSA_RATIO_KEYS, _safe_ratio_num

SCREEN_OPS = {
    "gte": "$gte",
    "gt": "$gt",
    "lte": "$lte",
    "lt": "$lt",
    "eq": "$eq",
}

SCREEN_RATIO_FIELDS = set(FSA_RATIO_KEYS)


def _extract_ide(item) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, (list, tuple)):
        if len(item) >= 2:
            return item[1] or ""
        if len(item) == 1:
            return item[0] or ""
        return ""
    if isinstance(item, dict):
        return item.get("IDE") or item.get("ide") or ""
    return ""


def ides_for_industries(self: KDB, industries: list[str] | None) -> list[str] | None:
    """Resolve stock IDEs belonging to the given industry names.

    Matches BKHY constituents and STOCK HY1/HY2/HY3 labels.
    Returns ``None`` when no industry filter is provided.
    """
    names = [str(n).strip() for n in (industries or []) if str(n).strip()]
    if not names:
        return None

    ides: set[str] = set()
    for name in names:
        for item in self.stocks_in_HY(name) or []:
            ide = _extract_ide(item)
            if ide:
                ides.add(ide)

        cursor = self.col_TDX_STOCK.find(
            {"$or": [{"HY1.0": name}, {"HY2.0": name}, {"HY3.0": name}]},
            {"_id": 0, "IDE": 1},
        )
        for doc in cursor:
            ide = doc.get("IDE") or ""
            if ide:
                ides.add(ide)

    return sorted(ides)


def _passes_ratio(doc: dict, ratios: list[dict]) -> bool:
    for cond in ratios:
        field = cond.get("field")
        op = cond.get("op")
        if field not in SCREEN_RATIO_FIELDS or op not in SCREEN_OPS:
            continue
        try:
            target = float(cond.get("value"))
        except (TypeError, ValueError):
            return False
        actual = _safe_ratio_num(doc.get(field))
        if actual is None:
            return False
        if op == "gte" and not (actual >= target):
            return False
        if op == "gt" and not (actual > target):
            return False
        if op == "lte" and not (actual <= target):
            return False
        if op == "lt" and not (actual < target):
            return False
        if op == "eq" and not (actual == target):
            return False
    return True


def _normalize_report_date(value) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text[:10]


def fsa_report_dates(self: KDB) -> list[str]:
    """Distinct FSA report dates, newest first."""
    dates = {
        normalized
        for raw in self.col_TDX_FSA.distinct("REPORTDATE")
        if (normalized := _normalize_report_date(raw))
    }
    return sorted(dates, reverse=True)


def _ratio_conds(ratios: list[dict] | None) -> list[dict]:
    return [
        cond
        for cond in (ratios or [])
        if isinstance(cond, dict)
        and cond.get("field") in SCREEN_RATIO_FIELDS
        and cond.get("op") in SCREEN_OPS
        and cond.get("value") is not None
        and str(cond.get("value")).strip() != ""
    ]


def _mongo_ratio_match(ratio_conds: list[dict], *, prefix: str = "") -> dict:
    match: dict = {}
    for cond in ratio_conds:
        field = f"{prefix}{cond['field']}"
        match.setdefault(field, {})[SCREEN_OPS[cond["op"]]] = float(cond["value"])
    return match


def _row_from_doc(self: KDB, doc: dict) -> dict:
    ide = doc.get("IDE") or ""
    info = self.StockInfo(ide) or {}
    row = {
        "ide": ide,
        "name": info.get("IDS") or ide,
        "REPORTDATE": _normalize_report_date(doc.get("REPORTDATE")),
        **{key: _safe_ratio_num(doc.get(key)) for key in FSA_RATIO_KEYS},
    }
    hy1 = info.get("HY1")
    hy2 = info.get("HY2")
    if isinstance(hy1, (list, tuple)) and hy1:
        row["hy1"] = hy1[0]
    if isinstance(hy2, (list, tuple)) and hy2:
        row["hy2"] = hy2[0]
    return row


def screen_stocks(
    self: KDB,
    *,
    industries: list[str] | None = None,
    ratios: list[dict] | None = None,
    report_date: str | None = None,
) -> list[dict]:
    """Screen stocks by industry, report date, and/or FSA ratio conditions.

    ``ratios`` items: ``{field, op, value}`` with op in gte/gt/lte/lt/eq.
    ``report_date`` selects one statement period. Omit it to use each stock's
    latest report. Results are not capped.
    """
    ratio_conds = _ratio_conds(ratios)
    report_date = _normalize_report_date(report_date)
    industry_ides = self.ides_for_industries(industries)
    if industries and industry_ides is not None and not industry_ides:
        return []

    if report_date:
        query: dict = {"REPORTDATE": report_date, **_mongo_ratio_match(ratio_conds)}
        if industry_ides is not None:
            query["IDE"] = {"$in": industry_ides}
        rows = []
        for doc in self.col_TDX_FSA.find(query, {"_id": 0}).sort("IDE", 1):
            if ratio_conds and not _passes_ratio(doc, ratio_conds):
                continue
            rows.append(_row_from_doc(self, doc))
        return rows

    if ratio_conds:
        match: dict = {}
        if industry_ides is not None:
            match["IDE"] = {"$in": industry_ides}

        pipeline: list[dict] = []
        if match:
            pipeline.append({"$match": match})
        pipeline.extend(
            [
                {"$sort": {"IDE": 1, "REPORTDATE": -1}},
                {"$group": {"_id": "$IDE", "doc": {"$first": "$$ROOT"}}},
            ]
        )
        mongo_match = _mongo_ratio_match(ratio_conds, prefix="doc.")
        if mongo_match:
            pipeline.append({"$match": mongo_match})
        pipeline.append({"$sort": {"_id": 1}})

        rows = []
        for item in self.col_TDX_FSA.aggregate(pipeline, allowDiskUse=True):
            doc = item.get("doc") or {}
            if not _passes_ratio(doc, ratio_conds):
                continue
            rows.append(_row_from_doc(self, doc))
        return rows

    if industry_ides is None:
        return []

    rows = []
    for ide in industry_ides:
        info = self.StockInfo(ide) or {}
        row = {"ide": ide, "name": info.get("IDS") or ide}
        hy1 = info.get("HY1")
        hy2 = info.get("HY2")
        if isinstance(hy1, (list, tuple)) and hy1:
            row["hy1"] = hy1[0]
        if isinstance(hy2, (list, tuple)) and hy2:
            row["hy2"] = hy2[0]
        rows.append(row)

    fsa_map = self.fsa_latest_for_ides([r["ide"] for r in rows])
    for row in rows:
        row.update(fsa_map.get(row["ide"]) or {})
    return rows


KDB.ides_for_industries = ides_for_industries
KDB.fsa_report_dates = fsa_report_dates
KDB.screen_stocks = screen_stocks
