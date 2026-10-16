# Matriz de memória da Babel — add/get

Data: 2026-10-07T02:11:54-03:00
Máquina: Windows-10-10.0.19045-SP0
Python: 3.12.3 (`C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe`)

Babel testada: `C:\OllamaLimit\Sei lá\Projeto TTC\Babel TTC`. SHA-256 dos arquivos Python atuais registrados no JSON: `memory_scaling_matrix_after_fix_result.json`. Nenhum arquivo da Babel foi editado.

## Método

CLI atual real em subprocesso isolado para add e get; pico via Windows GetProcessMemoryInfo amostrado a cada 50 ms (inclui high-water counters); fonte aleatória preparada antes da medição com `os.urandom` em blocos de 1 MiB; dados temporários limpos ao final. Caso de código real é tar determinístico dos arquivos Python da implementação atual.

Critério relativo: pico de 1 GB deve ser no máximo pico de 100 MB + 50.000.000 bytes, tanto WS quanto commit. A integridade do get exige tamanho e SHA-256 iguais.

## Resultados

| Caso | Operação | Entrada (bytes) | Pico WS (bytes) | Pico commit (bytes) | Tempo (s) | Exit | Integridade/status |
|---|---:|---:|---:|---:|---:|---:|---|
| random_100000000 | add | 100000000 | 23617536 | 17231872 | 6.655 | 0 | ADDED |
| random_100000000 | get | 100000000 | 23126016 | 16429056 | 3.321 | 0 | PASS; get verificado |
| random_300000000 | add | 300000000 | 23539712 | 17133568 | 13.173 | 0 | ADDED |
| random_300000000 | get | 300000000 | 23212032 | 16568320 | 2.415 | 0 | PASS; get verificado |
| random_1000000000 | add | 1000000000 | 23347200 | 16928768 | 43.324 | 0 | ADDED |
| random_1000000000 | get | 1000000000 | 23449600 | 16908288 | 7.716 | 0 | PASS; get verificado |
| real_babel_python_sources_tar | add | 51200 | 20480000 | 13840384 | 0.278 | 0 | PASS |
| real_babel_python_sources_tar | get | 51200 | 20398080 | 13717504 | 0.228 | 0 | PASS; get verificado |

## Comando de reprodução

```powershell
& 'C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe' 'C:\OllamaLimit\Sei lá\Projeto TTC\experimentos TTC\memory_scaling_matrix_after_fix.py' --babel-dir 'C:\OllamaLimit\Sei lá\Projeto TTC\Babel TTC' --experiment-dir 'C:\OllamaLimit\Sei lá\Projeto TTC\experimentos TTC'
```

## Evidência detalhada

Os logs do CLI, tamanhos, SHA-256 de entrada/saída, erros e medições por execução estão em `memory_scaling_matrix_after_fix_result.json`.
