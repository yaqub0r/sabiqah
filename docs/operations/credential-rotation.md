# Credential rotation runbook

Tracking issue: [#8](https://github.com/yaqub0r/sabiqah/issues/8)

## Purpose

Rotate Cloudflare and R2 credentials without exposing secret values, losing
OpenTofu state access, interrupting asset publishing, or broadening permissions.
The machine-readable expiry register is
[`ops/credential-expirations.json`](../../ops/credential-expirations.json).

## Reminder and ownership model

The `Credential expiry reminders` workflow runs daily at 13:23 America/New_York
and can also be dispatched manually. At 45, 30, 14, 7, and 0 days it creates or
updates a credential-specific issue, assigns the repository administrator, and
mentions that administrator so GitHub can route an email notification to the
configured administrative mailbox. An overdue credential generates a new
mention each day. The job fails when a credential is within 14 days of expiry.

GitHub email delivery is an account setting. The administrator must enable email
notifications, select the administrative mailbox as the notification address,
and confirm delivery using the workflow's `test` mode.

### Scheduler limitation

GitHub automatically disables scheduled workflows in a public repository after
60 days without repository activity. A scheduled workflow cannot detect its own
disabled state. During the quarterly access review, verify that this workflow is
enabled in the Actions page. Re-enable it with:

```text
gh workflow enable credential-expiry-reminders.yml --repo yaqub0r/sabiqah
```

If this repository may remain inactive for 60 days, move the schedule to an
independent administrative scheduler or make the repository private. Do not
represent this GitHub schedule as a standalone paging system.

## Rotation safety rules

- Never paste a token or key into Git, an issue, a pull request, workflow input,
  command argument, log, or chat.
- Create the replacement before revoking the active credential.
- Match or reduce the existing scope; never add billing, membership, token
  administration, bucket deletion, or unrelated bucket access.
- Give the replacement a finite expiry and record that date in the manifest and
  credential register in the same reviewed change.
- Verify an allowed operation and an expected denial before revocation.
- Treat production secret replacement and credential revocation as separate,
  auditable steps with owner approval.
- If verification fails, leave the existing credential active, revoke the
  failed replacement, and investigate. Do not widen its permissions.

## Standard rotation procedure

1. Open or use the generated credential-specific issue. Record scope, owner,
   reason, and intended expiry—but no secret value.
2. In the Cloudflare owner session, create an account-owned replacement with
   the same resource boundary and the shortest practical lifetime.
3. Transfer the new value directly into the matching GitHub environment secret.
   Use a one-time local file only when direct transfer is unavailable; validate
   its path and shape, overwrite it, and delete it immediately afterward.
4. Run the credential's verification path below.
5. Confirm the consumer works with the replacement. Existing data and the old
   credential remain unchanged during this check.
6. Revoke the old Cloudflare credential by its exact name. Verify that it is no
   longer listed as active.
7. Update `ops/credential-expirations.json`, the credential register, and the
   generated issue with the new expiry and verification evidence.
8. Merge the metadata update through a pull request, then close the rotation
   issue as completed.

GitHub encrypted secrets cannot be read back. If a newly stored replacement is
invalid, create another replacement; do not depend on restoring the prior value.

## Verification by credential class

### Infrastructure planning token

Replace `CLOUDFLARE_API_TOKEN` in `development`, then dispatch
`cloudflare-credential-smoke.yml` for `development` and run
`infra-plan.yml`. Success requires R2 listing and a no-drift plan. The token must
remain read-only.

### Infrastructure apply token

Replace `CLOUDFLARE_API_TOKEN` in `production`. Dispatch the credential smoke
test and approve the production environment. Run a protected no-drift plan
before any apply. Do not create a change merely to test the token.

### OpenTofu state credential

The same state credential is stored as `AWS_ACCESS_KEY_ID` and
`AWS_SECRET_ACCESS_KEY` in both environments. Replace development first and run
a no-drift plan. Replace production only after development succeeds, approve a
second no-drift plan, and then revoke the old state credential. A failed state
credential prevents initialization but does not delete state or buckets.

### Development publisher

Replace `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` in `development`, then run
`r2-publisher-smoke.yml` for `development`. It must list
`sabiqah-assets-dev` and be denied access to `sabiqah-assets-prod`.

### Production publisher

Replace `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` in `production`, approve
the protected publisher smoke test, and confirm it can list only
`sabiqah-assets-prod`. Revoke the old credential only after that test passes.

## Emergency and expired-credential recovery

If exposure is suspected, prioritize revocation over zero downtime. Disable the
affected workflow, preserve Cloudflare audit logs and GitHub deployment records,
create a narrower replacement, and rerun both allowed and denied checks.

If a credential has already expired:

1. Use the MFA-protected Cloudflare owner account to create a replacement.
2. Restore state access first, then development, then production.
3. Run no-drift plans before resuming applies or publishing.
4. Inspect audit logs for failed or unexpected use around expiration.
5. Record the missed reminder or scheduler failure as an incident and correct
   the operational control before closing the rotation issue.

Never delete or recreate an R2 bucket to recover from credential expiry.
