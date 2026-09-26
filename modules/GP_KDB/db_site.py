"""site database — chart domains, user markers, and stock pool."""

from __future__ import annotations

import pymongo

from .connection import KDB, setting_fcns


def setting_fcn(self: KDB) -> None:
    self.SITE = self.connection["site"]

    self.col_chartdomain = self.SITE["chartdomain"]
    self.col_chartdomain.create_index([("chartname", pymongo.ASCENDING)], unique=True)

    self.col_rullerpoint = self.SITE["rullerpoint"]
    self.col_rullerpoint.create_index([("IDE", pymongo.ASCENDING), ("name", pymongo.ASCENDING)], unique=True)

    self.col_alarmpoint = self.SITE["alarmpoint"]
    self.col_alarmpoint.create_index([("IDE", pymongo.ASCENDING), ("name", pymongo.ASCENDING)], unique=True)

    # 后选股 / 股票池：类别注册表 + 成分股归属
    self.col_POOL = self.SITE["POOL"]
    self.col_POOL.create_index(
        [("username", pymongo.ASCENDING), ("category", pymongo.ASCENDING)],
        unique=True,
    )

    self.col_GOLDENSTOCK = self.SITE["GOLDENSTOCK"]
    self.col_GOLDENSTOCK.create_index(
        [("username", pymongo.ASCENDING), ("IDE", pymongo.ASCENDING)],
        unique=True,
    )
    self.col_GOLDENSTOCK.create_index(
        [("username", pymongo.ASCENDING), ("category", pymongo.ASCENDING)],
    )


setting_fcns.append(setting_fcn)


def chart_domain(self: KDB, chartname: str) -> dict:
    result = KDB().col_chartdomain.find_one({"chartname": chartname}, {"_id": 0})
    return result or {}


def save_chart_domain(self: KDB, chartname: str, data: dict) -> dict:
    KDB().col_chartdomain.update_one({"chartname": chartname}, {"$set": data}, upsert=True)
    return {"success": True}


KDB.ChartDomain = chart_domain
KDB.save_ChartDomain = save_chart_domain
