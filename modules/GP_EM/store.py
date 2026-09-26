"""Mongo helpers and PDF download for EM reports."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

import pymongo
from pymongo.collection import Collection

from .config import COL_FILING, COL_RESEARCH, Config, DEFAULT_CONFIG
from .http import fetch


ErrorCallback = Callable[[str, Exception], None]


class EmDB:
    def __init__(self, config: Config | None = None):
        self.config = config or DEFAULT_CONFIG
        self._client: pymongo.MongoClient | None = None

    @property
    def client(self) -> pymongo.MongoClient:
        if self._client is None:
            self._client = pymongo.MongoClient(self.config.mongo_uri)
        return self._client

    @property
    def db(self):
        return self.client[self.config.mongo_db]

    def collection(self, name: str) -> Collection:
        return self.db[name]

    def ensure_indexes(self) -> None:
        self.collection(COL_RESEARCH).create_index([("infoCode", 1)], unique=True)
        self.collection(COL_RESEARCH).create_index([("stockCode", 1), ("publishDate", -1)])
        self.collection(COL_FILING).create_index([("art_code", 1)], unique=True)
        self.collection(COL_FILING).create_index([("IDE", 1), ("notice_date", -1)])

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def research_pdf_url(info_code: str) -> str:
    return f"http://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf"


def filing_pdf_url(art_code: str) -> str:
    return f"http://pdf.dfcfw.com/pdf/H2_{art_code}_1.pdf"


def research_local_path(config: Config, info_code: str, column_type: str | None = None) -> str:
    sub = str(column_type or "misc").strip() or "misc"
    # Windows-safe folder name
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in sub)[:80]
    return os.path.join(config.research_pdf_dir, safe, f"{info_code}.pdf")


def filing_local_path(config: Config, art_code: str) -> str:
    return os.path.join(config.filing_pdf_dir, "REPORT", f"{art_code}.pdf")


def bulk_upsert(
    collection: Collection,
    records: Iterable[dict[str, Any]],
    key_field: str,
    *,
    chunk_size: int = 500,
) -> dict[str, int]:
    upserted = 0
    modified = 0
    chunk: list[Any] = []

    def flush() -> None:
        nonlocal upserted, modified, chunk
        if not chunk:
            return
        result = collection.bulk_write(chunk, ordered=False)
        upserted += result.upserted_count
        modified += result.modified_count
        chunk = []

    for record in records:
        key = record.get(key_field)
        if not key:
            continue
        doc = dict(record)
        chunk.append(
            pymongo.UpdateOne(
                {key_field: key},
                {
                    "$set": doc,
                    "$setOnInsert": {"created_at": utc_now_iso()},
                    "$unset": {"updated_at": ""},
                },
                upsert=True,
            )
        )
        if len(chunk) >= chunk_size:
            flush()
    flush()
    return {"upserted": upserted, "modified": modified}


def download_pdf_file(
    url: str,
    dest_path: str,
    *,
    timeout: float = 60.0,
    skip_existing: bool = True,
) -> str:
    """Download PDF to dest_path. Returns status: downloaded|skipped|failed."""
    if skip_existing and os.path.isfile(dest_path) and os.path.getsize(dest_path) > 0:
        return "skipped"
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    response = fetch(url, timeout=timeout)
    content = response.content
    if not content or len(content) < 100:
        raise ValueError(f"empty or invalid PDF response ({len(content or b'')} bytes)")
    tmp_path = dest_path + ".part"
    with open(tmp_path, "wb") as fh:
        fh.write(content)
    os.replace(tmp_path, dest_path)
    return "downloaded"


def download_missing_pdfs(
    collection: Collection,
    *,
    id_field: str,
    url_field: str = "pdf_url",
    path_builder: Callable[[dict[str, Any]], str],
    timeout: float = 60.0,
    limit: int | None = None,
    on_error: ErrorCallback | None = None,
    show_progress: bool = True,
) -> dict[str, int]:
    query = {
        "$or": [
            {"local_path": {"$exists": False}},
            {"local_path": None},
            {"local_path": ""},
        ]
    }
    cursor = collection.find(query, no_cursor_timeout=True)
    if limit is not None:
        cursor = cursor.limit(int(limit))

    docs = list(cursor)
    cursor.close()

    downloaded = skipped = failed = 0
    iterator = docs
    if show_progress:
        try:
            from tqdm import tqdm

            iterator = tqdm(docs, desc=f"PDF {collection.name}", unit="file")
        except ImportError:
            pass

    for doc in iterator:
        doc_id = doc.get(id_field) or "?"
        url = doc.get(url_field)
        if not url:
            failed += 1
            continue
        dest = path_builder(doc)
        try:
            status = download_pdf_file(url, dest, timeout=timeout)
            if status == "downloaded":
                downloaded += 1
            else:
                skipped += 1
            collection.update_one(
                {id_field: doc[id_field]},
                {"$set": {"local_path": dest}, "$unset": {"updated_at": ""}},
            )
        except Exception as exc:
            failed += 1
            if on_error:
                on_error(str(doc_id), exc)

    return {"downloaded": downloaded, "skipped": skipped, "failed": failed}
