# Al-Isabah governance compatibility

- **Status:** Accepted
- **Issues:** [#113](https://github.com/yaqub0r/sabiqah/issues/113) and
  [#136](https://github.com/yaqub0r/sabiqah/issues/136)

## Authority and pin

Al-Isabah is the sole authority for its translation policy and profile, formula
semantics, source and rights decisions, per-record scholarly review metadata,
corrections, promotion, and immutable releases. Sabiqah is a verified
application consumer and does not keep a governing copy of those policies.

The current consumer pin is Al-Isabah commit
[`e301d22b`](https://github.com/yaqub0r/al-isabah/tree/e301d22bd634777d5846a844340d42a00e3a2e3a).
At that commit:

- the
  [`translation-governance-reference.v2.json`](https://github.com/yaqub0r/al-isabah/blob/e301d22bd634777d5846a844340d42a00e3a2e3a/docs/contracts/translation-governance-reference.v2.json)
  reference is version `2.0.0` with normalized SHA-256
  `7d73170d384f417733134e5ca09263ba73c92e941c5590d534d9eb38ec6704ae`;
- the referenced
  [`translation-quality-workflow`](https://github.com/yaqub0r/al-isabah/blob/e301d22bd634777d5846a844340d42a00e3a2e3a/docs/contracts/translation-quality-workflow.md)
  and
  [Al-Isabah profile](https://github.com/yaqub0r/al-isabah/blob/e301d22bd634777d5846a844340d42a00e3a2e3a/docs/translation-profiles/al-isabah.md)
  govern translation execution; and
- the referenced
  [`honorific-formulas.v1.json`](https://github.com/yaqub0r/al-isabah/blob/e301d22bd634777d5846a844340d42a00e3a2e3a/profiles/honorific-formulas.v1.json)
  registry is version `1.3.0` with normalized SHA-256
  `b23fcd528b840b0e5bbe8932fca6eeaaa576ee51263d9838d4f8d18e40c9e100`.

The machine-readable Sabiqah compatibility pin lives in
`packages/release-model/src/al-isabah-governance.compatibility.json`. Its
honorific projection is a verified consumer adapter, not a policy authority.
Sabiqah separately owns font support, fallback, search, copy, bidirectional
isolation, and accessibility presentation.

## Consumer boundary

Sabiqah may verify and ingest checksum-pinned releases, retain private evidence
under its own controls, provide reader and review interfaces, store append-only
application events, and present release provenance and rights. It may not
define Al-Isabah translation policy, treat a local projection as governing,
mutate an immutable release, or turn a human review event into another release
class.

Human review is append-only, ongoing, nonterminal metadata. Its state must be
disclosed, but zero or incomplete coverage does not block public-working
publication, canonical promotion, or immutable release eligibility and does
not select a release class. Concrete source, provenance, rights, validation,
substantive, or unresolved-disclosure defects remain independent fail-closed
controls. Accepted corrections and review events use a new immutable upstream
release with explicit supersession; Sabiqah's operational review overlay does
not change the pinned corpus object.

## Compatibility changes

A future update must start from an immutable Al-Isabah commit, verify the
reference and artifact hashes using UTF-8/LF normalization, and reject an
unknown reference major version. Update the consumer pin and derived
projection together in a reviewed Sabiqah change. Distribution schema `2.0.0`
remains active for new ingestion and schema `1.0.0` remains rollback-only; this
governance pin does not replace release verification.
