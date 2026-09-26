"""Market heatmap treemap data for dashboard / industry pages."""

from __future__ import annotations

from .connection import KDB

RETURN_KEYS = ("chg_1d", "chg_3d", "chg_5d", "chg_1m", "chg_1y")


def _parse_stock_item(item) -> dict | None:
    ide = ""
    name = ""
    if isinstance(item, str):
        ide = item
    elif isinstance(item, (list, tuple)):
        if len(item) >= 2:
            name, ide = item[0], item[1]
        elif len(item) == 1:
            ide = item[0]
    elif isinstance(item, dict):
        ide = item.get("IDE", item.get("ide", ""))
        name = item.get("IDS", item.get("name", ""))
    if not ide:
        return None
    return {"name": name or ide, "ide": ide, "abb": "", "node_type": "stock"}


def _load_stock_meta(self: KDB, ides: list[str]) -> dict[str, dict]:
    if not ides:
        return {}
    cursor = self.col_TDX_STOCK.find(
        {"IDE": {"$in": ides}},
        {"_id": 0, "IDE": 1, "IDS": 1, "ABB": 1},
    )
    return {
        doc["IDE"]: {
            "name": doc.get("IDS") or doc["IDE"],
            "abb": doc.get("ABB") or "",
        }
        for doc in cursor
        if doc.get("IDE")
    }


def _leaf_nodes(node: dict) -> list[dict]:
    children = node.get("children") or []
    if not children:
        if node.get("node_type") == "stock":
            return [node]
        return []
    leaves: list[dict] = []
    for child in children:
        leaves.extend(_leaf_nodes(child))
    return leaves


def _rollup_metrics(node: dict) -> None:
    children = node.get("children") or []
    if not children:
        if node.get("value") is None:
            node["value"] = 1.0
        return

    for child in children:
        _rollup_metrics(child)

    node["value"] = sum(float(child.get("value") or 0) for child in children)
    for key in RETURN_KEYS:
        total_w = 0.0
        weighted = 0.0
        for child in children:
            chg = child.get(key)
            weight = float(child.get("value") or 0)
            if chg is None or weight <= 0:
                continue
            total_w += weight
            weighted += float(chg) * weight
        node[key] = round(weighted / total_w, 2) if total_w > 0 else None


def _sector_node(doc: dict) -> dict:
    return {
        "name": doc.get("IDS") or "",
        "ide": doc.get("IDE") or "",
        "node_type": "sector",
        "children": [],
    }


def _build_subtree(doc: dict, hy_by_name: dict[str, dict]) -> dict | None:
    children_entries = doc.get("children") or []
    if children_entries:
        root = _sector_node(doc)
        for entry in children_entries:
            child_name = entry[0] if isinstance(entry, (list, tuple)) else entry
            child_doc = hy_by_name.get(child_name)
            if not child_doc:
                continue
            child_node = _sector_node(child_doc)
            for item in child_doc.get("stocks") or []:
                stock = _parse_stock_item(item)
                if stock:
                    child_node["children"].append(stock)
            if child_node["children"]:
                root["children"].append(child_node)
        return root if root["children"] else None

    stocks = doc.get("stocks") or []
    if not stocks:
        return None
    root = _sector_node(doc)
    for item in stocks:
        stock = _parse_stock_item(item)
        if stock:
            root["children"].append(stock)
    return root if root["children"] else None


def market_heatmap_tree(self: KDB, sector: str | None = None) -> dict:
    """Build nested treemap tree: HY1 -> HY2 -> stocks (or sector -> stocks).

    Leaf ``value`` uses latest turnover (``A``) as size weight; sector nodes roll up.
    """
    all_docs = list(
        self.col_TDX_BKHY.find(
            {},
            {"_id": 0, "IDS": 1, "IDE": 1, "L": 1, "code": 1, "children": 1, "stocks": 1},
        )
    )
    hy_by_name = {doc["IDS"]: doc for doc in all_docs if doc.get("IDS")}

    if sector and sector not in {"全部行业", "市场"}:
        doc = hy_by_name.get(sector)
        if not doc:
            return {"name": sector, "node_type": "root", "children": [], "stock_count": 0}
        tree = _build_subtree(doc, hy_by_name)
        if not tree:
            return {"name": sector, "node_type": "root", "children": [], "stock_count": 0}
        root = {"name": sector, "node_type": "root", "children": [tree]}
    else:
        l1_docs = sorted(
            [doc for doc in all_docs if str(doc.get("L") or "") == "1"],
            key=lambda row: row.get("code") or row.get("IDS") or "",
        )
        root = {"name": "市场", "node_type": "root", "children": []}
        for l1 in l1_docs:
            l1_name = l1.get("IDS") or ""
            l1_node = _sector_node(l1)
            for entry in l1.get("children") or []:
                child_name = entry[0] if isinstance(entry, (list, tuple)) else entry
                child_doc = hy_by_name.get(child_name)
                if not child_doc:
                    continue
                child_node = _sector_node(child_doc)
                for item in child_doc.get("stocks") or []:
                    stock = _parse_stock_item(item)
                    if stock:
                        child_node["children"].append(stock)
                if child_node["children"]:
                    l1_node["children"].append(child_node)
            if l1_node["children"]:
                root["children"].append(l1_node)

    leaves = _leaf_nodes(root)
    ides = [leaf["ide"] for leaf in leaves if leaf.get("ide")]
    meta = _load_stock_meta(self, ides)
    returns = self.returns_for_ides(ides) if ides else {}
    amounts = self.latest_amount_for_ides(ides) if hasattr(self, "latest_amount_for_ides") and ides else {}

    for leaf in leaves:
        ide = leaf.get("ide")
        info = meta.get(ide) or {}
        if info.get("name"):
            leaf["name"] = info["name"]
        leaf["abb"] = info.get("abb") or ""
        chg = returns.get(ide) or {}
        for key in RETURN_KEYS:
            leaf[key] = chg.get(key)
        leaf["value"] = float(amounts.get(ide) or 1.0)

    _rollup_metrics(root)
    return {
        **root,
        "stock_count": len(leaves),
    }


KDB.market_heatmap_tree = market_heatmap_tree
