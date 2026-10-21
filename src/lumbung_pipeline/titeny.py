"""Pengirim event ke Titeny: POST /api/v1/event/masuk, retry 3x (5/30/300 dtk) lalu DLQ.

ASUMSI: Titeny belum mendokumentasikan autentikasi pintu masuk; hanya `X-Idempotency-Key`
dikirim (docs/api-asumsi.md). Timeout 10 dtk, 422 tidak di-retry (event_id baru wajib).
"""

from __future__ import annotations

import functools
import json
import logging
import time
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .client import Response, Transport, urllib_transport

log = logging.getLogger("lumbung_pipeline")

PATH = "/api/v1/event/masuk"
JEDA_RETRY = (5, 30, 300)  # detik
TIMEOUT = 10


class Transien(RuntimeError):
    """Layak di-retry: jaringan, timeout, 408/429/5xx."""


class Ditolak(RuntimeError):
    """4xx lain (termasuk 422): tidak di-retry, langsung DLQ."""


@dataclass(frozen=True)
class Hasil:
    status: str  # "diterima" | "duplikat" | "dlq"
    percobaan: int


class DeadLetterQueue:
    """DLQ berkas JSONL: amplop + alasan + jumlah percobaan (tanpa rahasia)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def tulis(self, amplop: Mapping[str, Any], alasan: str, percobaan: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        baris = {"alasan": alasan, "percobaan": percobaan, "amplop": amplop}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(baris, sort_keys=True, ensure_ascii=False) + "\n")

    def isi(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines() if x]


class TitenyClient:
    def __init__(self, base_url: str, transport: Transport | None = None):
        self._base = base_url.rstrip("/")
        self._transport = transport or functools.partial(urllib_transport, timeout=TIMEOUT)

    def kirim_sekali(self, amplop: Mapping[str, Any]) -> str:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Idempotency-Key": amplop["event_id"],
        }
        data = json.dumps(amplop, separators=(",", ":")).encode()
        try:
            r: Response = self._transport("POST", self._base + PATH, headers, data)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise Transien(f"jaringan: {type(e).__name__}") from e
        if r.status in (200, 201, 202):
            sel = (r.body or {}).get("status") if isinstance(r.body, dict) else None
            return "duplikat" if sel == "duplikat_diabaikan" else "diterima"
        ringkas = str(r.body)[:200]
        if r.status in (408, 429) or r.status >= 500:
            raise Transien(f"HTTP {r.status}: {ringkas}")
        raise Ditolak(f"HTTP {r.status}: {ringkas}")


def kirim_dengan_retry(
    client: TitenyClient,
    amplop: Mapping[str, Any],
    dlq: DeadLetterQueue,
    jeda: tuple[int, ...] = JEDA_RETRY,
    sleep: Callable[[float], None] = time.sleep,
) -> Hasil:
    """1 percobaan awal + len(jeda) retry; gagal akhir atau ditolak -> DLQ."""
    percobaan = 0
    alasan = ""
    for i in range(len(jeda) + 1):
        percobaan += 1
        try:
            status = client.kirim_sekali(amplop)
            log.info("event %s %s (percobaan=%d)", amplop["event_id"], status, percobaan)
            return Hasil(status, percobaan)
        except Ditolak as e:
            alasan = f"ditolak: {e}"
            break
        except Transien as e:
            alasan = f"gagal setelah retry: {e}"
            if i < len(jeda):
                log.warning("event %s transien, retry dalam %ds: %s", amplop["event_id"], jeda[i], e)
                sleep(jeda[i])
    dlq.tulis(amplop, alasan, percobaan)
    log.error("event %s masuk DLQ: %s", amplop["event_id"], alasan)
    return Hasil("dlq", percobaan)
