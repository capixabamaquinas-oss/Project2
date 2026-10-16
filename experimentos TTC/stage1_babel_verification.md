# Verificação da etapa 1 — Babel TTC

Data: 2026-10-07. Ambiente: Windows 10 build 19045, Python 3.12.3. Diretório examinado: `C:\OllamaLimit\Sei lá\Projeto TTC\Babel TTC`. Esta pasta não é um repositório Git (`git log` retornou “not a git repository”); os hashes SHA-256 ao final identificam os arquivos examinados nesta auditoria.

## Veredito

A Babel **não está funcional de ponta a ponta**. O caminho simples de adicionar e recuperar 32 bytes passou byte a byte. Falharam importação para pacote novo, integridade do `get` com payload adulterado, estabilidade do endereço com diferentes ordens de inserção e o teste de adição de 1 GB dentro do limite de memória. O `verify` detectou o payload adulterado no caso pequeno.

## Suíte existente

Comando executado:

```powershell
& 'C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe' -B 'C:\OllamaLimit\Sei lá\Projeto TTC\experimentos TTC\run_current_babel_suite.py'
```

Resultado: **14 testes, 0 falhas, 0 erros; OK**. A saída completa está em `stage1_babel_unit_tests.log`. O wrapper mapeia a pasta `Babel TTC` para o nome de pacote `babel` que `test_babel.py` importa. A execução direta `python -B -m unittest -v test_babel` falhou antes dos testes, com `ModuleNotFoundError: No module named 'babel'`.

O teste chamado `test_08_arquivo_1gb_streaming` não testa 1 GB real: `test_babel.py:200` define 100 MiB; `:214` comprime somente um bloco de 1 MiB; e o teste insere diretamente no índice. Por isso, os 14 testes verdes não cobrem adição grande pelo CLI.

## Testes de fluxo real

Comando executado:

```powershell
& 'C:\Users\User PC\AppData\Local\Programs\Python\Python312\python.exe' -B 'C:\OllamaLimit\Sei lá\Projeto TTC\experimentos TTC\run_stage1_babel_integration.py'
```

Dados: arquivo binário de 32 bytes, SHA-256 `ad5ca211e1eed04794516a21574a634c798219028da50235b3b7b29403370d9dab`. Resultado bruto: `stage1_babel_integration_result.json`; conteúdo de teste e bancos ficaram em diretório temporário sob `_work`.

| Verificação | Resultado observado |
| --- | --- |
| CLI `add` seguido de `get` | PASSOU; saída idêntica byte a byte; 1 item no índice |
| Exportar/importar para pacote novo e fazer `get` | FALHOU; import imprimiu “Importados 1”, mas o banco destino ficou com 0 itens e `get` retornou código 1 |
| Payload adulterado seguido de `get` | FALHOU; `get` retornou código 0 e gravou bytes errados |
| Payload adulterado seguido de `verify` | detectado; código 1 |
| Mesmo conteúdo inserido em ordens diferentes | FALHOU; endereços `e8a964a77897568f9cf00fc0dd132399d2869da5020735b3b7b29403370d9dab:0/0/0/0/0` vs `e8a964a77897568f9cf00fc0dd132399d2869da5020735b3b7b29403370d9dab:0/0/0/0/1` |

## Teste real de 1 GB já executado

Relatório: `memory_1gb_real_report.md`; entrada aleatória de 1,000,000,000 bytes, SHA-256 `496f041dfa6aa8c5dfdba034b7a3a9eeeb1a2ba4cf90df7d8348abb5566c1c88`. Pico de working set: 1,011,879,936 bytes; pico pagefile/commit: 1,014,460,416 bytes; limite: 200,000,000 bytes. O CLI terminou com erro `sqlite3.DataError: string or blob too big` em `BabelIndex.add_item`; a inclusão não foi concluída.

## Evidência no código

- `cli.py:44` lê o payload comprimido inteiro com `storage.read`; `storage.py:88` usa `f.read()`. `cli.py:51` passa o objeto `bytes` a `add_item`; `index.py:34` guarda `payload BLOB NOT NULL`.
- `cli.py:81` recupera o payload inteiro; `index.py:92` usa `SELECT *`; `index.py:126` também lista itens com `SELECT *`. `validator.py` usa `list_all` e descomprime payloads inteiros. A memória de `verify` não foi medida.
- `package.py:83` aponta `self.index` para o índice extraído dentro do `TemporaryDirectory`; o teste confirmou que o pacote destino persistente ficou vazio após o retorno.
- `test_babel.py:200,214` explica por que o teste denominado “1 GB” é simulado.

## Limites e identidade do código

Não testei merge ponta a ponta, retry após falha simulada, arquivo malicioso em import, zip slip ou os tamanhos 100/300 MB para add/get. A medição de memória de 1 GB anterior não registrou hashes dos módulos na ocasião; os hashes abaixo identificam o código examinado agora, mas não provam retrospectivamente igualdade byte a byte. Os timestamps dos módulos são anteriores à medição e não há Git neste diretório.

Nenhum arquivo em `Babel TTC` foi editado nesta auditoria. Scripts e resultados estão em `experimentos TTC`; dados de teste ficaram em temporários.

## SHA-256 dos arquivos Python examinados

| Arquivo | SHA-256 |
| --- | --- |
| __init__.py | 22ff7e5cf66e302bdcad100da940e428c9f9206dce6866978c468f2c5ca96984 |
| cli.py | 0d473deee524328751ed7fd12732373e2e2fd0582fb4f68bf353e93f8e56b223 |
| compression.py | 94e6385c61ee2fc58d57e6148e6a945d444ffb9a91a7d936a9ff15e76a3b7ac1 |
| hash_address.py | 2d818d4c1b226480d817d62714f626b24c6c802d5e09f8edc539dd07d23cf7f7 |
| index.py | 60f5a664ecf9e10ef8a3da1475bc7cfa894e5ea0cbcb614ed31cc7df6cf36266 |
| package.py | dbdbe23c863c4cb3ac927e93254b4318c6a1c2145d45df2ea4c9c5fe21822f28 |
| storage.py | 5167334d4f0da142a32f2f8bef8ac47e23334913d94a0843f6bd929e05c1964f |
| test_babel.py | 6e31b93e82d368b5bc47f6b9ffb987fd0ce0439fdd4ed916d964541612ac5428 |
| validator.py | 20e2009eb7454abd7c0de0a937024994f41d53917ba7b73e92ec1ff8a2504ddc |
