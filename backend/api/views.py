import math
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from GP_KDB import KDB
from GP_KDB.ohlc_resample import normalize_adjustment, normalize_period
from GP_KDB.utils import security_type
from GP_FSA import Stock, accounts
from GP_FSA.table import CW_TABLES
from GP_TECH import (
    parse_indicator_kinds,
    recent_swings_for_ides,
    scan_channel_stocks,
    scan_independent_strong_stocks,
    scan_industry_relative,
    stock_indicators,
    stock_swings,
)
from GP_AI import confirm_advice, model_status, run_buy_advice

from . import data_update, fsa_update, industry_profit
from .heatmap_cache import DEFAULT_TTL_SECONDS, get_cached, set_cached

def _ensure_kdb():
    kdb = KDB()
    if not kdb.is_configured:
        kdb.setting()
    return kdb


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "message": "Backend is running"})


@api_view(["GET"])
def info(request):
    return Response(
        {
            "name": "Project API",
            "version": "1.0.0",
            "timestamp": timezone.now().isoformat(),
            "endpoints": {
                "health": "/api/health/",
                "info": "/api/info/",
                "stocks": "/api/stocks/",
                "stock_info": "/api/stock/<ide>/",
                "stock_fdk": "/api/stock/<ide>/fdk/",
                "stock_indicators": "/api/stock/<ide>/indicators/",
                "stock_swings": "/api/stock/<ide>/swings/",
                "stock_main_fsa": "/api/stock/<ide>/main-fsa/",
                "stock_cw_tables": "/api/stock/<ide>/cw/",
                "stock_cw": "/api/stock/<ide>/cw/<name>/",
                "stock_ratio": "/api/stock/<ide>/ratio/<name>/",
                "stock_reports": "/api/stock/<ide>/reports/",
                "hy_sectors": "/api/hy/",
                "hy_list": "/api/hy/list/",
                "hy_info": "/api/hy/<ids>/",
                "hy_stocks": "/api/hy/<ids>/stocks/",
                "market_heatmap": "/api/market/heatmap/",
                "industry_profit_growth": "/api/industry/profit-growth/",
                "pool_categories": "/api/pool/categories/",
                "pool_stocks": "/api/pool/stocks/",
                "pool_recent_swings": "/api/pool/recent-swings/",
                "pool_stock": "/api/pool/stock/<ide>/",
                "screen": "/api/screen/",
                "compare": "/api/compare/",
                "tech_channel_scan": "/api/tech/channel/scan/",
                "tech_independent_strong_scan": "/api/tech/independent-strong/scan/",
                "tech_industry_relative_scan": "/api/tech/industry-relative/scan/",
                "ai_advice_scan": "/api/ai/advice/scan/",
                "ai_advice_models": "/api/ai/advice/models/",
                "ai_advice_confirm": "/api/ai/advice/confirm/",
                "update_config": "/api/update/config/",
                "update_tasks": "/api/update/tasks/",
                "update_run": "/api/update/run/",
                "update_jobs": "/api/update/jobs/",
                "update_job": "/api/update/jobs/<job_id>/",
                "update_ratios": "/api/update/ratios/",
                "update_reports": "/api/update/reports/",
            },
        }
    )


@api_view(["GET"])
def stocks_list(request):
    _ensure_kdb()
    data = KDB().StocksList()
    return Response({"stocks": data, "count": len(data)})


@api_view(["GET"])
def stock_fdk(request, ide):
    _ensure_kdb()
    period = request.GET.get("period", "daily")
    adjustment = request.GET.get("adjustment", "forward")
    try:
        period = normalize_period(period)
        adjustment = normalize_adjustment(adjustment)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)

    # Market indices have no dividend table — always use unadjusted quotes.
    if security_type(ide) == "index":
        adjustment = "none"

    df = KDB().STOCK_OHLC_PERIOD(ide, period, adjustment=adjustment)
    if df.empty:
        return Response({"error": f"No quote data for: {ide}"}, status=404)

    info_data = KDB().StockInfo(ide) or {}
    stock_name = info_data.get("IDS") or ide

    columns = ["DT", "O", "H", "L", "C", "V", "raw_O", "raw_H", "raw_L", "raw_C", "raw_V"]
    if "raw_A" in df.columns:
        columns.append("raw_A")

    chart_df = df[[c for c in columns if c in df.columns]].rename(
        columns={
            "DT": "dt",
            "O": "open",
            "H": "high",
            "L": "low",
            "C": "close",
            "V": "volume",
            "raw_O": "raw_open",
            "raw_H": "raw_high",
            "raw_L": "raw_low",
            "raw_C": "raw_close",
            "raw_V": "raw_volume",
            "raw_A": "raw_amount",
        }
    )
    data = chart_df.where(chart_df.notna(), None).to_dict(orient="records")
    return Response(
        {
            "ide": ide,
            "stock_name": stock_name,
            "period": period,
            "adjustment": adjustment,
            "data": data,
            "count": len(data),
        }
    )


@api_view(["GET"])
def stock_indicators_view(request, ide):
    """Technical indicators on the same OHLC bars as the FDK chart."""
    _ensure_kdb()
    period = request.GET.get("period", "daily")
    adjustment = request.GET.get("adjustment", "forward")
    kinds = parse_indicator_kinds(request.GET.get("kinds"))
    try:
        period = normalize_period(period)
        adjustment = normalize_adjustment(adjustment)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)

    if security_type(ide) == "index":
        adjustment = "none"

    payload = stock_indicators(
        KDB(),
        ide,
        period=period,
        adjustment=adjustment,
        kinds=kinds,
    )
    if payload.get("count", 0) == 0:
        return Response({"error": f"No quote data for: {ide}"}, status=404)
    return Response(payload)


def _parse_optional_float(raw):
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid float: {raw}") from exc


def _parse_optional_int(raw, default):
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid int: {raw}") from exc


@api_view(["GET"])
def stock_swings_view(request, ide):
    """Swing high/low markers on the same OHLC bars as the FDK chart."""
    _ensure_kdb()
    period = request.GET.get("period", "daily")
    adjustment = request.GET.get("adjustment", "forward")
    try:
        period = normalize_period(period)
        adjustment = normalize_adjustment(adjustment)
        n = _parse_optional_int(request.GET.get("n"), 2)
        min_distance = _parse_optional_int(request.GET.get("min_distance"), 3)
        min_change = _parse_optional_float(request.GET.get("min_change"))
        adaptive_raw = request.GET.get("adaptive", "1").strip().lower()
        adaptive = adaptive_raw not in ("0", "false", "no")
        if n < 1 or min_distance < 0:
            raise ValueError("n must be >= 1 and min_distance >= 0")
        if min_change is not None and min_change < 0:
            raise ValueError("min_change must be >= 0")
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)

    if security_type(ide) == "index":
        adjustment = "none"

    payload = stock_swings(
        KDB(),
        ide,
        period=period,
        adjustment=adjustment,
        n=n,
        min_change=min_change,
        min_distance=min_distance,
        adaptive=adaptive,
    )
    if payload.get("count", 0) == 0 and not payload.get("markers"):
        # Distinguish empty OHLC from "no swings after filters".
        # stock_swings returns count=0 for both; check via FDK period frame length.
        df = KDB().STOCK_OHLC_PERIOD(ide, period, adjustment=adjustment)
        if df is None or df.empty:
            return Response({"error": f"No quote data for: {ide}"}, status=404)
    return Response(payload)


@api_view(["GET"])
def stock_info(request, ide):
    _ensure_kdb()
    info_data = KDB().StockInfo(ide)
    if not info_data:
        return Response({"error": f"Stock not found: {ide}"}, status=404)
    return Response(info_data)


def _normalize_cell_value(val):
    if val is None:
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num):
        return None
    return num


def _serialize_cw_table(table, st):
    df = table.get_df(st)
    if df is None or df.empty:
        return {"columns": [], "rows": []}

    date_cols = sorted(
        [col for col in df.columns if col != "propert"],
        reverse=True,
    )

    rows = []
    for item in table.items:
        row_id = item.ID
        if row_id not in df.index:
            continue

        props = df.at[row_id, "propert"]
        if not isinstance(props, dict):
            props = item.proprty()

        values = {}
        for col in date_cols:
            values[col] = _normalize_cell_value(df.at[row_id, col])

        rows.append(
            {
                "id": row_id,
                "name": props.get("tag", row_id),
                "level": props.get("taglevel", 0),
                "color": props.get("color"),
                "is_percent": props.get("isPercent", False),
                "values": values,
            }
        )

    return {"columns": date_cols, "rows": rows}


@api_view(["GET"])
def stock_cw_tables(request, ide):
    _ensure_kdb()
    return Response(
        {
            "ide": ide,
            "tables": [{"key": key, "label": label} for key, (label, _) in CW_TABLES.items()],
        }
    )


@api_view(["GET"])
def stock_cw(request, ide, name):
    _ensure_kdb()
    if name not in CW_TABLES:
        return Response({"error": f"Unknown CW table: {name}"}, status=404)

    label, table = CW_TABLES[name]
    st = Stock(ide).load_FS()
    if st.FS.empty:
        return Response(
            {
                "ide": ide,
                "table": name,
                "label": label,
                "columns": [],
                "rows": [],
            }
        )

    payload = _serialize_cw_table(table, st)
    return Response(
        {
            "ide": ide,
            "table": name,
            "label": label,
            **payload,
        }
    )


_CHG_KEYS = ("chg_1d", "chg_3d", "chg_5d", "chg_1m", "chg_1y")
_FSA_KEYS = ("REPORTDATE", *(field["key"] for field in fsa_update.RATIO_FIELDS))


def _empty_chg():
    return {key: None for key in _CHG_KEYS}


def _empty_fsa():
    return {key: None for key in _FSA_KEYS}


def _reload_kdb_helpers():
    """Rebind stock helpers so edits under modules/GP_KDB apply after views reload."""
    import importlib

    from GP_KDB import functions_stock as fs
    from GP_KDB import functions_heatmap as fh
    from GP_KDB import functions_screen as fsc
    from GP_KDB import functions_pool as fp
    from GP_KDB import blocknew_pool as bp

    importlib.reload(fs)
    importlib.reload(fh)
    importlib.reload(fsc)
    importlib.reload(bp)
    importlib.reload(fp)
    KDB.returns_for_ides = fs.returns_for_ides
    KDB.latest_amount_for_ides = fs.latest_amount_for_ides
    KDB.fsa_latest_for_ides = fs.fsa_latest_for_ides
    KDB.screen_stocks = fsc.screen_stocks
    KDB.fsa_report_dates = fsc.fsa_report_dates
    KDB.pool_list_categories = fp.pool_list_categories
    KDB.pool_create_category = fp.pool_create_category
    KDB.pool_delete_category = fp.pool_delete_category
    KDB.pool_stock_membership = fp.pool_stock_membership
    KDB.pool_add_stock = fp.pool_add_stock
    KDB.pool_remove_stock = fp.pool_remove_stock
    KDB.pool_stocks = fp.pool_stocks
    KDB.market_heatmap_tree = fh.market_heatmap_tree


# Ensure bankuai/hy list 涨幅 uses the latest returns_for_ides implementation.
try:
    _reload_kdb_helpers()
except Exception:
    pass


def _attach_returns(rows):
    """Merge batch 涨幅 onto sector/stock list rows that have an ``ide``."""
    _ensure_kdb()
    ides = [row["ide"] for row in rows if row.get("ide")]
    if not ides:
        for row in rows:
            row.update(_empty_chg())
        return rows

    kdb = KDB()
    if not hasattr(kdb, "returns_for_ides"):
        _reload_kdb_helpers()
    returns = kdb.returns_for_ides(ides) if hasattr(kdb, "returns_for_ides") else {}
    for row in rows:
        chg = returns.get(row.get("ide")) or _empty_chg()
        row.update(chg)
    return rows


def _attach_fsa(rows):
    """Merge latest-season FSA ratios onto stock list rows."""
    ides = [row["ide"] for row in rows if row.get("ide")]
    latest = KDB().fsa_latest_for_ides(ides) if ides else {}
    for row in rows:
        fsa = latest.get(row.get("ide")) or _empty_fsa()
        row.update(fsa)
    return rows


def _serialize_hy_entry(item):
    if isinstance(item, (list, tuple)):
        if len(item) >= 2:
            return {
                "name": item[0],
                "ide": item[1],
                "code": item[2] if len(item) > 2 else "",
            }
        return None
    if isinstance(item, dict):
        return {
            "name": item.get("IDS", ""),
            "ide": item.get("IDE", ""),
            "code": item.get("code", ""),
        }
    return None


def _serialize_hy_stocks(stocks):
    kdb = KDB()
    rows = []
    for item in stocks or []:
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
            continue
        if not name:
            info = kdb.StockInfo(ide)
            name = info.get("IDS", "") if info else ""
        rows.append({"ide": ide, "name": name})
    return rows


@api_view(["GET"])
def hy_list(request):
    _ensure_kdb()
    sectors = KDB().HYList()
    return Response({"sectors": sectors, "count": len(sectors)})


@api_view(["GET"])
def hy_info(request, ids):
    _ensure_kdb()
    info = KDB().HYInfo(ids)
    if not info:
        return Response({"error": f"Industry not found: {ids}"}, status=404)
    return Response(info)


@api_view(["GET"])
def hy_sectors(request):
    _ensure_kdb()
    parent = request.GET.get("parent", "全部行业")
    level = request.GET.get("level", "1")
    if parent == "全部行业":
        result = KDB().HYchildren(parent, level=level)
    else:
        result = KDB().HYchildren(parent)
    children = result.get("children", [])
    sectors = [entry for item in children if (entry := _serialize_hy_entry(item))]
    _attach_returns(sectors)
    return Response(
        {
            "parent": parent,
            "level": level if parent == "全部行业" else None,
            "sectors": sectors,
            "count": len(sectors),
        }
    )


@api_view(["GET"])
def hy_stocks(request, ids):
    _ensure_kdb()
    stocks = KDB().stocks_in_HY(ids)
    rows = _serialize_hy_stocks(stocks)
    _attach_returns(rows)
    _attach_fsa(rows)
    children_result = KDB().HYchildren(ids)
    has_children = bool(children_result.get("children"))
    return Response(
        {
            "sector": ids,
            "stocks": rows,
            "count": len(rows),
            "has_children": has_children,
        }
    )


@api_view(["GET"])
def market_heatmap(request):
    """Treemap tree: market (HY1→HY2→stocks) or single sector subtree."""
    _ensure_kdb()
    sector = (request.GET.get("sector") or "").strip() or None
    refresh = request.GET.get("refresh", "").lower() in {"1", "true", "yes"}

    kdb = KDB()
    if not hasattr(kdb, "market_heatmap_tree"):
        _reload_kdb_helpers()

    latest_doc = kdb.col_TDX_QUATE.find_one(
        {"C": {"$nin": [None, 0]}},
        {"_id": 0, "DT": 1},
        sort=[("DT", -1)],
    )
    as_of = latest_doc.get("DT") if latest_doc else ""
    cache_key = f"heatmap:{sector or 'market'}:{as_of}"
    cached_payload = None if refresh else get_cached(cache_key, DEFAULT_TTL_SECONDS)
    if cached_payload is not None:
        return Response(cached_payload)

    tree = kdb.market_heatmap_tree(sector)
    payload = {
        "sector": sector or "市场",
        "tree": tree,
        "stock_count": tree.get("stock_count", 0),
        "as_of": as_of,
        "cached": False,
    }
    set_cached(cache_key, {**payload, "cached": True})
    return Response(payload)


@api_view(["GET"])
def industry_profit_growth(request):
    """Industry profit growth dashboard metrics."""
    year_raw = request.GET.get("year")
    year = None
    if year_raw not in (None, ""):
        try:
            year = int(year_raw)
        except (TypeError, ValueError):
            return Response({"error": "year must be an integer"}, status=400)

    period = request.GET.get("period") or "yoy"
    level = request.GET.get("level") or "1"
    industry = (request.GET.get("industry") or "").strip() or None
    refresh = request.GET.get("refresh", "").lower() in {"1", "true", "yes"}

    payload = industry_profit.get_profit_growth(
        year=year,
        period=period,
        level=level,
        industry=industry,
        use_cache=not refresh,
    )
    if payload.get("error") and not payload.get("industries"):
        return Response(payload, status=404)
    return Response(payload)


def _normalize_report_date(idx):
    if idx is None:
        return None
    if hasattr(idx, "strftime"):
        try:
            return idx.strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            pass
    text = str(idx)
    return text[:10] if len(text) >= 10 else text


@api_view(["GET"])
def stock_ratio(request, ide, name):
    _ensure_kdb()
    if name not in accounts:
        return Response({"error": f"Unknown ratio/account: {name}"}, status=404)

    st = Stock(ide).load_FS()
    series = accounts[name].value(st).dropna()
    data = []
    for idx, val in series.items():
        num = _normalize_cell_value(val)
        date = _normalize_report_date(idx)
        if num is None or not date:
            continue
        data.append({"report_date": date, "value": num})
    return Response({"ide": ide, "account": name, "data": data})


@api_view(["GET"])
def stock_main_fsa(request, ide):
    """Quarterly main_FSA overlays for K-line steplines (BPS / 固有PB / C_BPS加5年净利润)."""
    _ensure_kdb()
    try:
        st = Stock(ide).load_FS()
        df = st.main_FSA()
    except Exception as exc:
        return Response({"error": f"main_FSA failed: {exc}"}, status=500)

    if df is None or getattr(df, "empty", True):
        return Response({"error": f"No main_FSA data for: {ide}"}, status=404)

    # source_col in DataFrame -> API series key
    field_map = (
        ("BPS", "BPS"),
        ("固有PB", "固有PB"),
        ("C_BPS加5年净利润", "C_BPS加5年净利润"),
    )

    series = {}
    for api_key, col in field_map:
        points = []
        if col not in df.columns:
            series[api_key] = points
            continue
        for _, row in df.iterrows():
            dt = row.get("REPORTDATE")
            val = _normalize_cell_value(row.get(col))
            if not dt or val is None:
                continue
            points.append({"dt": str(dt)[:10], "value": val})
        series[api_key] = points

    return Response(
        {
            "ide": ide,
            "series": series,
            "fields": [
                {"key": "BPS", "label": "BPS"},
                {"key": "固有PB", "label": "固有PB"},
                {"key": "C_BPS加5年净利润", "label": "C_BPS加5年净利润"},
            ],
        }
    )


@api_view(["GET"])
def stock_fsa(request, ide):
    _ensure_kdb()
    kdb = KDB()
    docs = list(
        kdb.col_TDX_FSA.find({"IDE": ide}, {"_id": 0})
        .sort([("REPORTDATE", -1)])
        .limit(12)
    )
    if not docs:
        return Response({"error": f"No FSA ratio data for: {ide}"}, status=404)
    return Response({"ide": ide, "data": docs, "count": len(docs)})


@api_view(["GET"])
def stock_reports(request, ide):
    """Research reports + periodic filings for a stock (from tdx.EM_*)."""
    from GP_EM import Config as EmConfig
    from GP_EM import list_stock_reports

    try:
        research_limit = int(request.GET.get("research_limit", 50))
        filing_limit = int(request.GET.get("filing_limit", 50))
    except (TypeError, ValueError):
        research_limit, filing_limit = 50, 50

    em_config = EmConfig(
        mongo_uri=getattr(settings, "GP_TDX_MONGO_URI", EmConfig().mongo_uri),
        mongo_db=getattr(settings, "GP_TDX_MONGO_DB", EmConfig().mongo_db),
    )
    payload = list_stock_reports(
        ide,
        config=em_config,
        research_limit=max(1, min(research_limit, 200)),
        filing_limit=max(1, min(filing_limit, 200)),
    )
    return Response(payload)


@api_view(["GET", "PUT"])
def update_config(request):
    if request.method == "GET":
        return Response(data_update.load_config())

    tdx_path = request.data.get("tdx_path")
    if not tdx_path or not str(tdx_path).strip():
        return Response({"error": "tdx_path is required"}, status=400)

    try:
        payload = data_update.save_config(str(tdx_path))
    except OSError as exc:
        return Response({"error": f"无法保存配置: {exc}"}, status=500)

    return Response(payload)


@api_view(["GET"])
def update_ratios(request):
    return Response(data_update.list_ratio_fields())


@api_view(["GET"])
def update_reports(request):
    return Response(data_update.list_report_options())


@api_view(["GET"])
def update_tasks(request):
    return Response({"tasks": data_update.list_tasks()})


@api_view(["POST"])
def update_run(request):
    task = request.data.get("task")
    if not task:
        return Response({"error": "task is required"}, status=400)

    tdx_path = request.data.get("tdx_path")
    options = request.data.get("options") or {}

    try:
        job = data_update.start_update_job(task, tdx_path=tdx_path, options=options)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)

    return Response(job, status=202)


@api_view(["GET"])
def update_jobs(request):
    try:
        limit = int(request.GET.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    return Response(data_update.list_jobs(limit=limit))


@api_view(["GET"])
def update_job(request, job_id):
    job = data_update.get_job(job_id)
    if not job:
        return Response({"error": "Job not found"}, status=404)
    return Response(job)


def _pool_username(request):
    return request.GET.get("username") or (request.data.get("username") if hasattr(request, "data") else None)


@api_view(["GET", "POST"])
def pool_categories(request):
    _ensure_kdb()
    kdb = KDB()
    username = _pool_username(request)
    if request.method == "GET":
        categories = kdb.pool_list_categories(username)
        return Response({"categories": categories, "count": len(categories)})

    category = (request.data.get("category") or "").strip()
    if not category:
        return Response({"error": "category is required"}, status=400)
    try:
        payload = kdb.pool_create_category(category, username)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)
    return Response(payload, status=201)


@api_view(["DELETE"])
def pool_category_detail(request, name):
    _ensure_kdb()
    try:
        payload = KDB().pool_delete_category(name, _pool_username(request))
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)
    return Response(payload)


@api_view(["GET"])
def pool_stocks(request):
    _ensure_kdb()
    category = request.GET.get("category") or ""
    rows = KDB().pool_stocks(category or None, _pool_username(request))
    # Enrich with returns + FSA like hy_stocks for consistent tables.
    _attach_returns(rows)
    _attach_fsa(rows)
    return Response(
        {
            "category": category or None,
            "stocks": rows,
            "count": len(rows),
        }
    )


@api_view(["GET"])
def pool_recent_swings(request):
    """Recent buy/sell swing flags for pool stocks (async-friendly companion to pool list)."""
    _ensure_kdb()
    category = request.GET.get("category") or ""
    try:
        days = int(request.GET.get("days", 3))
    except (TypeError, ValueError):
        return Response({"error": "days must be an integer"}, status=400)
    if days < 1 or days > 20:
        return Response({"error": "days must be between 1 and 20"}, status=400)

    kdb = KDB()
    rows = kdb.pool_stocks(category or None, _pool_username(request))
    ides = [row["ide"] for row in rows if row.get("ide")]
    swings = recent_swings_for_ides(kdb, ides, recent_days=days, period="daily", adjustment="forward")
    return Response(
        {
            "category": category or None,
            "days": days,
            "swings": swings,
            "count": len(swings),
        }
    )


@api_view(["GET", "POST", "DELETE"])
def pool_stock(request, ide):
    _ensure_kdb()
    kdb = KDB()
    username = _pool_username(request)

    if request.method == "GET":
        return Response(kdb.pool_stock_membership(ide, username))

    category = (request.data.get("category") or "").strip()
    if request.method == "POST":
        if not category:
            return Response({"error": "category is required"}, status=400)
        try:
            payload = kdb.pool_add_stock(ide, category, username)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        return Response(payload)

    # DELETE — category optional: omit/empty removes stock from entire pool
    try:
        payload = kdb.pool_remove_stock(ide, category or None, username)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)
    return Response(payload)


def _median(values):
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    nums.sort()
    mid = len(nums) // 2
    if len(nums) % 2 == 1:
        return round(nums[mid], 2)
    return round((nums[mid - 1] + nums[mid]) / 2, 2)


_COMPARE_BENCHMARK_KEYS = tuple(
    key for key in _FSA_KEYS if key != "REPORTDATE"
) + _CHG_KEYS


@api_view(["POST"])
def compare_stocks(request):
    """Batch compare stocks: latest FSA ratios, 涨幅, and peer medians."""
    _ensure_kdb()
    ides = request.data.get("ides") or []
    if not isinstance(ides, list):
        return Response({"error": "ides must be a list"}, status=400)

    ides = list(dict.fromkeys(str(x).strip() for x in ides if str(x).strip()))[:8]
    if not ides:
        return Response({"error": "请至少选择一只股票"}, status=400)

    kdb = KDB()
    name_map = {item["ide"]: item for item in kdb.StocksList()}
    rows = []
    for ide in ides:
        info = kdb.StockInfo(ide) or {}
        stock_row = name_map.get(ide, {})
        rows.append(
            {
                "ide": ide,
                "name": info.get("IDS") or stock_row.get("name") or ide,
                "ABB": info.get("ABB") or stock_row.get("ABB") or "",
                "HY1": info.get("HY1"),
                "HY2": info.get("HY2"),
            }
        )

    _attach_returns(rows)
    _attach_fsa(rows)

    benchmarks = {}
    for key in _COMPARE_BENCHMARK_KEYS:
        vals = [row.get(key) for row in rows if row.get(key) is not None]
        med = _median(vals)
        if med is not None:
            benchmarks[key] = med

    return Response(
        {
            "stocks": rows,
            "benchmarks": benchmarks,
            "count": len(rows),
        }
    )


@api_view(["POST"])
def tech_channel_scan(request):
    """Scan Mongo quotes for stocks in or newly entering an ascending channel."""
    _ensure_kdb()
    mode = request.data.get("mode", "entered")
    industries = request.data.get("industries") or []
    ides = request.data.get("ides") or []

    if mode not in {"in", "entered"}:
        return Response({"error": "mode must be 'in' or 'entered'"}, status=400)
    if not isinstance(industries, list):
        return Response({"error": "industries must be a list"}, status=400)
    if not isinstance(ides, list):
        return Response({"error": "ides must be a list"}, status=400)

    try:
        lookback = int(request.data.get("lookback", 80))
        pivot_window = int(request.data.get("pivot_window", 5))
        min_score = int(request.data.get("min_score", 6))
        limit = int(request.data.get("limit", 500))
    except (TypeError, ValueError):
        return Response({"error": "扫描参数必须是整数"}, status=400)

    try:
        rows = scan_channel_stocks(
            KDB(),
            ides=ides or None,
            industries=industries or None,
            mode=mode,
            lookback=lookback,
            pivot_window=pivot_window,
            min_score=min_score,
            limit=limit,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)

    _attach_returns(rows)
    _attach_fsa(rows)
    return Response(
        {
            "mode": mode,
            "industries": industries,
            "ides": ides,
            "count": len(rows),
            "stocks": rows,
        }
    )


@api_view(["POST"])
def tech_independent_strong_scan(request):
    """Scan for ascending-channel stocks with positive excess and low index corr."""
    _ensure_kdb()
    mode = request.data.get("mode", "in")
    industries = request.data.get("industries") or []
    ides = request.data.get("ides") or []
    benchmark = request.data.get("benchmark") or "sh000001"

    if mode not in {"in", "entered"}:
        return Response({"error": "mode must be 'in' or 'entered'"}, status=400)
    if not isinstance(industries, list):
        return Response({"error": "industries must be a list"}, status=400)
    if not isinstance(ides, list):
        return Response({"error": "ides must be a list"}, status=400)

    try:
        lookback = int(request.data.get("lookback", 80))
        pivot_window = int(request.data.get("pivot_window", 5))
        min_score = int(request.data.get("min_score", 6))
        corr_window = int(request.data.get("corr_window", 60))
        excess_window = int(request.data.get("excess_window", 21))
        limit = int(request.data.get("limit", 500))
        max_corr = float(request.data.get("max_corr", 0.4))
        min_excess = float(request.data.get("min_excess", 0.0))
    except (TypeError, ValueError):
        return Response({"error": "扫描参数格式不正确"}, status=400)

    try:
        rows = scan_independent_strong_stocks(
            KDB(),
            ides=ides or None,
            industries=industries or None,
            benchmark_ide=str(benchmark).strip(),
            mode=mode,
            lookback=lookback,
            pivot_window=pivot_window,
            min_score=min_score,
            corr_window=corr_window,
            excess_window=excess_window,
            max_corr=max_corr,
            min_excess=min_excess,
            limit=limit,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)

    _attach_returns(rows)
    _attach_fsa(rows)
    return Response(
        {
            "mode": mode,
            "benchmark": str(benchmark).strip(),
            "industries": industries,
            "ides": ides,
            "corr_window": corr_window,
            "excess_window": excess_window,
            "max_corr": max_corr,
            "min_excess": min_excess,
            "count": len(rows),
            "stocks": rows,
        }
    )


def _optional_float(payload, key):
    if key not in payload or payload.get(key) is None or payload.get(key) == "":
        return None
    return float(payload.get(key))


@api_view(["POST"])
def tech_industry_relative_scan(request):
    """Scan industry indices (default HY2) for correlation vs a benchmark index."""
    _ensure_kdb()
    level = str(request.data.get("level") or "2").strip() or "2"
    parents = request.data.get("parents") or request.data.get("industries") or []
    ides = request.data.get("ides") or []
    benchmark = request.data.get("benchmark") or "sh000001"

    if level not in {"1", "2", "3"}:
        return Response({"error": "level must be '1', '2', or '3'"}, status=400)
    if not isinstance(parents, list):
        return Response({"error": "parents must be a list"}, status=400)
    if not isinstance(ides, list):
        return Response({"error": "ides must be a list"}, status=400)

    try:
        corr_window = int(request.data.get("corr_window", 60))
        excess_window = int(request.data.get("excess_window", 21))
        history_days = int(request.data.get("history_days", 400))
        limit = int(request.data.get("limit", 500))
        max_corr = _optional_float(request.data, "max_corr")
        min_corr = _optional_float(request.data, "min_corr")
        min_excess = _optional_float(request.data, "min_excess")
    except (TypeError, ValueError):
        return Response({"error": "扫描参数格式不正确"}, status=400)

    try:
        rows = scan_industry_relative(
            KDB(),
            level=level,
            parents=parents or None,
            ides=ides or None,
            benchmark_ide=str(benchmark).strip(),
            history_days=history_days,
            corr_window=corr_window,
            excess_window=excess_window,
            max_corr=max_corr,
            min_corr=min_corr,
            min_excess=min_excess,
            limit=limit,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)

    _attach_returns(rows)
    return Response(
        {
            "level": level,
            "benchmark": str(benchmark).strip(),
            "parents": parents,
            "ides": ides,
            "corr_window": corr_window,
            "excess_window": excess_window,
            "max_corr": max_corr,
            "min_corr": min_corr,
            "min_excess": min_excess,
            "count": len(rows),
            "sectors": rows,
        }
    )


@api_view(["GET", "POST"])
def screen_stocks(request):
    """Screen stocks by industries, report date, and/or FSA ratio conditions."""
    _ensure_kdb()
    kdb = KDB()
    if not hasattr(kdb, "fsa_report_dates"):
        _reload_kdb_helpers()
        kdb = KDB()

    if request.method == "GET":
        return Response({"report_dates": kdb.fsa_report_dates()})

    industries = request.data.get("industries") or []
    ratios = request.data.get("ratios") or []
    report_date = request.data.get("report_date") or None

    if not isinstance(industries, list):
        return Response({"error": "industries must be a list"}, status=400)
    if not isinstance(ratios, list):
        return Response({"error": "ratios must be a list"}, status=400)
    if not industries and not ratios and not str(report_date or "").strip():
        return Response({"error": "请至少设置一个行业、报告期或比率条件"}, status=400)

    rows = kdb.screen_stocks(
        industries=industries,
        ratios=ratios,
        report_date=report_date,
    )
    _attach_returns(rows)
    return Response(
        {
            "stocks": rows,
            "count": len(rows),
            "industries": industries,
            "ratios": ratios,
            "report_date": report_date,
        }
    )


@api_view(["GET"])
def ai_advice_models(request):
    """Return whether AI advice models are trained and meta info."""
    return Response(model_status())


@api_view(["POST"])
def ai_advice_scan(request):
    """Run LightGBM advice pipeline and return ranked buy suggestions."""
    _ensure_kdb()
    industries = request.data.get("industries") or []
    ides = request.data.get("ides") or []
    pool_category = (request.data.get("pool_category") or "").strip() or None
    username = _pool_username(request) or "default"

    if not isinstance(industries, list):
        return Response({"error": "industries must be a list"}, status=400)
    if not isinstance(ides, list):
        return Response({"error": "ides must be a list"}, status=400)
    if not industries and not ides and not pool_category:
        return Response({"error": "请至少选择一个行业、股票池或股票代码"}, status=400)

    try:
        limit = int(request.data.get("limit", 50))
        top_k = int(request.data.get("top_k", 200))
        p_min = float(request.data.get("p_min", 0.35))
    except (TypeError, ValueError):
        return Response({"error": "扫描参数格式不正确"}, status=400)

    require_channel = request.data.get("require_channel", False)
    if isinstance(require_channel, str):
        require_channel = require_channel.strip().lower() not in {"0", "false", "no"}
    drop_anomaly = request.data.get("drop_anomaly", True)
    if isinstance(drop_anomaly, str):
        drop_anomaly = drop_anomaly.strip().lower() not in {"0", "false", "no"}

    try:
        rows, stats = run_buy_advice(
            KDB(),
            ides=ides or None,
            industries=industries or None,
            pool_category=pool_category,
            username=username,
            limit=limit,
            top_k=top_k,
            p_min=p_min,
            require_channel=bool(require_channel),
            drop_anomaly=bool(drop_anomaly),
            return_stats=True,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)

    _attach_returns(rows)
    _attach_fsa(rows)
    return Response(
        {
            "count": len(rows),
            "stocks": rows,
            "stats": stats,
            "industries": industries,
            "ides": ides,
            "pool_category": pool_category,
            "p_min": p_min,
            "require_channel": bool(require_channel),
            "drop_anomaly": bool(drop_anomaly),
            "limit": limit,
            "disclaimer": "建议仅供参考，确认仅记录客户意向，不构成投资建议，亦不自动下单。",
        }
    )


@api_view(["POST"])
def ai_advice_confirm(request):
    """Record manual buy/skip intent for an AI advice row (no brokerage order)."""
    _ensure_kdb()
    ide = (request.data.get("ide") or "").strip()
    action = (request.data.get("action") or "").strip().lower()
    note = request.data.get("note") or ""
    username = _pool_username(request) or "default"
    score = request.data.get("score")
    payload = request.data.get("payload") or {}

    try:
        if score is not None and score != "":
            score = float(score)
        else:
            score = None
    except (TypeError, ValueError):
        return Response({"error": "score must be a number"}, status=400)

    try:
        result = confirm_advice(
            KDB(),
            ide=ide,
            action=action,
            username=username,
            note=str(note),
            score=score,
            payload=payload if isinstance(payload, dict) else {},
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)

    return Response(result)
