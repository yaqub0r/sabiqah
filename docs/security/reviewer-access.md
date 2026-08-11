# Reviewer enrollment and access

## Beta policy

Sabiqah uses a reusable global invitation code so trusted participants may pass
access word of mouth. The code is a community boundary, not a strong identity
factor. The safeguards are:

1. Turnstile verification and edge rate limiting before OAuth;
2. an HMAC digest of the normalized code, never the plaintext code, in Worker
   secrets;
3. GitHub OAuth binding to the immutable numeric GitHub user ID;
4. short-lived signed enrollment state and an HTTP-only signed session cookie;
5. D1 membership status (`active`, `limited`, or `suspended`) checked on every
   protected request;
6. a rotation runbook and append-only audit/reputation events.

Anyone with active membership may review by default. This does not grant merge,
Cloudflare, R2, D1, or repository-administration access. Open Authoring creates
a user-owned fork and pull request. Book maintainers decide what becomes
canonical.

## Limitations and response

A global code can leak and cannot identify who shared it. If abuse appears,
rotate the digest, keep existing legitimate memberships active, rate-limit new
enrollment, and moderate individual GitHub identities. Do not mass-revoke
existing reviewers merely because the code changed.

AI-derived quality signals may be attached to evidence events, but access is
limited only by an explainable policy and a human-reviewable moderation event.
Users must have a route to appeal or correct mistaken attribution before the
system is used beyond a small beta.

## Secret placement

GitHub OAuth client secrets, the invite-code pepper and digest, the session
secret, and the Turnstile secret are Cloudflare Worker secrets. Local copies
belong only in the ignored `.dev.vars`. Recovery codes belong in the owner's
password manager, not this repository, GitHub Actions, D1, or R2.
