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
