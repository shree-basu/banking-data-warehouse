resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = "${var.name_prefix}-${var.environment}-runtime"
  display_name = "Banking DWH ${var.environment} runtime"
}

resource "google_service_account" "ci" {
  project      = var.project_id
  account_id   = "${var.name_prefix}-${var.environment}-ci"
  display_name = "Banking DWH ${var.environment} CI deployer"
}

resource "google_storage_bucket_iam_member" "runtime_raw_reader" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_bigquery_dataset_iam_member" "runtime_data_editor" {
  for_each = google_bigquery_dataset.layer

  project    = var.project_id
  dataset_id = each.value.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "runtime_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "runtime_composer_worker" {
  count = var.enable_composer ? 1 : 0

  project = var.project_id
  role    = "roles/composer.worker"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "ci_deployer" {
  for_each = var.enable_workload_identity_federation ? var.ci_project_roles : toset([])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.ci.email}"
}

resource "google_iam_workload_identity_pool" "github" {
  count = var.enable_workload_identity_federation ? 1 : 0

  project                   = var.project_id
  workload_identity_pool_id = "${var.name_prefix}-${var.environment}-gh"
  display_name              = "Banking DWH GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  count = var.enable_workload_identity_federation ? 1 : 0

  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github[0].workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub repository OIDC"
  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
  }
  attribute_condition = "assertion.repository == '${var.github_repository}'"
  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}

resource "google_service_account_iam_member" "github_wif" {
  count = var.enable_workload_identity_federation ? 1 : 0

  service_account_id = google_service_account.ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github[0].name}/attribute.repository/${var.github_repository}"
}
