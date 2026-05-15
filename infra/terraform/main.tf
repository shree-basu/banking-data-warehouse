terraform {
    required_providers{
        google = {
            source = "hashicorp/google"
            version = "~>4.0"
        }
    }
}

provider "google" {
    project = var.project_id
    reg ion = var.region
}

resource "google_storage_bucket" "raw_data_bucket"{
    name = var.gcs_bucket_name
    location = var.region
    force_destroy = true

    lifecycle_rule{
        action {
            type = "Delete"
        }
        condition {
            age = 90
        }
    }
}

resource "google_bigquery_dataset" "banking_dwh"{
    dataset_id = var.dataset_id
    description = "Banking Data Warehouse dataset"
    location = var.region
}