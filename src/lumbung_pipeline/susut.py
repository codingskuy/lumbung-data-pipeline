"""Rekap susut harian per komoditas + susut jalan per trip terhadap pagu.

Pagu (tiket LMB-DATA-002): cabai 6%, bawang 4%, kangkung 8%, jalan 2%/trip.
Aritmetika integer (basis poin) agar bebas galat float.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

from .domain import PAGU_SUSUT_BP, PAGU_SUSUT_JALAN_BP


@dataclass(frozen=True)
class RekapSusut:
    tanggal: str  # YYYY-MM-DD (tanggal lokal dari `ditimbang_at`)
    komoditas: str
    berat_kebun_g: int
    berat_gudang_g: int
    susut_g: int
    susut_bp: int  # basis poin (1% = 100), dibulatkan ke bawah
    pagu_bp: int
    melebihi_pagu: bool

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SusutJalan:
    trip_kode: str
    susut_g: int
    susut_bp: int
    pagu_bp: int
    melebihi_pagu: bool


def _bp(susut: int, dasar: int) -> int:
    return susut * 10000 // dasar if dasar > 0 else 0


def rekap_harian(timbangan: Iterable[Mapping]) -> list[RekapSusut]:
    """Input: payload timbangan terparse (`ditimbang_at`, `komoditas`, `berat_kebun_g`, `berat_gudang_g`)."""
    agg: dict[tuple[str, str], list[int]] = {}
    for t in timbangan:
        kunci = (t["ditimbang_at"][:10], t["komoditas"])
        a = agg.setdefault(kunci, [0, 0])
        a[0] += t["berat_kebun_g"]
        a[1] += t["berat_gudang_g"]
    hasil = []
    for (tgl, kom), (kebun, gudang) in sorted(agg.items()):
        susut = max(kebun - gudang, 0)
        bp = _bp(susut, kebun)
        pagu = PAGU_SUSUT_BP[kom]
        hasil.append(RekapSusut(tgl, kom, kebun, gudang, susut, bp, pagu, bp > pagu))
    return hasil


def susut_jalan(trips: Iterable[Mapping]) -> list[SusutJalan]:
    hasil = []
    for t in trips:
        susut = max(t["berat_muat_g"] - t["berat_terima_g"], 0)
        bp = _bp(susut, t["berat_muat_g"])
        hasil.append(SusutJalan(t["trip_kode"], susut, bp, PAGU_SUSUT_JALAN_BP, bp > PAGU_SUSUT_JALAN_BP))
    return hasil
