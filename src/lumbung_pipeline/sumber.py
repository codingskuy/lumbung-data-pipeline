"""Pembaca berkas sumber (CSV) dan penanda sumber untuk audit."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator


def baca_csv(path: str | Path) -> Iterator[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)
