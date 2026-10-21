# ADR-0002 — Bahasa implementasi pipeline: Python

- Status: Diterima
- Tanggal: 2026-10-21

## Konteks

ADR-0001 (butir 6) menunda pilihan bahasa pipeline ke ADR ini, sebelum kode pertama LMB-DATA-002. `pipelines/README.md` menyarankan Python atau Rust; stack terkunci divisi memakai Python untuk AI dan pipeline.

## Keputusan

1. Bahasa: **Python >= 3.11**, paket `lumbung_pipeline` di `src/` (layout `src`), satu modul per pipeline di `src/lumbung_pipeline/pipelines/`.
2. Runtime **tanpa dependensi pihak ketiga** (hanya pustaka standar: `urllib`, `csv`, `json`, `uuid`, `logging`) agar permukaan serangan kecil dan mudah dijalankan oleh cron/GitHub Actions. Dependensi pengembangan: `pytest`.
3. Akses data hanya lewat REST API `lumbung-backend-service` dengan header `X-Service-Key` (ADR-0001 butir 2); tidak ada driver basis data.
4. Idempotensi lewat `uuid` klien deterministik (UUIDv5 dari kunci alami) sesuai konvensi `openapi.yaml` ("POST membawa uuid klien; ulang -> 200 duplikat: true").
5. Konfigurasi hanya lewat variabel lingkungan: `LUMBUNG_API_URL`, `LUMBUNG_SERVICE_KEY` (tidak pernah dicatat di log atau repo).
6. Uji: `pytest`, TDD merah-hijau, tanpa jaringan nyata (transport disuntik/dipalsukan).

## Konsekuensi

- Jadwal di `docs/schedule.md` dijalankan oleh scheduler eksternal yang memanggil `python -m lumbung_pipeline <pipeline>`; scheduler bukan bagian ADR ini.
- Tambah dependensi runtime baru butuh ADR baru.
