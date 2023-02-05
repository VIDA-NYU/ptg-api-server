variable "minio_subdomain" {
  type = string
  default = "s3"
}
variable "minio_console_subdomain" {
  type = string
  default = "minio"
}

variable "minio_client_id" {
  type = string
  default = "minio"
}

# ---------------------------------------------------------------------------- #
#                                Minio Instance                                #
# ---------------------------------------------------------------------------- #

resource "kubernetes_secret" "minio_admin" {
  metadata {
    name      = "minio-admin"
    namespace = var.namespace
  }

  data = {
    rootUser     = var.admin_user
    rootPassword = var.admin_pass
  }
}

# ----------------------------- Setup helm chart ----------------------------- #

resource "helm_release" "minio" {
  chart      = "minio"
  name       = "minio"
  repository = "https://charts.min.io/"
  namespace  = var.namespace
  timeout = 180

  values = [
    replace(templatefile("${path.module}/values/minio.values.yml", {
      
      console_domain        = "${var.minio_console_subdomain}.${var.domain}"
      domain                = "${var.minio_subdomain}.${var.domain}"
      # oidc
      auth_domain           = "${var.auth_subdomain}.${var.domain}"
      auth_realm            = keycloak_realm.main.id
      client_id             = keycloak_openid_client.minio.client_id
      client_secret         = random_password.minio_client_secret.result
      # credentials
      admin_existing_secret = kubernetes_secret.minio_admin.metadata[0].name
      # misc
      storage_class = "minio"
      replicas = 3
    }), "/(?m)^\\s*#.*\\n?/", "") # removes comment lines :)
  ]
}

# ---------------------------------------------------------------------------- #
#                          Minio Keycloak Integration                          #
# ---------------------------------------------------------------------------- #

# ------------------------------ Keycloak client ----------------------------- #

resource "random_password" "minio_client_secret" {
  length = 24
}

resource "keycloak_openid_client" "minio" {
  realm_id  = keycloak_realm.main.id
  client_id = var.minio_client_id
  client_secret = random_password.minio_client_secret.result
  enabled = true

  access_type           = "CONFIDENTIAL"
  standard_flow_enabled = true
  valid_redirect_uris = [
    "https://${var.minio_console_subdomain}.${var.domain}/*",
    "https://${var.minio_subdomain}.${var.domain}/*",
  ]
  web_origins = [
    "https://${var.minio_console_subdomain}.${var.domain}/*",
    "https://${var.minio_subdomain}.${var.domain}/*",
  ]
  root_url    = "$${authBaseUrl}"
  admin_url   = "$${authBaseUrl}"
}

# -------------------------- Keycloak scope mapping -------------------------- #

resource "keycloak_openid_client_scope" "minio_policy" {
  realm_id               = keycloak_realm.main.id
  name                   = "minio-policy"
  description            = "Map minio policy in the token"
  # include_in_token_scope = true
  # gui_order              = 1
}

resource "keycloak_openid_client_default_scopes" "minio" {
  realm_id  = keycloak_realm.main.id
  client_id = keycloak_openid_client.minio.id

  default_scopes = [
    "profile",
    "email",
    "roles",
    "web-origins",
    keycloak_openid_client_scope.minio_policy.name,
  ]
}

resource "keycloak_openid_user_client_role_protocol_mapper" "minio" {
  realm_id        = keycloak_realm.main.id
  # client_id       = keycloak_openid_client.minio.id
  client_scope_id = keycloak_openid_client_scope.minio_policy.id
  client_id_for_role_mappings =  keycloak_openid_client.minio.client_id
  name            = "minio-policy"
  claim_name      = "policy"
  # claim_value_type = "String"
  multivalued = true
}

# ------------------------ Assign Minio to Admin Group ----------------------- #

resource "keycloak_role" "minio_consoleAdmin_role" {
  realm_id        = keycloak_realm.main.id
  client_id       = keycloak_openid_client.minio.id
  name            = "consoleAdmin"
}

resource "keycloak_group_roles" "minio_admin" {
  realm_id = keycloak_realm.main.id
  group_id  = keycloak_group.admin.id
  exhaustive = false

  role_ids = [
    keycloak_role.minio_consoleAdmin_role.id,
  ]
}