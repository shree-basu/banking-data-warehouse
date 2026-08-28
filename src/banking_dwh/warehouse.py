"""Transactional reference model for cloud-free acceptance tests."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from .contracts import BatchContractError, DqResult, validate_batch

UNKNOWN_KEY = "0"
SCD = {
    "customers": (
        "customer_id",
        ["name", "age", "gender", "city", "state", "email", "phone", "kyc_status"],
    ),
    "accounts": (
        "account_id",
        ["customer_id", "account_type", "currency", "branch_code", "ifsc_code", "status"],
    ),
    "merchants": ("merchant_id", ["merchant_name", "category", "city", "state", "status"]),
}


def _digest(*values: str) -> str:
    return hashlib.sha256("|".join(values).encode()).hexdigest()


@dataclass
class LocalWarehouse:
    """Mirrors the invariants that the BigQuery SQL must preserve."""

    dimensions: dict[str, list[dict]] = field(
        default_factory=lambda: {entity: [] for entity in SCD}
    )
    transactions: dict[str, dict] = field(default_factory=dict)
    account_snapshots: dict[tuple[str, str], dict] = field(default_factory=dict)
    batch_runs: dict[str, dict] = field(default_factory=dict)
    dq_results: list[dict] = field(default_factory=list)
    quarantine: list[dict] = field(default_factory=list)

    def curated_counts(self) -> dict[str, int]:
        return {
            **{name: len(rows) for name, rows in self.dimensions.items()},
            "transactions": len(self.transactions),
            "account_snapshots": len(self.account_snapshots),
        }

    def transaction_total(self) -> Decimal:
        return sum((Decimal(row["amount"]) for row in self.transactions.values()), Decimal("0"))

    def publish(self, manifest_path: Path, *, dag_run_id: str = "local-test") -> dict:
        before = copy.deepcopy(self.__dict__)
        try:
            manifest, rows, results = validate_batch(manifest_path)
            batch_id = manifest["batch_id"]
            if self.batch_runs.get(batch_id, {}).get("status") == "SUCCESS":
                return self.batch_runs[batch_id]
            for entity in SCD:
                self._publish_dimension(entity, rows[entity], manifest)
            self._publish_transactions(rows["transactions"], manifest)
            self._publish_snapshots(rows["account_snapshots"], manifest)
            self._assert_scd()
            source_count, curated_count, source_amount, curated_amount = (
                self._assert_batch_reconciliation(manifest, rows)
            )
            run = {
                "batch_id": batch_id,
                "business_date": manifest["business_date"],
                "dag_run_id": dag_run_id,
                "status": "SUCCESS",
                "source_row_count": sum(len(value) for value in rows.values()),
                "curated_counts": self.curated_counts(),
                "source_transaction_count": source_count,
                "curated_transaction_count": curated_count,
                "source_amount": str(source_amount),
                "curated_amount": str(curated_amount),
                "code_version": "local-reference-v2",
            }
            self.batch_runs[batch_id] = run
            self.dq_results.extend(self._dq_rows(batch_id, results))
            return run
        except BatchContractError as error:
            rejected = error.quarantine
            self.__dict__.update(before)
            self.quarantine.extend(rejected)
            raise

    @staticmethod
    def _dq_rows(batch_id: str, results: list[DqResult]) -> list[dict]:
        return [
            {
                "batch_id": batch_id,
                "rule_code": result.rule_code,
                "entity": result.entity,
                "passed": result.passed,
                "observed": result.observed,
                "severity": result.severity,
            }
            for result in results
        ]

    def _publish_dimension(self, entity: str, source_rows: list[dict], manifest: dict) -> None:
        natural_key, tracked = SCD[entity]
        effective_from = manifest["business_date"]
        rows = self.dimensions[entity]
        for source in source_rows:
            key = source[natural_key]
            current = next(
                (row for row in rows if row[natural_key] == key and row["is_current"]), None
            )
            hash_diff = _digest(*(source[column] for column in tracked))
            if current and current["hash_diff"] == hash_diff:
                continue
            if current:
                current["effective_to"] = effective_from
                current["is_current"] = False
            rows.append(
                {
                    **source,
                    f"{entity[:-1]}_key": _digest(entity, key, effective_from)[:24],
                    "effective_from": effective_from,
                    "effective_to": "9999-12-31",
                    "is_current": True,
                    "hash_diff": hash_diff,
                    "batch_id": manifest["batch_id"],
                    "source_file": manifest["expected_entities"][entity]["object_path"],
                    "loaded_at": f"{effective_from}T02:00:00+05:30",
                }
            )

    def _dimension_key(self, entity: str, natural_key: str, event_date: str) -> str:
        natural_column = SCD[entity][0]
        surrogate_column = f"{entity[:-1]}_key"
        match = next(
            (
                row
                for row in self.dimensions[entity]
                if row[natural_column] == natural_key
                and row["effective_from"] <= event_date < row["effective_to"]
            ),
            None,
        )
        return match[surrogate_column] if match else UNKNOWN_KEY

    def _publish_transactions(self, source_rows: list[dict], manifest: dict) -> None:
        for source in source_rows:
            if source["transaction_id"] in self.transactions:
                continue
            event_date = source["transaction_ts"][:10]
            account_key = self._dimension_key("accounts", source["account_id"], event_date)
            account = next(
                (
                    row
                    for row in self.dimensions["accounts"]
                    if row.get("account_key") == account_key
                ),
                None,
            )
            self.transactions[source["transaction_id"]] = {
                **source,
                "transaction_date": event_date,
                "account_key": account_key,
                "customer_key": self._dimension_key("customers", account["customer_id"], event_date)
                if account
                else UNKNOWN_KEY,
                "merchant_key": self._dimension_key("merchants", source["merchant_id"], event_date),
                "date_key": event_date.replace("-", ""),
                "batch_id": manifest["batch_id"],
                "source_file": manifest["expected_entities"]["transactions"]["object_path"],
            }

    def _publish_snapshots(self, source_rows: list[dict], manifest: dict) -> None:
        for source in source_rows:
            identity = (source["account_id"], source["business_date"])
            self.account_snapshots[identity] = {
                **source,
                "account_key": self._dimension_key(
                    "accounts", source["account_id"], source["business_date"]
                ),
                "batch_id": manifest["batch_id"],
                "source_file": manifest["expected_entities"]["account_snapshots"]["object_path"],
            }

    def repair_unknown_dimension_keys(self) -> int:
        repaired = 0
        for fact in self.transactions.values():
            if fact["account_key"] == UNKNOWN_KEY:
                account_key = self._dimension_key(
                    "accounts", fact["account_id"], fact["transaction_date"]
                )
                if account_key != UNKNOWN_KEY:
                    fact["account_key"] = account_key
                    account = next(
                        row
                        for row in self.dimensions["accounts"]
                        if row["account_key"] == account_key
                    )
                    fact["customer_key"] = self._dimension_key(
                        "customers", account["customer_id"], fact["transaction_date"]
                    )
                    repaired += 1
            if fact["merchant_key"] == UNKNOWN_KEY:
                merchant_key = self._dimension_key(
                    "merchants", fact["merchant_id"], fact["transaction_date"]
                )
                if merchant_key != UNKNOWN_KEY:
                    fact["merchant_key"] = merchant_key
                    repaired += 1
        return repaired

    def _assert_batch_reconciliation(
        self, manifest: dict, rows: dict[str, list[dict]]
    ) -> tuple[int, int, Decimal, Decimal]:
        batch_id = manifest["batch_id"]
        source_count = len(rows["transactions"])
        source_amount = sum((Decimal(row["amount"]) for row in rows["transactions"]), Decimal("0"))
        curated_rows = [row for row in self.transactions.values() if row["batch_id"] == batch_id]
        curated_count = len(curated_rows)
        curated_amount = sum((Decimal(row["amount"]) for row in curated_rows), Decimal("0"))
        if source_count != curated_count:
            raise BatchContractError("final row-count reconciliation failed")
        if source_amount != curated_amount:
            raise BatchContractError("final monetary reconciliation failed")
        return source_count, curated_count, source_amount, curated_amount

    def _assert_scd(self) -> None:
        for entity, rows in self.dimensions.items():
            natural_key = SCD[entity][0]
            for key in {row[natural_key] for row in rows}:
                versions = sorted(
                    [row for row in rows if row[natural_key] == key],
                    key=lambda row: row["effective_from"],
                )
                if sum(row["is_current"] for row in versions) != 1:
                    raise AssertionError(f"{entity}:{key} must have one current row")
                for left, right in zip(versions, versions[1:], strict=False):
                    if left["effective_to"] > right["effective_from"]:
                        raise AssertionError(f"{entity}:{key} has overlapping versions")
