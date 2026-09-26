"""MongoDB singleton connection for GP_KDB."""

from __future__ import annotations

import pymongo

from .config import DEFAULT_CONFIG, Config

setting_fcns: list = []


class KDB:
    """Singleton MongoDB accessor. Call setting() once before use."""

    _instance: KDB | None = None

    def __new__(cls) -> KDB:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._configured = False
        return cls._instance

    def setting(
        self,
        ip: str | None = None,
        port: str | None = None,
        *,
        uri: str | None = None,
        config: Config | None = None,
    ) -> KDB:
        """Connect to MongoDB and run database setup hooks."""
        cfg = config or DEFAULT_CONFIG

        if uri:
            client_uri = uri
        elif ip is not None or port is not None:
            host = ip or cfg.mongo_ip
            host_port = port or cfg.mongo_port
            client_uri = f"mongodb://{host}:{host_port}/"
        else:
            client_uri = cfg.mongo_uri

        self.ip = ip or cfg.mongo_ip
        self.port = port or cfg.mongo_port
        self.connection = pymongo.MongoClient(client_uri)

        for fcn in setting_fcns:
            fcn(self)

        self._configured = True
        return self

    @property
    def is_configured(self) -> bool:
        return getattr(self, "_configured", False)

    def close(self) -> None:
        if hasattr(self, "connection"):
            self.connection.close()
            self._configured = False
