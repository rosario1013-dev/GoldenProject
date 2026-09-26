"""GP_EM — East Money research reports and company filings → MongoDB."""

from .config import (
    COL_FILING,
    COL_RESEARCH,
    DEFAULT_CONFIG,
    FILING_COLUMN_CODES,
    Config,
)
from .query import list_stock_reports
from .sync import upload_reports

__all__ = [
    "Config",
    "DEFAULT_CONFIG",
    "COL_RESEARCH",
    "COL_FILING",
    "FILING_COLUMN_CODES",
    "upload_reports",
    "list_stock_reports",
]

__version__ = "0.1.0"
