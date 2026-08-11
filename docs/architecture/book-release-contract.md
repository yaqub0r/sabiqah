# Book release and review contract

## Ownership

Every book repository publishes its own canonical schema and releases. Sabiqah
consumes a small, versioned reader contract rather than taking ownership of the
book's complete editorial model. A book-specific exporter may discard internal
fields but must preserve stable IDs, provenance, uncertainty, and review state.

The beta fixture contract lives in `packages/release-model`. It is versioned as
`1.0.0` and requires:

- stable work, entry, and segment identifiers;
- Arabic and English display text kept in separate fields;
- explicit Arabic and translation review states;
- source spans with edition, volume, page, and evidence references;
- visible issues for disputed readings, OCR concerns, and incomplete review;
- a release ID, source commit, publication time, and repository URL.

## Review proposal

The editor emits a proposal, never a rewritten canonical entry. A proposal
names the base release, entry, segment, field, proposed value, rationale, and
evidence references. Translation proposals and canonical-Arabic corrections
are distinct operations.

The Decap adapter stores that object under a single `proposal` key in a
workflow envelope. It converts the validated object to Decap's immutable data
structure and renders it read-only; contributors return to the Sabiqah editor
to change it. Book-repository CI must unwrap and validate the proposal before a
maintainer reviews the scholarly change.

Arabic is read-only in the ordinary editor. A proposed Arabic correction must
use the protected correction path, include a rationale and evidence, and be
approved through the book repository's review policy. Automation never silently
normalizes or replaces canonical Arabic.

## Compatibility

Sabiqah rejects unknown major schema versions and malformed records. Additive
minor fields may be ignored. Consumers pin a release ID and source commit so a
deployment can be reproduced or rolled back.

The three initial fixtures are deliberately synthetic and cover:

1. a normal reviewed single-page entry;
2. an entry spanning source pages;
3. an unresolved reading/OCR concern.

They test interface behavior and make no claim to be publishable Al-Isabah
scholarship.
