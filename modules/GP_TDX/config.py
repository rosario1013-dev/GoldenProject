"""Configuration for GP_TDX — paths and MongoDB settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """TDX local install paths and MongoDB connection."""

    tdx_path: str = field(default_factory=lambda: os.environ.get("GP_TDX_PATH", "C:/zd_zsone"))
    mongo_uri: str = field(
        default_factory=lambda: os.environ.get(
            "GP_TDX_MONGO_URI",
            "mongodb://127.0.0.1:27017",
        )
    )
    mongo_db: str = field(default_factory=lambda: os.environ.get("GP_TDX_MONGO_DB", "tdx"))
    api_ip: str = field(default_factory=lambda: os.environ.get("GP_TDX_API_IP", "120.53.204.206"))
    api_port: int = field(default_factory=lambda: int(os.environ.get("GP_TDX_API_PORT", "7709")))

    @property
    def vipdoc_path(self) -> str:
        return os.path.join(self.tdx_path, "vipdoc")

    @property
    def cw_path(self) -> str:
        return os.path.join(self.vipdoc_path, "cw")

    @property
    def gbbq_path(self) -> str:
        return os.path.join(self.tdx_path, "T0002", "hq_cache", "gbbq")

    @property
    def hq_cache_path(self) -> str:
        return os.path.join(self.tdx_path, "T0002", "hq_cache")


DEFAULT_CONFIG = Config()
