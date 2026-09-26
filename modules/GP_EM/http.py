"""HTTP helpers for East Money APIs."""

from __future__ import annotations

import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://data.eastmoney.com/",
}


def fetch(url: str, *, timeout: float = 60.0) -> requests.Response:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response


def build_url(base: str, params: dict) -> str:
    return requests.Request("GET", url=base, params=params).prepare().url or base
