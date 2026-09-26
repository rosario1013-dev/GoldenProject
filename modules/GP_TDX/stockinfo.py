"""Stock list and company profile (F10) upload to MongoDB STOCK / STOCKINFO."""

from __future__ import annotations

import glob
import os
import re
from typing import Callable, Iterable

import pandas as pd
import pymongo
from pytdx.hq import TdxHq_API

from .config import Config, DEFAULT_CONFIG
from .db import TdxDB, bulk_upsert, bulk_upsert_df
from .stock_meta import STOCK_PRESERVE_FIELDS, StockMetaBuilder
from .utils import ide_to_market_code

COL_STOCK = "STOCK"
COL_STOCKINFO = "STOCKINFO"

SEP = "\uff5c"
A_SHARE_CODE_PATTERN = re.compile(r"^(60|68|00|30|43|83|87|92)\d{4}$")


def get_local_stock_codes(vipdoc_path: str | None = None, *, config: Config | None = None) -> pd.DataFrame:
    cfg = config or DEFAULT_CONFIG
    vipdoc_path = vipdoc_path or cfg.vipdoc_path
    rows = []
    for market in ("sh", "sz", "bj"):
        pattern = os.path.join(vipdoc_path, market, "lday", "*.day")
        for file in glob.glob(pattern):
            ide = os.path.basename(file).split(".")[0]
            rows.append({"IDE": ide, "market": market, "code": ide[2:]})
    return pd.DataFrame(rows)


def _parse_ds_stk(path: str) -> dict[str, str]:
    with open(path, "rb") as f:
        data = f.read()
    name_map: dict[str, str] = {}
    i = 8
    while i < len(data) - 40:
        chunk = data[i : i + 6]
        if chunk.isdigit() and len(chunk) == 6:
            code = chunk.decode()
            name = data[i + 6 : i + 30].decode("gbk", errors="ignore").strip("\x00 ")
            if name and re.search(r"[\u4e00-\u9fff]", name):
                name_map[code] = name
            i += 6
        else:
            i += 1
    return name_map


def _parse_addedcode_bj(path: str) -> dict[str, str]:
    name_map: dict[str, str] = {}
    if not os.path.isfile(path):
        return name_map
    with open(path, encoding="gbk", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("000000") or "|" not in line:
                continue
            parts = line.split("|")
            if len(parts) >= 4 and parts[1].isdigit() and parts[2].isdigit():
                old_code, new_code = parts[1], parts[2]
                name = parts[3].split("(")[0]
                name_map[old_code] = name
                name_map[new_code] = name
    return name_map


def get_stock_names_from_pytdx(
    ip: str | None = None,
    port: int | None = None,
    *,
    config: Config | None = None,
) -> dict[str, str]:
    cfg = config or DEFAULT_CONFIG
    ip = ip or cfg.api_ip
    port = port or cfg.api_port

    api = TdxHq_API()
    if not api.connect(ip, port):
        raise ConnectionError(f"Cannot connect to TDX server {ip}:{port}")

    name_map: dict[str, str] = {}
    try:
        for market, label in [(0, "sz"), (1, "sh"), (2, "bj")]:
            count = api.get_security_count(market)
            for start in range(0, count, 1000):
                batch = api.get_security_list(market, start)
                if not batch:
                    continue
                for item in batch:
                    name_map[f"{label}{item['code']}"] = item["name"]
    finally:
        api.disconnect()
    return name_map


def get_bj_stock_names_from_local(hq_cache_path: str | None = None, *, config: Config | None = None) -> dict[str, str]:
    cfg = config or DEFAULT_CONFIG
    hq_cache_path = hq_cache_path or cfg.hq_cache_path
    ds_stk_path = os.path.join(hq_cache_path, "ds_stk.dat")
    addedcode_path = os.path.join(hq_cache_path, "addedcode_bj.cfg")
    code_name: dict[str, str] = {}
    if os.path.isfile(ds_stk_path):
        code_name.update(_parse_ds_stk(ds_stk_path))
    code_name.update(_parse_addedcode_bj(addedcode_path))
    return {f"bj{code}": name for code, name in code_name.items()}


def build_a_share_list(
    *,
    config: Config | None = None,
    vipdoc_path: str | None = None,
) -> pd.DataFrame:
    """Local A-share list with names from pytdx + BJ local cache."""
    cfg = config or DEFAULT_CONFIG
    stock_df = get_local_stock_codes(vipdoc_path, config=cfg)
    name_map = get_stock_names_from_pytdx(config=cfg)
    name_map.update(get_bj_stock_names_from_local(config=cfg))
    stock_df["IDS"] = stock_df["IDE"].map(name_map)

    a_share = stock_df[stock_df["code"].str.match(A_SHARE_CODE_PATTERN, na=False)]
    return a_share.dropna(subset=["IDS"]).reset_index(drop=True)


def _get_section(categories, keyword: str):
    return next((c for c in categories if keyword in c["name"]), None)


def _parse_key_values(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if SEP not in line:
            continue
        parts = [p.strip() for p in line.split(SEP) if p.strip()]
        for i in range(0, len(parts) - 1, 2):
            key = parts[i].rstrip("：:")
            val = parts[i + 1]
            if key and val and key not in fields and len(key) <= 20:
                fields[key] = val
    return fields


def _parse_main_business(text: str) -> str:
    lines = []
    capture = False
    box_chars = set("┌┐└┘├┤┬┴┼─━")
    for line in text.splitlines():
        if "1.主营业务" in line:
            capture = True
            continue
        if capture:
            if line.strip().startswith("【2") or "2.主营构成" in line:
                break
            cleaned = line.strip().strip(SEP).strip()
            if cleaned and not set(cleaned) <= box_chars:
                lines.append(cleaned)
    return lines[0] if lines else ""


def get_company_profile(api: TdxHq_API, ide: str) -> dict:
    market, code = ide_to_market_code(ide)
    categories = api.get_company_info_category(market, code)
    overview = _get_section(categories, "概况")
    business = _get_section(categories, "经营")
    if not overview:
        raise ValueError(f"No company overview section for {ide}")

    overview_text = api.get_company_info_content(
        market, code, overview["filename"], overview["start"], overview["length"]
    )
    fields = _parse_key_values(overview_text)

    main_business = ""
    if business:
        business_text = api.get_company_info_content(
            market, code, business["filename"], business["start"], business["length"]
        )
        main_business = _parse_main_business(business_text)

    return {
        "IDE": ide,
        "code": code,
        "company_name": fields.get("公司名称"),
        "website": fields.get("公司网址"),
        "email": fields.get("电子信箱"),
        "phone": fields.get("联系电话"),
        "registered_address": fields.get("注册地址"),
        "office_address": fields.get("办公地址"),
        "industry": fields.get("所属行业"),
        "business_scope": fields.get("经营范围"),
        "main_business": main_business or fields.get("经营范围", ""),
    }


def fetch_company_profiles(
    ides: Iterable[str],
    ip: str | None = None,
    port: int | None = None,
    *,
    config: Config | None = None,
    on_error: Callable[[str, Exception], None] | None = None,
    show_progress: bool = True,
) -> pd.DataFrame:
    cfg = config or DEFAULT_CONFIG
    ip = ip or cfg.api_ip
    port = port or cfg.api_port

    api = TdxHq_API()
    if not api.connect(ip, port):
        raise ConnectionError(f"Cannot connect to TDX server {ip}:{port}")

    rows = []
    ides_list = list(ides)
    iterator: Iterable[str] = ides_list
    if show_progress:
        try:
            import tqdm

            iterator = tqdm.tqdm(ides_list, desc="STOCKINFO")
        except ImportError:
            pass

    try:
        for ide in iterator:
            try:
                rows.append(get_company_profile(api, ide))
            except Exception as exc:
                if on_error:
                    on_error(ide, exc)
                rows.append({"IDE": ide, "error": str(exc)})
    finally:
        api.disconnect()
    return pd.DataFrame(rows)


def upload_stock_list(
    *,
    config: Config | None = None,
    db: TdxDB | None = None,
    stock_df: pd.DataFrame | None = None,
) -> dict[str, int]:
    """Upload STOCK docs with IDE/ABB/DQ/HY*/ID6/IDS/market.

    BK_GN / BK_FG / index / oldIDE are intentionally omitted from ``$set``
    so existing Mongo values are preserved on update.
    """
    cfg = config or DEFAULT_CONFIG
    tdx_db = db or TdxDB(cfg)

    if stock_df is None:
        stock_df = build_a_share_list(config=cfg)

    meta = StockMetaBuilder(config=cfg)
    records = meta.enrich_stock_df_records(stock_df)

    # Safety: never overwrite block/index fields that live only in Mongo.
    for record in records:
        for key in STOCK_PRESERVE_FIELDS:
            record.pop(key, None)

    upserted = bulk_upsert(tdx_db.collection(COL_STOCK), records, ("IDE",))
    return {"stocks": len(records), "upserted": upserted}


def upload_stockinfo(
    *,
    config: Config | None = None,
    db: TdxDB | None = None,
    ides: Iterable[str] | None = None,
    stock_df: pd.DataFrame | None = None,
    on_error: Callable[[str, Exception], None] | None = None,
    show_progress: bool = True,
) -> dict[str, int]:
    """Fetch F10 company profiles and upload to STOCKINFO collection."""
    cfg = config or DEFAULT_CONFIG
    tdx_db = db or TdxDB(cfg)

    tdx_db.ensure_index(COL_STOCKINFO, [("IDE", pymongo.ASCENDING)])

    if stock_df is None:
        stock_df = build_a_share_list(config=cfg)
    if ides is None:
        ides = stock_df["IDE"].tolist()

    profile_df = fetch_company_profiles(
        ides,
        config=cfg,
        on_error=on_error,
        show_progress=show_progress,
    )
    if "error" in profile_df.columns:
        ok_df = profile_df[profile_df["error"].isna()].drop(columns=["error"])
    else:
        ok_df = profile_df

    if not stock_df.empty and "IDS" in stock_df.columns:
        id_to_ids = stock_df.set_index("IDE")["IDS"]
        ok_df = ok_df.copy()
        ok_df["IDS"] = ok_df["IDE"].map(id_to_ids)

    upserted = bulk_upsert_df(tdx_db.collection(COL_STOCKINFO), ok_df, ("IDE",))
    errors = len(profile_df) - len(ok_df)
    return {"profiles": len(ok_df), "upserted": upserted, "errors": errors}


def upload_all_stockinfo(
    *,
    config: Config | None = None,
    db: TdxDB | None = None,
    include_profiles: bool = True,
    on_error: Callable[[str, Exception], None] | None = None,
    show_progress: bool = True,
) -> dict[str, int]:
    """Upload STOCK list and optionally STOCKINFO profiles."""
    cfg = config or DEFAULT_CONFIG
    tdx_db = db or TdxDB(cfg)
    stock_df = build_a_share_list(config=cfg)

    result = upload_stock_list(config=cfg, db=tdx_db, stock_df=stock_df)
    if include_profiles:
        profile_result = upload_stockinfo(
            config=cfg,
            db=tdx_db,
            stock_df=stock_df,
            on_error=on_error,
            show_progress=show_progress,
        )
        result.update({f"profile_{k}": v for k, v in profile_result.items()})
    return result
