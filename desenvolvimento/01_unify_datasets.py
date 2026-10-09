# ═══════════════════════════════════════════════════════════════════
# 01 — UNIFICAÇÃO DOS DATASETS
# ═══════════════════════════════════════════════════════════════════
import json, hashlib, time
from pathlib import Path

PIPE = Path("/content/drive/MyDrive/datasets/")

DS1 = PIPE / "base" / "dataset_final.jsonl"
DS2 = PIPE / "bifonia" / "dataset_final_bifonia.jsonl"
OUT = PIPE / "BCDE-tagger" /"unified_text.jsonl"

def extrair_sentencas(path, tag):
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except: continue
            toks = r.get("tokens_pos") or r.get("tokens") or []
            if not toks: continue
            texts = [(t.get("text") or "") for t in toks]
            if not any(texts): continue

            senses = []
            for a in (r.get("anotacoes") or []):
                idx = a.get("idx_token")
                s = a.get("sentido_bifonia") or a.get("sentido")
                if idx is not None and s and 0 <= idx < len(texts):
                    senses.append({"idx": idx, "w": texts[idx], "sense": s})

            n += 1
            yield {"text": " ".join(texts), "src": tag, "senses": senses}

def main():
    if OUT.exists():
        n = sum(1 for _ in open(OUT, encoding="utf-8"))
        print(f"[unified] já existe ({n:,} linhas) → pulando")
        return

    seen = set()
    n_written = n_skipped = n_senses = 0
    t0 = time.time()

    with open(OUT, "w", encoding="utf-8") as out:
        for path, tag in [(DS1, "ds1"), (DS2, "ds2")]:
            print(f"[unified] lendo {tag}...", flush=True)
            for sent in extrair_sentencas(path, tag):
                h = hashlib.md5(sent["text"].encode("utf-8")).hexdigest()
                if h in seen:
                    n_skipped += 1
                    continue
                seen.add(h)
                sent["h"] = h
                if sent["senses"]:
                    n_senses += 1
                out.write(json.dumps(sent, ensure_ascii=False) + "\n")
                n_written += 1
                if n_written % 200_000 == 0:
                    dt = time.time() - t0
                    print(f"  written={n_written:,} skipped={n_skipped:,} "
                          f"senses={n_senses:,} ({dt:.1f}s)", flush=True)

    print(f"[unified] total={n_written:,}  pulado={n_skipped:,}  "
          f"com sentidos={n_senses:,}")

if __name__ == "__main__":
    main()
