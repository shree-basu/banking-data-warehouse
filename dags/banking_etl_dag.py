from airflow import DAG
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.operator.dummy import DummyOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'shreetama',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id = 'banking_etl_pipeline',
    default_args = default_args,
    description = 'End-to-end Banking Data Warehouse ETL pipeline',
    schedule_interval = '0 2 * * *',
    start_date = (2024,1,1),
    catchup = False,
    tags = ['banking', 'etl', 'bigquery']
) as dag: