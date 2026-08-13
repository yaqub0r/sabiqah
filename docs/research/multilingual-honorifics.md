# Multilingual honorific research

- **Status:** Complete for implementation v1
- **Issue:** [#55](https://github.com/yaqub0r/sabiqah/issues/55)
- **Research baseline:** Unicode 17.0; Noto Naskh Arabic 2.021
- **Languages in scope:** Arabic, English, and Urdu

## Question

How should Sabiqah preserve, validate, and present devotional formulas when a
source and translation may use different written conventions, while keeping
the result readable, searchable, copyable, and grammatically correct?

## Findings

### A glyph, a character, and a formula are different things

An honorific is first a semantic formula attached to one or more referents. A
font may draw that formula as one glyph, and Unicode may encode a compact
character for it, but neither representation replaces the underlying meaning.

Unicode 17 contains three relevant mechanisms:

1. word-level combining marks at `U+0610` through `U+0613`, documented from
   Pakistani publishing in Urdu, Balochi, and other Arabic-script languages;
2. older compatibility ligatures such as `U+FDFA` (`ﷺ`), whose compatibility
   decomposition is the spelled-out formula; and
3. semantic honorific word-ligature characters, including `U+FD40` through
   `U+FD4F`, `U+FDFE`, and `U+FDFF`, which have no Unicode decomposition.

The last group was encoded only after published running-text examples were
found. Its proposal explicitly treats different glyph designs as
interchangeable when the underlying phrase has the same meaning. It also
records published English-language use and distinguishes masculine,
feminine, dual, masculine-or-mixed plural, and feminine plural forms.

Unicode 17 adds more honorific characters at `U+FBC3` through `U+FBD2`,
`U+FD90` through `U+FD91`, `U+FDC8` through `U+FDCE`, and `U+10ED1` through
`U+10ED8`. They are valid characters, but the tested Noto Naskh Arabic 2.021
release does not yet contain their glyphs. Sabiqah therefore records their
semantics and expands them for display until an audited bundled font supports
them.

Primary references:

- [Unicode 17 Arabic Presentation Forms-A names list](https://unicode.org/charts/nameslist/n_FB50.html)
- [Unicode 17 character database](https://www.unicode.org/Public/17.0.0/ucd/UnicodeData.txt)
- [Unicode 17 character ages](https://www.unicode.org/Public/17.0.0/ucd/DerivedAge.txt)
- [2019 proposal with running-text evidence](https://www.unicode.org/L2/L2019/19289r-arabic-honorifics.pdf)
- [2001 Pakistani Arabic-script publishing proposal](https://www.unicode.org/L2/L2001/01425-arabic_marks.pdf)
- [2020 proposal for `U+FD4E` and `U+FD4F`](https://www.unicode.org/L2/L2020/20042-two-arabic-honorifics.pdf)

### Language convention does not change the referent

Arabic, Urdu, and English publications do not always realize a formula with
the same words or typography. For example, invocations attached to Allah may
use `سبحانه وتعالى`, `عز وجل`, a compact character, or an English phrase such
as “Allah Most High.” Those are possible target-language realizations of a
semantic class; they are not literal string equivalents in every context.

The translator must still preserve distinctions that carry meaning:

- the person or persons to whom the formula refers;
- singular, dual, or plural number;
- masculine, feminine, or mixed agreement where the formula encodes it;
- whether the Prophet's family is included; and
- whether the wording is itself being quoted, contrasted, defined, or
  analyzed.

The dual is particularly important. The Unicode evidence documents an
honorific following “Abd Allah ibn Umar” that intentionally includes both son
and father. A nearest-name rule would incorrectly reduce it to singular.

### Normalization cannot supply the semantic model

Unicode normalization is not a sufficient expansion mechanism. `U+FDFA`
compatibility-normalizes to letters, while the newer honorific word ligatures
deliberately have no decomposition. Blind `NFKC` therefore treats equivalent
formulas inconsistently and may also erase distinctions that matter in other
text. Sabiqah expands known honorifics through its versioned semantic registry
before applying search-only normalization. Stored source text is never
rewritten by search normalization.

### Compact display needs an explicit fallback

Noto Naskh Arabic 2.021 was inspected directly. It covers the Unicode 14
honorific repertoire used by Al-Isabah, including all five agreement forms of
`رضي الله عنه`, but not the honorific characters newly assigned in Unicode 17.
Amiri 1.003 covers the older combining signs and compatibility ligatures but
not the Unicode 14 semantic honorific characters. Noto Naskh Arabic is therefore
the bundled reading font for the first implementation.

The implementation pins `@fontsource-variable/noto-naskh-arabic` 5.3.0
(Fontsource metadata version `v44`, modified 2026-01-28). The exact Arabic WOFF2
shipped by that package is 94,032 bytes with SHA-256
`2a10d33e1f7129ab2b6ec76666e82ac5b509fbcfa7b4a3a1289bff42d2d64cd7`.
Its cmap was inspected after installation and confirmed the same boundary:
`U+FD40` through `U+FD4F`, `U+FDCF`, `U+FDFA`, `U+FDFE`, and `U+FDFF` are
present; `U+FBC3`, `U+FDC8`, and `U+10ED1` through `U+10ED8` are absent.

The web presentation must not expose a compact character as the only usable
text. It displays the supported glyph while retaining an expanded,
language-appropriate value for assistive technology, browser search, and
plain-text copy. Inline Arabic is directionally isolated with markup rather
than embedded control characters. This follows W3C guidance for hidden
accessible text and bidirectional inline content:

- [WAI technique C7](https://www.w3.org/WAI/WCAG22/Techniques/css/C7)
- [W3C inline bidi markup](https://www.w3.org/International/articles/inline-bidi-markup/)

## Decision inputs for Al-Isabah

The existing 1,565-entry working corpus demonstrated why literal inventory
equality is unsafe as a publication gate:

- 52 complete English records were withheld solely because source and target
  literal formula counts differed;
- five were withheld because private editorial notes had been removed, even
  though the independently written translation could be repaired against the
  approved source; and
- twelve short records lost their English because the full translation lived
  in the title and a duplicate-title cleanup left an empty body.

None of these were rights failures. Literal or count differences remain useful
review diagnostics, but they do not erase otherwise public-eligible working
English. A semantic or agreement concern blocks machine approval and canonical
promotion until resolved; it does not turn the public reader into an
Arabic-only edition.

## Result

The implementation decision is recorded in
[`honorific-presentation.md`](../architecture/honorific-presentation.md). The
machine-readable repertoire lives with the release model and is versioned
independently from any book profile.
