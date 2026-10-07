use once_cell::sync::Lazy;
use regex::Regex;
use std::collections::{HashMap, HashSet};

pub(crate) static PAT: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"d'|\w+(?:[-']\w+)*|[^\w\s]").unwrap()
});

static MWT: Lazy<HashMap<&'static str, Vec<&'static str>>> = Lazy::new(|| {
    let mut m = HashMap::new();
    m.insert("do", vec!["de","o"]); m.insert("da", vec!["de","a"]);
    m.insert("dos", vec!["de","os"]); m.insert("das", vec!["de","as"]);
    m.insert("no", vec!["em","o"]); m.insert("na", vec!["em","a"]);
    m.insert("nos", vec!["em","os"]); m.insert("nas", vec!["em","as"]);
    m.insert("pelo", vec!["por","o"]); m.insert("pela", vec!["por","a"]);
    m.insert("pelos", vec!["por","os"]); m.insert("pelas", vec!["por","as"]);
    m.insert("ao", vec!["a","o"]); m.insert("à", vec!["a","a"]);
    m.insert("aos", vec!["a","os"]); m.insert("às", vec!["a","as"]);
    m.insert("dum", vec!["de","um"]); m.insert("duma", vec!["de","uma"]);
    m.insert("duns", vec!["de","uns"]); m.insert("dumas", vec!["de","umas"]);
    m.insert("num", vec!["em","um"]); m.insert("numa", vec!["em","uma"]);
    m.insert("nuns", vec!["em","uns"]); m.insert("numas", vec!["em","umas"]);
    m.insert("deste", vec!["de","este"]); m.insert("desta", vec!["de","esta"]);
    m.insert("destes", vec!["de","estes"]); m.insert("destas", vec!["de","estas"]);
    m.insert("desse", vec!["de","esse"]); m.insert("dessa", vec!["de","essa"]);
    m.insert("desses", vec!["de","esses"]); m.insert("dessas", vec!["de","essas"]);
    m.insert("neste", vec!["em","este"]); m.insert("nesta", vec!["em","esta"]);
    m.insert("nestes", vec!["em","estes"]); m.insert("nestas", vec!["em","estas"]);
    m.insert("nesse", vec!["em","esse"]); m.insert("nessa", vec!["em","essa"]);
    m.insert("nesses", vec!["em","esses"]); m.insert("nessas", vec!["em","essas"]);
    m.insert("naquele", vec!["em","aquele"]); m.insert("naquela", vec!["em","aquela"]);
    m.insert("naqueles", vec!["em","aqueles"]); m.insert("naquelas", vec!["em","aquelas"]);
    m.insert("naquilo", vec!["em","aquilo"]);
    m.insert("àquele", vec!["a","aquele"]); m.insert("àquela", vec!["a","aquela"]);
    m.insert("àqueles", vec!["a","aqueles"]); m.insert("àquelas", vec!["a","aquelas"]);
    m.insert("àquilo", vec!["a","aquilo"]);
    m.insert("disto", vec!["de","isto"]); m.insert("disso", vec!["de","isso"]);
    m.insert("daquilo", vec!["de","aquilo"]);
    m.insert("nisso", vec!["em","isso"]); m.insert("nisto", vec!["em","isto"]);
    m.insert("daqui", vec!["de","aqui"]); m.insert("dali", vec!["de","ali"]);
    m.insert("dacolá", vec!["de","acolá"]); m.insert("daí", vec!["de","aí"]);
    m.insert("vos", vec!["v","os"]);
    m
});

/// MWT ambíguas — também existem como palavra única (NOUN/VERB).
/// Só expandimos quando o contexto indica contração.
static MWT_AMBIGUAS: Lazy<HashSet<&'static str>> = Lazy::new(|| {
    ["pelo","pela","pelos","pelas"].into_iter().collect()
});

/// Palavras funcionais — se a próxima é uma delas, `pelo` não é contração.
static FUNCIONAIS: Lazy<HashSet<&'static str>> = Lazy::new(|| {
    [
        "a","o","as","os","um","uma","uns","umas",
        "de","do","da","dos","das","em","no","na","nos","nas",
        "por","pelo","pela","pelos","pelas","com","sem","para",
        "que","se","como","quando","onde","porque","pois",
        "e","ou","mas","porém","contudo","todavia","entretanto",
        "não","sim","muito","mais","menos","também","só","já","ainda",
        "eu","tu","ele","ela","nós","vós","você","vocês","eles","elas",
        "me","te","lhe","nos","vos","se","mim","ti","si","lhe",
        "este","esta","estes","estas","esse","essa","esses","essas",
        "aquele","aquela","aqueles","aquelas","isso","isto","aquilo",
    ].into_iter().collect()
});

static SUJEITOS: Lazy<HashSet<&'static str>> = Lazy::new(|| {
    ["eu","tu","ele","ela","nós","vós","você","vocês","eles","elas"]
        .into_iter().collect()
});

const VERB_SUFIXOS: &[&str] = &[
    "ar","er","ir","or","ou","eu","iu","am","em","ão",
    "ei","as","es","is","mos","ram","rem","sse","ria",
    "rei","ra","va","nha","do","da","to","ta",
];

fn next_verb(tok: &str) -> bool {
    let t = tok.to_lowercase();
    if t.chars().count() < 3 { return false; }
    VERB_SUFIXOS.iter().any(|s| t.ends_with(s))
}

fn prev_sujeito(surface: &[&str], i: usize) -> bool {
    if i == 0 { return false; }
    SUJEITOS.contains(surface[i-1].to_lowercase().as_str())
}

/// Heurística: expandir `pelo` só quando o próximo parece nome.
fn deve_expandir_ambigua(surface: &[&str], i: usize) -> bool {
    if i + 1 >= surface.len() { return false; }
    let next = surface[i+1].to_lowercase();
    if FUNCIONAIS.contains(next.as_str()) { return false; }
    if next.chars().count() > 3 && VERB_SUFIXOS.iter().any(|s| next.ends_with(s)) {
        return false;
    }
    true
}

fn decide(surface: &[&str], i: usize) -> (bool, bool) {
    // retorna (expandir, manter_surface)
    let low = surface[i].to_lowercase();
    if !MWT.contains_key(low.as_str()) {
        return (false, true); // não é MWT, mantém
    }
    // nos/vos: pronome se prev é sujeito ou next é verbo
    if low == "nos" || low == "vos" {
        if prev_sujeito(surface, i)
            || (i+1 < surface.len() && next_verb(surface[i+1])) {
            return (false, true);
        }
    }
    // pelo/pela/pelos/pelas: só expande se next parece nome
    if MWT_AMBIGUAS.contains(low.as_str()) {
        if !deve_expandir_ambigua(surface, i) {
            return (false, true);
        }
    }
    // qualquer outra MWT: expande
    if prev_sujeito(surface, i) {
        return (false, true);
    }
    (true, false)
}

pub fn tokenize_mwt(text: &str) -> Vec<String> {
    let surface: Vec<&str> = PAT.find_iter(text).map(|m| m.as_str()).collect();
    let mut out = Vec::with_capacity(surface.len());
    for i in 0..surface.len() {
        let (expandir, manter) = decide(&surface, i);
        if manter {
            out.push(surface[i].to_string());
        } else if expandir {
            let exp = MWT.get(surface[i].to_lowercase().as_str()).unwrap();
            out.extend(exp.iter().map(|s| s.to_string()));
        }
    }
    out
}

pub fn tokenize_mwt_with_spans(text: &str) -> (Vec<String>, Vec<(usize, usize)>) {
    let surface: Vec<&str> = PAT.find_iter(text).map(|m| m.as_str()).collect();
    let mut tokens: Vec<String> = Vec::new();
    let mut spans: Vec<(usize, usize)> = Vec::new();
    for i in 0..surface.len() {
        let start = tokens.len();
        let (expandir, manter) = decide(&surface, i);
        if manter {
            tokens.push(surface[i].to_string());
        } else if expandir {
            let exp = MWT.get(surface[i].to_lowercase().as_str()).unwrap();
            tokens.extend(exp.iter().map(|s| s.to_string()));
        }
        spans.push((start, tokens.len()));
    }
    (tokens, spans)
}
