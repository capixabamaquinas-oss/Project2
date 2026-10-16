# Babel Pura H1 experiment report

Status: measured experiments only; no product code or BP1 choice was made.

## Scope and setup
- Runtime: `3.12.14` at `C:\Users\User PC\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.
- Platform: `Windows-10-10.0.19045-SP0`.
- Input sizes: 1024, 16384, 262144, 1048576, 4194304 bytes; random seeded data, not repeated blocks.
- Segmented chunk size: 65536 bytes. This is an experiment parameter, not a product recommendation.
- Each format and codec timing is the median of 3 runs in a fresh worker process; later repetitions may benefit from the operating-system file cache.
- X1 measures the three approved index serializations without an envelope.
- X2/X4 compares integer monolithic, segmented reverse-read, and segmented two-pass addition. Time includes file I/O.
- Process memory records per-worker peak Windows working set and peak commit; each process includes runtime startup.
- The attached temporary DOCX was unavailable on the final rerun; X6 reused the UTF-8 text fixture and source hash recorded in `fixtures/director_dossier_text_source.json`, validating the fixture hash before measuring.

## Results
- Edge vectors passed: 11; each was round-tripped through H1 and all three serializers.
- X1 measured format cases: 15; CSV: `address_formats/x1_format_results.csv`.
- X2/X4 measured codec cases: 15; CSV: `performance/x2_x4_results.csv`.
- X6 text sample measured: yes; code sample: not supplied.
- See `results.json`, `run.log`, and `manifest.json` for per-case data, raw worker commands/output, seeds, and SHA-256 values.

## Limits and pending measurements
- X3 remains unmeasured until the checksum primitive and bit width are specified; only coverage scope was approved.
- X5 remains pending numeric input and address limits (Q7).
- X7 remains pending approved target platforms (Q6).
- X1 paste ergonomics remain pending the envelope and whitespace policy (Q5).
- The 4 MiB upper point is a measured range endpoint, not a recommended or maximum product size.
- X6 uses the user-provided dossier as text; no Director-provided code sample was supplied.
- A rerun that tried to reopen the expired temporary attachment failed at X6 after completing X1/X2; its raw output is retained in `rerun-failure-source-missing.txt`. The final run succeeded from the staged, hash-checked X6 text fixture.
- SHA-256 inventory for the delivered files is `SHA256SUMS.txt`.

## Raw execution command
The exact top-level command and raw console output are recorded in `console-output.txt`; worker subprocess commands and outputs are in `run.log`.
