"""GP_TECH — technical analysis and stock scanning."""

from .channel.ascending import detect_ascending_channel, fit_line
from .channel.entered import detect_channel_state
from .config import (
    ChannelConfig,
    DEFAULT_CHANNEL_CONFIG,
    DEFAULT_INDEPENDENT_STRONG_CONFIG,
    DEFAULT_INDUSTRY_RELATIVE_CONFIG,
    IndependentStrongConfig,
    IndustryRelativeConfig,
)
from .data.quotes import load_fdk_ohlc, load_forward_ohlc, load_raw_ohlc
from .indicators import (
    add_technical_indicators,
    calc_boll,
    calc_kdj,
    calc_macd,
    calc_rsi,
    calc_rsi_multi,
    detect_swing_turning_points,
    parse_indicator_kinds,
    recent_swings_for_ides,
    stock_indicators,
    stock_recent_swings,
    stock_swings,
)
from .relative import relative_metrics
from .scan import (
    scan_channel_stocks,
    scan_independent_strong_stocks,
    scan_industry_relative,
)

__all__ = [
    "ChannelConfig",
    "DEFAULT_CHANNEL_CONFIG",
    "DEFAULT_INDEPENDENT_STRONG_CONFIG",
    "DEFAULT_INDUSTRY_RELATIVE_CONFIG",
    "IndependentStrongConfig",
    "IndustryRelativeConfig",
    "add_technical_indicators",
    "calc_boll",
    "calc_kdj",
    "calc_macd",
    "calc_rsi",
    "calc_rsi_multi",
    "detect_ascending_channel",
    "detect_channel_state",
    "detect_swing_turning_points",
    "fit_line",
    "load_fdk_ohlc",
    "load_forward_ohlc",
    "load_raw_ohlc",
    "parse_indicator_kinds",
    "recent_swings_for_ides",
    "relative_metrics",
    "scan_channel_stocks",
    "scan_independent_strong_stocks",
    "scan_industry_relative",
    "stock_indicators",
    "stock_recent_swings",
    "stock_swings",
]

__version__ = "0.1.0"
