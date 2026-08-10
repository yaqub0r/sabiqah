# Sabiqah

Sabiqah is the public reader and editorial application for open scholarly
Islamic editions. It begins with the Al-Isabah edition while remaining
independent of any single work.

## Repository status

This repository is in its security and infrastructure bootstrap phase. No
application or cloud environment has been deployed yet.

- Bootstrap issue: [#1](https://github.com/yaqub0r/sabiqah/issues/1)
- Proposed cloud architecture: [`docs/architecture/cloud-foundation.md`](docs/architecture/cloud-foundation.md)
- Proposed access model: [`docs/security/access-model.md`](docs/security/access-model.md)
- Secret-handling policy: [`SECURITY.md`](SECURITY.md)

## Project boundaries

- **Sabiqah** owns the reader/editor application and its deployment.
- **Al-Isabah** owns the canonical scholarly dataset and versioned releases.
- **FirstLight** consumes pinned scholarly releases as a downstream product.
- Large facsimiles and page images belong in versioned object storage, not Git.

## Security rule

This public repository may document account aliases, role names, permission
boundaries, resource names, and access procedures. It must never contain access
keys, secret keys, passwords, session tokens, MFA seeds, recovery codes, private
keys, or unredacted secret values.
