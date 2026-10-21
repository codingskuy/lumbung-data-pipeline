# Changelog

Semua perubahan penting lumbung-data-pipeline dicatat di sini. Format mengikuti Keep a Changelog; versi mengikuti versi milestone Lumbung.

## [Belum dirilis]

### Ditambahkan
- LMB-DATA-004: event keluar ke Titeny (4 `event_type` terkunci, amplop `evt_YYYYMMDD_NNNNNN`, `X-Idempotency-Key`, retry 5/30/300 dtk lalu DLQ JSONL), `docs/kontrak-event.md` (konsumen + temuan ketidaksesuaian).
- LMB-DATA-002: `ingest-timbangan` dan `ingest-trip` idempoten (uuid dari kunci alami, sumber + waktu ingest, `X-Service-Key`), rekap susut harian vs pagu, CLI `python -m lumbung_pipeline`, ADR-0002 (Python), `docs/api-asumsi.md`.
- Fondasi AI-dev v1.0.0: `AGENTS.md`, `CLAUDE.md`, `docs/decisions/` (ADR-0001), `versions/v1.0.0/docs/40-TECHSTACK.md`, `versions/v1.0.0/docs/60-BLAST-RADIUS.md` (tiket LMB-DATA-001, 2026-10-14).
