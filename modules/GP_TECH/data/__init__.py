"""Market-data adapters for technical analysis."""

from .quotes import load_fdk_ohlc, load_forward_ohlc, load_raw_ohlc

__all__ = ["load_fdk_ohlc", "load_forward_ohlc", "load_raw_ohlc"]
