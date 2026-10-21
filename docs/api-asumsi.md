# Asumsi kontrak API (lumbung-backend-service)

`docs/api/openapi.yaml` v1.0.0 repo `lumbung-backend-service` (commit `04c3e25`) belum memuat endpoint ingest untuk `X-Service-Key`. Pipeline memakai asumsi berikut; ganti saat kontrak resmi terbit (perubahan kontrak wajib ADR + bump versi).

| Asumsi | Bentuk | Dasar |
|---|---|---|
| `POST /pipeline/timbangan` | body `{uuid, lot_kode, komoditas, berat_kebun_g, berat_gudang_g, ditimbang_at, sumber, diingest_at}`; `201` baru, `200 {duplikat:true}` ulang | konvensi idempotensi openapi.yaml ("POST membawa uuid klien") |
| `POST /pipeline/trip` | body `{uuid, trip_kode, komoditas, berat_muat_g, berat_terima_g, berangkat_at, tiba_at, sumber, diingest_at}` | idem |
| `POST /pipeline/harga-referensi` | body `{uuid, tanggal_survei, komoditas, referensi, harga_per_kg, simpan_sampai, sumber, diingest_at}` | idem; retensi 6 bulan dari keuangan/20 butir 4 |
| Satuan gram integer | `*_g` integer | openapi.yaml + KONTEKS §6 |

Sudah ada di kontrak dan dipakai apa adanya (serviceKey): `GET /admin/rekap-harian`, `POST /admin/papan-harga`.

Diperiksa ulang terhadap `lumbung-backend-service` (working tree, setelah commit 94e7a3c): endpoint `X-Service-Key` yang ada hanya `/admin/*` (rekap-harian, papan-harga, invoice, mitra, insiden); belum ada endpoint ingest timbangan/trip/harga-referensi, jadi asumsi di atas tetap berlaku.

Keputusan berat: gram bilangan bulat di semua tempat pipeline (CSV, payload ingest, rekap, event); kg desimal tidak diterima. Temuan untuk backend: `migrations/0001_init.sql` masih memakai `NUMERIC(10,2)` kg (`berat_kebun_kg`, `berat_gudang_kg`, `susut_kg`), tidak selaras dengan openapi dan KONTEKS §6 (gram integer).
