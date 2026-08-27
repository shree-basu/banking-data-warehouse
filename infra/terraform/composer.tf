resource "google_composer_environment" "pipeline" {
  count = var.enable_composer ? 1 : 0

  project = var.project_id
  name    = "${local.prefix}-composer"
  region  = var.region
  labels  = local.labels

  config {
    environment_size = "ENVIRONMENT_SIZE_SMALL"
    node_config {
      service_account = google_service_account.runtime.email
    }
    software_config {
      image_version = var.composer_image_version
      env_variables = {
        BANKING_PROJECT_ID = var.project_id
        BANKING_RAW_BUCKET = google_storage_bucket.raw.name
      }
    }
  }

  depends_on = [google_project_service.required]
}
