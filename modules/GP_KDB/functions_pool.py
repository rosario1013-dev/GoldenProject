"""Stock pool (后选股) — categories stored as 招商证券 custom blocks."""

from __future__ import annotations

from . import blocknew_pool
from .connection import KDB

DEFAULT_POOL_USERNAME = "pjs"
_mongo_imported = False


def _username(username: str | None) -> str:
    return (username or DEFAULT_POOL_USERNAME).strip() or DEFAULT_POOL_USERNAME


def _import_mongo_categories(self: KDB) -> None:
    """Copy Mongo pool categories that are not already custom blocks."""
    global _mongo_imported
    if _mongo_imported:
        return
    try:
        existing = set(blocknew_pool.list_categories())
        categories = {
            (doc.get("category") or "").strip()
            for doc in self.col_POOL.find({}, {"_id": 0, "category": 1})
            if (doc.get("category") or "").strip()
        }
        memberships: dict[str, set[str]] = {name: set() for name in categories}
        for doc in self.col_GOLDENSTOCK.find({}, {"_id": 0, "IDE": 1, "category": 1}):
            ide = (doc.get("IDE") or "").strip()
            if not ide:
                continue
            for name in doc.get("category") or []:
                name = (name or "").strip()
                if not name:
                    continue
                categories.add(name)
                memberships.setdefault(name, set()).add(ide)
        for name in sorted(categories):
            if name in existing:
                continue
            blocknew_pool.create_category(name)
            for ide in sorted(memberships.get(name) or []):
                try:
                    blocknew_pool.add_code(name, blocknew_pool.ide_to_code(ide))
                except ValueError:
                    continue
        _mongo_imported = True
    except Exception:
        return


def pool_list_categories(self: KDB, username: str | None = None) -> list[str]:
    _import_mongo_categories(self)
    return blocknew_pool.list_categories()


def pool_create_category(self: KDB, category: str, username: str | None = None) -> dict:
    user = _username(username)
    created = blocknew_pool.create_category(category)
    return {"username": user, "category": created["category"]}


def pool_delete_category(self: KDB, category: str, username: str | None = None) -> dict:
    user = _username(username)
    deleted = blocknew_pool.delete_category(category)
    return {"username": user, "category": (category or "").strip(), "deleted": deleted}


def pool_stock_membership(self: KDB, ide: str, username: str | None = None) -> dict:
    user = _username(username)
    _import_mongo_categories(self)
    code = ""
    try:
        code = blocknew_pool.ide_to_code(ide)
    except ValueError:
        code = ""
    categories = blocknew_pool.categories_for_code(code) if code else []
    return {
        "ide": ide,
        "username": user,
        "categories": categories,
        "all_categories": blocknew_pool.list_categories(),
    }


def pool_add_stock(
    self: KDB,
    ide: str,
    category: str,
    username: str | None = None,
) -> dict:
    user = _username(username)
    name = (category or "").strip()
    if not ide:
        raise ValueError("ide is required")
    if not name:
        raise ValueError("category is required")

    blocknew_pool.create_category(name)
    blocknew_pool.add_code(name, blocknew_pool.ide_to_code(ide))
    return pool_stock_membership(ide, user)


def pool_remove_stock(
    self: KDB,
    ide: str,
    category: str | None = None,
    username: str | None = None,
) -> dict:
    """Remove stock from one category, or from every custom block if category is None."""
    user = _username(username)
    if not ide:
        raise ValueError("ide is required")

    code = blocknew_pool.ide_to_code(ide)
    name = (category or "").strip() if category is not None else ""
    if name:
        blocknew_pool.remove_code(name, code)
    else:
        for category_name in blocknew_pool.categories_for_code(code):
            blocknew_pool.remove_code(category_name, code)
    return pool_stock_membership(ide, user)


def pool_stocks(
    self: KDB,
    category: str | None = None,
    username: str | None = None,
) -> list[dict]:
    """List pool stocks, optionally filtered by category."""
    _import_mongo_categories(self)
    name = (category or "").strip() if category else ""
    grouped = blocknew_pool.all_memberships()
    rows = []
    for code, categories in grouped.items():
        if name and name not in categories:
            continue
        ide = blocknew_pool.code_to_ide(code)
        if not ide:
            continue
        info = self.StockInfo(ide) or {}
        rows.append(
            {
                "ide": ide,
                "name": info.get("IDS") or ide,
                "categories": categories,
            }
        )
    rows.sort(key=lambda row: row["ide"])
    return rows


KDB.pool_list_categories = pool_list_categories
KDB.pool_create_category = pool_create_category
KDB.pool_delete_category = pool_delete_category
KDB.pool_stock_membership = pool_stock_membership
KDB.pool_add_stock = pool_add_stock
KDB.pool_remove_stock = pool_remove_stock
KDB.pool_stocks = pool_stocks
