"""Eksekusi per-batch: kegagalan satu batch tidak menghentikan batch berikutnya."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Callable, Iterable, Iterator, Sequence, TypeVar

T = TypeVar("T")
log = logging.getLogger("lumbung_pipeline")


@dataclass
class BatchStats:
    pipeline: str
    masuk: int = 0
    duplikat: int = 0
    gagal: int = 0

    def as_log(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def potong(items: Sequence[T], ukuran: int) -> Iterator[Sequence[T]]:
    for i in range(0, len(items), ukuran):
        yield items[i : i + ukuran]


def jalankan_batch(
    pipeline: str,
    items: Iterable[T],
    kirim: Callable[[T], bool],
    ukuran_batch: int = 50,
) -> BatchStats:
    """`kirim(item)` -> True bila duplikat, False bila baru; exception = gagal.

    Gagal pada satu baris dihitung + dicatat, lalu lanjut; log terstruktur di akhir.
    """
    stats = BatchStats(pipeline)
    for no, batch in enumerate(potong(list(items), ukuran_batch), start=1):
        for item in batch:
            try:
                if kirim(item):
                    stats.duplikat += 1
                else:
                    stats.masuk += 1
            except Exception as e:  # noqa: BLE001 - batas isolasi kegagalan
                stats.gagal += 1
                log.error("batch=%d gagal: %s", no, e)
    log.info("selesai %s", stats.as_log())
    return stats
