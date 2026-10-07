use bcde_tagger::Tagger;
use std::io::{self, BufRead, Write};

fn main() -> std::io::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let mut surface = false;
    let mut base = "data".to_string();
    for a in args.iter().skip(1) {
        if a == "--surface" {
            surface = true;
        } else {
            base = a.clone();
        }
    }

    let tagger = Tagger::load(&base)?;
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();

    for line in stdin.lock().lines() {
        let text = line?;
        if text.trim().is_empty() {
            continue;
        }
        let tokens = if surface {
            tagger.tag_surface(&text)
        } else {
            tagger.tag(&text)
        };
        for t in tokens {
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
