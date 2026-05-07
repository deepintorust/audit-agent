from __future__ import annotations

import hashlib


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def short_id_from_hash(hash_full_hex: str, length: int = 16) -> str:
    # Keep short ids stable but always store full hash in DB for collision detection.
    if len(hash_full_hex) < length:
        raise ValueError("hash too short")
    return hash_full_hex[:length]

