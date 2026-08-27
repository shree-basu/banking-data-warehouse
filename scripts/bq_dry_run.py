"""Authenticated BigQuery dry run that reports estimated bytes without executing SQL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from google.cloud import bigquery


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query_file", type=Path)
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", default="asia-south1")
    args = parser.parse_args()

    sql = args.query_file.read_text(encoding="utf-8").replace("{{project_id}}", args.project)
    client = bigquery.Client(project=args.project, location=args.location)
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
    )
    print(
        json.dumps(
            {
                "dry_run": True,
                "project": args.project,
                "location": args.location,
                "query_file": str(args.query_file),
                "total_bytes_processed": job.total_bytes_processed,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
