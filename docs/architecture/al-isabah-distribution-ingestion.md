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

## Safety and rollback

- Archives are extracted with a strict member allowlist and traversal checks.
- Manifests, shard checksums, record counts, licenses, source authority, stable
  identities, and public-output state are validated before any upload.
- Existing immutable prefixes are never overwritten with different bytes.
- Activation occurs only after an R2 download-and-validate round trip.
- Rollback changes the pointer to a previously verified immutable prefix; it
  does not delete or rewrite corpus objects.
- The initial automation targets only the protected `development` environment.
  Production promotion remains a separate approval-controlled operation.
