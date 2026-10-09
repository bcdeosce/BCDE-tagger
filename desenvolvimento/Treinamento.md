Ordem completa com estimativas
passo	script	entrada	saída	tempo
1	01_unify_datasets.py	2 JSONLs fonte	unified_text.jsonl	~2 min
2	02_reannotate_stanza.py	unified_text.jsonl	unified_stanza.jsonl	~4–5h GPU
3	03_build_tables_split.py	unified_stanza.jsonl	tabelas_v3.json + splits	~5 min
4	04_extract_features.py	splits	features_v2/*.parquet	~10 min
5	05_train_crf.py	parquet	crf_final.pkl + crf_weights.json	~1h20
6	06_train_resolver.py	unified_stanza.jsonl	resolver_v7.json	~5 min
