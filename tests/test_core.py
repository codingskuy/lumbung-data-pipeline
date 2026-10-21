import pytest

from lumbung_pipeline.batch import jalankan_batch
from lumbung_pipeline.client import ApiError, LumbungClient, Response
from lumbung_pipeline.config import Config, ConfigError
from lumbung_pipeline.idempotency import uuid_dari_kunci_alami


def test_config_wajib_dan_tidak_bocor_di_repr():
    with pytest.raises(ConfigError):
        Config.from_env({"LUMBUNG_API_URL": "http://x"})
    c = Config.from_env({"LUMBUNG_API_URL": "http://x/", "LUMBUNG_SERVICE_KEY": "rahasia"})
    assert c.api_url == "http://x"
    assert "rahasia" not in repr(c)


def test_uuid_deterministik_dan_beda_per_jenis():
    a = uuid_dari_kunci_alami("timbangan", "L-1", "t")
    assert a == uuid_dari_kunci_alami("timbangan", "L-1", "t")
    assert a != uuid_dari_kunci_alami("trip", "L-1", "t")


def _client(responses, calls):
    def transport(method, url, headers, data):
        calls.append((method, url, dict(headers), data))
        return responses.pop(0)

    return LumbungClient(Config("http://api", "KUNCI"), transport)


def test_client_kirim_service_key_dan_duplikat():
    calls = []
    c = _client([Response(201, {}), Response(200, {"duplikat": True})], calls)
    assert c.post_idempoten("/p", {"uuid": "u"}) is False
    assert c.post_idempoten("/p", {"uuid": "u"}) is True
    assert calls[0][2]["X-Service-Key"] == "KUNCI"
    assert calls[0][1] == "http://api/p"


def test_client_galat_tidak_membocorkan_kunci():
    c = _client([Response(403, {"pesan": "ditolak"})], [])
    with pytest.raises(ApiError) as e:
        c.post_idempoten("/p", {})
    assert "KUNCI" not in str(e.value) and e.value.status == 403


def test_batch_gagal_satu_tidak_menghentikan_berikutnya():
    def kirim(x):
        if x == 2:
            raise RuntimeError("boom")
        return x == 3  # 3 = duplikat

    s = jalankan_batch("t", [1, 2, 3, 4], kirim, ukuran_batch=2)
    assert (s.masuk, s.duplikat, s.gagal) == (2, 1, 1)
