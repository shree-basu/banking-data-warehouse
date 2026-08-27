# ADR 003: Batch-specific strict staging

Status: accepted.

Each entity loads into a table named with the sanitized batch token, using an explicit schema, no autodetect, and zero tolerated bad records. This preserves replay evidence and isolates retries. Seven-day default expiry limits storage. Shared truncate-and-reload staging was rejected because overlapping investigation/backfill runs would destroy evidence.
