# ingest-trip

- **Sumber**: berkas CSV log trip (`trip_kode,komoditas,berat_muat_g,berat_terima_g,berangkat_at,tiba_at`).
- **Jadwal**: tiap 1 jam (`docs/schedule.md`).
- **Kunci idempotensi**: `trip_kode` (contoh `TRIP-UT-041`) -> `uuid` UUIDv5.
- **Tujuan**: `POST /pipeline/trip` (asumsi, lihat `docs/api-asumsi.md`) dengan `X-Service-Key`; baris membawa `sumber` + `diingest_at`.
- **Jalankan**: `python -m lumbung_pipeline ingest-trip --berkas trip.csv --rekap-out susut-jalan.json`
- **Susut jalan** per trip terhadap pagu 2% (`susut.susut_jalan`).
