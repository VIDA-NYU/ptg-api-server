terraform {
  required_providers {
    keycloak = {
      source = "mrparkers/keycloak"
      version = ">= 2.0.0"
    }
    
    postgresql = {
      source = "cyrilgdn/postgresql"
      version = "1.17.1"
    }

    minio = {
      # ATTENTION: use the current version here!
      version = "0.1.0-alpha5"
      source  = "refaktory/minio"
    }
  }
}

provider "minio" {
  # The Minio server endpoint.
  # NOTE: do NOT add an http:// or https:// prefix!
  # Set the `ssl = true/false` setting instead.
  endpoint = "${var.s3_service_name}:9000"
  # Specify your minio user access key here.
  access_key = var.s3_access_key
  # Specify your minio user secret key here.
  secret_key = var.s3_secret_key
  # If true, the server will be contacted via https://
  ssl = false
}
