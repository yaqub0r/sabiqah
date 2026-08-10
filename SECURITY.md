# Security policy

## Never commit secrets

Do not commit or paste any of the following into this repository, issues, pull
requests, CI logs, or documentation:

- Cloudflare API tokens, R2 access keys, or R2 secret keys
- passwords, MFA seeds, backup codes, or account recovery codes
- private keys, signing keys, webhook secrets, or database credentials
- unredacted environment files or Terraform/OpenTofu state

If a secret is exposed, revoke or rotate it first. Removing it from the latest
commit is not sufficient because Git history, forks, caches, and logs may retain
it.

## Allowed access documentation

The repository may contain non-secret operational metadata such as:

- role and permission-set names
- intended permissions and trust relationships
- environment and resource names
- account aliases and non-sensitive identifiers when operationally necessary
- onboarding, revocation, rotation, and recovery procedures
- the names of secret stores and CI secret variables, but never their values

## Credential model

- The account owner uses a named Cloudflare login protected by MFA; recovery
  material stays outside the repository.
- Codex-assisted bootstrap uses an account-owned Cloudflare API token that is
  temporary, narrowly scoped, and revoked when bootstrap is complete.
- Routine automation uses separate tokens per workload and environment.
- R2 credentials are bucket-scoped and never exposed to browser code.
- Production writes require a protected GitHub environment and approval.

## Reporting

Until a private reporting channel is published, do not open a public issue that
contains exploit details or credentials. Contact the repository owner directly.
