"""Build STOCK classification fields from local TDX hq_cache (ABB/DQ/HY*).

Does not touch BK_GN / BK_FG / index — those stay as already stored in MongoDB.
"""

from __future__ import annotations

import os
from pathlib import Path

from dbfread import DBF
from pypinyin import Style, lazy_pinyin

from .config import Config, DEFAULT_CONFIG

MARKET_PREFIX = {"0": "sz", "1": "sh", "2": "bj"}

# Fields refreshed from local TDX cache on STOCK upsert.
STOCK_META_FIELDS = ("ABB", "DQ", "HY1", "HY2", "HY3", "ID6", "IDS", "market")

# Preserved on update (never written by this module).
STOCK_PRESERVE_FIELDS = ("BK_GN", "BK_FG", "index", "oldIDE")


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    for encoding in ("gbk", "gb18030", "utf-8"):
        try:
            return path.read_text(encoding=encoding, errors="strict").splitlines()
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="gbk", errors="replace").splitlines()


def normalize_stock_code(value) -> str:
    code = str(value).strip()
    if code.endswith(".0"):
        code = code[:-2]
    return code.zfill(6)


def to_abb(name: str) -> str:
    """深圳新星 -> SZXX"""
    letters: list[str] = []
    for ch in name or "":
        if "\u4e00" <= ch <= "\u9fff":
            letters.extend(lazy_pinyin(ch, style=Style.FIRST_LETTER))
        elif ch.isalpha():
            letters.append(ch)
    return "".join(letters).upper()


def short_region_name(name: str) -> str:
    for suffix in ("特区", "板块"):
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
    return name


def _hq_cache(config: Config | None = None) -> Path:
    cfg = config or DEFAULT_CONFIG
    return Path(cfg.hq_cache_path)


def load_research_industry_defs(hq_cache: Path) -> dict[str, tuple[str, str]]:
    """X-code -> (name, block_code) from tdxzs category 12."""
    result: dict[str, tuple[str, str]] = {}
    for filename in ("tdxzs3.cfg", "tdxzs.cfg"):
        for line in _read_lines(hq_cache / filename):
            parts = line.strip().split("|")
            if len(parts) < 6 or parts[2].strip() != "12":
                continue
            name = parts[0].strip()
            block_code = parts[1].strip()
            internal = parts[5].strip()
            if name and internal and internal not in result:
                result[internal] = (name, block_code)
    return result


def load_region_defs(hq_cache: Path) -> dict[str, tuple[str, str]]:
    """DY code -> (name, block_code) from tdxzs category 3."""
    regions: dict[str, tuple[str, str]] = {}
    for filename in ("tdxzs3.cfg", "tdxzs.cfg"):
        for line in _read_lines(hq_cache / filename):
            parts = line.strip().split("|")
            if len(parts) < 6 or parts[2].strip() != "3":
                continue
            name = parts[0].strip()
            block_code = parts[1].strip()
            region_code = parts[5].strip()
            if region_code and region_code not in regions:
                regions[region_code] = (name, block_code)
    return regions


def load_stock_dy(hq_cache: Path) -> dict[str, str]:
    """stock code -> DY region number from base.dbf."""
    path = hq_cache / "base.dbf"
    if not path.exists():
        return {}
    mapping: dict[str, str] = {}
    table = DBF(str(path), encoding="gbk", ignore_missing_memofile=True)
    for rec in table:
        code = normalize_stock_code(rec.get("GPDM") or "")
        dy = str(rec.get("DY") or "").strip()
        if code and dy:
            mapping[code] = dy
    return mapping


def load_research_codes(hq_cache: Path) -> dict[str, str]:
    """stock code -> research industry X-code from tdxhy.cfg."""
    path = hq_cache / "tdxhy.cfg"
    if not path.exists():
        raise FileNotFoundError(f"Missing tdxhy.cfg: {path}")
    mapping: dict[str, str] = {}
    for line in _read_lines(path):
        parts = line.strip().split("|")
        if len(parts) < 3:
            continue
        code = normalize_stock_code(parts[1])
        research = parts[5].strip() if len(parts) >= 6 else ""
        if code and research:
            mapping[code] = research
    return mapping


def _industry_levels(definitions: dict[str, tuple[str, str]]) -> dict[str, int]:
    return {
        code: sum(1 for parent in definitions if code.startswith(parent))
        for code in definitions
    }


def hy_arrays_for_code(
    research_code: str,
    definitions: dict[str, tuple[str, str]],
    levels: dict[str, int],
) -> dict[str, list[str]]:
    """Build HY1/HY2/HY3 as [name, sh{block}, X-code]."""
    if not research_code:
        return {}
    by_level: dict[int, list[tuple[str, str, str]]] = {}
    for internal, (name, block_code) in definitions.items():
        if not research_code.startswith(internal):
            continue
        level = levels[internal]
        by_level.setdefault(level, []).append((name, block_code, internal))

    result: dict[str, list[str]] = {}
    for level in (1, 2, 3):
        items = by_level.get(level)
        if not items:
            continue
        # Prefer shortest internal code at this level (canonical parent).
        name, block_code, internal = sorted(items, key=lambda x: len(x[2]))[0]
        result[f"HY{level}"] = [name, f"sh{block_code}", internal]
    return result


class StockMetaBuilder:
    """Load TDX hq_cache once, then enrich A-share rows with ABB/DQ/HY*."""

    def __init__(self, config: Config | None = None):
        self.config = config or DEFAULT_CONFIG
        hq = _hq_cache(self.config)
        self.industry_defs = load_research_industry_defs(hq)
        self.industry_levels = _industry_levels(self.industry_defs)
        self.region_defs = load_region_defs(hq)
        self.stock_dy = load_stock_dy(hq)
        self.research_codes = load_research_codes(hq)

    def dq_for(self, code: str) -> list[str] | None:
        region_code = self.stock_dy.get(normalize_stock_code(code))
        if not region_code:
            return None
        region = self.region_defs.get(region_code)
        if not region:
            return [region_code]
        name, block_code = region
        return [short_region_name(name), f"sh{block_code}", region_code]

    def enrich_record(self, *, ide: str, code: str, ids: str, market: str) -> dict:
        """Return STOCK fields suitable for upsert (no BK_GN/BK_FG/index)."""
        code = normalize_stock_code(code)
        record: dict = {
            "IDE": ide,
            "ABB": to_abb(ids),
            "DQ": self.dq_for(code),
            "ID6": code,
            "IDS": ids,
            "market": market,
        }
        record.update(
            hy_arrays_for_code(
                self.research_codes.get(code, ""),
                self.industry_defs,
                self.industry_levels,
            )
        )
        return record

    def enrich_stock_df_records(self, stock_df) -> list[dict]:
        records = []
        for row in stock_df[["IDE", "code", "IDS", "market"]].dropna(subset=["IDS"]).to_dict("records"):
            records.append(
                self.enrich_record(
                    ide=row["IDE"],
                    code=row["code"],
                    ids=row["IDS"],
                    market=row["market"],
                )
            )
        return records
