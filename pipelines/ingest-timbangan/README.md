# ingest-timbangan

- **Sumber**: berkas CSV timbang gudang (`lot_kode,komoditas,berat_kebun_g,berat_gudang_g,ditimbang_at`; berat gram integer, waktu ISO-8601 bersertifikat zona).
- **Jadwal**: tiap 15 menit 06.00-20.00 WIB (`docs/schedule.md`).
- **Kunci idempotensi**: `(lot_kode, ditimbang_at)` -> `uuid` UUIDv5 deterministik; ingest ulang dibalas `200 duplikat: true`.
- **Tujuan**: `POST /pipeline/timbangan` (asumsi, lihat `docs/api-asumsi.md`) dengan `X-Service-Key`. Tiap baris membawa `sumber` (nama berkas) dan `diingest_at`.
- **Jalankan**: `LUMBUNG_API_URL=... LUMBUNG_SERVICE_KEY=... python -m lumbung_pipeline ingest-timbangan --berkas timbang.csv --rekap-out rekap-susut.json`
- **Rekap susut harian** per komoditas terhadap pagu: cabai 6%, bawang 4%, kangkung 8% (`susut.rekap_harian`).
- Kegagalan satu baris dihitung dan dicatat; sisanya lanjut; kode keluar 1 bila ada gagal.
