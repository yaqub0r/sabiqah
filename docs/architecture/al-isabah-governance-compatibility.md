# Al-Isabah governance compatibility

- **Status:** Accepted
- **Issues:** [#113](https://github.com/yaqub0r/sabiqah/issues/113),
  [#136](https://github.com/yaqub0r/sabiqah/issues/136), and
  [#158](https://github.com/yaqub0r/sabiqah/issues/158)

## Authority and pin

Al-Isabah is the sole authority for its translation policy and profile, formula
semantics, source and rights decisions, per-record scholarly review metadata,
corrections, promotion, and immutable releases. Sabiqah is a verified
application consumer and does not keep a governing copy of those policies.

The current consumer pin is Al-Isabah commit
[`9dfb8cea`](https://github.com/yaqub0r/al-isabah/tree/9dfb8cea613329917ea9c932baaaef0bb842e966).
At that commit:

- the
  [`translation-governance-reference.v13.json`](https://github.com/yaqub0r/al-isabah/blob/9dfb8cea613329917ea9c932baaaef0bb842e966/docs/contracts/translation-governance-reference.v13.json)
  reference is version `13.0.0` with normalized SHA-256
  `f5c0b4819939fadcd5808bec26fe345c9c868faddbf2b00556ecc0df02a175a5`;
- the referenced
  [`translation-quality-workflow`](https://github.com/yaqub0r/al-isabah/blob/9dfb8cea613329917ea9c932baaaef0bb842e966/docs/contracts/translation-quality-workflow.md)
  and
  [Al-Isabah profile](https://github.com/yaqub0r/al-isabah/blob/9dfb8cea613329917ea9c932baaaef0bb842e966/docs/translation-profiles/al-isabah.md)
  govern translation execution; and
- the referenced
  [`honorific-formulas.v1.json`](https://github.com/yaqub0r/al-isabah/blob/9dfb8cea613329917ea9c932baaaef0bb842e966/profiles/honorific-formulas.v1.json)
  registry is version `1.9.0` with normalized SHA-256
  `6a9dc65f90947ffb1ce43d05c3404493514f564cda43742f90b28ebb43bf180d`.

The machine-readable Sabiqah compatibility pin lives in
`packages/release-model/src/al-isabah-governance.compatibility.json`. Its
formula projection preserves the complete verified upstream registry but is not
a policy authority. Sabiqah applies its compact honorific presentation only to
formulae with an existing consumer-owned display adapter; other verified
formulae retain their upstream text without invented compact semantics. Sabiqah
separately owns font support, fallback, search, copy, bidirectional isolation,
and accessibility presentation.

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
projection together in a reviewed Sabiqah change. Distribution-manifest schema
`2.0.0` remains active for new ingestion, including its backward-compatible
record shapes `2.0.0` and `2.1.0`; schema `1.0.0` remains rollback-only. This
governance pin does not replace release verification.
