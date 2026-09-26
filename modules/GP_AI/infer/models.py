"""Load trained model artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib

from ..config import (
    ANOMALY_PATH,
    ARTIFACTS_DIR,
    META_PATH,
    RANKER_PATH,
    SIGNAL_LGB_PATH,
    SIGNAL_XGB_PATH,
)


@dataclass
class ModelBundle:
    ranker: object | None = None
    signal_lgb: object | None = None
    signal_xgb: object | None = None
    anomaly: object | None = None
    meta: dict | None = None
    artifacts_dir: Path = ARTIFACTS_DIR

    @property
    def ready(self) -> bool:
        return self.ranker is not None and self.signal_lgb is not None and self.anomaly is not None

    def missing(self) -> list[str]:
        missing = []
        if self.ranker is None:
            missing.append("ranker.joblib")
        if self.signal_lgb is None:
            missing.append("signal_lgb.joblib")
        if self.anomaly is None:
            missing.append("anomaly.joblib")
        return missing


def _safe_load(path: Path):
    if not path.exists():
        return None
    return joblib.load(path)


def load_models(artifacts_dir: Path | None = None) -> ModelBundle:
    root = artifacts_dir or ARTIFACTS_DIR
    meta = {}
    meta_path = root / META_PATH.name if artifacts_dir else META_PATH
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    return ModelBundle(
        ranker=_safe_load(root / RANKER_PATH.name),
        signal_lgb=_safe_load(root / SIGNAL_LGB_PATH.name),
        signal_xgb=_safe_load(root / SIGNAL_XGB_PATH.name),
        anomaly=_safe_load(root / ANOMALY_PATH.name),
        meta=meta,
        artifacts_dir=root,
    )


def model_status(artifacts_dir: Path | None = None) -> dict:
    bundle = load_models(artifacts_dir)
    return {
        "ready": bundle.ready,
        "missing": bundle.missing(),
        "has_xgb": bundle.signal_xgb is not None,
        "meta": bundle.meta or {},
        "artifacts_dir": str(bundle.artifacts_dir),
    }
