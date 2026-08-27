variable "project_id" {
  description = "Existing GCP project ID; this module never creates a project."
  type        = string
}

variable "region" {
  description = "Regional location for GCS and optional Composer."
  type        = string
  default     = "asia-south1"
}

variable "bigquery_location" {
  description = "BigQuery dataset location."
  type        = string
  default     = "asia-south1"
}

variable "environment" {
  description = "Environment label."
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "environment must be dev, test, or prod."
  }
}

variable "name_prefix" {
  description = "Short resource-name prefix."
  type        = string
  default     = "banking-dwh"
}

variable "raw_bucket_name" {
  description = "Globally unique immutable raw-zone bucket name."
  type        = string
}

variable "enable_apis" {
  description = "Enable required project APIs."
  type        = bool
  default     = true
}

variable "raw_retention_days" {
  description = "Days before immutable raw batch objects are deleted."
  type        = number
  default     = 365
}

variable "bucket_soft_delete_seconds" {
  description = "GCS soft-delete retention; minimum seven days."
  type        = number
  default     = 604800
}

variable "staging_table_expiration_ms" {
  description = "Default expiration for batch-specific staging tables."
  type        = number
  default     = 604800000
}

variable "enable_composer" {
  description = "Create the chargeable Composer environment. Disabled by default."
  type        = bool
  default     = false
}

variable "composer_image_version" {
  description = "Validated Composer image target."
  type        = string
  default     = "composer-3-airflow-2.10.5-build.47"
}

variable "enable_workload_identity_federation" {
  description = "Create GitHub Actions Workload Identity Federation resources."
  type        = bool
  default     = false
}

variable "github_repository" {
  description = "GitHub owner/repository allowed to federate."
  type        = string
  default     = ""
  validation {
    condition     = !var.enable_workload_identity_federation || can(regex("^[^/]+/[^/]+$", var.github_repository))
    error_message = "github_repository must be owner/repository when WIF is enabled."
  }
}

variable "ci_project_roles" {
  description = "Explicit roles required for the Terraform deployment identity; review per organization policy."
  type        = set(string)
  default = [
    "roles/bigquery.admin",
    "roles/composer.admin",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.workloadIdentityPoolAdmin",
    "roles/logging.configWriter",
    "roles/monitoring.editor",
    "roles/resourcemanager.projectIamAdmin",
    "roles/serviceusage.serviceUsageAdmin",
    "roles/storage.admin",
  ]
}

variable "notification_channels" {
  description = "Existing Cloud Monitoring notification channel resource names."
  type        = list(string)
  default     = []
}

variable "labels" {
  description = "Additional resource labels."
  type        = map(string)
  default     = {}
}
