"""kdb database — trading calendar and date indexes."""

from __future__ import annotations

import pymongo

from .connection import KDB, setting_fcns


def setting_fcn(self: KDB) -> None:
    self.DB = self.connection["kdb"]

    self.col_dates = self.DB["dates"]
    self.col_dates.create_index([("DT", pymongo.ASCENDING)], unique=True)

    cur = self.col_dates.find({}, {"_id": 0, "DT": 1, "DTnum": 1}).sort([("DT", 1)])
    self.EDTs: dict[str, int] = {}
    for d in cur:
        self.EDTs[d["DT"]] = d["DTnum"]
    self.DTs = list(self.EDTs.keys())
    self.EDTs["1900-01-01"] = -1


def sync_dates_from_quate(self: KDB, *, start_dt: str | None = None) -> dict[str, object]:
    """Add missing trading days from ``tdx.QUATE`` into ``kdb.dates`` and refresh EDTs."""
    query: dict[str, object] = {}
    if start_dt:
        query["DT"] = {"$gte": start_dt}

    quate_dts = sorted(self.col_TDX_QUATE.distinct("DT", query))
    existing = set(self.DTs)
    new_dts = [dt for dt in quate_dts if dt not in existing]

    if not new_dts:
        return {
            "dates_added": 0,
            "total_dates": len(self.DTs),
            "latest_date": self.DTs[-1] if self.DTs else None,
        }

    max_dtnum = max(
        (self.EDTs[dt] for dt in self.DTs if dt != "1900-01-01"),
        default=-1,
    )
    docs = []
    for dt in new_dts:
        max_dtnum += 1
        docs.append({"DT": dt, "DTnum": max_dtnum})

    self.col_dates.insert_many(docs, ordered=True)
    for doc in docs:
        self.EDTs[doc["DT"]] = doc["DTnum"]
        self.DTs.append(doc["DT"])

    return {
        "dates_added": len(new_dts),
        "total_dates": len(self.DTs),
        "latest_date": self.DTs[-1],
        "new_dates": new_dts,
    }


KDB.sync_dates_from_quate = sync_dates_from_quate


setting_fcns.append(setting_fcn)
