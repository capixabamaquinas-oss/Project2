"""Integrity checks for on-disk payloads using bounded-memory streaming."""
from typing import Tuple, List, Optional
from .index import BabelIndex
from .storage import stream_decompress_verify, PayloadError

def _verify_item(index: BabelIndex, item) -> Tuple[bool, Optional[str]]:
    content_hash, original_size, compressed_size = item[1], item[7], item[8]
    path = index.payload_path(content_hash)
    if not path.is_file():
        return False, f"Hash {content_hash[:16]}...: payload não encontrado"
    try:
        stream_decompress_verify(str(path), content_hash, original_size, compressed_size)
    except (OSError, PayloadError) as exc:
        return False, f"Hash {content_hash[:16]}...: {exc}"
    return True, None

def validate_package(index: BabelIndex) -> Tuple[bool, List[str]]:
    errors = []
    for item in index.list_all():
        valid, error = _verify_item(index, item)
        if not valid: errors.append(error)
    return not errors, errors

def verify_file(index: BabelIndex, path: str) -> Tuple[bool, Optional[str]]:
    item = index.get_by_path(path)
    if item is None: item = index.get_by_hash(path)
    if item is None: return False, f"Arquivo não encontrado: {path}"
    return _verify_item(index, item)
