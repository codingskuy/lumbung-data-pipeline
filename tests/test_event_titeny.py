import json
import urllib.error

import pytest

from lumbung_pipeline import events
from lumbung_pipeline.client import Response
from lumbung_pipeline.titeny import DeadLetterQueue, TitenyClient, kirim_dengan_retry

PANEN = {"panen_id": "pn_20261001_0091", "komoditas_id": "cmd_cabai", "hasil_kg": 120.5, "tanggal_panen": "2026-10-01"}


def amplop(urutan=None, **kw):
    a = dict(event_type="panen.dicatat", payload=PANEN, occurred_at="2026-10-01T07:00:00+07:00",
             received_at="2026-10-01T07:00:05+07:00", batch_id="batch_lumbung_20261001_pagi")
    a.update(kw)
    return events.buat_amplop(urutan=urutan or events.SequenceStore(), **a)


def test_amplop_wajib_lengkap_dan_format_event_id():
    a = amplop()
    assert set(a) == {"event_id", "event_type", "schema_version", "source", "occurred_at", "received_at", "batch_id", "payload"}
    assert a["source"] == "lumbung" and a["schema_version"] == 1
    assert events.EVENT_ID_RE.match(a["event_id"]) and a["event_id"] == "evt_20261001_000001"


def test_event_id_berurutan_dan_persisten(tmp_path):
    f = tmp_path / "seq.json"
    a = amplop(events.SequenceStore(f))
    b = amplop(events.SequenceStore(f))  # proses baru, berkas sama
    assert (a["event_id"], b["event_id"]) == ("evt_20261001_000001", "evt_20261001_000002")


def test_empat_event_type_terkunci_dan_tolak_lainnya():
    assert events.EVENT_TYPES == ("panen.dicatat", "harga.diperbarui", "stok.berubah", "stok.snapshot_harian")
    for et in ("transaksi.dibuat", "lot.disortir", "keuangan.ringkasan_harian"):
        with pytest.raises(events.EventError):
            amplop(event_type=et)


@pytest.mark.parametrize("et,payload", [
    ("panen.dicatat", {"panen_id": "x"}),
    ("stok.berubah", {"gudang_id": "g", "komoditas_id": "c", "perubahan_kg": 1, "stok_akhir_kg": 2, "alasan": "hilang"}),
    ("harga.diperbarui", {"pasar_id": "p", "komoditas_id": "c", "tanggal": "2026-10-01", "harga_per_kg": 35.5}),
    ("stok.snapshot_harian", {"gudang_id": "g", "tanggal": "2026-10-01", "baris": [], "jumlah_baris": 3}),
])
def test_payload_tidak_sah_ditolak(et, payload):
    with pytest.raises(events.EventError):
        amplop(event_type=et, payload=payload)


def test_waktu_tanpa_zona_ditolak():
    with pytest.raises(events.EventError):
        amplop(occurred_at="2026-10-01T07:00:00")


class Seq:
    """Transport berskrip: daftar respons/exception dikonsumsi berurutan."""

    def __init__(self, *langkah):
        self.langkah, self.panggilan = list(langkah), []

    def __call__(self, method, url, headers, data):
        self.panggilan.append((method, url, dict(headers), data))
        x = self.langkah.pop(0)
        if isinstance(x, Exception):
            raise x
        return x


def jalankan(tmp_path, *langkah):
    t, tidur = Seq(*langkah), []
    dlq = DeadLetterQueue(tmp_path / "dlq.jsonl")
    h = kirim_dengan_retry(TitenyClient("http://titeny", t), amplop(), dlq, sleep=tidur.append)
    return h, t, tidur, dlq


def test_kirim_header_idempotency_key_dan_endpoint(tmp_path):
    h, t, tidur, dlq = jalankan(tmp_path, Response(200, {"status": "diterima"}))
    m, url, hd, data = t.panggilan[0]
    assert (m, url) == ("POST", "http://titeny/api/v1/event/masuk")
    assert hd["X-Idempotency-Key"] == json.loads(data)["event_id"]
    assert (h.status, h.percobaan, tidur, dlq.isi()) == ("diterima", 1, [], [])


def test_duplikat_bukan_error(tmp_path):
    h, *_ = jalankan(tmp_path, Response(200, {"status": "duplikat_diabaikan"}))
    assert h.status == "duplikat"


def test_retry_5_30_300_lalu_sukses(tmp_path):
    h, t, tidur, dlq = jalankan(tmp_path, Response(503, {}), urllib.error.URLError("putus"), Response(429, {}), Response(200, {"status": "ok"}))
    assert tidur == [5, 30, 300] and h.status == "diterima" and h.percobaan == 4 and dlq.isi() == []


def test_gagal_semua_masuk_dlq_setelah_3_retry(tmp_path):
    h, t, tidur, dlq = jalankan(tmp_path, *[Response(500, {})] * 4)
    assert tidur == [5, 30, 300] and len(t.panggilan) == 4 and h.status == "dlq"
    (baris,) = dlq.isi()
    assert baris["percobaan"] == 4 and baris["amplop"]["event_id"] == "evt_20261001_000001"
    assert "HTTP 500" in baris["alasan"]


def test_422_tidak_di_retry_langsung_dlq(tmp_path):
    h, t, tidur, dlq = jalankan(tmp_path, Response(422, {"status": "ditolak", "alasan": "x", "field": "payload"}))
    assert tidur == [] and len(t.panggilan) == 1 and h.status == "dlq"
    assert dlq.isi()[0]["alasan"].startswith("ditolak")


def test_event_id_sama_dipakai_ulang_pada_retry(tmp_path):
    _, t, *_ = jalankan(tmp_path, Response(500, {}), Response(200, {}))
    ids = {c[2]["X-Idempotency-Key"] for c in t.panggilan}
    assert len(ids) == 1


def test_cli_kirim_event_sukses_dan_dlq(tmp_path):
    from lumbung_pipeline import kirim_event

    k = {"event_type": "panen.dicatat", "payload": PANEN, "occurred_at": "2026-10-01T07:00:00+07:00", "batch_id": "b1"}
    f = tmp_path / "e.jsonl"
    f.write_text(json.dumps(k) + "\n" + json.dumps(dict(k, event_type="transaksi.dibuat")) + "\n", encoding="utf-8")
    t = Seq(Response(200, {"status": "diterima"}))
    args = ["--berkas", str(f), "--dlq", str(tmp_path / "dlq.jsonl"), "--urutan", str(tmp_path / "seq.json")]
    kode = kirim_event.main(args, client=TitenyClient("http://titeny", t), sleep=lambda s: None)
    assert kode == 1 and len(t.panggilan) == 1  # event_type terlarang tidak pernah dikirim
