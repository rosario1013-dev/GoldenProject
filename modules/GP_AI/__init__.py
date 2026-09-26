"""GP_AI — semi-quantitative advice pipeline."""

from .config import (
    CHANNEL_FEATURE_COLUMNS,
    DEFAULT_ADVICE_CONFIG,
    DEFAULT_CHANNEL_SAMPLE_CONFIG,
    DEFAULT_FEATURE_CONFIG,
    DEFAULT_TRAIN_CONFIG,
    FEATURE_COLUMNS,
    AdviceConfig,
    ChannelSampleConfig,
    FeatureConfig,
    TrainConfig,
)

__all__ = [
    "AdviceConfig",
    "CHANNEL_FEATURE_COLUMNS",
    "ChannelSampleConfig",
    "DEFAULT_ADVICE_CONFIG",
    "DEFAULT_CHANNEL_SAMPLE_CONFIG",
    "DEFAULT_FEATURE_CONFIG",
    "DEFAULT_TRAIN_CONFIG",
    "FEATURE_COLUMNS",
    "FeatureConfig",
    "TrainConfig",
    "confirm_advice",
    "load_models",
    "model_status",
    "run_buy_advice",
]

__version__ = "0.1.0"


def __getattr__(name: str):
    if name in {"load_models", "model_status", "run_buy_advice"}:
        from . import infer

        return getattr(infer, name)
    if name == "confirm_advice":
        from .store import confirm_advice

        return confirm_advice
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
