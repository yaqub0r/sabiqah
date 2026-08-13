# Sabiqah

Sabiqah is the governed acquisition-to-publication system for open scholarly
Islamic editions. It supports source discovery and acquisition, rights
assessment and clearance, private research evidence, textual comparison,
translation and review, promotion into canonical book repositories, and public
presentation. It begins with the Al-Isabah edition while remaining independent
of any single work.

Sabiqah does not treat public availability as permission to reproduce or
redistribute material. Research witnesses that are not approved for public
release remain outside public repositories and deployment artifacts. See the
[content-governance operating model](docs/architecture/content-governance.md)
for repository responsibilities and trust boundaries.

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
- Secret-handling policy: [`SECURITY.md`](SECURITY.md)
- Application architecture: [`docs/architecture/application-platform.md`](docs/architecture/application-platform.md)
- Content-governance model: [`docs/architecture/content-governance.md`](docs/architecture/content-governance.md)
- Repository contracts: [`docs/contracts/INDEX.md`](docs/contracts/INDEX.md)
- Book release contract: [`docs/architecture/book-release-contract.md`](docs/architecture/book-release-contract.md)
- Honorific semantics and presentation: [`docs/architecture/honorific-presentation.md`](docs/architecture/honorific-presentation.md)
- Reviewer access model: [`docs/security/reviewer-access.md`](docs/security/reviewer-access.md)

## Project boundaries

- **Sabiqah** governs acquisition, rights assessment, private research
  evidence, comparison, translation and review workflows, promotion, and the
  reader/editor application.
- **Al-Isabah** owns its approved canonical scholarly dataset, book-specific
  provenance and editorial history, and versioned releases.
- **FirstLight** consumes pinned scholarly releases as a downstream product.
- Restricted research witnesses belong in governed private storage, never in a
  public Git repository or deployment artifact. Approved public facsimiles and
  page images belong in versioned object storage rather than Git.

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
