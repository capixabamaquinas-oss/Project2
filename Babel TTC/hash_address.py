"""Content hashes, stable addresses, and deterministic descriptive coordinates."""
import hashlib
import re
from typing import Tuple

PAGES_PER_VOLUME = 100
VOLUMES_PER_SHELF = 100
SHELVES_PER_WALL = 100
WALLS_PER_HEXAGON = 100
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
ADDRESS_PREFIX = "BABEL://sha256:"

def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _check_hash(content_hash: str) -> str:
    normalized = content_hash.lower()
    if not _HASH_RE.fullmatch(normalized):
        raise ValueError("SHA-256 deve conter exatamente 64 dígitos hexadecimais")
    return normalized

def compute_address(content_hash: str, hexagon: int = 0, wall: int = 0,
                    shelf: int = 0, volume: int = 0, page: int = 0) -> str:
    return ADDRESS_PREFIX + _check_hash(content_hash)

def parse_address(address: str) -> Tuple[str, int, int, int, int, int]:
    if address.startswith(ADDRESS_PREFIX):
        content_hash = _check_hash(address[len(ADDRESS_PREFIX):])
        return (content_hash, *assign_coordinates(content_hash))
    parts = address.split(":", 1)
    if len(parts) == 2:
        content_hash = _check_hash(parts[0])
        coords = parts[1].split("/")
        if len(coords) == 5:
            return (content_hash, *(int(value) for value in coords))
    raise ValueError(f"Endereço inválido: {address}")

def hash_to_index(content_hash: str) -> int:
    return int(_check_hash(content_hash)[:16], 16)

def assign_coordinates(content_hash: str) -> Tuple[int, int, int, int, int]:
    index = hash_to_index(content_hash)
    page = index % PAGES_PER_VOLUME
    volume = (index // PAGES_PER_VOLUME) % VOLUMES_PER_SHELF
    shelf = (index // (PAGES_PER_VOLUME * VOLUMES_PER_SHELF)) % SHELVES_PER_WALL
    wall = (index // (PAGES_PER_VOLUME * VOLUMES_PER_SHELF * SHELVES_PER_WALL)) % WALLS_PER_HEXAGON
    hexagon = index // (PAGES_PER_VOLUME * VOLUMES_PER_SHELF * SHELVES_PER_WALL * WALLS_PER_HEXAGON)
    return (hexagon, wall, shelf, volume, page)
