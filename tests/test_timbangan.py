import pytest

from lumbung_pipeline.client import LumbungClient, Response
from lumbung_pipeline.config import Config
from lumbung_pipeline.pipelines import timbangan

ROW = {
    "lot_kode": "L-8812",
    "komoditas": "Cabai",
    "berat_kebun_g": "100000",
    "berat_gudang_g": "95000",
    "ditimbang_at": "2026-10-10T07:15:00+07:00",
}


class Palsu:
    """Backend palsu: uuid yang sama dibalas 200 duplikat, tanpa baris ganda."""

    def __init__(self, gagal_lot=()):
        self.tersimpan, self.headers, self.gagal_lot = {}, [], gagal_lot

    def __call__(self, method, url, headers, data):
        import json

        self.headers.append(headers)
        body = json.loads(data)
        if body["lot_kode"] in self.gagal_lot:
            return Response(500, {"pesan": "galat"})
        if body["uuid"] in self.tersimpan:
            return Response(200, {"duplikat": True})
        self.tersimpan[body["uuid"]] = body
        return Response(201, {"duplikat": False})


def klien(p):
    return LumbungClient(Config("http://api", "K"), p)


def test_parse_menyimpan_sumber_dan_waktu_ingest():
    p = timbangan.parse_baris(ROW, "timbang-2026-10-10.csv", "2026-10-10T08:00:00+00:00")
    assert p["sumber"] == "timbang-2026-10-10.csv"
    assert p["diingest_at"] == "2026-10-10T08:00:00+00:00"
    assert p["komoditas"] == "cabai" and p["berat_gudang_g"] == 95000


def test_ingest_ulang_tidak_menggandakan():
    p = Palsu()
    c = klien(p)
    s1 = timbangan.ingest(c, [ROW], "a.csv")
    s2 = timbangan.ingest(c, [ROW], "a.csv")
    assert (s1.masuk, s1.duplikat) == (1, 0)
    assert (s2.masuk, s2.duplikat) == (0, 1)
    assert len(p.tersimpan) == 1


def test_kegagalan_satu_baris_tidak_menghentikan_sisanya():
    p = Palsu(gagal_lot=("L-BAD",))
    rows = [dict(ROW, lot_kode="L-BAD"), dict(ROW, lot_kode="L-2"), dict(ROW, komoditas="mangga")]
    s = timbangan.ingest(klien(p), rows, "a.csv", ukuran_batch=1)
    assert (s.masuk, s.gagal) == (1, 2)  # 500 backend + komoditas tidak sah


@pytest.mark.parametrize("kolom,nilai", [("berat_gudang_g", "-1"), ("berat_kebun_g", "1.5"), ("ditimbang_at", "2026-10-10T07:15:00")])
def test_baris_tidak_sah_ditolak(kolom, nilai):
    with pytest.raises(ValueError):
        timbangan.parse_baris(dict(ROW, **{kolom: nilai}), "a.csv", "t")


def test_service_key_dikirim():
    p = Palsu()
    timbangan.ingest(klien(p), [ROW], "a.csv")
    assert p.headers[0]["X-Service-Key"] == "K"
