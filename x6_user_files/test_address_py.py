"""Tests for Babel Pura H1 address envelope (minimal implementation).

Covers:
- Round-trip encode/decode for various inputs
- Empty index marker
- Invalid prefix, version, payload
- Whitespace rejection (strict policy)
- Canonical form enforcement (no leading zeros)
"""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from babel_pura.address import (
    decode_address,
    encode_address,
    is_empty_address,
    AddressError,
    EmptyIndexError,
    InvalidAddressError,
)
from babel_pura.codec import decode_h1_integer, encode_h1_integer


class TestAddressRoundTrip(unittest.TestCase):
    """Test round-trip encode/decode for various inputs."""

    def test_empty(self):
        address = encode_address(b"")
        self.assertEqual(address, "B1:v1:EMPTY")
        with self.assertRaises(EmptyIndexError):
            decode_address(address)

    def test_single_byte(self):
        for b in [1, 2, 127, 128, 254, 255]:
            data = bytes([b])
            e = encode_h1_integer(data)
            if e == 0:
                index_bytes = b""
            else:
                index_bytes = e.to_bytes((e.bit_length() + 7) // 8, "big")
            address = encode_address(index_bytes)
            decoded = decode_address(address)
            self.assertEqual(decoded, index_bytes)

    def test_various_sizes(self):
        rng = random.Random(42)
        for size in [1, 10, 100, 1000, 10000]:
            data = rng.randbytes(size)
            e = encode_h1_integer(data)
            if e == 0:
                index_bytes = b""
            else:
                index_bytes = e.to_bytes((e.bit_length() + 7) // 8, "big")
            address = encode_address(index_bytes)
            decoded = decode_address(address)
            self.assertEqual(decoded, index_bytes)

    def test_all_byte_values(self):
        data = bytes(range(256))
        e = encode_h1_integer(data)
        index_bytes = e.to_bytes((e.bit_length() + 7) // 8, "big")
        address = encode_address(index_bytes)
        decoded = decode_address(address)
        self.assertEqual(decoded, index_bytes)


class TestAddressFormat(unittest.TestCase):
    """Test address format properties."""

    def test_prefix(self):
        address = encode_address(b"\x01")
        self.assertTrue(address.startswith("B1:"))

    def test_version(self):
        address = encode_address(b"\x01")
        self.assertIn(":v1:", address)

    def test_empty_marker(self):
        address = encode_address(b"")
        self.assertTrue(address.endswith(":EMPTY"))

    def test_hex_payload(self):
        address = encode_address(b"\xab\xcd")
        payload = address.split(":")[2]
        self.assertEqual(payload, "abcd")

    def test_no_padding(self):
        address = encode_address(b"\x01")
        payload = address.split(":")[2]
        self.assertNotIn("=", payload)


class TestAddressWhitespace(unittest.TestCase):
    """Test strict whitespace rejection."""

    def test_reject_space(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1: 01")

    def test_reject_newline(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:01\n")

    def test_reject_tab(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:\t01")

    def test_reject_carriage_return(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:01\r")

    def test_reject_leading_space(self):
        with self.assertRaises(InvalidAddressError):
            decode_address(" B1:v1:01")

    def test_reject_trailing_space(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:01 ")


class TestAddressInvalid(unittest.TestCase):
    """Test rejection of invalid addresses."""

    def test_invalid_prefix(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B2:v1:01")

    def test_invalid_version(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v2:01")

    def test_missing_parts(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1")

    def test_extra_parts(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:01:extra")

    def test_empty_string(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("")

    def test_empty_payload(self):
        # B1:v1: (empty payload after second colon) must be rejected
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:")

    def test_empty_payload(self):
        # B1:v1: (empty payload after second colon) must be rejected
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:")

    def test_empty_payload(self):
        # B1:v1: (empty payload after second colon) must be rejected
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:")

    def test_empty_payload(self):
        # B1:v1: (empty payload after second colon) must be rejected
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:")

    def test_empty_payload(self):
        # B1:v1: (empty payload after second colon) must be rejected
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:")

    def test_empty_payload(self):
        # B1:v1: (empty payload after second colon) must be rejected
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:")

    def test_none_input(self):
        with self.assertRaises(InvalidAddressError):
            decode_address(None)

    def test_invalid_hex(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:xyz")

    def test_odd_hex_length(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:abc")


class TestAddressCanonicalForm(unittest.TestCase):
    """Test canonical form enforcement (no leading zeros in index bytes)."""

    def test_non_canonical_leading_zero(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:001")

    def test_non_canonical_leading_zero_0001(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:0001")

    def test_non_canonical_leading_zero_00(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:00")

    def test_non_canonical_leading_zero_000000(self):
        with self.assertRaises(InvalidAddressError):
            decode_address("B1:v1:000000")

    def test_non_canonical_encode_leading_zero(self):
        with self.assertRaises(ValueError) as ctx:
            encode_address(b"\x00\x01")
        self.assertIn("minimal", str(ctx.exception))

    def test_non_canonical_encode_leading_zero_single(self):
        with self.assertRaises(ValueError) as ctx:
            encode_address(b"\x00")
        self.assertIn("minimal", str(ctx.exception))

    def test_canonical_single_byte(self):
        address = encode_address(b"\x01")
        self.assertEqual(address, "B1:v1:01")
        self.assertEqual(decode_address(address), b"\x01")

    def test_canonical_multi_byte(self):
        address = encode_address(b"\x01\x02")
        self.assertEqual(address, "B1:v1:0102")
        self.assertEqual(decode_address(address), b"\x01\x02")


class TestIsEmptyAddress(unittest.TestCase):
    """Test is_empty_address helper."""

    def test_empty(self):
        self.assertTrue(is_empty_address("B1:v1:EMPTY"))

    def test_non_empty(self):
        self.assertFalse(is_empty_address("B1:v1:01"))

    def test_invalid(self):
        self.assertFalse(is_empty_address("invalid"))


if __name__ == "__main__":
    unittest.main()
