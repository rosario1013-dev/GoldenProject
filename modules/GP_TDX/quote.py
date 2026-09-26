"""Daily quote (K-line) read from vipdoc and upload to MongoDB QUATE collection."""

from __future__ import annotations

import glob
import os
from typing import Callable

import pandas as pd
import pymongo
from pytdx.reader import TdxDailyBarReader

from .config import Config, DEFAULT_CONFIG
from .db import TdxDB, bulk_upsert_df
from .utils import describe_upload_scope, filter_by_date

COLLECTION = "QUATE"


def all_lday_files(
    vipdoc_path: str | None = None,
    *,
    config: Config | None = None,
    ides: list[str] | None = None,
) -> list[str]:
    cfg = config or DEFAULT_CONFIG
    vipdoc_path = vipdoc_path or cfg.vipdoc_path
    files: list[str] = []
    for market in ("sh", "sz", "bj"):
        pattern = os.path.join(vipdoc_path, market, "lday", "*.day")
        files.extend(glob.glob(pattern))
    files = sorted(files)
    if ides is not None:
        ide_set = set(ides)
        files = [f for f in files if os.path.basename(f).split(".")[0] in ide_set]
    return files


def read_lday_file(filepath: str) -> pd.DataFrame:
    """Read one .day file into a normalized quote DataFrame."""
    reader = TdxDailyBarReader()
    df = reader.get_df_by_file(filepath)
    df = df.reset_index().rename(
        columns={
            "date": "DT",
            "open": "O",
            "high": "H",
            "low": "L",
            "close": "C",
            "amount": "A",
            "volume": "V",
        }
    )
    df = df.astype({"DT": "string"})
    df["IDE"] = os.path.basename(filepath).split(".")[0]
    return df


CALENDAR_IDES = ("sh000001", "sz399001", "sz000001")


def recent_trading_dates(
    config: Config | None = None,
    *,
    n: int = 10,
) -> list[str]:
    """Infer recent trading dates from index/sample .day files."""
    if n <= 0:
        raise ValueError("n must be positive")

    cfg = config or DEFAULT_CONFIG
    for ide in CALENDAR_IDES:
        market = ide[:2]
        filepath = os.path.join(cfg.vipdoc_path, market, "lday", f"{ide}.day")
        if not os.path.isfile(filepath):
            continue
        df = read_lday_file(filepath)
        dates = sorted(df["DT"].astype(str).unique())
        if dates:
            return dates[-n:]
    raise FileNotFoundError("找不到用于推断交易日的指数/样本行情文件")


def upload_quote_file(
    filepath: str,
    db: TdxDB | None = None,
    *,
    config: Config | None = None,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    year: int | str | None = None,
) -> tuple[int, int]:
    """Read one .day file and upsert rows into QUATE. Returns (upserted, rows_read)."""
    tdx_db = db or TdxDB(config)
    df = read_lday_file(filepath)
    df = filter_by_date(df, col="DT", date=date, date_from=date_from, date_to=date_to, year=year)
    if df.empty:
        return 0, 0
    return bulk_upsert_df(tdx_db.collection(COLLECTION), df, ("IDE", "DT"), double_precision=2), len(df)


def upload_all_quotes(
    *,
    config: Config | None = None,
    db: TdxDB | None = None,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    year: int | str | None = None,
    ides: list[str] | None = None,
    on_error: Callable[[str, Exception], None] | None = None,
    show_progress: bool = True,
) -> dict[str, int | str | dict | None]:
    """Upload quotes — all history or rows matching ``date`` / range / ``year``."""
    cfg = config or DEFAULT_CONFIG
    tdx_db = db or TdxDB(cfg)

    tdx_db.ensure_index(COLLECTION, [("IDE", pymongo.ASCENDING), ("DT", pymongo.ASCENDING)])
    tdx_db.ensure_index(COLLECTION, [("DT", pymongo.ASCENDING), ("IDE", pymongo.ASCENDING)])

    files = all_lday_files(config=cfg, ides=ides)
    total_rows = 0
    rows_read = 0
    errors = 0
    filtered = any(v is not None for v in (date, date_from, date_to, year))

    iterator = files
    if show_progress:
        try:
            import tqdm

            iterator = tqdm.tqdm(files, desc="QUATE")
        except ImportError:
            pass

    for filepath in iterator:
        try:
            upserted, read_count = upload_quote_file(
                filepath,
                tdx_db,
                config=cfg,
                date=date,
                date_from=date_from,
                date_to=date_to,
                year=year,
            )
            total_rows += upserted
            rows_read += read_count
        except Exception as exc:
            errors += 1
            if on_error:
                on_error(filepath, exc)

    result = {
        "files": len(files),
        "rows_upserted": total_rows,
        "rows_read": rows_read,
        "errors": errors,
        "mongo_db": cfg.mongo_db,
    }
    result.update(
        describe_upload_scope(
            scope="filtered" if filtered or ides else "all",
            date=date,
            date_from=date_from,
            date_to=date_to,
            year=year,
            ides=ides,
        )
    )
    return result
