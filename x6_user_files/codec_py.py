"""Babel Pura H1 codec: bijection between finite byte sequences (B*) and N0.

This module implements the pure mathematical core of Babel Pura.
It has no UI, no network, no database, and no checksum.

The bijection E: B* -> N0 is defined as:
    For x with n bytes x_0 ... x_(n-1):
        v(x) = sum(x_i * 256^(n-1-i))
        O_n = (256^n - 1) / 255 = 1 + 256 + ... + 256^(n-1)
        E(x) = O_n + v(x)

For the empty sequence (n=0): O_0 = 0, E = 0.
For n >= 1: O_n in base 256 is exactly n bytes of 0x01.

Decode: given E, find n such that O_n <= E < O_(n+1), then
        v = E - O_n, and x = v.to_bytes(n, "big").
"""
from __future__ import annotations

import base64
from pathlib import Path


def offset_for_length(n: int) -> int:
    """Return O_n = (256^n - 1) / 255."""
    if n < 0:
        raise ValueError("length must be non-negative")
    return ((1 << (8 * n)) - 1) // 255


def encode_h1_integer(data: bytes) -> int:
    """Encode bytes to H1 integer: E(x) = O_n + v(x)."""
    return int.from_bytes(data, "big") + offset_for_length(len(data))


def integer_minimal_bytes(value: int) -> bytes:
    """Serialize integer to minimal big-endian bytes (no leading zeros)."""
    if value < 0:
        raise ValueError("H1 index must be non-negative")
    if value == 0:
        return b""
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def decode_h1_integer(value: int) -> bytes:
    """Decode H1 integer back to bytes."""
    if value < 0:
        raise ValueError("negative H1 index")
    if value == 0:
        return b""
    m = (value.bit_length() + 7) // 8
    n = m if value >= offset_for_length(m) else m - 1
    payload = value - offset_for_length(n)
    if payload < 0 or payload >= (1 << (8 * n)):
        raise ValueError("index outside inferred length interval")
    return payload.to_bytes(n, "big")


def add_one_reverse(block: bytes, carry: int) -> tuple[bytes, int]:
    """Add O_n (n bytes of 0x01) to block, propagating carry leftward."""
    out = bytearray(block)
    for i in range(len(block) - 1, -1, -1):
        total = block[i] + 1 + carry
        out[i] = total & 0xFF
        carry = total >> 8
    return bytes(out), carry


def subtract_one_reverse(block: bytes, borrow: int) -> tuple[bytes, int]:
    """Subtract 1 + borrow from each byte, propagating borrow leftward.

    This is the inverse of add_one_reverse, used for segmented decoding.
    """
    out = bytearray(block)
    for i in range(len(block) - 1, -1, -1):
        total = block[i] - 1 - borrow
        out[i] = total & 0xFF
        borrow = 1 if total < 0 else 0
    return bytes(out), borrow


def _validate_index(index_bytes: bytes) -> None:
    """Validate that index bytes are minimal (no leading zero byte)."""
    if index_bytes and index_bytes[0] == 0:
        raise ValueError("index bytes are not minimal (leading zero)")


# --- Encode file-based ---


def encode_monolithic_file(source: Path, output: Path) -> None:
    """Encode file using monolithic integer conversion (fast, more memory)."""
    data = source.read_bytes()
    value = encode_h1_integer(data)
    output.write_bytes(integer_minimal_bytes(value))


def encode_segmented_reverse(source: Path, output: Path, chunk_size: int) -> None:
    """Encode file using segmented reverse-read (less memory, slower)."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    n = source.stat().st_size
    temp = output.with_name(output.name + ".raw")
    carry = 0
    with source.open("rb") as inp, temp.open("w+b") as out:
        out.truncate(n)
        end = n
        while end > 0:
            start = max(0, end - chunk_size)
            inp.seek(start)
            block = inp.read(end - start)
            transformed, carry = add_one_reverse(block, carry)
            out.seek(start)
            out.write(transformed)
            end = start
    if carry:
        with temp.open("rb") as inp, output.open("wb") as out:
            out.write(bytes([carry]))
            while True:
                block = inp.read(1024 * 1024)
                if not block:
                    break
                out.write(block)
        temp.unlink()
    else:
        temp.replace(output)


def encode_segmented_two_pass(source: Path, output: Path, chunk_size: int) -> None:
    """Encode file using segmented two-pass addition (less memory, slower)."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    n = source.stat().st_size
    blocks: list[tuple[int, int, int]] = []
    carry = 0
    with source.open("rb") as inp:
        end = n
        while end > 0:
            start = max(0, end - chunk_size)
            inp.seek(start)
            block = inp.read(end - start)
            carry_at_right = carry
            for byte in reversed(block):
                carry = 1 if byte + 1 + carry > 0xFF else 0
            blocks.append((start, end, carry_at_right))
            end = start
    total_carry = carry
    with source.open("rb") as inp, output.open("wb") as out:
        if total_carry:
            out.write(bytes([total_carry]))
        for start, end, carry_at_right in reversed(blocks):
            inp.seek(start)
            block = inp.read(end - start)
            transformed, carry_after = add_one_reverse(block, carry_at_right)
            out.write(transformed)
        if out.tell() != n + total_carry:
            raise AssertionError("two-pass output length mismatch")


# --- Decode file-based ---


def decode_monolithic_file(source: Path, output: Path) -> None:
    """Decode file using monolithic integer conversion (fast, more memory)."""
    index_bytes = source.read_bytes()
    if not index_bytes:
        output.write_bytes(b"")
        return
    _validate_index(index_bytes)
    value = int.from_bytes(index_bytes, "big")
    data = decode_h1_integer(value)
    output.write_bytes(data)


def decode_segmented_reverse(source: Path, output: Path, chunk_size: int) -> None:
    """Decode file using segmented reverse-read (less memory, slower).

    Reads the index file from end to start, propagating borrow backward.
    If borrow remains, the carry byte is discarded.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    n = source.stat().st_size
    if n == 0:
        output.write_bytes(b"")
        return
    # Check minimality before processing
    with source.open("rb") as inp:
        first_byte = inp.read(1)
        if first_byte and first_byte[0] == 0:
            raise ValueError("index bytes are not minimal (leading zero)")
    temp = output.with_name(output.name + ".raw")
    try:
        borrow = 0
        with source.open("rb") as inp, temp.open("w+b") as out:
            out.truncate(n)
            end = n
            while end > 0:
                start = max(0, end - chunk_size)
                inp.seek(start)
                block = inp.read(end - start)
                transformed, borrow = subtract_one_reverse(block, borrow)
                out.seek(start)
                out.write(transformed)
                end = start
        if borrow:
            # The index had a carry byte at the front; discard it
            with temp.open("rb") as inp, output.open("wb") as out:
                first = inp.read(1)
                if first:
                    while True:
                        block = inp.read(1024 * 1024)
                        if not block:
                            break
                        out.write(block)
                else:
                    raise ValueError("empty index with borrow")
            temp.unlink()
        else:
            temp.replace(output)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def decode_segmented_two_pass(source: Path, output: Path, chunk_size: int) -> None:
    """Decode file using segmented two-pass subtraction (less memory, slower).

    First pass: compute borrow at each block boundary (reading backward).
    Second pass: apply the subtraction with the correct borrow for each block.
    If borrow remains, the carry byte is discarded.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    n = source.stat().st_size
    if n == 0:
        output.write_bytes(b"")
        return
    # Check minimality before processing
    with source.open("rb") as inp:
        first_byte = inp.read(1)
        if first_byte and first_byte[0] == 0:
            raise ValueError("index bytes are not minimal (leading zero)")
    temp = output.with_name(output.name + ".raw")
    try:
        blocks: list[tuple[int, int, int]] = []
        borrow = 0
        with source.open("rb") as inp:
            end = n
            while end > 0:
                start = max(0, end - chunk_size)
                inp.seek(start)
                block = inp.read(end - start)
                borrow_at_right = borrow
                for byte in reversed(block):
                    borrow = 1 if byte - 1 - borrow < 0 else 0
                blocks.append((start, end, borrow_at_right))
                end = start
        total_borrow = borrow
        with source.open("rb") as inp, temp.open("wb") as out:
            if total_borrow:
                # Discard the carry byte (0x01 or 0xFF)
                first = inp.read(1)
                if not first:
                    raise ValueError("empty index with borrow")
                data_start = 1
            else:
                data_start = 0
                inp.seek(0)
            for start, end, borrow_at_right in reversed(blocks):
                actual_start = start + data_start if start == 0 else start
                inp.seek(actual_start)
                read_size = end - actual_start
                if read_size > 0:
                    block = inp.read(read_size)
                    transformed, borrow_after = subtract_one_reverse(block, borrow_at_right)
                    out.write(transformed)
            expected_size = n - (1 if total_borrow else 0)
            if out.tell() != expected_size:
                raise AssertionError("two-pass decode output length mismatch")
        temp.replace(output)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


# --- Format serialization ---


def encode_format(name: str, raw: bytes) -> bytes:
    """Serialize index bytes to canonical text format."""
    if raw and raw[0] == 0:
        raise ValueError("index bytes are not minimal (leading zero)")
    if name == "hex-lower":
        return raw.hex().encode("ascii")
    if name == "base32-no-padding":
        return base64.b32encode(raw).rstrip(b"=")
    if name == "base64url-no-padding":
        return base64.urlsafe_b64encode(raw).rstrip(b"=")
    raise ValueError(f"unknown format: {name}")


def decode_format(name: str, text: bytes) -> bytes:
    """Deserialize canonical text format back to index bytes."""
    if name == "hex-lower":
        result = bytes.fromhex(text.decode("ascii"))
    elif name == "base32-no-padding":
        result = base64.b32decode(text + b"=" * ((-len(text)) % 8), casefold=False)
    elif name == "base64url-no-padding":
        result = base64.b64decode(text + b"=" * ((-len(text)) % 4), altchars=b"-_", validate=True)
    else:
        raise ValueError(f"unknown format: {name}")
    if result and result[0] == 0:
        raise ValueError("index bytes are not minimal (leading zero)")
    return result
