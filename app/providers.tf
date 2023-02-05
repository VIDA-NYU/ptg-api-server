
# terraform {
#   required_providers {
#     minio = {
#       # ATTENTION: use the current version here!
#       version = "0.1.0-alpha5"
#       source  = "refaktory/minio"
#     }
#   }
# }


# provider "minio" {
#   # The Minio server endpoint.
#   # NOTE: do NOT add an http:// or https:// prefix!
#   # Set the `ssl = true/false` setting instead.
#   endpoint = "localhost:9000"
#   # Specify your minio user access key here.
#   access_key = "00000000"
#   # Specify your minio user secret key here.
#   secret_key = "00000000"
#   # If true, the server will be contacted via https://
#   ssl = false
# }