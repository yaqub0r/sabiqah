# Cloudflare infrastructure

This root configuration manages the Sabiqah R2 asset buckets. It uses OpenTofu
and Cloudflare provider 5.23.0.

## Safety boundaries

- Provider authentication comes only from `CLOUDFLARE_API_TOKEN`.
- R2 state-backend authentication comes only from `AWS_ACCESS_KEY_ID` and
  `AWS_SECRET_ACCESS_KEY`; these are R2 S3-compatible credentials, not AWS
  credentials.
- The production asset bucket has `prevent_destroy` enabled.
- R2 buckets remain private unless a separate, reviewed resource explicitly
  enables a public domain.
- CI validation uses no credentials and cannot change Cloudflare.

Cloudflare account-owned tokens currently expose account-level R2 permissions
but not zone-scoped DNS permissions. DNS therefore remains owner-managed rather
than introducing a human user token into automation. Revisit this boundary if
Cloudflare adds zone permissions to account-owned tokens.

## State bootstrap

The state bucket must exist before this configuration can use it. Create only
the private `sabiqah-infra-state` R2 bucket during the one-time manual bootstrap,
create an R2 token scoped only to that bucket with Object Read & Write, and put
the access key ID and secret access key directly into the protected GitHub
environments. The protected apply workflow then creates the asset buckets from
this configuration; do not create them manually unless an import is planned.

Copy `backend.hcl.example` to an ignored `backend.hcl`, replace only the account
identifier placeholder, and initialize with:

```text
tofu init -backend-config=backend.hcl
```

Never put credentials in `backend.hcl` or command-line backend arguments because
OpenTofu records backend arguments in local metadata and saved plans.

## Review path

1. Run `tofu fmt -check -recursive` and `tofu validate`.
2. Generate a speculative plan with a read-capable development token.
3. Review the plan in a pull request.
4. Merge the reviewed change to `main`.
5. Dispatch `Apply Cloudflare infrastructure`; the job can run only from `main`
   and requires approval through the `production` environment.

Do not use the broad bootstrap token for routine plans or applies.
