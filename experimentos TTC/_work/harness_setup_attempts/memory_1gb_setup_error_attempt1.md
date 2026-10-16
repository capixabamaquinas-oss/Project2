# Teste real de memória — inserção de arquivo de 1 GB na Babel

Data/hora: 2026-10-06T22:46:15-03:00  
Máquina: Windows-10-10.0.19045-SP0  
Python: 3.12.3 (`C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe`)

## Caminho executado

`Babel TTC/cli.py:main → cmd_add → LocalDiskStorage.store_file_streaming → storage.read → BabelIndex.add_item`

O teste chama o CLI atual em processo filho isolado. O arquivo de entrada tem 1.000.000.000 bytes (1 GB decimal), foi gravado antes da medição em blocos de 1 MiB com `os.urandom`; SHA-256: `2ea03688efe75bbc2813c7d12da2551e896a6b3cd2907780dfa0c9b6b04230e9`. A fonte e o pacote SQLite ficam em diretório temporário em `experimentos TTC/_work` e são removidos após a medição.

## Comando

`& 'C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe' 'experimentos TTC/memory_1gb_real_test.py' --babel-dir 'Babel TTC' --experiment-dir 'experimentos TTC'`

## Critério e medição

Critério previamente adotado: **FALHA se o pico do working set ou o pico de pagefile/commit for ≥ 200.000.000 bytes (200 MB decimais)**. Memória do processo medida por `GetProcessMemoryInfo` no Windows, consultada em intervalos de 50 ms e novamente após o processo terminar, enquanto o handle ainda estava aberto. Pico working set: **18,051,072 bytes (18.05 MB)**. Pico pagefile/commit: **11,513,856 bytes (11.51 MB)**. Baseline após carregar o código: `null`.

## Resultado

**FALHA DE EXECUÇÃO/INTEGRIDADE**. Exit code: `1`; duração: 0.279 s. Registro no SQLite confirmado: `False`; item (hash, tamanho original, tamanho comprimido, bytes do BLOB): `None`; aliases: `None`.

## Saída do CLI

```text
Traceback (most recent call last):
  File "C:\OllamaLimit\Sei l�\Projeto TTC\experimentos TTC\_work\memory_1gb_real__dw6rr5j\invoke_actual_babel_cli.py", line 15, in <module>
    if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(p), p.cb): raise ctypes.WinError()
                                                                                                                        ^^^^^^^^^^^^^^^^^^^^^^^
OSError: [WinError 6] Identificador inv�lido.
```

## Evidência bruta

Veja `memory_1gb_real_result.json`. O teste antigo `test_08_arquivo_1gb_streaming` não foi usado: ele processa 100 MiB, repete um bloco de `A`, comprime apenas 1 MiB e insere diretamente no índice, portanto não percorre o fluxo real do CLI.
