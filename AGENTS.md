# Repository workflow

## Issue-first development

Every repository change must be associated with a GitHub issue before work
begins. Keep work within the issue scope and reference the issue in commits and
pull requests.

## Infrastructure safety

- Treat architecture records as proposals until their status is Accepted.
- Use infrastructure as code for repeatable cloud changes.
- Run validation and a plan before applying infrastructure changes.
- Require explicit approval for production applies, identity changes, public
  access changes, destructive operations, and changes that expand trust.
- Prefer short-lived credentials, least-privilege roles, and workload identity.
- Never commit credentials or secret values.
- Record role purpose and policy intent, but not credentials or personal
  recovery information.

## Content governance

- Follow `docs/architecture/content-governance.md` when acquiring, comparing,
  translating, promoting, or presenting scholarly content.
- Treat public availability as provenance, not permission to reproduce, adapt,
  or redistribute an artifact.
- Keep restricted research witnesses and private comparison evidence out of
  public repositories and deployment artifacts.
- Promote content into a canonical book repository only through an explicit,
  reviewable manifest; never silently overwrite canonical book content.

## Delivery

Use feature branches and pull requests after the repository bootstrap commit.
Do not bypass required checks or environment protections. Keep generated state,
local runtime data, and infrastructure state files out of Git.
