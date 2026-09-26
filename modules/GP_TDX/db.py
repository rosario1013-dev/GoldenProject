"""MongoDB client and bulk upsert helpers."""

from __future__ import annotations

import json
from typing import Any, Iterable, Sequence

import pandas as pd
import pymongo
from pymongo.collection import Collection

from .config import Config, DEFAULT_CONFIG


class TdxDB:
    """MongoDB accessor for the tdx database."""

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

    def ensure_index(self, name: str, keys: Sequence[tuple[str, int]], *, unique: bool = True) -> None:
        col = self.collection(name)
        col.create_index(list(keys), unique=unique)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


def df_to_records(df: pd.DataFrame, *, double_precision: int = 4) -> list[dict[str, Any]]:
    return json.loads(df.to_json(orient="records", double_precision=double_precision))


def bulk_upsert(
    collection: Collection,
    records: Iterable[dict[str, Any]],
    key_fields: Sequence[str],
    *,
    chunk_size: int = 5000,
) -> int:
    """Upsert records in chunks. Returns total modified + upserted count."""
    total = 0
    chunk: list[dict[str, Any]] = []

    for record in records:
        chunk.append(record)
        if len(chunk) >= chunk_size:
            total += _write_chunk(collection, chunk, key_fields)
            chunk = []

    if chunk:
        total += _write_chunk(collection, chunk, key_fields)
    return total


def bulk_upsert_df(
    collection: Collection,
    df: pd.DataFrame,
    key_fields: Sequence[str],
    *,
    double_precision: int = 4,
    chunk_size: int = 5000,
) -> int:
    if df.empty:
        return 0
    records = df_to_records(df, double_precision=double_precision)
    return bulk_upsert(collection, records, key_fields, chunk_size=chunk_size)


def _write_chunk(collection: Collection, chunk: list[dict[str, Any]], key_fields: Sequence[str]) -> int:
    ops = [
        pymongo.UpdateOne(
            {k: d[k] for k in key_fields},
            {"$set": d},
            upsert=True,
        )
        for d in chunk
    ]
    result = collection.bulk_write(ops, ordered=False)
    return result.modified_count + result.upserted_count
