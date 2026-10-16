"""SQLite index storing metadata only; payload bytes live beside the package."""
import sqlite3
from pathlib import Path
from typing import Optional, Tuple, List

ITEM_COLUMNS = "id, content_hash, hexagon, wall, shelf, volume, page, original_size, compressed_size"

def payload_directory_for(db_path: str) -> Path:
    """Return the sidecar directory dedicated to one package database."""
    return Path(str(Path(db_path).resolve()) + ".payloads")

class BabelIndex:
    def __init__(self, db_path: str):
        self.db_path = str(Path(db_path).resolve())
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT UNIQUE NOT NULL,
                hexagon INTEGER NOT NULL, wall INTEGER NOT NULL,
                shelf INTEGER NOT NULL, volume INTEGER NOT NULL, page INTEGER NOT NULL,
                original_size INTEGER NOT NULL, compressed_size INTEGER NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                content_hash TEXT NOT NULL REFERENCES items(content_hash)
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_aliases_hash ON aliases(content_hash)")
            conn.commit()
        finally:
            conn.close()

    def add_item(self, content_hash: str, hexagon: int, wall: int, shelf: int,
                 volume: int, page: int, original_size: int, compressed_size: int) -> bool:
        conn = self._connect()
        try:
            with conn:
                cur = conn.execute("""INSERT INTO items
                    (content_hash, hexagon, wall, shelf, volume, page, original_size, compressed_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(content_hash) DO NOTHING""",
                    (content_hash, hexagon, wall, shelf, volume, page, original_size, compressed_size))
            return cur.rowcount == 1
        finally:
            conn.close()

    def add_item_and_alias(self, content_hash: str, coords: Tuple[int, int, int, int, int],
                           original_size: int, compressed_size: int, path: str) -> bool:
        """Insert metadata and alias in one transaction; return whether item was new."""
        conn = self._connect()
        try:
            with conn:
                row = conn.execute("SELECT original_size, compressed_size FROM items WHERE content_hash=?",
                                   (content_hash,)).fetchone()
                inserted = row is None
                if inserted:
                    conn.execute("""INSERT INTO items
                        (content_hash, hexagon, wall, shelf, volume, page, original_size, compressed_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (content_hash, *coords, original_size, compressed_size))
                elif row != (original_size, compressed_size):
                    raise ValueError("Metadados existentes não correspondem ao conteúdo")
                alias = conn.execute("SELECT content_hash FROM aliases WHERE path=?", (path,)).fetchone()
                if alias is not None and alias[0] != content_hash:
                    raise ValueError(f"O alias já pertence a outro conteúdo: {path}")
                conn.execute("INSERT OR IGNORE INTO aliases(path, content_hash) VALUES (?, ?)",
                             (path, content_hash))
            return inserted
        finally:
            conn.close()

    def add_alias(self, path: str, content_hash: str) -> None:
        conn = self._connect()
        try:
            with conn:
                alias = conn.execute("SELECT content_hash FROM aliases WHERE path=?", (path,)).fetchone()
                if alias is not None and alias[0] != content_hash:
                    raise ValueError(f"O alias já pertence a outro conteúdo: {path}")
                conn.execute("INSERT OR IGNORE INTO aliases(path, content_hash) VALUES (?, ?)",
                             (path, content_hash))
        finally:
            conn.close()

    def get_by_hash(self, content_hash: str) -> Optional[Tuple]:
        conn = self._connect()
        try:
            return conn.execute(f"SELECT {ITEM_COLUMNS} FROM items WHERE content_hash=?",
                                (content_hash,)).fetchone()
        finally:
            conn.close()

    def get_by_path(self, path: str) -> Optional[Tuple]:
        conn = self._connect()
        try:
            return conn.execute("SELECT i.id, i.content_hash, i.hexagon, i.wall, i.shelf, i.volume, i.page, i.original_size, i.compressed_size FROM items i JOIN aliases a "
                                "ON i.content_hash=a.content_hash WHERE a.path=?", (path,)).fetchone()
        finally:
            conn.close()

    def payload_path(self, content_hash: str) -> Path:
        return payload_directory_for(self.db_path) / content_hash

    def list_all(self) -> List[Tuple]:
        conn = self._connect()
        try:
            return conn.execute(f"SELECT {ITEM_COLUMNS} FROM items ORDER BY id").fetchall()
        finally:
            conn.close()

    def list_aliases(self) -> List[Tuple[str, str]]:
        conn = self._connect()
        try:
            return conn.execute("SELECT path, content_hash FROM aliases ORDER BY id").fetchall()
        finally:
            conn.close()

    def count_items(self) -> int:
        conn = self._connect()
        try:
            return conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        finally:
            conn.close()

    def count_aliases(self) -> int:
        conn = self._connect()
        try:
            return conn.execute("SELECT COUNT(*) FROM aliases").fetchone()[0]
        finally:
            conn.close()

    def vacuum(self) -> None:
        conn = self._connect()
        try:
            conn.execute("VACUUM")
        finally:
            conn.close()

    def merge(self, other_db_path: str) -> int:
        """Merge metadata and aliases using one destination transaction."""
        other = sqlite3.connect(other_db_path)
        conn = self._connect()
        try:
            items = other.execute(f"SELECT {ITEM_COLUMNS.replace('id, ', '')} FROM items").fetchall()
            aliases = other.execute("SELECT path, content_hash FROM aliases ORDER BY id").fetchall()
            with conn:
                added = 0
                for row in items:
                    cur = conn.execute("""INSERT INTO items
                        (content_hash, hexagon, wall, shelf, volume, page, original_size, compressed_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(content_hash) DO NOTHING""", row)
                    added += cur.rowcount
                for path, content_hash in aliases:
                    conn.execute("INSERT OR IGNORE INTO aliases(path, content_hash) VALUES (?, ?)",
                                 (path, content_hash))
            return added
        finally:
            conn.close()
            other.close()

