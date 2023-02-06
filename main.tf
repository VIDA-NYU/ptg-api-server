module "db" {
  source = "./db"
}

module "services" {
  source = "./services"

  domain = var.domain
  domain_email = var.domain_email
  namespace = var.namespace
  project_id = var.project_id
  admin_user = var.admin_user
  admin_pass = var.admin_pass

  db_name = module.db.db_name
  db_service_name = module.db.service_name
  db_super_user = module.db.super_user
  db_super_pass = module.db.super_pass

  #s3_service_name = module.db.s3_service_name
  #s3_user = module.db.s3_user
  #s3_pass = module.db.s3_pass
}

# module "app" {
#   source = "./app"

#   domain = var.domain
#   domain_email = var.domain_email
#   project_id = var.project_id
#   admin_user = var.admin_user
#   admin_pass = var.admin_pass

#   db_name = module.db.db_name
#   db_service_name = module.db.service_name
#   db_super_user = module.db.super_user
#   db_super_pass = module.db.super_pass
#   depends_on = [module.db]
# }
