import pytest

from lumbung_pipeline.client import LumbungClient, Response
from lumbung_pipeline.config import Config
from lumbung_pipeline.pipelines import trip

ROW = {
    "trip_kode": "TRIP-UT-041",
    "komoditas": "bawang",
    "berat_muat_g": "200000",
    "berat_terima_g": "197000",
    "berangkat_at": "2026-10-10T05:00:00+07:00",
    "tiba_at": "2026-10-10T06:10:00+07:00",
}


def test_ingest_ulang_trip_tidak_menggandakan():
    simpan = {}

    def t(method, url, headers, data):
        import json

        b = json.loads(data)
        if b["uuid"] in simpan:
            return Response(200, {"duplikat": True})
        simpan[b["uuid"]] = b
        return Response(201, {"duplikat": False})

    c = LumbungClient(Config("http://api", "K"), t)
    assert trip.ingest(c, [ROW], "trip.csv").masuk == 1
    assert trip.ingest(c, [ROW], "trip.csv").duplikat == 1
    assert len(simpan) == 1
    (b,) = simpan.values()
    assert b["sumber"] == "trip.csv" and b["diingest_at"]


def test_kunci_alami_hanya_kode_trip():
    a = trip.parse_baris(ROW, "x", "t1")
    b = trip.parse_baris(dict(ROW, berat_terima_g="1"), "y", "t2")
    assert a["uuid"] == b["uuid"]


@pytest.mark.parametrize("kolom,nilai", [("trip_kode", "UT-041"), ("komoditas", "beras"), ("tiba_at", "kemarin")])
def test_trip_tidak_sah(kolom, nilai):
    with pytest.raises(ValueError):
        trip.parse_baris(dict(ROW, **{kolom: nilai}), "x", "t")
