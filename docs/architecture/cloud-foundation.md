# Cloud foundation

Status: **Proposed**

Tracking issue: [#1](https://github.com/yaqub0r/sabiqah/issues/1)

## Goals

- Establish an auditable, least-privilege path from human approval to cloud
  changes.
- Avoid long-lived AWS credentials and shared administrator users.
- Keep AWS and Cloudflare as separate trust boundaries.
- Make infrastructure changes reviewable and reproducible.
- Prevent accidental public exposure of source material or editorial data.

## Trust boundaries

### AWS account

The AWS account hosts application compute, application data, secrets, logs, and
monitoring selected during later design. The account root user is break-glass
only, protected by phishing-resistant MFA, and is not used for routine work.

Human access should be provided through IAM Identity Center permission sets.
Codex should use a short-lived session initiated and approved by a human, not a
stored IAM access key.

GitHub Actions should assume dedicated IAM roles through GitHub's OIDC provider.
The trust policy must restrict the repository, environment, and allowed refs.
Planning and applying infrastructure should use different roles.

### Cloudflare account and R2

R2 is a Cloudflare service, not an AWS resource. It therefore has its own
identity, audit, billing, and recovery boundary.

Initial buckets should be private. Candidate separation:

- `sabiqah-assets-dev`: non-production test facsimiles and derived images
- `sabiqah-assets-prod`: production facsimiles and derived images

Object keys should be immutable or content-addressed so a citation cannot
silently begin pointing at different bytes. A typical shape is:

```text
works/al-isabah/sources/<sha256>/volume-08.pdf
```

Use separate bucket-scoped credentials for publishing and validation. Never put
an R2 secret in browser code. Public delivery should eventually use a custom
domain or narrowly designed delivery layer, with CORS and caching reviewed before
public access is enabled.

### GitHub

GitHub is the change-control plane, not a secret store for AWS user keys.

- Pull requests run validation and infrastructure plans.
- Protected environments gate infrastructure applies.
- AWS authentication uses OIDC and short-lived role sessions.
- A narrowly scoped Cloudflare token may need to be held as an environment
  secret unless a stronger workload-identity option is confirmed.
- Production applies require explicit approval.

## Proposed change path

```text
Developer or Codex session
        |
        v
Pull request -> validation + infrastructure plan
        |
        v
Protected GitHub environment approval
        |
        +--> AWS OIDC apply role -> AWS resources
        |
        +--> scoped Cloudflare credential -> R2 resources
```

## Bootstrap sequence

1. Secure and verify the AWS root account, recovery contacts, and MFA.
2. Enable IAM Identity Center and create named permission sets.
3. Establish a short-lived operator session for Codex-assisted bootstrap.
4. Choose and initialize infrastructure as code.
5. Add GitHub OIDC with repository/ref/environment restrictions.
6. Create development resources first, including a private R2 bucket.
7. Enable audit logging, budget alerts, and secret scanning.
8. Validate restore, revocation, and deployment procedures.
9. Create production resources only after the development path is reviewed.

## Decisions still required

- AWS Organizations/multi-account now versus a single workload account initially
- primary AWS region and recovery-region expectations
- OpenTofu/Terraform versus AWS CDK for infrastructure as code
- application compute, database, search, and authentication services
- R2 custom-domain and public-delivery policy
- production approval owners and recovery contacts
