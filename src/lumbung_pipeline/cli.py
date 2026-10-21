"""CLI: python -m lumbung_pipeline <pipeline> --berkas <csv> [--rekap-out <json>]."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import susut
from .client import LumbungClient
from .config import Config
from datetime import date

from .pipelines import pasar_induk, timbangan, trip
from .sumber import baca_csv


def _valid(parse, rows, sumber):
    for r in rows:
        try:
            yield parse(r, sumber, "")
        except ValueError:
            continue  # baris tidak sah sudah dihitung gagal oleh ingest


def _pasar_induk(a, client) -> int:
    """Harian: --tanggal. Backfill: --dari DAN --sampai eksplisit (tanpa keduanya = galat)."""
    if a.tanggal and (a.dari or a.sampai):
        raise SystemExit("pakai --tanggal ATAU --dari/--sampai, bukan keduanya")
    if a.tanggal:
        dari = sampai = date.fromisoformat(a.tanggal)
    elif a.dari and a.sampai:
        dari, sampai = date.fromisoformat(a.dari), date.fromisoformat(a.sampai)
    else:
        raise SystemExit("wajib --tanggal atau rentang eksplisit --dari dan --sampai (tanpa backfill implisit)")
    client = client or LumbungClient(Config.from_env())
    sumber = Path(a.berkas).name
    rows = pasar_induk.filter_rentang(baca_csv(a.berkas), dari, sampai)
    stats = pasar_induk.ingest(client, rows, sumber, a.ukuran_batch)
    valid = list(_valid(pasar_induk.parse_baris, rows, sumber))
    if a.lembar_kerja_out:
        lk = [pasar_induk.lembar_kerja(valid, d) for d in sorted({date.fromisoformat(v["tanggal_survei"]) for v in valid})]
        Path(a.lembar_kerja_out).write_text(json.dumps(lk, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if a.tanggal:
        kurang = pasar_induk.kekurangan(valid, dari)
        if kurang:
            logging.getLogger("lumbung_pipeline").warning("referensi kurang untuk %s: %s", a.tanggal, kurang)
            return 3
    return 1 if stats.gagal else 0


def main(argv: list[str] | None = None, client: LumbungClient | None = None) -> int:
    p = argparse.ArgumentParser(prog="lumbung_pipeline")
    p.add_argument("pipeline", choices=["ingest-timbangan", "ingest-trip", "ingest-pasar-induk"])
    p.add_argument("--berkas", required=True)
    p.add_argument("--rekap-out", help="tulis rekap susut JSON ke berkas ini")
    p.add_argument("--ukuran-batch", type=int, default=50)
    p.add_argument("--tanggal", help="ingest-pasar-induk: tanggal survei harian (YYYY-MM-DD)")
    p.add_argument("--dari", help="ingest-pasar-induk backfill: awal rentang eksplisit")
    p.add_argument("--sampai", help="ingest-pasar-induk backfill: akhir rentang eksplisit")
    p.add_argument("--lembar-kerja-out", help="ingest-pasar-induk: tulis lembar kerja audit JSON")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if a.pipeline == "ingest-pasar-induk":
        return _pasar_induk(a, client)
    client = client or LumbungClient(Config.from_env())
    sumber = Path(a.berkas).name
    rows = list(baca_csv(a.berkas))
    mod = timbangan if a.pipeline == "ingest-timbangan" else trip
    stats = mod.ingest(client, rows, sumber, a.ukuran_batch)
    if a.rekap_out:
        valid = list(_valid(mod.parse_baris, rows, sumber))
        if mod is timbangan:
            hasil = [r.as_dict() for r in susut.rekap_harian(valid)]
        else:
            hasil = [r.__dict__ for r in susut.susut_jalan(valid)]
        Path(a.rekap_out).write_text(json.dumps(hasil, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if stats.gagal else 0


if __name__ == "__main__":
    sys.exit(main())
