"""CLI entry point for GP_KDB."""

from __future__ import annotations

import argparse

from . import KDB


def main() -> None:
    parser = argparse.ArgumentParser(description="GP_KDB MongoDB connection test")
    parser.add_argument("--ip", default=None, help="MongoDB host (default: from env or localhost)")
    parser.add_argument("--port", default=None, help="MongoDB port (default: from env or 27017)")
    parser.add_argument("--uri", default=None, help="Full MongoDB URI (overrides ip/port)")
    args = parser.parse_args()

    kdb = KDB().setting(ip=args.ip, port=args.port, uri=args.uri)

    print(f"Connected to MongoDB at {kdb.ip}:{kdb.port}")
    print(f"  kdb dates: {len(kdb.DTs)} trading days")
    print(f"  tdx STOCK: {kdb.col_TDX_STOCK.estimated_document_count()} documents")
    print(f"  tdx QUATE: {kdb.col_TDX_QUATE.estimated_document_count()} documents")

    # kdb.close()


if __name__ == "__main__":
    main()
