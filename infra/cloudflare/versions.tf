terraform {
  required_version = ">= 1.10.0, < 2.0.0"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "5.23.0"
    }
  }

  # Supply the R2 backend settings at init time after the state bucket exists.
  backend "s3" {}
}
