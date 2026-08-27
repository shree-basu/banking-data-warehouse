# Cost and retention

Assumptions: raw objects retain for 365 days; GCS soft deletion retains deleted objects for seven days; archived object versions expire after 30 days; staging tables expire after seven days; curated/audit/analytics tables have no automatic expiry because regulatory policy is unknown. Production owners must replace these assumptions with approved policy.

Composer is disabled by default because it creates continuous cost. BigQuery facts require partition filters and cluster on join keys. The daily aggregate is batch-refreshed to avoid unsupported/expensive materialized-view joins. Use authenticated dry runs before approving representative queries, dataset budgets/quotas, or schedules; no cost or performance numbers are claimed here.

`force_destroy=false` and `delete_contents_on_destroy=false` protect production data. Terraform cannot alone prevent an authorized operator from deleting individual objects; IAM, versioning, soft deletion, state review, and organization policy form the defense in depth.
