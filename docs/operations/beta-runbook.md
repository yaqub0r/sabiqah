# Beta operations runbook

## Development bootstrap

1. Confirm the `sabiqah-platform-dev` D1 binding in `wrangler.jsonc` matches
   Cloudflare database `fecd6d21-6348-4d47-acb7-95c83055ee6e`.
2. Apply `migrations/0001_beta_identity.sql` with Wrangler.
   Apply all later migrations in filename order, including the append-only
   translation-review ledger, before deploying code that uses them.
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

## Private research preservation and public-corpus deployment

The one-time preservation workflow exports the review corpus from the exact
`yaqub0r/al-isabah` research revision recorded in
`evidence/research-snapshots/al-isabah-a3b76bf.v1.json`. It also creates a
restorable Git archive of that revision. Both private objects are validated
against the non-sensitive integrity manifest before and after upload to R2.
The export includes draft Arabic and English, machine findings, and recorded
translation workflow state, but excludes raw restricted witnesses and private
comparison artifacts.

The preservation workflow then rebuilds the reader corpus from that legacy
inventory and the pinned OpenITI source authority in
`evidence/source-authorities/al-isabah.v1.json`. It replaces displayed Arabic,
removes restricted apparatus and locators, enforces the honorific inventory,
records exact observed and rendered honorific forms separately, and emits an
internal quarantine ledger plus a public, metadata-only exclusion report.
Validation fails unless every legacy record is accounted for exactly once as
public or excluded, each exclusion has an explicit disposition, and every public
record is bound to the approved source and license. A literal honorific difference is a
review diagnostic; only a semantic, referent, or agreement concern changes
translation readiness, and working English remains readable.

Ordinary development deployments resolve
`public-corpora/al-isabah/current.json`, then download and validate the selected
immutable public corpus. During pointer migration only, a missing pointer falls
back to `AL_ISABAH_PUBLIC_CORPUS_URI`; a malformed pointer fails the deployment.
Validation covers the complete manifest, source hash, eligibility flags,
quarantine accounting, and absence of forbidden private provenance.
`AL_ISABAH_REVIEW_CORPUS_URI` and
`AL_ISABAH_RESEARCH_SNAPSHOT_URI` remain private preservation inputs; the
runtime reader never serves them.

To update the research corpus, produce a new immutable snapshot and corpus ID in
Sabiqah's governed workflow. Publication-ready records are promoted separately
to the canonical book repository through the canonical-book-promotion contract.
Never overwrite or delete a deployed corpus in place. Upload and verify the new
immutable objects before switching the Worker to them. A rollback therefore
restores the preceding Worker version, whose corpus ID still resolves to the
preceding immutable objects.

For a new Al-Isabah repository distribution, dispatch
`Ingest Al-Isabah public distribution` with the exact GitHub release tag, or
allow its twice-hourly poll to select the latest `public-working` prerelease.
The workflow validates the distribution, merges unchanged volumes from the
active base corpus, uploads and verifies a new immutable prefix, then switches
the activation pointer. Dispatch the development deployment after ingestion
succeeds. Retain the preceding pointer value and immutable prefix for rollback.

The older preservation workflow still accepts an explicit
`AL_ISABAH_PUBLIC_CORPUS_URI` when rebuilding legacy research material. It must
not overwrite the active pointer or any immutable prefix.

The summary, index, section, item, and aggregate-review endpoints are public.
The Worker is the only R2 origin client and returns cacheable reader responses;
do not place R2 credentials or object keys in browser code or deployment logs.
Review mutation endpoints still require an active same-origin session. Limited,
suspended, and anonymous users can read, but cannot approve or correct.

## Smoke checks

- Public work inventory, reading sections, items, and aggregate approval counts
  load without a session.
- An anonymous reader can move through volumes and substantial reading sections
  in book order, with English on the left and Arabic on the right.
- Search can locate a record without replacing volume/section navigation as the
  primary reading experience.
- Unresolved work, provenance, and workflow history remain available from the
  relevant record without interrupting the default continuous reading flow.
- An active reviewer can approve an English translation from the continuous or
  individual record view, see the current approval count, hide human-reviewed
  records, and withdraw their own approval.
- Repeating the same approval action does not append a duplicate event. A
  withdrawal appends a reversal and restores the record to the unreviewed
  filter when no other current approvals remain.
- Anonymous readers can see aggregate translation-approval state but cannot
  write it. Limited, suspended, and cross-origin requests also cannot write it.
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
