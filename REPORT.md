# Relatório dos experimentos Babel Pura H1 X1 a X6

Data da execução: 2026-10-15

## Escopo e integridade

Os experimentos mediram o núcleo H1 (sequências de bytes finitas para N0) usando apenas uma cópia descartável do pacote em `source-copy/`. Nenhum arquivo em `babel_pura/` ou `tests/` do projeto original foi escrito. A auditoria final comparou os 33 arquivos que existiam antes da execução: **33/33 hashes SHA-256 coincidiram**. Os cinco arquivos de código/teste da cópia também coincidem com a fonte (**5/5**). A área de trabalho temporária de 618.535.940 bytes foi removida depois da validação; scripts, entradas, resultados e logs permanecem.

A tabela X1-X7 utilizada está registrada em `references/dossier_section_7_1_X1-X7.txt`. O arquivo temporário original da tabela (`01f0665c-8b09-45e4-941f-c52d4a9f8653.tmp`) não está mais em Downloads nesta sessão. O texto pré-extraído existente no projeto registra SHA-256 do DOCX de origem `528826faec1f7dffdfa9bf128d69a37d90ba058625f9994d39dae993f06d3743` e tem SHA-256 `50c30e1fd13cadc813f13153499ac11b8354df039187f9fe8ed60cac57767f87`. O hash do DOCX temporário original não pode ser revalidado sem o arquivo. O DOCX v3 atualmente disponível em Downloads não contêm a tabela X1-X6 dentro da seção 7.1; essa diferença de versão fica registrada para não confundir as especificações.

## Ambiente e registro inicial

- Python: `3.12.14` (CPython 64-bit).
- Sistema: `Windows-10-10.0.19045-SP0` / `Microsoft Windows NT 10.0.19045.0` (build 19045).
- Os hashes SHA-256 iniciais dos 33 arquivos do projeto e do DOCX v3 estão em `00_baseline_raw.txt`; o comando está em `00_baseline_command.txt`.
- O DOCX v2 usado como arquivo real X6 foi hashado antes da leitura: ver `01_v2_dossier_sha256_raw.txt`.
- Os caminhos, tamanhos, seeds e hashes dos arquivos de entrada estão em `input_manifest.json`; a cópia do pacote está em `source_copy_sha256.json`.
- Memória: Windows `GetProcessMemoryInfo`, com `PeakWorkingSetSize` e `PeakPagefileUsage`; nenhum resultado usa `tracemalloc`.
- As medidas de tempo X2 incluem I/O de arquivo dentro da função de codificação, mas excluem início/importação do processo. O Working Set de pico e o commit são absolutos desde o início do worker; o CSV também inclui a diferença sobre o Working Set medido apos importação.

## Resultados

### X1 - formatos textuais

Foram comparados os bytes textuais do indice H1, sem prefixo, checksum ou política de quebra de linha. Cada tempo e a mediana de três chamadas de codificação/decodificação do formato no mesmo processo. Em 4 MiB:

| Formato | Caracteres | Texto / entrada | Codificar (ms) | Decodificar (ms) |
|---|---:|---:|---:|---:|
| hex-lower | 8 388 608 | 2.0000x | 25.318 | 27.538 |
| base32-no-padding | 6 710 887 | 1.6000x | 783.628 | 857.378 |
| base64url-no-padding | 5 592 406 | 1.3333x | 22.408 | 26.313 |

Nos 39 casos, incluindo vetor vazio, bytes de borda e entradas aleatórias, passaram 39/39 round-trips. Ergonomia real de copiar/colar e quebras de linha não foi medida; a política final de envelope continua aberta. Dados completos: `x1_formats.csv`.

### X2 - soma monolítica e segmentada

Foram medidos 35 grupos: cinco tamanhos (1 KiB, 64 KiB, 1 MiB, 4 MiB e 16 MiB), três repetições por grupo e três chunks segmentados (4 KiB, 64 KiB e 1 MiB), para leitura inversa e duas passagens, mais monolítico. Todos os dados eram pseudoaleatórios com seeds registradas. As saídas SHA-256 coincidiram entre estratégias por tamanho; não houve falha de decodificação/round-trip.

Resultados medianos na entrada de 16 MiB:

| Método | Chunk | Tempo (s) | Pico Working Set (MiB) | Pico commit (MiB) |
|---|---:|---:|---:|---:|
| monolithic | n/a | 0.128 | 84.66 | 78.32 |
| segmented_reverse | 4 KiB | 1.738 | 19.47 | 13.03 |
| segmented_reverse | 64 KiB | 3.746 | 19.26 | 12.77 |
| segmented_reverse | 1 MiB | 1.949 | 21.40 | 14.91 |
| segmented_two_pass | 4 KiB | 2.848 | 19.26 | 12.84 |
| segmented_two_pass | 64 KiB | 2.674 | 19.35 | 12.79 |
| segmented_two_pass | 1 MiB | 2.963 | 21.60 | 14.90 |

Nesta amostra, o monolítico foi mais rápido e teve pico de memória maior. A segmentação reduziu o Working Set de pico, com tempos maiores e sensíveis ao chunk; estes valores não definem um limite de produto nem uma escolha final. CSV agregado: `x2_x4_scale.csv`; saída bruta e argv de cada worker: `x2_worker_raw.txt`.

### X3 - candidatos de checksum

Foram registrados 140 resultados de quatro candidatos (`CRC32`, `SHA-256` completo, primeiros 128 bits de SHA-256, `BLAKE2s-128`), cobertura dos bytes e cobertura do texto do índice nos três formatos (hex, base32 e base64url), e três repetições. São candidatos experimentais, não aprovação para o produto. A tabela abaixo usa 4 MiB e base64url para os escopos de texto. `Ambos` concatena dois resultados independentes, um sobre os bytes e outro sobre o texto do índice.

| Candidato | Tamanho de um digest (bytes / hex chars) | Bytes (ms) | Texto (ms) | Ambos (ms) |
|---|---:|---:|---:|---:|
| crc32 | 4 / 8 | 2.267 | 3.204 | 7.038 |
| sha256 | 32 / 64 | 8.844 | 11.833 | 20.052 |
| sha256_128 | 16 / 32 | 8.857 | 12.192 | 20.472 |
| blake2s_128 | 16 / 32 | 14.698 | 14.214 | 27.307 |

O overhead total de `Ambos` é o dobro do tamanho de um digest quando os dois valores são mantidos. Tamanhos mostrados supõem checksum em hexadecimal minúsculo; prefixo, separador e serialização de checksum não foram decididos. `x3_checksum_candidates.csv` contém os casos por tamanho, formato e cobertura.

### X4 - escala com dados não repetitivos

Foram usados cinco arquivos de `random.Random(seed).randbytes`, de 1 KiB a 16 MiB. As quatro amostras a partir de 64 KiB apresentaram os 256 valores de byte; a amostra de 1 KiB apresentou 253. Esses mesmos arquivos foram usados no X2. Seeds, entropia observada e SHA-256:

| Bytes | Seed | Valores de byte distintos | Entropia (bits/símbolo) | SHA-256 |
|---:|---:|---:|---:|---|
| 1 024 | 20261015 | 253 | 7.82025 | `6394231106427ed874675c4bf17c6a66199cb6eb19a11c18c9083c07a3c13f01` |
| 65 536 | 20261016 | 256 | 7.99718 | `872ab354928a52de7d6334631dd88c98f2379e8adc2efb41535029c06fb3defa` |
| 1 048 576 | 20261017 | 256 | 7.99981 | `05cdac6fabfa51e6ee23ff4568db74b5d5ae7747f3d7849dedad5a7f177b17e2` |
| 4 194 304 | 20261018 | 256 | 7.99996 | `8d38e5c70932b418c654aaa79a46ed64dbcd5580502f19701d4978ab60ecf8bb` |
| 16 777 216 | 20261019 | 256 | 7.99999 | `146a5cb9d41cfe2c72843981d236482cbea884f35b3fa1b3b9fdd949b890eaf6` |

A execução chegou a 16 MiB. Isso não determina o tamanho máximo prático nem atende a X7 em outras plataformas.

### X5 - entrada hostil e limite antes do parser

O limite `4096` abaixo é apenas parâmetro do experimento, não uma decisão de Q7. O wrapper de preflight existe somente no script experimental. Testes de borda corrigidos usam payload hexadecimal minúsculo:

| Tamanho | Modo | Resultado | Chamadas ao parser / decoder de formato |
|---:|---|---|---:|
| 4095 | direct | InvalidAddressError | 1 / 1 |
| 4095 | preflight | InvalidAddressError | 1 / 1 |
| 4096 | direct | accepted | 1 / 1 |
| 4096 | preflight | accepted | 1 / 1 |
| 4097 | direct | InvalidAddressError | 1 / 1 |
| 4097 | preflight | preflight_rejected_before_parser | 0 / 0 |

No preflight experimental, o limite exato foi aceito e +1 foi rejeitado com zero chamadas ao parser e ao decodificador de formato. Chamando o pacote copiado diretamente, +1 chegou ao parser e ao decodificador, embora o payload hexadecimal ímpar acabasse rejeitado. Portanto, o pacote atual **não implementa o limite nem o preflight**.

No caso de endereço válido com 8 MiB de texto (`B1:v1:` + hexadecimal), o parser direto aceitou a entrada; tempo 0,486 s, pico Working Set 61,65 MiB, incremento sobre baseline 28,03 MiB, pico commit 55,38 MiB. A entrada de 8 MiB de lixo foi rejeitada como prefixo/forma incorreta. `x5_hostile.csv`, `x5_boundary_verified.csv` e `x5_worker_raw.txt` / `x5_boundary_retry_raw.txt` preservam os casos completos.

### X6 - arquivos reais do usuário

Foram processadas 7 entradas, entre arquivos reais e texto extraído de documento real: dois DOCX do dossiê, quatro arquivos `.py` do projeto H1 e uma extração UTF-8 do DOCX v3. Os bytes do DOCX foram tratados como bytes, sem descompactar ou normalizar. Todos os 21 round-trips (sete arquivos x três formatos) passaram. O endereço candidato abaixo soma o prefixo de rascunho `B1:v1:` (6 caracteres) ao texto do índice, sem checksum; não e contrato final.

| Arquivo | Bytes | Endereço base64url (chars) | Razão endereço/arquivo | SHA-256 da entrada |
|---|---:|---:|---:|---|
| address_py.py | 3 463 | 4 624 | 1.33526x | `0b041bbc3451cf085c85a01cf7b2758c61fd98c05bc7451b7a3dfbc69feddd4a` |
| codec_py.py | 11 429 | 15 245 | 1.33389x | `6a72eb64d420570499d9cafe29ea6f39e0a90687686006d6404e7d0bfd2d72b6` |
| dossier_v2_docx.docx | 55 879 | 74 512 | 1.33345x | `3a12823e5110b979849f5d7a0da84af92d4aeaf4e269e0eee9aada944b25094c` |
| dossier_v3_docx.docx | 157 130 | 209 513 | 1.33337x | `b628be6e4cc301d512a27c28bfdeff3bd63d98c8b127ffe1e8d5625058f6f094` |
| dossier_v3_extracted.txt | 27 108 | 36 150 | 1.33355x | `917d6a0c4836793b54aa19a43b763e0a5cd7014678e9f98e1627f92e01005a4d` |
| test_address_py.py | 8 013 | 10 690 | 1.33408x | `60f5cc53a084681ced22f3d70dfdd99947ad0e743991c6f91ea6505f68466c0e` |
| test_codec_py.py | 11 624 | 15 505 | 1.33388x | `af446eb7192dc2f1cacfc209b824403eb74e96e4cb1b7bc166f768c3b3d8f10a` |

Os resultados completos para hex e base32 estão em `x6_real_user_files.csv`; a lista de origens e hashes também está em `input_manifest.json`.

## Arquivos de evidência

- `03_run_command.txt`: comando principal executado.
- `03_run_raw.txt`: saída bruta principal; `x2_worker_raw.txt`, `x5_worker_raw.txt` e `x5_boundary_retry_raw.txt`: argv e saídas dos subprocessos.
- `x1_formats.csv`, `x2_x4_scale.csv`, `x3_checksum_candidates.csv`, `x4_random_fixtures.csv`, `x5_hostile.csv`, `x5_boundary_verified.csv`, `x6_real_user_files.csv`, `edge_vectors.csv`: resultados tabulares.
- `input_manifest.json`: caminhos, tamanhos, seeds e SHA-256 das entradas.
- `source_copy/` e `source_copy_sha256.json`: cópia H1 usada e hashes.
- `00_baseline_raw.txt`, `04_review_raw.txt`, `05_cleanup_raw.txt`: registro inicial, integridade final e limpeza de temporários.

## Limites da conclusão

- Os tempos e memorias são especificos deste Windows 10 / CPython 3.12.14 e desta execução; apenas uma plataforma foi medida.
- `MAX_ADDRESS_CHARS=4096` é puramente experimental. O limite de produto segue aberto.
- X3 mediu candidatos de checksum; nenhum algoritmo ou tamanho foi selecionado para BP1.
- X1 mediu tamanho e tempo do texto do índice; UX de colagem, quebras de linha e envelope final ficaram fora.
- X6 usa arquivos reais já presentes no projeto/Downloads. O DOCX temporário que originou a tabela X1-X7 não estava presente; para a especificação, foi usada a extração preexistente com hash registrado.
- O trabalho verificou as funções H1 copiadas; não executou a suíte de unidade completa nem alterou a árvore original.

## Integridade final

- Arquivos originais hashados no início: 33; coincidências no encerramento: 33; divergências: 0.
- Arquivos de código/teste na cópia comparados com a fonte: 5/5.
- Vetores de borda: 99/99 passaram.
- Round-trips X1: 39/39; X6: 21/21.
- X2: hashes de saída iguais entre métodos por tamanho; 0 falhas de validação/round-trip.
- X5: o wrapper experimental rejeitou +1 antes de chamar o parser; o parser do pacote não tem esse bloqueio.
