use bcde_tagger::Tagger;
use std::io::{self, BufRead, Write};

fn main() -> std::io::Result<()> {
    let base = std::env::args().nth(1).unwrap_or_else(|| "data".to_string());
    let tagger = Tagger::load(&base)?;
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();
    for line in stdin.lock().lines() {
        let text = line?;
        if text.trim().is_empty() { continue; }
        for t in tagger.tag(&text) {
            let extra = match (&t.diacritic, &t.sense, &t.resolver_level) {
                (Some(d), Some(s), Some(l)) => format!("\tdiac={d}\tsense={s}\tvia={l}"),
                (Some(d), _, _) => format!("\tdiac={d}"),
                _ => String::new(),
            };
            writeln!(out, "{}\t{}{}", t.word, t.upos, extra)?;
        }
        writeln!(out)?;
    }
    Ok(())
}
