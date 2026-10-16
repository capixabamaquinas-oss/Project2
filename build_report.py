import csv,json
from pathlib import Path
run=Path(__file__).resolve().parent
def read(n):
    with (run/n).open(encoding="utf-8",newline="") as f: return list(csv.DictReader(f))
x2=read("x2_summary.csv"); x3=read("x3_summary.csv"); rep2=read("x2_repetitions.csv"); rep3=read("x3_repetitions.csv")
m=json.loads((run/"fixture_manifest.json").read_text(encoding="utf-8"))
def f(v): return f"{float(v):.2f}"
def chunk(v):
    if not v: return "—"
    n=int(v)
    return f"{n//1024} KiB" if n<1024*1024 else f"{n//(1024*1024)} MiB"
case={"random":"aleatório","all_ff":"todos FF","all_00":"todos 00"}
op={"encode":"encode","decode":"decode","roundtrip":"caminho completo"}
lines=[
"# X2 (16 MiB) e X3 (dispersão)",
"",
"## Escopo e execução",
"",
"Executados somente X2 e X3 na cópia descartável source-copy/. Nenhum arquivo do pacote foi editado. Os hashes do pacote original foram conferidos antes e depois; a cópia usada nas medições tem os mesmos hashes.",
"",
"Ambiente: Python 3.12.3 (64-bit), Windows 10.0.19045, Intel(R) Core(TM) i3-10100 CPU @ 3.60GHz, 4 núcleos físicos e 8 processadores lógicos. A memória é PeakWorkingSetSize real de cada processo Windows, obtido por GetProcessMemoryInfo; os números abaixo usam MiB (1 MiB = 1.048.576 bytes). Cada observação foi executada por uma invocação nova de Python. Quartis e IQR usam interpolação inclusiva (Q3 − Q1).",
"",
"X2 final: 315 observações, 45 combinações, 7 repetições por combinação. O caminho completo foi refeito em 21 processos para parar o cronômetro antes da validação SHA-256. X3: 60 observações, 4 métricas, 15 repetições por métrica. A ordem de execução foi embaralhada com semente fixa. PIDs repetidos podem aparecer no log porque o Windows reutiliza identificadores após subprocessos encerrados; cada observação tem uma invocação de processo registrada.",
"",
"A revisão medida usa o endereço atual obrigatório B1:v1:crc32:<checksum>:<hex>. No X2, o caminho completo foi medido com esse formato e os limites atuais de endereço/saída. O CRC32 é requisito da revisão atual do pacote e foi usado apenas como parâmetro da medição.",
"",
"## SHA-256 do pacote medido",
"",
"| Arquivo | SHA-256 |",
"|---|---|"
]
for line in (run/"00_measured_package_sha256.txt").read_text(encoding="utf-8-sig").splitlines():
    if "  original/" in line:
        sha,path=line.split("  ",1)
        lines.append(f"| {path.replace('original/','')} | {sha} |")
lines += [
"",
"Os hashes acima são da revisão presente no início das medições. O codec.py manteve o mesmo hash da rodada anterior. A fonte original foi novamente verificada ao final e confere com este inventário.",
"",
"## Dados usados",
"",
"| Caso | Tamanho | SHA-256 | Índice H1 (bytes) | SHA-256 do índice |",
"|---|---:|---|---:|---|"
]
for k,v in m["cases"].items():
    lines.append(f"| {case[k]} | {v['data_bytes']:,} | {v['data_sha256']} | {v['index_bytes']:,} | {v['index_sha256']} |".replace(","," "))
lines += [
"",
f"X3 usou 4 MiB aleatórios (semente {m['x3']['seed']}), SHA-256 {m['x3']['data_sha256']}. O texto base64url sem padding teve {m['x3']['base64url_bytes']:,} bytes; o hex minúsculo teve {m['x3']['hex_bytes']:,} bytes.".replace(","," "),
"",
"## X2 — 16 MiB",
"",
"Os valores de tempo e pico de Working Set são apresentados como mínimo / mediana / IQR. Encode/decode usam as funções de arquivo do codec.py; o caminho completo mede bytes em memória → índice H1 → endereço hex com CRC32 → parse/verificação → bytes. Todos os resultados passaram na comparação SHA-256 com o original.",
"",
"| Caso | Operação | Estratégia | Chunk | Checksum | Tempo (ms) min / med / IQR | Peak WS (MiB) min / med / IQR | n |",
"|---|---|---|---:|---|---:|---:|---:|"
]
for r in x2:
    lines.append(f"| {case[r['case']]} | {op[r['operation']]} | {r['strategy']} | {chunk(r['chunk_size'])} | {r['checksum'] or '—'} | {f(r['time_min_ms'])} / {f(r['time_median_ms'])} / {f(r['time_iqr_ms'])} | {f(r['peak_ws_min_mib'])} / {f(r['peak_ws_median_mib'])} / {f(r['peak_ws_iqr_mib'])} | {r['repetitions']} |")
lines += [
"",
f"Verificação X2: {len(rep2)} observações finais; {len(x2)} grupos; todos os SHA-256 conferem. O caso todos FF gerou índice de {m['cases']['all_ff']['index_bytes']:,} bytes.".replace(","," "),
"",
"## X3 — CRC32 e linha de base, 4 MiB",
"",
"| Medição | Bytes processados | CRC32 observado | Tempo (ms) min / med / IQR | Peak WS (MiB) min / med / IQR | n |",
"|---|---:|---|---:|---:|---:|"
]
for r in x3:
    metric=r["metric"]
    size=m["x3"]["data_bytes"] if metric in ("bytes","baseline") else (m["x3"]["base64url_bytes"] if metric=="base64url_text" else m["x3"]["hex_bytes"])
    if metric=="bytes": crc=f"0x{m['x3']['crc32_bytes']:08x}"
    elif metric=="base64url_text": crc=f"0x{m['x3']['crc32_base64url']:08x}"
    elif metric=="hex_text": crc=f"0x{m['x3']['crc32_hex']:08x}"
    else: crc="—"
    name={"bytes":"CRC32 sobre bytes","base64url_text":"CRC32 sobre texto base64url","hex_text":"CRC32 sobre texto hex","baseline":"linha de base H1 + bytes mínimos + hex"}[metric]
    lines.append(f"| {name} | {size:,} | {crc} | {f(r['time_min_ms'])} / {f(r['time_median_ms'])} / {f(r['time_iqr_ms'])} | {f(r['peak_ws_min_mib'])} / {f(r['peak_ws_median_mib'])} / {f(r['peak_ws_iqr_mib'])} | {r['repetitions']} |".replace(","," "))
base=next(r for r in x3 if r["metric"]=="baseline")
lines += [
"",
f"Na linha de base, a mediana foi {f(base['time_median_ms'])} ms. O índice resultante teve {m['x3']['index_bytes']:,} bytes e {m['x3']['index_bytes']*2:,} caracteres hex. A leitura do arquivo de entrada ocorreu antes do cronômetro.".replace(","," "),
"",
"## Anomalias da X3 anterior",
"",
"Na rodada anterior, com apenas três repetições, BLAKE2s-128 levou 14,6981 ms sobre bytes e 14,2142 ms sobre texto base64url, embora o texto fosse maior (5.592.406 contra 4.194.304 bytes). Essa diferença não identifica uma causa: a amostra era pequena e as medições não isolaram efeitos de escalonamento do sistema, cache e variação entre execuções. Ela não demonstra que o texto seja intrinsecamente mais rápido.",
"",
"O CRC32 ambos mediu 7,0379 ms, contra 2,2667 + 3,2045 = 5,4712 ms para a soma das medianas separadas. A mediana de uma medição combinada não precisa ser a soma das medianas de duas amostras separadas; as execuções também diferem em estado de cache e variação de temporização. Com três repetições e sem desenho pareado, os dados anteriores não permitem atribuir os 1,5667 ms adicionais a uma causa específica.",
"",
"## Comandos e saídas brutas",
"",
"| Artefato | Conteúdo |",
"|---|---|",
"| 00_baseline_sha_system_raw.txt | hash inicial observado e primeira tentativa de consulta do ambiente |",
"| 00_measured_package_sha256.txt | hashes dos arquivos .py medidos e da cópia descartável |",
"| 00_environment_python_raw.txt | Python, Windows e identificação de CPU via Python/registro |",
"| 00_cpu_topology_raw.txt | consulta de núcleos físicos/lógicos pela API do Windows |",
"| 01_prepare_raw.txt | preparação e hashes dos dados de entrada/índices |",
"| 02_x2_worker_raw.txt | saída bruta dos 315 workers X2 da execução inicial; os 21 tempos de caminho completo foram substituídos pela rechecagem abaixo |",
"| 02_x2_roundtrip_recheck_worker_raw.txt | saída bruta autoritativa dos 21 caminhos completos X2, com SHA fora do cronômetro |",
"| 02_x2_aggregate_raw.txt | agregação X2 a partir dos workers originais |",
"| 02_x2_recheck_raw.txt | rechecagem do caminho completo e reconstrução dos CSVs finais X2 |",
"| 03_x3_worker_raw.txt | saída bruta dos 60 workers X3 |",
"| 02_x2_orchestrator_raw.txt | saída do primeiro agregador; erro apenas no campo auxiliar suite do CSV, corrigido sem repetir medições válidas |",
"",
"Arquivos tabulares: x2_repetitions.csv (315 observações finais), x2_summary.csv (45 grupos), x2_full_path_recheck.csv (21 medições completas), x3_repetitions.csv (60 observações) e x3_summary.csv (4 grupos).",
"",
"X5 não foi executado nesta rodada, conforme a instrução de aguardar a entrega do OpenCode.",
"",
"## Integridade do pacote",
"",
"source-copy/ contém somente os arquivos Python medidos. Os SHA-256 do original foram iguais antes e depois; nenhum arquivo do pacote foi modificado. As saídas binárias temporárias de encode/decode foram removidas após a validação SHA-256. Os dados de entrada e seus hashes permanecem em work/fixtures/."
]
report="\n".join(lines)+"\n"
p=run/"REPORT.md"; p.write_text(report,encoding="utf-8",newline="")
print(f"report_lines={len(lines)}")
print(f"x2_rows={len(x2)} x2_repetitions={len(rep2)} x3_rows={len(x3)} x3_repetitions={len(rep3)}")
print(f"report_sha256={__import__('hashlib').sha256(p.read_bytes()).hexdigest()}")
