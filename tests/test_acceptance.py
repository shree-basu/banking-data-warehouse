from __future__ import annotations

import importlib.util
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from banking_dwh import BatchContractError, LocalWarehouse, validate_batch
from banking_dwh.warehouse import UNKNOWN_KEY


def _generator():
    path = Path(__file__).parents[1] / "data" / "simulator" / "generate_data.py"
    spec = importlib.util.spec_from_file_location("generate_data", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def generator():
    return _generator()


@pytest.fixture
def initial_manifest(tmp_path, generator):
    return generator.generate_batch(
        tmp_path,
        business_date=date(2026, 1, 1),
        batch_id="batch-20260101-v1",
        scenario="initial",
    )


def test_manifest_schema_checksums_and_historical_path(initial_manifest):
    manifest, rows, results = validate_batch(initial_manifest)
    assert manifest["batch_id"] == "batch-20260101-v1"
    assert set(rows) == {"customers", "accounts", "merchants", "transactions", "account_snapshots"}
    assert all(result.passed for result in results if result.severity == "ERROR")
    normalized = str(initial_manifest).replace("\\", "/")
    assert "business_date=2026-01-01/batch_id=batch-20260101-v1" in normalized
    assert all(
        metadata["object_path"].startswith(
            "raw/business_date=2026-01-01/batch_id=batch-20260101-v1/"
        )
        for metadata in manifest["expected_entities"].values()
    )


def test_generation_is_byte_deterministic(tmp_path, generator):
    first = generator.generate_batch(
        tmp_path / "first",
        business_date=date(2026, 1, 1),
        batch_id="batch-20260101-v1",
    )
    second = generator.generate_batch(
        tmp_path / "second",
        business_date=date(2026, 1, 1),
        batch_id="batch-20260101-v1",
    )
    assert first.read_bytes() == second.read_bytes()
    assert {p.name: p.read_bytes() for p in first.parent.glob("*.csv")} == {
        p.name: p.read_bytes() for p in second.parent.glob("*.csv")
    }


def test_initial_replay_and_next_day_scd(initial_manifest, tmp_path, generator):
    warehouse = LocalWarehouse()
    first = warehouse.publish(initial_manifest)
    initial_counts = warehouse.curated_counts()
    initial_total = warehouse.transaction_total()
    assert first["source_row_count"] == 55

    assert warehouse.publish(initial_manifest) == first
    assert warehouse.curated_counts() == initial_counts
    assert warehouse.transaction_total() == initial_total

    next_day = generator.generate_batch(
        tmp_path,
        business_date=date(2026, 1, 2),
        batch_id="batch-20260102-v1",
        scenario="next_day",
    )
    warehouse.publish(next_day)
    assert warehouse.curated_counts()["customers"] == initial_counts["customers"] + 1
    assert warehouse.curated_counts()["accounts"] == initial_counts["accounts"] + 1
    assert warehouse.curated_counts()["merchants"] == initial_counts["merchants"] + 1
    keys = {"customers": "customer_id", "accounts": "account_id", "merchants": "merchant_id"}
    for entity, rows in warehouse.dimensions.items():
        for natural_key in {row[keys[entity]] for row in rows}:
            versions = [row for row in rows if row[keys[entity]] == natural_key]
            assert sum(row["is_current"] for row in versions) == 1


def test_critical_dq_failure_is_quarantined_and_atomic(initial_manifest, tmp_path, generator):
    warehouse = LocalWarehouse()
    warehouse.publish(initial_manifest)
    before_counts = warehouse.curated_counts()
    before_total = warehouse.transaction_total()
    invalid = generator.generate_batch(
        tmp_path,
        business_date=date(2026, 1, 2),
        batch_id="batch-invalid",
        scenario="invalid",
    )
    with pytest.raises(BatchContractError) as caught:
        warehouse.publish(invalid)
    assert any(result.rule_code == "UNIQUE_NATURAL_KEY" for result in caught.value.results)
    assert warehouse.curated_counts() == before_counts
    assert warehouse.transaction_total() == before_total
    assert warehouse.quarantine


def test_late_dimension_uses_unknown_member(initial_manifest, tmp_path, generator):
    warehouse = LocalWarehouse()
    warehouse.publish(initial_manifest)
    late = generator.generate_batch(
        tmp_path,
        business_date=date(2026, 1, 2),
        batch_id="batch-late",
        scenario="late_dimension",
    )
    warehouse.publish(late)
    late_facts = [
        fact for fact in warehouse.transactions.values() if fact["batch_id"] == "batch-late"
    ]
    assert any(fact["account_key"] == UNKNOWN_KEY for fact in late_facts)
    assert warehouse.repair_unknown_dimension_keys() == 0
    assert warehouse.transaction_total() > Decimal("0")


def test_manifest_checksum_tampering_fails(initial_manifest):
    manifest = json.loads(initial_manifest.read_text(encoding="utf-8"))
    object_name = Path(manifest["expected_entities"]["customers"]["object_path"]).name
    (initial_manifest.parent / object_name).write_text("tampered\n", encoding="utf-8")
    with pytest.raises(BatchContractError, match="missing or corrupt"):
        validate_batch(initial_manifest)


def test_manifest_object_path_must_match_contract(initial_manifest):
    manifest = json.loads(initial_manifest.read_text(encoding="utf-8"))
    manifest["expected_entities"]["customers"]["object_path"] = (
        "raw/business_date=2026-01-01/batch_id=batch-20260101-v1/accounts.csv"
    )
    initial_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BatchContractError, match="object path does not match"):
        validate_batch(initial_manifest)


def test_final_reconciliation_failure_rolls_back(
    initial_manifest, tmp_path, generator, monkeypatch
):
    warehouse = LocalWarehouse()
    warehouse.publish(initial_manifest)
    before_counts = warehouse.curated_counts()
    next_day = generator.generate_batch(
        tmp_path,
        business_date=date(2026, 1, 2),
        batch_id="batch-20260102-v1",
        scenario="next_day",
    )
    publish_transactions = warehouse._publish_transactions
    monkeypatch.setattr(
        warehouse,
        "_publish_transactions",
        lambda rows, manifest: publish_transactions(rows[:-1], manifest),
    )
    with pytest.raises(BatchContractError, match="final row-count reconciliation failed"):
        warehouse.publish(next_day)
    assert warehouse.curated_counts() == before_counts


def test_late_merchant_key_is_repaired(initial_manifest):
    warehouse = LocalWarehouse()
    warehouse.publish(initial_manifest)
    fact = next(iter(warehouse.transactions.values()))
    expected_merchant_key = fact["merchant_key"]
    fact["merchant_key"] = UNKNOWN_KEY

    assert warehouse.repair_unknown_dimension_keys() == 1
    assert fact["merchant_key"] == expected_merchant_key
