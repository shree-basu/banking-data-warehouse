CREATE TABLE IF NOT EXISTS `audit.batch_run` (
  batch_id STRING NOT NULL,
  business_date DATE NOT NULL,
  dag_id STRING NOT NULL,
  dag_run_id STRING NOT NULL,
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  status STRING NOT NULL,
  source_row_count INT64,
  staging_row_count INT64,
  curated_row_count INT64,
  source_monetary_total NUMERIC,
  curated_monetary_total NUMERIC,
  rejected_row_count INT64,
  error_summary STRING,
  code_version STRING NOT NULL,
  PRIMARY KEY (batch_id) NOT ENFORCED
)
PARTITION BY business_date
OPTIONS (description = 'One lifecycle record per immutable source batch');

CREATE TABLE IF NOT EXISTS `audit.dq_result` (
  batch_id STRING NOT NULL,
  business_date DATE NOT NULL,
  rule_code STRING NOT NULL,
  entity STRING NOT NULL,
  severity STRING NOT NULL,
  passed BOOL NOT NULL,
  observed_value STRING,
  threshold_value STRING,
  checked_at TIMESTAMP NOT NULL
)
PARTITION BY business_date
CLUSTER BY batch_id, severity, entity
OPTIONS (description = 'Persisted source, staging, reconciliation, and curated DQ evidence');

CREATE TABLE IF NOT EXISTS `audit.quarantine` (
  batch_id STRING NOT NULL,
  business_date DATE NOT NULL,
  entity STRING NOT NULL,
  record_key STRING,
  rule_code STRING NOT NULL,
  reason STRING NOT NULL,
  source_file STRING NOT NULL,
  raw_record JSON,
  quarantined_at TIMESTAMP NOT NULL
)
PARTITION BY business_date
CLUSTER BY batch_id, entity, rule_code
OPTIONS (description = 'Rejected records with rule and immutable source provenance');

