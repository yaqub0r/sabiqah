variable "cloudflare_account_id" {
  description = "Cloudflare account identifier. This is operational metadata, not a secret."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{32}$", var.cloudflare_account_id))
    error_message = "cloudflare_account_id must be a 32-character hexadecimal identifier."
  }
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone identifier for sabiqah.org."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{32}$", var.cloudflare_zone_id))
    error_message = "cloudflare_zone_id must be a 32-character hexadecimal identifier."
  }
}

variable "zone_name" {
  description = "Authoritative DNS zone."
  type        = string
  default     = "sabiqah.org"

  validation {
    condition     = var.zone_name == "sabiqah.org"
    error_message = "This root configuration is intentionally limited to sabiqah.org."
  }
}

variable "development_bucket_name" {
  description = "Private R2 bucket for development assets."
  type        = string
  default     = "sabiqah-assets-dev"
}

variable "production_bucket_name" {
  description = "Private R2 bucket for approved production assets."
  type        = string
  default     = "sabiqah-assets-prod"
}

variable "publish_no_mail_records" {
  description = "Publish RFC 7505 null MX plus strict SPF and DMARC while the domain sends no email."
  type        = bool
  default     = true
}
