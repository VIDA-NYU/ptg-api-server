terraform {
  required_providers {
    docker = {
      source = "kreuzwerker/docker"
      version = "3.0.1"
    }
  }
}

provider "docker" {
  # Configuration options
}


/* -------------------------------------------------------------------------- */
/*                                  Database                                  */
/* -------------------------------------------------------------------------- */

resource "docker_image" "postgres" {
  name = "postgis/postgis:13-master"
}
resource "docker_container" "postgres" {
  image = docker_image.postgres.image_id
  name  = "db"
  volumes = [
    { host_path = "./data/postgres", container_path = "/var/lib/postgresql/data" },
    { host_path = "./postgres.initdb.d", container_path = "/docker-entrypoint-initdb.d" },
  ]
  env = [
    "POSTGRES_USER=${var.admin_user}",
    "POSTGRES_PASSWORD=${var.admin_pass}",
    "POSTGRES_DB=postgres",
  ]
}

resource "docker_image" "pgadmin" {
  name = "dpage/pgadmin4"
}
resource "docker_container" "pgadmin" {
  image = docker_image.pgadmin.image_id
  name  = "pgadmin"
  ports = [
    { internal = 80, external = 8070 }
  ]
  volumes {
  }
  restart = "unless-stopped"
  env = [
    "PGADMIN_DEFAULT_EMAIL=${var.admin_email}",
    "PGADMIN_DEFAULT_PASSWORD=${var.admin_pass}",
    "PGADMIN_CONFIG_SERVER_MODE=True",
    "PGHOST=db",
    "PGPORT=5432",
    "PGDATABASE=postgres",
    "PGUSER=${var.admin_user}",
    "PGPASSWORD=${var.admin_pass}",
  ]
}


resource "docker_image" "minio" {
  name = "minio/minio"
}
resource "docker_container" "minio" {
  image = docker_image.minio.image_id
  name  = "minio"
  ports = [
    { internal = 9000, external = 9000 },
    { internal = 9001, external = 9001 },
  ]
  volumes {
    { host_path = "./data/minio", container_path = "/var/lib/postgresql/data" },
  }
  restart = "unless-stopped"
  env = [
    "PGADMIN_DEFAULT_EMAIL=${var.admin_email}",
    "PGADMIN_DEFAULT_PASSWORD=${var.admin_pass}",
    "PGADMIN_CONFIG_SERVER_MODE=True",
    "PGHOST=db",
    "PGPORT=5432",
    "PGDATABASE=postgres",
    "PGUSER=${var.admin_user}",
    "PGPASSWORD=${var.admin_pass}",
  ]
}
