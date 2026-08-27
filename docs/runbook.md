# Runbook

## Bootstrap and deploy

1. Create a dedicated GCS state bucket outside this root module; enable versioning, uniform access, public-access prevention, and grant the Terraform identity object-admin access only on that bucket.
2. Run `terraform init -backend-config="bucket=STATE_BUCKET" -backend-config="prefix=banking-dwh/ENV"`.
3. Copy `dev.auto.tfvars.example` to an ignored `.auto.tfvars`, use non-secret project/bucket values, then review `terraform plan`.
4. Keep `enable_composer=false` until billing/cost approval. Configure GitHub WIF and a protected `production` environment before using the manual deploy workflow.
5. Apply infrastructure, execute SQL in order: warehouse tables, audit tables, publish procedures, DQ procedures, aggregate procedure; then upload the DAG. This order is mandatory.

## Daily triage

Start with `audit.batch_run`, then `audit.dq_result` and `audit.quarantine`. Match `batch_id`, Airflow run ID, deterministic BigQuery job ID, source/stage/curated counts, monetary totals, and code version. A batch is complete only when final status is `SUCCESS`.

## Backfill

Confirm the immutable prefix and manifest, then trigger the historical logical date—not an arbitrary path. Run oldest to newest with one active run. Replays must produce zero new curated rows. Compare audit totals before and after.

## Authorized cloud verification (not yet run)

Run the SQL DDL/procedures in a non-production project, upload one generated batch, trigger its logical date, rerun it, then execute the next-day and late-dimension batches. Use `bq query --dry_run --use_legacy_sql=false < docs/example-queries.sql` to record estimated bytes. Confirm alerts with a controlled test error. Delete only explicitly approved test resources.

RTO/RPO assumptions are eight hours and one accepted daily batch. Escalate if a manifest is unavailable near the four-hour completion SLO, reconciliation cannot be restored from immutable input, or Composer is unavailable long enough to threaten RTO.
