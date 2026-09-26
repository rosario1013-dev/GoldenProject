"""Default parameters for GP_AI pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = PACKAGE_ROOT / "artifacts"
DATA_DIR = PACKAGE_ROOT / "data"

FEATURE_COLUMNS = (
    "chg_1d",
    "chg_3d",
    "chg_5d",
    "chg_1m",
    "volatility_20",
    "ma20_dev",
    "corr_60",
    "beta_60",
    "excess_21",
    "ROE",
    "ROA",
    "归母净利润同比",
    "营业总收入同比",
    "毛利率",
    "BPS",
)

CHANNEL_FEATURE_COLUMNS = (
    "channel_score",
    "channel_width_pct",
    "lower_slope_pct",
    "upper_slope_pct",
    "parallel_error",
    "price_in_channel_pos",
)


@dataclass(frozen=True)
class FeatureConfig:
    benchmark_ide: str = "sh000001"
    history_days: int = 400
    corr_window: int = 60
    excess_window: int = 21
    vol_window: int = 20
    ma_window: int = 20


@dataclass(frozen=True)
class TrainConfig:
    horizon: int = 21
    buy_threshold: float = 0.0
    min_history: int = 60
    sample_as_of_count: int = 8
    max_ides: int = 800
    random_state: int = 42


@dataclass(frozen=True)
class AdviceConfig:
    top_k: int = 200
    p_min: float = 0.35
    require_channel: bool = False
    min_channel_score: int = 6
    channel_lookback: int = 80
    channel_pivot_window: int = 5
    drop_anomaly: bool = True
    limit: int = 50
    rank_weight: float = 0.4
    signal_weight: float = 0.3
    trend_weight: float = 0.2
    anomaly_weight: float = 0.1


DEFAULT_FEATURE_CONFIG = FeatureConfig()
DEFAULT_TRAIN_CONFIG = TrainConfig()
DEFAULT_ADVICE_CONFIG = AdviceConfig()

RANKER_PATH = ARTIFACTS_DIR / "ranker.joblib"
SIGNAL_LGB_PATH = ARTIFACTS_DIR / "signal_lgb.joblib"
SIGNAL_XGB_PATH = ARTIFACTS_DIR / "signal_xgb.joblib"
ANOMALY_PATH = ARTIFACTS_DIR / "anomaly.joblib"
META_PATH = ARTIFACTS_DIR / "meta.json"
CHANNEL_SAMPLES_PATH = DATA_DIR / "channel_samples.parquet"
CHANNEL_SAMPLES_META_PATH = DATA_DIR / "channel_samples_meta.json"


@dataclass(frozen=True)
class ChannelSampleConfig:
    """Learning-sample builder for ascending-channel persistence.

    Benchmark market: sh000001. Drawdown: peak-to-trough MDD after as_of.
    """

    market_ide: str = "sh000001"
    horizon: int = 20
    channel_lookback: int = 80
    channel_pivot_window: int = 5
    min_channel_score: int = 6
    channel_mode: str = "entered"
    lower_break_buffer: float = 0.98
    alpha_excess_min: float = 0.05
    alpha_max_dd: float = 0.08
    sector_excess_min: float = 0.0
    min_history: int = 80
    max_ides: int = 300
    # Only scan as_of on every N-th trading day for speed (1 = every day).
    scan_stride: int = 1
    train_end: str = "2022-12-31"
    val_end: str = "2023-12-31"
    # How many calendar trading days to pull from Mongo (multi-year sample window).
    quote_days: int = 2800
    # Extra bars beyond horizon for alignment safety.
    history_buffer: int = 50


DEFAULT_CHANNEL_SAMPLE_CONFIG = ChannelSampleConfig()
