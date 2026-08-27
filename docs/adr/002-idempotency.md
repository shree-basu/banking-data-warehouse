# ADR 002: Batch identity and idempotency

Status: accepted.

`(business_date, batch_id)` plus object SHA-256 is the immutable ingestion identity. Staging targets and BigQuery job IDs are deterministic. Facts MERGE on source natural keys only after uniqueness DQ. Audit records completion separately from data publication. A replay therefore reuses source identity and changes neither curated rows nor aggregates.
