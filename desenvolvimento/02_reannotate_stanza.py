# ═══════════════════════════════════════════════════════════════════
# 02 — RE-ANOTAÇÃO COM STANZA
# ═══════════════════════════════════════════════════════════════════
import json, time, os
from pathlib import Path
import stanza

PIPE = Path("/content/drive/MyDrive/fonetizador/pipeline")
IN   = PIPE / "unified_text.jsonl"
OUT  = PIPE / "unified_stanza.jsonl"
PROG = PIPE / "unified_progress.json"

BATCH_SIZE = 256
CHECKPOINT_EVERY = 20_000

def build_pipeline():
    use_gpu = os.environ.get("STANZA_GPU", "1") == "1"
    print(f"[stanza] GPU={use_gpu}", flush=True)
    return stanza.Pipeline(
        "pt",
        processors="tokenize,pos,lemma,depparse",
        use_gpu=use_gpu,
        tokenize_batch_size=BATCH_SIZE,
        pos_batch_size=BATCH_SIZE,
        lemma_batch_size=BATCH_SIZE,
        depparse_batch_size=BATCH_SIZE,
        verbose=False,
    )

def processar_batch(nlp, batch):
    textos = [b["text"] for b in batch]
    docs = nlp([stanza.Document([], text=t) for t in textos])
    resultado = []
    for b, doc in zip(batch, docs):
        toks = []
        for sent in doc.sentences:
            for w in sent.words:
                toks.append({
                    "id": w.id, "text": w.text, "lemma": w.lemma,
                    "upos": w.upos, "xpos": w.xpos, "feats": w.feats,
                    "head": w.head, "deprel": w.deprel,
                })
        resultado.append({
            "h": b["h"], "src": b["src"], "text": b["text"],
            "senses": b["senses"], "tokens": toks,
        })
    return resultado

def main():
    done = 0
    if PROG.exists():
        try: done = json.loads(PROG.read_text())["done"]
        except: done = 0
    print(f"[stanza] retomando de {done:,}", flush=True)

    nlp = build_pipeline()
    mode = "a" if done > 0 else "w"
    t0 = time.time()
    n_proc = done
    n_tokens_total = 0

    with open(IN, encoding="utf-8") as fin, \
         open(OUT, mode, encoding="utf-8") as fout:

        for _ in range(done):
            next(fin, None)

        batch = []
        for line in fin:
            try: r = json.loads(line)
            except: continue
            batch.append(r)
            if len(batch) < BATCH_SIZE: continue

            anotados = processar_batch(nlp, batch)
            for a in anotados:
                fout.write(json.dumps(a, ensure_ascii=False) + "\n")
                n_tokens_total += len(a["tokens"])
            n_proc += len(batch)
            batch = []

            if n_proc % CHECKPOINT_EVERY < BATCH_SIZE:
                dt = time.time() - t0
                rate = (n_proc - done) / dt if dt > 0 else 0
                eta_min = (2_203_617 - n_proc) / rate / 60 if rate > 0 else 0
                print(f"  {n_proc:,} ({rate:.1f} sent/s, ETA {eta_min:.1f} min)",
                      flush=True)
                PROG.write_text(json.dumps({"done": n_proc}))
                fout.flush()

        if batch:
            anotados = processar_batch(nlp, batch)
            for a in anotados:
                fout.write(json.dumps(a, ensure_ascii=False) + "\n")
                n_tokens_total += len(a["tokens"])
            n_proc += len(batch)
            PROG.write_text(json.dumps({"done": n_proc}))

    print(f"[stanza] processado={n_proc:,}  tokens={n_tokens_total:,}")

if __name__ == "__main__":
    main()
