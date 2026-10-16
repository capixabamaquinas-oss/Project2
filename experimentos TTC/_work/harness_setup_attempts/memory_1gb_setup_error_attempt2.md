# Teste real de memória — inserção de arquivo de 1 GB na Babel

Data/hora: 2026-10-06T22:47:10-03:00  
Máquina: Windows-10-10.0.19045-SP0  
Python: 3.12.3 (`C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe`)

## Caminho executado

`Babel TTC/cli.py:main → cmd_add → LocalDiskStorage.store_file_streaming → storage.read → BabelIndex.add_item`

O teste chama o CLI atual em processo filho isolado. O arquivo de entrada tem 1.000.000.000 bytes (1 GB decimal), foi gravado antes da medição em blocos de 1 MiB com `os.urandom`; SHA-256: `6ac8a143539d7ebed968d4be22070326cc974b336f6c26ca57e2c5787b33942d`. A fonte e o pacote SQLite ficam em diretório temporário em `experimentos TTC/_work` e são removidos após a medição.

## Comando

`& 'C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe' 'experimentos TTC/memory_1gb_real_test.py' --babel-dir 'Babel TTC' --experiment-dir 'experimentos TTC'`

## Critério e medição

Critério previamente adotado: **FALHA se o pico do working set ou o pico de pagefile/commit for ≥ 200.000.000 bytes (200 MB decimais)**. Memória do processo medida por `GetProcessMemoryInfo` no Windows, consultada em intervalos de 50 ms e novamente após o processo terminar, enquanto o handle ainda estava aberto. Pico working set: **18,530,304 bytes (18.53 MB)**. Pico pagefile/commit: **11,862,016 bytes (11.86 MB)**. Baseline após carregar o código: `{"working_set_bytes": 18059264, "private_bytes": 11591680}`.

## Resultado

**FALHA DE EXECUÇÃO/INTEGRIDADE**. Exit code: `1`; duração: 2.454 s. Registro no SQLite confirmado: `False`; item (hash, tamanho original, tamanho comprimido, bytes do BLOB): `None`; aliases: `None`.

## Saída do CLI

```text
Traceback (most recent call last):
  File "C:\OllamaLimit\Sei l�\Projeto TTC\experimentos TTC\_work\memory_1gb_real_ve3_f5qy\invoke_actual_babel_cli.py", line 24, in <module>
    cli.main()
  File "C:\OllamaLimit\Sei l�\Projeto TTC\Babel TTC\cli.py", line 182, in main
    commands[args.command](args)
  File "C:\OllamaLimit\Sei l�\Projeto TTC\Babel TTC\cli.py", line 21, in cmd_add
    pkg.open()
  File "C:\OllamaLimit\Sei l�\Projeto TTC\Babel TTC\package.py", line 29, in open
    raise FileNotFoundError(f"Pacote n�o encontrado: {self.package_path}")
FileNotFoundError: Pacote n�o encontrado: C:\OllamaLimit\Sei l�\Projeto TTC\experimentos TTC\_work\memory_1gb_real_ve3_f5qy\babel.sqlite
```

## Evidência bruta

Veja `memory_1gb_real_result.json`. O teste antigo `test_08_arquivo_1gb_streaming` não foi usado: ele processa 100 MiB, repete um bloco de `A`, comprime apenas 1 MiB e insere diretamente no índice, portanto não percorre o fluxo real do CLI.
