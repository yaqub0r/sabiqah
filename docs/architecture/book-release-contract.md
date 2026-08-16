# Book release and review contract

## Ownership

Every book repository publishes its own canonical schema and releases. Sabiqah
consumes a small, versioned reader contract rather than taking ownership of the
book's complete editorial model. A book-specific exporter may discard internal
fields but must preserve stable IDs, provenance, uncertainty, and review state.
For Al-Isabah, Sabiqah also verifies the immutable
[upstream governance compatibility pin](al-isabah-governance-compatibility.md)
without copying it as local policy.

Before canonical promotion, a book repository may also publish a validated,
immutable `public-working` distribution for reading and review. This handoff is
application-neutral and checksum-bound. Sabiqah independently validates and
projects it; it does not inspect mutable working files or assign new scholarly
identities. The Al-Isabah implementation is recorded in
[`al-isabah-distribution-ingestion.md`](al-isabah-distribution-ingestion.md).

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

The canonical book repository governs whether a proposal changes per-record
review metadata, confidence, translation, or source text. Human review does
not select another release class. An accepted correction, incremental
translation, or review-coverage change appears through a new immutable release
with explicit supersession.

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

## Public working corpus and private evidence

Research inputs and public reading records are separate products. Restricted
facsimiles, comparison transcriptions, editorial apparatus, model traces, and
other pre-publication evidence remain in private R2. They are never made safe by
removing a hostname or relabeling an old record.

A `public-working` corpus is rebuilt from an approved, pinned source authority.
Its generated manifest proves the source artifact and license, replaces any
restricted displayed Arabic, excludes modern apparatus, removes private
locators, applies the work's honorific rules, and accounts for every legacy
record as either eligible or quarantined. A failed record is omitted from the
reader, not silently repaired or dropped. Publicly readable means compliant and
attributable; it does not mean human-reviewed or canonical.

Validated public-working summaries, indexes, sections, and items live under an
immutable R2 prefix selected by a separately verified activation pointer. R2 remains a private origin: the Worker serves these
objects anonymously with public cache headers, while the browser receives
neither R2 credentials nor object keys. Short entries remain in book order
inside substantial sections so the default experience reads like a book.

Human translation approvals are a Sabiqah operational overlay on this
immutable public corpus. The Worker accepts an approval or withdrawal only
from an active same-origin reviewer session after resolving the stable item ID
against the pinned corpus. Each event binds the decision to the corpus ID and
exact object digest. Anonymous readers receive aggregate approval counts; an
active reviewer also receives their own current state. Approval does not alter
the record,
satisfy canonical promotion, change upstream per-record metadata, or create a
different release class. An accepted decision follows the book repository's
proposal and immutable-release process before Sabiqah can ingest it.
