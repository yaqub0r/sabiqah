resource "cloudflare_r2_bucket" "development_assets" {
  account_id    = var.cloudflare_account_id
  name          = var.development_bucket_name
  storage_class = "Standard"
}

resource "cloudflare_r2_bucket" "production_assets" {
  account_id    = var.cloudflare_account_id
  name          = var.production_bucket_name
  storage_class = "Standard"

  lifecycle {
    prevent_destroy = true
  }
}

# The domain does not currently receive or send email. These records make that
# policy explicit and reduce spoofing until an email design is intentionally
# adopted. Remove or revise all three together before enabling email service.
resource "cloudflare_dns_record" "no_mail_mx" {
  count = var.publish_no_mail_records ? 1 : 0

  zone_id  = var.cloudflare_zone_id
  name     = var.zone_name
  type     = "MX"
  content  = "."
  priority = 0
  ttl      = 3600
  comment  = "RFC 7505: sabiqah.org does not accept email"
}

resource "cloudflare_dns_record" "no_mail_spf" {
  count = var.publish_no_mail_records ? 1 : 0

  zone_id = var.cloudflare_zone_id
  name    = var.zone_name
  type    = "TXT"
  content = "v=spf1 -all"
  ttl     = 3600
  comment = "No hosts are authorized to send mail for sabiqah.org"
}

resource "cloudflare_dns_record" "no_mail_dmarc" {
  count = var.publish_no_mail_records ? 1 : 0

  zone_id = var.cloudflare_zone_id
  name    = "_dmarc.${var.zone_name}"
  type    = "TXT"
  content = "v=DMARC1; p=reject; adkim=s; aspf=s; pct=100"
  ttl     = 3600
  comment = "Reject mail that impersonates sabiqah.org"
}
