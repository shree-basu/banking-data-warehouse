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
        AIRFLOW_VAR_GCP_PROJECT_ID = var.project_id
        AIRFLOW_VAR_RAW_BUCKET     = google_storage_bucket.raw.name
        AIRFLOW_VAR_BQ_LOCATION    = var.bigquery_location
      }
    }
  }

  depends_on = [google_project_service.required]
}
