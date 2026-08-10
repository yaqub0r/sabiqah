# Credential register

This register contains credential metadata only. Secret values must never be
added to this file, Git, issues, pull requests, workflow logs, or chat.

| Credential name | Scope | Secret location | Owner | Review/rotation |
| --- | --- | --- | --- | --- |
| Bootstrap operator | Temporary Cloudflare account and Sabiqah zone setup | Owner-controlled password manager or ephemeral session only | Account owner | Revoke immediately after routine credentials are verified |
| `CLOUDFLARE_API_TOKEN` (development) | R2 bucket administration for development and DNS only when required by an approved plan | GitHub `development` environment | Account owner | Review quarterly and rotate after suspected exposure |
| `CLOUDFLARE_API_TOKEN` (production) | Approved production R2 and DNS changes | GitHub `production` environment | Account owner | Review quarterly; rotate with an approved production change |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (state) | R2 object read/write on `sabiqah-infra-state` only | GitHub environment secrets | Account owner | Review quarterly; rotate one environment at a time |
| Development publisher | R2 object read/write on `sabiqah-assets-dev` only | GitHub `development` environment | Application maintainer | Rotate quarterly or after suspected exposure |
| Production publisher | R2 object read/write on `sabiqah-assets-prod` only | GitHub `production` environment | Application maintainer | Rotate quarterly with overlap and verification |
| Validator | R2 object read/list on named asset buckets | Protected CI environment | Application maintainer | Remove if unused; review quarterly |

## Rotation invariant

Create the replacement, verify it with the least privileged operation needed,
update the consuming environment, verify the consumer, and only then revoke the
old credential. Never leave two valid credentials active longer than the
rotation window.

## Emergency revocation

If disclosure is suspected, revoke the credential first. Disable affected
workflows if attribution is unclear, inspect Cloudflare audit logs and GitHub
deployment history, replace the credential with narrower scope, and document
the incident without including secret values.
