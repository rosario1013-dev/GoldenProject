"""GP_KDB — MongoDB management for kdb, tdx, and site databases."""

from .connection import KDB, setting_fcns
from .utils import logfcn, logize, security_type

from . import db_kdb  # noqa: F401 — registers kdb setup
from . import db_tdx  # noqa: F401 — registers tdx setup
from . import db_site  # noqa: F401 — registers site setup
from . import functions_stock  # noqa: F401 — attaches stock methods
from . import functions_info  # noqa: F401 — attaches info methods
from . import functions_bk  # noqa: F401 — attaches block methods
from . import functions_pool  # noqa: F401 — attaches pool methods
from . import functions_screen  # noqa: F401 — attaches screen methods
from . import functions_heatmap  # noqa: F401 — attaches heatmap methods

__all__ = [
    "KDB",
    "setting_fcns",
    "logfcn",
    "logize",
    "security_type",
]
