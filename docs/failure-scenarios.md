# Failure scenarios

| Scenario | Expected behavior | Recovery |
|---|---|---|
| Missing manifest | Deferrable sensor times out; no staging/publish | Correct producer, rerun same logical date |
| Missing/corrupt object | checksum/manifest gate fails permanently | Restore exact immutable object or issue a new batch ID |
| Schema drift | strict load fails with zero bad records | version contract and code together |
| Duplicate batch | audit/replay detects existing identity | replay safely; never overwrite identity |
| Duplicate transaction | critical DQ fails before publication | quarantine and correct source batch |
| Late dimension | fact uses key `0`, warning persists | load a covering account/customer/merchant version, then run repair; otherwise replay chronologically |
| Staging retry | deterministic table/job IDs reattach or replace safely | retry transient task |
| DQ failure | quarantine/audit update; curated state unchanged | fix source/rule and rerun |
| BigQuery transform failure | transaction rolls back | inspect deterministic job and retry |
| Partial deployment | workflow stops before SQL/DAG step | fix plan/apply; resume in documented order |
| Backfill | historical interval selects historical prefix | process oldest-first, one active run |
| Raw-object deletion | GCS soft delete/versioning protects seven days | restore generation before retention expiry |
| Composer outage | immutable input remains; SLO may breach | resume/backfill after service restoration |

Never bypass reconciliation or manually mark success. Any manual repair must leave an audit trail and preserve the original raw batch.
