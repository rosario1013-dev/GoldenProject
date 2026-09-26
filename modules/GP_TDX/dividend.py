"""GBBQ dividend / capital-change data: readjust and upload to FHZGB + STOCK_PKVZGB."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pymongo
from pytdx.reader import GbbqReader

from .config import Config, DEFAULT_CONFIG
from .db import TdxDB, bulk_upsert_df
from .utils import code_to_ide, describe_upload_scope, filter_by_year, is_a_share_stock

COL_FHZGB = "FHZGB"
COL_PKVZGB = "STOCK_PKVZGB"

GBBQ_CAT_DICT = {
    "1": "除权除息",
    "2": "送配股上市",
    "3": "非流通股上市",
    "4": "未知股本变动",
    "5": "股本变化",
    "6": "增发新股",
    "7": "股份回购",
    "8": "增发新股上市",
    "9": "转配股上市",
    "10": "可转债上市",
    "12": "非流通股缩股",
    "13": "送认购权证",
    "14": "送认沽权证",
}


def load_gbbq(path: str | None = None, *, config: Config | None = None) -> pd.DataFrame:
    cfg = config or DEFAULT_CONFIG
    path = path or cfg.gbbq_path
    if not os.path.isfile(path):
        raise FileNotFoundError(f"gbbq file not found: {path}")

    raw = GbbqReader().get_df(path).astype({"datetime": "string"})
    df = raw.rename(
        columns={
            "market": "MK",
            "code": "ID6",
            "datetime": "DT",
        }
    )
    df["DT"] = df["DT"].str[:4] + "-" + df["DT"].str[4:6] + "-" + df["DT"].str[6:]
    df["IDE"] = df.apply(lambda r: code_to_ide(r["ID6"], r["MK"]), axis=1)
    return df[
        [
            "IDE",
            "DT",
            "category",
            "hongli_panqianliutong",
            "peigujia_qianzongguben",
            "songgu_qianzongguben",
            "peigu_houzongguben",
        ]
    ].sort_values(["IDE", "DT", "category"]).reset_index(drop=True)


def readjust(df: pd.DataFrame) -> pd.DataFrame:
    """Process GBBQ records for one stock (logic from TDX02_GBBQ / import_dividend_per_share)."""
    if df.empty:
        return pd.DataFrame()

    ide = df.iloc[0]["IDE"]
    if not is_a_share_stock(ide):
        return pd.DataFrame()

    result = []
    pre = {"后流通股": 0, "后总股本": 0, "DT": "1900-01-01"}

    for _, d in df.iterrows():
        ans = {
            "IDE": d["IDE"],
            "DT": d["DT"],
            "类别": GBBQ_CAT_DICT.get(str(d["category"]), "-"),
        }
        ans["前流通股"] = pre["后流通股"]
        ans["前总股本"] = pre["后总股本"]

        if ans["类别"] == "除权除息":
            ans["配股"] = round(float(d["peigu_houzongguben"]), 1)
            ans["配股价"] = round(float(d["peigujia_qianzongguben"]), 3)
            ans["送转股"] = round(float(d["songgu_qianzongguben"]), 1)
            ans["分红"] = round(float(d["hongli_panqianliutong"]), 3)
            ans["P"] = (10 + ans["送转股"] + ans["配股"]) / 10
            ans["后流通股"] = ans["前流通股"] * ans["P"]
            ans["后总股本"] = ans["前总股本"] * ans["P"]
        else:
            ans["前流通股"] = round(float(d["hongli_panqianliutong"]), 1)
            ans["后流通股"] = round(float(d["songgu_qianzongguben"]), 1)
            ans["流通股变动"] = ans["后流通股"] - ans["前流通股"]
            ans["前总股本"] = round(float(d["peigujia_qianzongguben"]), 1)
            ans["后总股本"] = round(float(d["peigu_houzongguben"]), 1)
            ans["总股本变动"] = ans["后总股本"] - ans["前总股本"]

            if ans["类别"] in ["送配股上市", "转配股上市"]:
                try:
                    ans["流通股变动p"] = ans["后流通股"] / ans["前流通股"]
                    ans["总股本变动p"] = ans["后总股本"] / ans["前总股本"]
                except Exception:
                    pass
                if pre["DT"] == ans["DT"] and pre["类别"] == "除权除息":
                    ans["类别"] = [pre["类别"], ans["类别"]]
                    ans["配股"] = pre["配股"]
                    ans["配股价"] = pre["配股价"]
                    ans["送转股"] = pre["送转股"]
                    ans["分红"] = pre["分红"]
                    ans["P"] = pre["P"]
                    ans["dif"] = (ans["后总股本"] - pre["后总股本"]) / ans["后总股本"]
                    result.remove(pre)

            elif ans["类别"] == "股本变化":
                if ans["总股本变动"] > 0 and ans["前总股本"] > 0:
                    ans["P"] = ans["后总股本"] / ans["前总股本"]
                    ans["dif"] = (ans["后总股本"] - pre["后总股本"]) / ans["后总股本"]

        if ans["后总股本"] not in [np.nan, 0]:
            if "流通股变动p" not in ans:
                ans["流通股变动p"] = np.nan
                ans["总股本变动p"] = np.nan
                ans["dif"] = np.nan
            result.append(ans)
            pre = ans

    new_df = pd.DataFrame(result)

    for col in ("送转股", "分红", "P", "配股", "配股价"):
        if col not in new_df:
            new_df[col] = np.nan

    for col in ("流通股变动p", "总股本变动p", "dif"):
        if col not in new_df:
            new_df[col] = np.nan

    new_df = new_df.rename(
        columns={
            "类别": "CAT",
            "送转股": "SZZBL",
            "分红": "XJBL",
            "配股": "PGBL",
            "配股价": "PGJ",
            "后流通股": "LTG",
            "流通股变动": "LTG_D",
            "后总股本": "ZGB",
            "总股本变动p": "ZGB_D",
        }
    )

    cols = ["IDE", "DT", "CAT", "P", "SZZBL", "XJBL", "PGBL", "PGJ", "LTG_D", "LTG", "ZGB_D", "ZGB"]
    if "dif" in new_df.columns:
        cols.append("dif")
    return new_df[cols]


def add_pkv(df: pd.DataFrame) -> pd.DataFrame:
    """Add init row and cumulative adjustment factor PKV."""
    if df.empty:
        return df

    first = {
        "IDE": df.iloc[0]["IDE"],
        "DT": "1990-01-01",
        "CAT": "init",
        "P": 1,
        "ZGB": 0,
        "PKV": 1,
    }
    out = pd.concat([pd.DataFrame([first]), df], ignore_index=True)
    out = out.sort_values("DT", ascending=True).reset_index(drop=True)
    out["PKV"] = out["P"].fillna(1).cumprod()
    return out


def process_all_gbbq(gbbq_df: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for _, chunk in gbbq_df.groupby("IDE", sort=True):
        adjusted = readjust(chunk.reset_index(drop=True))
        if not adjusted.empty:
            parts.append(add_pkv(adjusted))
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def extract_dividend_df(fhzgb_df: pd.DataFrame) -> pd.DataFrame:
    """Extract ex-dividend records with per-share dividend."""
    is_xdxr = fhzgb_df["CAT"].apply(
        lambda x: x == "除权除息" or (isinstance(x, list) and "除权除息" in x)
    )
    dividend_df = fhzgb_df.loc[
        is_xdxr, ["IDE", "DT", "CAT", "XJBL", "SZZBL", "PGBL", "PGJ", "P", "PKV", "ZGB"]
    ].copy()
    return dividend_df.rename(columns={"XJBL": "dividend_per_share", "DT": "ex_date"}).sort_values(
        ["IDE", "ex_date"]
    ).reset_index(drop=True)


def upload_dividend(
    *,
    config: Config | None = None,
    db: TdxDB | None = None,
    gbbq_path: str | None = None,
    year: int | str | None = None,
) -> dict[str, int | str | dict | None]:
    """Process gbbq, then upload FHZGB and STOCK_PKVZGB to MongoDB.

    Full history is always processed so PKV stays correct; ``year`` limits which
    rows are written to MongoDB.
    """
    cfg = config or DEFAULT_CONFIG
    tdx_db = db or TdxDB(cfg)

    tdx_db.ensure_index(COL_FHZGB, [("IDE", pymongo.ASCENDING), ("DT", pymongo.ASCENDING)])

    gbbq_df = load_gbbq(gbbq_path, config=cfg)
    fhzgb_df = process_all_gbbq(gbbq_df)

    if year is not None:
        fhzgb_df = filter_by_year(fhzgb_df, year, col="DT")

    fhzgb_rows = bulk_upsert_df(tdx_db.collection(COL_FHZGB), fhzgb_df, ("IDE", "DT"))

    pkv_df = fhzgb_df[["IDE", "DT", "P", "PKV", "ZGB"]].copy()
    pkv_rows = bulk_upsert_df(tdx_db.collection(COL_PKVZGB), pkv_df, ("IDE", "DT"))

    dividend_df = extract_dividend_df(fhzgb_df)
    result = {
        "gbbq_records": len(gbbq_df),
        "fhzgb_records": len(fhzgb_df),
        "fhzgb_upserted": fhzgb_rows,
        "pkvzgb_upserted": pkv_rows,
        "dividend_records": len(dividend_df),
    }
    result.update(
        describe_upload_scope(
            scope="filtered" if year is not None else "all",
            year=year,
        )
    )
    return result
