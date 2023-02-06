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
     grafana = {
      source = "grafana/grafana"
      version = "1.31.1"
    }
  }

  #backend "azurerm" {
  #  resource_group_name  = "tfstate"
  #  storage_account_name = "tfstate2693456765613"
  #  container_name       = "tfstate"
  #  key                  = "terraform.tfstate"
  #}

  required_version = ">= 0.14"
}

provider "kubernetes" {
  # config_path    = module.aks.kube_config #"~/.kube/config"
  config_path = "/etc/rancher/k3s/k3s.yaml"
}

provider "helm" {
  kubernetes {
    # config_path = module.aks.kube_config
    # config_context = "floodnet"
    config_path = "/etc/rancher/k3s/k3s.yaml"
  }
}


provider "postgresql" {
  host       = "localhost" #module.postgres_tunnel.host
  port       = "5432" #module.postgres_tunnel.port
  database   = module.db.db_name
  sslmode    = "disable"

  username   = module.db.super_user
  password   = module.db.super_pass
  superuser  = "true"
  expected_version = "14.6"
}

provider "keycloak" {
    # url           = "http://${helm_release.keycloak.name}.${var.namespace}"
    url           = "https://${module.services.auth_domain}"
    client_id     = "admin-cli"
    username = var.admin_user
    password = var.admin_pass
    initial_login = false
    # base_path = "/auth"
}
