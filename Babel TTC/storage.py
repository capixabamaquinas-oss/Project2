"""Local file storage and bounded-memory zlib streaming helpers."""
import hashlib
import os
import tempfile
import zlib
from pathlib import Path
from typing import Optional, Tuple, BinaryIO

CHUNK_SIZE = 1024 * 1024

class PayloadError(ValueError):
    pass

class StorageBackend:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _full_path(self, path: str) -> Path:
        return self.base_path / path

    def write(self, path: str, data: bytes) -> None:
        full = self._full_path(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(full.parent), prefix=f".tmp_{full.name}_")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data); f.flush(); os.fsync(f.fileno())
            os.replace(tmp, full)
        except Exception:
            try: os.unlink(tmp)
            except OSError: pass
            raise

    def exists(self, path: str) -> bool:
        return self._full_path(path).exists()

    def delete(self, path: str) -> None:
        self._full_path(path).unlink(missing_ok=True)

    def size(self, path: str) -> int:
        return self._full_path(path).stat().st_size

    def list_files(self, directory: str) -> list:
        root = self._full_path(directory)
        return [str(f.relative_to(self.base_path)) for f in root.rglob("*") if f.is_file()] if root.exists() else []

    def store_file_streaming(self, source_path: str, dest_dir: str = ".",
                             chunk_size: int = CHUNK_SIZE) -> Tuple[str, int, bool, str]:
        """Hash and zlib-compress to a temporary file, then atomically publish by hash."""
        payload_dir = self._full_path(dest_dir)
        payload_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(payload_dir), prefix=".tmp_payload_")
        hasher = hashlib.sha256()
        compressed_size = 0
        compressor = zlib.compressobj(6)
        try:
            with open(source_path, "rb") as src, os.fdopen(fd, "wb") as dst:
                while True:
                    chunk = src.read(chunk_size)
                    if not chunk: break
                    hasher.update(chunk)
                    block = compressor.compress(chunk)
                    if block:
                        dst.write(block); compressed_size += len(block)
                block = compressor.flush()
                if block:
                    dst.write(block); compressed_size += len(block)
                dst.flush(); os.fsync(dst.fileno())
            content_hash = hasher.hexdigest()
            final = payload_dir / content_hash
            existed = final.exists()
            os.replace(tmp, final)
            return content_hash, compressed_size, existed, str(final)
        except Exception:
            try: os.unlink(tmp)
            except OSError: pass
            raise

class LocalDiskStorage(StorageBackend):
    """Filesystem backend used for package payloads."""
    pass

def stream_decompress_verify(compressed_path: str, expected_hash: str, expected_size: int,
                             expected_compressed_size: Optional[int] = None,
                             output: Optional[BinaryIO] = None,
                             chunk_size: int = CHUNK_SIZE) -> Tuple[int, int]:
    """Stream-decompress, optionally write output, and validate hash and both lengths."""
    hasher = hashlib.sha256()
    output_size = compressed_size = 0
    dec = zlib.decompressobj()
    try:
        with open(compressed_path, "rb") as src:
            while True:
                data = src.read(chunk_size)
                if not data: break
                compressed_size += len(data)
                pending = data
                while pending:
                    block = dec.decompress(pending, chunk_size)
                    pending = dec.unconsumed_tail
                    if dec.unused_data:
                        raise PayloadError("bytes extras após o fluxo zlib")
                    if block:
                        output_size += len(block); hasher.update(block)
                        if output is not None: output.write(block)
                if dec.eof and src.peek(1):
                    raise PayloadError("bytes extras após o fluxo zlib")
            if not dec.eof:
                raise PayloadError("fluxo zlib incompleto")
            tail = dec.flush()
            if tail:
                output_size += len(tail); hasher.update(tail)
                if output is not None: output.write(tail)
    except zlib.error as exc:
        raise PayloadError(f"falha na descompressão zlib: {exc}") from exc
    if expected_compressed_size is not None and compressed_size != expected_compressed_size:
        raise PayloadError(f"tamanho comprimido divergente: {compressed_size} != {expected_compressed_size}")
    if output_size != expected_size:
        raise PayloadError(f"tamanho original divergente: {output_size} != {expected_size}")
    actual = hasher.hexdigest()
    if actual != expected_hash:
        raise PayloadError(f"SHA-256 divergente: esperado {expected_hash}, obtido {actual}")
    return output_size, compressed_size



