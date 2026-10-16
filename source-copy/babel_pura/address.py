"""Babel Pura H1 address: minimal envelope around the serialized index.

This module implements a minimal textual envelope for the H1 index.
It includes a prefix, version, and an explicit marker for the empty index.

The envelope is NOT the final BP1 contract. It is a minimal implementation
to validate the core H1 mathematics. The final envelope (with checksum,
whitespace policy, etc.) will be defined in BP1 after BP-G0B.

Envelope format:
    B1:v1:<hex-lower-index>

For the empty index (natural 0, minimal bytes = empty):
    B1:v1:EMPTY

Whitespace policy: strict rejection (no spaces, no newlines).
Canonical policy: index bytes must be minimal (no leading zero byte).
"""
from __future__ import annotations

from .codec import decode_format, encode_format

PREFIX = "B1"
VERSION = "v1"
EMPTY_MARKER = "EMPTY"
FORMAT = "hex-lower"


class AddressError(Exception):
    """Base class for address errors."""


class InvalidAddressError(AddressError):
    """Raised when the address text is malformed."""


class EmptyIndexError(AddressError):
    """Raised when decoding an empty index (natural 0)."""


def encode_address(index_bytes: bytes) -> str:
    """Encode index bytes to textual address with minimal envelope.

    Raises ValueError if index_bytes is not minimal (has leading zero).
    """
    if index_bytes and index_bytes[0] == 0:
        raise ValueError("index bytes are not minimal (leading zero)")
    if not index_bytes:
        return f"{PREFIX}:{VERSION}:{EMPTY_MARKER}"
    text = encode_format(FORMAT, index_bytes).decode("ascii")
    return f"{PREFIX}:{VERSION}:{text}"


def decode_address(address: str) -> bytes:
    """Decode textual address back to index bytes.

    Raises:
        InvalidAddressError: if the address is malformed.
        EmptyIndexError: if the address represents the empty index.
    """
    if not isinstance(address, str):
        raise InvalidAddressError("address must be a string")

    # Strict whitespace policy: reject any whitespace
    if any(c.isspace() for c in address):
        raise InvalidAddressError("address contains whitespace")

    parts = address.split(":")
    if len(parts) != 3:
        raise InvalidAddressError(f"expected 3 colon-separated parts, got {len(parts)}")

    prefix, version, payload = parts

    if prefix != PREFIX:
        raise InvalidAddressError(f"unknown prefix: {prefix!r}")
    if version != VERSION:
        raise InvalidAddressError(f"unknown version: {version!r}")

    if payload == EMPTY_MARKER:
        raise EmptyIndexError("address represents the empty index")

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

    return index_bytes


def is_empty_address(address: str) -> bool:
    """Check if the address represents the empty index."""
    try:
        decode_address(address)
        return False
    except EmptyIndexError:
        return True
    except InvalidAddressError:
        return False
