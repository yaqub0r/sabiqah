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

Reading the validated public-working corpus requires no account or invitation.
The Worker reads it from a private R2 origin and serves its summary, index,
sections, items, and aggregate approval counts anonymously. Neither browser code
nor readers receive R2 credentials or direct object URLs. Membership status is
irrelevant to read access; the invitation authorizes review and correction
actions only.

An active reviewer may record or withdraw approval of an English translation
through a same-origin Worker endpoint. The Worker first verifies the item in
the pinned public-working corpus, then appends a D1 event containing its immutable
corpus ID, stable item ID, and object digest. Repeated identical decisions are
idempotent. Reviewers can see aggregate current approval counts and their own
current decision, but not another reviewer's identity. Approval does not grant
merge, publication, or moderation authority.

## Selected-text reports

An active reviewer may select Arabic or English text in the public reader and
submit a categorized report. The browser sends the stable corpus, record,
segment, field, language, selected text, surrounding context, reader URL, and
reviewer comment to the same-origin Worker. The Worker derives the reporter
from the signed session, verifies the selection against the pinned R2 corpus,
rejects stale or cross-record input, rate-limits by durable GitHub user ID, and
creates one issue in the Sabiqah repository.

The GitHub credential is a server-only fine-grained token restricted to the
Sabiqah repository with Issues write and Metadata read. It is stored as the
`GITHUB_ISSUES_TOKEN` Worker secret and is never returned to the browser. A
report is unadjudicated workflow evidence; approved canonical changes still
move through the individual book repository's review and release process.

To enable this feature in an environment, create the credential with the scope
above, store it with `wrangler secret put GITHUB_ISSUES_TOKEN`, deploy through
the protected environment, submit one known test report, verify its structured
location and escaped content, and then close the test issue. Rotate by creating
and verifying a replacement before revoking the old token.

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
