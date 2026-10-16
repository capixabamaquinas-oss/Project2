"""Suíte de testes para babel_pura.limits (pré-limite e verificação de tamanho).

Cobre:
- check_address_size_preflight com limite explícito
- compute_output_size_from_index (tamanho exato antes de reconstruir)
- check_output_size com limite explícito
- check_address_and_output com limites explícitos
- Sem limite (None) não restringe nada
"""
from __future__ import annotations

import unittest

from babel_pura.codec import encode_h1_integer, integer_minimal_bytes
from babel_pura.limits import (
    check_address_and_output,
    check_address_size_preflight,
    check_output_size,
    compute_output_size_from_index,
)


class TestNoLimits(unittest.TestCase):
    """Sem limite (None) não restringe nada."""

    def test_no_limit_preflight(self):
        check_address_size_preflight("B1:v1:" + "0" * 100000, None)

    def test_no_limit_output_size(self):
        check_output_size(10**9, None)

    def test_no_limit_combined(self):
        index_bytes = integer_minimal_bytes(encode_h1_integer(b"\x01\x02"))
        check_address_and_output("B1:v1:0102", index_bytes, None, None)


class TestAddressSizePreflight(unittest.TestCase):
    """check_address_size_preflight com limite explícito."""

    def test_under_limit_passes(self):
        check_address_size_preflight("B1:v1:01", 10)

    def test_at_limit_passes(self):
        # Exactly 10 chars is OK
        check_address_size_preflight("B1:v1:012", 10)

    def test_over_limit_rejects(self):
        with self.assertRaises(ValueError) as ctx:
            check_address_size_preflight("B1:v1:0123456789abcdef", 10)
        self.assertIn("MAX_ADDRESS_CHARS", str(ctx.exception))


class TestComputeOutputSize(unittest.TestCase):
    """Exact output size from index bytes."""

    def test_empty(self):
        self.assertEqual(compute_output_size_from_index(b""), 0)

    def test_single_byte(self):
        index_bytes = integer_minimal_bytes(encode_h1_integer(b"\x01"))
        self.assertEqual(compute_output_size_from_index(index_bytes), 1)

    def test_two_bytes(self):
        index_bytes = integer_minimal_bytes(encode_h1_integer(b"\x01\x02"))
        self.assertEqual(compute_output_size_from_index(index_bytes), 2)

    def test_rejects_leading_zero(self):
        with self.assertRaises(ValueError) as ctx:
            compute_output_size_from_index(b"\x00\x01")
        self.assertIn("minimal", str(ctx.exception))


class TestCheckOutputSize(unittest.TestCase):
    """check_output_size com limite explícito."""

    def test_under_limit_passes(self):
        check_output_size(5, 100)

    def test_at_limit_passes(self):
        check_output_size(100, 100)

    def test_over_limit_rejects(self):
        with self.assertRaises(ValueError) as ctx:
            check_output_size(101, 100)
        self.assertIn("MAX_OUTPUT_BYTES", str(ctx.exception))


class TestCheckAddressAndOutput(unittest.TestCase):
    """Combined preflight check with explicit limits."""

    def test_no_limits_passes(self):
        index_bytes = integer_minimal_bytes(encode_h1_integer(b"\x01"))
        check_address_and_output("B1:v1:01", index_bytes, None, None)

    def test_address_limit_rejects(self):
        index_bytes = integer_minimal_bytes(encode_h1_integer(b"\x01"))
        with self.assertRaises(ValueError):
            check_address_and_output("B1:v1:01", index_bytes, 5, None)

    def test_output_limit_rejects(self):
        index_bytes = integer_minimal_bytes(encode_h1_integer(b"\x01\x02"))
        with self.assertRaises(ValueError):
            check_address_and_output("B1:v1:0102", index_bytes, None, 1)

    def test_both_limits_pass(self):
        index_bytes = integer_minimal_bytes(encode_h1_integer(b"\x01"))
        check_address_and_output("B1:v1:01", index_bytes, 100, 1000)


if __name__ == "__main__":
    unittest.main()
