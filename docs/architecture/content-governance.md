# Content-governance operating model

- **Status:** Proposed
- **Issue:** [#26](https://github.com/yaqub0r/sabiqah/issues/26)

## Purpose

Sabiqah is the governed system that prepares scholarly content for publication
and presents approved releases. It owns the process from source discovery
through public presentation; each book repository owns the resulting canonical
edition and its release history.

This record defines repository responsibilities and trust boundaries. It does
not decide the rights status of a particular source or replace qualified legal
review.

## Operating model

Sabiqah governs:

1. discovery and acquisition of research witnesses through ordinary lawful
   access;
2. bibliographic identification, provenance capture, and rights assessment;
3. controlled private storage for research material that is not approved for
   public release;
4. textual comparison, editorial analysis, translation, and scholarly review;
5. compliance review and explicit promotion of publication-ready content into
   a canonical book repository; and
6. reader, contributor, and reviewer experiences, including application state
   and public presentation of pinned book releases.

Repositories and services such as Internet Archive, Usul, Shamela, OpenITI,
Google Books, HathiTrust, library collections and catalogs, and publisher or
rights-holder sites may be used for discovery, bibliographic verification, or
textual comparison. Their inclusion here does not assert that every item they
provide may be reproduced, adapted, or redistributed. The rights basis for an
artifact must be assessed separately from its availability.

## Trust boundaries

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

### Canonical book repositories

A book repository receives only material approved for public release. It owns
the work's canonical Arabic and translation records, book-specific provenance,
editorial decisions, stable identifiers, review state, and versioned releases.
It does not own Sabiqah account data, reviewer reputation, invitations, private
research storage, or presentation infrastructure.

### Public application

Sabiqah consumes pinned, versioned book releases. It may link to a provider's
ordinary item or reader page for research convenience, but an external link is
not a rights determination and does not transfer the linked material into a
Sabiqah release.

## Promotion control

Moving content from the governed research workflow into a book repository is
an explicit promotion event, not an automatic synchronization. A promotion
must identify:

- the canonical book repository and target release;
- the content and provenance manifest being promoted;
- the applicable compliance-policy version;
- the source commit or reproducible content hash;
- the completed scholarly and compliance reviews; and
- unresolved limitations that remain visible in the public record.

Book-repository review and validation remain required. Sabiqah must never
silently replace canonical content.

## Public documentation rule

The public record should accurately describe which sources were used as a
translation base and which were consulted only for comparison. Public
availability, another service's conduct, removal of visible annotations, or an
AI transformation must never be represented as an independent grant of reuse
rights.

Detailed source classifications, provenance schemas, release validation, and
correction or takedown procedures will be defined by the content-compliance
policy and enforced at the promotion and release boundaries.
