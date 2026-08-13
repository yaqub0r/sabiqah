# Private evidence ingestion contract

Status: **Active**

Tracking issue: [#62](https://github.com/yaqub0r/sabiqah/issues/62)

## Purpose

This contract governs preservation of lawfully acquired research evidence that
cannot be published. It keeps acquisition work reproducible without putting
restricted source material, storage locators, or credentials in Git.

## Transfer paths

- Repository-reproducible artifacts may be transferred by a narrowly scoped
  GitHub Actions workload.
- Workstation-only evidence must be transferred directly from the acquisition
  workstation with the local ingestion command. It must not be staged in a
  GitHub repository or Actions artifact.
- A credential created for one path must not be copied into the other path.

## Eligibility

The local path accepts only manifests whose `classification` is
`private-reference`, `permission-required`, or `unresolved` and whose
`publicationEligibility` is `blocked`. Public or publication-eligible material
belongs in a public-content workflow, not this private evidence store.

An evidence manifest must include:

- schema version and stable evidence identifier;
- acquisition date, purpose, provenance, and rights assessment;
- every preserved file's relative name, byte count, and SHA-256 digest; and
- no unlisted files or links that escape the evidence directory.

## Storage invariant

Development ingestion is fixed to the private `sabiqah-assets-dev` bucket and
the key shape
`research-evidence/<collection>/<evidence-id>/<evidence-id>.zip`. The command
must fail closed for production, an unexpected bucket, an invalid collection,
or an ambiguous rights classification.

The archive is deterministic. Before upload, the command checks the destination
key. A missing key may be created. An existing key is accepted only when its
stored SHA-256 metadata and byte count equal the local archive; otherwise the
operation fails without overwriting it. After a new upload, the command downloads
the object and verifies its SHA-256 digest.

The command writes a local, ignored receipt containing metadata only. It never
deletes source evidence, makes the bucket public, or records a private object
locator in Git.

## Identity boundary

Local ingestion uses the named AWS shared-credentials profile
`sabiqah-r2-dev`. Its Cloudflare R2 credential is account-owned, limited to
Object Read & Write on `sabiqah-assets-dev`, and excluded from production,
bucket administration, DNS, membership, and billing.

Secret values must not be committed, logged, passed on a command line, copied
into chat, or stored as GitHub secrets. The credential register records only
purpose, scope, owner, location, and rotation metadata.

## Recovery and rotation

Keep a recovery copy under the account owner's control. Rotate by creating a
replacement with the same or narrower scope, verifying a read/write round trip,
updating the local profile, and then revoking the old credential. Suspected
disclosure requires immediate revocation and a review of Cloudflare audit logs.
