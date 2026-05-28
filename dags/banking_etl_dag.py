from airflow import DAG
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.operators.dummy import DummyOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'shreetama',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id='banking_etl_pipeline',
    default_args=default_args,
    description='End-to-end Banking Data Warehouse ETL pipeline',
    schedule_interval='0 2 * * *',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['banking', 'etl', 'bigquery']
) as dag:

    start = DummyOperator(task_id='start')
    end = DummyOperator(task_id='end')

    load_customers = GCSToBigQueryOperator(
        task_id='load_customers_to_staging',
        bucket='{{ var.value.gcs_bucket }}',
        source_objects=['customers.csv'],
        destination_project_dataset_table='banking_dwh.stg_customers',
        source_format='CSV',
        skip_leading_rows=1,
        write_disposition='WRITE_TRUNCATE'
    )

    load_accounts = GCSToBigQueryOperator(
        task_id='load_accounts_to_staging',
        bucket='{{ var.value.gcs_bucket }}',
        source_objects=['accounts.csv'],
        destination_project_dataset_table='banking_dwh.stg_accounts',
        source_format='CSV',
        skip_leading_rows=1,
        write_disposition='WRITE_TRUNCATE'
    )

    load_merchants = GCSToBigQueryOperator(
        task_id='load_merchants_to_staging',
        bucket='{{ var.value.gcs_bucket }}',
        source_objects=['merchants.csv'],
        destination_project_dataset_table='banking_dwh.stg_merchants',
        source_format='CSV',
        skip_leading_rows=1,
        write_disposition='WRITE_TRUNCATE'
    )

    load_dates = GCSToBigQueryOperator(
        task_id='load_dates_to_staging',
        bucket='{{ var.value.gcs_bucket }}',
        source_objects=['dates.csv'],
        destination_project_dataset_table='banking_dwh.stg_dates',
        source_format='CSV',
        skip_leading_rows=1,
        write_disposition='WRITE_TRUNCATE'
    )

    load_transactions = GCSToBigQueryOperator(
        task_id='load_transactions_to_staging',
        bucket='{{ var.value.gcs_bucket }}',
        source_objects=['transactions.csv'],
        destination_project_dataset_table='banking_dwh.stg_transactions',
        source_format='CSV',
        skip_leading_rows=1,
        write_disposition='WRITE_TRUNCATE'
    )

    load_dim_customer = BigQueryInsertJobOperator(
        task_id='load_dim_customer',
        configuration={
            "query": {
                "query": """
                    INSERT INTO `banking_dwh.dim_customer`
                    SELECT
                        customer_id,
                        name,
                        age,
                        gender,
                        city,
                        state,
                        email,
                        phone,
                        kyc_status,
                        PARSE_DATE('%Y-%m-%d', customer_since) AS customer_since
                    FROM `banking_dwh.stg_customers`
                """,
                "useLegacySql": False
            }
        }
    )

    load_dim_account = BigQueryInsertJobOperator(
        task_id='load_dim_account',
        configuration={
            "query": {
                "query": """
                    INSERT INTO `banking_dwh.dim_account`
                    SELECT
                        account_id,
                        customer_id,
                        account_type,
                        balance,
                        currency,
                        branch_code,
                        ifsc_code,
                        PARSE_DATE('%Y-%m-%d', opened_date) AS opened_date,
                        status
                    FROM `banking_dwh.stg_accounts`
                """,
                "useLegacySql": False
            }
        }
    )

    load_dim_merchant = BigQueryInsertJobOperator(
        task_id='load_dim_merchant',
        configuration={
            "query": {
                "query": """
                    INSERT INTO `banking_dwh.dim_merchant`
                    SELECT
                        merchant_id,
                        merchant_name,
                        category,
                        city,
                        state,
                        PARSE_DATE('%Y-%m-%d', registered_since) AS registered_since,
                        status
                    FROM `banking_dwh.stg_merchants`
                """,
                "useLegacySql": False
            }
        }
    )

    load_dim_date = BigQueryInsertJobOperator(
        task_id='load_dim_date',
        configuration={
            "query": {
                "query": """
                    INSERT INTO `banking_dwh.dim_date`
                    SELECT
                        date_id,
                        PARSE_DATE('%Y-%m-%d', full_date) AS full_date,
                        day,
                        month,
                        month_name,
                        quarter,
                        year,
                        day_of_week,
                        is_weekend
                    FROM `banking_dwh.stg_dates`
                """,
                "useLegacySql": False
            }
        }
    )

    load_fact_transactions = BigQueryInsertJobOperator(
        task_id='load_fact_transactions',
        configuration={
            "query": {
                "query": """
                    INSERT INTO `banking_dwh.fact_transactions`
                    SELECT
                        transaction_id,
                        account_id,
                        merchant_id,
                        date_id,
                        PARSE_DATE('%Y%m%d', date_id) AS transaction_date,
                        amount,
                        currency,
                        channel,
                        transaction_type,
                        status,
                        ip_address,
                        country_code
                    FROM `banking_dwh.stg_transactions`
                """,
                "useLegacySql": False
            }
        }
    )

    start >> [load_customers, load_accounts, load_merchants, load_dates, load_transactions]

    [load_customers, load_accounts, load_merchants, load_dates, load_transactions] >> load_dim_customer

    load_dim_customer >> load_dim_account

    [load_dim_account, load_dim_merchant, load_dim_date] >> load_fact_transactions

    load_fact_transactions >> end