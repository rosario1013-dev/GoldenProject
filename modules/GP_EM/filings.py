"""East Money company periodic filings (年报/半年报/季报)."""

from __future__ import annotations

from typing import Any, Iterator

from .config import (
    DEFAULT_CONFIG,
    FILING_COLUMN_CODES,
    FILING_COLUMN_LABELS,
    Config,
)
from .http import build_url, fetch
from .store import filing_pdf_url


def market_code_to_ide(stock_code: str, market_code: str | int | None) -> str:
    code = str(stock_code or "").strip()
    if not code:
        return ""
    mk = str(market_code if market_code is not None else "").strip()
    # Eastmoney: 1=SH, 0=SZ (also CYB/KCB via stock_code prefix)
    if mk == "1" or code.startswith(("6", "9")):
        return f"sh{code}"
    if mk == "0" or code.startswith(("0", "3")):
        return f"sz{code}"
    if code.startswith(("4", "8")):
        return f"bj{code}"
    return code


def _filing_list_url(page_index: int, *, config: Config, stock_list: str | None = None) -> str:
    params: dict[str, Any] = {
        "sr": -1,
        "page_size": config.filing_page_size,
        "page_index": page_index,
        "ann_type": "A",
        "f_node": 1,
        "s_node": 1,
    }
    if stock_list:
        params["stock_list"] = stock_list
    return build_url("https://np-anotice-stock.eastmoney.com/api/security/ann", params)


def fetch_filing_page(
    page_index: int = 1,
    *,
    config: Config | None = None,
    stock_list: str | None = None,
) -> list[dict[str, Any]]:
    cfg = config or DEFAULT_CONFIG
    payload = fetch(
        _filing_list_url(page_index, config=cfg, stock_list=stock_list),
        timeout=cfg.request_timeout,
    ).json()
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return []
    rows = data.get("list") or []
    return rows if isinstance(rows, list) else []


def _primary_column(item: dict[str, Any]) -> tuple[str, str]:
    columns = item.get("columns") or []
    if not columns or not isinstance(columns, list):
        return "", ""
    first = columns[0] if isinstance(columns[0], dict) else {}
    code = str(first.get("column_code") or "").strip()
    name = str(first.get("column_name") or FILING_COLUMN_LABELS.get(code, "")).strip()
    return code, name


def _primary_stock(item: dict[str, Any]) -> tuple[str, str, str]:
    codes = item.get("codes") or []
    if not codes or not isinstance(codes, list):
        return "", "", ""
    first = codes[0] if isinstance(codes[0], dict) else {}
    stock_code = str(first.get("stock_code") or "").strip()
    market_code = first.get("market_code")
    short_name = str(first.get("short_name") or "").strip()
    return stock_code, str(market_code) if market_code is not None else "", short_name


def normalize_filing_item(item: dict[str, Any]) -> dict[str, Any] | None:
    art_code = str(item.get("art_code") or "").strip()
    if not art_code:
        return None
    column_code, column_name = _primary_column(item)
    if column_code not in FILING_COLUMN_CODES:
        return None

    stock_code, market_code, short_name = _primary_stock(item)
    ide = market_code_to_ide(stock_code, market_code)
    title = item.get("title_ch") or item.get("title") or ""
    notice_date = str(item.get("notice_date") or item.get("display_time") or "")[:19]

    return {
        "art_code": art_code,
        "IDE": ide,
        "ID6": stock_code,
        "name": short_name,
        "title": title,
        "column_code": column_code,
        "column_name": column_name or FILING_COLUMN_LABELS.get(column_code, ""),
        "notice_date": notice_date,
        "pdf_url": filing_pdf_url(art_code),
        "source": "eastmoney_ann",
    }


def iter_filings(
    *,
    config: Config | None = None,
    max_pages: int | None = None,
    stock_list: str | None = None,
) -> Iterator[dict[str, Any]]:
    cfg = config or DEFAULT_CONFIG
    page = 1
    while True:
        if max_pages is not None and page > max_pages:
            break
        rows = fetch_filing_page(page, config=cfg, stock_list=stock_list)
        if not rows:
            break
        for item in rows:
            if not isinstance(item, dict):
                continue
            normalized = normalize_filing_item(item)
            if normalized:
                yield normalized
        if len(rows) < cfg.filing_page_size:
            break
        page += 1
