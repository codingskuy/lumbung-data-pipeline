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
