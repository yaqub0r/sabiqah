# Cloudflare bootstrap and recovery runbook

Tracking issue: [#1](https://github.com/yaqub0r/sabiqah/issues/1)

## Verified foundation

- The Cloudflare owner login is protected by MFA and recovery material.
- Namecheap delegates `sabiqah.org` to `chip.ns.cloudflare.com` and
  `sureena.ns.cloudflare.com`.
- Cloudflare reports that traffic for `sabiqah.org` is behind Cloudflare.
- Imported registrar parking and email-forwarding DNS records were removed.
- GitHub has separate `development` and owner-approved `production`
  environments; production accepts deployments only from `main`.
- GitHub secret scanning and push protection are enabled.

## R2 bootstrap

1. The owner approves and activates the usage-billed R2 subscription.
2. Create three private Standard buckets: `sabiqah-infra-state`,
   `sabiqah-assets-dev`, and `sabiqah-assets-prod`.
3. Keep `r2.dev` public access disabled on every bucket.
4. Create an R2 Object Read & Write token scoped only to
   `sabiqah-infra-state` for the OpenTofu backend.
5. Store its S3-compatible access key ID and secret access key directly in the
   protected GitHub environments. Do not expose them to the Cloudflare provider.
6. Initialize the backend and import the two asset buckets before the first
   managed plan if they were created manually.
7. Verify state locking with two concurrent speculative plans before enabling a
   production apply workflow.

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

Enable DNSSEC only after the Cloudflare zone is active. Copy the generated DS
record into Namecheap, then verify both the parent `.org` delegation and
Cloudflare report the chain as active. A half-configured DS record can make the
entire domain unreachable; remove the registrar DS record first if rollback is
required.

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
