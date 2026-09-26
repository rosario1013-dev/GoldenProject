"""Configuration for GP_EM — East Money research / filing reports."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


def _default_pdf_root() -> str:
    env = os.environ.get("GP_EM_PDF_ROOT")
    if env:
        return env
    # modules/GP_EM/../../data/em_reports → repo/data/em_reports
    root = Path(__file__).resolve().parents[2] / "data" / "em_reports"
    return str(root)


def _default_end_time() -> str:
    return os.environ.get("GP_EM_END_TIME") or date.today().isoformat()


@dataclass
class Config:
    """MongoDB + local PDF storage for East Money reports."""

    mongo_uri: str = field(
        default_factory=lambda: os.environ.get(
            "GP_EM_MONGO_URI",
            os.environ.get(
                "GP_TDX_MONGO_URI",
                "mongodb://127.0.0.1:27017/",
            ),
        )
    )
    mongo_db: str = field(
        default_factory=lambda: os.environ.get(
            "GP_EM_MONGO_DB",
            os.environ.get("GP_TDX_MONGO_DB", "tdx"),
        )
    )
    pdf_root: str = field(default_factory=_default_pdf_root)
    begin_time: str = field(
        default_factory=lambda: os.environ.get("GP_EM_BEGIN_TIME", "2020-01-01")
    )
    end_time: str = field(default_factory=_default_end_time)
    research_page_size: int = 100
    filing_page_size: int = 50
    request_timeout: float = 60.0

    @property
    def research_pdf_dir(self) -> str:
        return os.path.join(self.pdf_root, "research")

    @property
    def filing_pdf_dir(self) -> str:
        return os.path.join(self.pdf_root, "filings")


DEFAULT_CONFIG = Config()

COL_RESEARCH = "EM_RESEARCH"
COL_FILING = "EM_FILING"

# 年报 / 半年报 / 一季报 / 三季报 全文
FILING_COLUMN_CODES = frozenset(
    {
        "001001001001001",
        "001001001002001",
        "001001001003001",
        "001001001004001",
    }
)

FILING_COLUMN_LABELS = {
    "001001001001001": "年度报告全文",
    "001001001002001": "半年度报告全文",
    "001001001003001": "一季度报告全文",
    "001001001004001": "三季度报告全文",
}
