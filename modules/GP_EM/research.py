"""East Money industry / research report list (研报 DG)."""

from __future__ import annotations

from typing import Any, Iterator

from .config import Config, DEFAULT_CONFIG
from .http import build_url, fetch
from .store import research_pdf_url


def _research_list_url(page_no: int, *, config: Config) -> str:
    return build_url(
        "http://reportapi.eastmoney.com/report/dg",
        {
            "pageNo": page_no,
            "pageSize": config.research_page_size,
            "endTime": config.end_time or "2050-12-31",
            "beginTime": config.begin_time,
        },
    )


def fetch_research_page(page_no: int = 1, *, config: Config | None = None) -> dict[str, Any]:
    cfg = config or DEFAULT_CONFIG
    payload = fetch(_research_list_url(page_no, config=cfg), timeout=cfg.request_timeout).json()
    if not isinstance(payload, dict):
        return {"hits": 0, "data": []}
    return payload


def research_total_hits(*, config: Config | None = None) -> int:
    payload = fetch_research_page(1, config=config)
    try:
        return int(payload.get("hits") or 0)
    except (TypeError, ValueError):
        return 0


def normalize_research_item(item: dict[str, Any]) -> dict[str, Any] | None:
    info_code = str(item.get("infoCode") or "").strip()
    if not info_code:
        return None
    column_type = item.get("columnType") or item.get("column_type") or ""
    title = item.get("title") or item.get("title_ch") or ""
    publish = (
        item.get("publishDate")
        or item.get("publishTime")
        or item.get("datetime")
        or item.get("createTime")
        or ""
    )
    author = item.get("author")
    if author is None:
        author = []

    return {
        "infoCode": info_code,
        "title": title,
        "columnType": column_type,
        "column": item.get("column") or "",
        "reportType": item.get("reportType"),
        "publishDate": str(publish)[:19] if publish else "",
        "orgName": item.get("orgName") or "",
        "orgSName": item.get("orgSName") or "",
        "orgCode": item.get("orgCode") or "",
        "orgType": item.get("orgType") or "",
        "author": author,
        "stockCode": item.get("stockCode") or "",
        "stockName": item.get("stockName") or "",
        "market": item.get("market") or "",
        "industryCode": item.get("industryCode") or "",
        "industryName": item.get("industryName") or item.get("industry") or "",
        "pdf_url": research_pdf_url(info_code),
        "source": "eastmoney_dg",
    }


def iter_research_reports(
    *,
    config: Config | None = None,
    max_pages: int | None = None,
) -> Iterator[dict[str, Any]]:
    cfg = config or DEFAULT_CONFIG
    page = 1
    while True:
        if max_pages is not None and page > max_pages:
            break
        payload = fetch_research_page(page, config=cfg)
        rows = payload.get("data") or []
        if not rows:
            break
        for item in rows:
            if not isinstance(item, dict):
                continue
            normalized = normalize_research_item(item)
            if normalized:
                yield normalized
        if len(rows) < cfg.research_page_size:
            break
        page += 1
