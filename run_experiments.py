#!/usr/bin/env python3
"""Reproducible, non-product H1 experiments for Babel Pura TTC.

This script implements only experiment fixtures and temporary benchmark code.
It does not create or modify Babel Pura product code.
"""
from __future__ import annotations

import argparse
import base64
import csv
import ctypes
from ctypes import wintypes
import hashlib
import json
import math
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIXTURES = HERE / "fixtures"
FORMATS_DIR = HERE / "address_formats"
PERFORMANCE_DIR = HERE / "performance"
MEMORY_DIR = HERE / "memory"
SCRATCH = HERE / "scratch"
SIZES = [1024, 16384, 262144, 1048576, 4194304]
SEED_BASE = 20261013
CHUNK_BYTES = 65536
REPEATS = 3


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def windows_memory() -> dict[str, int]:
    if os.name != "nt":
        return {"peak_working_set_bytes": 0, "peak_commit_bytes": 0}
    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_mem = psapi.GetProcessMemoryInfo
    get_mem.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
    get_mem.restype = wintypes.BOOL
    get_current = kernel32.GetCurrentProcess
    get_current.restype = wintypes.HANDLE
    if not get_mem(get_current(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
        # PROCESS_MEMORY_COUNTERS.PeakPagefileUsage is the process peak commit charge.
        "peak_commit_bytes": int(counters.PeakPagefileUsage),
    }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def offset_for_length(n: int) -> int:
    # O_n = (256^n - 1) / 255, as specified in the supplied dossier.
    return ((1 << (8 * n)) - 1) // 255


def encode_h1_integer(data: bytes) -> int:
    return int.from_bytes(data, "big") + offset_for_length(len(data))


def integer_minimal_bytes(value: int) -> bytes:
    if value == 0:
        return b""
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def decode_h1_integer(value: int) -> bytes:
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


def encode_format(name: str, raw: bytes) -> bytes:
    if name == "hex-lower":
        return raw.hex().encode("ascii")
    if name == "base32-no-padding":
        return base64.b32encode(raw).rstrip(b"=")
    if name == "base64url-no-padding":
        return base64.urlsafe_b64encode(raw).rstrip(b"=")
    raise ValueError(f"unknown format: {name}")


def decode_format(name: str, text: bytes) -> bytes:
    if name == "hex-lower":
        return bytes.fromhex(text.decode("ascii"))
    if name == "base32-no-padding":
        return base64.b32decode(text + b"=" * ((-len(text)) % 8), casefold=False)
    if name == "base64url-no-padding":
        return base64.b64decode(text + b"=" * ((-len(text)) % 4), altchars=b"-_", validate=True)
    raise ValueError(f"unknown format: {name}")


def memory_row(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    keys = ("peak_working_set_bytes", "peak_commit_bytes")
    row: dict[str, int] = {}
    for key in keys:
        row[f"baseline_{key}"] = before[key]
        row[key] = after[key]
        row[f"delta_{key}"] = max(0, after[key] - before[key])
    return row


def worker_format(args: argparse.Namespace) -> dict[str, Any]:
    before = windows_memory()
    source = Path(args.input)
    started = time.perf_counter()
    data = source.read_bytes()
    index_value = encode_h1_integer(data)
    index_bytes = integer_minimal_bytes(index_value)
    codec_encode_s = time.perf_counter() - started

    encode_times: list[float] = []
    text = b""
    for _ in range(args.repeats):
        t0 = time.perf_counter()
        text = encode_format(args.format, index_bytes)
        encode_times.append(time.perf_counter() - t0)
    decode_times: list[float] = []
    decoded_index = b""
    for _ in range(args.repeats):
        t0 = time.perf_counter()
        decoded_index = decode_format(args.format, text)
        decode_times.append(time.perf_counter() - t0)
    if decoded_index != index_bytes or encode_format(args.format, decoded_index) != text:
        raise AssertionError("format round-trip or canonical re-encoding mismatch")
    decoded_data = decode_h1_integer(int.from_bytes(decoded_index, "big"))
    if decoded_data != data:
        raise AssertionError("H1 round-trip mismatch")
    after = windows_memory()
    result = {
        "kind": "format",
        "format": args.format,
        "input_path": str(source),
        "input_bytes": len(data),
        "input_sha256": sha256_bytes(data),
        "index_bytes": len(index_bytes),
        "index_sha256": sha256_bytes(index_bytes),
        "address_chars_without_envelope": len(text),
        "chars_per_input_byte": (len(text) / len(data)) if data else None,
        "estimated_80_char_lines": math.ceil(len(text) / 80) if text else 0,
        "codec_encode_s_including_input_read": codec_encode_s,
        "format_encode_median_s": statistics.median(encode_times),
        "format_decode_median_s": statistics.median(decode_times),
        "repeats": args.repeats,
        "canonical_reencode_equal": True,
        "round_trip_equal": True,
    }
    result.update(memory_row(before, after))
    return result


def add_one_reverse(block: bytes, carry: int) -> tuple[bytes, int]:
    out = bytearray(block)
    for i in range(len(block) - 1, -1, -1):
        total = block[i] + 1 + carry
        out[i] = total & 0xFF
        carry = total >> 8
    return bytes(out), carry


def encode_monolithic_file(source: Path, output: Path) -> None:
    data = source.read_bytes()
    value = encode_h1_integer(data)
    output.write_bytes(integer_minimal_bytes(value))


def encode_segmented_reverse(source: Path, output: Path, chunk_size: int) -> None:
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
        os.replace(temp, output)


def encode_segmented_two_pass(source: Path, output: Path, chunk_size: int) -> None:
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


def worker_codec(args: argparse.Namespace) -> dict[str, Any]:
    before = windows_memory()
    source, output = Path(args.input), Path(args.output)
    elapsed_values: list[float] = []
    for _ in range(args.repeats):
        started = time.perf_counter()
        if args.method == "monolithic":
            encode_monolithic_file(source, output)
        elif args.method == "segmented-reverse":
            encode_segmented_reverse(source, output, args.chunk_bytes)
        elif args.method == "segmented-two-pass":
            encode_segmented_two_pass(source, output, args.chunk_bytes)
        else:
            raise ValueError(f"unknown method: {args.method}")
        elapsed_values.append(time.perf_counter() - started)
    elapsed = statistics.median(elapsed_values)
    after = windows_memory()
    result = {
        "kind": "codec",
        "method": args.method,
        "input_path": str(source),
        "input_bytes": source.stat().st_size,
        "input_sha256": sha256_file(source),
        "output_path": str(output),
        "output_bytes": output.stat().st_size,
        "output_sha256": sha256_file(output),
        "elapsed_median_s_including_file_io": elapsed,
        "elapsed_runs_s": elapsed_values,
        "repeats": args.repeats,
        "chunk_bytes": args.chunk_bytes if args.method != "monolithic" else None,
    }
    result.update(memory_row(before, after))
    return result


def run_worker(args: list[str], log_lines: list[str]) -> dict[str, Any]:
    command = [sys.executable, "-I", str(Path(__file__).resolve()), *args]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log_lines.append("COMMAND: " + subprocess.list2cmdline(command))
    log_lines.append("EXIT_CODE: " + str(completed.returncode))
    log_lines.append("STDOUT:")
    log_lines.append(completed.stdout.rstrip("\r\n"))
    if completed.stderr:
        log_lines.append("STDERR:")
        log_lines.append(completed.stderr.rstrip("\r\n"))
    if completed.returncode != 0:
        raise RuntimeError(f"worker failed: {completed.args}; see worker output above")
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("worker emitted no JSON output")
    return json.loads(lines[-1])


def extract_docx_text(source: Path, destination: Path) -> dict[str, Any]:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = Document(str(source))
    pieces: list[str] = []
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = Paragraph(child, document).text
            if text:
                pieces.append(text)
        elif tag == "tbl":
            table = Table(child, document)
            for row in table.rows:
                pieces.append(" | ".join(cell.text.replace("\n", " / ") for cell in row.cells))
    data = ("\n".join(pieces) + "\n").encode("utf-8")
    destination.write_bytes(data)
    return {
        "source_path": str(source),
        "source_docx_sha256": sha256_file(source),
        "extraction": "document body paragraphs and table rows in order; cells joined with ' | '; UTF-8 with LF separators",
        "text_path": str(destination),
        "text_bytes": len(data),
        "text_sha256": sha256_bytes(data),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def assert_within_experiment_root(path: Path) -> None:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"refusing to write outside experiment root: {resolved}")


def vector_roundtrips() -> list[dict[str, Any]]:
    edge_cases: list[tuple[str, bytes]] = [
        ("empty", b""),
        ("single-nul", b"\x00"),
        ("single-ff", b"\xff"),
        ("leading-zeros", b"\x00\x00\x00\x01"),
        ("all-byte-values-00-ff", bytes(range(256))),
        ("two-bytes", bytes([0x00, 0xFF])),
        ("length-255", bytes((i * 73 + 19) & 0xFF for i in range(255))),
        ("length-256", bytes((i * 73 + 19) & 0xFF for i in range(256))),
        ("long-carry-run", b"\xff" * 256),
        ("zero-filled-256", b"\x00" * 256),
        ("seeded-random-1024", random.Random(SEED_BASE).randbytes(1024)),
    ]
    results: list[dict[str, Any]] = []
    for name, data in edge_cases:
        value = encode_h1_integer(data)
        index_bytes = integer_minimal_bytes(value)
        decoded = decode_h1_integer(value)
        if decoded != data:
            raise AssertionError(f"codec round-trip failed for {name}")
        formats: dict[str, Any] = {}
        for fmt in ("hex-lower", "base32-no-padding", "base64url-no-padding"):
            text = encode_format(fmt, index_bytes)
            recovered = decode_format(fmt, text)
            if recovered != index_bytes or encode_format(fmt, recovered) != text:
                raise AssertionError(f"canonical text round-trip failed for {name}/{fmt}")
            formats[fmt] = {"address_chars_without_envelope": len(text), "round_trip": "PASS", "canonical_reencode": "PASS"}
        results.append({
            "name": name,
            "input_bytes": len(data),
            "input_hex": data.hex(),
            "input_sha256": sha256_bytes(data),
            "index_minimal_bytes": len(index_bytes),
            "index_hex": index_bytes.hex(),
            "codec_round_trip": "PASS",
            "formats": formats,
        })
    return results


def main_run(args: argparse.Namespace) -> None:
    for path in (FIXTURES, FORMATS_DIR, PERFORMANCE_DIR, MEMORY_DIR, SCRATCH):
        assert_within_experiment_root(path)
        path.mkdir(parents=True, exist_ok=True)
    log_lines: list[str] = []
    x1_rows: list[dict[str, Any]] = []
    x2_rows: list[dict[str, Any]] = []
    fixture_meta: list[dict[str, Any]] = []
    vector_rows = vector_roundtrips()
    (FORMATS_DIR / "edge_vectors.json").write_text(json.dumps(vector_rows, indent=2), encoding="utf-8")

    input_paths: dict[int, Path] = {}
    for i, size in enumerate(SIZES):
        seed = SEED_BASE + i
        data = random.Random(seed).randbytes(size)
        path = FIXTURES / f"seeded_random_{size}.bin"
        path.write_bytes(data)
        input_paths[size] = path
        fixture_meta.append({"path": str(path), "bytes": size, "seed": seed, "sha256": sha256_bytes(data), "generator": "random.Random(seed).randbytes(n)"})

    for size, source in input_paths.items():
        for fmt in ("hex-lower", "base32-no-padding", "base64url-no-padding"):
            result = run_worker(["worker-format", "--format", fmt, "--input", str(source), "--repeats", str(REPEATS)], log_lines)
            result["experiment_id"] = "X1"
            result["input_size_label"] = size
            x1_rows.append(result)
            print(f"X1 PASS size={size} format={fmt} chars={result['address_chars_without_envelope']} encode_s={result['format_encode_median_s']:.6f} decode_s={result['format_decode_median_s']:.6f}")

    for size, source in input_paths.items():
        data = source.read_bytes()
        expected = integer_minimal_bytes(encode_h1_integer(data))
        expected_hash = sha256_bytes(expected)
        for method in ("monolithic", "segmented-reverse", "segmented-two-pass"):
            out = SCRATCH / f"{method}_{size}.bin"
            assert_within_experiment_root(out)
            result = run_worker(["worker-codec", "--method", method, "--input", str(source), "--output", str(out), "--chunk-bytes", str(CHUNK_BYTES), "--repeats", str(REPEATS)], log_lines)
            result["experiment_id"] = "X2/X4"
            result["input_size_label"] = size
            result["expected_output_sha256"] = expected_hash
            result["matches_monolithic_reference"] = result["output_sha256"] == expected_hash
            if not result["matches_monolithic_reference"] or out.read_bytes() != expected:
                raise AssertionError(f"segmented/monolithic output mismatch: size={size} method={method}")
            x2_rows.append(result)
            print(f"X2/X4 PASS size={size} method={method} out={result['output_bytes']} elapsed_median_s={result['elapsed_median_s_including_file_io']:.6f} peak_ws={result['peak_working_set_bytes']} peak_commit={result['peak_commit_bytes']}")
            out.unlink()
            raw = out.with_name(out.name + ".raw")
            if raw.exists():
                raw.unlink()

    x6_text_meta: dict[str, Any] | None = None
    x6_rows: list[dict[str, Any]] = []
    text_path = FIXTURES / "director_dossier_text_utf8.txt"
    source_meta_path = FIXTURES / "director_dossier_text_source.json"
    if args.dossier:
        dossier = Path(args.dossier)
        if dossier.is_file():
            x6_text_meta = extract_docx_text(dossier, text_path)
            source_meta_path.write_text(json.dumps(x6_text_meta, indent=2), encoding="utf-8")
        elif text_path.is_file() and source_meta_path.is_file():
            x6_text_meta = json.loads(source_meta_path.read_text(encoding="utf-8"))
            if sha256_file(text_path) != x6_text_meta["text_sha256"]:
                raise RuntimeError("staged dossier text hash differs from its source metadata")
        else:
            raise FileNotFoundError(f"dossier and staged X6 text are unavailable: {dossier}")
    elif text_path.is_file() and source_meta_path.is_file():
        x6_text_meta = json.loads(source_meta_path.read_text(encoding="utf-8"))
        if sha256_file(text_path) != x6_text_meta["text_sha256"]:
            raise RuntimeError("staged dossier text hash differs from its source metadata")
    if x6_text_meta:
        for fmt in ("hex-lower", "base32-no-padding", "base64url-no-padding"):
            result = run_worker(["worker-format", "--format", fmt, "--input", str(text_path), "--repeats", str(REPEATS)], log_lines)
            result["experiment_id"] = "X6_TEXT_ONLY"
            result["input_size_label"] = "director-dossier-text"
            x6_rows.append(result)
            print(f"X6_TEXT_ONLY PASS format={fmt} input={result['input_bytes']} chars={result['address_chars_without_envelope']}")

    run_log = "\n".join(log_lines) + "\n"
    (HERE / "run.log").write_text(run_log, encoding="utf-8")
    write_csv(FORMATS_DIR / "x1_format_results.csv", x1_rows)
    write_csv(FORMATS_DIR / "x6_text_results.csv", x6_rows)
    write_csv(PERFORMANCE_DIR / "x2_x4_results.csv", x2_rows)
    memory_rows = []
    for row in x1_rows + x6_rows + x2_rows:
        memory_rows.append({key: value for key, value in row.items() if "memory" in key or key in ("experiment_id", "format", "method", "input_bytes", "input_sha256")})
    write_csv(MEMORY_DIR / "process_memory.csv", memory_rows)

    source_files = [Path(__file__).resolve(), FORMATS_DIR / "edge_vectors.json", FORMATS_DIR / "x1_format_results.csv", FORMATS_DIR / "x6_text_results.csv", PERFORMANCE_DIR / "x2_x4_results.csv", MEMORY_DIR / "process_memory.csv", HERE / "run.log"]
    source_files += input_paths.values()
    if x6_text_meta:
        source_files.append(Path(x6_text_meta["text_path"]))
        source_files.append(source_meta_path)
    result = {
        "metadata": {
            "run_date_local": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "runtime": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "os_name": os.name,
            "sizes_bytes": SIZES,
            "chunk_bytes_for_segmented_methods": CHUNK_BYTES,
            "format_timing_repeats": REPEATS,
            "seed_base": SEED_BASE,
            "seed_rule": "seed = 20261013 + size_index; random.Random(seed).randbytes(size)",
            "memory_measurement": "Windows GetProcessMemoryInfo PROCESS_MEMORY_COUNTERS peak working set and peak pagefile usage (commit); per worker process, includes runtime startup",
            "format_scope": "index bytes only; no envelope, prefix, version, checksum, whitespace policy, or empty-index marker",
        },
        "fixtures": fixture_meta,
        "edge_vector_results": vector_rows,
        "X1_format_results": x1_rows,
        "X2_X4_codec_scale_results": x2_rows,
        "X6_text_sample": x6_text_meta,
        "X6_text_format_results": x6_rows,
        "not_run_or_partial": {
            "X3": "Not run: coverage alternatives (index text, reconstructed bytes, both) were approved, but no checksum primitive or bit width is specified in the dossier; choosing one would invent a BP-G0A candidate.",
            "X5": "Not run: MAX_ADDRESS_CHARS and numeric limits remain open (Q7).",
            "X6_code_sample": "Not run: no Director-provided code sample was supplied. The user-provided dossier was used only as a text sample.",
            "X7": "Not run: target platforms are not approved (Q6); measurements here are on the current Windows environment only.",
            "X1_ergonomics": "Character counts and 80-character line estimates are recorded; paste/line-break ergonomics are not measured because envelope whitespace policy remains open (Q5).",
            "X4_limit": "Reports measured data only through the listed 4 MiB input size; no practical threshold or production limit is inferred.",
        },
        "artifact_hashes_sha256": {str(p): sha256_file(p) for p in source_files if p.exists()},
    }
    (HERE / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (HERE / "manifest.json").write_text(json.dumps({
        "command": [sys.executable, "-I", str(Path(__file__).resolve()), "run"] + (["--dossier", args.dossier] if args.dossier else []),
        "runtime": sys.version,
        "platform": platform.platform(),
        "seed_base": SEED_BASE,
        "sizes_bytes": SIZES,
        "chunk_bytes": CHUNK_BYTES,
        "repeats": REPEATS,
        "fixture_hashes": fixture_meta,
        "dossier_text_source": x6_text_meta,
        "artifact_hashes_sha256": result["artifact_hashes_sha256"],
    }, indent=2), encoding="utf-8")

    report = [
        "# Babel Pura H1 experiment report",
        "",
        "Status: measured experiments only; no product code or BP1 choice was made.",
        "",
        "## Scope and setup",
        f"- Runtime: `{sys.version.split()[0]}` at `{sys.executable}`.",
        f"- Platform: `{platform.platform()}`.",
        f"- Input sizes: {', '.join(str(x) for x in SIZES)} bytes; random seeded data, not repeated blocks.",
        f"- Segmented chunk size: {CHUNK_BYTES} bytes. This is an experiment parameter, not a product recommendation.",
        f"- Each format and codec timing is the median of {REPEATS} runs in a fresh worker process; later repetitions may benefit from the operating-system file cache.",
        "- X1 measures the three approved index serializations without an envelope.",
        "- X2/X4 compares integer monolithic, segmented reverse-read, and segmented two-pass addition. Time includes file I/O.",
        "- Process memory records per-worker peak Windows working set and peak commit; each process includes runtime startup.",
        "- The attached temporary DOCX was unavailable on the final rerun; X6 reused the UTF-8 text fixture and source hash recorded in `fixtures/director_dossier_text_source.json`, validating the fixture hash before measuring.",
        "",
        "## Results",
        f"- Edge vectors passed: {len(vector_rows)}; each was round-tripped through H1 and all three serializers.",
        f"- X1 measured format cases: {len(x1_rows)}; CSV: `address_formats/x1_format_results.csv`.",
        f"- X2/X4 measured codec cases: {len(x2_rows)}; CSV: `performance/x2_x4_results.csv`.",
        f"- X6 text sample measured: {'yes' if x6_text_meta else 'no'}; code sample: not supplied.",
        "- See `results.json`, `run.log`, and `manifest.json` for per-case data, raw worker commands/output, seeds, and SHA-256 values.",
        "",
        "## Limits and pending measurements",
        "- X3 remains unmeasured until the checksum primitive and bit width are specified; only coverage scope was approved.",
        "- X5 remains pending numeric input and address limits (Q7).",
        "- X7 remains pending approved target platforms (Q6).",
        "- X1 paste ergonomics remain pending the envelope and whitespace policy (Q5).",
        "- The 4 MiB upper point is a measured range endpoint, not a recommended or maximum product size.",
        "- X6 uses the user-provided dossier as text; no Director-provided code sample was supplied.",
        "- A rerun that tried to reopen the expired temporary attachment failed at X6 after completing X1/X2; its raw output is retained in `rerun-failure-source-missing.txt`. The final run succeeded from the staged, hash-checked X6 text fixture.",
        "- SHA-256 inventory for the delivered files is `SHA256SUMS.txt`.",
        "",
        "## Raw execution command",
        "The exact top-level command and raw console output are recorded in `console-output.txt`; worker subprocess commands and outputs are in `run.log`.",
    ]
    (HERE / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"EDGE_VECTORS PASS count={len(vector_rows)}")
    print(f"SUMMARY X1={len(x1_rows)} X2_X4={len(x2_rows)} X6_TEXT={len(x6_rows)}")
    print("BLOCKED X3=checksum primitive/width; X5=Q7; X7=Q6; X6 code sample unavailable; X1 ergonomics=Q5")
    print("RESULTS_JSON=experiments/results.json")
    print("REPORT=experiments/REPORT.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--dossier")
    wf = sub.add_parser("worker-format")
    wf.add_argument("--format", required=True)
    wf.add_argument("--input", required=True)
    wf.add_argument("--repeats", type=int, default=REPEATS)
    wc = sub.add_parser("worker-codec")
    wc.add_argument("--method", required=True)
    wc.add_argument("--input", required=True)
    wc.add_argument("--output", required=True)
    wc.add_argument("--chunk-bytes", type=int, default=CHUNK_BYTES)
    wc.add_argument("--repeats", type=int, default=REPEATS)
    return parser


if __name__ == "__main__":
    parsed = build_parser().parse_args()
    if parsed.command == "run":
        main_run(parsed)
    elif parsed.command == "worker-format":
        print(json.dumps(worker_format(parsed), separators=(",", ":")))
    elif parsed.command == "worker-codec":
        print(json.dumps(worker_codec(parsed), separators=(",", ":")))
