# Honorific semantics and presentation

- **Status:** Accepted
- **Issue:** [#55](https://github.com/yaqub0r/sabiqah/issues/55)
- **Punctuation follow-up:** [#69](https://github.com/yaqub0r/sabiqah/issues/69)
- **Decision date:** 2026-08-12

## Decision

Sabiqah consumes honorific semantics from each canonical book repository and
adapts the supplied realization for accessible presentation. For Al-Isabah,
the pinned
[upstream formula registry](al-isabah-governance-compatibility.md) owns the
semantic class, referent, agreement, source form, expansion, and target
realization. The Sabiqah adapter separately tracks:

- the upstream projection identity;
- expanded Arabic and target-language accessibility text needed for fallback;
- preferred compact Unicode character, when one exists; and
- font-support and fallback state.

The exact source and upstream registry remain hash-bound provenance. Sabiqah's
font or fallback choices may not change the referent, agreement, family
inclusion, or substantive meaning selected by the upstream profile.

## Formulaic versus substantive wording

Compaction is allowed only when the words function as a formulaic honorific or
devotional invocation. If a passage quotes, defines, contrasts, grammatically
analyzes, or otherwise depends on the words themselves, the words are
substantive text and remain expanded. Uncertain classification produces a
review finding rather than a silent rewrite.

## Storage and rendering

Public corpus text may contain the upstream registry's preferred compact
character. Every occurrence resolves through the pinned consumer projection
and Sabiqah's presentation metadata to expanded Arabic, English accessibility
text, semantic class, agreement, and supported display form.

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

An upstream formula or book-profile change follows the canonical repository's
new immutable release cycle. A Sabiqah font or presentation-adapter change is
an application version change. Neither rewrites an already published corpus
object in place.
