"""Shared helpers for IDE codes, dates, quarters, and A-share filtering."""

from __future__ import annotations

import os
import re
from typing import Literal

import pandas as pd

MARKET_MAP = {0: "sz", 1: "sh", 2: "bj"}

A_SHARE_PATTERN = re.compile(r"^(60|68|00|30|43|83|87|92)\d{4}$")

QUARTER_END_MM_DD = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}

QUARTER_PATTERN = re.compile(r"^(\d{4})Q([1-4])$", re.IGNORECASE)
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def code_to_ide(code, market: int | None = None) -> str:
    """Convert a 6-digit code to IDE (e.g. sz000001)."""
    code = str(code).zfill(6)
    if market is not None:
        prefix = MARKET_MAP.get(int(market), "sz")
        return f"{prefix}{code}"
    if code.startswith(("60", "68", "90", "91")):
        return f"sh{code}"
    if code.startswith(("43", "83", "87", "92")):
        return f"bj{code}"
    return f"sz{code}"


def ide_to_market_code(ide: str) -> tuple[int, str]:
    return {"sh": 1, "sz": 0, "bj": 2}[ide[:2]], ide[2:]


def format_report_date(report_date) -> str:
    s = str(int(report_date)).zfill(8)
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


def is_a_share_stock(ide: str) -> bool:
    if not isinstance(ide, str) or len(ide) < 8:
        return False
    return bool(A_SHARE_PATTERN.match(ide[2:]))


def parse_quarter(quarter: str) -> str:
    """Convert quarter label to report date, e.g. ``2026Q1`` → ``2026-03-31``."""
    match = QUARTER_PATTERN.match(quarter.strip().upper())
    if not match:
        raise ValueError(f"Invalid quarter {quarter!r}; use format YYYYQ1..Q4 (e.g. 2026Q1)")
    year, q = int(match.group(1)), int(match.group(2))
    return f"{year}-{QUARTER_END_MM_DD[q]}"


def normalize_report_date(value: str) -> str:
    """Accept ``2026Q1`` or ``2026-03-31`` and return ``YYYY-MM-DD``."""
    value = value.strip()
    if QUARTER_PATTERN.match(value.upper()):
        return parse_quarter(value)
    if DATE_PATTERN.match(value):
        return value
    raise ValueError(f"Invalid report date {value!r}; use YYYY-MM-DD or YYYYQ1..Q4")


def report_date_to_cw_basename(report_date: str) -> str:
    """``2026-03-31`` → ``gpcw20260331.dat``."""
    report_date = normalize_report_date(report_date)
    return f"gpcw{report_date.replace('-', '')}.dat"


def cw_filepath_for_report_date(report_date: str, cw_path: str) -> str:
    return os.path.join(cw_path, report_date_to_cw_basename(report_date))


def filter_by_year(df: pd.DataFrame, year: int | str, *, col: str = "DT") -> pd.DataFrame:
    prefix = f"{int(year)}-"
    return df[df[col].astype(str).str.startswith(prefix)].copy()


def filter_by_date(
    df: pd.DataFrame,
    *,
    col: str = "DT",
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    year: int | str | None = None,
) -> pd.DataFrame:
    """Filter a DataFrame by exact date, range, and/or calendar year."""
    if date is None and date_from is None and date_to is None and year is None:
        return df

    out = df
    series = out[col].astype(str)

    if year is not None:
        out = out[series.str.startswith(f"{int(year)}-")]

    if date is not None:
        out = out[out[col].astype(str) == date]

    if date_from is not None:
        out = out[out[col].astype(str) >= date_from]

    if date_to is not None:
        out = out[out[col].astype(str) <= date_to]

    return out.copy()


def describe_upload_scope(
    *,
    scope: Literal["all", "filtered"],
    **filters: object,
) -> dict[str, object]:
    active = {k: v for k, v in filters.items() if v is not None}
    return {"scope": scope, "filters": active or None}
