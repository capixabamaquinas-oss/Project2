from pathlib import Path
import csv,hashlib,json,re
root=Path(__file__).resolve().parent
project=root.parent.parent

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def rows(name):
 with (root/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def mib(x):return float(x)/1048576
base=(root/'00_baseline_raw.txt').read_text(encoding='utf-8-sig',errors='replace')
expected={}
for line in base.splitlines():
 m=re.match(r'^([0-9A-Fa-f]{64}) \*(.+)$',line)
 if m:expected[m.group(2)]=m.group(1).lower()
changed=[];matches=0
for p,h in expected.items():
 q=Path(p)
 if not q.exists() or sha(q)!=h:changed.append(p)
 else:matches+=1
copy=json.loads((root/'source_copy_sha256.json').read_text(encoding='utf-8'))
copy_matches=sum(1 for r in copy if sha(project/r['relative_path'])==r['sha256'])
summary=json.loads((root/'run_summary.json').read_text(encoding='utf-8'))
x1=rows('x1_formats.csv'); x2=rows('x2_x4_scale.csv'); x3=rows('x3_checksum_candidates.csv'); x4=rows('x4_random_fixtures.csv'); x5=rows('x5_hostile.csv'); x5b=rows('x5_boundary_verified.csv'); x6=rows('x6_real_user_files.csv')
if changed or matches!=len(expected) or copy_matches!=len(copy): raise SystemExit('Integrity mismatch; report not finalized')
runraw=(root/'03_run_raw.txt').read_text(encoding='utf-8-sig',errors='replace')
assert 'X2_DECODE_VALIDATION_FAIL' not in runraw and 'X2_ROUNDTRIP_FAIL' not in runraw and 'X2_OUTPUT_MISMATCH' not in runraw and 'X2_WORKER_FAIL' not in runraw
assert all(r['all_repeats_same_output']=='True' for r in x2)
assert summary['edge_failed']==0 and summary['x1_failed']==0 and summary['x6_failed']==0

x1_4m=[r for r in x1 if r['input_bytes']=='4194304']
x2_16=[r for r in x2 if r['size_bytes']=='16777216']
x3_4m=[r for r in x3 if r['size_bytes']=='4194304' and (r['format']=='base64url-no-padding' or r['coverage']=='bytes')]
x4rows=x4
x6b=[r for r in x6 if r['format']=='base64url-no-padding']
x6files=json.loads((root/'input_manifest.json').read_text(encoding='utf-8'))
x6inputs=[r for r in x6files if r['kind'] in ('real_user_file','derived_real_user_text')]
source_meta=json.loads((root/'references'/'director_dossier_text_source.json').read_text(encoding='utf-8'))

lines=[]
lines += ['# Relatorio dos experimentos Babel Pura H1 X1 a X6','', 'Data da execucao: 2026-10-15', '', '## Escopo e integridade', '', 'Os experimentos mediram o nucleo H1 (sequencias de bytes finitas para N0) usando apenas uma copia descartavel do pacote em `source-copy/`. Nenhum arquivo em `babel_pura/` ou `tests/` do projeto original foi escrito. A auditoria final comparou os 33 arquivos que existiam antes da execucao: **33/33 hashes SHA-256 coincidiram**. Os cinco arquivos de codigo/teste da copia tambem coincidem com a fonte (**5/5**). A area de trabalho temporaria de 618.535.940 bytes foi removida depois da validacao; scripts, entradas, resultados e logs permanecem.', '', 'A tabela X1-X7 utilizada esta registrada em `references/dossier_section_7_1_X1-X7.txt`. O arquivo temporario original da tabela (`01f0665c-8b09-45e4-941f-c52d4a9f8653.tmp`) nao esta mais em Downloads nesta sessao. O texto pre-extraido existente no projeto registra SHA-256 do DOCX de origem `' + source_meta['source_docx_sha256'] + '` e tem SHA-256 `' + source_meta['text_sha256'] + '`. O hash do DOCX temporario original nao pode ser revalidado sem o arquivo. O DOCX v3 atualmente disponivel em Downloads nao contem a tabela X1-X6 dentro da secao 7.1; essa diferenca de versao fica registrada para nao confundir as especificacoes.', '', '## Ambiente e registro inicial', '', '- Python: `3.12.14` (CPython 64-bit).', '- Sistema: `Windows-10-10.0.19045-SP0` / `Microsoft Windows NT 10.0.19045.0` (build 19045).', '- Os hashes SHA-256 iniciais dos 33 arquivos do projeto e do DOCX v3 estao em `00_baseline_raw.txt`; o comando esta em `00_baseline_command.txt`.', '- O DOCX v2 usado como arquivo real X6 foi hashado antes da leitura: ver `01_v2_dossier_sha256_raw.txt`.', '- Os caminhos, tamanhos, seeds e hashes dos arquivos de entrada estao em `input_manifest.json`; a copia do pacote esta em `source_copy_sha256.json`.', '- Memoria: Windows `GetProcessMemoryInfo`, com `PeakWorkingSetSize` e `PeakPagefileUsage`; nenhum resultado usa `tracemalloc`.', '- As medidas de tempo X2 incluem I/O de arquivo dentro da funcao de codificacao, mas excluem inicio/importacao do processo. O Working Set de pico e o commit sao absolutos desde o inicio do worker; o CSV tambem inclui a diferenca sobre o Working Set medido apos importacao.', '', '## Resultados', '', '### X1 ? formatos textuais', '', 'Foram comparados os bytes textuais do indice H1, sem prefixo, checksum ou politica de quebra de linha. Cada tempo e a mediana de tres chamadas de codificacao/decodificacao do formato no mesmo processo. Em 4 MiB:', '', '| Formato | Caracteres | Texto / entrada | Codificar (ms) | Decodificar (ms) |', '|---|---:|---:|---:|---:|']
for r in x1_4m:
 lines.append(f"| {r['format']} | {int(r['text_chars']):,} | {float(r['payload_to_input_ratio']):.4f}x | {float(r['encode_median_ms']):.3f} | {float(r['decode_median_ms']):.3f} |".replace(',',' '))
lines += ['', f"Nos {len(x1)} casos, incluindo vetor vazio, bytes de borda e entradas aleatorias, passaram {summary['x1_passed']}/{summary['x1_records']} round-trips. Ergonomia real de copiar/colar e quebras de linha nao foi medida; a politica final de envelope continua aberta. Dados completos: `x1_formats.csv`.", '', '### X2 ? soma monolitica e segmentada', '', f"Foram medidos {len(x2)} grupos: cinco tamanhos (1 KiB, 64 KiB, 1 MiB, 4 MiB e 16 MiB), tres repeticoes por grupo e tres chunks segmentados (4 KiB, 64 KiB e 1 MiB), para leitura inversa e duas passagens, mais monolitico. Todos os dados eram pseudoaleatorios com seeds registradas. As saidas SHA-256 coincidiram entre estrategias por tamanho; nao houve falha de decodificacao/round-trip.", '', 'Resultados medianos na entrada de 16 MiB:', '', '| Metodo | Chunk | Tempo (s) | Pico Working Set (MiB) | Pico commit (MiB) |', '|---|---:|---:|---:|---:|']
for r in x2_16:
 chunk='?' if not r['chunk_size'] else f"{int(r['chunk_size'])//1024} KiB"
 lines.append(f"| {r['method']} | {chunk} | {float(r['median_elapsed_seconds']):.3f} | {mib(r['median_peak_working_set_bytes']):.2f} | {mib(r['median_peak_commit_bytes']):.2f} |")
lines += ['', 'Nesta amostra, o monolitico foi mais rapido e teve pico de memoria maior. A segmentacao reduziu o Working Set de pico, com tempos maiores e sensiveis ao chunk; estes valores nao definem um limite de produto nem uma escolha final. CSV agregado: `x2_x4_scale.csv`; saida bruta e argv de cada worker: `x2_worker_raw.txt`.', '', '### X3 ? candidatos de checksum', '', f"Foram registrados {len(x3)} resultados de quatro candidatos (`CRC32`, `SHA-256` completo, primeiros 128 bits de SHA-256, `BLAKE2s-128`), quatro escopos de texto (hex, base32 e base64url) mais bytes, e tres repeticoes. Sao candidatos experimentais, nao aprovacao para o produto. A tabela abaixo usa 4 MiB e base64url para os escopos de texto. `Ambos` concatena dois resultados independentes, um sobre os bytes e outro sobre o texto do indice.", '', '| Candidato | Tamanho de um digest (bytes / hex chars) | Bytes (ms) | Texto (ms) | Ambos (ms) |', '|---|---:|---:|---:|---:|']
by={(r['algorithm'],r['coverage']):r for r in x3_4m if r['format']=='base64url-no-padding' or r['coverage']=='bytes'}
for alg in ('crc32','sha256','sha256_128','blake2s_128'):
 b=by[(alg,'bytes')]; t=by[(alg,'text')]; both=by[(alg,'both')]
 lines.append(f"| {alg} | {int(b['checksum_bytes'])} / {int(b['checksum_hex_chars'])} | {float(b['median_checksum_ms']):.3f} | {float(t['median_checksum_ms']):.3f} | {float(both['median_checksum_ms']):.3f} |")
lines += ['', 'O overhead total de `Ambos` e o dobro do tamanho de um digest quando os dois valores sao mantidos. Tamanhos mostrados supoem checksum em hexadecimal min?sculo; prefixo, separador e serializacao de checksum nao foram decididos. `x3_checksum_candidates.csv` contem os casos por tamanho, formato e cobertura.', '', '### X4 ? escala com dados nao repetitivos', '', 'Foram usados cinco arquivos de `random.Random(seed).randbytes`, de 1 KiB a 16 MiB; cada um continha todos os 256 valores de byte observados. Esses mesmos arquivos foram usados no X2. Seeds, entropia observada e SHA-256:', '', '| Bytes | Seed | Valores de byte distintos | Entropia (bits/simbolo) | SHA-256 |', '|---:|---:|---:|---:|---|']
for r in x4rows:
 lines.append(f"| {int(r['size_bytes']):,} | {r['seed']} | {r['distinct_byte_values']} | {float(r['byte_entropy_bits_per_symbol']):.5f} | `{r['sha256']}` |".replace(',',' '))
lines += ['', 'A execucao chegou a 16 MiB. Isso nao determina o tamanho maximo pratico nem atende a X7 em outras plataformas.', '', '### X5 ? entrada hostil e limite antes do parser', '', 'O limite `4096` abaixo e apenas parametro do experimento, nao uma decisao de Q7. O wrapper de preflight existe somente no script experimental. Testes de borda corrigidos usam payload hexadecimal minusculo:', '', '| Tamanho | Caminho | Resultado | Chamadas ao parser / decoder de formato |', '|---:|---|---|---:|']
for n in (4095,4096,4097):
 for mode in ('direct','preflight'):
  r=next(x for x in x5b if x['case']==f'lowercase_limit_{n}' and x['mode']==mode)
  lines.append(f"| {n} | {mode} | {r['outcome']} | {r['parser_calls']} / {r['format_decode_calls']} |")
lines += ['', 'No preflight experimental, o limite exato foi aceito e +1 foi rejeitado com zero chamadas ao parser e ao decodificador de formato. Chamando o pacote copiado diretamente, +1 chegou ao parser e ao decodificador, embora o payload hexadecimal impar acabasse rejeitado. Portanto, o pacote atual **nao implementa o limite nem o preflight**.', '', 'No caso de endereco valido com 8 MiB de texto (`B1:v1:` + hexadecimal), o parser direto aceitou a entrada; tempo 0,486 s, pico Working Set 61,65 MiB, incremento sobre baseline 28,03 MiB, pico commit 55,38 MiB. A entrada de 8 MiB de lixo foi rejeitada como prefixo/forma incorreta. `x5_hostile.csv`, `x5_boundary_verified.csv` e `x5_worker_raw.txt` / `x5_boundary_retry_raw.txt` preservam os casos completos.', '', '### X6 ? arquivos reais do usuario', '', f"Foram medidos {len(x6inputs)} entradas reais ou texto derivado de documento real: dois DOCX do dossie, quatro arquivos `.py` do projeto H1 e uma extracao UTF-8 do DOCX v3. Os bytes do DOCX foram tratados como bytes, sem descompactar ou normalizar. Todos os {len(x6)} round-trips (sete arquivos x tres formatos) passaram. O endereco candidato abaixo soma o prefixo de rascunho `B1:v1:` (6 caracteres) ao texto do indice, sem checksum; nao e contrato final.", '', '| Arquivo | Bytes | Endereco base64url (chars) | Razao endereco/arquivo | SHA-256 da entrada |', '|---|---:|---:|---:|---|']
for r in x6b:
 lines.append(f"| {r['file']} | {int(r['input_bytes']):,} | {int(r['draft_address_chars_no_checksum']):,} | {float(r['draft_address_to_file_ratio']):.5f}x | `{r['input_sha256']}` |".replace(',',' '))
lines += ['', 'Os resultados completos para hex e base32 estao em `x6_real_user_files.csv`; a lista de origens e hashes tambem esta em `input_manifest.json`.', '', '## Arquivos de evidencia', '', '- `03_run_command.txt`: comando principal executado.', '- `03_run_raw.txt`: saida bruta principal; `x2_worker_raw.txt`, `x5_worker_raw.txt` e `x5_boundary_retry_raw.txt`: argv e saidas dos subprocessos.', '- `x1_formats.csv`, `x2_x4_scale.csv`, `x3_checksum_candidates.csv`, `x4_random_fixtures.csv`, `x5_hostile.csv`, `x5_boundary_verified.csv`, `x6_real_user_files.csv`, `edge_vectors.csv`: resultados tabulares.', '- `input_manifest.json`: caminhos, tamanhos, seeds e SHA-256 das entradas.', '- `source_copy/` e `source_copy_sha256.json`: copia H1 usada e hashes.', '- `00_baseline_raw.txt`, `04_review_raw.txt`, `05_cleanup_raw.txt`: registro inicial, integridade final e limpeza de temporarios.', '', '## Limites da conclusao', '', '- Os tempos e memorias sao especificos deste Windows 10 / CPython 3.12.14 e desta execucao; apenas uma plataforma foi medida.', '- `MAX_ADDRESS_CHARS=4096` e puramente experimental. O limite de produto segue aberto.', '- X3 mediu candidatos de checksum; nenhum algoritmo ou tamanho foi selecionado para BP1.', '- X1 mediu tamanho e tempo do texto do indice; UX de colagem, quebras de linha e envelope final ficaram fora.', '- X6 usa arquivos reais ja presentes no projeto/Downloads. O DOCX temporario que originou a tabela X1-X7 nao estava presente; para a especificacao, foi usada a extracao preexistente com hash registrado.', '- O trabalho verificou as funcoes H1 copiadas; nao executou a suite de unidade completa nem alterou a arvore original.', '', f"## Integridade final", '', f"- Arquivos originais hashados no inicio: {len(expected)}; coincidencias no encerramento: {matches}; divergencias: {len(changed)}.", f"- Arquivos de codigo/teste na copia comparados com a fonte: {copy_matches}/{len(copy)}.", f"- Vetores de borda: {summary['edge_passed']}/{summary['edge_rows']} passaram.", f"- Round-trips X1: {summary['x1_passed']}/{summary['x1_records']}; X6: {summary['x6_passed']}/{summary['x6_records']}.", '- X2: hashes de saida iguais entre metodos por tamanho; 0 falhas de validacao/round-trip.', '- X5: o wrapper experimental rejeitou +1 antes de chamar o parser; o parser do pacote nao tem esse bloqueio.', '']
report=root/'REPORT.md'
report.write_text('\n'.join(lines),encoding='utf-8')
integrity={'baseline_file_count':len(expected),'baseline_matches':matches,'baseline_changed':changed,'copy_file_count':len(copy),'copy_matches_original':copy_matches,'edge_passed':summary['edge_passed'],'edge_rows':summary['edge_rows'],'x1_passed':summary['x1_passed'],'x1_records':summary['x1_records'],'x2_aggregated_records':len(x2),'x2_validation_failure_markers':{k:runraw.count(k) for k in ('X2_DECODE_VALIDATION_FAIL','X2_ROUNDTRIP_FAIL','X2_OUTPUT_MISMATCH','X2_WORKER_FAIL')},'x3_records':len(x3),'x5_records_initial':len(x5),'x5_boundary_records':len(x5b),'x6_passed':summary['x6_passed'],'x6_records':summary['x6_records'],'report_sha256':sha(report)}
(root/'integrity_results.json').write_text(json.dumps(integrity,indent=2)+'\n',encoding='utf-8')
print(json.dumps(integrity,sort_keys=True))
print('REPORT='+str(report))
