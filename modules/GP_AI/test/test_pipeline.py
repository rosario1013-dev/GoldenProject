from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from GP_AI.config import FEATURE_COLUMNS
from GP_AI.features.builders import build_feature_row, matrix_from_frame
from GP_AI.scoring import composite_score, normalize_rank_scores, trend_score
from GP_AI.train import train_anomaly, train_ranker, train_signal
from GP_AI.infer.models import load_models
from GP_AI.infer.pipeline import run_buy_advice


def _synth_closes(n: int = 120, drift: float = 0.002, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    rets = drift + rng.normal(0, 0.01, size=n)
    prices = 100 * np.cumprod(1 + rets)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.Series(prices, index=idx)


class FeatureTests(unittest.TestCase):
    def test_build_feature_row_keys(self):
        stock = _synth_closes(seed=1)
        index = _synth_closes(seed=2, drift=0.0005)
        row = build_feature_row(stock, index, {"ROE": 12.3, "ROA": 5.0})
        for key in FEATURE_COLUMNS:
            self.assertIn(key, row)
        self.assertIsNotNone(row["chg_1d"])
        self.assertEqual(row["ROE"], 12.3)

    def test_matrix_fills_nan(self):
        frame = pd.DataFrame(
            [{"chg_1d": 1.0, "ROE": None, **{k: 0.0 for k in FEATURE_COLUMNS if k not in {"chg_1d", "ROE"}}}]
        )
        matrix = matrix_from_frame(frame)
        self.assertEqual(matrix.shape, (1, len(FEATURE_COLUMNS)))
        self.assertTrue(np.isfinite(matrix).all())


class ScoringTests(unittest.TestCase):
    def test_composite_and_trend(self):
        self.assertEqual(trend_score(6, 6), 1.0)
        self.assertEqual(normalize_rank_scores([1, 2, 3]), [0.0, 0.5, 1.0])
        score = composite_score(rank_score=1, signal_prob=1, trend=1, anomaly_risk=0)
        self.assertAlmostEqual(score, 1.0)


class PipelineTrainTests(unittest.TestCase):
    def test_train_and_infer_with_mocks(self):
        rows = []
        for i in range(40):
            row = {col: float((i % 7) - 3) for col in FEATURE_COLUMNS}
            row.update(
                {
                    "ide": f"sz00000{i % 10}",
                    "as_of": f"2025-0{(i % 4) + 1}-15",
                    "fwd_excess": (i - 20) / 100.0,
                    "buy_label": int(i > 20),
                }
            )
            rows.append(row)
        frame = pd.DataFrame(rows)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("GP_AI.train.ranker.update_meta", return_value={}), patch(
                "GP_AI.train.signal.update_meta", return_value={}
            ), patch("GP_AI.train.anomaly.update_meta", return_value={}):
                train_ranker(frame, out_path=root / "ranker.joblib")
                train_signal(frame, lgb_path=root / "signal_lgb.joblib", xgb_path=root / "signal_xgb.joblib")
                train_anomaly(frame, out_path=root / "anomaly.joblib")
            import json

            meta = {
                "ranker": {"path": "ranker.joblib"},
                "signal": {"lgb_path": "signal_lgb.joblib", "xgb_path": "signal_xgb.joblib"},
                "anomaly": {"path": "anomaly.joblib"},
                "feature_columns": list(FEATURE_COLUMNS),
            }
            (root / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
            bundle = load_models(root)
            self.assertTrue(bundle.ready)

            feat_frame = frame.drop_duplicates("ide").set_index("ide")[list(FEATURE_COLUMNS)].head(8)

            class DummyKdb:
                def StockInfo(self, ide):
                    return {"IDS": ide}

            with patch("GP_AI.infer.pipeline.features_frame_for_ides", return_value=feat_frame), patch(
                "GP_AI.infer.pipeline.resolve_universe",
                return_value=list(feat_frame.index),
            ), patch(
                "GP_AI.infer.pipeline._channel_for_ide",
                return_value={"is_match": True, "score": 6, "score_text": "6/7"},
            ):
                advice = run_buy_advice(
                    DummyKdb(),
                    require_channel=True,
                    drop_anomaly=False,
                    p_min=0.0,
                    limit=5,
                    models=bundle,
                )
            self.assertGreaterEqual(len(advice), 1)
            self.assertIn("score", advice[0])
            self.assertIn("signal_prob", advice[0])


if __name__ == "__main__":
    unittest.main()
