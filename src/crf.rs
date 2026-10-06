use serde::Deserialize;
use std::collections::HashMap;

#[derive(Deserialize)]
pub struct CrfWeights {
    pub labels: Vec<String>,
    pub trans: Vec<Vec<f64>>,
    pub state: HashMap<String, Vec<(usize, f64)>>,
}

pub struct Crf {
    pub labels: Vec<String>,
    pub trans: Vec<Vec<f64>>,
    pub state: HashMap<String, Vec<(usize, f64)>>,
}

impl Crf {
    pub fn load(path: &str) -> std::io::Result<Self> {
        let data = std::fs::read_to_string(path)?;
        let w: CrfWeights = serde_json::from_str(&data)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        Ok(Self { labels: w.labels, trans: w.trans, state: w.state })
    }

    pub fn predict(&self, feats_per_token: &[Vec<String>]) -> Vec<usize> {
        let n = feats_per_token.len();
        if n == 0 { return vec![]; }
        let l = self.labels.len();

        let mut s = vec![vec![0.0f64; l]; n];
        for (i, feats) in feats_per_token.iter().enumerate() {
            for f in feats {
                if let Some(list) = self.state.get(f) {
                    for &(li, w) in list {
                        s[i][li] += w;
                    }
                }
            }
        }

        let mut v = vec![vec![f64::NEG_INFINITY; l]; n];
        let mut bp = vec![vec![0usize; l]; n];
        for li in 0..l { v[0][li] = s[0][li]; }
        for i in 1..n {
            for li in 0..l {
                let mut best = f64::NEG_INFINITY;
                let mut arg = 0;
                for lj in 0..l {
                    if v[i-1][lj].is_infinite() { continue; }
                    let sc = v[i-1][lj] + self.trans[lj][li];
                    if sc > best { best = sc; arg = lj; }
                }
                v[i][li] = best + s[i][li];
                bp[i][li] = arg;
            }
        }
        let mut path = vec![0usize; n];
        let mut best = f64::NEG_INFINITY;
        for li in 0..l {
            if v[n-1][li] > best { best = v[n-1][li]; path[n-1] = li; }
        }
        for i in (0..n-1).rev() {
            path[i] = bp[i+1][path[i+1]];
        }
        path
    }
}