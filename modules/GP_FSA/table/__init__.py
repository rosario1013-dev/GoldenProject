from .balanceSheet import *
from .cashflowSheet import *
from .implementSheet import *
from .incomeSheet import *
from .dashboardSheet import *

CW_TABLES = {
    "dashboard": ("财务概览", tbl_Dashboard),
    "reformed": ("重构利润表", tbl_Reformed_BS),
    "asset": ("资产负债表", tbl_ASSET),
    "income": ("利润表", tbl_IS),
    "cashflow": ("现金流量表", tbl_CS),
    "cashflow2": ("现金流量表(续)", tbl_CS2),
    "cost": ("成本结构", tbl_COST),
}
