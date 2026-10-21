"""ingest-timbangan: berkas timbang gudang -> API Lumbung, idempoten per (lot, waktu timbang).

ASUMSI KONTRAK: openapi.yaml v1.0.0 belum punya endpoint ingest `X-Service-Key`;
`POST /pipeline/timbangan` di bawah adalah asumsi (lihat docs/api-asumsi.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Iterable, Mapping

from ..batch import BatchStats, jalankan_batch
from ..client import LumbungClient
from ..domain import int_positif, komoditas_sah, waktu_iso
from ..idempotency import uuid_dari_kunci_alami

PATH = "/pipeline/timbangan"


def parse_baris(row: Mapping[str, str], sumber: str, diingest_at: str) -> dict:
    lot = str(row.get("lot_kode", "")).strip()
    if not lot:
        raise ValueError("lot_kode kosong")
    ditimbang_at = waktu_iso(row.get("ditimbang_at", ""), "ditimbang_at")
    kebun = int_positif(row.get("berat_kebun_g", ""), "berat_kebun_g")
    gudang = int_positif(row.get("berat_gudang_g", ""), "berat_gudang_g")
    return {
        "uuid": uuid_dari_kunci_alami("timbangan", lot, ditimbang_at),
        "lot_kode": lot,
        "komoditas": komoditas_sah(row.get("komoditas", "")),
        "berat_kebun_g": kebun,
        "berat_gudang_g": gudang,
        "ditimbang_at": ditimbang_at,
        "sumber": sumber,
        "diingest_at": diingest_at,
    }


def sekarang() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ingest(
    client: LumbungClient,
    rows: Iterable[Mapping[str, str]],
    sumber: str,
    ukuran_batch: int = 50,
    now: Callable[[], str] = sekarang,
) -> BatchStats:
    diingest_at = now()

    def kirim(row: Mapping[str, str]) -> bool:
        return client.post_idempoten(PATH, parse_baris(row, sumber, diingest_at))

    return jalankan_batch("ingest-timbangan", rows, kirim, ukuran_batch)
