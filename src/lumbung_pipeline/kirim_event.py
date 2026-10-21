"""CLI kirim-event: baca JSONL kejadian domain -> amplop -> Titeny (retry/DLQ).

Tiap baris: {"event_type","payload","occurred_at","batch_id"}. `received_at` = waktu pipeline menerima kejadian.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from .batch import BatchStats
from .events import EventError, SequenceStore, buat_amplop
from .pipelines.timbangan import sekarang
from .titeny import DeadLetterQueue, TitenyClient, kirim_dengan_retry


def main(argv: list[str] | None = None, client: TitenyClient | None = None, sleep=None) -> int:
    p = argparse.ArgumentParser(prog="lumbung_pipeline.kirim_event")
    p.add_argument("--berkas", required=True, help="JSONL kejadian domain")
    p.add_argument("--dlq", required=True, help="berkas DLQ JSONL")
    p.add_argument("--urutan", required=True, help="berkas JSON penghitung event_id")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = client or TitenyClient(os.environ["TITENY_API_URL"])
    seq, dlq = SequenceStore(a.urutan), DeadLetterQueue(a.dlq)
    stats = BatchStats("kirim-event")
    kw = {"sleep": sleep} if sleep else {}
    for baris in Path(a.berkas).read_text(encoding="utf-8").splitlines():
        if not baris.strip():
            continue
        try:
            k = json.loads(baris)
            amplop = buat_amplop(k["event_type"], k["payload"], k["occurred_at"], sekarang(), k["batch_id"], seq)
        except (EventError, KeyError, ValueError) as e:
            stats.gagal += 1
            logging.getLogger("lumbung_pipeline").error("kejadian tidak sah: %s", e)
            continue
        h = kirim_dengan_retry(client, amplop, dlq, **kw)
        if h.status == "diterima":
            stats.masuk += 1
        elif h.status == "duplikat":
            stats.duplikat += 1
        else:
            stats.gagal += 1
    logging.getLogger("lumbung_pipeline").info("selesai %s", stats.as_log())
    return 1 if stats.gagal else 0


if __name__ == "__main__":
    sys.exit(main())
