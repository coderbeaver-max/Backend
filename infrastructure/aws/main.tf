
locals {
  project_context = {
    project     = var.project_name
    environment = var.environment
    aws_region  = var.aws_region
  }
}
