"""Stock metadata and industry block queries."""

from __future__ import annotations

from .connection import KDB
from .utils import security_type as _security_type


def stock_info(self: KDB, ide: str) -> dict | None:
    return self.col_TDX_STOCK.find_one({"IDE": ide}, {"_id": 0})


def hy_children(self: KDB, ids: str, level: str | int | None = None) -> dict:
    """Children of an industry block.

    For root ``全部行业``, ``level`` selects BKHY.L (``1`` / ``2``; default ``1``).
    """
    if ids == "全部行业":
        level_key = str(level or "1").strip() or "1"
        if level_key not in {"1", "2", "3"}:
            level_key = "1"
        query = (
            KDB()
            .col_TDX_BKHY.find({"L": level_key}, {"_id": 0, "IDS": 1, "IDE": 1, "code": 1})
            .sort([("code", 1)])
        )
        return {"children": [[x["IDS"], x["IDE"], x["code"]] for x in query]}

    query = KDB().col_TDX_BKHY.find_one({"IDS": ids}, {"_id": 0, "children": 1})
    return {"children": query["children"] if query else []}


def stocks_in_hy(self: KDB, ids: str) -> list:
    query = KDB().col_TDX_BKHY.find_one({"IDS": ids}, {"_id": 0})
    return query["stocks"] if query else []


def stocks_ides(self: KDB) -> list[str]:
    query = self.col_TDX_STOCK.find({}, {"_id": 0, "IDE": 1}).sort([("IDE", 1)])
    return [x["IDE"] for x in query]


def stocks_list(self: KDB) -> list[dict]:
    query = self.col_TDX_STOCK.find({}, {"_id": 0, "IDE": 1, "IDS": 1, "ABB": 1}).sort([("IDE", 1)])
    return [{"ide": doc["IDE"], "name": doc.get("IDS") or "", "ABB": doc.get("ABB") or ""} for doc in query]


def hy_list(self: KDB) -> list[dict]:
    """All industry blocks for search dropdown / industry pages."""
    query = self.col_TDX_BKHY.find(
        {},
        {"_id": 0, "IDS": 1, "IDE": 1, "code": 1, "L": 1},
    ).sort([("code", 1)])
    rows = []
    for doc in query:
        name = doc.get("IDS") or ""
        if not name:
            continue
        rows.append(
            {
                "name": name,
                "ide": doc.get("IDE") or "",
                "code": doc.get("code") or "",
                "level": doc.get("L") or "",
            }
        )
    return rows


def hy_info(self: KDB, ids: str) -> dict | None:
    """Single industry block metadata by name (IDS)."""
    doc = self.col_TDX_BKHY.find_one(
        {"IDS": ids},
        {"_id": 0, "IDS": 1, "IDE": 1, "code": 1, "L": 1, "children": 1, "stocks": 1},
    )
    if not doc:
        return None
    children = doc.get("children") or []
    stocks = doc.get("stocks") or []
    return {
        "name": doc.get("IDS") or ids,
        "ide": doc.get("IDE") or "",
        "code": doc.get("code") or "",
        "level": doc.get("L") or "",
        "has_children": bool(children),
        "stock_count": len(stocks),
    }


def security_type_method(self: KDB, ide: str) -> str | None:
    return _security_type(ide)


KDB.StockInfo = stock_info
KDB.HYchildren = hy_children
KDB.stocks_in_HY = stocks_in_hy
KDB.stocksIDEs = stocks_ides
KDB.StocksList = stocks_list
KDB.HYList = hy_list
KDB.HYInfo = hy_info
KDB.SecurityType = security_type_method
