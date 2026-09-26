"""tdx database — quote, stock, block, and financial collections."""

from __future__ import annotations

import pymongo

from .connection import KDB, setting_fcns


def setting_fcn(self: KDB) -> None:
    self.TDX = self.connection["tdx"]

    self.col_TDX_QUATE = self.TDX["QUATE"]
    self.col_TDX_QUATE.create_index([("IDE", pymongo.ASCENDING), ("DT", pymongo.ASCENDING)], unique=True)
    self.col_TDX_QUATE.create_index([("DT", pymongo.ASCENDING), ("IDE", pymongo.ASCENDING)], unique=True)

    self.col_TDX_STOCK = self.TDX["STOCK"]
    self.col_TDX_STOCK.create_index([("IDE", pymongo.ASCENDING)], unique=True)

    self.col_TDX_BKGN = self.TDX["BKGN"]
    self.col_TDX_BKGN.create_index([("IDS", pymongo.ASCENDING)], unique=True)

    self.col_TDX_BKFG = self.TDX["BKFG"]
    self.col_TDX_BKFG.create_index([("IDS", pymongo.ASCENDING)], unique=True)

    self.col_TDX_BKDQ = self.TDX["BKDQ"]
    self.col_TDX_BKDQ.create_index([("IDE", pymongo.ASCENDING)], unique=True)

    self.col_TDX_BKHY = self.TDX["BKHY"]
    self.col_TDX_BKHY.create_index([("IDS", pymongo.ASCENDING)], unique=True)

    self.col_STOCK_PKVZGB = self.TDX["STOCK_PKVZGB"]
    self.col_STOCK_PKVZGB.create_index([("IDE", pymongo.ASCENDING), ("DT", pymongo.ASCENDING)], unique=True)
    self.col_STOCK_PKVZGB.create_index([("DT", pymongo.ASCENDING), ("IDE", pymongo.ASCENDING)], unique=True)

    self.col_TDX_CW = self.TDX["CW"]
    self.col_TDX_CW.create_index([("IDE", pymongo.ASCENDING), ("REPORTDATE", pymongo.ASCENDING)], unique=True)
    self.col_TDX_CW.create_index([("REPORTDATE", pymongo.ASCENDING), ("IDE", pymongo.ASCENDING)], unique=True)

    self.col_TDX_CWBK = self.TDX["CWBK"]
    self.col_TDX_CWBK.create_index([("IDE", pymongo.ASCENDING), ("REPORTDATE", pymongo.ASCENDING)], unique=True)
    self.col_TDX_CWBK.create_index([("REPORTDATE", pymongo.ASCENDING), ("IDE", pymongo.ASCENDING)], unique=True)

    self.col_TDX_FSA = self.TDX["FSA"]
    self.col_TDX_FSA.create_index([("IDE", pymongo.ASCENDING), ("REPORTDATE", pymongo.ASCENDING)], unique=True)
    self.col_TDX_FSA.create_index([("REPORTDATE", pymongo.ASCENDING), ("IDE", pymongo.ASCENDING)], unique=True)

    self.col_TDX_INDUSTRY_PROFIT_YEARLY = self.TDX["INDUSTRY_PROFIT_YEARLY"]
    self.col_TDX_INDUSTRY_PROFIT_YEARLY.create_index(
        [
            ("industry", pymongo.ASCENDING),
            ("level", pymongo.ASCENDING),
            ("year", pymongo.ASCENDING),
        ],
        unique=True,
    )
    self.col_TDX_INDUSTRY_PROFIT_YEARLY.create_index(
        [("level", pymongo.ASCENDING), ("year", pymongo.ASCENDING)],
    )


setting_fcns.append(setting_fcn)
