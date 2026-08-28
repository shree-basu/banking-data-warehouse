"""Manifest and record-level contracts used before curated publication."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

COLUMNS = {
    "customers": {
        "customer_id",
        "name",
        "age",
        "gender",
        "city",
        "state",
        "email",
        "phone",
        "kyc_status",
        "customer_since",
    },
    "accounts": {
        "account_id",
        "customer_id",
        "account_type",
        "currency",
        "branch_code",
        "ifsc_code",
        "opened_date",
        "status",
    },
    "merchants": {
        "merchant_id",
        "merchant_name",
        "category",
        "city",
        "state",
        "registered_since",
        "status",
    },
    "transactions": {
        "transaction_id",
        "account_id",
        "merchant_id",
        "transaction_ts",
        "amount",
        "currency",
        "channel",
        "transaction_type",
        "status",
        "ip_address",
        "country_code",
    },
    "account_snapshots": {"account_id", "business_date", "balance", "currency"},
}
DOMAINS = {
    ("customers", "kyc_status"): {"Verified", "Pending", "Rejected"},
    ("accounts", "status"): {"Active", "Inactive", "Frozen"},
    ("merchants", "status"): {"Active", "Inactive"},
    ("transactions", "status"): {"Success", "Failed", "Pending"},
    ("transactions", "transaction_type"): {"Debit", "Credit"},
}
KEYS = {
    "customers": "customer_id",
    "accounts": "account_id",
    "merchants": "merchant_id",
    "transactions": "transaction_id",
}
GRAINS = {
    **{entity: (key,) for entity, key in KEYS.items()},
    "account_snapshots": ("account_id", "business_date"),
}


@dataclass(frozen=True)
class DqResult:
    rule_code: str
    entity: str
    passed: bool
    observed: int | str
    severity: str = "ERROR"


class BatchContractError(ValueError):
    def __init__(
        self,
        message: str,
        results: list[DqResult] | None = None,
        quarantine: list[dict] | None = None,
    ) -> None:
        super().__init__(message)
        self.results = results or []
        self.quarantine = quarantine or []


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_batch(manifest_path: Path) -> tuple[dict, dict[str, list[dict]], list[DqResult]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {"batch_id", "business_date", "expected_entities", "source_created_at"}
    if required - manifest.keys():
        raise BatchContractError("manifest is missing required metadata")
    if set(manifest["expected_entities"]) != set(COLUMNS):
        raise BatchContractError("manifest entity set does not match the contract")

    by_entity: dict[str, list[dict]] = {}
    results: list[DqResult] = []
    quarantine: list[dict] = []
    for entity, metadata in manifest["expected_entities"].items():
        required_metadata = {"object_path", "expected_row_count", "sha256"}
        if required_metadata - metadata.keys():
            raise BatchContractError(f"manifest metadata is incomplete for {entity}")
        expected_path = (
            f"raw/business_date={manifest['business_date']}/"
            f"batch_id={manifest['batch_id']}/{entity}.csv"
        )
        if metadata["object_path"] != expected_path:
            raise BatchContractError(f"manifest object path does not match contract: {entity}")
        expected_row_count = metadata["expected_row_count"]
        if (
            not isinstance(expected_row_count, int)
            or isinstance(expected_row_count, bool)
            or expected_row_count < 0
        ):
            raise BatchContractError(f"invalid expected row count: {entity}")
        path = manifest_path.parent / Path(metadata["object_path"]).name
        if not path.is_file() or _sha256(path) != metadata["sha256"]:
            raise BatchContractError(f"missing or corrupt object: {entity}")
        rows = _rows(path)
        by_entity[entity] = rows
        results.extend(
            [
                DqResult(
                    "SOURCE_ROW_COUNT",
                    entity,
                    len(rows) == expected_row_count,
                    len(rows),
                ),
                DqResult(
                    "SOURCE_SCHEMA",
                    entity,
                    bool(rows) and set(rows[0]) == COLUMNS[entity],
                    ",".join(sorted(rows[0])) if rows else "",
                ),
            ]
        )

    for entity, grain in GRAINS.items():
        values = [tuple(row[column] for column in grain) for row in by_entity[entity]]
        duplicate_count = len(values) - len(set(values))
        results.append(
            DqResult("UNIQUE_NATURAL_KEY", entity, duplicate_count == 0, duplicate_count)
        )
    for (entity, column), allowed in DOMAINS.items():
        invalid = [row for row in by_entity[entity] if row[column] not in allowed]
        results.append(DqResult(f"DOMAIN_{column.upper()}", entity, not invalid, len(invalid)))
        quarantine.extend(
            {
                "entity": entity,
                "record_key": row[KEYS[entity]],
                "rule_code": f"DOMAIN_{column.upper()}",
                "reason": f"{column}={row[column]!r} is invalid",
            }
            for row in invalid
        )

    bad_amounts = []
    for row in by_entity["transactions"]:
        try:
            if Decimal(row["amount"]) <= 0:
                bad_amounts.append(row)
        except InvalidOperation:
            bad_amounts.append(row)
    results.append(DqResult("POSITIVE_AMOUNT", "transactions", not bad_amounts, len(bad_amounts)))
    quarantine.extend(
        {
            "entity": "transactions",
            "record_key": row["transaction_id"],
            "rule_code": "POSITIVE_AMOUNT",
            "reason": "amount must be positive",
        }
        for row in bad_amounts
    )

    customer_ids = {row["customer_id"] for row in by_entity["customers"]}
    orphan_accounts = [
        row for row in by_entity["accounts"] if row["customer_id"] not in customer_ids
    ]
    results.append(
        DqResult("ACCOUNT_CUSTOMER_FK", "accounts", not orphan_accounts, len(orphan_accounts))
    )
    account_ids = {row["account_id"] for row in by_entity["accounts"]}
    late_refs = sum(row["account_id"] not in account_ids for row in by_entity["transactions"])
    results.append(
        DqResult("LATE_ACCOUNT_REFERENCE", "transactions", True, late_refs, severity="WARN")
    )
    if any(not result.passed and result.severity == "ERROR" for result in results):
        raise BatchContractError("critical data-quality contract failed", results, quarantine)
    return manifest, by_entity, results
