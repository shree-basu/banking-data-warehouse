output "gcs_bucket_name"{
    description = "GCS bucket name for raw data"
    value: gcs_storage_bucket.raw_data_bucket.name
}
output "bigquery_dataset"{
    description = "BigQuery dataset ID"
    value = google_bigquery_dataset.banking_dwh.dataset_id
}