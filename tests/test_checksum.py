"""Suíte de testes para checksum no babel_pura.address.

Cobre:
- encode_address_with_checksum / decode_address com checksum explícito
- Checksum mismatch rejection
- Empty index (EMPTY) without checksum
- Round-trip for various sizes
- Unknown checksum algorithm rejection
- Case sensitivity: uppercase checksum hex rejected
- Minimal envelope backward compatibility
"""
from __future__ import annotations

import unittest

from babel_pura.address import (
    CHECKSUM_BLAKE2S_128,
    CHECKSUM_CRC32,
    CHECKSUM_SHA256,
    CHECKSUM_SHA256_128,
    ChecksumError,
    EmptyIndexError,
    InvalidAddressError,
    decode_address,
    encode_address,
    encode_address_with_checksum,
    is_empty_address,
)
from babel_pura.codec import encode_h1_integer, integer_minimal_bytes


def _index_for(data: bytes) -> bytes:
    """Generate H1 minimal index bytes for raw data."""
    return integer_minimal_bytes(encode_h1_integer(data))


class TestChecksumEncodeDecode(unittest.TestCase):
    """Round-trip with all checksum algorithms."""

    def test_crc32_round_trip(self):
        for data in [b"\x01\x02", b"\xff" * 100, bytes(range(256))]:
            idx = _index_for(data)
            addr = encode_address_with_checksum(idx, CHECKSUM_CRC32)
            decoded = decode_address(addr)
            self.assertEqual(decoded, idx)

    def test_sha256_round_trip(self):
        for data in [b"\x01\x02", b"\xff" * 100, bytes(range(256))]:
            idx = _index_for(data)
            addr = encode_address_with_checksum(idx, CHECKSUM_SHA256)
            decoded = decode_address(addr)
            self.assertEqual(decoded, idx)

    def test_sha256_128_round_trip(self):
        for data in [b"\x01\x02", b"\xff" * 100]:
            idx = _index_for(data)
            addr = encode_address_with_checksum(idx, CHECKSUM_SHA256_128)
            decoded = decode_address(addr)
            self.assertEqual(decoded, idx)

    def test_blake2s_128_round_trip(self):
        for data in [b"\x01\x02", b"\xff" * 100]:
            idx = _index_for(data)
            addr = encode_address_with_checksum(idx, CHECKSUM_BLAKE2S_128)
            decoded = decode_address(addr)
            self.assertEqual(decoded, idx)

    def test_empty_index_no_checksum(self):
        addr = encode_address_with_checksum(b"", CHECKSUM_CRC32)
        self.assertEqual(addr, "B1:v1:EMPTY")
        self.assertTrue(is_empty_address(addr))
        with self.assertRaises(EmptyIndexError):
            decode_address(addr)

    def test_unknown_algorithm_rejected(self):
        idx = _index_for(b"\x01\x02")
        with self.assertRaises(ValueError):
            encode_address_with_checksum(idx, "md5")


class TestChecksumCaseSensitivity(unittest.TestCase):
    """Checksum hex must be lowercase; uppercase creates aliases."""

    def test_uppercase_checksum_rejected(self):
        idx = _index_for(b"\x01\x02")
        addr = encode_address_with_checksum(idx, CHECKSUM_CRC32)
        parts = addr.split(":")
        # Uppercase the checksum
        parts[3] = parts[3].upper()
        tampered = ":".join(parts)
        with self.assertRaises(ChecksumError):
            decode_address(tampered)

    def test_mixed_case_checksum_rejected(self):
        idx = _index_for(b"\x01\x02")
        addr = encode_address_with_checksum(idx, CHECKSUM_CRC32)
        parts = addr.split(":")
        # Mixed case
        parts[3] = "A" + parts[3][1:]
        tampered = ":".join(parts)
        with self.assertRaises(ChecksumError):
            decode_address(tampered)


class TestChecksumMismatch(unittest.TestCase):
    """Tampered checksum must be rejected."""

    def test_crc32_tampered(self):
        idx = _index_for(b"\x01\x02")
        addr = encode_address_with_checksum(idx, CHECKSUM_CRC32)
        parts = addr.split(":")
        parts[3] = "00000000"
        tampered = ":".join(parts)
        with self.assertRaises(ChecksumError):
            decode_address(tampered)

    def test_sha256_tampered(self):
        idx = _index_for(b"\x01\x02")
        addr = encode_address_with_checksum(idx, CHECKSUM_SHA256)
        parts = addr.split(":")
        parts[3] = "0" * 64
        tampered = ":".join(parts)
        with self.assertRaises(ChecksumError):
            decode_address(tampered)

    def test_malformed_checksum_is_invalid_address(self):
        """Checksum with non-hex chars raises InvalidAddressError, not ChecksumError."""
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:crc32:zz:0102")


class TestChecksumFormat(unittest.TestCase):
    """Envelope format correctness."""

    def test_crc32_format(self):
        idx = _index_for(b"\x01")
        addr = encode_address_with_checksum(idx, CHECKSUM_CRC32)
        parts = addr.split(":")
        self.assertEqual(parts[0], "B1")
        self.assertEqual(parts[1], "v1")
        self.assertEqual(parts[2], "crc32")
        self.assertEqual(len(parts[3]), 8)

    def test_sha256_format(self):
        idx = _index_for(b"\x01")
        addr = encode_address_with_checksum(idx, CHECKSUM_SHA256)
        parts = addr.split(":")
        self.assertEqual(parts[2], "sha256")
        self.assertEqual(len(parts[3]), 64)

    def test_sha256_128_format(self):
        idx = _index_for(b"\x01")
        addr = encode_address_with_checksum(idx, CHECKSUM_SHA256_128)
        parts = addr.split(":")
        self.assertEqual(parts[2], "sha256_128")
        self.assertEqual(len(parts[3]), 32)

    def test_blake2s_128_format(self):
        idx = _index_for(b"\x01")
        addr = encode_address_with_checksum(idx, CHECKSUM_BLAKE2S_128)
        parts = addr.split(":")
        self.assertEqual(parts[2], "blake2s_128")
        self.assertEqual(len(parts[3]), 32)


class TestMinimalEnvelopeStillWorks(unittest.TestCase):
    """Backward compatibility: minimal envelope without checksum."""

    def test_minimal_encode_decode(self):
        idx = _index_for(b"\x01\x02")
        addr = encode_address(idx)
        self.assertTrue(addr.startswith("B1:v1:"))
        decoded = decode_address(addr)
        self.assertEqual(decoded, idx)

    def test_minimal_empty(self):
        addr = encode_address(b"")
        self.assertEqual(addr, "B1:v1:EMPTY")

    def test_minimal_rejects_leading_zero(self):
        try:
            encode_address(b"\x00\x01")
            self.fail("Should have raised ValueError")
        except ValueError:
            pass

    def test_minimal_rejects_empty_payload(self):
        try:
            decode_address("B1:v1:")
            self.fail("Should have raised InvalidAddressError")
        except InvalidAddressError:
            pass


class TestIsEmptyAddress(unittest.TestCase):
    """is_empty_address returns False for any error, including checksum."""

    def test_valid_non_empty(self):
        idx = _index_for(b"\x01")
        addr = encode_address(idx)
        self.assertFalse(is_empty_address(addr))

    def test_empty_marker(self):
        self.assertTrue(is_empty_address("B1:v1:EMPTY"))

    def test_checksum_error_returns_false(self):
        """ChecksumError is subclass of InvalidAddressError, so is_empty_address
        returns False instead of propagating."""
        idx = _index_for(b"\x01\x02")
        addr = encode_address_with_checksum(idx, CHECKSUM_CRC32)
        parts = addr.split(":")
        parts[3] = "00000000"
        tampered = ":".join(parts)
        self.assertFalse(is_empty_address(tampered))

    def test_invalid_address_returns_false(self):
        self.assertFalse(is_empty_address("not-an-address"))
        self.assertFalse(is_empty_address(""))
        self.assertFalse(is_empty_address(None))


if __name__ == "__main__":
    unittest.main()
