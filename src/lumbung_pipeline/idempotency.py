"""Kunci idempoten deterministik dari kunci alami (AGENTS butir 8)."""

from __future__ import annotations

import uuid

# Namespace tetap: mengubahnya mengubah semua uuid (jangan diubah tanpa ADR).
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/Coding-Skuy/lumbung-data-pipeline")


def uuid_dari_kunci_alami(jenis: str, *bagian: str) -> str:
    """UUIDv5 stabil: kunci alami yang sama selalu menghasilkan uuid yang sama."""
    return str(uuid.uuid5(NAMESPACE, "|".join((jenis, *bagian))))
