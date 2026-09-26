"""Train LightGBM LambdaRank for stock ranking."""

from __future__ import annotations

from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from ..config import DEFAULT_TRAIN_CONFIG, RANKER_PATH, TrainConfig
from .common import feature_matrix, group_relevance, save_joblib, update_meta


def train_ranker(
    frame: pd.DataFrame,
    *,
    out_path: Path = RANKER_PATH,
    train_cfg: TrainConfig = DEFAULT_TRAIN_CONFIG,
    n_bins: int = 5,
) -> dict:
    if frame.empty or "fwd_excess" not in frame.columns:
        raise ValueError("训练样本为空，无法训练 Ranker")

    X, _ = feature_matrix(frame)
    # Group by as_of date for lambdarank; bin relevance to avoid LightGBM
    # "Label N is not less than the number of label mappings (31)".
    if "as_of" in frame.columns:
        groups = frame.groupby("as_of", sort=True).size().tolist()
        labels = [
            group_relevance(group["fwd_excess"].astype(float).to_numpy(), n_bins=n_bins)
            for _, group in frame.groupby("as_of", sort=True)
        ]
        y = np.concatenate(labels)
    else:
        groups = [len(frame)]
        y = group_relevance(frame["fwd_excess"].astype(float).to_numpy(), n_bins=n_bins)

    max_label = int(y.max()) if len(y) else 0
    train_set = lgb.Dataset(X, label=y, group=groups)
    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_data_in_leaf": 20,
        "verbosity": -1,
        "seed": train_cfg.random_state,
        # Explicit gains for labels 0..max_label (default only covers 0..30).
        "label_gain": list(range(max_label + 1)),
    }
    model = lgb.train(params, train_set, num_boost_round=80)
    save_joblib(model, out_path)
    meta = update_meta(
        ranker={
            "path": str(out_path.name),
            "samples": int(len(frame)),
            "groups": int(len(groups)),
            "horizon": train_cfg.horizon,
            "relevance_bins": int(n_bins),
            "max_label": max_label,
        }
    )
    return {"path": str(out_path), "samples": len(frame), "meta": meta}
