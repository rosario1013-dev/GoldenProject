"""CLI: python -m GP_AI <task>."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from GP_KDB import KDB

from .config import (
    CHANNEL_SAMPLES_META_PATH,
    CHANNEL_SAMPLES_PATH,
    DEFAULT_CHANNEL_SAMPLE_CONFIG,
    DEFAULT_TRAIN_CONFIG,
)


def _kdb() -> KDB:
    return KDB().setting()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GoldenProject AI advice pipeline")
    parser.add_argument(
        "task",
        choices=[
            "train-ranker",
            "train-signal",
            "train-anomaly",
            "train-all",
            "advice",
            "models",
            "build-channel-samples",
        ],
    )
    parser.add_argument("--horizon", type=int, default=None)
    parser.add_argument("--max-ides", type=int, default=None)
    parser.add_argument("--as-of-count", type=int, default=DEFAULT_TRAIN_CONFIG.sample_as_of_count)
    parser.add_argument("--scan-stride", type=int, default=None, help="channel sample day stride")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--p-min", type=float, default=0.35)
    parser.add_argument("--industry", action="append", help="limit advice/train universe")
    parser.add_argument("--ide", action="append")
    parser.add_argument("--require-channel", action="store_true", help="hard-filter ascending channel")
    parser.add_argument("--no-xgb", action="store_true")
    parser.add_argument("--out", type=str, default=None, help="channel samples output path")
    parser.add_argument("--meta-out", type=str, default=None, help="channel samples meta json path")
    args = parser.parse_args(argv)

    if args.task == "models":
        from .infer.models import model_status

        print(json.dumps(model_status(), ensure_ascii=False, indent=2))
        return 0

    kdb = _kdb()

    if args.task == "build-channel-samples":
        from .features.channel_dataset import build_channel_training_frame, save_channel_samples

        cfg = DEFAULT_CHANNEL_SAMPLE_CONFIG
        cfg = replace(
            cfg,
            horizon=args.horizon if args.horizon is not None else cfg.horizon,
            max_ides=args.max_ides if args.max_ides is not None else cfg.max_ides,
            scan_stride=args.scan_stride if args.scan_stride is not None else cfg.scan_stride,
        )
        ides = None
        if args.industry:
            ides = kdb.ides_for_industries(args.industry) or []
            ides = ides[: cfg.max_ides]
        if args.ide:
            ides = list(dict.fromkeys((ides or []) + args.ide))[: cfg.max_ides]

        frame, stats = build_channel_training_frame(kdb, cfg=cfg, ides=ides)
        out_path = Path(args.out) if args.out else CHANNEL_SAMPLES_PATH
        meta_path = Path(args.meta_out) if args.meta_out else CHANNEL_SAMPLES_META_PATH
        try:
            meta = save_channel_samples(frame, stats, cfg, out_path=out_path, meta_path=meta_path)
        except ImportError:
            out_path = out_path.with_suffix(".csv")
            meta = save_channel_samples(frame, stats, cfg, out_path=out_path, meta_path=meta_path)
        print(json.dumps(meta, ensure_ascii=False, indent=2, default=str))
        return 0

    from .features.dataset import build_training_frame
    from .infer.pipeline import run_buy_advice
    from .train import train_anomaly, train_ranker, train_signal

    train_cfg = replace(
        DEFAULT_TRAIN_CONFIG,
        horizon=args.horizon if args.horizon is not None else DEFAULT_TRAIN_CONFIG.horizon,
        max_ides=args.max_ides if args.max_ides is not None else DEFAULT_TRAIN_CONFIG.max_ides,
        sample_as_of_count=args.as_of_count,
    )

    if args.task.startswith("train"):
        ides = None
        if args.industry:
            ides = kdb.ides_for_industries(args.industry) or []
            ides = ides[: train_cfg.max_ides]
        if args.ide:
            ides = list(dict.fromkeys((ides or []) + args.ide))
        frame = build_training_frame(kdb, train_cfg=train_cfg, ides=ides)
        print(json.dumps({"samples": len(frame)}, ensure_ascii=False))
        if args.task in {"train-ranker", "train-all"}:
            print(json.dumps(train_ranker(frame, train_cfg=train_cfg), ensure_ascii=False, indent=2, default=str))
        if args.task in {"train-signal", "train-all"}:
            print(
                json.dumps(
                    train_signal(frame, train_cfg=train_cfg, train_xgb=not args.no_xgb),
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
        if args.task in {"train-anomaly", "train-all"}:
            print(json.dumps(train_anomaly(frame, train_cfg=train_cfg), ensure_ascii=False, indent=2, default=str))
        return 0

    rows = run_buy_advice(
        kdb,
        ides=args.ide,
        industries=args.industry,
        limit=args.limit,
        p_min=args.p_min,
        require_channel=args.require_channel,
    )
    print(json.dumps({"count": len(rows), "stocks": rows}, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
