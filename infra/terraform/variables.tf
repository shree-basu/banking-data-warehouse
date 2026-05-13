variable "project_id"{
    description = "GCP Project ID"
    type = string
    default = banking-dwh-project
    }

variable "region"{
    description = "GCP Region"
    type = string
    default = asia-south1
}

variable "dataset_id"{
    description = "BigQuery Dataset ID"
    type = string
    default = banking_dwh
}

variable "gcs_bucket_name"{
    description = "GCS Bucket name for raw data"
    type = string
    default = banking-dwh-raw-data
}