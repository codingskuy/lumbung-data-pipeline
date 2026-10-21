"""ingest-trip: log trip kebun-gudang -> API Lumbung, idempoten per kode trip.

ASUMSI KONTRAK: `POST /pipeline/trip` belum ada di openapi.yaml v1.0.0 (lihat docs/api-asumsi.md).
"""

from __future__ import annotations

from typing import Callable, Iterable, Mapping

from ..batch import BatchStats, jalankan_batch
from ..client import LumbungClient
from ..domain import int_positif, komoditas_sah, waktu_iso
from ..idempotency import uuid_dari_kunci_alami
from .timbangan import sekarang

PATH = "/pipeline/trip"


def parse_baris(row: Mapping[str, str], sumber: str, diingest_at: str) -> dict:
    kode = str(row.get("trip_kode", "")).strip()  # contoh TRIP-UT-041 (KONTEKS §6)
    if not kode.startswith("TRIP-"):
        raise ValueError(f"trip_kode tidak sah: {kode!r}")
    return {
        "uuid": uuid_dari_kunci_alami("trip", kode),
        "trip_kode": kode,
        "komoditas": komoditas_sah(row.get("komoditas", "")),
        "berat_muat_g": int_positif(row.get("berat_muat_g", ""), "berat_muat_g"),
        "berat_terima_g": int_positif(row.get("berat_terima_g", ""), "berat_terima_g"),
        "berangkat_at": waktu_iso(row.get("berangkat_at", ""), "berangkat_at"),
        "tiba_at": waktu_iso(row.get("tiba_at", ""), "tiba_at"),
        "sumber": sumber,
        "diingest_at": diingest_at,
    }


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

    return jalankan_batch("ingest-trip", rows, kirim, ukuran_batch)
