# Matriz de memória da Babel — add/get

Data: 2026-10-07T01:26:55-03:00
Máquina: Windows-10-10.0.19045-SP0
Python: 3.12.3 (`C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe`)

Babel testada: `C:\OllamaLimit\Sei lá\Projeto TTC\Babel TTC`. SHA-256 dos arquivos Python atuais registrados no JSON: `memory_scaling_matrix_result.json`. Nenhum arquivo da Babel foi editado.

## Método

CLI atual real em subprocesso isolado para add e get; pico via Windows GetProcessMemoryInfo amostrado a cada 50 ms (inclui high-water counters); fonte aleatória preparada antes da medição com `os.urandom` em blocos de 1 MiB; dados temporários limpos ao final. Caso de código real é tar determinístico dos arquivos Python da implementação atual.

Critério relativo: pico de 1 GB deve ser no máximo pico de 100 MB + 50.000.000 bytes, tanto WS quanto commit. A integridade do get exige tamanho e SHA-256 iguais.

## Resultados

| Caso | Operação | Entrada (bytes) | Pico WS (bytes) | Pico commit (bytes) | Tempo (s) | Exit | Integridade/status |
|---|---:|---:|---:|---:|---:|---:|---|
| random_100000000 | add | 100000000 | 23212032 | 16896000 | 8.931 | 0 | ADDED |
| random_100000000 | get | 100000000 | 18903040 | 12312576 | 0.325 | 1 | FAIL; get não verificado |
| random_300000000 | add | 300000000 | 23486464 | 17133568 | 19.755 | 0 | ADDED |
| random_300000000 | get | 300000000 | 19050496 | 12378112 | 1.277 | 1 | FAIL; get não verificado |
| random_1000000000 | add | 1000000000 | 23392256 | 17125376 | 34.479 | 0 | ADDED |
| random_1000000000 | get | 1000000000 | 19177472 | 12521472 | 0.272 | 1 | FAIL; get não verificado |
| real_babel_python_sources_tar | add | 61440 | 20353024 | 13824000 | 0.422 | 0 | PASS |
| real_babel_python_sources_tar | get | 61440 | 19116032 | 12468224 | 0.17 | 1 | FAIL; get não verificado |

## Comando de reprodução

```powershell
& 'C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe' 'C:\OllamaLimit\Sei lá\Projeto TTC\experimentos TTC\memory_scaling_matrix.py' --babel-dir 'C:\OllamaLimit\Sei lá\Projeto TTC\Babel TTC' --experiment-dir 'C:\OllamaLimit\Sei lá\Projeto TTC\experimentos TTC'
```

## Evidência detalhada

Os logs do CLI, tamanhos, SHA-256 de entrada/saída, erros e medições por execução estão em `memory_scaling_matrix_result.json`.

## Leitura estrita dos resultados

- `add` aleatório: 100 MB → pico WS 23.212.032 B e commit 16.896.000 B; 1 GB → WS 23.392.256 B e commit 17.125.376 B. Diferenças 1 GB − 100 MB: WS **180.224 B**; commit **229.376 B**. Para o caminho `add`, ambos ficam abaixo do limite de crescimento de 50.000.000 B.
- `add` aleatório de 1 GB saiu com código 0 e informou payload comprimido de 1.000.305.046 B. Esses números demonstram inserção pelo `add` no teste executado; não demonstram recuperação.
- Os quatro `get` terminaram com código 1, saída de 0 bytes e sem igualdade de SHA-256. Portanto não há medição válida de memória para recuperação. A saída de erro termina com `TypeError: a bytes-like object is required, not 'NoneType'`.
- A inspeção do código atual mostra a causa provável diretamente: `cli.py` chama `store_file_streaming(..., "payloads")`; `storage.py` cria o arquivo em `<base>/payloads/payloads/<hash>`, mas `index.py:get_payload` procura em `<base>/payloads/<hash>`. Assim, não alego que `get` funciona; o teste registrou falha de recuperação.
- O import do `validator.py` referencia `Optional` sem importá-lo. O harness forneceu `typing.Optional` em `builtins` antes do import para conseguir medir os caminhos CLI; isso é um shim do experimento, não uma correção da Babel. Essa limitação consta junto com os hashes das fontes no JSON.
- Caso de código real: tar determinístico dos `.py` presentes em `Babel TTC`, 61.440 B originais e 10.183 B comprimidos (razão 0,1657). O `add` saiu com código 0; o `get` falhou da mesma forma acima.

**Veredito limitado ao medido:** a memória observada no `add` escalou em ~0,18–0,23 MB entre entradas aleatórias de 100 MB e 1 GB e atendeu o critério relativo definido. A recuperação (`get`) falhou em todas as quatro tentativas, então a Babel não passou o teste completo de round-trip; o pico de memória do `get` funcional não foi medido.
