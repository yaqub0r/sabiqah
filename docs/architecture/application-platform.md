# Application platform

Status: **Accepted for beta implementation**

Tracking issue: [#12](https://github.com/yaqub0r/sabiqah/issues/12)

## Decision

Sabiqah is the public reader and collaborative-review application. Al-Isabah
and future book repositories own canonical scholarly data, evidence, pull
requests, and versioned releases. FirstLight consumes pinned releases rather
than Sabiqah's operational database.

The beta uses:

- Astro for static-first public reading pages;
- React for the specialized segment review editor;
- Decap as a replaceable GitHub fork/pull-request workflow shell;
- one Cloudflare Worker for static assets and `/api/*` routes;
- D1 for identities, memberships, moderation state, and append-only reputation
  evidence;
- R2 for large versioned assets, never for application source or secrets.

This is intentionally one deployable Worker at first. Splitting the API, admin,
and reader would add authentication boundaries and operational overhead before
traffic or team ownership requires them.

## Boundaries

```text
book repository -> signed/versioned release -> Sabiqah reader
       ^                                      |
       |                                      v
       +---------- fork + pull request <- editor/Decap

GitHub identity -> Sabiqah Worker -> D1 membership and reputation events
large evidence ------------------> R2 immutable/versioned objects
```

The platform-neutral release model and React editor may not import Decap. The
Decap adapter translates between its widget API and a review proposal. That
keeps scholarly records portable if the workflow shell changes.

## Deployment and rollback

Development deploys are promoted from reviewed commits. Production remains a
separate protected GitHub environment and is not enabled during the initial
vertical slice. Cloudflare Worker versions provide code rollback; D1 migrations
are forward-only, small, and deployed before code that requires them. A release
must remain compatible with the immediately previous schema version.

## Authentication boundary

The enrollment code proves possession of an invitation, not identity. Turnstile
and edge rate limiting slow guessing; D1 is authoritative for membership.
GitHub's numeric user ID becomes the durable external identity after OAuth.
Handles and avatars are mutable profile data.

Decap needs a GitHub OAuth access token to create a fork and pull request. The
Worker returns that token only to the same-origin Decap popup and does not store
it. The current OAuth scope is broader than ideal for a single book repository;
a narrowly-permissioned GitHub App is the preferred future replacement when it
can support the chosen Decap/Open Authoring path.

Decap 3.15 also retains older UI dependencies. The workspace overrides its
vulnerable `immutable` and `trim` transitive versions, runs a high-severity
production audit in CI, and verifies the CMS login runtime in a browser. Build
warnings about legacy `eval` branches remain isolated to the CMS chunk and must
be reevaluated before a strict content-security policy or production promotion.

## Review and reputation

All active enrolled members may propose reviews. Repository maintainers retain
merge authority. Accepted changes and review discussion remain in each book
repository. D1 stores cross-book evidence events such as enrollment, submitted
review, maintainer acceptance, reversal, and moderation action.

AI assessment is advisory metadata on an event. It can prioritize human review
and flag patterns, but it cannot by itself revoke access, declare scholarship
correct, or set a canonical record to verified.
