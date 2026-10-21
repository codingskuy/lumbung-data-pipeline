"""Konfigurasi dari variabel lingkungan; rahasia tidak pernah dicatat."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    api_url: str
    service_key: str = field(repr=False)  # repr=False agar tidak bocor ke log

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Config":
        env = os.environ if env is None else env
        url = env.get("LUMBUNG_API_URL", "").strip()
        key = env.get("LUMBUNG_SERVICE_KEY", "").strip()
        if not url:
            raise ConfigError("LUMBUNG_API_URL belum diset")
        if not key:
            raise ConfigError("LUMBUNG_SERVICE_KEY belum diset")
        return cls(api_url=url.rstrip("/"), service_key=key)
