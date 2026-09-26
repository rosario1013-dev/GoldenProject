"""Default parameters for GP_TECH scanners."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelConfig:
    """Ascending-channel detection defaults."""

    history_days: int = 400
    lookback: int = 80
    pivot_window: int = 5
    min_score: int = 6


@dataclass(frozen=True)
class IndependentStrongConfig:
    """Low-corr + positive excess + ascending-channel defaults."""

    benchmark_ide: str = "sh000001"
    history_days: int = 400
    lookback: int = 80
    pivot_window: int = 5
    min_score: int = 6
    corr_window: int = 60
    excess_window: int = 21
    max_corr: float = 0.4
    min_excess: float = 0.0


@dataclass(frozen=True)
class IndustryRelativeConfig:
    """Industry-index vs benchmark correlation defaults."""

    benchmark_ide: str = "sh000001"
    level: str = "2"
    history_days: int = 400
    corr_window: int = 60
    excess_window: int = 21


DEFAULT_CHANNEL_CONFIG = ChannelConfig()
DEFAULT_INDEPENDENT_STRONG_CONFIG = IndependentStrongConfig()
DEFAULT_INDUSTRY_RELATIVE_CONFIG = IndustryRelativeConfig()
