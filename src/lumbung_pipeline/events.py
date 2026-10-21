"""Amplop event Lumbung -> Titeny (KONTEKS §3; Titeny data/20-kontrak-event.md).

Hanya 4 `event_type` bersumber `lumbung` yang boleh dikirim pipeline ini. Menambah event_type
baru butuh bump versi + 30 hari dual-read (KONTEKS §9) -- bukan di sini.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

SOURCE = "lumbung"
SCHEMA_VERSION = 1
EVENT_TYPES = ("panen.dicatat", "harga.diperbarui", "stok.berubah", "stok.snapshot_harian")
EVENT_ID_RE = re.compile(r"^evt_\d{8}_\d{6}$")

# Field wajib payload v1 (Titeny §3.x).
WAJIB = {
    "panen.dicatat": ("panen_id", "komoditas_id", "hasil_kg", "tanggal_panen"),
    "harga.diperbarui": ("pasar_id", "komoditas_id", "tanggal", "harga_per_kg"),
    "stok.berubah": ("gudang_id", "komoditas_id", "perubahan_kg", "stok_akhir_kg", "alasan"),
    "stok.snapshot_harian": ("gudang_id", "tanggal", "baris", "jumlah_baris"),
}
ALASAN_STOK = ("masuk_panen", "masuk_beli", "keluar_penjualan", "susut", "koreksi_opname")


class EventError(ValueError):
    pass


class SequenceStore:
    """Penghitung NNNNNN per tanggal, disimpan di berkas JSON agar tidak ulang antar proses."""

    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path else None
        self._data: dict[str, int] = {}
        if self._path and self._path.exists():
            self._data = json.loads(self._path.read_text(encoding="utf-8"))

    def berikutnya(self, tanggal: str) -> int:
        n = self._data.get(tanggal, 0) + 1
        if n > 999_999:
            raise EventError(f"urutan event habis untuk {tanggal}")
        self._data[tanggal] = n
        if self._path:
            self._path.write_text(json.dumps(self._data, sort_keys=True), encoding="utf-8")
        return n


def validasi_payload(event_type: str, payload: Mapping[str, Any]) -> None:
    kurang = [k for k in WAJIB[event_type] if k not in payload]
    if kurang:
        raise EventError(f"{event_type}: field wajib hilang {kurang}")
    if event_type == "stok.berubah" and payload["alasan"] not in ALASAN_STOK:
        raise EventError(f"stok.berubah: alasan tidak sah {payload['alasan']!r}")
    if event_type == "harga.diperbarui":
        h = payload["harga_per_kg"]
        if not isinstance(h, int) or isinstance(h, bool) or h <= 0:
            raise EventError("harga.diperbarui: harga_per_kg harus integer rupiah > 0")
    if event_type == "stok.snapshot_harian" and payload["jumlah_baris"] != len(payload["baris"]):
        raise EventError("stok.snapshot_harian: jumlah_baris != len(baris)")


def _waktu(v: str, nama: str) -> datetime:
    try:
        t = datetime.fromisoformat(v)
    except ValueError as e:
        raise EventError(f"{nama} bukan ISO-8601: {v!r}") from e
    if t.tzinfo is None:
        raise EventError(f"{nama} tanpa zona waktu")
    return t


def buat_amplop(
    event_type: str,
    payload: Mapping[str, Any],
    occurred_at: str,
    received_at: str,
    batch_id: str,
    urutan: SequenceStore,
) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise EventError(f"event_type di luar registry Lumbung: {event_type!r}")
    validasi_payload(event_type, payload)
    kejadian = _waktu(occurred_at, "occurred_at")
    _waktu(received_at, "received_at")
    if not batch_id.strip():
        raise EventError("batch_id kosong")
    tgl = kejadian.strftime("%Y%m%d")
    event_id = f"evt_{tgl}_{urutan.berikutnya(tgl):06d}"
    assert EVENT_ID_RE.match(event_id)
    return {
        "event_id": event_id,
        "event_type": event_type,
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "occurred_at": occurred_at,
        "received_at": received_at,
        "batch_id": batch_id,
        "payload": dict(payload),
    }
