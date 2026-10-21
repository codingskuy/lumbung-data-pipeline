# ingest-pasar-induk

- **Sumber**: CSV `tanggal_survei,komoditas,referensi,harga_per_kg` (rupiah integer/kg); `referensi` ∈ `pasar_induk`, `pasar_kota`, `eceran_daring` (keuangan/20-papan-harga-mingguan.md).
- **Jadwal**: harian 05.00 WIB (`docs/schedule.md`), sehingga 3 referensi tersedia sebelum papan Jumat 15.00.
- **Kunci idempotensi**: `(tanggal_survei, komoditas, referensi)` -> `uuid` UUIDv5.
- **Tujuan**: `POST /pipeline/harga-referensi` (asumsi, `docs/api-asumsi.md`); tiap baris membawa `sumber`, `diingest_at`, `simpan_sampai` (= tanggal survei + 6 bulan).
- **Lembar kerja** (3 harga + tanggal survei per komoditas) untuk audit sengketa: `--lembar-kerja-out lk.json`; minimal disimpan 6 bulan (`boleh_dihapus` melarang pembuangan lebih awal).
- **Harian**: `python -m lumbung_pipeline ingest-pasar-induk --berkas pi.csv --tanggal 2026-10-09` (kode keluar 3 bila ada referensi kurang untuk tanggal itu).
- **Backfill**: hanya `--dari D --sampai E` eksplisit; tanpa tanggal atau rentang = galat.
- **Monitoring**: log terstruktur `{"pipeline","masuk","duplikat","gagal"}` tiap jalan.
