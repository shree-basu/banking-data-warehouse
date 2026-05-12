CREATE TABLE IF NOT EXISTS 'banking_dwh.fact_transactions'(
    transaction_id STRING,
    account_id STRING,
    merchant_id STRING,
    date_id STRING,
    transaction_date DATE,
    amount FLOAT64,
    currency STRING,
    channel STRING,
    transaction_type STRING,
    status STRING,
    ip_address STRING,
    country_code STRING
)
PARTITION BY transaction_date
CLUSTER BY status,channel,transaction_type;