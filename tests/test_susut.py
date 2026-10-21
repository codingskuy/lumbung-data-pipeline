from lumbung_pipeline.susut import rekap_harian, susut_jalan


def t(kom, kebun, gudang, waktu="2026-10-10T07:00:00+07:00"):
    return {"komoditas": kom, "berat_kebun_g": kebun, "berat_gudang_g": gudang, "ditimbang_at": waktu}


def test_rekap_per_komoditas_dan_pagu():
    r = rekap_harian([
        t("cabai", 100000, 95000),       # 5% <= 6%
        t("cabai", 100000, 91000),       # total 14% -> 7% > 6%? (200k, 186k) = 7%
        t("bawang", 100000, 96000),      # tepat 4% = pagu, tidak melebihi
        t("kangkung", 100000, 91000),    # 9% > 8%
    ])
    per = {x.komoditas: x for x in r}
    assert per["cabai"].susut_bp == 700 and per["cabai"].melebihi_pagu
    assert per["bawang"].susut_bp == 400 and not per["bawang"].melebihi_pagu
    assert per["kangkung"].melebihi_pagu and per["kangkung"].pagu_bp == 800


def test_rekap_dipisah_per_tanggal_dan_dasar_nol():
    r = rekap_harian([t("cabai", 0, 0), t("cabai", 1000, 1000, "2026-10-11T07:00:00+07:00")])
    assert [x.tanggal for x in r] == ["2026-10-10", "2026-10-11"]
    assert all(x.susut_bp == 0 and not x.melebihi_pagu for x in r)


def test_susut_jalan_pagu_2_persen():
    ok, lebih = susut_jalan([
        {"trip_kode": "TRIP-UT-1", "berat_muat_g": 100000, "berat_terima_g": 98000},
        {"trip_kode": "TRIP-UT-2", "berat_muat_g": 100000, "berat_terima_g": 97900},
    ])
    assert not ok.melebihi_pagu and lebih.melebihi_pagu
