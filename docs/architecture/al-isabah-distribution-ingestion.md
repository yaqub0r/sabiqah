# Al-Isabah distribution ingestion

- **Status:** Accepted
- **Issues:** [#114](https://github.com/yaqub0r/sabiqah/issues/114),
  [#123](https://github.com/yaqub0r/sabiqah/issues/123),
  [#125](https://github.com/yaqub0r/sabiqah/issues/125),
  [#129](https://github.com/yaqub0r/sabiqah/issues/129),
  [#131](https://github.com/yaqub0r/sabiqah/issues/131), and
  [#133](https://github.com/yaqub0r/sabiqah/issues/133)

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

Sabiqah pins the book repository's
[versioned translation-governance reference](al-isabah-governance-compatibility.md)
for consumer compatibility. The pin does not make the local adapter or review
overlay authoritative for translation execution, per-record scholarly
metadata, corrections, or release class.

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

## Mixed provenance and rights cohorts

Reader-corpus schema `5.0.0` represents a combined corpus as an ordered set of
provenance and rights cohorts. Each item and index entry carries exactly one
`cohortId`. Each cohort records its stable ID, source authority, producer
authority when applicable, repository, commit, artifact hash, Arabic rights,
English authorship and rights, rights-matrix decision, publication and
promotion state, completeness state, and upstream release or legacy-corpus
identity. Its sorted item-ID inventory is bound by an exact count and SHA-256.
The corpus object deliberately has no global source, license, attribution, or
rights-matrix field.

When a schema-2 Al-Isabah distribution is partial, ingestion projects and
validates the complete incoming stable-ID inventory before changing cohort
membership. Incoming entries and structural passages replace carried items
with the same stable IDs; duplicate IDs inside the incoming projection fail
closed. Other records are carried forward in their existing cohorts. The first
schema-5 construction migrates the active schema-4 corpus into a
`legacy-schema-4` cohort only after every carried record matches that corpus's
already verified source and rights metadata. It adds the cohort reference and
explicit repository/commit binding without changing the record's authority,
artifact hash, attribution, license, rights matrix, review state, or promotion
state. Legacy records are never assigned to the new distribution cohort.

The deployed schema-4 corpus predates complete corpus-level rights metadata and
therefore cannot use that generic path. Its only compatibility path is the
versioned one-time attestation at
`evidence/legacy-bindings/al-isabah-active-schema-4.v1.json`. The network-free
verifier binds the exact active pointer, schema, six core-object hashes,
complete manifest inventory, member count and ID/content digests, section
inventory, source authority, activation run, legacy release/tag/asset digest,
rights-policy blobs, approval identity, and one allowed schema-2 target release.
It recomputes the corpus inventory and checks supplied GitHub metadata; a name
or corpus-ID match alone has no authority.

Existing alignment evidence divides the bound corpus into two legacy cohorts:
the 1,565-record Sabiqah v11 remediation and the 1,731-record Al-Isabah af7
distribution lineage. They retain separate producer and English-attribution
claims while sharing the independently verified OpenITI Arabic authority and
Arabic rights. All 3,296 records remain explicitly unreviewed, public-working,
and promotion-blocked. The attestation does not make a legal conclusion,
approve restricted evidence or modern apparatus, claim ACO/OpenITI edition or
page identity, or transfer schema-2 provenance to legacy members.

The binding is applicable only while the exact schema-4 pointer is active and
only with `public-working-623e4d341e24b33496629036aa8bb1dd3a405f2c` as the
schema-5 target. Repeating the same offline construction is deterministic, but
using the binding with a changed pointer, member, object, claim, target, or a
schema-5 base fails closed. The resulting corpus manifest and activation plan
record the binding ID and file digest.

A later approved correction may replace the same stable ID. The new cohort
then records the superseded cohort and the exact count, sorted IDs, and hash;
the earlier cohort and its immutable upstream corpus remain recorded even when
its current membership becomes empty. Rerunning the same distribution against
its own schema-5 candidate produces the same corpus artifacts.

The immutable candidate ID includes a SHA-256 of the verified distribution
manifest, complete cohort metadata, and every projected item except its derived
corpus ID. The same partial distribution combined with a different base
therefore cannot collide at one R2 prefix, while an identical rebuild remains
idempotent.

Schema-5 validation fails before upload when cohort metadata is missing,
unknown, contradictory, overlapping, unassigned, count- or hash-mismatched;
when a record differs from its cohort's source or rights bindings; when legacy
metadata is rebound; or when the corpus makes a global source or rights claim.
Readers resolve and display the cohort ID and the item-bound Arabic, English,
and rights-matrix metadata. Schema `4.0.0` remains readable and valid for the
current active corpus and rollback. Unknown major versions fail closed.

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

For the one-time schema-4 migration, run
`scripts/verify_al_isabah_legacy_binding.py` with the exact pointer, base corpus,
attestation, legacy release/tag metadata, rights matrix, approval issue,
activation run, and target release/tag/manifest metadata. The ingestion command
invokes this verifier again before it creates output. Compatibility checks are
read-only and offline after those non-content metadata files and corpus objects
have been supplied; they print no corpus content.

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
- The workflow captures the exact active pointer before candidate construction
  and re-reads it immediately before activation. A changed or missing pointer
  fails closed. If the intended immutable corpus is already active, the
  workflow preserves the first activation and rollback pointer byte-for-byte
  instead of replacing it with a later self-referential rollback.
- Rollback changes the pointer to a previously verified immutable prefix; it
  does not delete or rewrite corpus objects. Each planned activation records
  the previously active corpus ID and prefix as explicit rollback metadata.
- The initial automation targets only the protected `development` environment.
  Production promotion remains a separate approval-controlled operation.
- Building or merging schema-5 support does not dispatch ingestion, upload a
  candidate, replace `current.json`, write D1, deploy, or promote content. Those
  remain separately approved operations; the ingestion and publication
  workflows may stay manually disabled while this contract is reviewed.
- After a verified schema-5 pointer supersedes the bound schema-4 corpus, remove
  the workflow's legacy-evidence fetch and arguments in a reviewed cleanup. Keep
  the attestation in Git as historical migration evidence, preserve schema-4
  read/rollback support, and never reuse the attestation to rebuild another
  base or target.

### Inert-run recovery fence

GitHub Actions run `31925000582` was created from the schema-5 compatibility
commit but remained queued without a job after its workflow was disabled. That
immutable snapshot reads the legacy `AL_ISABAH_PUBLIC_CORPUS_URI` DEVELOPMENT
variable and validates its root before any R2 access. While the run exists, the
legacy variable is intentionally set to a non-URI fence value so that the old
snapshot cannot upload or activate if GitHub later schedules it. Current
ingestion and deployment code use the separate
`AL_ISABAH_PUBLIC_CORPUS_ROOT_URI` variable, fixed to the exact DEVELOPMENT
corpus root.

Do not restore or reuse the legacy variable while run `31925000582` exists.
After GitHub reports the run terminal and it has been deleted through the
supported API, verify the active pointer, health, D1 digest, and both workflow
states before removing the legacy variable in a reviewed cleanup. The new root
variable and activation preflight are durable controls and are not retired with
the incident fence.
