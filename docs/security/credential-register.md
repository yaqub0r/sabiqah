# Credential register

This register contains credential metadata only. Secret values must never be
added to this file, Git, issues, pull requests, workflow logs, or chat.

| Credential name | Scope | Secret location | Owner | Review/rotation |
| --- | --- | --- | --- | --- |
| Bootstrap operator | Temporary Cloudflare account and Sabiqah zone setup | Owner-controlled password manager or ephemeral session only | Account owner | Revoke immediately after routine credentials are verified |
| `CLOUDFLARE_API_TOKEN` (development) | Account-owned token; Workers R2 Storage Read; expires 2026-11-08 | GitHub `development` environment | Account owner | Rotate before expiry or after suspected exposure |
| `CLOUDFLARE_API_TOKEN` (production) | Account-owned token; Workers R2 Storage Write; expires 2026-11-08 | GitHub `production` environment | Account owner | Rotate before expiry with an approved production change |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (state) | Account-owned R2 Object Read & Write on `sabiqah-infra-state` only; expires 2027-02-10 | GitHub `development` and `production` environment secrets | Account owner | Review quarterly; rotate one environment at a time |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` (development publisher) | Account-owned R2 Object Read & Write on `sabiqah-assets-dev` only; expires 2027-02-10 | GitHub `development` environment | Application maintainer | Rotate quarterly or after suspected exposure |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` (production publisher) | Account-owned R2 Object Read & Write on `sabiqah-assets-prod` only; expires 2027-02-10 | GitHub `production` environment | Application maintainer | Rotate quarterly with overlap and verification |
| Validator | R2 object read/list on named asset buckets | Protected CI environment | Application maintainer | Remove if unused; review quarterly |

## Rotation invariant

Create the replacement, verify it with the least privileged operation needed,
update the consuming environment, verify the consumer, and only then revoke the
old credential. Never leave two valid credentials active longer than the
rotation window.

Account-owned tokens do not currently expose zone-scoped DNS permissions in the
Cloudflare dashboard. Do not substitute a broad human user token merely to put
DNS in the same OpenTofu root; DNS stays owner-managed until a workload identity
can be constrained to `sabiqah.org`.

## Emergency revocation

If disclosure is suspected, revoke the credential first. Disable affected
workflows if attribution is unclear, inspect Cloudflare audit logs and GitHub
deployment history, replace the credential with narrower scope, and document
the incident without including secret values.
