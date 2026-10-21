import json
from datetime import date

import pytest

from lumbung_pipeline.client import LumbungClient, Response
from lumbung_pipeline.config import Config
from lumbung_pipeline.pipelines import pasar_induk as pi


def baris(kom="cabai", ref="pasar_induk", harga="36000", tgl="2026-10-09"):
    return {"tanggal_survei": tgl, "komoditas": kom, "referensi": ref, "harga_per_kg": harga}


def klien(simpan):
    def t(m, u, h, data):
        b = json.loads(data)
        if b["uuid"] in simpan:
            return Response(200, {"duplikat": True})
        simpan[b["uuid"]] = b
        return Response(201, {"duplikat": False})

    return LumbungClient(Config("http://api", "K"), t)


def lengkap(tgl="2026-10-09"):
    return [baris(k, r, "1000", tgl) for k in pi.KOMODITAS_PILOT for r in pi.REFERENSI]


def test_idempoten_dan_menyimpan_tanggal_survei_dan_retensi():
    simpan = {}
    c = klien(simpan)
    assert pi.ingest(c, lengkap(), "pi.csv").masuk == 9
    s = pi.ingest(c, lengkap(), "pi.csv")
    assert (s.masuk, s.duplikat) == (0, 9) and len(simpan) == 9
    b = next(iter(simpan.values()))
    assert b["tanggal_survei"] == "2026-10-09" and b["simpan_sampai"] == "2027-04-09"


def test_retensi_6_bulan_akhir_bulan():
    assert pi.simpan_sampai(date(2026, 8, 31)) == date(2027, 2, 28)
    assert not pi.boleh_dihapus(date(2026, 10, 9), date(2027, 4, 9))
    assert pi.boleh_dihapus(date(2026, 10, 9), date(2027, 4, 10))


def test_kekurangan_referensi_sebelum_papan():
    rows = [pi.parse_baris(r, "x", "t") for r in lengkap()]
    assert pi.kekurangan(rows, date(2026, 10, 9)) == []
    rows.pop()  # kangkung/eceran_daring hilang
    assert pi.kekurangan(rows, date(2026, 10, 9)) == [("kangkung", "eceran_daring")]
    assert len(pi.kekurangan(rows, date(2026, 10, 10))) == 9


def test_lembar_kerja_3_harga():
    rows = [pi.parse_baris(baris(ref=r, harga=h), "x", "t") for r, h in zip(pi.REFERENSI, ("36000", "34000", "35000"))]
    lk = pi.lembar_kerja(rows, date(2026, 10, 9))
    assert lk["komoditas"]["cabai"] == {"pasar_induk": 36000, "pasar_kota": 34000, "eceran_daring": 35000}
    assert lk["tanggal_survei"] == "2026-10-09"


def test_backfill_hanya_rentang_eksplisit():
    rows = [baris(tgl="2026-10-01"), baris(tgl="2026-10-05"), baris(tgl="2026-10-09")]
    dalam = pi.filter_rentang(rows, date(2026, 10, 2), date(2026, 10, 6))
    assert [r["tanggal_survei"] for r in dalam] == ["2026-10-05"]
    with pytest.raises(ValueError):
        pi.filter_rentang(rows, date(2026, 10, 6), date(2026, 10, 2))


@pytest.mark.parametrize("kolom,nilai", [("referensi", "pasar_x"), ("harga_per_kg", "0"), ("harga_per_kg", "35.5"), ("tanggal_survei", "9-10-2026"), ("komoditas", "beras")])
def test_baris_tidak_sah(kolom, nilai):
    with pytest.raises(ValueError):
        pi.parse_baris(dict(baris(), **{kolom: nilai}), "x", "t")
