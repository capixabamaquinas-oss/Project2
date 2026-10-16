# X2 (16 MiB) e X3 (dispersão)

## Escopo e execução

Executados somente X2 e X3 na cópia descartável source-copy/. Nenhum arquivo do pacote foi editado. Os hashes do pacote original foram conferidos antes e depois; a cópia usada nas medições tem os mesmos hashes.

Ambiente: Python 3.12.3 (64-bit), Windows 10.0.19045, Intel(R) Core(TM) i3-10100 CPU @ 3.60GHz, 4 núcleos físicos e 8 processadores lógicos. A memória é PeakWorkingSetSize real de cada processo Windows, obtido por GetProcessMemoryInfo; os números abaixo usam MiB (1 MiB = 1.048.576 bytes). Cada observação foi executada por uma invocação nova de Python. Quartis e IQR usam interpolação inclusiva (Q3 − Q1).

X2 final: 315 observações, 45 combinações, 7 repetições por combinação. O caminho completo foi refeito em 21 processos para parar o cronômetro antes da validação SHA-256. X3: 60 observações, 4 métricas, 15 repetições por métrica. A ordem de execução foi embaralhada com semente fixa. PIDs repetidos podem aparecer no log porque o Windows reutiliza identificadores após subprocessos encerrados; cada observação tem uma invocação de processo registrada.

A revisão medida usa o endereço atual obrigatório B1:v1:crc32:<checksum>:<hex>. No X2, o caminho completo foi medido com esse formato e os limites atuais de endereço/saída. O CRC32 é requisito da revisão atual do pacote e foi usado apenas como parâmetro da medição.

## SHA-256 do pacote medido

| Arquivo | SHA-256 |
|---|---|
| babel_pura/__init__.py | 72179c81b57ff7c7e1f74cbd0043f9ebd0d82be4d536b9151c020000195eaeca |
| babel_pura/address.py | 23c3bdd3f21dc8d25e026fa79a820077e28fc5ef450322540ea6550388e46924 |
| babel_pura/codec.py | 6a72eb64d420570499d9cafe29ea6f39e0a90687686006d6404e7d0bfd2d72b6 |
| babel_pura/limits.py | 553c887beabd5768bb97b3b1c7b8f3fb41e6c7346d129cce82311e1648080c4f |

Os hashes acima são da revisão presente no início das medições. O codec.py manteve o mesmo hash da rodada anterior. A fonte original foi novamente verificada ao final e confere com este inventário.

## Dados usados

| Caso | Tamanho | SHA-256 | Índice H1 (bytes) | SHA-256 do índice |
|---|---:|---|---:|---|
| aleatório | 16 777 216 | 58b9c3b857ddaacdf9d98e6119056cc2d80eb3dd2ac657de8e1db006bea12412 | 16 777 216 | d8f42a967db3f996bbc596956094771451ad34d08cf506fb923d386faeef4815 |
| todos FF | 16 777 216 | dffab0dd410657cb30c7b2fd7f2586a4792e8472e58882b3532581f8111a646d | 16 777 217 | 72506f2fc87d9d43109df9fa9696c36755040fcbd93adfab76123239025bac0e |
| todos 00 | 16 777 216 | 080acf35a507ac9849cfcba47dc2ad83e01b75663a516279c8b9d243b719643e | 16 777 216 | b70a752bfdf8d3446d286dc7562cc34093f611be1c88867c062b35b442b0bd04 |

X3 usou 4 MiB aleatórios (semente 20261016)  SHA-256 37f51b2a00b832b7bafa8494918b68ac4048630ebed6df6ec2a4ac6bc61993e4. O texto base64url sem padding teve 5 592 406 bytes; o hex minúsculo teve 8 388 608 bytes.

## X2 — 16 MiB

Os valores de tempo e pico de Working Set são apresentados como mínimo / mediana / IQR. Encode/decode usam as funções de arquivo do codec.py; o caminho completo mede bytes em memória → índice H1 → endereço hex com CRC32 → parse/verificação → bytes. Todos os resultados passaram na comparação SHA-256 com o original.

| Caso | Operação | Estratégia | Chunk | Checksum | Tempo (ms) min / med / IQR | Peak WS (MiB) min / med / IQR | n |
|---|---|---|---:|---|---:|---:|---:|
| todos 00 | decode | monolithic | — | — | 165.82 / 172.77 / 13.55 | 84.23 / 84.31 / 0.18 | 7 |
| todos 00 | decode | reverse | 64 KiB | — | 1717.03 / 1764.01 / 127.15 | 17.37 / 17.57 / 0.17 | 7 |
| todos 00 | decode | reverse | 1 MiB | — | 1721.66 / 1765.68 / 134.00 | 21.05 / 21.15 / 0.06 | 7 |
| todos 00 | decode | reverse | 4 MiB | — | 1706.31 / 1784.08 / 89.23 | 33.05 / 33.26 / 0.08 | 7 |
| todos 00 | decode | two_pass | 64 KiB | — | 2442.89 / 2480.77 / 47.29 | 17.30 / 17.46 / 0.14 | 7 |
| todos 00 | decode | two_pass | 1 MiB | — | 2419.24 / 2461.07 / 52.06 | 21.05 / 21.16 / 0.14 | 7 |
| todos 00 | decode | two_pass | 4 MiB | — | 2432.87 / 2514.29 / 107.75 | 33.03 / 33.13 / 0.18 | 7 |
| todos 00 | encode | monolithic | — | — | 107.26 / 116.54 / 6.39 | 67.19 / 67.26 / 0.14 | 7 |
| todos 00 | encode | reverse | 64 KiB | — | 1761.62 / 1781.31 / 29.17 | 17.27 / 17.39 / 0.14 | 7 |
| todos 00 | encode | reverse | 1 MiB | — | 1751.41 / 1786.81 / 51.71 | 20.96 / 21.10 / 0.21 | 7 |
| todos 00 | encode | reverse | 4 MiB | — | 1753.19 / 1782.30 / 54.03 | 32.96 / 33.16 / 0.18 | 7 |
| todos 00 | encode | two_pass | 64 KiB | — | 2445.39 / 2525.69 / 77.17 | 17.32 / 17.36 / 0.11 | 7 |
| todos 00 | encode | two_pass | 1 MiB | — | 2398.61 / 2490.82 / 63.64 | 21.05 / 21.24 / 0.11 | 7 |
| todos 00 | encode | two_pass | 4 MiB | — | 2509.25 / 2539.70 / 20.92 | 33.01 / 33.21 / 0.16 | 7 |
| todos 00 | caminho completo | full_address | — | crc32 | 2017.11 / 2073.21 / 98.79 | 210.06 / 210.19 / 0.04 | 7 |
| todos FF | decode | monolithic | — | — | 178.23 / 187.34 / 4.90 | 84.29 / 84.45 / 0.16 | 7 |
| todos FF | decode | reverse | 64 KiB | — | 1780.79 / 1820.51 / 43.01 | 19.24 / 19.48 / 0.11 | 7 |
| todos FF | decode | reverse | 1 MiB | — | 1772.76 / 1807.93 / 200.38 | 21.00 / 21.14 / 0.14 | 7 |
| todos FF | decode | reverse | 4 MiB | — | 1770.72 / 1820.98 / 61.47 | 33.07 / 33.11 / 0.09 | 7 |
| todos FF | decode | two_pass | 64 KiB | — | 2473.43 / 2569.09 / 47.65 | 17.39 / 17.57 / 0.04 | 7 |
| todos FF | decode | two_pass | 1 MiB | — | 2467.03 / 2505.77 / 111.06 | 21.01 / 21.27 / 0.15 | 7 |
| todos FF | decode | two_pass | 4 MiB | — | 2509.32 / 2531.29 / 49.67 | 33.04 / 33.25 / 0.21 | 7 |
| todos FF | encode | monolithic | — | — | 112.74 / 211.18 / 125.14 | 84.23 / 84.38 / 0.18 | 7 |
| todos FF | encode | reverse | 64 KiB | — | 1928.72 / 1961.69 / 109.76 | 19.29 / 19.54 / 0.09 | 7 |
| todos FF | encode | reverse | 1 MiB | — | 1942.92 / 2016.74 / 291.93 | 20.96 / 21.27 / 0.17 | 7 |
| todos FF | encode | reverse | 4 MiB | — | 1985.79 / 2012.46 / 220.97 | 33.06 / 33.27 / 0.08 | 7 |
| todos FF | encode | two_pass | 64 KiB | — | 2822.41 / 2913.81 / 129.59 | 17.30 / 17.45 / 0.19 | 7 |
| todos FF | encode | two_pass | 1 MiB | — | 2807.45 / 2859.02 / 59.30 | 21.04 / 21.12 / 0.17 | 7 |
| todos FF | encode | two_pass | 4 MiB | — | 2824.60 / 3002.57 / 282.49 | 33.12 / 33.20 / 0.10 | 7 |
| todos FF | caminho completo | full_address | — | crc32 | 2062.15 / 2089.12 / 21.93 | 210.12 / 210.34 / 0.09 | 7 |
| aleatório | decode | monolithic | — | — | 172.67 / 186.77 / 12.27 | 84.24 / 84.39 / 0.16 | 7 |
| aleatório | decode | reverse | 64 KiB | — | 1707.87 / 1766.85 / 45.53 | 17.35 / 17.62 / 0.18 | 7 |
| aleatório | decode | reverse | 1 MiB | — | 1733.44 / 1757.27 / 44.83 | 21.05 / 21.14 / 0.16 | 7 |
| aleatório | decode | reverse | 4 MiB | — | 1728.88 / 1794.27 / 200.24 | 33.06 / 33.12 / 0.10 | 7 |
| aleatório | decode | two_pass | 64 KiB | — | 2382.84 / 2486.69 / 80.51 | 17.35 / 17.38 / 0.15 | 7 |
| aleatório | decode | two_pass | 1 MiB | — | 2465.30 / 2509.58 / 43.46 | 21.02 / 21.08 / 0.19 | 7 |
| aleatório | decode | two_pass | 4 MiB | — | 2427.66 / 2531.69 / 95.24 | 33.01 / 33.22 / 0.16 | 7 |
| aleatório | encode | monolithic | — | — | 119.05 / 142.48 / 12.01 | 84.30 / 84.46 / 0.07 | 7 |
| aleatório | encode | reverse | 64 KiB | — | 1745.26 / 1757.65 / 12.18 | 17.37 / 17.54 / 0.10 | 7 |
| aleatório | encode | reverse | 1 MiB | — | 1748.06 / 1815.64 / 47.75 | 21.05 / 21.12 / 0.12 | 7 |
| aleatório | encode | reverse | 4 MiB | — | 1758.32 / 1841.75 / 68.36 | 33.04 / 33.10 / 0.26 | 7 |
| aleatório | encode | two_pass | 64 KiB | — | 2414.31 / 2488.04 / 321.11 | 17.25 / 17.39 / 0.30 | 7 |
| aleatório | encode | two_pass | 1 MiB | — | 2446.87 / 2487.34 / 44.70 | 21.12 / 21.27 / 0.04 | 7 |
| aleatório | encode | two_pass | 4 MiB | — | 2444.12 / 2480.36 / 43.03 | 33.03 / 33.26 / 0.17 | 7 |
| aleatório | caminho completo | full_address | — | crc32 | 2039.92 / 2048.36 / 49.81 | 210.13 / 210.32 / 0.10 | 7 |

Verificação X2: 315 observações finais; 45 grupos; todos os SHA-256 conferem. O caso todos FF gerou índice de 16 777 217 bytes.

## X3 — CRC32 e linha de base, 4 MiB

| Medição | Bytes processados | CRC32 observado | Tempo (ms) min / med / IQR | Peak WS (MiB) min / med / IQR | n |
|---|---:|---|---:|---:|---:|
| CRC32 sobre texto base64url | 5 592 406 | 0x9aef658d | 3.05 / 3.06 / 0.08 | 22.41 / 22.64 / 0.23 | 15 |
| linha de base H1 + bytes mínimos + hex | 4 194 304 | — | 28.68 / 30.03 / 1.01 | 37.36 / 37.57 / 0.22 | 15 |
| CRC32 sobre bytes | 4 194 304 | 0xadee12ca | 2.28 / 2.29 / 0.04 | 21.09 / 21.21 / 0.17 | 15 |
| CRC32 sobre texto hex | 8 388 608 | 0xc0392ec0 | 4.57 / 4.61 / 0.06 | 25.09 / 25.32 / 0.12 | 15 |

Na linha de base  a mediana foi 30.03 ms. O índice resultante teve 4 194 304 bytes e 8 388 608 caracteres hex. A leitura do arquivo de entrada ocorreu antes do cronômetro.

## Anomalias da X3 anterior

Na rodada anterior, com apenas três repetições, BLAKE2s-128 levou 14,6981 ms sobre bytes e 14,2142 ms sobre texto base64url, embora o texto fosse maior (5.592.406 contra 4.194.304 bytes). Essa diferença não identifica uma causa: a amostra era pequena e as medições não isolaram efeitos de escalonamento do sistema, cache e variação entre execuções. Ela não demonstra que o texto seja intrinsecamente mais rápido.

O CRC32 ambos mediu 7,0379 ms, contra 2,2667 + 3,2045 = 5,4712 ms para a soma das medianas separadas. A mediana de uma medição combinada não precisa ser a soma das medianas de duas amostras separadas; as execuções também diferem em estado de cache e variação de temporização. Com três repetições e sem desenho pareado, os dados anteriores não permitem atribuir os 1,5667 ms adicionais a uma causa específica.

## Comandos e saídas brutas

| Artefato | Conteúdo |
|---|---|
| 00_baseline_sha_system_raw.txt | hash inicial observado e primeira tentativa de consulta do ambiente |
| 00_measured_package_sha256.txt | hashes dos arquivos .py medidos e da cópia descartável |
| 00_environment_python_raw.txt | Python, Windows e identificação de CPU via Python/registro |
| 00_cpu_topology_raw.txt | consulta de núcleos físicos/lógicos pela API do Windows |
| 01_prepare_raw.txt | preparação e hashes dos dados de entrada/índices |
| 02_x2_worker_raw.txt | saída bruta dos 315 workers X2 da execução inicial; os 21 tempos de caminho completo foram substituídos pela rechecagem abaixo |
| 02_x2_roundtrip_recheck_worker_raw.txt | saída bruta autoritativa dos 21 caminhos completos X2, com SHA fora do cronômetro |
| 02_x2_aggregate_raw.txt | agregação X2 a partir dos workers originais |
| 02_x2_recheck_raw.txt | rechecagem do caminho completo e reconstrução dos CSVs finais X2 |
| 03_x3_worker_raw.txt | saída bruta dos 60 workers X3 |
| 02_x2_orchestrator_raw.txt | saída do primeiro agregador; erro apenas no campo auxiliar suite do CSV, corrigido sem repetir medições válidas |

Arquivos tabulares: x2_repetitions.csv (315 observações finais), x2_summary.csv (45 grupos), x2_full_path_recheck.csv (21 medições completas), x3_repetitions.csv (60 observações) e x3_summary.csv (4 grupos).

X5 não foi executado nesta rodada, conforme a instrução de aguardar a entrega do OpenCode.

## Integridade do pacote

source-copy/ contém somente os arquivos Python medidos. Os SHA-256 do original foram iguais antes e depois; nenhum arquivo do pacote foi modificado. As saídas binárias temporárias de encode/decode foram removidas após a validação SHA-256. Os dados de entrada e seus hashes permanecem em work/fixtures/.
