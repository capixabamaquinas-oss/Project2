import contextlib
import hashlib
import importlib
import importlib.util
import io
import json
import os
import pathlib
import sqlite3
import sys
import tempfile
import zlib

sys.dont_write_bytecode = True
ROOT = pathlib.Path(r"C:\OllamaLimit\Sei lá\Projeto TTC")
BABEL = ROOT / "Babel TTC"
EXP = ROOT / "experimentos TTC"
WORK = EXP / "_work"
WORK.mkdir(parents=True, exist_ok=True)

def load_babel():
    spec = importlib.util.spec_from_file_location("babel", BABEL / "__init__.py", submodule_search_locations=[str(BABEL)])
    pkg = importlib.util.module_from_spec(spec)
    sys.modules["babel"] = pkg
    spec.loader.exec_module(pkg)
    return importlib.import_module("babel.cli"), importlib.import_module("babel.package").BabelPackage, importlib.import_module("babel.index").BabelIndex, importlib.import_module("babel.hash_address").compute_address

cli, BabelPackage, BabelIndex, compute_address = load_babel()

def call(args):
    old = sys.argv
    out, err = io.StringIO(), io.StringIO()
    try:
        sys.argv = ["babel"] + list(map(str, args))
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                cli.main()
                code = 0
            except SystemExit as e:
                code = int(e.code or 0)
        return {"exit_code": code, "stdout": out.getvalue(), "stderr": err.getvalue()}
    finally:
        sys.argv = old

with tempfile.TemporaryDirectory(prefix="babel_stage1_audit_", dir=WORK) as td:
    d = pathlib.Path(td)
    sample = b"Babel real CLI smoke\x00\r\nline two\n"
    source_dir = d / "source_pkg"; source_dir.mkdir()
    src = source_dir / "sample.bin"; src.write_bytes(sample)
    expected_hash = hashlib.sha256(sample).hexdigest()
    db = source_dir / "source.sqlite"
    BabelPackage(str(db)).create()
    add = call(["--package", db, "add", src, "--path", "docs/sample.bin"])
    output = d / "roundtrip.bin"
    get = call(["--package", db, "get", "docs/sample.bin", "--output", output])
    roundtrip_ok = output.exists() and output.read_bytes() == sample
    source_count = BabelIndex(str(db)).count_items()

    bundle = d / "source.babel"
    export = call(["--package", db, "export", bundle])
    imported_dir = d / "imported_pkg"; imported_dir.mkdir()
    imported_db = imported_dir / "imported.sqlite"
    imported = call(["--package", imported_db, "import", bundle])
    imported_count_after_return = BabelIndex(str(imported_db)).count_items()
    imported_out = imported_dir / "imported_get.bin"
    imported_get = call(["--package", imported_db, "get", "docs/sample.bin", "--output", imported_out])
    import_roundtrip_ok = imported_out.exists() and imported_out.read_bytes() == sample

    # Test retrieval integrity: replace the stored BLOB with a valid compressed but wrong payload.
    tampered = zlib.compress(b"tampered-but-valid-zlib")
    con = sqlite3.connect(db)
    con.execute("UPDATE items SET payload=?, compressed_size=? WHERE content_hash=?", (tampered, len(tampered), expected_hash))
    con.commit(); con.close()
    corrupt_out = d / "corrupt_get.bin"
    corrupt_get = call(["--package", db, "get", "docs/sample.bin", "--output", corrupt_out])
    corrupted_get_succeeded = corrupt_get["exit_code"] == 0
    corrupted_get_wrote_wrong_bytes = corrupt_out.exists() and corrupt_out.read_bytes() != sample
    verify_corrupt = call(["--package", db, "verify", "--file", "docs/sample.bin"])

    # Same content inserted at different positions in two indexes.
    a = d / "a.txt"; a.write_bytes(b"same payload for stable address")
    b = d / "b.txt"; b.write_bytes(b"different payload")
    addr_results = []
    for order, label in [([a,b], "a_then_b"), ([b,a], "b_then_a")]:
        order_dir = d / label; order_dir.mkdir()
        odb = order_dir / f"{label}.sqlite"; BabelPackage(str(odb)).create()
        for f in order:
            call(["--package", odb, "add", f, "--path", f.name])
        qcon = sqlite3.connect(odb)
        try:
            row = qcon.execute("SELECT content_hash,hexagon,wall,shelf,volume,page FROM items WHERE content_hash=?", (hashlib.sha256(a.read_bytes()).hexdigest(),)).fetchone()
        finally:
            qcon.close()
        if row is None:
            raise RuntimeError(f"Missing indexed item for address order case {label}: {[(p.name, p.read_bytes()[:20]) for p in order]}")
        addr_results.append(compute_address(*row))
    address_order_independent = addr_results[0] == addr_results[1]

    result = {
        "add_exit": add["exit_code"], "add_output": add["stdout"],
        "get_exit": get["exit_code"], "get_output": get["stdout"],
        "small_file_add_get_byte_exact": roundtrip_ok, "source_item_count": source_count,
        "export_exit": export["exit_code"], "import_exit": imported["exit_code"],
        "import_output": imported["stdout"], "imported_item_count_after_import_returns": imported_count_after_return,
        "imported_get_exit": imported_get["exit_code"], "imported_get_stderr": imported_get["stderr"],
        "new_package_import_get_byte_exact": import_roundtrip_ok,
        "tampered_get_exit": corrupt_get["exit_code"], "tampered_get_succeeded": corrupted_get_succeeded,
        "tampered_get_wrote_wrong_bytes": corrupted_get_wrote_wrong_bytes,
        "verify_corrupt_exit": verify_corrupt["exit_code"], "verify_corrupt_stderr": verify_corrupt["stderr"],
        "address_a_order1": addr_results[0], "address_a_order2": addr_results[1],
        "address_independent_of_insertion_order": address_order_independent,
        "sample_sha256": expected_hash,
    }
    result["checks"] = {
        "basic_add_get": roundtrip_ok and add["exit_code"] == 0 and get["exit_code"] == 0,
        "import_to_new_package": import_roundtrip_ok,
        "get_detects_tampering": corrupt_get["exit_code"] != 0 and not corrupted_get_wrote_wrong_bytes,
        "address_stable_across_order": address_order_independent,
    }
    result["all_functional_checks_pass"] = all(result["checks"].values())
    (EXP / "stage1_babel_integration_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=True))
