"""Konstanta domain terkunci v1.0.0 (KONTEKS §4; angka dari tiket LMB-DATA-002)."""

from __future__ import annotations

from datetime import datetime

KOMODITAS_PILOT = ("cabai", "bawang", "kangkung")

# Pagu susut (persen dalam basis poin agar bebas float): cabai 6%, bawang 4%, kangkung 8%.
PAGU_SUSUT_BP = {"cabai": 600, "bawang": 400, "kangkung": 800}
PAGU_SUSUT_JALAN_BP = 200  # 2% per trip


def int_positif(nilai: str, nama: str) -> int:
    """Berat gram integer >= 0 (KONTEKS §6: berat integer gram)."""
    try:
        n = int(str(nilai).strip())
    except ValueError as e:
        raise ValueError(f"{nama} bukan integer: {nilai!r}") from e
    if n < 0:
        raise ValueError(f"{nama} negatif: {n}")
    return n


def komoditas_sah(nilai: str) -> str:
    k = str(nilai).strip().lower()
    if k not in KOMODITAS_PILOT:
        raise ValueError(f"komoditas di luar pilot v1.0.0: {nilai!r}")
    return k


def waktu_iso(nilai: str, nama: str) -> str:
    """Validasi ISO-8601 bersertifikat zona; dikembalikan apa adanya (kunci alami stabil)."""
    v = str(nilai).strip()
    try:
        t = datetime.fromisoformat(v)
    except ValueError as e:
        raise ValueError(f"{nama} bukan ISO-8601: {nilai!r}") from e
    if t.tzinfo is None:
        raise ValueError(f"{nama} tanpa zona waktu: {nilai!r}")
    return v
