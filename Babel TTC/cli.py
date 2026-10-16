"""Command line interface for Babel V1."""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from .package import BabelPackage
from .index import payload_directory_for
from .storage import LocalDiskStorage, stream_decompress_verify, PayloadError
from .validator import validate_package, verify_file
from .hash_address import compute_address, assign_coordinates, ADDRESS_PREFIX


def _get_item(index, address):
    if address.startswith(ADDRESS_PREFIX):
        return index.get_by_hash(address[len(ADDRESS_PREFIX):].lower())
    item = index.get_by_path(address)
    return item if item is not None else index.get_by_hash(address.lower())


def cmd_add(args):
    pkg = BabelPackage(args.package); pkg.open()
    payload_dir = payload_directory_for(pkg.index.db_path)
    storage = LocalDiskStorage(str(payload_dir))
    content_hash, compressed_size, _already_existed, _payload_path = storage.store_file_streaming(args.file)
    original_size = os.path.getsize(args.file)
    coords = assign_coordinates(content_hash)
    alias = args.path or args.file
    inserted = pkg.index.add_item_and_alias(content_hash, coords, original_size, compressed_size, alias)
    address = compute_address(content_hash, *coords)
    print(("Arquivo adicionado" if inserted else "Arquivo já indexado") + f": {args.file}")
    print(f"Hash: {content_hash}")
    print(f"Endereço: {address}")
    print(f"Tamanho original: {original_size} bytes")
    print(f"Tamanho comprimido: {compressed_size} bytes")


def _write_validated(index, item, destination):
    content_hash, original_size, compressed_size = item[1], item[7], item[8]
    source = index.payload_path(content_hash)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent))
    try:
        with os.fdopen(fd, "wb") as output:
            stream_decompress_verify(str(source), content_hash, original_size, compressed_size, output)
            output.flush(); os.fsync(output.fileno())
        os.replace(temp_name, destination)
    except Exception:
        try: os.unlink(temp_name)
        except OSError: pass
        raise


def cmd_get(args):
    pkg = BabelPackage(args.package); pkg.open()
    item = _get_item(pkg.index, args.address)
    if item is None:
        print(f"Erro: endereço não encontrado: {args.address}", file=sys.stderr); sys.exit(1)
    try:
        if args.output:
            _write_validated(pkg.index, item, args.output)
            print(f"Arquivo recuperado: {args.output}")
        else:
            with tempfile.TemporaryDirectory(prefix="babel_get_") as tmp:
                staged = Path(tmp) / "verified_output"
                _write_validated(pkg.index, item, staged)
                with staged.open("rb") as source:
                    shutil.copyfileobj(source, sys.stdout.buffer, length=1024 * 1024)
    except (OSError, PayloadError, ValueError) as exc:
        print(f"Erro ao recuperar arquivo: {exc}", file=sys.stderr); sys.exit(1)


def cmd_verify(args):
    pkg = BabelPackage(args.package); pkg.open()
    if args.file:
        valid, error = verify_file(pkg.index, args.file)
        if valid: print(f"OK: {args.file}")
        else: print(f"ERRO: {error}", file=sys.stderr); sys.exit(1)
    else:
        valid, errors = validate_package(pkg.index)
        if valid: print(f"Pacote íntegro: {pkg.index.count_items()} itens, {pkg.index.count_aliases()} aliases")
        else:
            print(f"ERRO: {len(errors)} problemas encontrados:", file=sys.stderr)
            for error in errors: print(f"  - {error}", file=sys.stderr)
            sys.exit(1)


def cmd_export(args):
    pkg = BabelPackage(args.package); pkg.open(); pkg.export(args.output)
    print(f"Pacote exportado: {args.output}")


def cmd_import(args):
    pkg = BabelPackage(args.package)
    if os.path.exists(args.package): pkg.open()
    else: pkg.create()
    count = pkg.import_package(args.input)
    print(f"Importados {count} itens de {args.input}")


def main():
    parser = argparse.ArgumentParser(description="Babel V1 — armazenamento por hash de conteúdo")
    parser.add_argument("--package", "-p", required=True, help="Caminho do banco SQLite do pacote")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="Adiciona arquivo"); add.add_argument("file"); add.add_argument("--path")
    get = commands.add_parser("get", help="Recupera por alias, SHA-256 ou endereço Babel"); get.add_argument("address"); get.add_argument("--output", "-o")
    verify = commands.add_parser("verify", help="Verifica hash e tamanho dos payloads"); verify.add_argument("--file")
    export = commands.add_parser("export", help="Exporta pacote .babel"); export.add_argument("output")
    imp = commands.add_parser("import", help="Importa/mescla pacote .babel no destino"); imp.add_argument("input"); imp.add_argument("--merge", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    {"add": cmd_add, "get": cmd_get, "verify": cmd_verify, "export": cmd_export, "import": cmd_import}[args.command](args)

if __name__ == "__main__":
    main()
