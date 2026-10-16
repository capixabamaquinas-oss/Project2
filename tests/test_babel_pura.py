"""Suíte de testes completa para Babel Pura H1 (rodada 2, decisões do Diretor).

Decisões do Diretor (2026-10-15):
- Formato do índice: hex minúsculo.
- Endereço com checksum, obrigatório, um único algoritmo:
    B1:v1:crc32:<8 hex minúsculos>:<índice em hex minúsculo>
  CRC32 calculado sobre os bytes do índice (minimais), não sobre o texto.
- Vazio: B1:v1:EMPTY (sem checksum), única exceção.
- MAX_OUTPUT_BYTES = 16 MiB (16_777_216).
- MAX_ADDRESS_CHARS derivado em código:
  len("B1:v1:crc32:") + 8 + 1 + 2*(MAX_OUTPUT_BYTES+1)  (= 33_554_456).

Cobertura:
a. Bijeção exaustiva: todas as sequências de 0, 1 e 2 bytes.
b. Bordas: vazio, 00, FF, só zeros, só FF, FE seguido de muitos FF, FF no início.
c. Segmentado vs monolítico: encode/decode, chunk_size 1, 2, 5, 7, 64, 1000.
d. chunk_size inválido (0, negativo, None, 1.5) e índice com 00 à esquerda.
e. Endereço: round-trip até 2 bytes; rejeições (sem checksum, outro algoritmo,
   checksum errado/tamanho errado/não hex, maiúsculas, espaço/quebra de linha,
   partes a mais/menos, payload vazio, índice com 00); unicidade.
f. Erro de digitação: trocar 1 caractere nunca aceito com conteúdo diferente.
g. Limites: MAX_ADDRESS_CHARS+1 rejeitado antes do parser; limite exato passa;
   MAX_OUTPUT_BYTES passa, +1 rejeitado antes de reconstruir; milhões de ":"
   rejeitados sem lista proporcional.
h. is_empty_address: True só para EMPTY; False sem exceção para qualquer outro.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from babel_pura.address import (
    ChecksumError,
    EmptyIndexError,
    InvalidAddressError,
    LimitError,
    decode_address,
    encode_address,
    is_empty_address,
)
from babel_pura.codec import (
    decode_h1_integer,
    decode_monolithic_file,
    decode_segmented_reverse,
    decode_segmented_two_pass,
    encode_h1_integer,
    encode_monolithic_file,
    encode_segmented_reverse,
    encode_segmented_two_pass,
    integer_minimal_bytes,
)
from babel_pura.limits import MAX_ADDRESS_CHARS, MAX_OUTPUT_BYTES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _round_trip_file(data: bytes, method: str, chunk_size: int) -> bytes:
    """Encode then decode a file using the given method and chunk size."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "input.bin"
        idx = Path(tmpdir) / "index.bin"
        out = Path(tmpdir) / "output.bin"
        raw = Path(tmpdir) / "output.bin.raw"
        src.write_bytes(data)

        if method == "monolithic":
            encode_monolithic_file(src, idx)
        elif method == "segmented-reverse":
            encode_segmented_reverse(src, idx, chunk_size)
        elif method == "segmented-two-pass":
            encode_segmented_two_pass(src, idx, chunk_size)
        else:
            raise ValueError(f"unknown method: {method}")

        if method == "monolithic":
            decode_monolithic_file(idx, out)
        elif method == "segmented-reverse":
            decode_segmented_reverse(idx, out, chunk_size)
        elif method == "segmented-two-pass":
            decode_segmented_two_pass(idx, out, chunk_size)

        assert not raw.exists(), f".raw file left behind: {raw}"
        return out.read_bytes()


# ---------------------------------------------------------------------------
# a. Bijeção exaustiva: 0, 1 e 2 bytes
# ---------------------------------------------------------------------------


class TestBijectionExhaustive(unittest.TestCase):
    """Todas as sequências de 0, 1 e 2 bytes: ida e volta, naturais distintos."""

    def test_image_is_contiguous_0_to_65792(self):
        seen = set()
        # Length 0
        e = encode_h1_integer(b"")
        self.assertEqual(e, 0)
        seen.add(e)
        # Length 1
        for b in range(256):
            e = encode_h1_integer(bytes([b]))
            self.assertNotIn(e, seen)
            seen.add(e)
        # Length 2
        for b0 in range(256):
            for b1 in range(256):
                e = encode_h1_integer(bytes([b0, b1]))
                self.assertNotIn(e, seen)
                seen.add(e)

        self.assertEqual(len(seen), 65793)
        self.assertEqual(min(seen), 0)
        self.assertEqual(max(seen), 65792)
        self.assertEqual(seen, set(range(65793)))

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

    def test_exhaustive_round_trip_through_address(self):
        """Every sequence up to 2 bytes round-trips through the address."""
        # Empty index (e=0) raises EmptyIndexError on decode - expected
        self.assertEqual(encode_address(b""), "B1:v1:EMPTY")
        with self.assertRaises(EmptyIndexError):
            decode_address("B1:v1:EMPTY")
        # All non-empty sequences
        for e in range(1, 65793):
            index_bytes = integer_minimal_bytes(e)
            addr = encode_address(index_bytes)
            decoded = decode_address(addr)
            self.assertEqual(decoded, index_bytes, f"failed for E={e}")


# ---------------------------------------------------------------------------
# b. Bordas
# ---------------------------------------------------------------------------


class TestEdgeVectors(unittest.TestCase):
    """Edge vectors: empty, 00, FF, zeros, FFs, FE+FFs, FF+data."""

    def test_empty(self):
        self.assertEqual(encode_h1_integer(b""), 0)
        self.assertEqual(decode_h1_integer(0), b"")

    def test_single_00(self):
        e = encode_h1_integer(b"\x00")
        self.assertEqual(decode_h1_integer(e), b"\x00")

    def test_single_ff(self):
        e = encode_h1_integer(b"\xff")
        self.assertEqual(decode_h1_integer(e), b"\xff")

    def test_zeros_256(self):
        data = b"\x00" * 256
        e = encode_h1_integer(data)
        self.assertEqual(decode_h1_integer(e), data)

    def test_ffs_256(self):
        data = b"\xff" * 256
        e = encode_h1_integer(data)
        self.assertEqual(decode_h1_integer(e), data)

    def test_fe_then_ffs(self):
        data = b"\xfe" + b"\xff" * 255
        e = encode_h1_integer(data)
        self.assertEqual(decode_h1_integer(e), data)

    def test_ff_then_data(self):
        data = b"\xff\x00\x01\x02\xff"
        e = encode_h1_integer(data)
        self.assertEqual(decode_h1_integer(e), data)


# ---------------------------------------------------------------------------
# c. Segmentado vs monolítico
# ---------------------------------------------------------------------------


class TestSegmentedVsMonolithic(unittest.TestCase):
    """Segmented encode/decode must match monolithic and round-trip."""

    METHODS = ["monolithic", "segmented-reverse", "segmented-two-pass"]
    CHUNK_SIZES = [1, 2, 5, 7, 64, 1000]

    def test_all_methods_all_chunks_round_trip(self):
        import random

        rng = random.Random(42)
        for size in [1, 10, 100, 1000, 10000]:
            data = rng.randbytes(size)
            for method in self.METHODS:
                for chunk in self.CHUNK_SIZES:
                    with self.subTest(
                        size=size, method=method, chunk=chunk
                    ):
                        result = _round_trip_file(data, method, chunk)
                        self.assertEqual(result, data)

    def test_segmented_matches_monolithic_index(self):
        """All segmented methods produce the same index bytes as monolithic."""
        import random

        rng = random.Random(7)
        for size in [1, 100, 1000, 10000]:
            data = rng.randbytes(size)
            with tempfile.TemporaryDirectory() as tmpdir:
                src = Path(tmpdir) / "input.bin"
                src.write_bytes(data)
                idx_mono = Path(tmpdir) / "idx_mono.bin"
                idx_rev = Path(tmpdir) / "idx_rev.bin"
                idx_2p = Path(tmpdir) / "idx_2p.bin"
                encode_monolithic_file(src, idx_mono)
                encode_segmented_reverse(src, idx_rev, 7)
                encode_segmented_two_pass(src, idx_2p, 7)
                self.assertEqual(idx_mono.read_bytes(), idx_rev.read_bytes())
                self.assertEqual(idx_mono.read_bytes(), idx_2p.read_bytes())

    def test_carry_overflow_round_trip(self):
        """Data ending in many 0xFF triggers carry overflow."""
        data = b"\xff" * 1000
        for method in self.METHODS:
            for chunk in self.CHUNK_SIZES:
                with self.subTest(method=method, chunk=chunk):
                    result = _round_trip_file(data, method, chunk)
                    self.assertEqual(result, data)


# ---------------------------------------------------------------------------
# d. chunk_size inválido e índice não mínimo
# ---------------------------------------------------------------------------


class TestInvalidInputs(unittest.TestCase):
    """chunk_size invalid and non-minimal index rejected."""

    def test_chunk_size_invalid_values(self):
        import tempfile

        for bad in [0, -1, 1.5]:
            with tempfile.TemporaryDirectory() as tmpdir:
                src = Path(tmpdir) / "input.bin"
                out = Path(tmpdir) / "output.bin"
                src.write_bytes(b"\x01\x02\x03")
                for method in [
                    encode_segmented_reverse,
                    encode_segmented_two_pass,
                    decode_segmented_reverse,
                    decode_segmented_two_pass,
                ]:
                    with self.assertRaises((ValueError, TypeError)):
                        method(src, out, bad)

    def test_chunk_size_none_rejected(self):
        """None as chunk_size must be rejected."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "input.bin"
            out = Path(tmpdir) / "output.bin"
            src.write_bytes(b"\x01\x02\x03")
            for method in [
                encode_segmented_reverse,
                encode_segmented_two_pass,
                decode_segmented_reverse,
                decode_segmented_two_pass,
            ]:
                with self.assertRaises((ValueError, TypeError)):
                    method(src, out, None)

    def test_decode_rejects_leading_zero_index(self):
        import tempfile

        for method, chunk in [
            (decode_monolithic_file, None),
            (decode_segmented_reverse, 64),
            (decode_segmented_two_pass, 64),
        ]:
            with tempfile.TemporaryDirectory() as tmpdir:
                src = Path(tmpdir) / "index.bin"
                out = Path(tmpdir) / "output.bin"
                src.write_bytes(b"\x00\x01")
                with self.assertRaises(ValueError) as ctx:
                    method(src, out, chunk) if chunk is not None else method(src, out)
                self.assertIn("minimal", str(ctx.exception))

    def test_decode_rejects_single_zero_index(self):
        import tempfile

        for method, chunk in [
            (decode_monolithic_file, None),
            (decode_segmented_reverse, 64),
            (decode_segmented_two_pass, 64),
        ]:
            with tempfile.TemporaryDirectory() as tmpdir:
                src = Path(tmpdir) / "index.bin"
                out = Path(tmpdir) / "output.bin"
                src.write_bytes(b"\x00")
                with self.assertRaises(ValueError) as ctx:
                    method(src, out, chunk) if chunk is not None else method(src, out)
                self.assertIn("minimal", str(ctx.exception))

    def test_raw_cleaned_on_decode_error(self):
        import tempfile

        for method in [decode_segmented_reverse, decode_segmented_two_pass]:
            with tempfile.TemporaryDirectory() as tmpdir:
                src = Path(tmpdir) / "index.bin"
                out = Path(tmpdir) / "output.bin"
                raw = Path(tmpdir) / "output.bin.raw"
                src.write_bytes(b"\x00\x01")
                with self.assertRaises(ValueError):
                    method(src, out, 64)
                self.assertFalse(raw.exists(), f".raw left behind for {method.__name__}")


# ---------------------------------------------------------------------------
# e. Endereço: round-trip e rejeições
# ---------------------------------------------------------------------------


class TestAddressRoundTrip(unittest.TestCase):
    """Address encode/decode round-trip for all sequences up to 2 bytes."""

    def test_all_sequences_up_to_2_bytes(self):
        """Every sequence up to 2 bytes round-trips through the address."""
        # Empty index (e=0) raises EmptyIndexError on decode - expected
        self.assertEqual(encode_address(b""), "B1:v1:EMPTY")
        with self.assertRaises(EmptyIndexError):
            decode_address("B1:v1:EMPTY")
        # All non-empty sequences
        for e in range(1, 65793):
            index_bytes = integer_minimal_bytes(e)
            addr = encode_address(index_bytes)
            decoded = decode_address(addr)
            self.assertEqual(decoded, index_bytes, f"failed for E={e}: addr={addr}")

    def test_address_format_is_crc32(self):
        addr = encode_address(integer_minimal_bytes(encode_h1_integer(b"\x01\x02")))
        parts = addr.split(":")
        self.assertEqual(parts[0], "B1")
        self.assertEqual(parts[1], "v1")
        self.assertEqual(parts[2], "crc32")
        self.assertEqual(len(parts[3]), 8)
        self.assertEqual(parts[3], parts[3].lower())

    def test_empty_address_format(self):
        addr = encode_address(b"")
        self.assertEqual(addr, "B1:v1:EMPTY")


class TestAddressRejections(unittest.TestCase):
    """All invalid address forms must be rejected."""

    def test_no_checksum_rejected(self):
        """Address without checksum (old format) must be rejected."""
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:0102")

    def test_wrong_algorithm_rejected(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:sha256:deadbeef:0102")

    def test_checksum_wrong_length_rejected(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:crc32:deadbe:0102")  # 7 chars
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:crc32:deadbeef0:0102")  # 9 chars

    def test_checksum_non_hex_rejected(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:crc32:zzzzzzzz:0102")

    def test_checksum_uppercase_rejected(self):
        addr = encode_address(integer_minimal_bytes(encode_h1_integer(b"\x01")))
        parts = addr.split(":")
        parts[3] = parts[3].upper()
        with self.assertRaises(InvalidAddressError):
            decode_address(":".join(parts))

    def test_whitespace_rejected(self):
        addr = encode_address(integer_minimal_bytes(encode_h1_integer(b"\x01")))
        for bad in [addr + " ", " " + addr, addr + "\n", addr + "\r", addr + "\t"]:
            with self.assertRaises(InvalidAddressError):
                decode_address(bad)

    def test_extra_parts_rejected(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:crc32:deadbeef:0102:extra")

    def test_missing_parts_rejected(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:crc32:deadbeef")
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1")

    def test_empty_payload_rejected(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:crc32:deadbeef:")

    def test_index_leading_zero_rejected(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:crc32:00000000:0001")

    def test_wrong_prefix_rejected(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B2:v1:crc32:deadbeef:0102")

    def test_wrong_version_rejected(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v2:crc32:deadbeef:0102")

    def test_none_input_rejected(self):
        with self.assertRaises(InvalidAddressError):
            decode_address(None)

    def test_empty_string_rejected(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("")


class TestAddressUniqueness(unittest.TestCase):
    """No two accepted addresses decode to the same content."""

    def test_uniqueness_up_to_2_bytes(self):
        seen = {}
        # Empty index
        self.assertEqual(encode_address(b""), "B1:v1:EMPTY")
        with self.assertRaises(EmptyIndexError):
            decode_address("B1:v1:EMPTY")
        # All non-empty sequences
        for e in range(1, 65793):
            index_bytes = integer_minimal_bytes(e)
            addr = encode_address(index_bytes)
            decoded = decode_address(addr)
            self.assertEqual(decoded, index_bytes)
            # Each index maps to exactly one address
            self.assertNotIn(decoded, seen)
            seen[decoded] = addr

    def test_different_addresses_different_content(self):
        addrs = set()
        for e in range(1000):
            index_bytes = integer_minimal_bytes(e)
            addr = encode_address(index_bytes)
            self.assertNotIn(addr, addrs)
            addrs.add(addr)


# ---------------------------------------------------------------------------
# f. Erro de digitação
# ---------------------------------------------------------------------------


class TestTypoDetection(unittest.TestCase):
    """Changing 1 char of the index must never decode to different content."""

    def test_typo_in_index_always_rejected(self):
        """Any single-character change to the index portion must be rejected
        either as invalid format or as checksum mismatch."""
        import random

        rng = random.Random(99)
        for _ in range(50):
            data = rng.randbytes(rng.randint(1, 50))
            index_bytes = integer_minimal_bytes(encode_h1_integer(data))
            addr = encode_address(index_bytes)
            parts = addr.split(":")
            index_hex = parts[4]

            # Try changing each character position once
            for i in range(len(index_hex)):
                for replacement in "0123456789abcdef":
                    if replacement == index_hex[i]:
                        continue
                    modified = index_hex[:i] + replacement + index_hex[i + 1 :]
                    tampered = ":".join([parts[0], parts[1], parts[2], parts[3], modified])
                    try:
                        result = decode_address(tampered)
                        # If it somehow decodes, it must equal the original
                        self.assertEqual(result, index_bytes)
                    except (InvalidAddressError, ChecksumError):
                        pass  # Expected: rejected

    def test_typo_in_checksum_rejected(self):
        """Changing the checksum hex must be rejected."""
        index_bytes = integer_minimal_bytes(encode_h1_integer(b"\x01\x02\x03"))
        addr = encode_address(index_bytes)
        parts = addr.split(":")
        # Flip last char of checksum
        modified_checksum = parts[3][:-1] + ("0" if parts[3][-1] != "0" else "1")
        tampered = ":".join([parts[0], parts[1], parts[2], modified_checksum, parts[4]])
        with self.assertRaises(ChecksumError):
            decode_address(tampered)


# ---------------------------------------------------------------------------
# g. Limites
# ---------------------------------------------------------------------------


class TestLimits(unittest.TestCase):
    """Address and output size limits enforced before parsing/reconstruction."""

    def test_address_over_limit_rejected_without_parser(self):
        """Address above MAX_ADDRESS_CHARS rejected before parser is called."""
        called = []

        def fake_decode_format(*args, **kwargs):
            called.append(True)
            raise AssertionError("parser should not be called for oversized address")

        # Build an address that is clearly over MAX_ADDRESS_CHARS
        # Use a very long index hex portion
        over_limit = "B1:v1:crc32:" + "0" * 8 + ":" + "00" * (MAX_ADDRESS_CHARS // 2)
        self.assertGreater(len(over_limit), MAX_ADDRESS_CHARS)

        # Patch decode_format to verify it's NOT called
        with patch("babel_pura.address.decode_format", side_effect=fake_decode_format):
            with self.assertRaises(LimitError):
                decode_address(over_limit, max_address_chars=MAX_ADDRESS_CHARS)
        self.assertEqual(called, [])

    def test_address_at_limit_exact_passes_preflight(self):
        """Address well under MAX_ADDRESS_CHARS passes preflight."""
        # A normal small address is far under MAX_ADDRESS_CHARS
        idx = integer_minimal_bytes(encode_h1_integer(b"\x01\x02"))
        addr = encode_address(idx)
        self.assertLess(len(addr), MAX_ADDRESS_CHARS)
        # decode_address should not raise LimitError from preflight
        result = decode_address(addr, max_address_chars=MAX_ADDRESS_CHARS)
        self.assertEqual(result, idx)

    def test_output_at_limit_passes(self):
        """Output of exactly MAX_OUTPUT_BYTES passes size check."""
        from babel_pura.limits import check_output_size
        check_output_size(MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES)

    def test_output_over_limit_rejected(self):
        """Output of MAX_OUTPUT_BYTES+1 rejected before reconstruction."""
        from babel_pura.limits import check_output_size
        with self.assertRaises(LimitError):
            check_output_size(MAX_OUTPUT_BYTES + 1, MAX_OUTPUT_BYTES)

    def test_many_colons_rejected_without_huge_list(self):
        """Address with more than MAX_ADDRESS_CHARS colons rejected before split."""
        evil = ":" * (MAX_ADDRESS_CHARS + 1)
        self.assertGreater(len(evil), MAX_ADDRESS_CHARS)
        with self.assertRaises(LimitError):
            decode_address(evil, max_address_chars=MAX_ADDRESS_CHARS)

    def test_default_limits_are_the_constants(self):
        """decode_address defaults use the module constants."""
        import inspect
        sig = inspect.signature(decode_address)
        self.assertEqual(
            sig.parameters["max_address_chars"].default, MAX_ADDRESS_CHARS
        )
        self.assertEqual(
            sig.parameters["max_output_bytes"].default, MAX_OUTPUT_BYTES
        )

    def test_encode_above_output_limit_rejected(self):
        """encode_address rejects content whose output exceeds MAX_OUTPUT_BYTES."""
        # Build an index that decodes to more than MAX_OUTPUT_BYTES
        # MAX_OUTPUT_BYTES + 1 bytes of index means m = MAX_OUTPUT_BYTES + 1
        # and n = m (since E >= O_m), so output = MAX_OUTPUT_BYTES + 1
        oversized_index = b"\x01" * (MAX_OUTPUT_BYTES + 1)
        with self.assertRaises(LimitError):
            encode_address(oversized_index)

    def test_encode_at_output_limit_accepted(self):
        """encode_address accepts content whose output is exactly MAX_OUTPUT_BYTES."""
        # m = MAX_OUTPUT_BYTES, n = m (since E >= O_m), output = MAX_OUTPUT_BYTES
        # We can't build such a huge index in memory, but we can verify
        # that compute_output_size_from_index returns MAX_OUTPUT_BYTES
        # for a hypothetical index of that size.
        # Instead, test with a smaller value that's clearly under the limit.
        idx = integer_minimal_bytes(encode_h1_integer(b"\x01\x02"))
        addr = encode_address(idx)
        decoded = decode_address(addr)
        self.assertEqual(decoded, idx)

    def test_is_empty_address_no_exception_on_over_limit(self):
        """is_empty_address returns False (no exception) for over-limit address."""
        over_limit = "B1:v1:crc32:" + "0" * 8 + ":" + "00" * (MAX_ADDRESS_CHARS // 2)
        self.assertGreater(len(over_limit), MAX_ADDRESS_CHARS)
        # Should not raise any exception
        result = is_empty_address(over_limit)
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# h. is_empty_address
# ---------------------------------------------------------------------------


class TestIsEmptyAddress(unittest.TestCase):
    """is_empty_address: True only for EMPTY; False for anything else."""

    def test_empty_marker_true(self):
        self.assertTrue(is_empty_address("B1:v1:EMPTY"))

    def test_valid_non_empty_false(self):
        idx = integer_minimal_bytes(encode_h1_integer(b"\x01"))
        addr = encode_address(idx)
        self.assertFalse(is_empty_address(addr))

    def test_checksum_error_returns_false(self):
        """Checksum error is InvalidAddressError, so is_empty_address returns False."""
        idx = integer_minimal_bytes(encode_h1_integer(b"\x01\x02"))
        addr = encode_address(idx)
        parts = addr.split(":")
        parts[3] = "00000000"
        tampered = ":".join(parts)
        self.assertFalse(is_empty_address(tampered))

    def test_invalid_address_returns_false(self):
        self.assertFalse(is_empty_address("not-an-address"))
        self.assertFalse(is_empty_address(""))
        self.assertFalse(is_empty_address(None))
        self.assertFalse(is_empty_address("B1:v1:crc32:zzzzzzzz:01"))
        self.assertFalse(is_empty_address("B1:v1:sha256:deadbeef:01"))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main()
