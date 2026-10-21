"""ingest-pasar-induk: 3 harga referensi per komoditas -> API Lumbung (papan Jumat 15.00).

Referensi (keuangan/20-papan-harga-mingguan.md): Pasar Induk, pasar kota, eceran daring.
Harga rupiah integer per kg. Kunci alami: (tanggal_survei, komoditas, referensi).
ASUMSI KONTRAK: `POST /pipeline/harga-referensi` belum ada di openapi.yaml (docs/api-asumsi.md).
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import Callable, Iterable, Mapping

from ..batch import BatchStats, jalankan_batch
from ..client import LumbungClient
from ..domain import KOMODITAS_PILOT, int_positif, komoditas_sah
from ..idempotency import uuid_dari_kunci_alami
from .timbangan import sekarang

PATH = "/pipeline/harga-referensi"
REFERENSI = ("pasar_induk", "pasar_kota", "eceran_daring")
RETENSI_BULAN = 6  # lembar kerja disimpan minimal 6 bulan (audit sengketa harga)


def tambah_bulan(d: date, n: int) -> date:
    idx = d.month - 1 + n
    y, m = d.year + idx // 12, idx % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def simpan_sampai(tanggal_survei: date) -> date:
    return tambah_bulan(tanggal_survei, RETENSI_BULAN)


def boleh_dihapus(tanggal_survei: date, hari_ini: date) -> bool:
    """Lembar kerja baru boleh dibuang setelah melewati 6 bulan."""
    return hari_ini > simpan_sampai(tanggal_survei)


def parse_baris(row: Mapping[str, str], sumber: str, diingest_at: str) -> dict:
    try:
        tgl = date.fromisoformat(str(row.get("tanggal_survei", "")).strip())
    except ValueError as e:
        raise ValueError(f"tanggal_survei tidak sah: {row.get('tanggal_survei')!r}") from e
    ref = str(row.get("referensi", "")).strip().lower()
    if ref not in REFERENSI:
        raise ValueError(f"referensi tidak dikenal: {ref!r}")
    harga = int_positif(row.get("harga_per_kg", ""), "harga_per_kg")
    if harga == 0:
        raise ValueError("harga_per_kg nol")
    kom = komoditas_sah(row.get("komoditas", ""))
    return {
        "uuid": uuid_dari_kunci_alami("harga-referensi", tgl.isoformat(), kom, ref),
        "tanggal_survei": tgl.isoformat(),
        "komoditas": kom,
        "referensi": ref,
        "harga_per_kg": harga,
        "simpan_sampai": simpan_sampai(tgl).isoformat(),
        "sumber": sumber,
        "diingest_at": diingest_at,
    }


def filter_rentang(rows: Iterable[Mapping[str, str]], dari: date, sampai: date) -> list[Mapping[str, str]]:
    """Backfill hanya per rentang tanggal EKSPLISIT; baris di luar rentang diabaikan."""
    if dari > sampai:
        raise ValueError("dari > sampai")
    hasil = []
    for r in rows:
        try:
            t = date.fromisoformat(str(r.get("tanggal_survei", "")).strip())
        except ValueError:
            hasil.append(r)  # biarkan ingest menghitungnya sebagai gagal
            continue
        if dari <= t <= sampai:
            hasil.append(r)
    return hasil


def kekurangan(terparse: Iterable[Mapping], tanggal: date) -> list[tuple[str, str]]:
    """Pasangan (komoditas, referensi) yang belum ada untuk `tanggal` (harus kosong sebelum Jumat 15.00)."""
    ada = {(p["komoditas"], p["referensi"]) for p in terparse if p["tanggal_survei"] == tanggal.isoformat()}
    return [(k, r) for k in KOMODITAS_PILOT for r in REFERENSI if (k, r) not in ada]


def lembar_kerja(terparse: Iterable[Mapping], tanggal: date) -> dict:
    """Lembar kerja audit: 3 harga + tanggal survei per komoditas."""
    out: dict = {"tanggal_survei": tanggal.isoformat(), "simpan_sampai": simpan_sampai(tanggal).isoformat(), "komoditas": {}}
    for p in terparse:
        if p["tanggal_survei"] == tanggal.isoformat():
            out["komoditas"].setdefault(p["komoditas"], {})[p["referensi"]] = p["harga_per_kg"]
    return out


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

    return jalankan_batch("ingest-pasar-induk", rows, kirim, ukuran_batch)
