"""TDX data update config and background jobs (GP_TDX)."""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from django.conf import settings

from GP_KDB import KDB
from GP_TDX import Config
from GP_TDX.cw import upload_all_cw
from GP_TDX.db import TdxDB
from GP_TDX.dividend import upload_dividend
from GP_TDX.quote import recent_trading_dates, upload_all_quotes
from GP_TDX.stockinfo import upload_all_stockinfo

from . import fsa_update

DEFAULT_TDX_PATH = getattr(settings, "TDX_DEFAULT_PATH", r"C:\zd_zsone")
CONFIG_PATH = Path(settings.BASE_DIR) / "tdx_config.json"

TASK_CHOICES = ("quote", "cw", "dividend", "stockinfo", "fsa", "report", "industry_profit")

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mongo_host_label(uri: str) -> str:
    parsed = urlparse(uri)
    return parsed.netloc or uri


def _read_saved_tdx_path() -> str:
    if CONFIG_PATH.is_file():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("tdx_path") or DEFAULT_TDX_PATH
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_TDX_PATH


def load_config() -> dict[str, Any]:
    tdx_path = _read_saved_tdx_path()
    payload = inspect_tdx_path(tdx_path)
    payload["mongo_uri"] = getattr(settings, "GP_TDX_MONGO_URI", Config().mongo_uri)
    payload["mongo_db"] = getattr(settings, "GP_TDX_MONGO_DB", Config().mongo_db)
    payload["mongo_host"] = _mongo_host_label(payload["mongo_uri"])
    return payload


def save_config(tdx_path: str) -> dict[str, Any]:
    tdx_path = os.path.normpath(tdx_path.strip())
    CONFIG_PATH.write_text(
        json.dumps({"tdx_path": tdx_path}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return load_config()


def inspect_tdx_path(tdx_path: str) -> dict[str, Any]:
    tdx_path = os.path.normpath(tdx_path.strip()) if tdx_path else DEFAULT_TDX_PATH
    cfg = Config(
        tdx_path=tdx_path,
        mongo_uri=getattr(settings, "GP_TDX_MONGO_URI", Config().mongo_uri),
        mongo_db=getattr(settings, "GP_TDX_MONGO_DB", Config().mongo_db),
    )
    checks = {
        "root": os.path.isdir(tdx_path),
        "vipdoc": os.path.isdir(cfg.vipdoc_path),
        "cw": os.path.isdir(cfg.cw_path),
        "gbbq": os.path.isfile(cfg.gbbq_path),
    }
    return {
        "tdx_path": tdx_path,
        "default_tdx_path": DEFAULT_TDX_PATH,
        "path_exists": checks["root"],
        "checks": checks,
        "ready": all(checks.values()),
        "paths": {
            "vipdoc": cfg.vipdoc_path,
            "cw": cfg.cw_path,
            "gbbq": cfg.gbbq_path,
        },
    }


def _make_config(tdx_path: str | None) -> Config:
    path = os.path.normpath((tdx_path or _read_saved_tdx_path()).strip())
    return Config(
        tdx_path=path,
        mongo_uri=getattr(settings, "GP_TDX_MONGO_URI", Config().mongo_uri),
        mongo_db=getattr(settings, "GP_TDX_MONGO_DB", Config().mongo_db),
    )


def _ensure_kdb() -> KDB:
    kdb = KDB()
    if not kdb.is_configured:
        kdb.setting(uri=getattr(settings, "GP_TDX_MONGO_URI", None))
    return kdb


def _resolve_report_options(options: dict[str, Any]) -> dict[str, Any]:
    kind = (options.get("kind") or "all").strip().lower()
    if kind not in {"all", "research", "filings"}:
        kind = "all"

    max_pages = options.get("max_pages")
    if max_pages is not None:
        try:
            max_pages = max(1, int(max_pages))
        except (TypeError, ValueError):
            max_pages = 20
    else:
        max_pages = 20

    begin_time = (options.get("begin_time") or "").strip() or None
    end_time = (options.get("end_time") or "").strip() or None
    download_pdf = bool(options.get("download_pdf"))
    stock_list = (options.get("stock_list") or "").strip() or None

    pdf_limit = options.get("pdf_limit")
    if pdf_limit is not None:
        try:
            pdf_limit = max(1, int(pdf_limit))
        except (TypeError, ValueError):
            pdf_limit = None

    return {
        "kind": kind,
        "download_pdf": download_pdf,
        "begin_time": begin_time,
        "end_time": end_time,
        "max_pages": max_pages,
        "stock_list": stock_list,
        "pdf_limit": pdf_limit,
    }


def _resolve_quote_options(config: Config, options: dict[str, Any]) -> dict[str, Any]:
    scope = options.get("scope", "recent")
    if scope == "all":
        return {
            "date": options.get("date"),
            "date_from": options.get("date_from"),
            "date_to": options.get("date_to"),
            "year": options.get("year"),
            "ides": options.get("ides"),
        }

    if options.get("date") or options.get("date_from") or options.get("date_to") or options.get("year"):
        return {
            "date": options.get("date"),
            "date_from": options.get("date_from"),
            "date_to": options.get("date_to"),
            "year": options.get("year"),
            "ides": options.get("ides"),
        }

    n = int(options.get("recent_trading_days", 10))
    dates = recent_trading_dates(config, n=n)
    return {
        "date_from": dates[0],
        "date_to": dates[-1],
        "ides": options.get("ides"),
        "_recent_trading_days": n,
        "_trading_dates": dates,
    }


def _resolve_cw_options(options: dict[str, Any]) -> dict[str, Any]:
    scope = options.get("scope", "recent")
    if scope == "all":
        return {
            "quarter": options.get("quarter"),
            "report_date": options.get("report_date"),
        }

    if options.get("quarter") or options.get("report_date"):
        return {
            "quarter": options.get("quarter"),
            "report_date": options.get("report_date"),
        }

    n = int(options.get("recent_quarters", 3))
    return {"recent_quarters": n}


def _verify_quote_upload(
    config: Config,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    tdx_db = TdxDB(config)
    try:
        col = tdx_db.collection("QUATE")
        query: dict[str, Any] = {}
        if date_from and date_to:
            query["DT"] = {"$gte": date_from, "$lte": date_to}
        elif date_from:
            query["DT"] = {"$gte": date_from}
        elif date_to:
            query["DT"] = {"$lte": date_to}

        docs_in_range = col.count_documents(query) if query else col.estimated_document_count()
        latest = col.find_one(sort=[("DT", -1), ("IDE", 1)])
        distinct_dates = sorted(col.distinct("DT", query)) if query else []
        return {
            "collection": "tdx.QUATE",
            "docs_in_range": docs_in_range,
            "distinct_dates_in_range": len(distinct_dates),
            "date_from": date_from,
            "date_to": date_to,
            "latest_doc": latest,
        }
    finally:
        tdx_db.close()


def _verify_cw_upload(config: Config) -> dict[str, Any]:
    tdx_db = TdxDB(config)
    try:
        col = tdx_db.collection("CW")
        latest = col.find_one(sort=[("REPORTDATE", -1), ("IDE", 1)])
        return {
            "collection": "tdx.CW",
            "estimated_documents": col.estimated_document_count(),
            "latest_doc": latest,
        }
    finally:
        tdx_db.close()


def _resolve_fsa_options(options: dict[str, Any]) -> dict[str, Any]:
    scope = options.get("scope", "recent")
    if scope == "all":
        return {"recent_quarters": None}
    return {"recent_quarters": int(options.get("recent_quarters", 40))}


def _log_task_start(task: str, config: Config | None, options: dict[str, Any]) -> None:
    print(f"\n[GP_TDX] start {task}", flush=True)
    if config:
        print(f"  tdx_path: {config.tdx_path}", flush=True)
        print(f"  mongo: {config.mongo_db} @ {_mongo_host_label(config.mongo_uri)}", flush=True)
    if options:
        print(f"  options: {options}", flush=True)


def _run_task(task: str, config: Config | None, options: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []

    def on_error(path_or_ide: str, exc: Exception) -> None:
        errors.append({"target": path_or_ide, "error": str(exc)})
        print(f"[GP_TDX] error {path_or_ide}: {exc}", file=sys.stderr, flush=True)

    if task == "fsa":
        _log_task_start(task, config, options)
        fsa_opts = _resolve_fsa_options(options)
        kdb = _ensure_kdb()
        result = fsa_update.upload_all_fsa_ratios(
            kdb=kdb,
            recent_quarters=fsa_opts.get("recent_quarters"),
            on_error=on_error,
            show_progress=True,
        )
        if errors:
            result = dict(result)
            result["error_details"] = errors[:50]
        print(f"[GP_FSA] done {task}: {result}", flush=True)
        return result

    if task == "industry_profit":
        from GP_KDB.industry_profit.aggregate import build_industry_profit_yearly

        _log_task_start(task, config, options)
        kdb = _ensure_kdb()
        levels_raw = options.get("levels") or "1,2"
        if isinstance(levels_raw, str):
            levels = tuple(
                part.strip().replace("HY", "")
                for part in levels_raw.split(",")
                if part.strip()
            ) or ("1", "2")
        else:
            levels = tuple(str(x).replace("HY", "") for x in levels_raw) or ("1", "2")

        def on_progress(message: str) -> None:
            print(f"[industry_profit] {message}", flush=True)

        result = build_industry_profit_yearly(
            kdb,
            levels=levels,
            on_progress=on_progress,
        )
        try:
            from .heatmap_cache import clear_cached

            clear_cached("industry_profit_growth:")
        except Exception:
            pass
        print(f"[GP_KDB] done {task}: {result}", flush=True)
        return result

    if task == "report":
        from GP_EM import Config as EmConfig
        from GP_EM import upload_reports

        _log_task_start(task, config, options)
        report_opts = _resolve_report_options(options)
        em_config = EmConfig(
            mongo_uri=getattr(settings, "GP_TDX_MONGO_URI", EmConfig().mongo_uri),
            mongo_db=getattr(settings, "GP_TDX_MONGO_DB", EmConfig().mongo_db),
        )
        if report_opts.get("begin_time"):
            em_config.begin_time = report_opts["begin_time"]
        if report_opts.get("end_time"):
            em_config.end_time = report_opts["end_time"]
        result = upload_reports(
            config=em_config,
            kind=report_opts["kind"],
            download_pdf=report_opts["download_pdf"],
            begin_time=report_opts.get("begin_time"),
            end_time=report_opts.get("end_time"),
            max_pages=report_opts.get("max_pages"),
            stock_list=report_opts.get("stock_list"),
            pdf_limit=report_opts.get("pdf_limit"),
            on_error=on_error,
            show_progress=True,
        )
        if errors:
            result = dict(result)
            result["error_details"] = errors[:50]
        print(f"[GP_EM] done {task}: {result}", flush=True)
        return result

    if not config:
        raise ValueError("TDX config is required for this task")

    _log_task_start(task, config, options)
    tdx_db = TdxDB(config)

    try:
        if task == "quote":
            quote_opts = _resolve_quote_options(config, options)
            meta = {
                k: quote_opts.pop(k)
                for k in ("_recent_trading_days", "_trading_dates")
                if k in quote_opts
            }
            result = upload_all_quotes(
                config=config,
                db=tdx_db,
                date=quote_opts.get("date"),
                date_from=quote_opts.get("date_from"),
                date_to=quote_opts.get("date_to"),
                year=quote_opts.get("year"),
                ides=quote_opts.get("ides"),
                on_error=on_error,
                show_progress=True,
            )
            if meta:
                result = dict(result)
                if meta.get("_recent_trading_days") is not None:
                    result["recent_trading_days"] = meta["_recent_trading_days"]
                if meta.get("_trading_dates") is not None:
                    result["trading_dates"] = meta["_trading_dates"]

            kdb = _ensure_kdb()
            sync_result = kdb.sync_dates_from_quate(start_dt=quote_opts.get("date_from"))
            result = dict(result)
            result["kdb_dates_sync"] = sync_result
            result["mongodb_verify"] = _verify_quote_upload(
                config,
                date_from=quote_opts.get("date_from"),
                date_to=quote_opts.get("date_to"),
            )
        elif task == "cw":
            cw_opts = _resolve_cw_options(options)
            result = upload_all_cw(
                config=config,
                db=tdx_db,
                quarter=cw_opts.get("quarter"),
                report_date=cw_opts.get("report_date"),
                recent_quarters=cw_opts.get("recent_quarters"),
                on_error=on_error,
                show_progress=True,
            )
            result = dict(result)
            result["mongodb_verify"] = _verify_cw_upload(config)
        elif task == "dividend":
            result = upload_dividend(
                config=config,
                db=tdx_db,
                year=options.get("year"),
            )
        elif task == "stockinfo":
            result = upload_all_stockinfo(
                config=config,
                db=tdx_db,
                on_error=on_error,
                show_progress=True,
            )
        else:
            raise ValueError(f"Unknown task: {task}")
    finally:
        tdx_db.close()

    if errors:
        result = dict(result)
        result["error_details"] = errors[:50]

    print(f"[GP_TDX] done {task}: {result}", flush=True)
    return result


def start_update_job(task: str, *, tdx_path: str | None = None, options: dict[str, Any] | None = None) -> dict[str, Any]:
    if task not in TASK_CHOICES:
        raise ValueError(f"Unsupported task: {task}")

    opts = options or {}

    if task in {"fsa", "report", "industry_profit"}:
        config = _make_config(tdx_path)
        config_info = {"tdx_path": config.tdx_path, "ready": True}
    else:
        config_info = inspect_tdx_path(tdx_path or load_config()["tdx_path"])
        if not config_info["ready"]:
            raise ValueError("通达信数据目录不完整，请检查路径设置")
        config = _make_config(config_info["tdx_path"])

    job_id = uuid.uuid4().hex

    job = {
        "id": job_id,
        "task": task,
        "status": "running",
        "tdx_path": config_info["tdx_path"],
        "mongo_db": config.mongo_db,
        "mongo_host": _mongo_host_label(config.mongo_uri),
        "options": opts,
        "started_at": _utc_now(),
        "finished_at": None,
        "result": None,
        "error": None,
    }

    def worker() -> None:
        try:
            result = _run_task(task, config, opts)
            with _jobs_lock:
                job["status"] = "completed"
                job["result"] = _json_safe(result)
                job["finished_at"] = _utc_now()
        except Exception as exc:
            with _jobs_lock:
                job["status"] = "failed"
                job["error"] = str(exc)
                job["finished_at"] = _utc_now()
            print(f"[GP_TDX] failed {task}: {exc}", file=sys.stderr, flush=True)

    with _jobs_lock:
        _jobs[job_id] = job

    threading.Thread(target=worker, daemon=True).start()
    return {
        "job_id": job_id,
        "task": task,
        "status": "running",
        "started_at": job["started_at"],
        "mongo_db": job["mongo_db"],
        "mongo_host": job["mongo_host"],
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def get_job(job_id: str) -> dict[str, Any] | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        out = dict(job)
        result = out.get("result")
        if isinstance(result, dict):
            out["result_summary"] = _summarize_result(out.get("task", ""), result)
        return out


def _summarize_result(task: str, result: dict[str, Any] | None) -> str:
    if not result or not isinstance(result, dict):
        return ""

    parts: list[str] = []
    if task == "quote":
        if result.get("files") is not None:
            parts.append(f"文件 {result['files']}")
        if result.get("records") is not None:
            parts.append(f"记录 {result['records']}")
        verify = result.get("mongodb_verify") or {}
        if verify.get("latest_doc", {}).get("DT"):
            parts.append(f"最新 {verify['latest_doc']['DT']}")
    elif task == "cw":
        if result.get("files") is not None:
            parts.append(f"文件 {result['files']}")
        if result.get("records") is not None:
            parts.append(f"记录 {result['records']}")
    elif task == "fsa":
        if result.get("stocks") is not None:
            parts.append(f"股票 {result['stocks']}")
        if result.get("rows") is not None:
            parts.append(f"行 {result['rows']}")
    elif task == "industry_profit":
        if result.get("rows") is not None:
            parts.append(f"行 {result['rows']}")
        if result.get("years"):
            parts.append(f"年份 {len(result['years'])}")
        if result.get("levels"):
            parts.append(f"层级 {','.join(str(x) for x in result['levels'])}")
    elif task == "report":
        for key in ("research", "filings", "research_upserted", "filing_upserted"):
            if result.get(key) is not None:
                parts.append(f"{key} {result[key]}")
    else:
        for key in ("upserted", "profiles", "records", "stocks"):
            if result.get(key) is not None:
                parts.append(f"{key} {result[key]}")

    return " · ".join(parts[:4])


def _job_list_item(job: dict[str, Any]) -> dict[str, Any]:
    result = job.get("result")
    return {
        "id": job.get("id"),
        "task": job.get("task"),
        "status": job.get("status"),
        "tdx_path": job.get("tdx_path"),
        "mongo_db": job.get("mongo_db"),
        "mongo_host": job.get("mongo_host"),
        "options": job.get("options"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "error": job.get("error"),
        "result_summary": _summarize_result(job.get("task", ""), result if isinstance(result, dict) else None),
    }


def list_jobs(*, limit: int = 50) -> dict[str, Any]:
    """Recent update jobs (in-memory, current process lifetime)."""
    limit = max(1, min(int(limit), 200))
    with _jobs_lock:
        jobs = sorted(_jobs.values(), key=lambda j: j.get("started_at") or "", reverse=True)[:limit]

    items = [_job_list_item(dict(job)) for job in jobs]
    summary = {
        "total": len(items),
        "completed": sum(1 for j in items if j.get("status") == "completed"),
        "running": sum(1 for j in items if j.get("status") == "running"),
        "failed": sum(1 for j in items if j.get("status") == "failed"),
    }

    last_success: dict[str, str | None] = {}
    for item in items:
        if item.get("status") != "completed":
            continue
        task = item.get("task")
        if task and task not in last_success:
            last_success[task] = item.get("finished_at")

    return {
        "jobs": items,
        "count": len(items),
        "summary": summary,
        "last_success": last_success,
    }


def list_ratio_fields() -> dict[str, object]:
    return {
        "ratios": fsa_update.list_ratio_fields(),
        "target_collection": "tdx.FSA",
        "options": {
            "scope": "recent",
            "recent_quarters": 40,
            "scopes": [
                {"value": "recent", "label": "最新 N 个季度"},
                {"value": "all", "label": "全部季度"},
            ],
        },
    }


def list_report_options() -> dict[str, object]:
    from GP_EM import COL_FILING, COL_RESEARCH, DEFAULT_CONFIG

    return {
        "target_collections": [f"tdx.{COL_RESEARCH}", f"tdx.{COL_FILING}"],
        "pdf_root": DEFAULT_CONFIG.pdf_root,
        "options": {
            "kind": "all",
            "download_pdf": False,
            "max_pages": 20,
            "begin_time": DEFAULT_CONFIG.begin_time,
            "end_time": DEFAULT_CONFIG.end_time,
            "kinds": [
                {"value": "all", "label": "研报 + 定期报告"},
                {"value": "research", "label": "仅研报"},
                {"value": "filings", "label": "仅定期报告（年报/半年报/季报）"},
            ],
            "pdf_modes": [
                {"value": False, "label": "仅同步信息（在线浏览 pdf_url）"},
                {"value": True, "label": "同步信息并本地下载 PDF"},
            ],
        },
    }


def list_tasks() -> list[dict[str, object]]:
    return [
        {
            "key": "quote",
            "label": "股价更新",
            "description": "从 vipdoc 日 K 线导入 tdx.QUATE，并同步 kdb.dates 交易日历",
            "options": {
                "scope": "recent",
                "recent_trading_days": 10,
                "scopes": [
                    {"value": "recent", "label": "最新 N 个交易日"},
                    {"value": "all", "label": "全部历史"},
                ],
            },
        },
        {
            "key": "cw",
            "label": "财务更新",
            "description": "从 gpcw*.dat 导入 tdx.CW 财务报表",
            "options": {
                "scope": "recent",
                "recent_quarters": 3,
                "scopes": [
                    {"value": "recent", "label": "最新 N 个季度"},
                    {"value": "all", "label": "全部季度"},
                ],
            },
        },
        {
            "key": "dividend",
            "label": "分红更新",
            "description": "从 gbbq 导入分红与股本变动 (FHZGB / STOCK_PKVZGB)",
        },
        {
            "key": "stockinfo",
            "label": "股票信息",
            "description": "更新 STOCK 列表与 F10 公司资料",
        },
        {
            "key": "industry_profit",
            "label": "行业利润预聚合",
            "description": "按行业+年报汇总归母净利润，写入 tdx.INDUSTRY_PROFIT_YEARLY",
            "options": {
                "levels": "1,2",
            },
        },
    ]
