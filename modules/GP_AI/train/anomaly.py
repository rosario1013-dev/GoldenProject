"""Train IsolationForest anomaly detector."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.ensemble import IsolationForest

from ..config import ANOMALY_PATH, DEFAULT_TRAIN_CONFIG, TrainConfig
from .common import feature_matrix, save_joblib, update_meta


def train_anomaly(
    frame: pd.DataFrame,
    *,
    out_path: Path = ANOMALY_PATH,
    train_cfg: TrainConfig = DEFAULT_TRAIN_CONFIG,
) -> dict:
    if frame.empty:
        raise ValueError("训练样本为空，无法训练异常检测模型")

    X, _ = feature_matrix(frame)
    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=train_cfg.random_state,
    )
    model.fit(X)
    save_joblib(model, out_path)
    meta = update_meta(
        anomaly={
            "path": str(out_path.name),
            "samples": int(len(frame)),
            "contamination": 0.05,
        }
    )
    return {"path": str(out_path), "samples": len(frame), "meta": meta}
