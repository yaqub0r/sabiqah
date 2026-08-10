# Cloud foundation

Status: **Accepted for initial implementation**

Tracking issue: [#1](https://github.com/yaqub0r/sabiqah/issues/1)

## Decision

Sabiqah begins as a Cloudflare-native application. Cloudflare will provide DNS,
edge application hosting, server-side functions, and R2 object storage. AWS is
not part of the initial architecture.

This keeps storage and delivery inside one provider, reduces identity and
billing boundaries, and matches the FirstLight design. AWS may be introduced
later only when a concrete requirement outweighs the added operational cost.

## Initial topology

```text
GitHub repository
      |
      | reviewed deployment
      v
Cloudflare Pages / Workers ----> private R2 buckets
      |                              |
      +---------- Cloudflare DNS ----+
                      |
                  sabiqah.org
```

GitHub remains the change-control plane. Application source and small,
reviewable scholarly data live in Git. Large facsimiles, page images, and
derived binary artifacts live in R2.

## R2 storage layout

Initial buckets should be private and separated by environment:

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

On 2026-08-10:

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
- 90-day account-owned R2 planning and apply tokens were stored directly in the
  corresponding GitHub environments;
- R2 activation reached the usage-billed subscription confirmation and has not
  yet been submitted.

No credentials, account recovery data, or personal contact information belong
in this record.

## Remaining bootstrap work

1. Activate R2 after the owner approves usage-based billing.
2. Create the private state, development, and production buckets.
3. Create a temporary, account-owned bootstrap token and store it directly in a
   protected secret store; never place it in Git or chat.
4. Import the bootstrapped resources into the OpenTofu configuration.
5. Create narrow deployment and R2 publishing tokens.
6. Add reviewed plans, protected production deployment, budget alerts, and
   credential-rotation procedures.
7. Validate revocation, restore, and rollback procedures before production use.

## Decisions still required

- Pages versus Workers-first application deployment
- infrastructure-as-code tool and Cloudflare provider version policy
- reader authentication and editorial authorization
- R2 custom-domain and public-delivery policy
- production approval owners, retention, backup, and recovery objectives
