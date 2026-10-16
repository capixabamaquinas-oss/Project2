"""Portable .babel archives containing a metadata database and verified payload files."""
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
from .index import BabelIndex, payload_directory_for
from .storage import stream_decompress_verify, PayloadError, CHUNK_SIZE

class BabelPackage:
    def __init__(self, package_path: str):
        self.package_path = str(Path(package_path).resolve())
        self.index: Optional[BabelIndex] = None

    def create(self) -> None:
        self.index = BabelIndex(self.package_path)

    def open(self) -> None:
        if not os.path.exists(self.package_path):
            raise FileNotFoundError(f"Pacote não encontrado: {self.package_path}")
        self.index = BabelIndex(self.package_path)

    def _require_index(self) -> BabelIndex:
        if self.index is None:
            if os.path.exists(self.package_path):
                self.open()
            else:
                self.create()
        return self.index

    def export(self, output_path: str) -> None:
        index = self._require_index()
        rows = index.list_all()
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(index.db_path, "index.sqlite")
            archive.writestr("metadata.json", json.dumps({
                "version": "1.0.0", "items": index.count_items(),
                "aliases": index.count_aliases()
            }, indent=2))
            for item in rows:
                content_hash, compressed_size = item[1], item[8]
                path = index.payload_path(content_hash)
                if not path.is_file():
                    raise FileNotFoundError(f"Payload ausente para exportação: {content_hash}")
                if path.stat().st_size != compressed_size:
                    raise PayloadError(f"Tamanho comprimido incorreto: {content_hash}")
                archive.write(path, f"payloads/{content_hash}")

    def import_package(self, package_path: str, merge: bool = True) -> int:
        """Validate an archive, then merge it into this persistent destination package."""
        index = self._require_index()
        with tempfile.TemporaryDirectory(prefix="babel_import_") as tmp:
            root = Path(tmp).resolve()
            with zipfile.ZipFile(package_path, "r") as archive:
                for info in archive.infolist():
                    target = (root / info.filename).resolve()
                    if not target.is_relative_to(root):
                        raise ValueError(f"Caminho suspeito no pacote: {info.filename}")
                archive.extractall(root)
            source_db = root / "index.sqlite"
            if not source_db.is_file():
                raise ValueError("Pacote inválido: index.sqlite não encontrado")
            source_index = BabelIndex(str(source_db))
            source_rows = source_index.list_all()
            # Validate every payload's compressed length, decompression, content length, and SHA-256 before copying/indexing.
            for item in source_rows:
                content_hash, original_size, compressed_size = item[1], item[7], item[8]
                payload = root / "payloads" / content_hash
                if not payload.is_file():
                    raise ValueError(f"Payload ausente no pacote: {content_hash}")
                stream_decompress_verify(str(payload), content_hash, original_size, compressed_size)
            destination_root = payload_directory_for(index.db_path)
            destination_root.mkdir(parents=True, exist_ok=True)
            for item in source_rows:
                content_hash, compressed_size = item[1], item[8]
                source_payload = root / "payloads" / content_hash
                destination_payload = index.payload_path(content_hash)
                existing = index.get_by_hash(content_hash)
                if existing is not None and destination_payload.exists():
                    continue
                if existing is not None and existing[8] != compressed_size:
                    raise ValueError(f"Payload existente ausente e formato comprimido incompatível: {content_hash}")
                fd, temp_name = tempfile.mkstemp(prefix=".tmp_import_", dir=str(destination_root))
                try:
                    with source_payload.open("rb") as src, os.fdopen(fd, "wb") as dst:
                        shutil.copyfileobj(src, dst, length=CHUNK_SIZE)
                        dst.flush(); os.fsync(dst.fileno())
                    os.replace(temp_name, destination_payload)
                except Exception:
                    try: os.unlink(temp_name)
                    except OSError: pass
                    raise
            return index.merge(str(source_db))

    def merge_packages(self, other_package_path: str) -> int:
        return self.import_package(other_package_path, merge=True)
