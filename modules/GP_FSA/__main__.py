"""CLI entry point for GP_FSA."""

from __future__ import annotations

import argparse

from GP_KDB import KDB

from . import Stock, accounts


def main() -> None:
    parser = argparse.ArgumentParser(description="GP_FSA — financial ratio calculator")
    parser.add_argument("ide", nargs="?", default="sh600519", help="Stock IDE, e.g. sh600519")
    parser.add_argument("--ratio", default="净资产收益率", help="Account/ratio name to display")
    args = parser.parse_args()

    KDB().setting()
    st = Stock(args.ide).load_FS()

    if args.ratio not in accounts:
        print(f"Unknown account: {args.ratio}")
        print("Sample accounts:", list(accounts.keys())[:10])
        return

    series = accounts[args.ratio].value(st)
    print(f"{args.ide} — {args.ratio}")
    print(series.dropna().tail(8))


if __name__ == "__main__":
    main()
