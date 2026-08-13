# Private evidence ingestion runbook

Use this runbook for restricted evidence that exists only on an authorized
workstation. GitHub Actions remains the publisher for repository-reproducible
artifacts.

## One-time credential setup

1. In Cloudflare R2, create an account-owned API token named
   `sabiqah-local-acquisition-dev`.
2. Grant **Object Read & Write** only for `sabiqah-assets-dev`. Do not grant
   production, bucket administration, DNS, membership, or billing access.
3. Set an expiry and add its metadata to `ops/credential-expirations.json`.
4. Store the values in the standard AWS shared-credentials profile
   `sabiqah-r2-dev`. Never paste them into chat, source files, shell history, or
   GitHub.
5. Keep the one-time recovery copy in the account owner's approved password
   manager, then close the Cloudflare success page.

The AWS profile is a local plaintext credential file protected by the operating
system account; it is not a Codex-managed vault. Use the host credential store
instead if one is introduced later.

## Validate and preserve

First run the offline validation and deterministic packaging step:

```powershell
pnpm evidence:preserve -- --source "C:\path\to\evidence" --collection al-isabah --dry-run
```

Then upload and verify against development R2:

```powershell
pnpm evidence:preserve -- --source "C:\path\to\evidence" --collection al-isabah --account-id <cloudflare-account-id>
```

Success means the remote object was downloaded again and its SHA-256 digest
matched the deterministic local archive. The metadata-only receipt is written
below `.runtime/private-evidence/` and remains outside Git.

## Failure handling

- Manifest or inventory failure: repair the manifest or evidence directory;
  do not weaken validation.
- Existing-object mismatch: stop. Investigate provenance and choose a new
  evidence ID only when the inputs genuinely represent a different bundle.
- Authentication failure: verify the named profile and token status; do not
  substitute a production or administrator credential.
- Round-trip mismatch: treat the upload as unverified, retain local evidence,
  and investigate before retrying.

The command never removes the local source. Delete redundant local copies only
after verified preservation and an explicit cleanup decision.

## Rotation

Create and verify a replacement before revoking the current token. Run a dry
run and one idempotent remote verification with the replacement, update the
credential register dates, revoke the old token, and confirm it can no longer
access R2. If disclosure is suspected, revoke first and preserve audit evidence.
