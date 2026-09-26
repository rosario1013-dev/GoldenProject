"""CLI entry point: python -m GP_TDX [quote|cw|dividend|stockinfo|all]"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import DEFAULT_CONFIG
from .cw import upload_all_cw
from .dividend import upload_dividend
from .quote import upload_all_quotes
from .stockinfo import upload_all_stockinfo


def _print_result(label: str, result: dict) -> None:
    print(f"\n{label}:")
    for key, value in result.items():
        print(f"  {key}: {value:,}" if isinstance(value, int) else f"  {key}: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Upload TDX local data to MongoDB (quote, CW, dividend, stockinfo)."
    )
    parser.add_argument(
        "task",
        choices=["quote", "cw", "dividend", "stockinfo", "all"],
        help="which data to upload",
    )
    parser.add_argument("--tdx-path", default=None, help=f"TDX install path (default: {DEFAULT_CONFIG.tdx_path})")
    parser.add_argument("--mongo-uri", default=None, help="MongoDB connection URI")
    parser.add_argument("--no-progress", action="store_true", help="disable tqdm progress bars")
    parser.add_argument(
        "--profiles-only",
        action="store_true",
        help="for stockinfo: skip STOCK list, only fetch F10 profiles",
    )

    filter_group = parser.add_argument_group("filters (optional — omit for full upload)")
    filter_group.add_argument(
        "--quarter",
        metavar="YYYYQN",
        help="CW: one report quarter, e.g. 2026Q1",
    )
    filter_group.add_argument(
        "--report-date",
        metavar="YYYY-MM-DD",
        help="CW: report date / quarter end, e.g. 2026-03-31",
    )
    filter_group.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="quote: one trading date, e.g. 2026-06-17",
    )
    filter_group.add_argument("--date-from", metavar="YYYY-MM-DD", help="quote: start date (inclusive)")
    filter_group.add_argument("--date-to", metavar="YYYY-MM-DD", help="quote: end date (inclusive)")
    filter_group.add_argument("--year", type=int, help="quote or dividend: calendar year, e.g. 2025")
    filter_group.add_argument(
        "--ide",
        action="append",
        metavar="IDE",
        help="quote: limit to stock IDE(s), e.g. sh600519 (repeatable)",
    )

    parser.add_argument("--version", action="version", version=f"GP_TDX {__version__}")
    args = parser.parse_args(argv)

    from .config import Config

    config = Config(
        tdx_path=args.tdx_path or DEFAULT_CONFIG.tdx_path,
        mongo_uri=args.mongo_uri or DEFAULT_CONFIG.mongo_uri,
    )
    show_progress = not args.no_progress

    def on_error(path_or_ide: str, exc: Exception) -> None:
        print(f"error {path_or_ide}: {exc}", file=sys.stderr)

    if args.task in ("quote", "all"):
        _print_result(
            "QUATE",
            upload_all_quotes(
                config=config,
                date=args.date,
                date_from=args.date_from,
                date_to=args.date_to,
                year=args.year,
                ides=args.ide,
                on_error=on_error,
                show_progress=show_progress,
            ),
        )

    if args.task in ("cw", "all"):
        _print_result(
            "CW",
            upload_all_cw(
                config=config,
                quarter=args.quarter,
                report_date=args.report_date,
                on_error=on_error,
                show_progress=show_progress,
            ),
        )

    if args.task in ("dividend", "all"):
        _print_result("Dividend", upload_dividend(config=config, year=args.year))

    if args.task in ("stockinfo", "all"):
        if args.profiles_only:
            from .stockinfo import upload_stockinfo

            _print_result("STOCKINFO", upload_stockinfo(config=config, on_error=on_error, show_progress=show_progress))
        else:
            _print_result(
                "Stockinfo",
                upload_all_stockinfo(config=config, on_error=on_error, show_progress=show_progress),
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
