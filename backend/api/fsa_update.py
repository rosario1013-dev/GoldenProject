"""Compute GP_FSA ratios and upload to MongoDB tdx.FSA."""

from __future__ import annotations

import json
import sys
from typing import Any, Callable

import pandas as pd
import pymongo

from GP_FSA import Stock, accounts
from GP_KDB import KDB

RATIO_FIELDS: list[dict[str, Any]] = [
    {
        "key": "BPS",
        "label": "每股净资产 BPS",
        "account": "BPS",
        "scale": 1,
        "percent": False,
        "description": "归属于母公司股东权益 / 总股本",
    },
    {
        "key": "ROE",
        "label": "净资产收益率_1Y",
        "account": "净资产收益率_1Y",
        "scale": 100,
        "percent": True,
        "description": "滚动一年净资产收益率 (%)",
    },
    {
        "key": "ROA",
        "label": "总资产收益率_1Y",
        "account": "总资产收益率_1Y",
        "scale": 100,
        "percent": True,
        "description": "滚动一年总资产收益率 (%)",
    },
    {
        "key": "归母净利润同比_1Y",
        "label": "归母净利润同比_1Y",
        "account": "归母净利润同比_1Y",
        "scale": 100,
        "percent": True,
        "description": "滚动一年归母净利润同比 (%)",
    },
    {
        "key": "归母净利润同比",
        "label": "归母净利润同比",
        "account": "归母净利润同比",
        "scale": 100,
        "percent": True,
        "description": "归母净利润相对上一报告期变动 (%)",
    },
    {
        "key": "营业总收入同比_1Y",
        "label": "营业总收入同比_1Y",
        "account": "营业总收入同比_1Y",
        "scale": 100,
        "percent": True,
        "description": "滚动一年营业总收入同比 (%)",
    },
    {
        "key": "营业总收入同比",
        "label": "营业总收入同比",
        "account": "营业总收入同比",
        "scale": 100,
        "percent": True,
        "description": "营业总收入相对上一报告期变动 (%)",
    },
    {
        "key": "营业总收入_单季同比",
        "label": "营业总收入单季同比",
        "account": "营业总收入_单季同比",
        "scale": 100,
        "percent": True,
        "description": "单季营业总收入相对上一报告期变动 (%)",
    },
    {
        "key": "每股流动资产",
        "label": "每股流动资产",
        "account": "每股流动资产",
        "scale": 1,
        "percent": False,
        "description": "流动资产合计 / 总股本",
    },
    {
        "key": "FQ每股流动资产",
        "label": "FQ每股流动资产",
        "account": "FQ每股流动资产",
        "scale": 1,
        "percent": False,
        "description": "复权每股流动资产",
    },
    {
        "key": "FQ每股净流动资产",
        "label": "FQ每股净流动资产",
        "account": "FQ每股净流动资产",
        "scale": 1,
        "percent": False,
        "description": "复权每股净流动资产",
    },
    {
        "key": "PKV",
        "label": "PKV",
        "account": "PKV",
        "scale": 1,
        "percent": False,
        "description": "复权因子",
    },
    {
        "key": "毛利率",
        "label": "毛利率",
        "account": "毛利率",
        "scale": 100,
        "percent": True,
        "description": "营业利润 / 营业收入 (%)",
    },
    {
        "key": "管理费用比例",
        "label": "管理费用比例",
        "account": "管理费用比例",
        "scale": 1,
        "percent": True,
        "description": "管理费用 / 营业总收入 (%)，公式已含 *100",
    },
    {
        "key": "销售费用比例",
        "label": "销售费用比例",
        "account": "销售费用比例",
        "scale": 1,
        "percent": True,
        "description": "销售费用 / 营业总收入 (%)，公式已含 *100",
    },
    {
        "key": "研发费用比例",
        "label": "研发费用比例",
        "account": "研发费用比例",
        "scale": 1,
        "percent": True,
        "description": "研发费用 / 营业总收入 (%)，公式已含 *100",
    },
    {
        "key": "营业成本比例",
        "label": "营业成本比例",
        "account": "营业成本比例",
        "scale": 1,
        "percent": True,
        "description": "营业成本 / 营业总收入 (%)，公式已含 *100",
    },
]


def list_ratio_fields() -> list[dict[str, Any]]:
    return RATIO_FIELDS


def calc_stock_ratios(ide: str, *, recent_quarters: int | None = 40) -> pd.DataFrame:
    """Compute configured ratios for one stock from CW data in MongoDB."""
    st = Stock(ide).load_FS()
    if st.FS.empty:
        return pd.DataFrame()

    series_map: dict[str, pd.Series] = {}
    for field in RATIO_FIELDS:
        account_name = field["account"]
        if account_name not in accounts:
            raise KeyError(f"Account not found: {account_name}")
        series_map[field["key"]] = accounts[account_name].value(st) * field["scale"]

    df = pd.DataFrame(series_map).dropna(how="all")
    if df.empty:
        return df

    if recent_quarters is not None and recent_quarters > 0:
        df = df.tail(recent_quarters)

    df["REPORTDATE"] = df.index
    df["IDE"] = ide
    return df.reset_index(drop=True)


def upload_stock_ratios(
    ide: str,
    kdb: KDB,
    *,
    recent_quarters: int | None = 40,
) -> int:
    df = calc_stock_ratios(ide, recent_quarters=recent_quarters)
    if df.empty:
        return 0

    records = json.loads(df.to_json(orient="records", double_precision=4))
    ops = [
        pymongo.UpdateOne(
            {"IDE": row["IDE"], "REPORTDATE": row["REPORTDATE"]},
            {"$set": row},
            upsert=True,
        )
        for row in records
    ]
    result = kdb.col_TDX_FSA.bulk_write(ops, ordered=False)
    return result.modified_count + result.upserted_count


def upload_all_fsa_ratios(
    *,
    kdb: KDB | None = None,
    ides: list[str] | None = None,
    recent_quarters: int | None = 40,
    on_error: Callable[[str, Exception], None] | None = None,
    show_progress: bool = True,
) -> dict[str, Any]:
    """Upload GP_FSA ratios for all stocks into tdx.FSA."""
    db = kdb or KDB()
    if not db.is_configured:
        raise RuntimeError("KDB is not configured")

    stock_list = ides or db.stocksIDEs()
    total_rows = 0
    stocks_updated = 0
    errors = 0

    iterator = stock_list
    if show_progress:
        try:
            import tqdm

            iterator = tqdm.tqdm(stock_list, desc="FSA")
        except ImportError:
            pass

    for ide in iterator:
        try:
            rows = upload_stock_ratios(ide, db, recent_quarters=recent_quarters)
            if rows > 0:
                stocks_updated += 1
            total_rows += rows
        except Exception as exc:
            errors += 1
            if on_error:
                on_error(ide, exc)
            else:
                print(f"[FSA] error {ide}: {exc}", file=sys.stderr, flush=True)

    verify = {
        "collection": "tdx.FSA",
        "estimated_documents": db.col_TDX_FSA.estimated_document_count(),
    }
    latest = db.col_TDX_FSA.find_one(sort=[("REPORTDATE", -1), ("IDE", 1)])
    if latest:
        verify["latest_doc"] = latest

    return {
        "stocks_total": len(stock_list),
        "stocks_updated": stocks_updated,
        "rows_upserted": total_rows,
        "errors": errors,
        "recent_quarters": recent_quarters,
        "ratio_fields": [field["key"] for field in RATIO_FIELDS],
        "mongodb_verify": verify,
    }
