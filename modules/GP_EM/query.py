"""Query research / filing reports for a stock IDE."""

from __future__ import annotations

from typing import Any

from .config import COL_FILING, COL_RESEARCH, Config, DEFAULT_CONFIG
from .store import EmDB


def ide_to_stock_code(ide: str) -> str:
    text = str(ide or "").strip()
    if len(text) >= 8 and text[:2].lower() in {"sh", "sz", "bj"}:
        return text[2:8]
    if text.isdigit() and len(text) == 6:
        return text
    return text[-6:] if len(text) >= 6 else text


def _serialize_research(doc: dict[str, Any]) -> dict[str, Any]:
    authors = doc.get("author") or []
    if isinstance(authors, str):
        author_text = authors
    elif isinstance(authors, list):
        names = []
        for item in authors:
            s = str(item)
            names.append(s.split(".", 1)[-1] if "." in s else s)
        author_text = "、".join(names)
    else:
        author_text = ""

    return {
        "id": doc.get("infoCode") or "",
        "kind": "research",
        "title": doc.get("title") or "",
        "date": str(doc.get("publishDate") or "")[:10],
        "column_type": doc.get("columnType") or "",
        "org": doc.get("orgSName") or doc.get("orgName") or "",
        "author": author_text,
        "stock_code": doc.get("stockCode") or "",
        "stock_name": doc.get("stockName") or "",
        "pdf_url": doc.get("pdf_url") or "",
        "local_path": doc.get("local_path") or "",
        "has_local": bool(doc.get("local_path")),
    }


def _serialize_filing(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": doc.get("art_code") or "",
        "kind": "filing",
        "title": doc.get("title") or "",
        "date": str(doc.get("notice_date") or "")[:10],
        "column_code": doc.get("column_code") or "",
        "column_name": doc.get("column_name") or "",
        "pdf_url": doc.get("pdf_url") or "",
        "local_path": doc.get("local_path") or "",
        "has_local": bool(doc.get("local_path")),
    }


def list_stock_reports(
    ide: str,
    *,
    config: Config | None = None,
    research_limit: int = 50,
    filing_limit: int = 50,
) -> dict[str, Any]:
    cfg = config or DEFAULT_CONFIG
    stock_code = ide_to_stock_code(ide)
    db = EmDB(cfg)
    try:
        db.ensure_indexes()
        research_docs = list(
            db.collection(COL_RESEARCH)
            .find({"stockCode": stock_code}, {"_id": 0})
            .sort([("publishDate", -1)])
            .limit(max(1, int(research_limit)))
        )
        filing_docs = list(
            db.collection(COL_FILING)
            .find({"IDE": ide}, {"_id": 0})
            .sort([("notice_date", -1)])
            .limit(max(1, int(filing_limit)))
        )
        research = [_serialize_research(doc) for doc in research_docs]
        filings = [_serialize_filing(doc) for doc in filing_docs]
        return {
            "ide": ide,
            "stock_code": stock_code,
            "research": research,
            "filings": filings,
            "research_count": len(research),
            "filing_count": len(filings),
        }
    finally:
        db.close()
