use bcde_tagger::Tagger;
use std::io::{self, BufRead, Write};

fn main() -> std::io::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let mut mode = "tag"; // "tag" | "surface" | "diacritize"
    let mut base = "data".to_string();

    for a in args.iter().skip(1) {
        match a.as_str() {
            "--surface"    => mode = "surface",
            "--diacritize" => mode = "diacritize",
            _ => base = a.clone(),
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
        match mode {
            "diacritize" => {
                writeln!(out, "{}", tagger.diacritize(&text))?;
            }
            "surface" => {
                for t in tagger.tag_surface(&text) {
                    write_token(&mut out, &t)?;
                }
                writeln!(out)?;
            }
            _ => {
                for t in tagger.tag(&text) {
                    write_token(&mut out, &t)?;
                }
                writeln!(out)?;
            }
        }
    }
    Ok(())
}

fn write_token<W: Write>(out: &mut W, t: &bcde_tagger::Token) -> io::Result<()> {
    let extra = match (&t.diacritic, &t.sense, &t.resolver_level) {
        (Some(d), Some(s), Some(l)) => format!("\tdiac={d}\tsense={s}\tvia={l}"),
        (Some(d), _, _) => format!("\tdiac={d}"),
        _ => String::new(),
    };
    writeln!(out, "{}\t{}{}", t.word, t.upos, extra)
}
