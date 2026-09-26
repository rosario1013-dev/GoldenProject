"""Train buy-signal classifiers (LightGBM + optional XGBoost)."""

from __future__ import annotations

from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from ..config import DEFAULT_TRAIN_CONFIG, SIGNAL_LGB_PATH, SIGNAL_XGB_PATH, TrainConfig
from .common import feature_matrix, save_joblib, update_meta


def train_signal(
    frame: pd.DataFrame,
    *,
    lgb_path: Path = SIGNAL_LGB_PATH,
    xgb_path: Path = SIGNAL_XGB_PATH,
    train_cfg: TrainConfig = DEFAULT_TRAIN_CONFIG,
    train_xgb: bool = True,
) -> dict:
    if frame.empty or "buy_label" not in frame.columns:
        raise ValueError("训练样本为空，无法训练信号模型")

    X, _ = feature_matrix(frame)
    y = frame["buy_label"].astype(int).to_numpy()
    if len(np.unique(y)) < 2:
        raise ValueError("买入标签只有单一类别，无法训练分类器")

    train_set = lgb.Dataset(X, label=y)
    params = {
        "objective": "binary",
        "metric": "auc",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_data_in_leaf": 20,
        "verbosity": -1,
        "seed": train_cfg.random_state,
    }
    lgb_model = lgb.train(params, train_set, num_boost_round=100)
    save_joblib(lgb_model, lgb_path)

    xgb_ok = False
    if train_xgb:
        try:
            from xgboost import XGBClassifier

            xgb_model = XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                eval_metric="logloss",
                random_state=train_cfg.random_state,
            )
            xgb_model.fit(X, y)
            save_joblib(xgb_model, xgb_path)
            xgb_ok = True
        except Exception:
            xgb_ok = False

    meta = update_meta(
        signal={
            "lgb_path": str(lgb_path.name),
            "xgb_path": str(xgb_path.name) if xgb_ok else None,
            "samples": int(len(frame)),
            "positive_rate": float(y.mean()),
            "horizon": train_cfg.horizon,
            "buy_threshold": train_cfg.buy_threshold,
        }
    )
    return {
        "lgb_path": str(lgb_path),
        "xgb_path": str(xgb_path) if xgb_ok else None,
        "samples": len(frame),
        "meta": meta,
    }
