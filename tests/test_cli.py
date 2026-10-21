import json

from lumbung_pipeline.cli import main
from lumbung_pipeline.client import LumbungClient, Response
from lumbung_pipeline.config import Config

CSV = (
    "lot_kode,komoditas,berat_kebun_g,berat_gudang_g,ditimbang_at\n"
    "L-1,cabai,100000,90000,2026-10-10T07:00:00+07:00\n"
    "L-2,mangga,1,1,2026-10-10T07:00:00+07:00\n"
)


def test_cli_ingest_dan_rekap(tmp_path):
    f = tmp_path / "timbang.csv"
    f.write_text(CSV, encoding="utf-8")
    out = tmp_path / "rekap.json"
    c = LumbungClient(Config("http://api", "K"), lambda *a: Response(201, {"duplikat": False}))
    kode = main(["ingest-timbangan", "--berkas", str(f), "--rekap-out", str(out)], client=c)
    assert kode == 1  # satu baris gagal -> kode keluar non-nol, tetapi baris sah tetap masuk
    (rekap,) = json.loads(out.read_text())
    assert rekap["komoditas"] == "cabai" and rekap["susut_bp"] == 1000 and rekap["melebihi_pagu"]


def _csv_pi(tmp_path, lengkap=True):
    from lumbung_pipeline.pipelines import pasar_induk as pi

    baris = ["tanggal_survei,komoditas,referensi,harga_per_kg"]
    for k in pi.KOMODITAS_PILOT:
        for r in pi.REFERENSI:
            baris.append(f"2026-10-09,{k},{r},1000")
    if not lengkap:
        baris.pop()
    baris.append("2026-09-01,cabai,pasar_induk,1")
    f = tmp_path / "pi.csv"
    f.write_text("\n".join(baris) + "\n", encoding="utf-8")
    return f


def _ok():
    return LumbungClient(Config("http://api", "K"), lambda *a: Response(201, {"duplikat": False}))


def test_cli_pasar_induk_harian_lengkap_dan_lembar_kerja(tmp_path):
    out = tmp_path / "lk.json"
    kode = main(["ingest-pasar-induk", "--berkas", str(_csv_pi(tmp_path)), "--tanggal", "2026-10-09", "--lembar-kerja-out", str(out)], client=_ok())
    assert kode == 0  # baris 2026-09-01 di luar tanggal, tidak diingest
    (lk,) = json.loads(out.read_text())
    assert set(lk["komoditas"]) == {"cabai", "bawang", "kangkung"}


def test_cli_pasar_induk_kode_3_bila_referensi_kurang(tmp_path):
    f = _csv_pi(tmp_path, lengkap=False)
    assert main(["ingest-pasar-induk", "--berkas", str(f), "--tanggal", "2026-10-09"], client=_ok()) == 3


def test_cli_pasar_induk_tanpa_tanggal_ditolak(tmp_path):
    import pytest

    with pytest.raises(SystemExit):
        main(["ingest-pasar-induk", "--berkas", str(_csv_pi(tmp_path))], client=_ok())
    with pytest.raises(SystemExit):
        main(["ingest-pasar-induk", "--berkas", str(_csv_pi(tmp_path)), "--dari", "2026-10-01"], client=_ok())
