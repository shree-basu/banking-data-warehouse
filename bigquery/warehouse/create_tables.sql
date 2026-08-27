-- Datasets are provisioned by Terraform. All monetary values use exact NUMERIC.
CREATE TABLE IF NOT EXISTS `curated.dim_customer` (
  customer_key STRING NOT NULL OPTIONS (description = 'Durable hashed surrogate key'),
  customer_id STRING NOT NULL OPTIONS (description = 'Source-system natural key'),
  name STRING,
  age INT64,
  gender STRING,
  city STRING,
  state STRING,
  email STRING,
  phone STRING,
  kyc_status STRING NOT NULL,
  customer_since DATE,
  effective_from DATE NOT NULL,
  effective_to DATE NOT NULL,
  is_current BOOL NOT NULL,
  hash_diff STRING NOT NULL,
  batch_id STRING NOT NULL,
  source_file STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL,
  PRIMARY KEY (customer_key) NOT ENFORCED
)
OPTIONS (description = 'SCD2 customer versions; DQ enforces one current row per customer_id');

CREATE TABLE IF NOT EXISTS `curated.dim_account` (
  account_key STRING NOT NULL OPTIONS (description = 'Durable hashed surrogate key'),
  account_id STRING NOT NULL OPTIONS (description = 'Source-system natural key'),
  customer_id STRING NOT NULL,
  account_type STRING NOT NULL,
  currency STRING NOT NULL,
  branch_code STRING,
  ifsc_code STRING,
  opened_date DATE,
  status STRING NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE NOT NULL,
  is_current BOOL NOT NULL,
  hash_diff STRING NOT NULL,
  batch_id STRING NOT NULL,
  source_file STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL,
  PRIMARY KEY (account_key) NOT ENFORCED
)
OPTIONS (description = 'SCD2 account descriptors; balances are stored in the snapshot fact');

CREATE TABLE IF NOT EXISTS `curated.dim_merchant` (
  merchant_key STRING NOT NULL OPTIONS (description = 'Durable hashed surrogate key'),
  merchant_id STRING NOT NULL OPTIONS (description = 'Source-system natural key'),
  merchant_name STRING,
  category STRING NOT NULL,
  city STRING,
  state STRING,
  registered_since DATE,
  status STRING NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE NOT NULL,
  is_current BOOL NOT NULL,
  hash_diff STRING NOT NULL,
  batch_id STRING NOT NULL,
  source_file STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL,
  PRIMARY KEY (merchant_key) NOT ENFORCED
)
OPTIONS (description = 'SCD2 merchant category and status history');

CREATE TABLE IF NOT EXISTS `curated.dim_date` (
  date_key INT64 NOT NULL,
  full_date DATE NOT NULL,
  day INT64 NOT NULL,
  month INT64 NOT NULL,
  month_name STRING NOT NULL,
  quarter INT64 NOT NULL,
  year INT64 NOT NULL,
  day_of_week STRING NOT NULL,
  is_weekend BOOL NOT NULL,
  PRIMARY KEY (date_key) NOT ENFORCED
)
OPTIONS (description = 'Deterministic calendar generated in SQL, not supplied by the source');

MERGE `curated.dim_date` AS target
USING (
  SELECT
    CAST(FORMAT_DATE('%Y%m%d', calendar_date) AS INT64) AS date_key,
    calendar_date AS full_date,
    EXTRACT(DAY FROM calendar_date) AS day,
    EXTRACT(MONTH FROM calendar_date) AS month,
    FORMAT_DATE('%B', calendar_date) AS month_name,
    EXTRACT(QUARTER FROM calendar_date) AS quarter,
    EXTRACT(YEAR FROM calendar_date) AS year,
    FORMAT_DATE('%A', calendar_date) AS day_of_week,
    EXTRACT(DAYOFWEEK FROM calendar_date) IN (1, 7) AS is_weekend
  FROM UNNEST(GENERATE_DATE_ARRAY(DATE '2020-01-01', DATE '2035-12-31')) AS calendar_date
) AS source
ON target.date_key = source.date_key
WHEN NOT MATCHED THEN
  INSERT ROW;

CREATE TABLE IF NOT EXISTS `curated.fact_transactions` (
  transaction_id STRING NOT NULL OPTIONS (description = 'One source event or attempt'),
  account_id STRING NOT NULL OPTIONS (description = 'Source account natural key'),
  merchant_id STRING NOT NULL OPTIONS (description = 'Source merchant natural key'),
  customer_key STRING NOT NULL,
  account_key STRING NOT NULL,
  merchant_key STRING NOT NULL,
  date_key INT64 NOT NULL,
  transaction_ts TIMESTAMP NOT NULL,
  transaction_date DATE NOT NULL,
  amount NUMERIC NOT NULL,
  currency STRING NOT NULL,
  channel STRING NOT NULL,
  transaction_type STRING NOT NULL,
  status STRING NOT NULL,
  ip_address STRING,
  country_code STRING,
  batch_id STRING NOT NULL,
  source_file STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL,
  PRIMARY KEY (transaction_id) NOT ENFORCED,
  FOREIGN KEY (customer_key) REFERENCES `curated.dim_customer` (customer_key) NOT ENFORCED,
  FOREIGN KEY (account_key) REFERENCES `curated.dim_account` (account_key) NOT ENFORCED,
  FOREIGN KEY (merchant_key) REFERENCES `curated.dim_merchant` (merchant_key) NOT ENFORCED
)
PARTITION BY transaction_date
CLUSTER BY account_key, merchant_key
OPTIONS (
  description = 'One row per transaction event or attempt',
  require_partition_filter = TRUE
);

CREATE TABLE IF NOT EXISTS `curated.fact_account_daily_snapshot` (
  account_key STRING NOT NULL,
  account_id STRING NOT NULL,
  business_date DATE NOT NULL,
  balance NUMERIC NOT NULL,
  currency STRING NOT NULL,
  batch_id STRING NOT NULL,
  source_file STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL,
  FOREIGN KEY (account_key) REFERENCES `curated.dim_account` (account_key) NOT ENFORCED
)
PARTITION BY business_date
CLUSTER BY account_key
OPTIONS (
  description = 'One row per account per business date',
  require_partition_filter = TRUE
);

-- Unknown members retain late-arriving facts without inventing source attributes.
INSERT INTO `curated.dim_customer`
SELECT '0', '__UNKNOWN__', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'Pending',
       DATE '1900-01-01', DATE '1900-01-01', DATE '9999-12-31', TRUE, '0',
       '__SYSTEM__', '__SYSTEM__', CURRENT_TIMESTAMP()
WHERE NOT EXISTS (
  SELECT 1 FROM `curated.dim_customer` WHERE customer_key = '0'
);

INSERT INTO `curated.dim_account`
SELECT '0', '__UNKNOWN__', '__UNKNOWN__', 'Unknown', 'INR', NULL, NULL,
       DATE '1900-01-01', 'Inactive', DATE '1900-01-01', DATE '9999-12-31',
       TRUE, '0', '__SYSTEM__', '__SYSTEM__', CURRENT_TIMESTAMP()
WHERE NOT EXISTS (
  SELECT 1 FROM `curated.dim_account` WHERE account_key = '0'
);

INSERT INTO `curated.dim_merchant`
SELECT '0', '__UNKNOWN__', 'Unknown', 'Unknown', NULL, NULL, DATE '1900-01-01',
       'Inactive', DATE '1900-01-01', DATE '9999-12-31', TRUE, '0',
       '__SYSTEM__', '__SYSTEM__', CURRENT_TIMESTAMP()
WHERE NOT EXISTS (
  SELECT 1 FROM `curated.dim_merchant` WHERE merchant_key = '0'
);
