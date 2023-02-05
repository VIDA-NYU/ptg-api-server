variable "directus_subdomain" {
  type = string
  default = "directus"
}


# ---------------------------------------------------------------------------- #
#                               Directus Instance                              #
# ---------------------------------------------------------------------------- #


# ----------------------------- Setup helm chart ----------------------------- #

resource "helm_release" "directus" {
  chart      = "directus"
  name       = "directus"
  repository = "https://directus-community.github.io/helm-chart/"
  namespace  = var.namespace
  timeout = 120

  values = [
    replace(templatefile("${path.module}/values/directus.values.yml", {
      configmap_version = "${kubernetes_secret.directus_environment.metadata.0.resource_version}-${kubernetes_config_map.directus_snapshot.metadata.0.resource_version}"
      redis_password        = random_password.directus_redis_password.result
      domain                = "${var.directus_subdomain}.${var.domain}"
      # oidc
      auth_domain           = "${var.auth_subdomain}.${var.domain}"
      auth_realm            = keycloak_realm.main.id
      # snapshot configmap
      # directus_snapshot_configmap = kubernetes_config_map.directus_snapshot.metadata[0].name
      directus_environment_secret = kubernetes_secret.directus_environment.metadata[0].name
    }), "/(?m)^\\s*#.*\\n?/", "") # removes comment lines :)
  ]
}


/* --------------------------------- Config --------------------------------- */

resource "random_string" "directus_key" {
  length = 24
  special = false
}

resource "random_password" "directus_secret" {
  length = 24
  special = false
}

resource "random_password" "directus_redis_password" {
  length = 24
  special = false
}


# resource "kubernetes_config_map" "directus_snapshot" {
#   metadata {
#     name = "directus-snapshot"
#   }

#   data = {
#     "snapshot.yaml" = file("${path.module}/configs/directus/snapshot.yaml")
#   }
# }

resource "kubernetes_secret" "directus_environment" {
  metadata {
    name = "directus-environment"
  }

  data = {
    # directus requirements
    KEY = random_string.directus_key.result
    SECRET = random_password.directus_secret.result

    # database
    DB_CLIENT = "pg"
    DB_HOST = var.db_service_name
    DB_PORT = "5432"
    DB_DATABASE = var.db_name
    DB_USER = postgresql_role.directus.name
    DB_PASSWORD = postgresql_role.directus.password

    # auth
    AUTH_PROVIDERS = "keycloak"
    AUTH_KEYCLOAK_DRIVER = "openid"
    AUTH_KEYCLOAK_CLIENT_ID = keycloak_openid_client.directus.client_id
    AUTH_KEYCLOAK_CLIENT_SECRET = random_password.directus_client_secret.result
    # AUTH_KEYCLOAK_ISSUER_URL = "https://${auth_domain}/realms/${auth_realm}/.well-known/openid-configuration"
    AUTH_KEYCLOAK_IDENTIFIER_KEY = "email"
    AUTH_KEYCLOAK_ALLOW_PUBLIC_REGISTRATION = "true"
    ADMIN_EMAIL = var.domain_email
    ADMIN_PASSWORD = var.admin_pass
  }
}


# ---------------------------------------------------------------------------- #
#                         Directus Postgres Integration                        #
# ---------------------------------------------------------------------------- #


resource "random_password" "directus_postgres_password" {
  length = 24
  special = false
}

resource "postgresql_role" "directus" {
    name                = "directus"
    password            = random_password.directus_postgres_password.result
    login               = true
}

resource "postgresql_grant" "directus_grant" {
  database    = var.db_name
  role        = postgresql_role.directus.name
  schema      = "public" #postgresql_schema.directus.name
  object_type = "schema"
  privileges  = ["CREATE", "USAGE"] #["ALL"]
}



# ---------------------------------------------------------------------------- #
#                         Directus Keycloak Integration                        #
# ---------------------------------------------------------------------------- #

resource "random_password" "directus_client_secret" {
  length = 24
  special = false
}

resource "keycloak_openid_client" "directus" {
  realm_id  = keycloak_realm.main.id
  client_id = "directus"
  client_secret = random_password.directus_client_secret.result
  enabled = true

  access_type           = "CONFIDENTIAL"
  standard_flow_enabled = true
  valid_redirect_uris = ["https://${var.directus_subdomain}.${var.domain}/*"]
  web_origins = ["https://${var.directus_subdomain}.${var.domain}/*"]
  root_url    = "$${authBaseUrl}"
  admin_url   = "$${authBaseUrl}"
}
