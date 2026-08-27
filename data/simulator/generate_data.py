"""Generate immutable, deterministic synthetic banking batches and manifests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from faker import Faker

ENTITIES = ("customers", "accounts", "merchants", "transactions", "account_snapshots")
NAMESPACE = uuid.UUID("1f233963-33e4-4f7d-bf3d-70913d33d54f")


def stable_id(prefix: str, index: int) -> str:
    return f"{prefix}-{uuid.uuid5(NAMESPACE, f'{prefix}:{index}')!s}"


def build_rows(business_date: date, *, seed: int, scenario: str) -> dict[str, list[dict]]:
    random.seed(seed)
    fake = Faker("en_IN")
    fake.seed_instance(seed)
    customers = [{
        "customer_id": stable_id("CUS", index),
        "name": fake.name(),
        "age": 25 + index,
        "gender": "Female" if index % 2 else "Male",
        "city": fake.city(),
        "state": fake.state(),
        "email": f"customer{index}@example.test",
        "phone": f"+91900000{index:04d}",
        "kyc_status": "Verified" if index != 9 else "Pending",
        "customer_since": (business_date - timedelta(days=500 + index)).isoformat(),
    } for index in range(10)]

    accounts = []
    snapshots = []
    for index, customer in enumerate(customers):
        account_id = stable_id("ACC", index)
        accounts.append({
            "account_id": account_id,
            "customer_id": customer["customer_id"],
            "account_type": "Savings" if index % 2 == 0 else "Current",
            "currency": "INR",
            "branch_code": f"BR{index:03d}",
            "ifsc_code": f"BANK0{index:06d}",
            "opened_date": (business_date - timedelta(days=400 + index)).isoformat(),
            "status": "Active",
        })
        snapshots.append({
            "account_id": account_id,
            "business_date": business_date.isoformat(),
            "balance": str(Decimal("10000.00") + Decimal(index * 100)),
            "currency": "INR",
        })

    categories = ["Retail", "Travel", "Utilities", "Healthcare", "Education"]
    merchants = [{
        "merchant_id": stable_id("MER", index),
        "merchant_name": f"{fake.company()} {index}",
        "category": categories[index],
        "city": fake.city(),
        "state": fake.state(),
        "registered_since": (business_date - timedelta(days=800 + index)).isoformat(),
        "status": "Active",
    } for index in range(5)]

    if scenario == "next_day":
        customers[0]["city"] = "Bengaluru"
        accounts[1]["status"] = "Frozen"
        merchants[2]["category"] = "Digital Services"

    transactions = []
    ist = timezone(timedelta(hours=5, minutes=30))
    for index in range(20):
        account_id = accounts[index % len(accounts)]["account_id"]
        if scenario == "late_dimension" and index == 0:
            account_id = stable_id("ACC-LATE", 0)
        event = datetime.combine(
            business_date, time(hour=9 + index % 10, minute=index % 60), tzinfo=ist
        )
        transactions.append({
            "transaction_id": stable_id(f"TXN-{business_date.isoformat()}", index),
            "account_id": account_id,
            "merchant_id": merchants[index % len(merchants)]["merchant_id"],
            "transaction_ts": event.isoformat(),
            "amount": str(Decimal("100.00") + Decimal(index * 11)),
            "currency": "INR",
            "channel": ["ATM", "Mobile App", "Internet Banking", "Branch"][index % 4],
            "transaction_type": "Debit" if index % 3 else "Credit",
            "status": "Success" if index % 5 else "Pending",
            "ip_address": f"192.0.2.{index + 1}",
            "country_code": "IN",
        })
    if scenario == "invalid":
        transactions[1]["transaction_id"] = transactions[0]["transaction_id"]
        transactions[2]["amount"] = "-10.00"
    return {
        "customers": customers,
        "accounts": accounts,
        "merchants": merchants,
        "transactions": transactions,
        "account_snapshots": snapshots,
    }


def _write_csv(path: Path, rows: list[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_batch(
    output_root: Path,
    *,
    business_date: date,
    batch_id: str,
    seed: int = 42,
    scenario: str = "initial",
) -> Path:
    rows_by_entity = build_rows(business_date, seed=seed, scenario=scenario)
    relative_root = Path(
        f"raw/business_date={business_date.isoformat()}/batch_id={batch_id}"
    )
    batch_root = output_root / relative_root
    expected = {}
    for entity in ENTITIES:
        path = batch_root / f"{entity}.csv"
        expected[entity] = {
            "object_path": (relative_root / path.name).as_posix(),
            "expected_row_count": len(rows_by_entity[entity]),
            "sha256": _write_csv(path, rows_by_entity[entity]),
        }
    manifest = {
        "manifest_version": 1,
        "batch_id": batch_id,
        "business_date": business_date.isoformat(),
        "scenario": scenario,
        "expected_entities": expected,
        "source_created_at": datetime.combine(
            business_date,
            time(hour=1),
            tzinfo=timezone(timedelta(hours=5, minutes=30)),
        ).isoformat(),
    }
    manifest_path = batch_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("data/generated"))
    parser.add_argument("--business-date", type=date.fromisoformat, default=date(2026, 1, 1))
    parser.add_argument("--batch-id", default="batch-20260101-v1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--scenario",
        choices=("initial", "next_day", "late_dimension", "invalid"),
        default="initial",
    )
    args = parser.parse_args()
    print(generate_batch(
        args.output_root,
        business_date=args.business_date,
        batch_id=args.batch_id,
        seed=args.seed,
        scenario=args.scenario,
    ).as_posix())


if __name__ == "__main__":
    main()

