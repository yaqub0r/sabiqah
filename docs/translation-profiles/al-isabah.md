# Al-Isabah translation profile

- **Status:** Active
- **Work:** _al-Isabah fi Tamyiz al-Sahabah_ by Ibn Hajar al-Asqalani
- **Governing contract:**
  [`translation-quality-workflow`](../contracts/translation-quality-workflow.md)
- **Continuation issue:** [#46](https://github.com/yaqub0r/sabiqah/issues/46)

## Purpose

This profile specializes Sabiqah's general translation-quality contract for
Al-Isabah. It captures the proven Volume 8 workflow in a form that can fill the
other volumes and topic cohorts without renumbering existing records.

It contains policy and non-sensitive implementation requirements only. Private
facsimiles, OCR, model outputs, comparison passages, object locations, and
credentials remain in Sabiqah-controlled storage.

## Authority and witnesses

The locked Arabic edition is authoritative. Its facsimile and aligned
machine-readable Arabic must remain hash-bound throughout the workflow.

Witness roles are explicit:

- another Al-Isabah edition is an **alternative edition**;
- Urdu, Persian, Turkish, or another translation is a **translation witness**;
- _Usd al-Ghaba_, _al-Isti'ab_, and other biographical dictionaries are
  **collateral works**; and
- dictionaries or specialist references are **lexical references**.

A witness may reveal damage or clarify ambiguity. It never silently becomes
the translation base. Clear canonical Arabic remains decisive; a corrected
reading requires a cited, reviewable emendation.

## Stable units

Canonical publication uses permanent entry identifiers such as
`isabah-entry-00010759`; the apparent number is an allocation token rather than
mutable printed metadata. Segments receive entry-scoped stable identifiers.
Later volume or cohort fills allocate new identities without renumbering or
reusing existing ones.

Every translated unit binds at minimum:

- stable entry and segment identity;
- volume, printed page when available, and facsimile scan;
- printed entry number and heading where present;
- exact Arabic and upstream evidence hashes;
- English candidate, machine state, human-review state, and unresolved items;
- names and observed mentions; and
- complete stage provenance.

## Autonomous implementation

The established pipeline implements the general state machine as follows:

1. align the locked Usul machine text to the same-edition facsimile and audit
   page, entry, and sequence coverage;
2. perform a provenance-bound blind Codex Arabic-to-English pass;
3. independently critique omissions, additions, names, isnads, negation,
   numbering, notes, and cross-page continuations;
4. resolve only flagged concerns against classified translation witnesses,
   alternative Al-Isabah editions, and exact-heading collateral searches;
5. adjudicate every substantive unit into a complete candidate while retaining
   explicit unresolved findings;
6. validate exact scope, hashes, entry numbering, material numerals, notes,
   boundaries, model lineage, and all-stage coverage;
7. build stable JSON name candidates and mentions, preserving operator decisions
   across reruns;
8. generate the bilingual English review presentation from validated JSONL; and
9. publish a machine-readiness record only after all preceding checks pass.

The former FirstLight implementation and closed Al-Isabah development branches
are historical evidence, not the governing location. Sabiqah owns future
translation execution and this profile. Al-Isabah receives only records that
complete human review, compliance approval, and explicit promotion.

## Volume and cohort coverage

A whole-volume run locks every substantive page and entry in that volume. A
topic cohort such as Khadijah and her immediate associates additionally records
the discovery query, relationship or inclusion rationale, all direct-mention
include/exclude decisions, and source spans across Volumes 1-8.

Both shapes produce the same entry and segment contracts. A cohort is therefore
an incremental coverage view, not a competing corpus, and later work can fill
gaps without changing stable identities.

## Al-Isabah-specific quality targets

Machine readiness requires:

- exact coverage of the locked pages or cohort inventory;
- continuous printed-entry sequence where the edition supplies one;
- zero unexplained missing, duplicated, or reordered units;
- explicit preservation checks for names, isnads, negation, entry numbers,
  material numerals, citations, footnotes, and continuations;
- definitive `hit` or `no_match` witness results where witness work is required;
  transient provider failure remains `unavailable` and blocks that concern;
- a complete unresolved list linked to exact source locations;
- matching hashes across aligned Arabic, adjudicated English, the name index,
  source bundle, readiness record, and generated presentation; and
- human-review state still `unreviewed` when machine readiness first opens.

Reasoning effort is calibrated with blinded paired comparisons whose source,
prompt, schema, model family, and witnesses are otherwise identical. A lower
setting is used only when the versioned evaluation policy accepts it without a
material quality regression.

## Reviewer handoff

The reviewer sees continuous bilingual reading, search, stable entry navigation,
names, workflow history, interventions, and unresolved findings. Name review and
English approval stay closed until the relevant source and presentation satisfy
machine readiness.

Human approval is append-only review evidence. It does not erase uncertainties,
alter canonical Arabic, or directly publish a release.

## Promotion boundary

Eligible records are packaged in an explicit promotion manifest referencing the
immutable Sabiqah corpus and evidence hashes without exposing restricted
expression or private object locations. The Al-Isabah repository independently
validates stable identifiers, reviewed Arabic and English, public provenance,
compliance status, and promotion lineage before accepting canonical content.
