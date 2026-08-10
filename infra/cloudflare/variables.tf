variable "cloudflare_account_id" {
  description = "Cloudflare account identifier. This is operational metadata, not a secret."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{32}$", var.cloudflare_account_id))
    error_message = "cloudflare_account_id must be a 32-character hexadecimal identifier."
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
