# Cloud foundation

Status: **Accepted for initial implementation**

Tracking issue: [#1](https://github.com/yaqub0r/sabiqah/issues/1)

## Decision

Sabiqah begins as a Cloudflare-native application. Cloudflare will provide DNS,
edge application hosting, server-side functions, and R2 object storage. AWS is
not part of the initial architecture.

This keeps storage and delivery inside one provider and reduces identity and
billing boundaries. AWS may be introduced later only when a concrete
requirement outweighs the added operational cost.

## Initial topology

```text
GitHub repository
      |
      | reviewed deployment
      v
Cloudflare Worker -----------> private R2 buckets
      |                              |
      +---------- Cloudflare DNS ----+
                      |
       dev.sabiqah.org / sabiqah.org
```

GitHub remains the change-control plane. Application source and small,
reviewable scholarly data live in Git. Large facsimiles, page images, and
derived binary artifacts live in R2.

## R2 storage layout

Initial buckets should be private and separated by environment:

- `sabiqah-infra-state`: OpenTofu state and locking
- `sabiqah-assets-dev`: development facsimiles and derived assets
- `sabiqah-assets-prod`: approved production assets

Object keys should be immutable or content-addressed so a citation cannot
silently point at different bytes. Example:

```text
works/al-isabah/sources/<sha256>/volume-08.pdf
```

Public delivery should use a Cloudflare custom domain or Worker rather than
public R2 API credentials. CORS, cache behavior, and download authorization must
be reviewed before public access is enabled.

## Change and trust path

```text
Developer or Codex session
        |
        v
Pull request -> validation and deployment preview
        |
        v
Protected GitHub environment approval
        |
        v
Scoped Cloudflare token -> Pages / Workers / R2
```

Bootstrap credentials are temporary. Routine deployments must use narrower
tokens that cannot administer account membership or billing. DNS stays
owner-managed until Cloudflare account-owned tokens can be scoped to zone DNS.

## Bootstrap record

On 2026-08-10 and 2026-08-11:

- the Cloudflare account owner completed MFA and recovery setup;
- the `sabiqah.org` zone was added on the Cloudflare Free plan;
- eight imported Namecheap parking and email-forwarding records were removed;
- Namecheap was configured to delegate to `chip.ns.cloudflare.com` and
  `sureena.ns.cloudflare.com`;
- public DNS and the Cloudflare dashboard confirm that the zone is active;
- DNSSEC is active at Cloudflare and the `.org` parent publishes the matching DS
  record;
- strict SPF, DMARC, and null-MX records declare that the domain sends and
  receives no email;
- GitHub `development` and owner-approved `production` environments were
  created, with production deployments restricted to `main`;
- R2 billing was activated with owner approval and a $1 monthly billable-usage
  alert was configured;
- private `sabiqah-infra-state`, `sabiqah-assets-dev`, and
  `sabiqah-assets-prod` buckets were created with public development URLs
  disabled;
- OpenTofu state, planning, apply, and bucket-scoped publisher credentials were
  stored only in their protected GitHub environments and passed access-isolation
  tests;
- a scoped development deployer was limited to D1 Write and Workers Scripts
  Write, with no membership, billing, or DNS permission;
- the reviewed `sabiqah-dev` Worker was deployed at `dev.sabiqah.org` with D1,
  Turnstile, GitHub OAuth, and protected GitHub environment configuration;
- production remained protected and undeployed.

No credentials, account recovery data, or personal contact information belong
in this record.

The bootstrap was completed under issue #1 without creating a broad temporary
operator token. Routine operations now use the documented scoped credentials,
reviewed workflows, rotation reminders, and recovery runbooks.

## Decisions still required before production

- R2 custom-domain and public-delivery policy
- production retention, backup, and recovery objectives
- whether and when a narrower GitHub App can replace Decap's OAuth
  `public_repo` scope
