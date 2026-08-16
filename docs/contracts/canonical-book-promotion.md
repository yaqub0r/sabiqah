# Canonical book promotion contract

- **Contract ID:** `canonical-book-promotion`
- **Status:** Active
- **Issue:** [#30](https://github.com/yaqub0r/sabiqah/issues/30)

## Purpose

This contract governs Sabiqah's proposal handoff and verified consumption at
the canonical book boundary. A canonical repository controls promotion and
publishes its immutable releases; Sabiqah never turns application state into a
release through silent synchronization.

## Ownership boundary

Sabiqah owns private-evidence handling, application state, verified release
ingestion, storage, and presentation. A book repository owns book-specific
source and rights decisions, translation policy and execution, per-record
scholarly review metadata, approved canonical records, corrections, editorial
history, stable identifiers, validation, promotion, and versioned releases.

Restricted research evidence and Sabiqah account, invitation, reputation, or
moderation state must not enter a public book repository.

## Promotion manifest

Every Sabiqah proposal handoff and consumed release must preserve or identify:

- canonical book repository and target release;
- immutable source commit and reproducible content hash;
- exact records and provenance manifest being promoted;
- content-compliance policy or contract version applied;
- rights classification and basis for every public dependency;
- translation or transcription base and comparison witnesses;
- the upstream scholarly and compliance review states; and
- unresolved limitations that remain visible in the public record.

The manifest contains non-sensitive identifiers and conclusions, not
restricted source expression, credentials, private URLs, or correspondence.

## Independent gates

Sabiqah review activity produces operational evidence or a proposal; it does
not approve scholarly content, change a release class, or replace upstream
review. The book repository independently validates its schema, provenance,
stable identifiers, and protected canonical-Arabic path. Automation must not
silently overwrite canonical Arabic, translation, provenance, or editorial
history.

## Release consumption

Sabiqah consumes an immutable release ID and source commit through the
versioned reader contract. It must reject malformed records and unknown major
contract versions. Deployments must be reproducible from the pinned release and
must not read private research evidence or mutable book working branches.

Corrections enter as reviewable upstream proposals and, when accepted, create
a new immutable release with explicit supersession. Incremental translation
and increased review coverage use the same release cycle. They do not erase
the provenance or review record of earlier releases.
