# ═══════════════════════════════════════════════════════════════════
# 04 — EXTRAÇÃO DE FEATURES
# ═══════════════════════════════════════════════════════════════════
import json, hashlib, time
from pathlib import Path
from collections import Counter, defaultdict
import pyarrow as pa
import pyarrow.parquet as pq

V3 = Path("/content/drive/MyDrive/fonetizador/pipeline/v3")
FEAT_V2 = V3 / "features_v2"
FEAT_V2.mkdir(exist_ok=True, parents=True)

ALL_POS = ["NOUN","PROPN","VERB","AUX","ADJ","ADV","PRON","DET",
           "ADP","CCONJ","SCONJ","NUM","PART","INTJ","PUNCT","SYM","X"]
N_POS = len(ALL_POS)
ID = {p:i for i,p in enumerate(ALL_POS)}

tabelas = json.loads((V3/"tabelas_v3.json").read_text(encoding="utf-8"))
ALWAYS_ANY = {w: p for p, ws in tabelas["always"].items() for w in ws}
AMBIG = {w: set(v) for w, v in tabelas["ambig"].items()}
PRIOR = tabelas["prior"]

W_BUCKETS, SUF_BUCKETS = 1<<18, 1<<14
def h(s, n): return int(hashlib.md5(str(s).encode()).hexdigest()[:8],16) % n

def encode(tokens):
    return [ALWAYS_ANY.get((t.get("text") or "").lower(), "?")
            for t in tokens]

def feat_sentence(tokens, gold_pos):
    n = len(tokens)
    enc = encode(tokens)
    words = [(t.get("text") or "").lower() for t in tokens]
    anchors = [(i, enc[i]) for i in range(n) if enc[i] != "?"]

    pl = [None]*n; last = None
    for i in range(n):
        pl[i] = last
        if gold_pos[i] == "PUNCT": last = i
    pr = [None]*n; nxt = None
    for i in range(n-1,-1,-1):
        pr[i] = nxt
        if gold_pos[i] == "PUNCT": nxt = i

    out = []
    for i in range(n):
        if enc[i] != "?": continue
        w = words[i]
        if not w: continue
        left  = [gold_pos[j] for j in range(max(0,i-3), i)]
        right = [enc[j] for j in range(i+1, min(n,i+4))]
        while len(left)  < 3: left  = ["NONE"] + left
        while len(right) < 3: right = right + ["NONE"]
        al = [(p,po) for p,po in anchors if p < i]
        ar = [(p,po) for p,po in anchors if p > i]
        if al: ap,apos = al[-1]; la_pos,la_d = apos, min(i-ap,6)
        else:  la_pos,la_d = "NONE",-1
        if ar: ap,apos = ar[0]; ra_pos,ra_d = apos, min(ap-i,6)
        else:  ra_pos,ra_d = "NONE",-1
        prw = PRIOR.get(w, {})
        pmax = max(prw.values()) if prw else 0.0
        parg = max(prw, key=prw.get) if prw else "NONE"
        cm = 0
        if w in AMBIG:
            for p in AMBIG[w]: cm |= 1 << ID[p]
        elif prw:
            for p in prw: cm |= 1 << ID[p]
        else:
            cm = (1<<N_POS)-1
        def po(v):
            if v == "?":    return -2
            if v == "NONE": return -1
            return ID.get(v, -1)
        out.append({
            "word":         w,
            "prev1_w":      words[i-1] if i>0 else "",
            "next1_w":      words[i+1] if i+1<n else "",
            "prev2_w":      words[i-2] if i>1 else "",
            "next2_w":      words[i+2] if i+2<n else "",
            "w_bucket":     h(w, W_BUCKETS),
            "suf3_bucket":  h(w[-3:], SUF_BUCKETS),
            "suf2_bucket":  h(w[-2:], SUF_BUCKETS),
            "suf1_bucket":  h(w[-1:], SUF_BUCKETS),
            "len":          min(len(w),15),
            "cap":          int(tokens[i]["text"][:1].isupper()),
            "prior_argmax": ID.get(parg,-1),
            "prior_max":    pmax,
            "c_prev1": po(left[-1]), "c_prev2": po(left[-2]), "c_prev3": po(left[-3]),
            "c_next1": po(right[0]), "c_next2": po(right[1]), "c_next3": po(right[2]),
            "left_anchor_pos":   ID.get(la_pos,-1),
            "left_anchor_dist":  la_d,
            "right_anchor_pos":  ID.get(ra_pos,-1),
            "right_anchor_dist": ra_d,
            "n_anchors_left":    min(len(al),6),
            "n_anchors_right":   min(len(ar),6),
            "prev_w_bucket": h(words[i-1],W_BUCKETS) if i>0 else 0,
            "next_w_bucket": h(words[i+1],W_BUCKETS) if i+1<n else 0,
            "prev2_w_bucket": h(words[i-2],W_BUCKETS) if i>1 else 0,
            "next2_w_bucket": h(words[i+2],W_BUCKETS) if i+2<n else 0,
            "is_first": int(i==0),
            "is_last":  int(i==n-1),
            "dist_punct_left":  (min(i-pl[i],6) if pl[i] is not None else -1),
            "dist_punct_right": (min(pr[i]-i,6) if pr[i] is not None else -1),
            "cands_mask":   cm,
            "target":       ID.get(gold_pos[i],-1),
        })
    return out

def extract(split):
    path = V3 / f"{split}.jsonl"
    out_path = FEAT_V2 / f"{split}.parquet"
    writer = None; n_sent = n_ex = 0; sid = 0
    t0 = time.time()
    with open(path, encoding="utf-8") as f:
        batch = []
        for line in f:
            try: r = json.loads(line)
            except: continue
            toks = r.get("tokens", [])
            if not toks: continue
            gold = [t.get("upos","X") for t in toks]
            ex = feat_sentence(toks, gold)
            for e in ex: e["sent_id"] = sid
            batch.extend(ex); n_sent += 1; n_ex += len(ex); sid += 1
            if len(batch) >= 200_000:
                t = pa.Table.from_pylist(batch)
                if writer is None:
                    writer = pq.ParquetWriter(out_path, t.schema, compression="zstd")
                writer.write_table(t); batch = []
                if n_sent % 200_000 < 1:
                    print(f"  {n_sent:,} sent  {n_ex:,} ex", flush=True)
        if batch:
            t = pa.Table.from_pylist(batch)
            if writer is None:
                writer = pq.ParquetWriter(out_path, t.schema, compression="zstd")
            writer.write_table(t)
    if writer: writer.close()
    print(f"[{split}] sent={n_sent:,} ex={n_ex:,} em {time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    for s in ("train","val","test"):
        print(f"\n[{s}]", flush=True)
        extract(s)
    print("\n✓ DONE")
