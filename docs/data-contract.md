# Batch data contract

Path: `raw/business_date=YYYY-MM-DD/batch_id=BATCH_ID/{entity}.csv`; the manifest is `manifest.json` in the same prefix and is written last.

Required manifest fields are `batch_id`, `business_date`, `expected_entities`, per-entity `object_path`, `expected_row_count`, `sha256`, and `source_created_at`. The only entities are customers, accounts, merchants, transactions, and account snapshots. CSV headers and BigQuery load schemas are explicit; autodetection and bad-record tolerance are disabled.

Batch-failing violations include missing/corrupt objects, schema mismatch, duplicate natural/transaction keys, invalid transaction amount/currency/date, broken account-customer references, source-stage mismatch, monetary mismatch, multiple current SCD rows, overlapping validity intervals, and unresolved non-unknown fact keys. Late merchant/account references may land on unknown key `0`, are recorded as warnings, and must be repaired after the dimension arrives. Invalid business records are persisted with batch, source metadata, rule code, and reason.

The simulator seeds `random`, Faker, and UUID5 identifiers. The same arguments produce byte-identical objects and checksums. Reusing a batch identity with different content is a contract violation, not an overwrite.
