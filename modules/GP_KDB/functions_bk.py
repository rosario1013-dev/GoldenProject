"""Block and sector financial data queries."""

from __future__ import annotations

import pandas as pd

from .connection import KDB


def stocks_by_bk(self: KDB) -> pd.DataFrame:
    query = (
        KDB()
        .col_TDX_STOCK.find(
            {},
            {"_id": 0, "IDE": 1, "DQ": 1, "HY1": 1, "HY2": 1, "HY3": 1, "BK_GN": 1, "BK_FG": 1},
        )
        .sort([("IDE", 1)])
    )
    stocks = list(query)

    result = []
    for stock in stocks:
        result.append({"IDE": stock["IDE"], "BK": "sh"})
        result.append({"IDE": stock["IDE"], "BK": stock["DQ"][1]})
        result.append({"IDE": stock["IDE"], "BK": stock["HY1"][1]})
        result.append({"IDE": stock["IDE"], "BK": stock["HY2"][1]})
        if isinstance(stock.get("HY3"), list) and len(stock["HY3"]) > 1:
            result.append({"IDE": stock["IDE"], "BK": stock["HY3"][1]})
        if "BK_GN" in stock:
            for bk in stock["BK_GN"]:
                result.append({"IDE": stock["IDE"], "BK": bk[1]})

    df = pd.DataFrame(result).dropna()
    df = df[df["BK"] != ""]
    return df.sort_values("BK")


def cw_bk(self: KDB, ide: str, end_dt: str | None = None) -> pd.DataFrame:
    finditem: dict = {"IDE": ide}
    if end_dt:
        finditem["REPORTDATE"] = {"$lte": end_dt}

    query = self.col_TDX_CWBK.find(finditem, {"_id": 0, "IDE": 0, "MK": 0}).sort([("REPORTDATE", 1)])
    return pd.DataFrame(list(query)).set_index("REPORTDATE").dropna()


KDB.StocksByBK = stocks_by_bk
KDB.CW_BK = cw_bk
