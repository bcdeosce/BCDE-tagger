use serde::Deserialize;
use std::collections::HashMap;

#[derive(Deserialize)]
pub struct ResolverFile {
    pub resolver: HashMap<String, HashMap<String, HashMap<String, String>>>,
    pub prior: HashMap<String, String>,
}

pub struct Resolver {
    pub resolver: HashMap<String, HashMap<String, HashMap<String, String>>>,
    pub prior: HashMap<String, String>,
    pub diac_table: HashMap<String, HashMap<String, String>>,
    pub full_fields: usize,
}

impl Resolver {
    pub fn load(resolver_path: &str, diac_path: &str) -> std::io::Result<Self> {
        let rdata = std::fs::read_to_string(resolver_path)?;
        let rf: ResolverFile = serde_json::from_str(&rdata)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        let ddata = std::fs::read_to_string(diac_path)?;
        let raw: HashMap<String, HashMap<String, String>> = serde_json::from_str(&ddata)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        let mut diac_table = HashMap::new();
        for (w, m) in raw {
            diac_table.insert(w.to_lowercase(), m);
        }
        let full_fields = rf.resolver.values().next()
            .and_then(|t| t.get("full"))
            .and_then(|t| t.keys().next())
            .map(|k| k.matches('|').count() + 1)
            .unwrap_or(6);
        Ok(Self { resolver: rf.resolver, prior: rf.prior, diac_table, full_fields })
    }

    pub fn resolve(
        &self,
        word: &str,
        words_l: &[String],
        i: usize,
        upos_ids: &[i32],
    ) -> Option<(String, String, Option<String>)> {
        if !self.diac_table.contains_key(word) { return None; }
        let tbl = self.resolver.get(word)?;

        let prev_w  = if i > 0 { words_l[i-1].as_str() } else { "" };
        let next_w  = if i+1 < words_l.len() { words_l[i+1].as_str() } else { "" };
        let prev2_w = if i > 1 { words_l[i-2].as_str() } else { "" };
        let next2_w = if i+2 < words_l.len() { words_l[i+2].as_str() } else { "" };
        let u       = upos_ids[i];
        let prev_u  = if i > 0 { upos_ids[i-1] } else { -1 };
        let next_u  = if i+1 < words_l.len() { upos_ids[i+1] } else { -1 };

        let fk_full = if self.full_fields == 7 {
            format!("{u}|{prev_w}|{next_w}|{prev_u}|{next_u}|{prev2_w}|{next2_w}")
        } else {
            format!("{u}|{prev_w}|{next_w}|{prev_u}|{next_u}")
        };

        let checks = [
            ("full", fk_full),
            ("pw",   format!("{u}|{prev_w}|{next_w}")),
            ("prev", format!("{u}|{prev_w}")),
            ("next", format!("{u}|{next_w}")),
            ("cls",  format!("{u}|{prev_u}|{next_u}")),
            ("upos", format!("{u}")),
        ];

        for (lvl, key) in checks.iter() {
            if let Some(sub) = tbl.get(*lvl) {
                if let Some(diac) = sub.get(key) {
                    let sense = self.diac_table.get(word)
                        .and_then(|m| m.iter()
                            .find(|(_, d)| d.as_str() == diac.as_str()))
                        .map(|(s, _)| s.clone());
                    return Some((diac.clone(), lvl.to_string(), sense));
                }
            }
        }
        let prior = self.prior.get(word).cloned()
            .unwrap_or_else(|| word.to_string());
        let sense = self.diac_table.get(word)
            .and_then(|m| m.iter().find(|(_, d)| d.as_str() == prior.as_str()))
            .map(|(s, _)| s.clone());
        Some((prior, "prior".to_string(), sense))
    }
}