"""Sync East Money research + periodic filing metadata (and optional PDFs)."""

from __future__ import annotations

from typing import Any, Callable

from .config import COL_FILING, COL_RESEARCH, Config, DEFAULT_CONFIG
from .filings import iter_filings
from .research import iter_research_reports
from .store import (
    EmDB,
    bulk_upsert,
    download_missing_pdfs,
    filing_local_path,
    research_local_path,
)

ErrorCallback = Callable[[str, Exception], None]


def _resolve_kind(kind: str | None) -> str:
    key = (kind or "all").strip().lower()
    if key in {"all", "research", "filings", "dg", "report"}:
        if key == "dg":
            return "research"
        if key == "report":
            return "filings"
        return key
    raise ValueError(f"Unknown kind: {kind}. Use all|research|filings")


def upload_reports(
    *,
    config: Config | None = None,
    kind: str = "all",
    download_pdf: bool = False,
    begin_time: str | None = None,
    end_time: str | None = None,
    max_pages: int | None = None,
    stock_list: str | None = None,
    pdf_limit: int | None = None,
    on_error: ErrorCallback | None = None,
    show_progress: bool = True,
) -> dict[str, Any]:
    """
    Sync report metadata into MongoDB; optionally download PDFs locally.

    - kind: all | research | filings
    - download_pdf=False: metadata only (online browse via pdf_url)
    - download_pdf=True: also save PDFs under config.pdf_root and set local_path
    """
    cfg = config or DEFAULT_CONFIG
    if begin_time or end_time:
        cfg = Config(
            mongo_uri=cfg.mongo_uri,
            mongo_db=cfg.mongo_db,
            pdf_root=cfg.pdf_root,
            begin_time=begin_time or cfg.begin_time,
            end_time=end_time or cfg.end_time,
            research_page_size=cfg.research_page_size,
            filing_page_size=cfg.filing_page_size,
            request_timeout=cfg.request_timeout,
        )

    resolved = _resolve_kind(kind)
    db = EmDB(cfg)
    result: dict[str, Any] = {
        "kind": resolved,
        "download_pdf": bool(download_pdf),
        "pdf_root": cfg.pdf_root,
        "begin_time": cfg.begin_time,
        "end_time": cfg.end_time,
        "max_pages": max_pages,
        "mongo_db": cfg.mongo_db,
        "collections": {},
    }

    try:
        db.ensure_indexes()

        if resolved in {"all", "research"}:
            print("[GP_EM] sync research metadata…", flush=True)
            research_rows = list(
                iter_research_reports(config=cfg, max_pages=max_pages)
            )
            stats = bulk_upsert(db.collection(COL_RESEARCH), research_rows, "infoCode")
            result["collections"][COL_RESEARCH] = {
                "fetched": len(research_rows),
                **stats,
            }
            print(
                f"[GP_EM] research fetched={len(research_rows)} "
                f"upserted={stats['upserted']} modified={stats['modified']}",
                flush=True,
            )

        if resolved in {"all", "filings"}:
            print("[GP_EM] sync filing metadata…", flush=True)
            filing_rows = list(
                iter_filings(config=cfg, max_pages=max_pages, stock_list=stock_list)
            )
            stats = bulk_upsert(db.collection(COL_FILING), filing_rows, "art_code")
            result["collections"][COL_FILING] = {
                "fetched": len(filing_rows),
                **stats,
            }
            print(
                f"[GP_EM] filings fetched={len(filing_rows)} "
                f"upserted={stats['upserted']} modified={stats['modified']}",
                flush=True,
            )

        if download_pdf:
            pdf_stats: dict[str, Any] = {}
            if resolved in {"all", "research"}:

                def research_path(doc: dict[str, Any]) -> str:
                    return research_local_path(
                        cfg, doc["infoCode"], doc.get("columnType")
                    )

                print("[GP_EM] download research PDFs…", flush=True)
                pdf_stats[COL_RESEARCH] = download_missing_pdfs(
                    db.collection(COL_RESEARCH),
                    id_field="infoCode",
                    path_builder=research_path,
                    timeout=cfg.request_timeout,
                    limit=pdf_limit,
                    on_error=on_error,
                    show_progress=show_progress,
                )

            if resolved in {"all", "filings"}:

                def filing_path(doc: dict[str, Any]) -> str:
                    return filing_local_path(cfg, doc["art_code"])

                print("[GP_EM] download filing PDFs…", flush=True)
                pdf_stats[COL_FILING] = download_missing_pdfs(
                    db.collection(COL_FILING),
                    id_field="art_code",
                    path_builder=filing_path,
                    timeout=cfg.request_timeout,
                    limit=pdf_limit,
                    on_error=on_error,
                    show_progress=show_progress,
                )
            result["pdf"] = pdf_stats

        return result
    finally:
        db.close()
