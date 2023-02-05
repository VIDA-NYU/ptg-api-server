# ---------------------------------------------------------------------------- #
#                                Domains & Users                               #
# ---------------------------------------------------------------------------- #

variable "domain" {
  type = string
  description = "The project domain (no https://)"
}

variable "domain_email" {
  type = string
  description = "The domain email used for letsencrypt"
}

variable "admin_user" {
  type = string
}

variable "admin_pass" {
  type = string
}

variable "app_name" {
  type = string
  default = "default"
}


# ---------------------------------------------------------------------------- #
#                              Database Variables                              #
# ---------------------------------------------------------------------------- #


variable "db_super_user" {
}

variable "db_super_pass" {
  sensitive = true
}

variable "db_name" {
}

variable "db_service_name" {
}

# ---------------------------------------------------------------------------- #
#                                    System                                    #
# ---------------------------------------------------------------------------- #

variable "project_id" {
  type = string
  description = "The project ID"
}

variable "namespace" {
  type = string
  default = "default"
  description = "kubernetes namespace"
}

variable "system_namespace" {
  type = string
  default = "monitoring"
  description = "kubernetes system namespace"
}