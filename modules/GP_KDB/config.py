"""Configuration for GP_KDB — MongoDB connection settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """MongoDB connection settings (env vars override defaults)."""

    mongo_uri: str = field(
        default_factory=lambda: os.environ.get(
            "GP_KDB_MONGO_URI",
            os.environ.get(
                "GP_TDX_MONGO_URI",
                "mongodb://127.0.0.1:27017",
            ),
        )
    )
    mongo_ip: str = field(default_factory=lambda: os.environ.get("GP_KDB_MONGO_IP", "localhost"))
    mongo_port: str = field(default_factory=lambda: os.environ.get("GP_KDB_MONGO_PORT", "27017"))


DEFAULT_CONFIG = Config()
