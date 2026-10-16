"""Babel Pura H1 address: textual envelope around the serialized index.

This module implements the single, mandatory textual envelope for the H1
index, as decided by the Diretor on 2026-10-15:

    Encode (every non-empty index):
        B1:v1:crc32:<8 hex minúsculos>:<índice em hex minúsculo>

    Empty index (natural 0, minimal bytes = empty):
        B1:v1:EMPTY

CRC32 is calculated over the minimal index bytes (not over the text).
There is exactly one address per index: uniqueness is guaranteed.

Whitespace policy: strict rejection (no spaces, no newlines).
Canonical policy: index bytes must be minimal (no leading zero byte);
checksum hex digest must be lowercase (uppercase/mixed-case is rejected).

Errors:
- InvalidAddressError: malformed structure, wrong prefix/version, wrong
  checksum format (not exactly 8 lowercase hex chars), bad hex payload,
  non-canonical re-encoding, leading-zero index bytes, empty payload.
- ChecksumError (subclass of InvalidAddressError): checksum well-formed
  but different from the value calculated over the index bytes.
- EmptyIndexError: address represents the empty index (B1:v1:EMPTY).
"""
from __future__ import annotations

import binascii

from .codec import decode_format, encode_format
from .limits import (
    MAX_ADDRESS_CHARS,
    MAX_OUTPUT_BYTES,
    compute_output_size_from_index,
    LimitError,
    AddressError,
)

PREFIX = "B1"
VERSION = "v1"
EMPTY_MARKER = "EMPTY"
FORMAT = "hex-lower"
CHECKSUM_ALGO = "crc32"
CHECKSUM_HEX_LEN = 8  # CRC32 = 4 bytes = 8 hex chars


class InvalidAddressError(AddressError):
    """Raised when the address text is malformed."""


class EmptyIndexError(AddressError):
    """Raised when decoding an empty index (natural 0)."""


class ChecksumError(InvalidAddressError):
    """Raised when checksum is well-formed but differs from the calculated
    value over the index bytes.

    Inherits InvalidAddressError so callers that catch InvalidAddressError
    also catch checksum failures.
    """


def _compute_crc32(data: bytes) -> str:
    """Compute CRC32 checksum of data bytes.

    Returns lowercase hex string, 8 characters.
    """
    return f"{binascii.crc32(data) & 0xFFFFFFFF:08x}"


def _is_valid_checksum_hex(text: str) -> bool:
    """Return True if text is exactly 8 lowercase hex characters."""
    if len(text) != CHECKSUM_HEX_LEN:
        return False
    if text != text.lower():
        return False
    return all(c in "0123456789abcdef" for c in text)


def encode_address(index_bytes: bytes) -> str:
    """Encode index bytes to textual address with mandatory CRC32 checksum.

    Envelope format:
        B1:v1:crc32:<8 hex minúsculos>:<índice em hex minúsculo>

    For the empty index (natural 0), returns B1:v1:EMPTY (no checksum).

    Raises:
        ValueError: if index_bytes is not minimal (has leading zero).
        LimitError: if the encoded address would exceed MAX_OUTPUT_BYTES.
    """
    if index_bytes and index_bytes[0] == 0:
        raise ValueError("index bytes are not minimal (leading zero)")
    if not index_bytes:
        return f"{PREFIX}:{VERSION}:{EMPTY_MARKER}"
    out_size = compute_output_size_from_index(index_bytes)
    if out_size > MAX_OUTPUT_BYTES:
        raise LimitError(
            f"output size exceeds MAX_OUTPUT_BYTES: {out_size} > {MAX_OUTPUT_BYTES}"
        )
    index_text = encode_format(FORMAT, index_bytes).decode("ascii")
    checksum_hex = _compute_crc32(index_bytes)
    return f"{PREFIX}:{VERSION}:{CHECKSUM_ALGO}:{checksum_hex}:{index_text}"


def decode_address(
    address: str,
    max_address_chars: int = MAX_ADDRESS_CHARS,
    max_output_bytes: int = MAX_OUTPUT_BYTES,
) -> bytes:
    """Decode textual address back to index bytes.

    Accepts only:
        B1:v1:EMPTY
        B1:v1:crc32:<8 hex minúsculos>:<índice em hex minúsculo>

    Order of checks:
    (a) address size preflight (len > max_address_chars) before any scan,
    (b) count ":" with address.count(":") before split (2 for EMPTY,
        4 for checksummed format) to avoid building a huge list from an
        address full of colons,
    (c) after obtaining index bytes, check exact output size with
        compute_output_size_from_index before any reconstruction.

    Raises:
        LimitError: if address exceeds max_address_chars or output size
            exceeds max_output_bytes.
        InvalidAddressError: if the address is malformed.
        EmptyIndexError: if the address represents the empty index.
        ChecksumError: if checksum is well-formed but differs from the
            calculated value (subclass of InvalidAddressError).
    """
    if not isinstance(address, str):
        raise InvalidAddressError("address must be a string")

    # (a) Preflight: reject oversized address before any scan or split.
    if len(address) > max_address_chars:
        raise LimitError(
            f"address exceeds MAX_ADDRESS_CHARS: {len(address)} > {max_address_chars}"
        )

    # Strict whitespace policy: reject any whitespace
    if any(c.isspace() for c in address):
        raise InvalidAddressError("address contains whitespace")

    # (b) Count colons before split, to avoid a huge list from malicious input.
    colon_count = address.count(":")
    if colon_count == 2:
        # Must be B1:v1:EMPTY
        parts = address.split(":")
        if parts[0] != PREFIX:
            raise InvalidAddressError(f"unknown prefix: {parts[0]!r}")
        if parts[1] != VERSION:
            raise InvalidAddressError(f"unknown version: {parts[1]!r}")
        if parts[2] != EMPTY_MARKER:
            raise InvalidAddressError(f"unexpected payload: {parts[2]!r}")
        raise EmptyIndexError("address represents the empty index")

    if colon_count != 4:
        raise InvalidAddressError(
            f"expected 4 colon separators, got {colon_count}"
        )

    parts = address.split(":")
    prefix, version, checksum_algo, checksum_hex, payload = parts

    if prefix != PREFIX:
        raise InvalidAddressError(f"unknown prefix: {prefix!r}")
    if version != VERSION:
        raise InvalidAddressError(f"unknown version: {version!r}")
    if checksum_algo != CHECKSUM_ALGO:
        raise InvalidAddressError(
            f"unknown checksum algorithm: {checksum_algo!r}"
        )

    if not _is_valid_checksum_hex(checksum_hex):
        raise InvalidAddressError(
            f"checksum must be exactly {CHECKSUM_HEX_LEN} lowercase hex chars"
        )

    if not payload:
        raise InvalidAddressError("payload is empty")

    try:
        index_bytes = decode_format(FORMAT, payload.encode("ascii"))
    except Exception as e:
        raise InvalidAddressError(f"invalid index payload: {e}") from e

    # Verify canonical re-encoding
    if encode_format(FORMAT, index_bytes).decode("ascii") != payload:
        raise InvalidAddressError("index payload is not canonical")

    # Verify minimality (no leading zero byte)
    if index_bytes and index_bytes[0] == 0:
        raise InvalidAddressError("index bytes are not minimal (leading zero)")

    # (c) Check exact output size before any reconstruction.
    out_size = compute_output_size_from_index(index_bytes)
    if out_size > max_output_bytes:
        raise LimitError(
            f"output size exceeds MAX_OUTPUT_BYTES: {out_size} > {max_output_bytes}"
        )

    # Verify checksum over the reconstructed index bytes
    actual_checksum = _compute_crc32(index_bytes)
    if actual_checksum != checksum_hex:
        raise ChecksumError(
            f"checksum mismatch: expected {checksum_hex}, got {actual_checksum}"
        )

    return index_bytes


def is_empty_address(address: str) -> bool:
    """Check if the address represents the empty index.

    Returns True only for B1:v1:EMPTY. Returns False (no exception) for
    any other input, including invalid addresses and checksum errors.
    """
    try:
        decode_address(address)
        return False
    except EmptyIndexError:
        return True
    except AddressError:
        return False
