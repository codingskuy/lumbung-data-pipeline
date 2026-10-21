"""Klien REST ke lumbung-backend-service memakai X-Service-Key (docs/auth.md)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .config import Config


class ApiError(RuntimeError):
    def __init__(self, status: int, pesan: str):
        super().__init__(f"HTTP {status}: {pesan}")
        self.status = status


@dataclass(frozen=True)
class Response:
    status: int
    body: Any


# Transport: (method, url, headers, payload-bytes|None) -> Response. Disuntik pada uji.
Transport = Callable[[str, str, Mapping[str, str], bytes | None], Response]


def urllib_transport(
    method: str, url: str, headers: Mapping[str, str], data: bytes | None, timeout: float = 30
) -> Response:
    req = urllib.request.Request(url, data=data, method=method, headers=dict(headers))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (URL dari konfigurasi)
            raw = r.read()
            return Response(r.status, json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            body = json.loads(raw) if raw else None
        except ValueError:
            body = raw.decode("utf-8", "replace")
        return Response(e.code, body)


class LumbungClient:
    def __init__(self, config: Config, transport: Transport = urllib_transport):
        self._config = config
        self._transport = transport

    def _kirim(self, method: str, path: str, payload: Any | None = None) -> Response:
        headers = {
            "X-Service-Key": self._config.service_key,
            "Accept": "application/json",
        }
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload, separators=(",", ":")).encode()
        resp = self._transport(method, self._config.api_url + path, headers, data)
        if resp.status >= 400:
            # Pesan galat tanpa header (kunci tidak boleh ikut tercatat).
            raise ApiError(resp.status, str(resp.body)[:300])
        return resp

    def post_idempoten(self, path: str, payload: dict[str, Any]) -> bool:
        """POST dengan `uuid` klien. True bila duplikat (200 duplikat:true), False bila baru (201)."""
        resp = self._kirim("POST", path, payload)
        return resp.status == 200 and bool((resp.body or {}).get("duplikat", True))

    def get(self, path: str) -> Any:
        return self._kirim("GET", path).body
