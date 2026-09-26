"""Shared helpers for GP_KDB."""

from __future__ import annotations

import math

log101 = math.log(1.01)


def logfcn(x: float) -> float:
    if x > 0:
        return math.log(x) / log101
    return 1.0


def logize(x: float) -> float:
    return math.log(x) / log101


def security_type(ide: str) -> str | None:
    """Classify a TDX security code (IDE) by market and type."""
    mk = ide[:2]
    code_head = ide[2:4]
    if mk == "sz":
        if code_head in ("00", "30"):
            return "stock"
        if code_head == "20":
            return "stock_b"
        if code_head == "39":
            return "index"
        if code_head in ("15", "16"):
            return "fund"
        if code_head in ("10", "11", "12", "13", "14"):
            return "bond"
    elif mk == "sh":
        if code_head in ("60", "68"):
            return "stock"
        if code_head == "90":
            return "stock_b"
        if code_head in ("00", "88", "99"):
            return "index"
        if code_head in ("50", "51"):
            return "fund"
        if code_head in ("01", "10", "11", "12", "13", "14"):
            return "bond"
    elif mk == "bj":
        if code_head in ("43", "83", "87", "92"):
            return "stock"
        if code_head in ("89", "82"):
            return "index"
    return None
