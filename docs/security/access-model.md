# Access model

Status: **Proposed**

Tracking issue: [#1](https://github.com/yaqub0r/sabiqah/issues/1)

## Principle

Separate the ability to administer identity from the ability to deploy the
application. No shared user should create users, build infrastructure, deploy
production, and read production data.

## Proposed AWS identities

| Identity or permission set | Principal | Purpose | Standing access |
| --- | --- | --- | --- |
| AWS root user | Account owner | Break-glass account recovery and root-only tasks | No routine use |
| `SecurityAdmin` | Named human administrator | IAM Identity Center, trust policies, security controls, emergency revocation | Short-lived SSO session |
| `PlatformAdmin` | Named human/operator | Development infrastructure and operational setup | Short-lived SSO session |
| `Developer` | Named contributor | Development application resources and logs | Short-lived SSO session |
| `AuditReadOnly` | Named reviewer | Configuration, logs, and access review | Short-lived SSO session |
| `SabiqahInfraPlan` | GitHub OIDC | Read configuration and generate pull-request plans | Per-workflow session |
| `SabiqahInfraApplyDev` | GitHub OIDC | Apply reviewed development infrastructure | Per-workflow session |
| `SabiqahInfraApplyProd` | GitHub OIDC | Apply approved production infrastructure | Protected-environment session |

Codex should not receive a permanent AWS identity. The operator signs in through
IAM Identity Center, authorizes a short-lived session, and Codex uses that
session for the approved task. Security administration and normal infrastructure
work should use different permission sets.

## Proposed R2 credentials

| Credential | Scope | Purpose | Storage |
| --- | --- | --- | --- |
| Development publisher | Development bucket, object read/write/list only | Upload and verify development assets | Protected CI environment |
| Production publisher | Production bucket, object read/write/list only | Approved production publishing | Protected production environment |
| Validator | Specific buckets, read/list only | Hash and release verification | Protected CI environment |

Public readers must not receive R2 API credentials. Delete or account-level
administration should remain outside routine publishing credentials.

## Lifecycle requirements

- Every principal has an owner, purpose, scope, and review date.
- Access is granted through groups or roles, not copied policies per person.
- Departures and compromised sessions trigger immediate revocation.
- Permission changes are reviewed separately from application code when they
  expand trust.
- Production access is periodically reviewed and removed when unused.
- Cloud audit records and GitHub deployment records must make each change
  attributable to a human approval or workload identity.
