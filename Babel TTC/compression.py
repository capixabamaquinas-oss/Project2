"""
Compressão — zlib (biblioteca padrão).
"""

import zlib

COMPRESSION_LEVEL = 6


def compress(data: bytes) -> bytes:
    """Comprime dados com zlib nível 6."""
    return zlib.compress(data, COMPRESSION_LEVEL)


def decompress(data: bytes) -> bytes:
    """Descomprime dados zlib."""
    return zlib.decompress(data)
