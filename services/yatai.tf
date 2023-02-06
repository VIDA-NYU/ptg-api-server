# export PG_PASSWORD=xxx
# export PG_HOST=1.1.1.1
# export PG_PORT=5432
# export PG_DATABASE=yatai
# export PG_USER=postgres
# export PG_SSLMODE=disable
# PGPASSWORD=$PG_PASSWORD psql \
#     -h $PG_HOST \
#     -p $PG_PORT \
#     -U $PG_USER \
#     -d postgres \
#     -c "create database $PG_DATABASE"

variable yatai_subdomain {
  default = "yatai"
}

# ----------------------------- Setup helm chart ----------------------------- #

resource "helm_release" "yatai" {
  repository = "https://bentoml.github.io/helm-charts"
  chart      = "yatai"
  name       = "yatai"
  namespace  = var.namespace
  timeout = 120

  values = [
    replace(templatefile("${path.module}/values/yatai.values.yml", {
      domain = "${var.yatai_subdomain}.${var.domain}"
        pg_host = var.db_service_name
        pg_user = postgresql_role.yatai.name
        pg_database = var.db_name

        s3_endpoint=helm_release.minio.name #var.s3_service_name
        s3_region="local"
        s3_bucketName="yatai"
        # s3_accessKey=random_string.yatai_key.result
        # s3_secretKey=random_password.yatai_secret.result
        secret_name = kubernetes_secret.yatai_secret.metadata[0].name
    }), "/(?m)^\\s*#.*\\n?/", "") # removes comment lines :)
  ]
}


resource "random_string" "yatai_key" {
  length = 24
  special = false
}

resource "random_password" "yatai_secret" {
  length = 24
  special = false
}

resource "random_password" "yatai_password" {
  length = 24
}

resource "postgresql_role" "yatai" {
    name                = "yatai"
    password            = random_password.yatai_password.result
    login               = true
}

# resource "postgresql_grant" "grafana_grant" {
#   database    = var.db_name
#   role        = "grafana_grant"
#   schema      = ""
#   object_type = "database"
#   privileges  = ["SELECT"]
# }

resource "kubernetes_secret" "yatai_secret" {
  metadata {
    name = "yatai-creds"
  }

  data = {
    pg_password = random_password.yatai_password.result
    access_key = var.admin_user #random_string.yatai_key.result
    secret_key = var.admin_pass #random_password.yatai_secret.result
  }
}
