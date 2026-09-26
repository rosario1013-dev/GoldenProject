"""Financial report (CW) read from gpcw*.dat and upload to MongoDB CW collection."""

from __future__ import annotations

import glob
import os
from typing import Callable

import pandas as pd
import pymongo
from pytdx.reader import HistoryFinancialReader

from .config import Config, DEFAULT_CONFIG
from .db import TdxDB, bulk_upsert_df
from .utils import code_to_ide, cw_filepath_for_report_date, describe_upload_scope, format_report_date, normalize_report_date

COLLECTION = "CW"


def all_cw_files(cw_path: str | None = None, *, config: Config | None = None) -> list[str]:
    cfg = config or DEFAULT_CONFIG
    cw_path = cw_path or cfg.cw_path
    files = glob.glob(os.path.join(cw_path, "gpcw*.dat"))
    return sorted(f for f in files if os.path.getsize(f) > 1000)


def select_cw_files(
    *,
    cw_path: str | None = None,
    config: Config | None = None,
    report_date: str | None = None,
    quarter: str | None = None,
    recent_quarters: int | None = None,
) -> list[str]:
    """Select CW files — all quarters, recent N quarters, or one report quarter."""
    cfg = config or DEFAULT_CONFIG
    cw_path = cw_path or cfg.cw_path

    if recent_quarters is not None:
        if recent_quarters <= 0:
            raise ValueError("recent_quarters must be positive")
        files = all_cw_files(cw_path, config=cfg)
        return files[-recent_quarters:]

    if report_date is None and quarter is None:
        return all_cw_files(cw_path, config=cfg)

    target = normalize_report_date(quarter or report_date or "")
    filepath = cw_filepath_for_report_date(target, cw_path)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"CW file not found for {target}: {filepath}")
    return [filepath]


def read_cw_file(filepath: str, *, report_date: str | None = None) -> pd.DataFrame:
    """Read one gpcw*.dat file into a normalized CW DataFrame."""
    df = HistoryFinancialReader().get_df(filepath)
    df = df.reset_index().rename(columns={"code": "CODE"})
    df["REPORTDATE"] = df["report_date"].map(format_report_date)
    df = df.drop(columns=["report_date"])
    df["IDE"] = df["CODE"].map(code_to_ide)
    if report_date is not None:
        target = normalize_report_date(report_date)
        df = df[df["REPORTDATE"] == target]
    return df


def upload_cw_file(
    filepath: str,
    db: TdxDB | None = None,
    *,
    config: Config | None = None,
    report_date: str | None = None,
) -> int:
    tdx_db = db or TdxDB(config)
    df = read_cw_file(filepath, report_date=report_date)
    if df.empty:
        return 0
    return bulk_upsert_df(tdx_db.collection(COLLECTION), df, ("IDE", "REPORTDATE"))


def upload_all_cw(
    *,
    config: Config | None = None,
    db: TdxDB | None = None,
    report_date: str | None = None,
    quarter: str | None = None,
    recent_quarters: int | None = None,
    on_error: Callable[[str, Exception], None] | None = None,
    show_progress: bool = True,
) -> dict[str, int | str | dict | None]:
    """Upload CW data — all quarters, recent N quarters, or one report quarter."""
    cfg = config or DEFAULT_CONFIG
    tdx_db = db or TdxDB(cfg)

    tdx_db.ensure_index(COLLECTION, [("IDE", pymongo.ASCENDING), ("REPORTDATE", pymongo.ASCENDING)])
    tdx_db.ensure_index(COLLECTION, [("REPORTDATE", pymongo.ASCENDING), ("IDE", pymongo.ASCENDING)])

    filter_date = None
    if recent_quarters is not None:
        files = select_cw_files(config=cfg, recent_quarters=recent_quarters)
    else:
        filter_date = normalize_report_date(quarter or report_date) if (quarter or report_date) else None
        files = select_cw_files(config=cfg, report_date=filter_date, quarter=quarter)
    total_rows = 0
    errors = 0

    iterator = files
    if show_progress:
        try:
            import tqdm

            iterator = tqdm.tqdm(files, desc="CW")
        except ImportError:
            pass

    for filepath in iterator:
        try:
            total_rows += upload_cw_file(filepath, tdx_db, config=cfg, report_date=filter_date)
        except Exception as exc:
            errors += 1
            if on_error:
                on_error(filepath, exc)

    result = {
        "files": len(files),
        "rows_upserted": total_rows,
        "errors": errors,
        "mongo_db": cfg.mongo_db,
    }
    result.update(
        describe_upload_scope(
            scope="filtered" if filter_date or recent_quarters is not None else "all",
            quarter=quarter,
            report_date=filter_date,
            recent_quarters=recent_quarters,
        )
    )
    return result
