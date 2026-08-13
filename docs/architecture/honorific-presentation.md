# Honorific semantics and presentation

- **Status:** Accepted
- **Issue:** [#55](https://github.com/yaqub0r/sabiqah/issues/55)
- **Punctuation follow-up:** [#69](https://github.com/yaqub0r/sabiqah/issues/69)
- **Decision date:** 2026-08-12

## Decision

Sabiqah models an honorific as semantic data and treats its written form as a
language- and book-profile realization. The model separates:

- semantic class;
- referent scope;
- grammatical agreement;
- exact observed source form;
- expanded Arabic form;
- target-language accessible expansion;
- preferred compact Unicode character, when one exists; and
- font-support and fallback state.

The exact source remains hash-bound provenance. A translation profile may
select an equivalent conventional formula, but it may not change the referent,
agreement, family inclusion, or substantive meaning.

## Formulaic versus substantive wording

Compaction is allowed only when the words function as a formulaic honorific or
devotional invocation. If a passage quotes, defines, contrasts, grammatically
analyzes, or otherwise depends on the words themselves, the words are
substantive text and remain expanded. Uncertain classification produces a
review finding rather than a silent rewrite.

## Storage and rendering

Public corpus text may contain the registry's preferred compact character.
Every occurrence also resolves through the versioned registry to its expanded
Arabic, English accessibility text, semantic class, and agreement.

The reader:

1. uses the bundled Noto Naskh Arabic font for compact characters supported by
   the audited font baseline;
2. renders unsupported characters as the reading language's expanded phrase;
3. exposes an expanded phrase to assistive technology;
4. expands compact characters for search and plain-text copy; and
5. wraps inline Arabic in directionally isolated markup.

The compact character is presentation, not the search key or only semantic
record. Unicode normalization is applied only after registry expansion for
search or comparison. It never mutates the stored authority text.

An expanded English honorific may be punctuated as a parenthetical phrase. If
it is replaced by a compact character, the renderer removes the comma before
the phrase and its paired closing comma so the character attaches to its
referent: `the Prophet, may God bless him and grant him peace, said` becomes
`the Prophet ﷺ said`. Punctuation belonging to the surrounding sentence is
preserved. Public-corpus validation rejects a comma between a referent and a
compact honorific.

## Validation boundary

Validation distinguishes two independent outcomes:

- **public eligibility** fails for restricted expression, missing public
  provenance, private locators, or absent working English; and
- **translation readiness** needs attention for unresolved referent,
  agreement, placement, or semantic-realization findings.

A literal spelling or global count difference by itself is not a public-
eligibility failure. A known wrong-gender, wrong-number, wrong-referent, or
meaning-changing substitution fails translation readiness and blocks human
approval and canonical promotion until corrected. The readable working record
remains visible with its honest state.

## Version policy

Unicode 14 honorific characters supported by Noto Naskh Arabic 2.021 may be
used for compact display. Unicode 17 additions are present in the semantic
registry but use expanded display until the bundled font is upgraded and the
font, browser, copy, search, bidi, and accessibility acceptance suite passes.

Registry or book-profile changes create a new immutable corpus version. They
never rewrite an already published corpus object in place.
