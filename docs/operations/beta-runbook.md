# Beta operations runbook

## Development bootstrap

1. Confirm the `sabiqah-platform-dev` D1 binding in `wrangler.jsonc` matches
   Cloudflare database `fecd6d21-6348-4d47-acb7-95c83055ee6e`.
2. Apply `migrations/0001_beta_identity.sql` with Wrangler.
3. Create a GitHub OAuth app with the development callback URL
   `/api/auth/github/callback`.
4. Configure a Turnstile widget for the development hostname.
5. Generate separate random values for the invite pepper and session secret.
6. Normalize the global code (trim and lowercase), calculate its HMAC-SHA-256
   digest with the pepper, and store only digest and pepper as Worker secrets.
7. deploy a reviewed commit to the development Worker and complete the smoke
   checks below.

Do not reuse production OAuth, Turnstile, invite, or session secrets in local or
development environments.

## Smoke checks

- Public reader loads without a session and all three fixture states render.
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
