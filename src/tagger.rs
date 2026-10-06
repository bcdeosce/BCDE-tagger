use std::collections::HashMap;
use std::path::Path;
use serde::Deserialize;
use crate::crf::Crf;
use crate::resolver::Resolver;
use crate::tokenizer::tokenize_mwt;

// ─── Ordem EXATA usada no treino Python ───
pub const ALL_POS: &[&str] = &[
    "NOUN","PROPN","VERB","AUX","ADJ","ADV","PRON","DET",
    "ADP","CCONJ","SCONJ","NUM","PART","INTJ","PUNCT","SYM","X",
];

#[derive(Deserialize)]
struct TabFile {
    always: HashMap<String, Vec<String>>,
    ambig: HashMap<String, Vec<String>>,
    prior: HashMap<String, HashMap<String, f64>>,
}

pub struct Tagger {
    pub always: HashMap<String, u8>,
    pub ambig: HashMap<String, Vec<u8>>,
    pub prior: HashMap<String, Vec<(u8, f64)>>,
    pub crf: Crf,
    pub resolver: Resolver,
    // mapeia índice de crf.labels → índice em ALL_POS
    pub crf_to_allpos: Vec<u8>,
}

#[derive(Debug)]
pub struct Token {
    pub word: String,
    pub upos: String,
    pub diacritic: Option<String>,
    pub sense: Option<String>,
    pub resolver_level: Option<String>,
}

impl Tagger {
    pub fn load(base: &str) -> std::io::Result<Self> {
        let p = Path::new(base);
        let crf = Crf::load(p.join("crf_weights.json").to_str().unwrap())?;

        // pos_idx em ordem ALL_POS (como o Python treinou)
        let pos_idx: HashMap<&str, u8> = ALL_POS.iter()
            .enumerate().map(|(i, p)| (*p, i as u8)).collect();

        // mapeia cada label do CRF pro índice em ALL_POS
        let crf_to_allpos: Vec<u8> = crf.labels.iter()
            .map(|l| *pos_idx.get(l.as_str()).unwrap_or(&0))
            .collect();

        let tab_raw = std::fs::read_to_string(p.join("tabelas_v3.json"))?;
        let tab: TabFile = serde_json::from_str(&tab_raw)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;

        let mut always = HashMap::new();
        for (pos, ws) in &tab.always {
            if let Some(&idx) = pos_idx.get(pos.as_str()) {
                for w in ws { always.insert(w.clone(), idx); }
            }
        }
        let mut ambig = HashMap::new();
        for (w, ps) in &tab.ambig {
            let ids: Vec<u8> = ps.iter()
                .filter_map(|p| pos_idx.get(p.as_str()).copied()).collect();
            ambig.insert(w.clone(), ids);
        }
        let mut prior: HashMap<String, Vec<(u8, f64)>> = HashMap::new();
        for (w, m) in &tab.prior {
            let v: Vec<(u8, f64)> = m.iter()
                .filter_map(|(p, &v)| pos_idx.get(p.as_str()).map(|&i| (i, v)))
                .collect();
            prior.insert(w.clone(), v);
        }

        let resolver = Resolver::load(
            p.join("resolver_v7.json").to_str().unwrap(),
            p.join("diacriticos_table.json").to_str().unwrap(),
        )?;

        Ok(Self { always, ambig, prior, crf, resolver, crf_to_allpos })
    }

    pub fn tag(&self, text: &str) -> Vec<Token> {
        let tokens = tokenize_mwt(text);
        if tokens.is_empty() { return vec![]; }
        let words_l: Vec<String> = tokens.iter().map(|t| t.to_lowercase()).collect();
        let n = tokens.len();

        // -2 = ambíguo (buraco). Senão, índice em ALL_POS.
        let mut enc: Vec<i32> = (0..n)
            .map(|i| self.always.get(&words_l[i]).map(|&x| x as i32).unwrap_or(-2))
            .collect();

        let amb_idx: Vec<usize> = (0..n).filter(|&i| enc[i] == -2).collect();

        if !amb_idx.is_empty() {
            let anchors: Vec<(usize, i32)> = (0..n)
                .filter(|&i| enc[i] != -2)
                .map(|i| (i, enc[i]))
                .collect();

            let feats_all: Vec<Vec<String>> = amb_idx.iter()
                .map(|&i| self.extract_features(&tokens, &words_l, i, &enc, &anchors))
                .collect();

            let preds = self.crf.predict(&feats_all);
            // Converte saída do CRF (índice em crf.labels) → índice em ALL_POS
            for (k, &i) in amb_idx.iter().enumerate() {
                enc[i] = self.crf_to_allpos[preds[k]] as i32;
            }
        }

        let mut out = Vec::with_capacity(n);
        for i in 0..n {
            let upos = ALL_POS[enc[i] as usize].to_string();
            let mut tok = Token {
                word: tokens[i].clone(),
                upos,
                diacritic: None, sense: None, resolver_level: None,
            };
            if let Some((d, lvl, sense)) = self.resolver.resolve(&words_l[i], &words_l, i, &enc) {
                tok.diacritic = Some(d);
                tok.resolver_level = Some(lvl);
                tok.sense = sense;
            }
            out.push(tok);
        }
        out
    }

    fn extract_features(
        &self,
        tokens: &[String],
        words_l: &[String],
        i: usize,
        enc: &[i32],
        anchors: &[(usize, i32)],
    ) -> Vec<String> {
        let w = &words_l[i];
        let w_raw = &tokens[i];
        let n = tokens.len();
        let mut f = Vec::with_capacity(50);

        let cp = |k: usize| -> i32 { if i < k { -1 } else { enc[i - k] } };
        let cn = |k: usize| -> i32 { if i + k >= n { -1 } else { enc[i + k] } };

        let al: Vec<&(usize, i32)> = anchors.iter().filter(|(p, _)| *p < i).collect();
        let ar: Vec<&(usize, i32)> = anchors.iter().filter(|(p, _)| *p > i).collect();
        let (la_pos, la_d) = match al.last() {
            Some(&&(p, pos)) => (pos, (i - p).min(6) as i32),
            None => (-1, -1),
        };
        let (ra_pos, ra_d) = match ar.first() {
            Some(&&(p, pos)) => (pos, (p - i).min(6) as i32),
            None => (-1, -1),
        };

        let (pmax, parg) = match self.prior.get(w) {
            Some(v) => {
                let mut best = (-1i32, 0.0f64);
                for &(li, sc) in v { if sc > best.1 { best = (li as i32, sc); } }
                (best.1, best.0)
            }
            None => (0.0, -1),
        };
        let cm: i64 = match self.ambig.get(w) {
            Some(ids) => ids.iter().fold(0i64, |acc, &x| acc | (1i64 << x)),
            None => match self.prior.get(w) {
                Some(v) => v.iter().fold(0i64, |acc, &(x, _)| acc | (1i64 << x)),
                None => (1i64 << ALL_POS.len()) - 1,
            },
        };

        let chars_w: Vec<char> = w.chars().collect();
        let len_c = chars_w.len();
        let s1: String = if len_c >= 1 { chars_w[len_c-1..].iter().collect() } else { String::new() };
        let s2: String = if len_c >= 2 { chars_w[len_c-2..].iter().collect() } else { w.clone() };
        let s3: String = if len_c >= 3 { chars_w[len_c-3..].iter().collect() } else { w.clone() };

        let p1 = if i > 0 { words_l[i-1].as_str() } else { "" };
        let n1 = if i+1 < n { words_l[i+1].as_str() } else { "" };
        let p2 = if i > 1 { words_l[i-2].as_str() } else { "" };
        let n2 = if i+2 < n { words_l[i+2].as_str() } else { "" };

        f.push(format!("w={w}"));
        f.push(format!("s3={s3}"));
        f.push(format!("s2={s2}"));
        f.push(format!("s1={s1}"));
        f.push(format!("p1={p1}"));
        f.push(format!("n1={n1}"));
        f.push(format!("p2={p2}"));
        f.push(format!("n2={n2}"));
        f.push(format!("len={}", len_c.min(15)));
        let cap = if w_raw.chars().next().map(|c| c.is_uppercase()).unwrap_or(false) { 1 } else { 0 };
        f.push(format!("cap={cap}"));
        f.push(format!("pa={parg}"));
        f.push(format!("pmax={}", (pmax * 10.0) as i32));
        f.push(format!("cp1={}", cp(1)));
        f.push(format!("cp2={}", cp(2)));
        f.push(format!("cp3={}", cp(3)));
        f.push(format!("cn1={}", cn(1)));
        f.push(format!("cn2={}", cn(2)));
        f.push(format!("cn3={}", cn(3)));
        f.push(format!("lap={la_pos}"));
        f.push(format!("lad={la_d}"));
        f.push(format!("rap={ra_pos}"));
        f.push(format!("rad={ra_d}"));
        f.push(format!("nal={}", al.len().min(6)));
        f.push(format!("nar={}", ar.len().min(6)));
        f.push(format!("ifl={}", if i == 0 { 1 } else { 0 }));
        f.push(format!("isl={}", if i == n-1 { 1 } else { 0 }));
        f.push("dpl=-1".to_string());
        f.push("dpr=-1".to_string());
        f.push(format!("cm={cm}"));
        f.push(format!("w|cp1={w}|{}", cp(1)));
        f.push(format!("w|cn1={w}|{}", cn(1)));
        f.push(format!("w|cm={w}|{cm}"));
        f.push(format!("cp1|cn1={}|{}", cp(1), cn(1)));
        f.push(format!("s2|cp1={s2}|{}", cp(1)));
        f.push(format!("s2|cn1={s2}|{}", cn(1)));
        f.push(format!("pa|cp1={parg}|{}", cp(1)));
        f
    }
}
