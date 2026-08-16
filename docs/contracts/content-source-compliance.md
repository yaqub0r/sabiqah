# Content source compliance contract

- **Contract ID:** `content-source-compliance`
- **Status:** Active
- **Issue:** [#30](https://github.com/yaqub0r/sabiqah/issues/30)

## Purpose

This contract governs how Sabiqah acquires, classifies, stores, compares, and
presents source material and how it verifies consumer-side provenance and
rights metadata. It is an operational control, not a source-specific legal
opinion or a substitute for qualified legal review.

Canonical book repositories own book-specific source and rights decisions,
translation policy, scholarly approval, corrections, and releases. Sabiqah may
preserve private evidence and reject an ineligible release, but it does not
govern how Al-Isabah translations are executed.

## Required behavior

1. Use ordinary lawful access when acquiring a research witness. Do not bypass
   access controls or provider restrictions.
2. Record bibliographic identity, provider landing-page URL, acquisition date,
   file hash when retained, and known rights information. Availability through
   a repository or another service's conduct is provenance, not permission.
3. Classify each artifact before release as one of:
   `approved-for-publication`, `external-reference`, `private-reference`,
   `permission-required`, `unresolved`, or `prohibited`.
4. Record the affirmative rights basis for `approved-for-publication`, such as
   verified public-domain status, a compatible license, documented permission,
   or Sabiqah authorship. A URL alone is not a rights basis.
5. Keep restricted scans, OCR, modern translations, reconstructive comparison
   output, rights-holder correspondence, credentials, and private storage
   details out of public repositories and deployment artifacts.
6. Identify the actual transcription or translation base separately from
   comparison witnesses. AI transformation, removal of visible notes, or
   independent reformatting does not change a source classification.
7. Preserve the supplied lineage through OCR, normalization, segmentation,
   comparison, translation, editorial correction, ingestion, and migration.
8. Stop public promotion when provenance or eligibility is unresolved. An
   authorized reviewer must approve any source-specific exception and record
   its scope without publishing restricted evidence.

## External references

Sabiqah may link to a provider's ordinary item or reader page for research
convenience. Do not proxy, cache, mirror, embed, or link directly to a raw file
unless that particular use is approved. An external link is not a Sabiqah
rights determination and must not be described as transferring responsibility
to the provider.

## Public record

Public provenance may include bibliographic facts, provider landing pages,
hashes, classifications, dates checked, transformations, and independently
written editorial decisions. It must accurately distinguish material used as a
base from material consulted only for comparison.

## Release condition

Only `approved-for-publication` content may be served from Sabiqah-controlled
storage. The canonical repository's release records and the consumer
verification required by `canonical-book-promotion` must bind that status to
the exact immutable content.
