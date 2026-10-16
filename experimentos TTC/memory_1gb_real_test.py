"""Real end-to-end 1 GB memory probe for Babel's existing CLI add path.
Writes no source files under Babel TTC. Run on Windows with Python 3.12+.
"""
import argparse
import ctypes
import datetime as dt
import hashlib
import importlib
import importlib.util
import json
import os
import pathlib
import platform
import random
import sqlite3
import subprocess
import sys
import tempfile
import time

SIZE_BYTES = 1_000_000_000  # 1 GB decimal
CHUNK_BYTES = 1024 * 1024
LIMIT_BYTES = 200_000_000  # suggested 200 MB decimal

class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]

def memory_counters(handle):
    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(counters)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = (ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), ctypes.c_ulong)
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "working_set_bytes": int(counters.WorkingSetSize),
        "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
        "private_bytes": int(counters.PrivateUsage),
        "peak_pagefile_bytes": int(counters.PeakPagefileUsage),
    }

def make_child_script(path):
    code = r'''import ctypes, importlib, importlib.util, json, os, pathlib, sys
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
babel_dir = pathlib.Path(sys.argv[1])
args = sys.argv[2:]
name = "babel_ttc_probe"
spec = importlib.util.spec_from_file_location(name, babel_dir / "__init__.py", submodule_search_locations=[str(babel_dir)])
package = importlib.util.module_from_spec(spec)
sys.modules[name] = package
spec.loader.exec_module(package)
cli = importlib.import_module(name + ".cli")
package_api = importlib.import_module(name + ".package")
package_arg = args[args.index("--package") + 1]
package_api.BabelPackage(package_arg).create()
class PMC(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t), ("PrivateUsage", ctypes.c_size_t)]
p = PMC(); p.cb = ctypes.sizeof(p)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)
kernel32.GetCurrentProcess.argtypes = ()
kernel32.GetCurrentProcess.restype = ctypes.c_void_p
psapi.GetProcessMemoryInfo.argtypes = (ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong)
psapi.GetProcessMemoryInfo.restype = ctypes.c_int
if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(p), p.cb): raise ctypes.WinError(ctypes.get_last_error())
pathlib.Path(os.environ["BABEL_PROBE_BASELINE"]).write_text(json.dumps({"working_set_bytes": int(p.WorkingSetSize), "private_bytes": int(p.PrivateUsage)}), encoding="utf-8")
sys.argv = ["babel-add", *args]
cli.main()
'''
    path.write_text(code, encoding="utf-8")

def mb(n):
    return f"{n / 1_000_000:.2f} MB"

def main():
    if os.name != "nt":
        raise SystemExit("Este medidor usa contadores de memória do Windows.")
    parser = argparse.ArgumentParser()
    parser.add_argument("--babel-dir", required=True)
    parser.add_argument("--experiment-dir", required=True)
    args = parser.parse_args()
    babel_dir = pathlib.Path(args.babel_dir).resolve()
    experiment_dir = pathlib.Path(args.experiment_dir).resolve()
    work_dir = experiment_dir / "_work"
    work_dir.mkdir(parents=True, exist_ok=True)
    result_path = experiment_dir / "memory_1gb_real_result.json"
    report_path = experiment_dir / "memory_1gb_real_report.md"
    if result_path.exists() or report_path.exists():
        raise SystemExit("Resultado já existe; não vou sobrescrever. Remova/renomeie explicitamente para repetir.")
    test_time = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    python_exe = sys.executable
    print(f"Preparando arquivo de {SIZE_BYTES:,} bytes em blocos de {CHUNK_BYTES:,} B...", flush=True)
    with tempfile.TemporaryDirectory(prefix="memory_1gb_real_", dir=work_dir) as td:
        run_dir = pathlib.Path(td)
        source = run_dir / "source_random_1gb.bin"
        db = run_dir / "babel.sqlite"
        helper = run_dir / "invoke_actual_babel_cli.py"
        baseline_path = run_dir / "baseline.json"
        log_path = run_dir / "cli_output.txt"
        h = hashlib.sha256()
        remaining = SIZE_BYTES
        with source.open("wb") as f:
            while remaining:
                block = os.urandom(min(CHUNK_BYTES, remaining))
                f.write(block)
                h.update(block)
                remaining -= len(block)
        input_sha256 = h.hexdigest()
        print(f"Arquivo criado; SHA-256={input_sha256}. Iniciando Babel CLI real...", flush=True)
        make_child_script(helper)
        cmd = [python_exe, str(helper), str(babel_dir), "--package", str(db), "add", str(source), "--path", "test/source_random_1gb.bin"]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["BABEL_PROBE_BASELINE"] = str(baseline_path)
        env["PYTHONIOENCODING"] = "utf-8"
        started = time.perf_counter()
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            process = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, creationflags=creationflags)
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = (ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong)
            kernel32.OpenProcess.restype = ctypes.c_void_p
            kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
            kernel32.CloseHandle.restype = ctypes.c_int
            handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_QUERY_LIMITED_INFORMATION, False, process.pid)
            if not handle:
                handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, process.pid)
            if not handle:
                process.kill()
                raise ctypes.WinError(ctypes.get_last_error())
            sampled_peak_ws = 0
            sampled_peak_private = 0
            last_progress = time.monotonic()
            while process.poll() is None:
                try:
                    m = memory_counters(handle)
                    sampled_peak_ws = max(sampled_peak_ws, m["working_set_bytes"], m["peak_working_set_bytes"])
                    sampled_peak_private = max(sampled_peak_private, m["private_bytes"], m["peak_pagefile_bytes"])
                except OSError:
                    pass
                if time.monotonic() - last_progress >= 15:
                    print(f"Ainda executando; pico observado até agora: WS {mb(sampled_peak_ws)}, commit {mb(sampled_peak_private)}", flush=True)
                    last_progress = time.monotonic()
                time.sleep(0.05)
            exit_code = process.wait()
            elapsed = time.perf_counter() - started
            final_memory = memory_counters(handle)
            kernel32.CloseHandle(handle)
        baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else None
        cli_output = log_path.read_text(encoding="utf-8", errors="replace")
        item = None
        alias_count = None
        if db.exists():
            con = sqlite3.connect(db)
            try:
                item = con.execute("SELECT content_hash, original_size, compressed_size, length(payload) FROM items").fetchone()
                alias_count = con.execute("SELECT COUNT(*) FROM aliases").fetchone()[0]
            finally:
                con.close()
        observed_ws = max(sampled_peak_ws, final_memory["peak_working_set_bytes"])
        observed_commit = max(sampled_peak_private, final_memory["peak_pagefile_bytes"])
        failed_threshold = observed_ws >= LIMIT_BYTES or observed_commit >= LIMIT_BYTES
        verified_add = bool(item and item[0] == input_sha256 and item[1] == SIZE_BYTES and item[2] == item[3] and alias_count == 1)
        passed_process = exit_code == 0 and verified_add
        verdict = "FALHA" if failed_threshold else ("PASSOU" if passed_process else "FALHA DE EXECUÇÃO/INTEGRIDADE")
        result = {
            "timestamp_local": test_time,
            "machine": platform.platform(),
            "python": sys.version,
            "python_executable": python_exe,
            "babel_dir": str(babel_dir),
            "actual_entrypoint": "BabelPackage.create (empty test package) -> Babel TTC/cli.py:main -> cmd_add -> LocalDiskStorage.store_file_streaming -> storage.read -> BabelIndex.add_item",
            "method": "1,000,000,000-byte OS-random input written before the measured child; initialize an empty package using BabelPackage.create; invoke actual CLI add path in isolated process; Windows GetProcessMemoryInfo counters queried during and after child lifetime",
            "input_size_bytes": SIZE_BYTES,
            "input_sha256": input_sha256,
            "input_generator": "os.urandom in 1 MiB blocks; not seeded; SHA-256 recorded",
            "threshold_bytes": LIMIT_BYTES,
            "threshold_basis": "FAIL if peak working set OR peak pagefile/commit reaches 200,000,000 bytes",
            "baseline_memory": baseline,
            "peak_working_set_bytes": observed_ws,
            "peak_pagefile_bytes": observed_commit,
            "duration_seconds": round(elapsed, 3),
            "child_exit_code": exit_code,
            "stored_item_row": item,
            "alias_count": alias_count,
            "add_integrity_verified": verified_add,
            "verdict": verdict,
            "file_add_completed": verified_add,
            "failure_reason": "sqlite3.DataError: string or blob too big" if "string or blob too big" in cli_output else None,
            "failure_stage": "BabelIndex.add_item" if "BabelIndex.add_item" in cli_output else None,
            "peak_working_set_delta_from_baseline_bytes": observed_ws - baseline["working_set_bytes"] if baseline else None,
            "peak_working_set_over_threshold_bytes": observed_ws - LIMIT_BYTES,
            "peak_working_set_multiple_of_threshold": round(observed_ws / LIMIT_BYTES, 6),
            "peak_working_set_to_input_ratio": round(observed_ws / SIZE_BYTES, 6),
            "peak_pagefile_over_threshold_bytes": observed_commit - LIMIT_BYTES,
            "peak_pagefile_multiple_of_threshold": round(observed_commit / LIMIT_BYTES, 6),
            "cli_output": cli_output,
            "source_and_database_cleaned_after_measurement": True,
        }
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    mbtext = lambda x: f"{x:,} bytes ({x/1_000_000:.2f} MB)"
    report = f'''# Teste real de memória — inserção de arquivo de 1 GB na Babel

Data/hora: {test_time}  
Máquina: {platform.platform()}  
Python: {sys.version.split()[0]} (`{python_exe}`)

## Caminho executado

`BabelPackage.create (pacote vazio) → Babel TTC/cli.py:main → cmd_add → LocalDiskStorage.store_file_streaming → storage.read → BabelIndex.add_item`

O teste chama o CLI atual em processo filho isolado. O arquivo de entrada tem 1.000.000.000 bytes (1 GB decimal), foi gravado antes da medição em blocos de 1 MiB com `os.urandom`; SHA-256: `{input_sha256}`. A fonte e o pacote SQLite ficam em diretório temporário em `experimentos TTC/_work` e são removidos após a medição.

## Comando

`& '{python_exe}' 'experimentos TTC/memory_1gb_real_test.py' --babel-dir 'Babel TTC' --experiment-dir 'experimentos TTC'`

## Critério e medição

Critério previamente adotado: **FALHA se o pico do working set ou o pico de pagefile/commit for ≥ 200.000.000 bytes (200 MB decimais)**. Memória do processo medida por `GetProcessMemoryInfo` no Windows, consultada em intervalos de 50 ms e novamente após o processo terminar, enquanto o handle ainda estava aberto. Pico working set: **{mbtext(observed_ws)}**. Pico pagefile/commit: **{mbtext(observed_commit)}**. Baseline após carregar o código: `{json.dumps(baseline, ensure_ascii=False)}`.

## Resultado

**{verdict}**. Exit code: `{exit_code}`; duração: {elapsed:.3f} s. Registro no SQLite confirmado: `{verified_add}`; item (hash, tamanho original, tamanho comprimido, bytes do BLOB): `{item}`; aliases: `{alias_count}`.

## Saída do CLI

```text
{cli_output.rstrip()}
```

## Evidência bruta

Veja `memory_1gb_real_result.json`. O teste antigo `test_08_arquivo_1gb_streaming` não foi usado: ele processa 100 MiB, repete um bloco de `A`, comprime apenas 1 MiB e insere diretamente no índice, portanto não percorre o fluxo real do CLI.
'''
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps({"result": result, "report": str(report_path), "raw": str(result_path)}, indent=2, ensure_ascii=True), flush=True)

if __name__ == "__main__":
    main()
