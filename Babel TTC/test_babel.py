"""Behavioral tests for Babel V1's actual CLI and persistent package paths."""
import contextlib
import hashlib
import io
import os
import pathlib
import random
import shutil
import sqlite3
import tempfile
import unittest
import zipfile
import zlib
from unittest import mock

from babel.cli import main
from babel.hash_address import compute_address, compute_hash, parse_address
from babel.index import BabelIndex
from babel.package import BabelPackage
from babel.storage import PayloadError

class TestBabelV1(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="babel_test_")
        self.root = pathlib.Path(self.temp.name)
        self.db = self.root / "main.sqlite"
        BabelPackage(str(self.db)).create()

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args):
        old_argv = __import__("sys").argv
        out, err = io.StringIO(), io.StringIO()
        code = 0
        try:
            __import__("sys").argv = ["babel", "--package", str(self.db), *map(str, args)]
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try: main()
                except SystemExit as exc: code = int(exc.code or 0)
            return code, out.getvalue(), err.getvalue()
        finally:
            __import__("sys").argv = old_argv

    def add_bytes(self, path, data, alias):
        source = self.root / path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(data)
        code, out, err = self.run_cli("add", source, "--path", alias)
        self.assertEqual((code, err), (0, ""), out + err)
        return source, out

    def get_bytes(self, alias, dest):
        code, out, err = self.run_cli("get", alias, "--output", self.root / dest)
        self.assertEqual((code, err), (0, ""), out + err)
        return (self.root / dest).read_bytes()

    def test_01_round_trip_edge_files(self):
        cases = [("empty.bin", b""), ("zeros.bin", b"\x00" * 257),
                 ("line_endings.bin", b"one\r\ntwo\nthree\r\n")]
        for name, data in cases:
            with self.subTest(name=name):
                alias = "edge/" + name
                self.add_bytes(name, data, alias)
                recovered = self.get_bytes("edge/" + name, "out_" + name)
                self.assertEqual(recovered, data)
                self.assertEqual(hashlib.sha256(recovered).hexdigest(), hashlib.sha256(data).hexdigest())

    def test_02_sha_address_resolves_same_content(self):
        data = b"same content"
        _, out = self.add_bytes("address.bin", data, "address.bin")
        address = next(line.split(": ", 1)[1] for line in out.splitlines() if line.startswith("Endereço:"))
        self.assertEqual(address, compute_address(compute_hash(data)))
        self.assertEqual(self.get_bytes(address, "address_out.bin"), data)
        self.assertEqual(parse_address(address)[0], compute_hash(data))

    def test_03_dedup_and_aliases(self):
        data = b"deduplicated data"
        self.add_bytes("first.bin", data, "first.bin")
        self.add_bytes("second.bin", data, "second.bin")
        index = BabelIndex(str(self.db))
        self.assertEqual(index.count_items(), 1)
        self.assertEqual(index.count_aliases(), 2)
        self.assertEqual(self.get_bytes("second.bin", "dedup_out.bin"), data)

    def test_04_add_writes_payload_outside_sqlite_and_per_package(self):
        data = random.Random(44).randbytes(12 * 1024 * 1024)
        self.add_bytes("large.bin", data, "large.bin")
        index = BabelIndex(str(self.db))
        payload = index.payload_path(hashlib.sha256(data).hexdigest())
        self.assertTrue(payload.is_file())
        self.assertEqual(payload.parent, pathlib.Path(str(self.db.resolve()) + ".payloads"))
        con = sqlite3.connect(self.db)
        try:
            columns = {row[1] for row in con.execute("PRAGMA table_info(items)")}
        finally: con.close()
        self.assertNotIn("payload", columns)
        self.assertEqual(self.get_bytes("large.bin", "large_out.bin"), data)

    def test_05_verify_detects_payload_tampering(self):
        data = b"original content for tamper test"
        self.add_bytes("tamper.bin", data, "tamper.bin")
        index = BabelIndex(str(self.db))
        item = index.get_by_path("tamper.bin")
        wrong = b"modified content for tamper test"
        self.assertEqual(len(wrong), len(data))
        compressed = zlib.compress(wrong, 6)
        index.payload_path(item[1]).write_bytes(compressed)
        code, out, err = self.run_cli("verify", "--file", "tamper.bin")
        self.assertNotEqual(code, 0)
        self.assertIn("SHA-256 divergente", err)

    def test_06_get_tampering_fails_without_partial_output(self):
        data = b"original content for tamper test"
        self.add_bytes("tamper_get.bin", data, "tamper_get.bin")
        index = BabelIndex(str(self.db)); item = index.get_by_path("tamper_get.bin")
        wrong = b"modified content for tamper test"
        index.payload_path(item[1]).write_bytes(zlib.compress(wrong, 6))
        target = self.root / "must_not_appear.bin"
        code, out, err = self.run_cli("get", "tamper_get.bin", "--output", target)
        self.assertNotEqual(code, 0)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob(".must_not_appear.bin.*.tmp")), [])
        self.assertIn("SHA-256 divergente", err)

    def test_07_export_import_new_package_round_trip(self):
        data = b"portable package\x00\r\nwith binary bytes"
        self.add_bytes("portable.bin", data, "folder/portable.bin")
        archive = self.root / "export.babel"
        code, out, err = self.run_cli("export", archive)
        self.assertEqual((code, err), (0, ""), out + err)
        imported_db = self.root / "imported.sqlite"
        imported = BabelPackage(str(imported_db)); imported.create()
        self.assertEqual(imported.import_package(str(archive)), 1)
        self.assertEqual(imported.index.count_items(), 1)
        self.assertEqual(imported.index.count_aliases(), 1)
        old_db = self.db
        try:
            self.db = imported_db
            self.assertEqual(self.get_bytes("folder/portable.bin", "imported_out.bin"), data)
        finally: self.db = old_db

    def test_import_rejects_tampered_payload_before_indexing(self):
        data = b"payload before archive tamper"
        self.add_bytes("archive_source.bin", data, "archive_source.bin")
        normal = self.root / "normal.babel"
        code, out, err = self.run_cli("export", normal)
        self.assertEqual((code, err), (0, ""), out + err)
        altered = self.root / "altered.babel"
        content_hash = hashlib.sha256(data).hexdigest()
        with zipfile.ZipFile(normal, "r") as source, zipfile.ZipFile(altered, "w") as dest:
            for info in source.infolist():
                payload = source.read(info.filename)
                if info.filename == f"payloads/{content_hash}":
                    payload = zlib.compress(data[::-1], 6)
                dest.writestr(info, payload)
        self.assertEqual(len(zlib.compress(data[::-1], 6)), len(zlib.compress(data, 6)))
        target_db = self.root / "bad_import_target.sqlite"
        target = BabelPackage(str(target_db)); target.create()
        with self.assertRaises(PayloadError):
            target.import_package(str(altered))
        index = BabelIndex(str(target_db))
        self.assertEqual(index.count_items(), 0)
        self.assertFalse(index.payload_path(content_hash).exists())
    def test_08_cli_add_streams_real_file_and_uses_sidecar(self):
        # Deterministic, multi-chunk file through the same CLI path used by users.
        data = random.Random(8).randbytes(8 * 1024 * 1024 + 37)
        self.add_bytes("multi_chunk.bin", data, "multi_chunk.bin")
        self.assertEqual(self.get_bytes("multi_chunk.bin", "multi_chunk_out.bin"), data)
        code, out, err = self.run_cli("verify")
        self.assertEqual((code, err), (0, ""), out + err)
        self.assertIn("1 itens", out)

    def test_09_retry_after_simulated_index_failure(self):
        data = b"retry must not produce an orphan alias"
        source = self.root / "retry.bin"; source.write_bytes(data)
        index = BabelIndex(str(self.db))
        original = BabelIndex.add_item_and_alias
        calls = {"count": 0}
        def fail_once(*args, **kwargs):
            if calls["count"] == 0:
                calls["count"] += 1
                raise sqlite3.OperationalError("simulated index failure")
            return original(*args, **kwargs)
        with mock.patch.object(BabelIndex, "add_item_and_alias", fail_once):
            with self.assertRaisesRegex(sqlite3.OperationalError, "simulated"):
                self.run_cli("add", source, "--path", "retry.bin")
        self.assertEqual(index.count_items(), 0)
        self.assertEqual(index.count_aliases(), 0)
        code, out, err = self.run_cli("add", source, "--path", "retry.bin")
        self.assertEqual((code, err), (0, ""), out + err)
        self.assertEqual(index.count_items(), 1)
        self.assertEqual(index.count_aliases(), 1)
        self.assertEqual(self.get_bytes("retry.bin", "retry_out.bin"), data)

    def test_10_address_is_independent_of_insertion_order(self):
        data_a, data_b = b"content A", b"content B"
        addresses = []
        for label, ordered in (("first", (data_a, data_b)), ("second", (data_b, data_a))):
            db = self.root / f"{label}.sqlite"; BabelPackage(str(db)).create()
            old_db = self.db; self.db = db
            try:
                for i, data in enumerate(ordered):
                    self.add_bytes(f"{label}_{i}.bin", data, f"{label}/{i}.bin")
                item = BabelIndex(str(db)).get_by_hash(hashlib.sha256(data_a).hexdigest())
                addresses.append(compute_address(item[1], *item[2:7]))
            finally: self.db = old_db
        self.assertEqual(addresses[0], addresses[1])
        self.assertTrue(addresses[0].startswith("BABEL://sha256:"))

    def test_11_zip_slip_is_rejected(self):
        archive = self.root / "malicious.babel"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("../../outside.txt", "must not escape")
        with self.assertRaisesRegex(ValueError, "Caminho suspeito"):
            BabelPackage(str(self.db)).import_package(str(archive))
        self.assertFalse((self.root.parent / "outside.txt").exists())

    def test_compression_helpers_round_trip(self):
        data = b"compression" * 1000
        self.assertEqual(zlib.decompress(zlib.compress(data, 6)), data)

    def test_coordinates_are_deterministic_from_hash(self):
        data = b"coordinate input"
        h = compute_hash(data)
        self.assertEqual(__import__("babel.hash_address", fromlist=["assign_coordinates"]).assign_coordinates(h),
                         __import__("babel.hash_address", fromlist=["assign_coordinates"]).assign_coordinates(h))

if __name__ == "__main__":
    unittest.main()





