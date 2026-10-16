# Teste real de memória — inserção de arquivo de 1 GB na Babel

Data/hora: 2026-10-06T22:47:58-03:00  
Máquina: Windows-10-10.0.19045-SP0  
Python: 3.12.3 (`C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe`)

## Caminho executado

`BabelPackage.create (pacote vazio) → Babel TTC/cli.py:main → cmd_add → LocalDiskStorage.store_file_streaming → storage.read → BabelIndex.add_item`

O teste chama o CLI atual em processo filho isolado. O arquivo de entrada tem 1.000.000.000 bytes (1 GB decimal), foi gravado antes da medição em blocos de 1 MiB com `os.urandom`; SHA-256: `496f041dfa6aa8c5dfdba034b7a3a9eeeb1a2ba4cf90df7d8348abb5566c1c88`. A fonte e o pacote SQLite ficam em diretório temporário em `experimentos TTC/_work` e são removidos após a medição.

## Comando

`& 'C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe' 'experimentos TTC/memory_1gb_real_test.py' --babel-dir 'Babel TTC' --experiment-dir 'experimentos TTC'`

## Critério e medição

Critério previamente adotado: **FALHA se o pico do working set ou o pico de pagefile/commit for ≥ 200.000.000 bytes (200 MB decimais)**. Memória do processo medida por `GetProcessMemoryInfo` no Windows, consultada em intervalos de 50 ms e novamente após o processo terminar, enquanto o handle ainda estava aberto. Pico working set: **1,011,879,936 bytes (1011.88 MB)**. Pico pagefile/commit: **1,014,460,416 bytes (1014.46 MB)**. Baseline após carregar o código: `{"working_set_bytes": 18841600, "private_bytes": 11677696}`.

## Resultado

**FALHA**. O pico do working set foi 1.011.879.936 bytes (1,0119× o arquivo e 5,0594× o limite), 993.038.336 bytes acima do baseline de working set. O pico pagefile/commit foi 1.014.460.416 bytes (5,0723× o limite). Ambos excedem 200.000.000 bytes. Exit code: `1`; duração: 47,208 s.

A operação não concluiu a inclusão: após a leitura completa do payload comprimido, a inserção no SQLite em `BabelIndex.add_item` falhou com `sqlite3.DataError: string or blob too big`. O hash/tamanho de entrada foram calculados; não há item nem alias no índice final. Assim, o teste registra falha do caminho de armazenamento por pico de memória acima do critério e por rejeição do BLOB pelo SQLite.

## Saída do CLI

```text
Traceback (most recent call last):
  File "C:\OllamaLimit\Sei lá\Projeto TTC\experimentos TTC\_work\memory_1gb_real_psles6kz\invoke_actual_babel_cli.py", line 27, in <module>
    cli.main()
  File "C:\OllamaLimit\Sei lá\Projeto TTC\Babel TTC\cli.py", line 182, in main
    commands[args.command](args)
  File "C:\OllamaLimit\Sei lá\Projeto TTC\Babel TTC\cli.py", line 51, in cmd_add
    pkg.index.add_item(
  File "C:\OllamaLimit\Sei lá\Projeto TTC\Babel TTC\index.py", line 61, in add_item
    conn.execute("""
sqlite3.DataError: string or blob too big
```

## Integridade e escopo

O código e os arquivos em `Babel TTC` não foram alterados. O import ocorreu com gravação de bytecode desativada. O arquivo de entrada, o SQLite de teste e os payloads temporários foram removidos ao terminar.

## Evidência bruta

Veja `memory_1gb_real_result.json`. O teste antigo `test_08_arquivo_1gb_streaming` não foi usado: ele processa 100 MiB, repete um bloco de `A`, comprime apenas 1 MiB e insere diretamente no índice, portanto não percorre o fluxo real do CLI.
