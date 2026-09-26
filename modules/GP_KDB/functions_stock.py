"""Stock quote and financial data queries."""

from __future__ import annotations

from dateutil.parser import parse as date_parse

import pandas as pd

from .connection import KDB
from .utils import logfcn, security_type
from .ohlc_resample import normalize_adjustment, resample_fdk_ohlc

_QUARTER_END = {0: "-03-31", 1: "-06-30", 2: "-09-30", 3: "-12-31"}


def _get_q(date_str: str) -> int:
    d = date_parse(date_str).date()
    return d.year * 4 + (d.month - 1) // 3


def _get_q_reverse(q: int) -> str:
    return str(q // 4) + _QUARTER_END[q % 4]


def dk_stock(self: KDB, ide: str) -> pd.DataFrame:
    result = self.col_TDX_QUATE.find(
        {"IDE": ide},
        {"_id": 0, "IDE": 1, "DT": 1, "O": 1, "C": 1, "H": 1, "L": 1, "V": 1, "A": 1},
    ).sort([("DT", 1)])
    df = pd.DataFrame(result, columns=["IDE", "DT", "O", "C", "H", "L", "V", "A"])
    df["DTnum"] = df["DT"].apply(lambda dt: self.EDTs[dt])
    return df


def fh(self: KDB, ide: str) -> pd.DataFrame:
    query = self.col_STOCK_PKVZGB.find(
        {"IDE": ide}, {"_id": 0, "IDE": 1, "DT": 1, "PKV": 1, "ZGB": 1}
    ).sort([("DT", 1)])
    df = pd.DataFrame(list(query))
    if df.empty:
        # Indices / funds often have quotes but no dividend adjustment table.
        return pd.DataFrame(columns=["IDE", "DT", "PKV", "ZGB"])
    df = df.fillna(1)
    if "ZGB" in df.columns:
        df["ZGB"] = df["ZGB"] * 10000
    return df


def fdk_stock(self: KDB, ide: str) -> pd.DataFrame:
    dk = self.DK_STOCK(ide).set_index("DT")
    fh_df = self.FH(ide)

    if fh_df.empty or "DT" not in fh_df.columns:
        # No adjustment factors — use raw quotes (typical for market indices).
        dk["PKV"] = 1.0
        dk["ZGB"] = 1.0
    else:
        fh_indexed = fh_df.set_index("DT")[["PKV", "ZGB"]]
        dk = dk.join(fh_indexed, how="outer", sort=True)
        dk["PKV"] = dk["PKV"].ffill().fillna(1.0)
        dk["ZGB"] = dk["ZGB"].ffill().fillna(1.0)

    zgb = dk["ZGB"].replace(0, pd.NA).fillna(1.0)
    pkv = dk["PKV"].replace(0, pd.NA).fillna(1.0)

    dk["MP"] = (dk["C"] * zgb).apply(logfcn)
    dk["O"] = (dk["O"] * pkv).apply(logfcn)
    dk["C"] = (dk["C"] * pkv).apply(logfcn)
    dk["H"] = (dk["H"] * pkv).apply(logfcn)
    dk["L"] = (dk["L"] * pkv).apply(logfcn)
    dk["T"] = dk["V"] / zgb * 10000
    dk["V"] = dk["V"] / pkv
    dk = dk[dk["A"] > 0]
    dk["DTnum"] = dk.index.map(lambda dt: self.EDTs[dt])
    return dk.reset_index()


def stock_ohlc_period(
    self: KDB,
    ide: str,
    period: str = "daily",
    adjustment: str = "forward",
) -> pd.DataFrame:
    """OHLCV for chart, merged with unadjusted OHLCV for crosshair display.

    ``adjustment='forward'`` uses FDK (复权). ``adjustment='none'`` uses raw DK
    only — indices and other non-equity quotes should use this path.
    """
    adjustment = normalize_adjustment(adjustment)
    if security_type(ide) == "index":
        adjustment = "none"

    raw_daily = self.DK_STOCK(ide)
    if raw_daily is None or raw_daily.empty:
        return pd.DataFrame()

    if "A" in raw_daily.columns:
        raw_daily = raw_daily[raw_daily["A"] > 0].copy()

    if adjustment == "none":
        chart_daily = raw_daily[["DT", "O", "H", "L", "C", "V"]].copy()
        for col in ("O", "H", "L", "C"):
            chart_daily[col] = chart_daily[col].apply(logfcn)
        adj = resample_fdk_ohlc(chart_daily, period)
    else:
        adj = resample_fdk_ohlc(self.FDK_STOCK(ide), period)

    fh_df = self.FH(ide)
    if not fh_df.empty and {"DT", "ZGB"}.issubset(fh_df.columns):
        raw_daily = raw_daily.merge(fh_df[["DT", "ZGB"]], on="DT", how="left")
        raw_daily["ZGB"] = raw_daily["ZGB"].ffill().fillna(1.0)
    else:
        raw_daily["ZGB"] = 1.0

    extra_cols = {"A": "sum", "ZGB": "last"} if "A" in raw_daily.columns else {"ZGB": "last"}
    raw_cols = ["DT", "O", "H", "L", "C", "V", *extra_cols.keys()]
    raw = resample_fdk_ohlc(raw_daily[raw_cols], period, extra_agg=extra_cols)
    rename_map = {
        "O": "raw_O",
        "H": "raw_H",
        "L": "raw_L",
        "C": "raw_C",
        "V": "raw_V",
        "A": "raw_A",
        "ZGB": "zgb",
    }
    raw = raw.rename(columns={k: v for k, v in rename_map.items() if k in raw.columns})
    return adj.merge(raw, on="DT", how="left")


def fdk_stock_period(
    self: KDB,
    ide: str,
    period: str = "daily",
    adjustment: str = "forward",
) -> pd.DataFrame:
    """OHLC bars resampled to ``period`` (daily/weekly/monthly/quarterly/yearly)."""
    return self.stock_ohlc_period(ide, period, adjustment=adjustment)


def get_dks_in_duration(
    self: KDB,
    ides: list[str] | None = None,
    dt: str = "2025-03-07",
    duration: int = 100,
) -> pd.DataFrame:
    if ides is None:
        ides = self.stocksIDEs()

    df = pd.DataFrame(
        self.col_TDX_QUATE.aggregate(
            [
                {"$match": {"DT": {"$lte": dt}, "IDE": {"$in": ides}}},
                {"$sort": {"IDE": 1, "DT": -1}},
                {"$group": {"_id": "$IDE", "DK": {"$push": "$$CURRENT"}}},
                {"$project": {"_id": "$_id", "EDK": {"$slice": ["$DK", 0, duration]}}},
                {"$unwind": "$EDK"},
                {"$replaceRoot": {"newRoot": "$EDK"}},
                {"$project": {"_id": 0}},
            ],
            allowDiskUse=True,
        )
    )

    zgb = pd.DataFrame(
        self.col_STOCK_PKVZGB.aggregate(
            [
                {"$match": {"DT": {"$lte": dt}, "IDE": {"$in": ides}}},
                {"$project": {"_id": 0, "IDE": 1, "DT": 1, "PKV": 1, "ZGB": 1}},
            ]
        )
    )
    zgb["ZGB"] = zgb["ZGB"] * 10000

    result = (
        df[["IDE", "DT", "O", "C", "H", "L", "V", "A"]]
        .merge(zgb[["IDE", "DT", "ZGB", "PKV"]], on=["IDE", "DT"], how="outer")
        .sort_values(["IDE", "DT"])
    )
    result[["ZGB", "PKV"]] = result.groupby("IDE")[["ZGB", "PKV"]].transform(lambda x: x.ffill())
    result = result.dropna()
    result["O"] = (result["O"] * result["PKV"]).apply(logfcn)
    result["C"] = (result["C"] * result["PKV"]).apply(logfcn)
    result["H"] = (result["H"] * result["PKV"]).apply(logfcn)
    result["L"] = (result["L"] * result["PKV"]).apply(logfcn)
    result["T"] = result["V"] / result["ZGB"]
    return result


def yield_rows(cursor, chunk_size: int):
    chunk = []
    for i, row in enumerate(cursor):
        if i % chunk_size == 0 and i > 0:
            yield chunk
            chunk = []
        chunk.append(row)
    if chunk:
        yield chunk


def continue_dk(
    self: KDB,
    ides: list[str] | None = None,
    start_dt: str | None = None,
    chunk: int = 100,
):
    if ides is None:
        ides = [x["IDE"] for x in self.col_TDX_STOCK.find({}, {"_id": 0, "IDE": 1}).sort([("IDE", 1)])]

    zgb = pd.DataFrame(
        self.col_STOCK_PKVZGB.aggregate(
            [
                {"$match": {"IDE": {"$in": ides}}},
                {"$project": {"_id": 0, "IDE": 1, "DT": 1, "PKV": 1, "ZGB": 1}},
            ]
        )
    )
    zgb["ZGB"] = zgb["ZGB"] * 10000

    dts = self.col_TDX_QUATE.distinct("DT")
    if start_dt is not None:
        dts = [x for x in dts if x >= start_dt]

    for dt_chunk in yield_rows(dts, chunk_size=chunk):
        df = pd.DataFrame(
            self.col_TDX_QUATE.find({"DT": {"$in": dt_chunk}, "IDE": {"$in": ides}}, {"_id": 0}).sort(
                [("IDE", 1), ("DT", 1)]
            )
        )

        if len(df) == 0:
            yield None
            continue

        result = (
            df[["IDE", "DT", "O", "C", "H", "L", "V", "A"]]
            .merge(zgb[["IDE", "DT", "ZGB", "PKV"]], on=["IDE", "DT"], how="outer")
            .sort_values(["IDE", "DT"])
        )
        result[["ZGB", "PKV"]] = result.groupby("IDE")[["ZGB", "PKV"]].transform(lambda x: x.ffill())
        result = result.dropna()
        result["O"] = (result["O"] * result["PKV"]).apply(logfcn)
        result["C"] = (result["C"] * result["PKV"]).apply(logfcn)
        result["H"] = (result["H"] * result["PKV"]).apply(logfcn)
        result["L"] = (result["L"] * result["PKV"]).apply(logfcn)
        result["T"] = result["V"] / result["ZGB"]
        yield result


def cw_stock(self: KDB, ide: str, end_dt: str | None = None) -> pd.DataFrame:
    finditem: dict = {"IDE": ide}
    if end_dt:
        finditem["REPORTDATE"] = {"$lte": end_dt}

    query = self.col_TDX_CW.find(finditem, {"_id": 0, "IDE": 0, "MK": 0}).sort([("REPORTDATE", 1)])
    rows = list(query)
    if not rows:
        return pd.DataFrame()

    full_index = [
        _get_q_reverse(x)
        for x in range(_get_q(rows[0]["REPORTDATE"]), _get_q(rows[-1]["REPORTDATE"]) + 1)
    ]
    return pd.DataFrame(rows).set_index("REPORTDATE").reindex(full_index)


# Trading-day offsets for list 涨幅 columns (1日 / 3日 / 5日 / 一月 / 一年).
RETURN_OFFSETS = (
    ("chg_1d", 1),
    ("chg_3d", 3),
    ("chg_5d", 5),
    ("chg_1m", 21),
    ("chg_1y", 244),
)


def returns_for_ides(self: KDB, ides: list[str] | None) -> dict[str, dict]:
    """Batch multi-horizon close-to-close return % for many IDEs.

    Horizons are measured in trading days (1 / 3 / 5 / ~1m / ~1y). Returns
    ``{ide: {chg_1d, chg_3d, chg_5d, chg_1m, chg_1y}}`` with float or None.
    """
    if not ides:
        return {}

    unique = list(dict.fromkeys(ides))
    need = max(offset for _, offset in RETURN_OFFSETS) + 1

    # Use the latest quote date in this batch, not cached ``kdb.DTs[-1]``.
    # A long-lived API process can keep stale calendar dates and zero out 涨幅.
    match: dict = {"IDE": {"$in": unique}, "C": {"$nin": [None, 0]}}
    latest_doc = self.col_TDX_QUATE.find_one(
        match,
        {"_id": 0, "DT": 1},
        sort=[("DT", -1)],
    )
    if latest_doc and latest_doc.get("DT"):
        match["DT"] = {"$lte": latest_doc["DT"]}

    cursor = self.col_TDX_QUATE.aggregate(
        [
            {"$match": match},
            {"$sort": {"IDE": 1, "DT": -1}},
            {"$group": {"_id": "$IDE", "closes": {"$push": "$C"}}},
            {"$project": {"closes": {"$slice": ["$closes", need]}}},
        ],
        allowDiskUse=True,
    )

    out: dict[str, dict] = {
        ide: {key: None for key, _ in RETURN_OFFSETS} for ide in unique
    }
    for doc in cursor:
        ide = doc["_id"]
        closes = [c for c in (doc.get("closes") or []) if c is not None]
        if not closes:
            continue
        last = closes[0]
        try:
            last_f = float(last)
        except (TypeError, ValueError):
            continue
        if last_f == 0:
            continue
        row = out.setdefault(ide, {key: None for key, _ in RETURN_OFFSETS})
        for key, offset in RETURN_OFFSETS:
            if len(closes) <= offset:
                continue
            base = closes[offset]
            try:
                base_f = float(base)
            except (TypeError, ValueError):
                continue
            if base_f == 0:
                continue
            row[key] = round((last_f / base_f - 1.0) * 100.0, 2)
    return out


# Latest-quarter FSA ratio fields persisted in tdx.FSA.
# Keep in sync with backend.api.fsa_update.RATIO_FIELDS keys.
FSA_RATIO_KEYS = (
    "BPS",
    "ROE",
    "ROA",
    "归母净利润同比_1Y",
    "归母净利润同比",
    "营业总收入同比_1Y",
    "营业总收入同比",
    "营业总收入_单季同比",
    "每股流动资产",
    "FQ每股流动资产",
    "FQ每股净流动资产",
    "PKV",
    "毛利率",
    "管理费用比例",
    "销售费用比例",
    "研发费用比例",
    "营业成本比例",
)


def _safe_ratio_num(value):
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(num) or num != num:  # NaN
        return None
    if abs(num) == float("inf"):
        return None
    return round(num, 2)


def fsa_latest_for_ides(self: KDB, ides: list[str] | None) -> dict[str, dict]:
    """Batch latest-season FSA ratios for many IDEs from ``tdx.FSA``.

    Returns ``{ide: {REPORTDATE, BPS, ROE, ...}}`` with None for missing values.
    """
    if not ides:
        return {}

    unique = list(dict.fromkeys(ides))
    empty = {"REPORTDATE": None, **{key: None for key in FSA_RATIO_KEYS}}
    out: dict[str, dict] = {ide: dict(empty) for ide in unique}

    cursor = self.col_TDX_FSA.aggregate(
        [
            {"$match": {"IDE": {"$in": unique}}},
            {"$sort": {"IDE": 1, "REPORTDATE": -1}},
            {"$group": {"_id": "$IDE", "doc": {"$first": "$$ROOT"}}},
        ],
        allowDiskUse=True,
    )

    for item in cursor:
        ide = item["_id"]
        doc = item.get("doc") or {}
        row = {
            "REPORTDATE": doc.get("REPORTDATE"),
            **{key: _safe_ratio_num(doc.get(key)) for key in FSA_RATIO_KEYS},
        }
        out[ide] = row
    return out


def latest_amount_for_ides(self: KDB, ides: list[str] | None) -> dict[str, float]:
    """Latest daily turnover (``A``) per IDE for treemap sizing."""
    if not ides:
        return {}

    unique = list(dict.fromkeys(ides))
    match: dict = {"IDE": {"$in": unique}, "A": {"$gt": 0}}
    latest_doc = self.col_TDX_QUATE.find_one(
        match,
        {"_id": 0, "DT": 1},
        sort=[("DT", -1)],
    )
    if latest_doc and latest_doc.get("DT"):
        match["DT"] = latest_doc["DT"]

    cursor = self.col_TDX_QUATE.aggregate(
        [
            {"$match": match},
            {"$group": {"_id": "$IDE", "amount": {"$max": "$A"}}},
        ],
        allowDiskUse=True,
    )
    out: dict[str, float] = {}
    for doc in cursor:
        ide = doc.get("_id")
        amount = doc.get("amount")
        if not ide or amount is None:
            continue
        try:
            out[ide] = float(amount)
        except (TypeError, ValueError):
            continue
    return out


KDB.DK_STOCK = dk_stock
KDB.FH = fh
KDB.FDK_STOCK = fdk_stock
KDB.FDK_STOCK_PERIOD = fdk_stock_period
KDB.STOCK_OHLC_PERIOD = stock_ohlc_period
KDB.getDKs_in_Duration = get_dks_in_duration
KDB.continueDK = continue_dk
KDB.CW_STOCK = cw_stock
KDB.returns_for_ides = returns_for_ides
KDB.latest_amount_for_ides = latest_amount_for_ides
KDB.fsa_latest_for_ides = fsa_latest_for_ides
