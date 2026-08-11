# Sabiqah

Sabiqah is the public reader and editorial application for open scholarly
Islamic editions. It begins with the Al-Isabah edition while remaining
independent of any single work.

## Repository status

The Cloudflare account and `sabiqah.org` zone are established. The first beta
application is being built in [issue #12](https://github.com/yaqub0r/sabiqah/issues/12):
an Astro reader, a Decap-independent React review editor, and a small Cloudflare
Worker for enrollment and reviewer evidence.

- Bootstrap issue: [#1](https://github.com/yaqub0r/sabiqah/issues/1)
- Cloud architecture: [`docs/architecture/cloud-foundation.md`](docs/architecture/cloud-foundation.md)
- Access model: [`docs/security/access-model.md`](docs/security/access-model.md)
- Credential rotation: [`docs/operations/credential-rotation.md`](docs/operations/credential-rotation.md)
- Secret-handling policy: [`SECURITY.md`](SECURITY.md)
- Application architecture: [`docs/architecture/application-platform.md`](docs/architecture/application-platform.md)
- Book release contract: [`docs/architecture/book-release-contract.md`](docs/architecture/book-release-contract.md)
- Reviewer access model: [`docs/security/reviewer-access.md`](docs/security/reviewer-access.md)

## Project boundaries

- **Sabiqah** owns the reader/editor application and its deployment.
- **Al-Isabah** owns the canonical scholarly dataset and versioned releases.
- **FirstLight** consumes pinned scholarly releases as a downstream product.
- Large facsimiles and page images belong in versioned object storage, not Git.

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
