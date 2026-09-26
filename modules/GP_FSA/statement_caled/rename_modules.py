"""Rename non-ASCII statement_caled modules to ASCII filenames."""

from __future__ import annotations

import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

SKIP = {
    "__init__.py",
    "rename_modules.py",
    "calced_basic.py",
    "calced_cashflow.py",
    "calced_income.py",
    "calced_proforma.py",
    "calced_fcf.py",
    "calced_profitability.py",
    "calced_enterprise.py",
    "calced_capital.py",
}


def target_name(text: str) -> str | None:
    if "formula_\u81ea\u7531\u73b0\u91d1\u6d41" in text:
        return "calced_fcf.py"
    if "Caled('\u51c0\u8d44\u4ea7\u6bd4\u7387')" in text:
        return "calced_capital.py"
    if "Caled('\u8425\u4e1a\u603b\u6536\u5165_1Y')" in text and "Revenue" in text:
        return "calced_enterprise.py"
    if "Caled('\u51c0\u8d44\u4ea7\u6536\u76ca\u7387_1Y')" in text:
        return "calced_profitability.py"
    return None


def main() -> None:
    for name in os.listdir(BASE):
        if not name.endswith(".py") or name in SKIP:
            continue
        path = os.path.join(BASE, name)
        text = open(path, encoding="utf-8").read()
        target = target_name(text)
        if not target:
            print("SKIP", name)
            continue
        dst = os.path.join(BASE, target)
        if os.path.abspath(path) == os.path.abspath(dst):
            continue
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(path, dst)
        print(f"{name} -> {target}")


if __name__ == "__main__":
    main()
