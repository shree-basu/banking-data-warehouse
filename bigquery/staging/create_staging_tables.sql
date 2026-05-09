CREATE TABLE IF NOT EXISTS 'banking_dwh.stg_customers'(
    customer_id STRING,
    name STRING,
    age INT64,
    gender STRING,
    city STRING,
    state STRING,
    email STRING,
    phone STRING,
    kyc_status STRING,
    customer_since STRING
);

CREATE TABLE IF NOT EXISTS 'banking_dwh.stg_accounts'(
    account_id STRING,
    customer_id STRING,
    account_type STRING,
    balance FLOAT64,
    currency STRING,
    branch_code STRING,
    ifsc_code STRING,
    opened_date STRING,
    status STRING
);

CREATE TABLE IF NOT EXISTS 'banking_dwh.stg_merchants'(
    merchant_id STRING,
    merchant_name STRING,
    category STRING,
    city STRING,
    state STRING,
    registered_since STRING,
    status STRING
);