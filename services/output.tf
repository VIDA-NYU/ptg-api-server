output "auth_domain" {
  value       = "${var.auth_subdomain}.${var.domain}"
}
