"""Ascending price-channel detection."""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"date", "open", "close", "high", "low", "volume"}


def fit_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Fit a straight line and return ``(slope, intercept, R²)``."""
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    residual_sum = float(np.sum((y - predicted) ** 2))
    total_sum = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - residual_sum / total_sum if total_sum > 0 else 0.0
    return float(slope), float(intercept), float(r_squared)


def detect_ascending_channel(
    df: pd.DataFrame,
    *,
    lookback: int = 80,
    pivot_window: int = 5,
    min_score: int = 6,
) -> dict:
    """Judge whether the latest bars form an ascending price channel."""
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"OHLC data missing columns: {missing}")

    lookback = max(60, int(lookback))
    pivot_window = max(3, int(pivot_window))
    min_score = max(1, min(int(min_score), 7))

    if len(df) < lookback:
        return {
            "is_channel": False,
            "score": 0,
            "score_text": "0/7",
            "reason": "历史数据不足",
        }

    data = df.tail(lookback).copy().reset_index(drop=True)
    x = np.arange(len(data), dtype=float)
    data["ma20"] = data["close"].rolling(20).mean()
    data["ma60"] = data["close"].rolling(60).mean()

    local_low = data["low"].eq(
        data["low"].rolling(pivot_window, center=True).min()
    )
    local_high = data["high"].eq(
        data["high"].rolling(pivot_window, center=True).max()
    )
    low_indexes = np.flatnonzero(local_low.fillna(False).to_numpy())
    high_indexes = np.flatnonzero(local_high.fillna(False).to_numpy())

    if len(low_indexes) < 3 or len(high_indexes) < 3:
        return {
            "is_channel": False,
            "score": 0,
            "score_text": "0/7",
            "reason": "有效高点或低点不足",
        }

    low_slope, low_intercept, low_r2 = fit_line(
        low_indexes.astype(float),
        data.loc[low_indexes, "low"].to_numpy(dtype=float),
    )
    high_slope, high_intercept, high_r2 = fit_line(
        high_indexes.astype(float),
        data.loc[high_indexes, "high"].to_numpy(dtype=float),
    )

    lower_channel = low_slope * x + low_intercept
    upper_channel = high_slope * x + high_intercept
    average_price = float(data["close"].mean())
    if not np.isfinite(average_price) or average_price <= 0:
        return {
            "is_channel": False,
            "score": 0,
            "score_text": "0/7",
            "reason": "价格数据无效",
        }

    low_slope_percent = low_slope / average_price * 100
    high_slope_percent = high_slope / average_price * 100
    parallel_error = abs(high_slope - low_slope) / max(
        abs(high_slope),
        abs(low_slope),
        1e-9,
    )

    channel_width = upper_channel - lower_channel
    channel_mid = (upper_channel + lower_channel) / 2
    valid_mid = np.abs(channel_mid) > 1e-9
    if valid_mid.all():
        channel_width_percent = float(np.mean(channel_width / channel_mid * 100))
    else:
        channel_width_percent = float("nan")

    current_close = float(data["close"].iloc[-1])
    inside_channel = bool(
        lower_channel[-1] * 0.98
        <= current_close
        <= upper_channel[-1] * 1.02
    )
    moving_average_up = bool(
        pd.notna(data["ma60"].iloc[-1])
        and data["ma20"].iloc[-1] > data["ma60"].iloc[-1]
        and data["ma20"].iloc[-1] > data["ma20"].iloc[-6]
    )

    conditions = {
        "低点趋势向上": bool(low_slope_percent > 0.03),
        "高点趋势向上": bool(high_slope_percent > 0.03),
        "上下轨大致平行": bool(parallel_error < 0.55),
        "趋势线拟合有效": bool(low_r2 > 0.25 and high_r2 > 0.25),
        "通道宽度合理": bool(
            np.all(channel_width > 0)
            and np.isfinite(channel_width_percent)
            and 3 <= channel_width_percent <= 30
        ),
        "当前价格在通道内": inside_channel,
        "均线趋势向上": moving_average_up,
    }
    passed_count = sum(conditions.values())

    return {
        "is_channel": passed_count >= min_score,
        "score": passed_count,
        "score_text": f"{passed_count}/7",
        "conditions": conditions,
        "metrics": {
            "下轨每日斜率百分比": round(float(low_slope_percent), 4),
            "上轨每日斜率百分比": round(float(high_slope_percent), 4),
            "平行误差": round(float(parallel_error), 4),
            "下轨R²": round(float(low_r2), 4),
            "上轨R²": round(float(high_r2), 4),
            "通道平均宽度百分比": round(float(channel_width_percent), 2),
        },
        "as_of": str(pd.Timestamp(data["date"].iloc[-1]).date()),
        "data": data,
        "lower_channel": lower_channel,
        "upper_channel": upper_channel,
        "low_indexes": low_indexes,
        "high_indexes": high_indexes,
    }
