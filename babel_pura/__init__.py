"""Babel Pura H1: self-sufficient address codec.

This package implements the H1 bijection between finite byte sequences
and natural numbers, with a single mandatory textual envelope:

    B1:v1:crc32:<8 hex minúsculos>:<índice em hex minúsculo>

Empty index: B1:v1:EMPTY.

Final decisions from the Diretor (2026-10-15) are baked into this package:
hex-lower index format, mandatory CRC32 checksum, MAX_OUTPUT_BYTES = 16 MiB,
and MAX_ADDRESS_CHARS derived from MAX_OUTPUT_BYTES.
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
from .address import (
    ChecksumError,
    EmptyIndexError,
    InvalidAddressError,
    decode_address,
    encode_address,
    is_empty_address,
)
from .limits import (
    AddressError,
    LimitError,
    MAX_ADDRESS_CHARS,
    MAX_OUTPUT_BYTES,
    check_address_and_output,
    check_address_size_preflight,
    check_output_size,
    compute_output_size_from_index,
)

__all__ = [
    "AddressError",
    "ChecksumError",
    "EmptyIndexError",
    "InvalidAddressError",
    "LimitError",
    "MAX_ADDRESS_CHARS",
    "MAX_OUTPUT_BYTES",
    "check_address_and_output",
    "check_address_size_preflight",
    "check_output_size",
    "compute_output_size_from_index",
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
    "is_empty_address",
    "offset_for_length",
    "subtract_one_reverse",
]
