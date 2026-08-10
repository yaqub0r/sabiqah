# Access model

Status: **Accepted for bootstrap**

Tracking issue: [#1](https://github.com/yaqub0r/sabiqah/issues/1)

## Principle

Separate account recovery and identity administration from deployment and asset
publishing. A routine workload must not be able to change billing, invite
members, deploy production, and delete production data.

## Cloudflare identities

| Identity | Purpose | Standing access |
| --- | --- | --- |
| Account owner | Recovery, billing, membership, and emergency revocation | Named login with MFA; no routine automation |
| Bootstrap operator token | Initial DNS, Pages/Workers, R2, and token setup | Temporary account-owned token; revoke after bootstrap |
| Deployment token (development) | Deploy development application resources | Protected development environment |
| Deployment token (production) | Deploy approved production resources | Protected production environment |
| R2 publisher (development) | Read, list, and write development assets | Development bucket only |
| R2 publisher (production) | Publish approved production assets | Production bucket only; no bucket administration |
| R2 validator | Verify hashes and releases | Read/list only on specified buckets |

The bootstrap operator is a service principal represented by an account-owned
API token, not a shared human login. The owner creates and can revoke it. The
token should be limited to the Sabiqah account and zone, expire when practical,
and exclude billing unless a specific task requires it.

## Permission boundaries

- Membership and billing stay with the owner.
- DNS administration is scoped to the `sabiqah.org` zone.
- Development and production use separate deployment credentials.
- R2 object publishing does not include bucket deletion or account settings.
- Public readers never receive Cloudflare or R2 credentials.
- Production changes require a protected GitHub environment and human approval.

GitHub environments named `development` and `production` implement this
separation. The production environment requires approval by the account owner
and accepts deployments only from `main`.

## Secret placement

Store tokens directly in the protected environment that consumes them. Record
only the secret name, owner, scope, creation date, expiry or review date, and
revocation procedure in this repository. Never copy a token value into an issue,
pull request, commit, terminal transcript, or chat.

## Lifecycle requirements

- Every principal has an owner, purpose, scope, and review date.
- Create separate credentials for separate workloads and environments.
- Revoke the bootstrap token as soon as narrow routine tokens are verified.
- Rotate a credential immediately after suspected disclosure.
- Review unused access periodically and remove it.
- Use Cloudflare audit logs and GitHub deployment records to attribute changes
  to a human approval or workload identity.
