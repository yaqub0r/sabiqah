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

- Before changing a governed surface, read `docs/contracts/INDEX.md` and every
  contract selected for the changed paths by
  `docs/contracts/contracts.registry.json`. List the applicable contract IDs in
  the pull request.
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

For requested repository implementation, Codex owns the complete delivery
cycle by default. An open or draft pull request is an intermediate state, not
the normal handoff point. Unless a required human approval, protected
environment, or genuine external blocker remains, Codex must:

1. associate the work with an accurately scoped issue;
2. isolate the work on a feature branch or dedicated worktree and preserve
   unrelated changes;
3. run relevant verification and resolve in-scope failures;
4. commit intentionally, push, and open or update a non-draft pull request;
5. monitor required checks and reviews to a terminal state without weakening or
   bypassing a gate;
6. merge with a repository-supported method after all requirements pass;
7. confirm the issue closes through the merged pull request and that remote
   `main` contains the delivered change; and
8. remove merged task branches and worktrees when safe, then fast-forward a
   clean default-branch checkout and report any intentionally retained or
   blocked cleanup.

Full-cycle ownership does not authorize production deployment, release
publication, identity or trust expansion, destructive history changes, secret
handling outside established controls, or overwriting unrelated work. Those
actions continue to require their normal explicit approvals and safeguards.
