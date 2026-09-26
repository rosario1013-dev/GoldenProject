"""Persist manual advice confirmations (intent only, no brokerage)."""

from __future__ import annotations

from datetime import datetime, timezone


def ensure_advice_collection(kdb) -> None:
    if getattr(kdb, "col_AI_ADVICE", None) is not None:
        return
    if not hasattr(kdb, "SITE"):
        raise RuntimeError("KDB site database is not configured")
    kdb.col_AI_ADVICE = kdb.SITE["ai_advice"]
    kdb.col_AI_ADVICE.create_index([("username", 1), ("ts", -1)])
    kdb.col_AI_ADVICE.create_index([("IDE", 1), ("ts", -1)])


def confirm_advice(
    kdb,
    *,
    ide: str,
    action: str,
    username: str = "default",
    note: str = "",
    score: float | None = None,
    payload: dict | None = None,
) -> dict:
    action = str(action or "").strip().lower()
    if action not in {"buy", "skip"}:
        raise ValueError("action must be 'buy' or 'skip'")
    ide = str(ide or "").strip()
    if not ide:
        raise ValueError("ide is required")

    ensure_advice_collection(kdb)
    doc = {
        "IDE": ide,
        "action": action,
        "username": username or "default",
        "note": note or "",
        "score": score,
        "payload": payload or {},
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    result = kdb.col_AI_ADVICE.insert_one(doc)
    return {
        "id": str(result.inserted_id),
        "ide": ide,
        "action": action,
        "username": doc["username"],
        "ts": doc["ts"],
    }


def list_confirmations(kdb, *, username: str = "default", limit: int = 50) -> list[dict]:
    ensure_advice_collection(kdb)
    cursor = (
        kdb.col_AI_ADVICE.find({"username": username or "default"}, {"_id": 0})
        .sort([("ts", -1)])
        .limit(max(1, min(int(limit), 500)))
    )
    return list(cursor)
