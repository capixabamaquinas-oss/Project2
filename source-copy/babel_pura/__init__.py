"""Babel Pura H1: self-sufficient address codec.

This package implements the H1 bijection between finite byte sequences
and natural numbers, with a minimal textual envelope.

Final envelope, checksum, and limits will be defined in BP1 after BP-G0B.
"""
from .codec import (
    decode_format,
    decode_h1_integer,
    decode_monolithic_file,
    decode_segmented_reverse,
    decode_segmented_two_pass,
    encode_format,
    encode_h1_integer,
    integer_minimal_bytes,
    offset_for_length,
    subtract_one_reverse,
)
from .address import decode_address, encode_address

__all__ = [
    "decode_address",
    "decode_format",
    "decode_h1_integer",
    "decode_monolithic_file",
    "decode_segmented_reverse",
    "decode_segmented_two_pass",
    "encode_address",
    "encode_format",
    "encode_h1_integer",
    "integer_minimal_bytes",
    "offset_for_length",
    "subtract_one_reverse",
]
