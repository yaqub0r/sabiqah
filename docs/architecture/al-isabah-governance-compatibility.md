# Al-Isabah governance compatibility

- **Status:** Accepted
- **Issue:** [#113](https://github.com/yaqub0r/sabiqah/issues/113)

## Authority and pin

Al-Isabah is the sole authority for its translation policy and profile, formula
semantics, source and rights decisions, per-record scholarly review metadata,
corrections, promotion, and immutable releases. Sabiqah is a verified
application consumer and does not keep a governing copy of those policies.

The current consumer pin is Al-Isabah commit
[`eb4fec9b`](https://github.com/yaqub0r/al-isabah/tree/eb4fec9b744c12fcb677d9a7c53c4a58628aaa41).
At that commit:

- the
  [`translation-governance-reference.v1.json`](https://github.com/yaqub0r/al-isabah/blob/eb4fec9b744c12fcb677d9a7c53c4a58628aaa41/docs/contracts/translation-governance-reference.v1.json)
  reference is version `1.0.0` with normalized SHA-256
  `81d115c85f5c7f793439991c36ae757a80ebe92e40017f65d8fb2eb7a1e1f5db`;
- the referenced
  [`translation-quality-workflow`](https://github.com/yaqub0r/al-isabah/blob/eb4fec9b744c12fcb677d9a7c53c4a58628aaa41/docs/contracts/translation-quality-workflow.md)
  and
  [Al-Isabah profile](https://github.com/yaqub0r/al-isabah/blob/eb4fec9b744c12fcb677d9a7c53c4a58628aaa41/docs/translation-profiles/al-isabah.md)
  govern translation execution; and
- the referenced
  [`honorific-formulas.v1.json`](https://github.com/yaqub0r/al-isabah/blob/eb4fec9b744c12fcb677d9a7c53c4a58628aaa41/profiles/honorific-formulas.v1.json)
  registry is version `1.2.0` with normalized SHA-256
  `2691994d50457d967f41d04140b9f86f23967254fd764f2c756109194ba51a55`.

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

Human review changes per-record metadata and confidence only after the result
is accepted through Al-Isabah's proposal process. Incremental translation,
corrections, and review-coverage changes all use a new immutable upstream
release with explicit supersession. Sabiqah's operational review overlay does
not change the pinned corpus object.

## Compatibility changes

A future update must start from an immutable Al-Isabah commit, verify the
reference and artifact hashes using UTF-8/LF normalization, and reject an
unknown reference major version. Update the consumer pin and derived
projection together in a reviewed Sabiqah change. Distribution schema `2.0.0`
remains active for new ingestion and schema `1.0.0` remains rollback-only; this
governance pin does not replace release verification.
