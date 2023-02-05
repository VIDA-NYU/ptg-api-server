/* -------------------------------- Postgres -------------------------------- */

output "super_user" {
  value       = "postgres"
}

output "super_pass" {
  value     = data.external.timescale_root_password.result.value
  sensitive = true
}

output "db_name" {
  value       = var.timescale_database
}

output "service_name" {
  value       = helm_release.timescale.name
}

# /* ---------------------------------- Minio --------------------------------- */

# output "s3_access_key" {
#   value       = var.admin_user
# }

# output "s3_secret_key" {
#   value     = var.admin_pass
#   sensitive = true
# }

# output "s3_service_name" {
#   value       = helm_release.minio.name
# }

# output "s3_host" {
#   value       = "${var.minio_subdomain}.${var.domain}"
# }