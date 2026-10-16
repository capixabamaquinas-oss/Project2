"""Suíte de testes do núcleo H1 — Babel Pura.

Cobertura:
- Todas as sequências de até 2 bytes (imagem de E = [0, 65792])
- Séries de FF (carry/borrow overflow)
- chunk_size 1, 3 e 64
- Índice inválido (não mínimo)
- Round-trip: encode -> decode para todos os métodos
"""
from __future__ import annotations

import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from babel_pura.codec import (
    add_one_reverse,
    decode_format,
    decode_h1_integer,
    decode_monolithic_file,
    decode_segmented_reverse,
    decode_segmented_two_pass,
    encode_format,
    encode_h1_integer,
    encode_monolithic_file,
    encode_segmented_reverse,
    encode_segmented_two_pass,
    integer_minimal_bytes,
    offset_for_length,
    subtract_one_reverse,
)


class TestExhaustive(unittest.TestCase):
    """Todas as sequências de até 2 bytes."""

    def test_exhaustive_image(self):
        seen = set()
        e = encode_h1_integer(b"")
        self.assertEqual(e, 0)
        seen.add(e)
        for b in range(256):
            e = encode_h1_integer(bytes([b]))
            self.assertGreaterEqual(e, 1)
            self.assertLessEqual(e, 256)
            self.assertNotIn(e, seen)
            seen.add(e)
        for b0 in range(256):
            for b1 in range(256):
                data = bytes([b0, b1])
                e = encode_h1_integer(data)
                self.assertGreaterEqual(e, 257)
                self.assertLessEqual(e, 65792)
                self.assertNotIn(e, seen)
                seen.add(e)
        self.assertEqual(len(seen), 65793)
        self.assertEqual(min(seen), 0)
        self.assertEqual(max(seen), 65792)

    def test_exhaustive_round_trip(self):
        self.assertEqual(decode_h1_integer(0), b"")
        for b in range(256):
            e = encode_h1_integer(bytes([b]))
            self.assertEqual(decode_h1_integer(e), bytes([b]))
        for b0 in range(256):
            for b1 in range(256):
                data = bytes([b0, b1])
                e = encode_h1_integer(data)
                self.assertEqual(decode_h1_integer(e), data)


class TestFFSeries(unittest.TestCase):
    """Séries de FF (carry/borrow overflow)."""

    def test_ff_series_round_trip(self):
        for length in [1, 2, 10, 100, 255, 256, 257, 1000]:
            data = b"\xff" * length
            e = encode_h1_integer(data)
            self.assertEqual(decode_h1_integer(e), data)

    def test_ff_series_file_round_trip(self):
        methods = ["monolithic", "segmented-reverse", "segmented-two-pass"]
        for length in [1, 100, 1000]:
            data = b"\xff" * length
            for method in methods:
                with self.subTest(length=length, method=method):
                    result = self._round_trip(data, method)
                    self.assertEqual(result, data)

    def _round_trip(self, data: bytes, method: str, chunk_size: int = 65536) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "input.bin"
            idx = Path(tmpdir) / "index.bin"
            out = Path(tmpdir) / "output.bin"
            src.write_bytes(data)
            if method == "monolithic":
                encode_monolithic_file(src, idx)
            elif method == "segmented-reverse":
                encode_segmented_reverse(src, idx, chunk_size)
            elif method == "segmented-two-pass":
                encode_segmented_two_pass(src, idx, chunk_size)
            if method == "monolithic":
                decode_monolithic_file(idx, out)
            elif method == "segmented-reverse":
                decode_segmented_reverse(idx, out, chunk_size)
            elif method == "segmented-two-pass":
                decode_segmented_two_pass(idx, out, chunk_size)
            return out.read_bytes()


class TestChunkSizes(unittest.TestCase):
    """chunk_size 1, 3 e 64."""

    def test_chunk_size_1(self):
        rng = random.Random(42)
        for size in [1, 10, 100]:
            data = rng.randbytes(size)
            for method in ["segmented-reverse", "segmented-two-pass"]:
                with self.subTest(size=size, method=method):
                    result = self._round_trip(data, method, chunk_size=1)
                    self.assertEqual(result, data)

    def test_chunk_size_3(self):
        rng = random.Random(42)
        for size in [1, 10, 100]:
            data = rng.randbytes(size)
            for method in ["segmented-reverse", "segmented-two-pass"]:
                with self.subTest(size=size, method=method):
                    result = self._round_trip(data, method, chunk_size=3)
                    self.assertEqual(result, data)

    def test_chunk_size_64(self):
        rng = random.Random(42)
        for size in [1, 100, 1000]:
            data = rng.randbytes(size)
            for method in ["segmented-reverse", "segmented-two-pass"]:
                with self.subTest(size=size, method=method):
                    result = self._round_trip(data, method, chunk_size=64)
                    self.assertEqual(result, data)

    def _round_trip(self, data: bytes, method: str, chunk_size: int = 65536) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "input.bin"
            idx = Path(tmpdir) / "index.bin"
            out = Path(tmpdir) / "output.bin"
            src.write_bytes(data)
            if method == "monolithic":
                encode_monolithic_file(src, idx)
            elif method == "segmented-reverse":
                encode_segmented_reverse(src, idx, chunk_size)
            elif method == "segmented-two-pass":
                encode_segmented_two_pass(src, idx, chunk_size)
            if method == "monolithic":
                decode_monolithic_file(idx, out)
            elif method == "segmented-reverse":
                decode_segmented_reverse(idx, out, chunk_size)
            elif method == "segmented-two-pass":
                decode_segmented_two_pass(idx, out, chunk_size)
            return out.read_bytes()


class TestInvalidIndex(unittest.TestCase):
    """Índice inválido (não mínimo) rejeitado em todos os decodificadores."""

    def test_decode_monolithic_rejects_leading_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "index.bin"
            out = Path(tmpdir) / "output.bin"
            src.write_bytes(b"\x00\x01")
            with self.assertRaises(ValueError) as ctx:
                decode_monolithic_file(src, out)
            self.assertIn("minimal", str(ctx.exception))

    def test_decode_segmented_reverse_rejects_leading_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "index.bin"
            out = Path(tmpdir) / "output.bin"
            src.write_bytes(b"\x00\x01")
            with self.assertRaises(ValueError) as ctx:
                decode_segmented_reverse(src, out, 64)
            self.assertIn("minimal", str(ctx.exception))

    def test_decode_segmented_two_pass_rejects_leading_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "index.bin"
            out = Path(tmpdir) / "output.bin"
            src.write_bytes(b"\x00\x01")
            with self.assertRaises(ValueError) as ctx:
                decode_segmented_two_pass(src, out, 64)
            self.assertIn("minimal", str(ctx.exception))

    def test_decode_segmented_reverse_rejects_single_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "index.bin"
            out = Path(tmpdir) / "output.bin"
            src.write_bytes(b"\x00")
            with self.assertRaises(ValueError) as ctx:
                decode_segmented_reverse(src, out, 64)
            self.assertIn("minimal", str(ctx.exception))

    def test_decode_segmented_two_pass_rejects_single_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "index.bin"
            out = Path(tmpdir) / "output.bin"
            src.write_bytes(b"\x00")
            with self.assertRaises(ValueError) as ctx:
                decode_segmented_two_pass(src, out, 64)
            self.assertIn("minimal", str(ctx.exception))

    def test_decode_segmented_reverse_cleans_raw_on_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "index.bin"
            out = Path(tmpdir) / "output.bin"
            src.write_bytes(b"\x00\x01")
            with self.assertRaises(ValueError):
                decode_segmented_reverse(src, out, 64)
            raw = out.with_name(out.name + ".raw")
            self.assertFalse(raw.exists())

    def test_decode_segmented_two_pass_cleans_raw_on_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "index.bin"
            out = Path(tmpdir) / "output.bin"
            src.write_bytes(b"\x00\x01")
            with self.assertRaises(ValueError):
                decode_segmented_two_pass(src, out, 64)
            raw = out.with_name(out.name + ".raw")
            self.assertFalse(raw.exists())


class TestRoundTrip(unittest.TestCase):
    """Round-trip: encode -> decode para todos os métodos."""

    METHODS = ["monolithic", "segmented-reverse", "segmented-two-pass"]

    def test_round_trip_random(self):
        rng = random.Random(42)
        for size in [1, 10, 100, 1000, 10000]:
            data = rng.randbytes(size)
            for method in self.METHODS:
                with self.subTest(size=size, method=method):
                    result = self._round_trip(data, method)
                    self.assertEqual(result, data)

    def test_round_trip_empty(self):
        for method in self.METHODS:
            with self.subTest(method=method):
                result = self._round_trip(b"", method)
                self.assertEqual(result, b"")

    def test_round_trip_single_byte(self):
        for b in [0, 1, 127, 128, 255]:
            data = bytes([b])
            for method in self.METHODS:
                with self.subTest(byte=b, method=method):
                    result = self._round_trip(data, method)
                    self.assertEqual(result, data)

    def test_round_trip_all_byte_values(self):
        data = bytes(range(256))
        for method in self.METHODS:
            with self.subTest(method=method):
                result = self._round_trip(data, method)
                self.assertEqual(result, data)

    def _round_trip(self, data: bytes, method: str, chunk_size: int = 65536) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "input.bin"
            idx = Path(tmpdir) / "index.bin"
            out = Path(tmpdir) / "output.bin"
            src.write_bytes(data)
            if method == "monolithic":
                encode_monolithic_file(src, idx)
            elif method == "segmented-reverse":
                encode_segmented_reverse(src, idx, chunk_size)
            elif method == "segmented-two-pass":
                encode_segmented_two_pass(src, idx, chunk_size)
            if method == "monolithic":
                decode_monolithic_file(idx, out)
            elif method == "segmented-reverse":
                decode_segmented_reverse(idx, out, chunk_size)
            elif method == "segmented-two-pass":
                decode_segmented_two_pass(idx, out, chunk_size)
            return out.read_bytes()


if __name__ == "__main__":
    unittest.main()
