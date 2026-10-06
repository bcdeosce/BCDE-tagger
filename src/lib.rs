//! BCDE-tagger — POS tagging e desambiguação de homógrafos para português brasileiro.
//!
//! # Exemplo
//!
//! ```no_run
//! use bcde_tagger::Tagger;
//!
//! let tagger = Tagger::load("data")?;
//! let tokens = tagger.tag("A sede da empresa é grande.");
//! for t in tokens {
//!     println!("{}\t{}\t{:?}", t.word, t.upos, t.diacritic);
//! }
//! # Ok::<(), std::io::Error>(())
//! ```

pub mod crf;
pub mod resolver;
pub mod tagger;
pub mod tokenizer;

pub use crf::Crf;
pub use resolver::Resolver;
pub use tagger::{Tagger, Token, ALL_POS};
pub use tokenizer::tokenize_mwt;
