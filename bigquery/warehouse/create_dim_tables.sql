CREATE TABLE IF NOT EXISTS 'banking_dwh.dim_customer'(
    customer_id STRING,
    name STRING,
    age INT64,
    gender STRING,
    city STRING,
    state STRING,
    email STRING,
    phone STRING,
    kyc_status STRING,
    customer_since DATE
);
CREATE TABLE IF NOT EXISTS 'banking_dwh.dim_acoount'(
    account_id STRING,
    customer_id STRING,
    account_type STRING,
    balance FLOAT64,
    currency STRING,
    branch_code STRING,
    ifsc_code STRING,
    opened_date DATE,
    status STRING
);
CREATE TABLE IF NOT EXISTS 'banking_dwh.dim_merchant'(
    merchant_id STRING,
    merchant_name STRING,
    category STRING,
    city STRING,
    state STRING,
    registered_since STRING,
    status STRING
);
CREATE TABLE IF NOT EXISTS 'banking_dwh.dim_date'(
    date_id STRING,
    full_date DATE,
    day INT64,
    month INT64,
    month_name STRING,
    quarter INT64,
    year INT64,
    day_of_week STRING,
    is_weekend BOOL
);