"""Idempotent daily GCS-to-BigQuery banking warehouse orchestration."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.utils.task_group import TaskGroup

IST = pendulum.timezone("Asia/Kolkata")
BUSINESS_DATE = "{{ data_interval_start.in_timezone('Asia/Kolkata').format('YYYY-MM-DD') }}"
BATCH_ID = (
    "{{ 'batch-' ~ "
    "data_interval_start.in_timezone('Asia/Kolkata').format('YYYYMMDD') ~ '-v1' }}"
)
BATCH_TOKEN = (
    "{{ 'batch_' ~ "
    "data_interval_start.in_timezone('Asia/Kolkata').format('YYYYMMDD') ~ '_v1' }}"
)
RAW_ROOT = f"raw/business_date={BUSINESS_DATE}/batch_id={BATCH_ID}"
ENTITIES = ("customers", "accounts", "merchants", "transactions", "account_snapshots")

SCHEMAS = {
    "customers": [
        {"name": "customer_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "name", "type": "STRING", "mode": "NULLABLE"},
        {"name": "age", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "gender", "type": "STRING", "mode": "NULLABLE"},
        {"name": "city", "type": "STRING", "mode": "NULLABLE"},
        {"name": "state", "type": "STRING", "mode": "NULLABLE"},
        {"name": "email", "type": "STRING", "mode": "NULLABLE"},
        {"name": "phone", "type": "STRING", "mode": "NULLABLE"},
        {"name": "kyc_status", "type": "STRING", "mode": "REQUIRED"},
        {"name": "customer_since", "type": "DATE", "mode": "NULLABLE"},
    ],
    "accounts": [
        {"name": "account_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "customer_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "account_type", "type": "STRING", "mode": "REQUIRED"},
        {"name": "currency", "type": "STRING", "mode": "REQUIRED"},
        {"name": "branch_code", "type": "STRING", "mode": "NULLABLE"},
        {"name": "ifsc_code", "type": "STRING", "mode": "NULLABLE"},
        {"name": "opened_date", "type": "DATE", "mode": "NULLABLE"},
        {"name": "status", "type": "STRING", "mode": "REQUIRED"},
    ],
    "merchants": [
        {"name": "merchant_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "merchant_name", "type": "STRING", "mode": "NULLABLE"},
        {"name": "category", "type": "STRING", "mode": "REQUIRED"},
        {"name": "city", "type": "STRING", "mode": "NULLABLE"},
        {"name": "state", "type": "STRING", "mode": "NULLABLE"},
        {"name": "registered_since", "type": "DATE", "mode": "NULLABLE"},
        {"name": "status", "type": "STRING", "mode": "REQUIRED"},
    ],
    "transactions": [
        {"name": "transaction_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "account_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "merchant_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "transaction_ts", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "amount", "type": "NUMERIC", "mode": "REQUIRED"},
        {"name": "currency", "type": "STRING", "mode": "REQUIRED"},
        {"name": "channel", "type": "STRING", "mode": "REQUIRED"},
        {"name": "transaction_type", "type": "STRING", "mode": "REQUIRED"},
        {"name": "status", "type": "STRING", "mode": "REQUIRED"},
        {"name": "ip_address", "type": "STRING", "mode": "NULLABLE"},
        {"name": "country_code", "type": "STRING", "mode": "NULLABLE"},
    ],
    "account_snapshots": [
        {"name": "account_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "business_date", "type": "DATE", "mode": "REQUIRED"},
        {"name": "balance", "type": "NUMERIC", "mode": "REQUIRED"},
        {"name": "currency", "type": "STRING", "mode": "REQUIRED"},
    ],
}


def validate_manifest(bucket: str, object_name: str, **context) -> dict:
    """Download and validate the manifest and every declared SHA-256 checksum."""
    hook = GCSHook(gcp_conn_id="google_cloud_default")
    manifest = json.loads(hook.download(bucket_name=bucket, object_name=object_name))
    expected_date = context["data_interval_start"].in_timezone(IST).to_date_string()
    requested_batch = f"batch-{expected_date.replace('-', '')}-v1"
    if manifest["business_date"] != expected_date or manifest["batch_id"] != requested_batch:
        raise AirflowFailException("manifest identity does not match the scheduled data interval")
    if set(manifest["expected_entities"]) != set(ENTITIES):
        raise AirflowFailException("manifest entity set does not match the data contract")
    for entity, metadata in manifest["expected_entities"].items():
        payload = hook.download(bucket_name=bucket, object_name=metadata["object_path"])
        if hashlib.sha256(payload).hexdigest() != metadata["sha256"]:
            raise AirflowFailException(f"SHA-256 mismatch for {entity}")
    return manifest


def structured_failure(context) -> None:
    event = {
        "event": "banking_batch_failure",
        "dag_id": context["dag"].dag_id,
        "run_id": context["run_id"],
        "task_id": context["task_instance"].task_id,
        "logical_date": context["logical_date"].isoformat(),
        "exception": str(context.get("exception", ""))[:1000],
    }
    logging.getLogger(__name__).error(json.dumps(event, sort_keys=True))
    try:
        project = Variable.get("gcp_project_id")
        batch_id = (
            "batch-"
            f"{context['data_interval_start'].in_timezone(IST).format('YYYYMMDD')}"
            "-v1"
        )
        BigQueryHook().insert_job(
            project_id=project,
            configuration={"query": {
                "query": (
                    "UPDATE `audit.batch_run` SET status='FAILED', "
                    "completed_at=CURRENT_TIMESTAMP(), error_summary=@error "
                    "WHERE batch_id=@batch_id"
                ),
                "useLegacySql": False,
                "queryParameters": [
                    {"name": "error", "parameterType": {"type": "STRING"},
                     "parameterValue": {"value": event["exception"]}},
                    {"name": "batch_id", "parameterType": {"type": "STRING"},
                     "parameterValue": {"value": batch_id}},
                ],
            }},
        )
    except Exception:
        logging.getLogger(__name__).exception("failed to persist failure audit")


def query_task(task_id: str, sql: str, *, group: TaskGroup, retries: int = 2):
    return BigQueryInsertJobOperator(
        task_id=task_id,
        task_group=group,
        configuration={"query": {"query": sql, "useLegacySql": False}},
        location="{{ var.value.bq_location }}",
        job_id=f"banking_{task_id}_{BATCH_TOKEN}",
        force_rerun=False,
        reattach_states={"PENDING", "RUNNING", "DONE"},
        retries=retries,
    )


with DAG(
    dag_id="banking_batch_warehouse",
    description="Manifest-gated, idempotent batch warehouse publication",
    start_date=pendulum.datetime(2026, 1, 1, tz=IST),
    schedule="0 2 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "data-engineering",
        "depends_on_past": False,
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=15),
        "execution_timeout": timedelta(minutes=45),
        "on_failure_callback": structured_failure,
    },
    render_template_as_native_obj=True,
    tags=["banking", "batch", "bigquery"],
) as dag:
    with TaskGroup("wait_and_validate_manifest") as wait_group:
        wait_manifest = GCSObjectExistenceSensor(
            task_id="wait_for_manifest",
            bucket="{{ var.value.raw_bucket }}",
            object=f"{RAW_ROOT}/manifest.json",
            deferrable=True,
            timeout=3600,
            poke_interval=60,
            soft_fail=False,
        )
        validate = PythonOperator(
            task_id="validate_manifest",
            python_callable=validate_manifest,
            op_kwargs={
                "bucket": "{{ var.value.raw_bucket }}",
                "object_name": f"{RAW_ROOT}/manifest.json",
            },
            retries=0,
        )
        start_audit = query_task(
            "start_batch_audit",
            f"""
            MERGE `audit.batch_run` AS target
            USING (
              SELECT '{BATCH_ID}' AS batch_id, DATE '{BUSINESS_DATE}' AS business_date
            ) AS source
            ON target.batch_id = source.batch_id
            WHEN NOT MATCHED THEN INSERT (
              batch_id, business_date, dag_id, dag_run_id, started_at, status, code_version
            ) VALUES (
              source.batch_id, source.business_date, '{{{{ dag.dag_id }}}}',
              '{{{{ run_id }}}}', CURRENT_TIMESTAMP(), 'RUNNING',
              '{{{{ var.value.get("code_version", "unversioned") }}}}'
            );
            """,
            group=wait_group,
        )
        wait_manifest >> validate >> start_audit

    with TaskGroup("load_strict_staging") as load_group:
        load_tasks = {}
        for entity in ENTITIES:
            load_tasks[entity] = GCSToBigQueryOperator(
                task_id=f"load_{entity}",
                bucket="{{ var.value.raw_bucket }}",
                source_objects=[f"{RAW_ROOT}/{entity}.csv"],
                destination_project_dataset_table=(
                    f"{{{{ var.value.gcp_project_id }}}}.staging.stg_{entity}__{BATCH_TOKEN}"
                ),
                schema_fields=SCHEMAS[entity],
                source_format="CSV",
                skip_leading_rows=1,
                autodetect=False,
                max_bad_records=0,
                write_disposition="WRITE_TRUNCATE",
                create_disposition="CREATE_IF_NEEDED",
                location="{{ var.value.bq_location }}",
            )

    with TaskGroup("run_staging_dq") as staging_dq_group:
        staging_dq = query_task(
            "assert_staging_quality",
            f"""
            DECLARE failed_rules INT64;
            CREATE TEMP TABLE rules AS
            SELECT 'UNIQUE_TRANSACTION_ID' AS rule_code, 'transactions' AS entity,
                   COUNT(*) - COUNT(DISTINCT transaction_id) AS failures
            FROM `staging.stg_transactions__{BATCH_TOKEN}`
            UNION ALL
            SELECT 'POSITIVE_AMOUNT', 'transactions', COUNTIF(amount <= 0)
            FROM `staging.stg_transactions__{BATCH_TOKEN}`
            UNION ALL
            SELECT 'VALID_TRANSACTION_DOMAIN', 'transactions',
                   COUNTIF(status NOT IN ('Success', 'Failed', 'Pending')
                     OR transaction_type NOT IN ('Debit', 'Credit')
                     OR currency != 'INR')
            FROM `staging.stg_transactions__{BATCH_TOKEN}`
            UNION ALL
            SELECT 'ACCOUNT_CUSTOMER_FK', 'accounts', COUNT(*)
            FROM `staging.stg_accounts__{BATCH_TOKEN}` AS account
            LEFT JOIN `staging.stg_customers__{BATCH_TOKEN}` AS customer
              USING (customer_id)
            WHERE customer.customer_id IS NULL;

            INSERT INTO `audit.dq_result`
            SELECT '{BATCH_ID}', DATE '{BUSINESS_DATE}', rule_code, entity,
                   'ERROR', failures = 0, CAST(failures AS STRING), '0',
                   CURRENT_TIMESTAMP()
            FROM rules;

            INSERT INTO `audit.quarantine`
            SELECT '{BATCH_ID}', DATE '{BUSINESS_DATE}', 'transactions',
                   transaction_id, 'POSITIVE_AMOUNT', 'amount must be positive',
                   '{RAW_ROOT}/transactions.csv', TO_JSON(source), CURRENT_TIMESTAMP()
            FROM `staging.stg_transactions__{BATCH_TOKEN}` AS source
            WHERE amount <= 0;

            SET failed_rules = (SELECT COUNTIF(failures > 0) FROM rules);
            ASSERT failed_rules = 0 AS 'permanent staging DQ failure';
            """,
            group=staging_dq_group,
            retries=0,
        )

    with TaskGroup("reconcile_source_and_staging") as reconcile_group:
        reconcile = query_task(
            "reconcile_manifest_counts",
            f"""
            DECLARE expected_transactions INT64 DEFAULT CAST(
              '{{{{ ti.xcom_pull(
                task_ids="wait_and_validate_manifest.validate_manifest"
              )["expected_entities"]["transactions"]["expected_row_count"] }}}}' AS INT64
            );
            DECLARE staged_transactions INT64 DEFAULT (
              SELECT COUNT(*) FROM `staging.stg_transactions__{BATCH_TOKEN}`
            );
            DECLARE staged_total NUMERIC DEFAULT (
              SELECT COALESCE(SUM(amount), 0)
              FROM `staging.stg_transactions__{BATCH_TOKEN}`
            );
            INSERT INTO `audit.dq_result`
            VALUES (
              '{BATCH_ID}', DATE '{BUSINESS_DATE}', 'SOURCE_STAGE_ROW_COUNT',
              'transactions', 'ERROR', expected_transactions = staged_transactions,
              CAST(staged_transactions AS STRING), CAST(expected_transactions AS STRING),
              CURRENT_TIMESTAMP()
            );
            UPDATE `audit.batch_run`
            SET source_row_count = expected_transactions,
                staging_row_count = staged_transactions,
                source_monetary_total = staged_total
            WHERE batch_id = '{BATCH_ID}';
            ASSERT expected_transactions = staged_transactions
              AS 'source-to-stage reconciliation failed';
            """,
            group=reconcile_group,
            retries=0,
        )

    with TaskGroup("publish_dimensions") as dimension_group:
        customer = query_task(
            "publish_customer",
            f"""CALL `curated.publish_dim_customer`(
              '{BATCH_ID}', DATE '{BUSINESS_DATE}',
              '{{{{ var.value.gcp_project_id }}}}.staging.stg_customers__{BATCH_TOKEN}',
              '{RAW_ROOT}/customers.csv'
            );""",
            group=dimension_group,
        )
        account = query_task(
            "publish_account",
            f"""CALL `curated.publish_dim_account`(
              '{BATCH_ID}', DATE '{BUSINESS_DATE}',
              '{{{{ var.value.gcp_project_id }}}}.staging.stg_accounts__{BATCH_TOKEN}',
              '{RAW_ROOT}/accounts.csv'
            );""",
            group=dimension_group,
        )
        merchant = query_task(
            "publish_merchant",
            f"""CALL `curated.publish_dim_merchant`(
              '{BATCH_ID}', DATE '{BUSINESS_DATE}',
              '{{{{ var.value.gcp_project_id }}}}.staging.stg_merchants__{BATCH_TOKEN}',
              '{RAW_ROOT}/merchants.csv'
            );""",
            group=dimension_group,
        )

    with TaskGroup("publish_facts") as fact_group:
        facts = query_task(
            "merge_facts",
            f"""CALL `curated.publish_facts`(
              '{BATCH_ID}', DATE '{BUSINESS_DATE}',
              '{{{{ var.value.gcp_project_id }}}}.staging.stg_transactions__{BATCH_TOKEN}',
              '{{{{ var.value.gcp_project_id }}}}.staging.stg_account_snapshots__{BATCH_TOKEN}',
              '{RAW_ROOT}/transactions.csv', '{RAW_ROOT}/account_snapshots.csv'
            );""",
            group=fact_group,
        )

    with TaskGroup("run_curated_dq") as curated_dq_group:
        repair_late = query_task(
            "repair_late_dimensions",
            f"CALL `curated.repair_late_account_keys`(DATE '{BUSINESS_DATE}');",
            group=curated_dq_group,
        )
        curated_dq = query_task(
            "assert_curated_quality",
            f"CALL `audit.assert_curated_quality`('{BATCH_ID}', DATE '{BUSINESS_DATE}');",
            group=curated_dq_group,
            retries=0,
        )
        repair_late >> curated_dq

    with TaskGroup("update_analytics") as analytics_group:
        analytics = query_task(
            "refresh_daily_metrics",
            f"CALL `analytics.refresh_daily_transaction_metrics`(DATE '{BUSINESS_DATE}');",
            group=analytics_group,
        )

    with TaskGroup("mark_batch_successful") as completion_group:
        final_reconcile = query_task(
            "final_reconciliation",
            f"CALL `audit.reconcile_batch`('{BATCH_ID}', DATE '{BUSINESS_DATE}');",
            group=completion_group,
            retries=0,
        )
        mark_success = query_task(
            "mark_success",
            f"""
            UPDATE `audit.batch_run`
            SET status = 'SUCCESS', completed_at = CURRENT_TIMESTAMP(),
                rejected_row_count = (
                  SELECT COUNT(*) FROM `audit.quarantine` WHERE batch_id = '{BATCH_ID}'
                )
            WHERE batch_id = '{BATCH_ID}';
            """,
            group=completion_group,
            retries=0,
        )
        final_reconcile >> mark_success

    wait_group >> load_group
    list(load_tasks.values()) >> staging_dq
    staging_dq >> reconcile >> [customer, account, merchant]
    [customer, account, merchant] >> facts
    facts >> curated_dq_group >> analytics >> completion_group
