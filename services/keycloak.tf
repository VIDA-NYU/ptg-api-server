variable "auth_subdomain" {
  type = string
  default = "auth"
}

variable "auth_realm" {
  type = string
  default = "floodnet"
}

# ---------------------------------------------------------------------------- #
#                               Keycloak Instance                              #
# ---------------------------------------------------------------------------- #

# resource "random_password" "keycloak" {
#   length = 24
# }

resource "kubernetes_secret" "keycloak_admin" {
  metadata {
    name      = "keycloak-admin"
    namespace = var.namespace
  }

  data = {
    KEYCLOAK_ADMIN = var.admin_user
    KEYCLOAK_ADMIN_PASSWORD = var.admin_pass
  }
}

resource "kubernetes_secret" "keycloak_db_password" {
  metadata {
    name      = "keycloak-db-password"
    namespace = var.namespace
  }

  data = {
    password = var.db_super_pass #postgresql_role.keycloak.password
  }
}

# ----------------------------- Setup helm chart ----------------------------- #

resource "helm_release" "keycloak" {
  repository = "https://codecentric.github.io/helm-charts"
  chart      = "keycloakx"
  name       = "keycloak"
  namespace  = var.namespace
  version = "2.1.0"
  timeout = 120

  values = [
    replace(templatefile("${path.module}/values/keycloak.values.yml", {
      domain = "${var.auth_subdomain}.${var.domain}"
      db_host = "${var.db_service_name}.${var.namespace}"
      db_name = var.db_name
      db_schema = postgresql_schema.keycloak.name
      db_user = var.db_super_user #postgresql_role.keycloak.name
      # db_pass = postgresql_role.keycloak.password
      # admin_user = var.admin_user
      # admin_pass = var.admin_pass
      admin_existing_secret = kubernetes_secret.keycloak_admin.metadata[0].name
      db_existing_secret = kubernetes_secret.keycloak_db_password.metadata[0].name
    }), "/(?m)^\\s*#.*\\n?/", "") # removes comment lines :)
  ]
}

# ---------------------------------------------------------------------------- #
#                         Keycloak Postgres Integration                        #
# ---------------------------------------------------------------------------- #

resource "random_password" "keycloak_postgres_password" {
  length = 24
  special = false
}

resource "postgresql_role" "keycloak" {
    name                = "keycloak"
    password            = random_password.keycloak_postgres_password.result
    login               = true
}

resource "postgresql_schema" "keycloak" {
  name  = "keycloak"
  owner = postgresql_role.keycloak.name
}

resource "postgresql_grant" "keycloak_grant" {
  database    = var.db_name
  role        = postgresql_role.keycloak.name
  schema      = postgresql_schema.keycloak.name
  object_type = "schema"
  privileges  = ["CREATE", "USAGE"] # ["ALL"]
}

# ---------------------------------------------------------------------------- #
#                    Keycloak Configuration & Initialization                   #
# ---------------------------------------------------------------------------- #

resource "keycloak_realm" "main" {
  realm             = var.auth_realm
  enabled           = true
  login_with_email_allowed = true
}

# ------------------------------ Keycloak Admin ------------------------------ #

resource "keycloak_user" "root" {
  realm_id = keycloak_realm.main.id
  username = var.admin_user
  enabled  = true

  email          = var.domain_email
  # first_name     = var.root_firstname
  # last_name      = var.root_lastname
  email_verified = true

  attributes = {
  }

  initial_password {
    value     = var.admin_pass
    temporary = false
  }
}

resource "keycloak_group" "admin" {
  realm_id = keycloak_realm.main.id
  name     = "admin"
}

resource "keycloak_user_groups" "root_admin" {
  realm_id = keycloak_realm.main.id
  user_id = keycloak_user.root.id

  group_ids  = [
    keycloak_group.admin.id
  ]
}
