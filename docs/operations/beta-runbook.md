# Beta operations runbook

## Development bootstrap

1. Confirm the `sabiqah-platform-dev` D1 binding in `wrangler.jsonc` matches
   Cloudflare database `fecd6d21-6348-4d47-acb7-95c83055ee6e`.
2. Apply `migrations/0001_beta_identity.sql` with Wrangler.
3. Create a GitHub OAuth app with the development callback URL
   `/api/auth/github/callback`.
4. Store its credentials in the GitHub development environment as
   `OAUTH_GITHUB_CLIENT_ID` and `OAUTH_GITHUB_CLIENT_SECRET`. The deployment
   workflow maps them to the Worker's `GITHUB_CLIENT_ID` and
   `GITHUB_CLIENT_SECRET` names because GitHub Actions reserves the `GITHUB_`
   secret prefix.
5. Configure a Turnstile widget for the development hostname.
6. Generate separate random values for the invite pepper and session secret.
7. Normalize the global code (trim and lowercase), calculate its HMAC-SHA-256
   digest with the pepper, and store only digest and pepper as Worker secrets.
8. Deploy a reviewed commit to the development Worker and complete the smoke
   checks below.

Do not reuse production OAuth, Turnstile, invite, or session secrets in local or
development environments.

## Development deployment record

As of 2026-08-11:

- the canonical development URL is `https://dev.sabiqah.org`, attached to
  Worker `sabiqah-dev`;
- D1 database `sabiqah-platform-dev`
  (`fecd6d21-6348-4d47-acb7-95c83055ee6e`) holds membership and reputation
  evidence;
- the GitHub OAuth callback base is `https://dev.sabiqah.org/api`, covering the
  enrollment and Decap callbacks;
- GitHub environment `development` accepts deployments only from `main` and
  stores the runtime secrets; the global invite plaintext exists only in the
  owner's password manager;
- deployment run `31533205409` migrated D1, deployed the Worker and assets,
  installed runtime secrets, and passed the canonical health check;
- public pages and all three fixture states returned successfully, invalid
  enrollment failed generically, GitHub enrollment created one active member
  and one append-only enrollment event, and the live editor enforced evidence
  for protected Arabic corrections;
- production remained protected and unchanged.

## Private review-corpus deployment

The development deployment exports the review corpus from the exact
`yaqub0r/al-isabah` revision pinned in the workflow. The export includes draft
Arabic and English, machine findings, and the recorded translation workflow,
but excludes raw restricted witnesses and private comparison artifacts. It is
validated before upload to the private `sabiqah-assets-dev` R2 bucket under an
immutable corpus ID.

To update the corpus, first review and merge the source work in the book
repository, then change both the pinned source revision and corpus ID in a
Sabiqah pull request. Never overwrite or delete a deployed corpus in place.
Deploy the new immutable objects before switching the Worker to them. A rollback
therefore restores the preceding Worker version, whose corpus ID still resolves
to the preceding immutable objects.

The public summary endpoint must expose only inventory and coverage counts. The
index and item endpoints must return `403` without an active reviewer session;
limited and suspended members must receive the same denial. Do not place R2
credentials, object keys, draft text, or source witnesses in deployment logs.

## Smoke checks

- Public work inventory loads without a session and contains no corpus text.
- Anonymous access to the corpus index and every item returns `403`.
- An active reviewer can filter the complete index and open bilingual items,
  unresolved work, provenance, and workflow history.
- A wrong invite fails without revealing whether Turnstile or the code failed.
- A correct invite completes GitHub OAuth and creates one active membership.
- Repeating OAuth updates mutable profile data without duplicating identity.
- The editor can create a translation proposal and requires evidence for an
  Arabic correction.
- Decap can create a fork-based draft pull request in the book repository.
- No GitHub access token is present in Worker logs or D1.
- Suspending a membership invalidates protected API use on the next request.

## Rollback

Roll back application code to the preceding Cloudflare Worker version. D1
migrations are not reversed in production; deploy compatibility code or a new
forward migration. Rotate the session secret only when invalidating all sessions
is intended. Rotate the invite code without changing existing memberships.

## Global invite rotation

1. Choose a new high-entropy but speakable code and store it in the owner's
   password manager.
2. Generate a new pepper and HMAC digest locally, away from shell history.
3. update both Worker secrets in development; test enrollment and a failed old
   code.
4. Repeat in production through its protected deployment environment.
5. Add an operations event recording who rotated it and why, without either
   plaintext code or digest.
6. Notify administrators and update the existing credential-expiry reminder.

Existing active memberships remain valid unless a separate, documented
moderation decision changes them.
