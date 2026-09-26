"""Build labeled channel-entry learning samples.

Event: ascending-channel ``entered`` on as_of.
Labels:
  - y_alpha: stock vs HY1 industry excess > 5%, peak MDD < 8%, no lower-rail break
  - y_sector: HY1 industry vs market (sh000001) excess > 0
Drawdown: peak-to-trough from as_of close through future horizon.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from GP_KDB.utils import security_type
from GP_TECH.channel.entered import detect_channel_state
from GP_TECH.data.quotes import load_forward_ohlc
from GP_TECH.relative import closes_series

from ..config import (
    CHANNEL_FEATURE_COLUMNS,
    CHANNEL_SAMPLES_META_PATH,
    CHANNEL_SAMPLES_PATH,
    DATA_DIR,
    DEFAULT_CHANNEL_SAMPLE_CONFIG,
    DEFAULT_FEATURE_CONFIG,
    FEATURE_COLUMNS,
    ChannelSampleConfig,
    FeatureConfig,
)
from .builders import build_feature_row

__all__ = [
    "assign_split",
    "build_channel_training_frame",
    "save_channel_samples",
]


def _candidate_ides(kdb, max_ides: int, ides: list[str] | None = None) -> list[str]:
    """Prefer sh/sz A-shares; skip empty ide strings."""
    max_ides = max(1, int(max_ides))
    if ides:
        return [ide for ide in dict.fromkeys(ides) if security_type(ide) == "stock"][:max_ides]

    all_ides = [ide for ide in (kdb.stocksIDEs() or []) if security_type(ide) == "stock"]
    # Main-board / ChiNext / STAR first — BJ quotes are often sparse in local DB.
    preferred = [ide for ide in all_ides if ide.startswith(("sh", "sz"))]
    others = [ide for ide in all_ides if not ide.startswith(("sh", "sz"))]
    ordered = preferred + others
    return ordered[:max_ides]


def _hy1_meta(info: dict | None) -> tuple[str, str]:
    """Return ``(hy1_name, hy1_ide)`` from StockInfo."""
    if not info:
        return "", ""
    hy1 = info.get("HY1")
    if isinstance(hy1, (list, tuple)) and len(hy1) >= 2:
        return str(hy1[0] or ""), str(hy1[1] or "")
    if isinstance(hy1, dict):
        return str(hy1.get("name") or hy1.get("IDS") or ""), str(hy1.get("ide") or hy1.get("IDE") or "")
    return "", ""


def _price_on(closes: pd.Series, as_of: pd.Timestamp) -> float | None:
    if closes is None or closes.empty:
        return None
    hist = closes.loc[:as_of]
    if hist.empty:
        return None
    value = float(hist.iloc[-1])
    return value if math.isfinite(value) and value > 0 else None


def _future_closes(
    closes: pd.Series,
    as_of: pd.Timestamp,
    horizon: int,
) -> pd.Series | None:
    """Return the next ``horizon`` closes strictly after as_of."""
    future = closes.loc[closes.index > as_of]
    if len(future) < horizon:
        return None
    return future.iloc[:horizon]


def _aligned_horizon_prices(
    stock: pd.Series,
    industry: pd.Series,
    market: pd.Series,
    as_of: pd.Timestamp,
    horizon: int,
) -> tuple[float, float, float, float, float, float, pd.Series] | None:
    """Point-in-time P0/I0/M0 and H-step-ahead P1/I1/M1 on common future dates."""
    p0 = _price_on(stock, as_of)
    i0 = _price_on(industry, as_of)
    m0 = _price_on(market, as_of)
    if p0 is None or i0 is None or m0 is None:
        return None

    common = stock.index.intersection(industry.index).intersection(market.index)
    future_idx = common[common > as_of]
    if len(future_idx) < horizon:
        return None
    end = future_idx[horizon - 1]
    p1 = float(stock.loc[end])
    i1 = float(industry.loc[end])
    m1 = float(market.loc[end])
    if min(p1, i1, m1) <= 0 or not all(math.isfinite(x) for x in (p1, i1, m1)):
        return None
    stock_path = stock.loc[(stock.index > as_of) & (stock.index <= end)]
    if len(stock_path) < horizon:
        # Fill from stock's own calendar if common calendar thinned stock bars
        stock_path = _future_closes(stock, as_of, horizon)
        if stock_path is None:
            return None
    return p0, i0, m0, p1, i1, m1, stock_path


def peak_mdd(path: pd.Series, p0: float) -> float | None:
    """Peak-to-trough max drawdown from as_of close through future path (fraction)."""
    if path is None or len(path) == 0 or not math.isfinite(p0) or p0 <= 0:
        return None
    values = [p0, *[float(x) for x in path.to_numpy(dtype=float)]]
    peak = values[0]
    max_dd = 0.0
    for price in values:
        if not math.isfinite(price) or price <= 0:
            continue
        peak = max(peak, price)
        dd = (peak - price) / peak
        if dd > max_dd:
            max_dd = dd
    return round(float(max_dd), 6)


def broke_lower_rail(path: pd.Series, lower_0: float, buffer: float) -> bool:
    if path is None or len(path) == 0 or not math.isfinite(lower_0):
        return True
    threshold = float(lower_0) * float(buffer)
    return bool((path.astype(float) < threshold).any())


def assign_split(as_of: str, cfg: ChannelSampleConfig) -> str:
    day = str(as_of)[:10]
    if day <= cfg.train_end:
        return "train"
    if day <= cfg.val_end:
        return "val"
    return "test"


def _channel_feature_dict(channel: dict, close: float) -> dict:
    metrics = channel.get("metrics") or {}
    lower = channel.get("lower_channel")
    upper = channel.get("upper_channel")
    lower_0 = float(lower[-1]) if lower is not None and len(lower) else float("nan")
    upper_0 = float(upper[-1]) if upper is not None and len(upper) else float("nan")
    width = upper_0 - lower_0
    if math.isfinite(width) and width > 1e-9 and math.isfinite(close):
        pos = (close - lower_0) / width
    else:
        pos = float("nan")
    return {
        "channel_score": int(channel.get("score") or 0),
        "channel_width_pct": metrics.get("通道平均宽度百分比"),
        "lower_slope_pct": metrics.get("下轨每日斜率百分比"),
        "upper_slope_pct": metrics.get("上轨每日斜率百分比"),
        "parallel_error": metrics.get("平行误差"),
        "price_in_channel_pos": round(float(pos), 4) if math.isfinite(pos) else None,
        "lower_0": round(lower_0, 6) if math.isfinite(lower_0) else None,
        "upper_0": round(upper_0, 6) if math.isfinite(upper_0) else None,
    }


def build_channel_training_frame(
    kdb,
    *,
    cfg: ChannelSampleConfig = DEFAULT_CHANNEL_SAMPLE_CONFIG,
    feature_cfg: FeatureConfig = DEFAULT_FEATURE_CONFIG,
    ides: list[str] | None = None,
    progress_every: int = 20,
) -> tuple[pd.DataFrame, dict]:
    """Scan channel-entry events and return ``(frame, stats)``."""
    days_needed = max(
        int(cfg.quote_days),
        max(cfg.min_history, cfg.channel_lookback, feature_cfg.history_days)
        + cfg.horizon
        + cfg.history_buffer,
    )
    market_ohlc = load_forward_ohlc(
        kdb,
        cfg.market_ide,
        days=days_needed,
        require_amount=False,
    )
    market_closes = closes_series(market_ohlc)
    if market_closes.empty:
        raise ValueError(f"无法加载大盘行情: {cfg.market_ide}")

    candidates = _candidate_ides(kdb, cfg.max_ides, ides)
    stats: dict = {
        "candidates": len(candidates),
        "events": 0,
        "rows": 0,
        "skip": Counter(),
    }
    industry_cache: dict[str, pd.Series] = {}
    rows: list[dict] = []

    for idx, ide in enumerate(candidates, start=1):
        if progress_every and idx % progress_every == 0:
            print(
                f"[channel-samples] {idx}/{len(candidates)} ide={ide} "
                f"rows={len(rows)} events={stats['events']}",
                flush=True,
            )

        info = kdb.StockInfo(ide) if hasattr(kdb, "StockInfo") else None
        hy1_name, hy1_ide = _hy1_meta(info)
        if not hy1_ide:
            stats["skip"]["no_hy1"] += 1
            continue

        if hy1_ide not in industry_cache:
            ind_ohlc = load_forward_ohlc(
                kdb,
                hy1_ide,
                days=days_needed,
                require_amount=False,
            )
            industry_cache[hy1_ide] = closes_series(ind_ohlc)
        industry_closes = industry_cache[hy1_ide]
        if industry_closes.empty:
            stats["skip"]["no_industry_quotes"] += 1
            continue

        ohlc = load_forward_ohlc(kdb, ide, days=days_needed, require_amount=False)
        if ohlc.empty or len(ohlc) < cfg.min_history + cfg.horizon:
            stats["skip"]["short_history"] += 1
            continue
        stock_closes = closes_series(ohlc)
        if stock_closes.empty:
            stats["skip"]["short_history"] += 1
            continue

        dates = list(pd.to_datetime(ohlc["date"]))
        # Candidate as_of positions: leave lookback on left, horizon on right.
        start_i = cfg.channel_lookback
        end_i = len(dates) - cfg.horizon
        if end_i <= start_i:
            stats["skip"]["short_history"] += 1
            continue

        for pos in range(start_i, end_i, max(1, int(cfg.scan_stride))):
            as_of = pd.Timestamp(dates[pos])
            hist = ohlc.iloc[: pos + 1].copy()
            if len(hist) < cfg.channel_lookback:
                continue

            channel = detect_channel_state(
                hist,
                mode=cfg.channel_mode,
                lookback=cfg.channel_lookback,
                pivot_window=cfg.channel_pivot_window,
                min_score=cfg.min_channel_score,
            )
            if not channel.get("is_match"):
                continue
            stats["events"] += 1

            aligned = _aligned_horizon_prices(
                stock_closes,
                industry_closes,
                market_closes,
                as_of,
                cfg.horizon,
            )
            if aligned is None:
                stats["skip"]["no_forward_window"] += 1
                continue
            p0, i0, m0, p1, i1, m1, stock_path = aligned

            ch_feats = _channel_feature_dict(channel, p0)
            lower_0 = ch_feats.get("lower_0")
            if lower_0 is None:
                stats["skip"]["no_lower_rail"] += 1
                continue

            r_stock = p1 / p0 - 1.0
            r_hy = i1 / i0 - 1.0
            r_mkt = m1 / m0 - 1.0
            stock_alpha = r_stock - r_hy
            sector_excess = r_hy - r_mkt
            max_dd = peak_mdd(stock_path, p0)
            if max_dd is None:
                stats["skip"]["bad_drawdown"] += 1
                continue
            broke = broke_lower_rail(stock_path, float(lower_0), cfg.lower_break_buffer)

            y_alpha = int(
                stock_alpha > cfg.alpha_excess_min
                and max_dd < cfg.alpha_max_dd
                and not broke
            )
            y_sector = int(sector_excess > cfg.sector_excess_min)

            feat = build_feature_row(
                stock_closes.loc[:as_of],
                market_closes.loc[:as_of],
                None,
                cfg=feature_cfg,
            )
            as_of_str = str(as_of.date())
            row = {
                "ide": ide,
                "name": (info or {}).get("IDS") or ide,
                "as_of": as_of_str,
                "split": assign_split(as_of_str, cfg),
                "hy1": hy1_name,
                "industry_ide": hy1_ide,
                "market_ide": cfg.market_ide,
                "r_stock": round(r_stock, 6),
                "r_hy": round(r_hy, 6),
                "r_mkt": round(r_mkt, 6),
                "stock_alpha": round(stock_alpha, 6),
                "sector_excess": round(sector_excess, 6),
                "max_dd_mdd": max_dd,
                "broke_lower": int(broke),
                "y_alpha": y_alpha,
                "y_sector": y_sector,
                **ch_feats,
                **feat,
            }
            rows.append(row)
            stats["rows"] += 1

    columns = [
        "ide",
        "name",
        "as_of",
        "split",
        "hy1",
        "industry_ide",
        "market_ide",
        "r_stock",
        "r_hy",
        "r_mkt",
        "stock_alpha",
        "sector_excess",
        "max_dd_mdd",
        "broke_lower",
        "y_alpha",
        "y_sector",
        "lower_0",
        "upper_0",
        *CHANNEL_FEATURE_COLUMNS,
        *FEATURE_COLUMNS,
    ]
    if not rows:
        frame = pd.DataFrame(columns=columns)
    else:
        frame = pd.DataFrame(rows)
        # Deduplicate CHANNEL_FEATURE already expanded via ch_feats keys
        keep = [c for c in columns if c in frame.columns]
        extras = [c for c in frame.columns if c not in keep]
        frame = frame[keep + extras]

    stats["skip"] = dict(stats["skip"])
    stats["y_alpha_rate"] = (
        float(frame["y_alpha"].mean()) if len(frame) and "y_alpha" in frame.columns else None
    )
    stats["y_sector_rate"] = (
        float(frame["y_sector"].mean()) if len(frame) and "y_sector" in frame.columns else None
    )
    if len(frame) and "split" in frame.columns:
        stats["split_counts"] = frame["split"].value_counts().to_dict()
    else:
        stats["split_counts"] = {}
    return frame, stats


def save_channel_samples(
    frame: pd.DataFrame,
    stats: dict,
    cfg: ChannelSampleConfig,
    *,
    out_path: Path = CHANNEL_SAMPLES_PATH,
    meta_path: Path = CHANNEL_SAMPLES_META_PATH,
) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(out_path)
    meta_path = Path(meta_path)
    if out_path.suffix.lower() == ".csv":
        frame.to_csv(out_path, index=False, encoding="utf-8-sig")
    else:
        frame.to_parquet(out_path, index=False)

    meta = {
        "config": asdict(cfg),
        "feature_columns": list(FEATURE_COLUMNS),
        "channel_feature_columns": list(CHANNEL_FEATURE_COLUMNS),
        "label_columns": ["y_alpha", "y_sector"],
        "drawdown": "peak_to_trough_mdd",
        "market_ide": cfg.market_ide,
        "stats": stats,
        "rows": int(len(frame)),
        "path": str(out_path),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta
