"""CLI entry point: python -m GP_TECH <task>."""

from __future__ import annotations

import argparse
import json

from GP_KDB import KDB

from .config import DEFAULT_INDEPENDENT_STRONG_CONFIG, DEFAULT_INDUSTRY_RELATIVE_CONFIG
from .scan import (
    scan_channel_stocks,
    scan_independent_strong_stocks,
    scan_industry_relative,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GoldenProject technical analysis")
    parser.add_argument(
        "task",
        choices=["channel", "independent-strong", "industry-relative"],
    )
    parser.add_argument("--mode", choices=["in", "entered"], default=None)
    parser.add_argument("--ide", action="append", help="limit to IDE (repeatable)")
    parser.add_argument("--industry", action="append", help="limit to industry (repeatable)")
    parser.add_argument("--parent", action="append", help="HY1 parent for industry-relative")
    parser.add_argument("--level", choices=["1", "2", "3"], default="2")
    parser.add_argument("--lookback", type=int, default=80)
    parser.add_argument("--pivot-window", type=int, default=5)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument(
        "--benchmark",
        default=DEFAULT_INDEPENDENT_STRONG_CONFIG.benchmark_ide,
        help="benchmark IDE (default sh000001)",
    )
    parser.add_argument("--corr-window", type=int, default=60)
    parser.add_argument("--excess-window", type=int, default=21)
    parser.add_argument("--max-corr", type=float, default=None)
    parser.add_argument("--min-corr", type=float, default=None)
    parser.add_argument("--min-excess", type=float, default=None)
    args = parser.parse_args(argv)

    kdb = KDB().setting()
    if args.task == "channel":
        rows = scan_channel_stocks(
            kdb,
            ides=args.ide,
            industries=args.industry,
            mode=args.mode or "entered",
            lookback=args.lookback,
            pivot_window=args.pivot_window,
            limit=args.limit,
        )
    elif args.task == "independent-strong":
        rows = scan_independent_strong_stocks(
            kdb,
            ides=args.ide,
            industries=args.industry,
            benchmark_ide=args.benchmark,
            mode=args.mode or "in",
            lookback=args.lookback,
            pivot_window=args.pivot_window,
            corr_window=args.corr_window,
            excess_window=args.excess_window,
            max_corr=args.max_corr if args.max_corr is not None else 0.4,
            min_excess=args.min_excess if args.min_excess is not None else 0.0,
            limit=args.limit,
        )
    else:
        rows = scan_industry_relative(
            kdb,
            level=args.level or DEFAULT_INDUSTRY_RELATIVE_CONFIG.level,
            parents=args.parent or args.industry,
            ides=args.ide,
            benchmark_ide=args.benchmark,
            corr_window=args.corr_window,
            excess_window=args.excess_window,
            max_corr=args.max_corr,
            min_corr=args.min_corr,
            min_excess=args.min_excess,
            limit=args.limit,
        )
    print(json.dumps({"count": len(rows), "stocks": rows}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
