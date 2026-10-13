# Pipeline de Treino — BCDE-tagger

Ordem de execução dos scripts que constroem o modelo do zero.

## Ordem

1. **`01_unify_datasets.py`** — lê os dois JSONLs brutos, extrai texto e sentidos anotados, remove duplicatas por hash. Saída: `unified_text.jsonl`.

2. **`02_reannotate_stanza.py`** — roda Stanza (tokenize, POS, lemma, deps) sobre cada texto. Saída: `unified_stanza.jsonl`. É o passo mais lento (~5 h em GPU).

3. **`03_build_tables_split.py`** — constrói as tabelas `always`/`never`/`prior`/`ambig` e divide o corpus em train/val/test (90/5/5). Saídas: `tabelas_v3.json`, `train.jsonl`, `val.jsonl`, `test.jsonl`.

4. **`04_extract_features.py`** — extrai 45 features por token ambíguo. Saídas: `features_v2/train.parquet`, `val.parquet`, `test.parquet`.

5. **`05_train_crf.py`** — treina o CRF linear e exporta os pesos para o Rust. Saídas: `crf_final.pkl` (Python) e `crf_weights.json` (Rust).

6. **`06_train_resolver.py`** — treina o resolver de diacríticos com backoff de 7 níveis. Saída: `resolver_v7.json`.

## Produto final

Os 4 arquivos que vão para `data/` do repositório Rust:

- `tabelas_v3.json` (passo 3)
- `crf_weights.json` (passo 5)
- `resolver_v7.json` (passo 6)
- `diacriticos_table.json` (curado manualmente)

## Observação

Os passos 1, 2 e 3 são sequenciais. Depois do 3, os passos 4, 5 e 6 podem rodar em paralelo. O passo 5 depende do 4; o 6 depende só do 2.
