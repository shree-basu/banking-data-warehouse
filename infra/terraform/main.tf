locals {
  prefix = "${var.name_prefix}-${var.environment}"
  labels = merge(var.labels, {
    application = "banking-dwh"
    environment = var.environment
    managed_by  = "terraform"
  })
  datasets = toset(["staging", "curated", "audit", "analytics"])
  services = toset([
    "bigquery.googleapis.com",
    "composer.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "monitoring.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
  ])
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "required" {
  for_each = var.enable_apis ? local.services : toset([])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "raw" {
  name                        = var.raw_bucket_name
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  labels                      = local.labels

  versioning { enabled = true }

  soft_delete_policy {
    retention_duration_seconds = var.bucket_soft_delete_seconds
  }

  lifecycle_rule {
    action { type = "Delete" }
    condition {
      age            = var.raw_retention_days
      with_state     = "ANY"
      matches_prefix = ["raw/"]
    }
  }

  lifecycle_rule {
    action { type = "Delete" }
    condition {
      age        = 30
      with_state = "ARCHIVED"
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_bigquery_dataset" "layer" {
  for_each = local.datasets

  project                     = var.project_id
  dataset_id                  = each.key
  friendly_name               = "${local.prefix} ${each.key}"
  description                 = "${each.key} layer for the banking batch warehouse"
  location                    = var.bigquery_location
  delete_contents_on_destroy  = false
  labels                      = local.labels
  default_table_expiration_ms = each.key == "staging" ? var.staging_table_expiration_ms : null

  depends_on = [google_project_service.required]
}
