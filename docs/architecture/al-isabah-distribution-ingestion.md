# Al-Isabah distribution ingestion

- **Status:** Accepted
- **Issue:** [#114](https://github.com/yaqub0r/sabiqah/issues/114)

## Decision

Al-Isabah publishes an application-neutral, checksum-bound `public-working`
distribution from its repository. Sabiqah treats that bundle as an immutable
input: it validates the manifest and every shard independently, projects the
records into the reader schema, validates the complete reader corpus, uploads
the result under a new immutable R2 prefix, verifies the uploaded objects, and
only then updates `public-corpora/al-isabah/current.json`.

The pointer contains the active corpus ID and prefix, not credentials. The
Worker resolves it at request time. Review approvals, reading progress, and
selection reports bind to the resolved corpus ID so decisions from one corpus
cannot silently apply to changed text. If the pointer is absent, the Worker
uses the last pre-pointer corpus during migration; a malformed pointer fails
closed.

## Producer and consumer boundary

The book repository owns stable source-unit identities, Arabic and English,
book structure, provenance, policy binding, uncertainty, machine assessment,
and human-review state. Printed entry numbers are display metadata and may
repeat; Sabiqah never uses them as identity.

Sabiqah owns only its deterministic reader projection, application state, R2
layout, activation pointer, and presentation. Structural headings and related
material remain ordered reading passages, but coverage counts distinguish
translated entries from those passages.

The development workflow polls the latest Al-Isabah `public-working` GitHub
prerelease twice per hour. This avoids a cross-repository write token; the
tradeoff is up to thirty minutes of automatic propagation latency. An operator
may dispatch the workflow with an explicit release tag for immediate ingestion.
Merging consumer code does not itself run ingestion; the next schedule,
repository dispatch, or approved manual dispatch does.

## Version and producer negotiation

Schema `2.0.0` is the only format accepted for a new ingestion. Schema `1.0.0`
is rollback-only: recovery restores the pointer to an already verified immutable
corpus rather than rebuilding from an old distribution. Unknown major versions
fail closed.

The consumer binds the distribution to evidence rather than trusting manifest
claims. It requires the exact Al-Isabah owner/repository, public-working release
tag, tag commit, release target, distribution ID, single asset name, byte count,
and GitHub-computed SHA-256. It also validates the manifest and shard hashes,
packet and record counts, public-only record allowlist, blocked canonical
promotion, the pinned OpenITI source commit and artifact hash, license and
attribution, and the exact per-book rights-matrix ID, schema, publication
decision, exclusions, review date, and follow-up policy. Only after those values
match Sabiqah's approved source-authority record may the reader projection use
that Sabiqah authority ID.

The projected corpus keeps Arabic-source rights, independently authored English
rights, and the rights-matrix identity as separate fields. It does not reduce
them to a repository-wide license string.

## Offline compatibility gate

Al-Isabah or another release-preparation environment can run the same
deterministic, network-free verifier after supplying immutable GitHub release
metadata and the rights matrix from the candidate commit:

```sh
pnpm compatibility:al-isabah -- \
  --distribution PATH/TO/EXTRACTED_DISTRIBUTION \
  --archive PATH/TO/al-isabah-public-distribution-COMMIT.zip \
  --release-metadata PATH/TO/release.json \
  --tag-ref PATH/TO/tag-ref.json \
  --rights-matrix PATH/TO/rights-matrix.json \
  --source-authority evidence/source-authorities/al-isabah.v1.json
```

This is a consumer compatibility check. It does not make Sabiqah the canonical
book owner, publish a release, upload a corpus, or change an activation pointer.

## Safety and rollback

- Archives are extracted with a strict member allowlist and traversal checks.
- Manifests, shard checksums, record counts, licenses, source authority, stable
  identities, and public-output state are validated before any upload.
- Verification errors use bounded contract messages and do not echo record
  content, credentials, paths from the distribution, or rejected values.
- Existing immutable prefixes are never overwritten with different bytes.
- Activation occurs only after an R2 download-and-validate round trip.
- Rollback changes the pointer to a previously verified immutable prefix; it
  does not delete or rewrite corpus objects. Each planned activation records
  the previously active corpus ID and prefix as explicit rollback metadata.
- The initial automation targets only the protected `development` environment.
  Production promotion remains a separate approval-controlled operation.
