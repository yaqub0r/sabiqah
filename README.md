# Sabiqah

Sabiqah is the reader, review, storage, and presentation application for open
scholarly Islamic editions. It verifies and ingests immutable book releases,
preserves consumer-side provenance and rights controls, manages private
research evidence and application state, and presents release content. It
begins with the Al-Isabah edition while remaining independent of any single
work.

Sabiqah does not treat public availability as permission to reproduce or
redistribute material. Research witnesses that are not approved for public
release remain outside public repositories and deployment artifacts. See the
[content-governance operating model](docs/architecture/content-governance.md)
for repository responsibilities and trust boundaries.

## Licensing and public boundary

Sabiqah software is licensed under the
[PolyForm Noncommercial License 1.0.0](LICENSE.md). Any legacy
Sabiqah-authored translations and other intentionally published scholarly
content are licensed under [CC BY-NC-SA 4.0](CONTENT-LICENSE.md). Canonical book
repositories govern new translation authorship and release terms. Third-party
materials retain their existing terms, and private research evidence is
neither published nor licensed. See [NOTICE.md](NOTICE.md) for the complete
boundary.

## Repository status

The Cloudflare foundation and R2 bootstrap are complete. The first development
beta is live at [dev.sabiqah.org](https://dev.sabiqah.org) from reviewed `main`
commits: an Astro reader, a Decap-independent React review editor, and a
Cloudflare Worker for enrollment and reviewer evidence. [Issue
#12](https://github.com/yaqub0r/sabiqah/issues/12) tracks final beta verification;
production remains protected and undeployed.

- Bootstrap issue: [#1](https://github.com/yaqub0r/sabiqah/issues/1)
- Cloud architecture: [`docs/architecture/cloud-foundation.md`](docs/architecture/cloud-foundation.md)
- Access model: [`docs/security/access-model.md`](docs/security/access-model.md)
- Credential rotation: [`docs/operations/credential-rotation.md`](docs/operations/credential-rotation.md)
- Private evidence ingestion: [`docs/operations/private-evidence-ingestion.md`](docs/operations/private-evidence-ingestion.md)
- Secret-handling policy: [`SECURITY.md`](SECURITY.md)
- Application architecture: [`docs/architecture/application-platform.md`](docs/architecture/application-platform.md)
- Content-governance model: [`docs/architecture/content-governance.md`](docs/architecture/content-governance.md)
- Repository contracts: [`docs/contracts/INDEX.md`](docs/contracts/INDEX.md)
- Book release contract: [`docs/architecture/book-release-contract.md`](docs/architecture/book-release-contract.md)
- Al-Isabah governance compatibility: [`docs/architecture/al-isabah-governance-compatibility.md`](docs/architecture/al-isabah-governance-compatibility.md)
- Honorific semantics and presentation: [`docs/architecture/honorific-presentation.md`](docs/architecture/honorific-presentation.md)
- Reviewer access model: [`docs/security/reviewer-access.md`](docs/security/reviewer-access.md)

## Project boundaries

- **Sabiqah** owns verified release ingestion, private-evidence handling,
  application review events, storage, provenance and rights display, and the
  reader/editor presentation.
- **Al-Isabah** owns its translation policy and profile, formula semantics,
  source and rights decisions, per-record scholarly review metadata,
  corrections, canonical dataset, and immutable releases. Sabiqah consumes its
  [versioned upstream governance reference](docs/architecture/al-isabah-governance-compatibility.md)
  and does not govern translation execution.
- Private downstream products may consume pinned scholarly releases without
  becoming owners of Sabiqah workflows, private evidence, or canonical book
  content.
- Restricted research witnesses belong in governed private storage, never in a
  public Git repository or deployment artifact. Approved public facsimiles and
  page images belong in versioned object storage rather than Git.

## Private evidence storage

For workstation-only restricted evidence, read the
[private-evidence ingestion contract](docs/contracts/private-evidence-ingestion.md)
and follow the
[private-evidence ingestion runbook](docs/operations/private-evidence-ingestion.md).
The supported command is `pnpm evidence:preserve`; it validates the evidence
manifest, builds a deterministic archive, stores it in private development R2,
and verifies a downloaded copy by SHA-256.

The command uses the local AWS shared-credentials profile `sabiqah-r2-dev`.
That name and its permission boundary are public metadata; its credential values
must remain outside Git, issues, logs, and chat. Do not substitute a GitHub
Actions or production credential.

## Local development

Prerequisites are Node.js 22.12 or newer and pnpm 11.

```sh
pnpm install --frozen-lockfile
pnpm dev
```

`pnpm dev` runs the Astro reader with fixture data. Worker-backed enrollment is
run separately with `pnpm dev:worker` after copying `.dev.vars.example` to the
ignored `.dev.vars` file and supplying development-only values.

Before opening a pull request, run `pnpm check`.

## Security rule

This public repository may document account aliases, role names, permission
boundaries, resource names, and access procedures. It must never contain access
keys, secret keys, passwords, session tokens, MFA seeds, recovery codes, private
keys, or unredacted secret values.
