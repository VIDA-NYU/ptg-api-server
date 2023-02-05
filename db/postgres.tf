# https://github.com/cyrilgdn/terraform-provider-postgresql/issues/81
variable "timescale_subdomain" {
  type = string
  default = "timescale"
}

variable "timescale_database" {
  type = string
  default = "postgres"
}

# setup service

resource "helm_release" "timescale" {
  # chart      = "./${path.module}/timescale-helm/charts/timescaledb-single"
  chart      = "timescaledb-single"
  name       = "timescale"
  repository = "https://charts.timescale.com/"
  namespace  = var.namespace

  timeout = 120

  values = [
    replace(templatefile("${path.module}/values/timescale.values.yml", {
    }), "/(?m)^\\s*#.*\\n?/", "") # removes comment lines :)
  ]
}
# setup DBs

# timescale secrets are not deleted when the chart gets torn down even when random_password does - 
# so we lose the postgres password - get the original password from the secret
data external timescale_root_password {
  program = ["bash", "-c", "echo -n '{\"value\": \"'$(kubectl get secrets/timescale-credentials --template={{.data.PATRONI_SUPERUSER_PASSWORD}} | base64 -D)'\"}'"]
}