# Matriz de memória da Babel — add/get

Data: 2026-10-07T02:17:41-03:00
Máquina: Windows-10-10.0.19045-SP0
Python: 3.12.3 (`C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe`)

Babel testada: `C:\OllamaLimit\Sei lá\Projeto TTC\Babel TTC`. SHA-256 dos arquivos Python atuais registrados no JSON: `memory_scaling_matrix_final_result.json`. Nenhum arquivo da Babel foi editado.

## Método

CLI atual real em subprocesso isolado para add e get; pico via Windows GetProcessMemoryInfo amostrado a cada 50 ms (inclui high-water counters); fonte aleatória preparada antes da medição com `os.urandom` em blocos de 1 MiB; dados temporários limpos ao final. Caso de código real é tar determinístico dos arquivos Python da implementação atual.

Critério relativo: pico de 1 GB deve ser no máximo pico de 100 MB + 50.000.000 bytes, tanto WS quanto commit. A integridade do get exige tamanho e SHA-256 iguais.

## Resultados

| Caso | Operação | Entrada (bytes) | Pico WS (bytes) | Pico commit (bytes) | Tempo (s) | Exit | Integridade/status |
|---|---:|---:|---:|---:|---:|---:|---|
| random_100000000 | add | 100000000 | 23674880 | 17367040 | 7.336 | 0 | ADDED |
| random_100000000 | get | 100000000 | 23105536 | 16363520 | 3.228 | 0 | PASS; get verificado |
| random_300000000 | add | 300000000 | 23576576 | 17293312 | 22.061 | 0 | ADDED |
| random_300000000 | get | 300000000 | 23138304 | 16457728 | 2.507 | 0 | PASS; get verificado |
| random_1000000000 | add | 1000000000 | 23584768 | 17219584 | 44.317 | 0 | ADDED |
| random_1000000000 | get | 1000000000 | 23191552 | 16556032 | 14.164 | 0 | PASS; get verificado |
| real_babel_python_sources_tar | add | 51200 | 20418560 | 13795328 | 0.277 | 0 | PASS |
| real_babel_python_sources_tar | get | 51200 | 20361216 | 13656064 | 0.427 | 0 | PASS; get verificado |

## Comando de reprodução

```powershell
& 'C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe' 'C:\OllamaLimit\Sei lá\Projeto TTC\experimentos TTC\memory_scaling_matrix_final.py' --babel-dir 'C:\OllamaLimit\Sei lá\Projeto TTC\Babel TTC' --experiment-dir 'C:\OllamaLimit\Sei lá\Projeto TTC\experimentos TTC'
```

## Evidência detalhada

Os logs do CLI, tamanhos, SHA-256 de entrada/saída, erros e medições por execução estão em `memory_scaling_matrix_final_result.json`.
