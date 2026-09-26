"""CLI: python -m GP_EM [--kind all|research|filings] [--download-pdf] [--max-pages N]"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .config import DEFAULT_CONFIG, Config
from .sync import upload_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync East Money research / filing metadata (optional PDF download)."
    )
    parser.add_argument(
        "--kind",
        default="all",
        choices=["all", "research", "filings"],
        help="which reports to sync",
    )
    parser.add_argument(
        "--download-pdf",
        action="store_true",
        help="also download PDFs to local pdf_root",
    )
    parser.add_argument("--begin-time", default=None, help="research beginTime YYYY-MM-DD")
    parser.add_argument("--end-time", default=None, help="research endTime YYYY-MM-DD")
    parser.add_argument("--max-pages", type=int, default=None, help="max API pages per source")
    parser.add_argument("--pdf-limit", type=int, default=None, help="max PDFs to download")
    parser.add_argument("--stock-list", default=None, help="filings: Eastmoney stock_list filter")
    parser.add_argument("--pdf-root", default=None, help="local PDF root directory")
    parser.add_argument("--mongo-uri", default=None, help="MongoDB URI")
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument("--version", action="version", version=f"GP_EM {__version__}")
    args = parser.parse_args(argv)

    config = Config(
        mongo_uri=args.mongo_uri or DEFAULT_CONFIG.mongo_uri,
        mongo_db=DEFAULT_CONFIG.mongo_db,
        pdf_root=args.pdf_root or DEFAULT_CONFIG.pdf_root,
        begin_time=args.begin_time or DEFAULT_CONFIG.begin_time,
        end_time=args.end_time or DEFAULT_CONFIG.end_time,
    )

    def on_error(target: str, exc: Exception) -> None:
        print(f"error {target}: {exc}", file=sys.stderr)

    result = upload_reports(
        config=config,
        kind=args.kind,
        download_pdf=args.download_pdf,
        begin_time=args.begin_time,
        end_time=args.end_time,
        max_pages=args.max_pages,
        stock_list=args.stock_list,
        pdf_limit=args.pdf_limit,
        on_error=on_error,
        show_progress=not args.no_progress,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
