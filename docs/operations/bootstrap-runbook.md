# Cloudflare bootstrap and recovery runbook

Tracking issue: [#1](https://github.com/yaqub0r/sabiqah/issues/1)

## Verified foundation

- The Cloudflare owner login is protected by MFA and recovery material.
- Namecheap delegates `sabiqah.org` to `chip.ns.cloudflare.com` and
  `sureena.ns.cloudflare.com`.
- Cloudflare reports that traffic for `sabiqah.org` is behind Cloudflare.
- Imported registrar parking and email-forwarding DNS records were removed.
- DNSSEC is active and the parent DS record matches Cloudflare key tag 2371,
  algorithm 13, and digest type 2.
- The domain publishes null MX, `v=spf1 -all`, and a strict `p=reject` DMARC
  policy while email is intentionally disabled.
- Namecheap domain privacy, auto-renew, and transfer lock are enabled.
- GitHub has separate `development` and owner-approved `production`
  environments; production accepts deployments only from `main`.
- GitHub secret scanning and push protection are enabled.
- R2 is active, and the private Standard `sabiqah-infra-state` bucket is the
  dedicated OpenTofu state backend.
- A $1 monthly R2 billable-usage alert notifies the account owner.
- The R2 planning token is read-only in `development`; the R2 write token is in
  `production`. Both are account-owned and expire on 2026-11-08.
- The development planning token successfully lists R2 buckets after activation.
- The state backend credential has Object Read & Write only on
  `sabiqah-infra-state`, is stored in both protected GitHub environments, and
  expires on 2027-02-10.

## R2 bootstrap

1. The owner approves and activates the usage-billed R2 subscription.
2. Manually create only the private Standard `sabiqah-infra-state` bucket.
3. Keep `r2.dev` public access disabled on every bucket.
4. Create an R2 Object Read & Write token scoped only to
   `sabiqah-infra-state` for the OpenTofu backend.
5. Store its S3-compatible access key ID and secret access key directly in the
   protected GitHub environments. Do not expose them to the Cloudflare provider.
6. Run the speculative plan, merge it, and use the owner-approved production
   apply workflow to create `sabiqah-assets-dev` and `sabiqah-assets-prod`.
7. Verify state locking with two concurrent speculative plans after the first
   apply.

## Credential bootstrap

1. Create an account-owned planning token with Workers R2 Storage Read and put
   it directly in the GitHub `development` environment.
2. Create an account-owned apply token with Workers R2 Storage Write and put it
   directly in the owner-approved `production` environment.
3. Exclude billing, membership, and API-token administration permissions.
4. Give both tokens a 90-day expiry and rotate them before expiration.
5. Keep DNS owner-managed because account-owned tokens currently do not expose
   zone-scoped DNS permissions; do not place a human user token in CI.
6. Create bucket-scoped publishing and validation credentials after the buckets
   exist.
7. Test every credential with an allowed operation and a deliberately denied
   operation.
8. Revoke any temporary bootstrap credential and confirm subsequent use fails.

## DNSSEC activation

DNSSEC was enabled after the Cloudflare zone became active. Both the parent
`.org` delegation and Cloudflare now report the chain as active. A mismatched DS
record can make the entire domain unreachable; remove the registrar DS record
first if rollback is required.

## Recovery order

1. Account owner recovery and MFA.
2. Registrar access and nameserver delegation.
3. Cloudflare zone, DNSSEC, and audit logs.
4. OpenTofu state-bucket access and state integrity.
5. Development deployment, then production deployment.
6. Asset hash verification and application availability.

Do not delete or recreate a production bucket as a first response. Preserve
evidence, revoke compromised access, and prefer restoring configuration from a
reviewed plan.

## Completed deployment verification

- The production apply created `sabiqah-assets-dev` and
  `sabiqah-assets-prod`; a subsequent pair of concurrent plans reported no
  drift while sharing the R2 state lock.
- All three buckets have no custom domain and have the public development URL
  disabled.
- The first malformed state-credential transfer was detected by the plan gate,
  replaced, verified, and permanently revoked before any apply.
