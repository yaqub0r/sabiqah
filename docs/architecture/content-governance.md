# Content-governance operating model

- **Status:** Proposed
- **Issue:** [#26](https://github.com/yaqub0r/sabiqah/issues/26)

## Purpose

Sabiqah is the application consumer that verifies, stores, reviews, and
presents scholarly releases. Canonical book repositories govern their source
and rights decisions, translation execution, per-record scholarly metadata,
corrections, promotion, and immutable release history.

This record defines repository responsibilities and trust boundaries. It does
not decide the rights status of a particular source or replace qualified legal
review.

## Operating model

Sabiqah governs its own:

1. discovery and acquisition of research witnesses through ordinary lawful
   access;
2. bibliographic identification plus consumer-side provenance and rights
   verification;
3. controlled private storage for research material that is not approved for
   public release;
4. application review events and correction-proposal interfaces;
5. deterministic validation, storage, activation, and rollback of pinned
   releases; and
6. reader, contributor, and reviewer experiences, including public
   presentation of pinned book releases.

For Al-Isabah, the canonical repository's
[versioned governance reference](al-isabah-governance-compatibility.md) owns
translation policy and execution. Sabiqah may reject an incompatible or
rights-ineligible release, but it does not replace the upstream decision or
keep a governing local copy.

Repositories and services such as Internet Archive, Usul, Shamela, OpenITI,
Google Books, HathiTrust, library collections and catalogs, and publisher or
rights-holder sites may be used for discovery, bibliographic verification, or
textual comparison. Their inclusion here does not assert that every item they
provide may be reproduced, adapted, or redistributed. The rights basis for an
artifact must be assessed separately from its availability.

## Trust boundaries

### Public licensing boundary

The repository's licenses attach to material by authorship and rights basis,
not merely by directory or delivery channel. Sabiqah-authored software and
code-adjacent implementation materials use PolyForm Noncommercial 1.0.0.
Any legacy Sabiqah-authored translations and other intentionally published
scholarly content use CC BY-NC-SA 4.0 unless a more specific notice applies.
Canonical book repositories govern new translation and release terms.
Third-party materials retain their existing terms and must carry their
required attribution. Private evidence is neither published nor licensed.

Every book or independently released content set must complete a rights matrix
from [`docs/templates/rights-matrix.md`](../templates/rights-matrix.md). The
matrix records each component's creator, role, rights basis, license or status,
attribution, publication classification, exact scope, and unresolved limits.
It supplements rather than replaces source-authority and promotion manifests.

### Private research evidence

Restricted scans, OCR, modern translations, detailed comparison output,
rights-holder correspondence, and other non-public evidence stay in access-
controlled storage governed by Sabiqah. They must not be committed to public
repositories, included in public build artifacts, or served by the public
application unless separately approved for that use.

Public repositories may record non-sensitive bibliographic metadata, stable
provider landing-page links, source hashes, rights classifications, dates
checked, and independently written editorial conclusions. They must not expose
credentials, private storage locations, access instructions, or restricted
expression.

Public records may state that generic private downstream products consume
pinned releases. They must not name or describe private systems or disclose
their code, schemas, APIs, operations, access information, or evidence.

### Canonical book repositories

A book repository owns the work's source and rights decisions, translation
policy, canonical Arabic and translation records, book-specific provenance,
editorial decisions, stable identifiers, per-record review state, corrections,
promotion, and versioned releases. It does not own Sabiqah account data,
reviewer reputation, invitations, private research storage, or presentation
infrastructure.

### Public application

Sabiqah consumes pinned, versioned book releases. It may link to a provider's
ordinary item or reader page for research convenience, but an external link is
not a rights determination and does not transfer the linked material into a
Sabiqah release.

## Promotion control

Submitting a Sabiqah review or correction proposal to a book repository is an
explicit handoff, not an automatic synchronization or promotion. The canonical
repository applies its own policy before a new release. The handoff must
identify:

- the canonical book repository and target release;
- the content and provenance manifest being promoted;
- the applicable compliance-policy version;
- the source commit or reproducible content hash;
- the completed scholarly and compliance reviews; and
- unresolved limitations that remain visible in the public record.

Book-repository review and validation remain authoritative. A Sabiqah event
does not change release class, and Sabiqah must never silently replace
canonical content or mutate a published release.

## Public documentation rule

The public record should accurately describe which sources were used as a
translation base and which were consulted only for comparison. Public
availability, another service's conduct, removal of visible annotations, or an
AI transformation must never be represented as an independent grant of reuse
rights.

Detailed source classifications, provenance schemas, release validation, and
correction or takedown procedures will be defined by the content-compliance
policy and enforced at the promotion and release boundaries.
