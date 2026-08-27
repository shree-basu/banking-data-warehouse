"""Airflow import and topology gate for the production DAG."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.airflow


def test_dagbag_has_no_import_errors() -> None:
    from airflow.models import DagBag

    dag_folder = Path(__file__).parents[1] / "dags"
    dagbag = DagBag(dag_folder=str(dag_folder), include_examples=False)
    assert dagbag.import_errors == {}

    dag = dagbag.dags.get("banking_batch_warehouse")
    assert dag is not None
    assert dag.max_active_runs == 1
    expected_groups = {
        "wait_and_validate_manifest",
        "load_strict_staging",
        "run_staging_dq",
        "reconcile_source_and_staging",
        "publish_dimensions",
        "publish_facts",
        "run_curated_dq",
        "update_analytics",
        "mark_batch_successful",
    }
    assert expected_groups <= set(dag.task_group.children)
    sensor = dag.get_task("wait_and_validate_manifest.wait_for_manifest")
    assert sensor.deferrable is True
