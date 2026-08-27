resource "google_logging_metric" "pipeline_error" {
  project = var.project_id
  name    = "${local.prefix}-pipeline-errors"
  filter  = "severity>=ERROR AND (resource.type=\"cloud_composer_environment\" OR resource.type=\"bigquery_resource\")"

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

resource "google_monitoring_alert_policy" "pipeline_error" {
  project               = var.project_id
  display_name          = "${local.prefix}: pipeline errors"
  combiner              = "OR"
  notification_channels = var.notification_channels

  conditions {
    display_name = "At least one error log"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.pipeline_error.name}\" AND resource.type=\"global\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "0s"
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  documentation {
    content   = "Use audit.batch_run, audit.dq_result, and the runbook to triage."
    mime_type = "text/markdown"
  }
}
