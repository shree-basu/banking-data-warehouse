output "raw_bucket_name" {
  description = "Immutable raw-zone bucket."
  value       = google_storage_bucket.raw.name
}

output "dataset_ids" {
  description = "Warehouse datasets by logical layer."
  value       = { for layer, dataset in google_bigquery_dataset.layer : layer => dataset.dataset_id }
}

output "runtime_service_account" {
  description = "Service account used by the pipeline runtime."
  value       = google_service_account.runtime.email
}

output "ci_service_account" {
  description = "OIDC/WIF CI service account."
  value       = google_service_account.ci.email
}

output "workload_identity_provider" {
  description = "Provider name for google-github-actions/auth. Null when disabled."
  value       = try(google_iam_workload_identity_pool_provider.github[0].name, null)
}

output "composer_environment" {
  description = "Composer environment ID. Null until explicitly enabled."
  value       = try(google_composer_environment.pipeline[0].id, null)
}
