output "development_bucket_name" {
  description = "Development asset bucket managed by this configuration."
  value       = cloudflare_r2_bucket.development_assets.name
}

output "production_bucket_name" {
  description = "Production asset bucket managed by this configuration."
  value       = cloudflare_r2_bucket.production_assets.name
}
