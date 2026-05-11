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