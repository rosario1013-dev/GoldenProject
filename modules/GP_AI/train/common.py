"""Shared training helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ..config import ARTIFACTS_DIR, FEATURE_COLUMNS, META_PATH
from ..features.builders import matrix_from_frame


def ensure_artifacts_dir(path: Path | None = None) -> Path:
    target = path or ARTIFACTS_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target


def feature_matrix(frame: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    feats = frame.reindex(columns=list(FEATURE_COLUMNS))
    return matrix_from_frame(feats), feats


def save_joblib(obj, path: Path) -> Path:
    ensure_artifacts_dir(path.parent)
    joblib.dump(obj, path)
    return path


def update_meta(**fields) -> dict:
    ensure_artifacts_dir()
    meta: dict = {}
    if META_PATH.exists():
        try:
            meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    meta.update(fields)
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    meta["feature_columns"] = list(FEATURE_COLUMNS)
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def group_ranks(values: np.ndarray) -> np.ndarray:
    """Higher value → better (lower) dense rank index within a group."""
    order = np.argsort(-values)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(len(values))
    return ranks.astype(int)


def group_relevance(values: np.ndarray, n_bins: int = 5) -> np.ndarray:
    """Map values to lambdarank relevance labels (higher = better).

    LightGBM default ``label_gain`` only covers labels 0..30, so large
    per-date universes must be binned instead of using raw 0..N ranks.
    """
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n == 0:
        return values.astype(int)
    bins = max(2, min(int(n_bins), n))
    # Rank ascending then cut into bins so top excess gets highest label.
    order = np.argsort(values)
    positions = np.empty(n, dtype=float)
    positions[order] = np.arange(n, dtype=float)
    # Map position to [0, bins-1]
    labels = np.floor(positions / n * bins).astype(int)
    labels = np.clip(labels, 0, bins - 1)
    return labels
