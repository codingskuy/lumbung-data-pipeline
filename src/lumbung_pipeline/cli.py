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
from .pipelines import timbangan, trip
from .sumber import baca_csv


def _valid(parse, rows, sumber):
    for r in rows:
        try:
            yield parse(r, sumber, "")
        except ValueError:
            continue  # baris tidak sah sudah dihitung gagal oleh ingest


def main(argv: list[str] | None = None, client: LumbungClient | None = None) -> int:
    p = argparse.ArgumentParser(prog="lumbung_pipeline")
    p.add_argument("pipeline", choices=["ingest-timbangan", "ingest-trip"])
    p.add_argument("--berkas", required=True)
    p.add_argument("--rekap-out", help="tulis rekap susut JSON ke berkas ini")
    p.add_argument("--ukuran-batch", type=int, default=50)
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

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
