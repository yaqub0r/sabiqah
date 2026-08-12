# Canonical book promotion contract

- **Contract ID:** `canonical-book-promotion`
- **Status:** Active
- **Issue:** [#30](https://github.com/yaqub0r/sabiqah/issues/30)

## Purpose

This contract governs the explicit promotion of publication-ready scholarly
content from Sabiqah's controlled workflow into an individual canonical book
repository. Promotion is a reviewed release operation, never silent
synchronization.

## Ownership boundary

Sabiqah owns acquisition, rights assessment, private research storage,
comparison and translation workflow, application state, and presentation. A
book repository owns its approved canonical records, book-specific provenance,
editorial history, stable identifiers, validation, and versioned releases.

Restricted research evidence and Sabiqah account, invitation, reputation, or
moderation state must not enter a public book repository.

## Promotion manifest

Every promotion must identify:

- canonical book repository and target release;
- immutable source commit and reproducible content hash;
- exact records and provenance manifest being promoted;
- content-compliance policy or contract version applied;
- rights classification and basis for every public dependency;
- translation or transcription base and comparison witnesses;
- completed scholarly and compliance reviews; and
- unresolved limitations that remain visible in the public record.

The manifest contains non-sensitive identifiers and conclusions, not
restricted source expression, credentials, private URLs, or correspondence.

## Independent gates

Sabiqah approval makes content eligible for book-repository review; it does not
replace that review. The book repository must independently validate its
schema, provenance, stable identifiers, and protected canonical-Arabic path.
Automation must not silently overwrite canonical Arabic, translation,
provenance, or editorial history.

## Release consumption

Sabiqah consumes an immutable release ID and source commit through the
versioned reader contract. It must reject malformed records and unknown major
contract versions. Deployments must be reproducible from the pinned release and
must not read private research evidence or mutable book working branches.

Corrections enter as reviewable proposals and create new versioned history.
They do not erase the provenance or review record of earlier releases.
