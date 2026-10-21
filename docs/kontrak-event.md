# Kontrak event keluar Lumbung -> Titeny

Sumber: KONTEKS-LINTAS-DIVISI §3 (registry 11 event terkunci), Titeny `data/20-kontrak-event.md` (amplop, pengiriman, versi). Dokumen ini hanya mencatat bagian yang diproduksi pipeline ini dan konsumennya.

## Event yang diproduksi (`source: lumbung`, `schema_version: 1`)

| `event_type` | Payload wajib (Titeny §3) | Konsumen terdokumentasi | Dasar konsumen (Titeny `10-sumber-data.md`) |
|---|---|---|---|
| `panen.dicatat` | `panen_id, komoditas_id, hasil_g, tanggal_panen` | Titeny: model panen | S5 |
| `harga.diperbarui` | `pasar_id, komoditas_id, tanggal, harga_per_kg` (integer rupiah > 0) | Titeny: model prediksi harga | S1 (lihat catatan) |
| `stok.berubah` | `gudang_id, komoditas_id, perubahan_g, stok_akhir_g, alasan` | Titeny: model harga + panen/demand | S2 |
| `stok.snapshot_harian` | `gudang_id, tanggal, baris[{komoditas_id, stok_g}], jumlah_baris` | Titeny: model harga + panen/demand | S2 |

Konsumen tunggal pintu masuk: Titeny `POST /api/v1/event/masuk`. Pipeline tidak menulis ke DB divisi lain.

## Satuan berat dan penerbit (keputusan user, ASUMSI)

- Semua berat payload dalam **gram bilangan bulat** (`hasil_g`, `perubahan_g`, `stok_akhir_g`, `baris[].stok_g`); float/kg desimal ditolak oleh `events.validasi_payload`. Ini berbeda dari Titeny §3 (`*_kg` desimal); perlu disepakati dengan Titeny, KONTEKS/TownHall tidak diubah.
- `harga.diperbarui` diterbitkan Lumbung (`source: lumbung`): USULAN keputusan user, belum ada dokumen yang menyebut penerbitnya (Titeny §2 menulis `pasaree`).

## Amplop

`event_id` (`evt_YYYYMMDD_NNNNNN`, tanggal dari `occurred_at`, urutan dari berkas penghitung), `event_type`, `schema_version` (1), `source` (`lumbung`), `occurred_at`, `received_at` (waktu pipeline menerima kejadian domain), `batch_id`, `payload`.

## Pengiriman

Header `X-Idempotency-Key: <event_id>`; timeout 10 dtk; retry 3x dengan jeda 5/30/300 dtk (event_id sama dipakai ulang) lalu DLQ (JSONL: amplop + alasan + jumlah percobaan). `200 duplikat_diabaikan` dihitung duplikat, bukan galat. `422` (dan 4xx lain) tidak di-retry: langsung DLQ, perbaiki dan kirim ulang dengan `event_id` baru. Jalankan: `python -m lumbung_pipeline.kirim_event --berkas e.jsonl --dlq dlq.jsonl --urutan seq.json` (env `TITENY_API_URL`).

## Aturan

Dilarang menambah `event_type` di luar 4 di atas tanpa bump versi + 30 hari dual-read (KONTEKS §9); `events.EVENT_TYPES` dikunci dan diuji.

## Ketidaksesuaian dokumen (untuk manajer; tidak diputuskan sepihak)

1. Titeny §2 menetapkan `harga.diperbarui` bersumber `pasaree`, sedangkan tiket LMB-DATA-004 dan ADR-0001 menugaskan Lumbung mengirimnya dengan `source: lumbung`. Payload Titeny (`pasar_id`, `jumlah_sampel_lapak`) juga berorientasi harga lapak Pasaree, bukan papan harga Lumbung.
2. Titeny §2 menandai `keuangan.ringkasan_harian` (S10) bersumber Lumbung, tetapi tiket hanya meminta 4 event; event ini belum dikirim.
3. ADR-0001 menyebut event domain FSD/30 (`lot.disortir`, `trip.dimuat`, ...) harus dipetakan ke registry; pemetaan belum ditetapkan di dokumen sumber, jadi belum diimplementasikan.
4. Titeny tidak mendokumentasikan autentikasi pintu masuk; hanya `X-Idempotency-Key` dikirim (asumsi).
5. `event_id` harus unik global, tetapi tidak ada alokator lintas-sumber; urutan di sini per pipeline Lumbung.
