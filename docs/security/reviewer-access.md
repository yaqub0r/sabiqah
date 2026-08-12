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

Active membership also grants read access to the private intermediate corpus
through Sabiqah's Worker. The Worker validates the signed session on every
index and item request and reads the pinned corpus from private R2. Limited and
suspended memberships receive no corpus text. The public work page receives
only the non-sensitive summary and coverage counts; neither browser code nor
reviewers receive R2 credentials or direct object URLs.

An active reviewer may record or withdraw approval of an English translation
through a same-origin Worker endpoint. The Worker first verifies the item in
the pinned private R2 corpus, then appends a D1 event containing its immutable
corpus ID, stable item ID, and object digest. Repeated identical decisions are
idempotent. Reviewers can see aggregate current approval counts and their own
current decision, but not another reviewer's identity. Approval does not grant
merge, publication, or moderation authority.

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
