# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
"""
Test script to verify the datacat-metastore-bigquery-reader-dev-roleset
has the required BigQuery permissions for Phase 1 extraction.

Run via: auto/run-local
"""

import os
import sys

from google.cloud import bigquery
from loguru import logger


def get_client(project: str) -> bigquery.Client:
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        logger.info(f"Using credentials from {creds_path}")
    else:
        logger.info("GOOGLE_APPLICATION_CREDENTIALS not set — using Application Default Credentials")
    return bigquery.Client(project=project)


def test_list_datasets(client: bigquery.Client, project: str) -> bool:
    logger.info("--- Test 1: List datasets ---")
    try:
        datasets = list(client.list_datasets(project=project))
        logger.success(f"OK — found {len(datasets)} dataset(s) in {project}")
        for ds in datasets[:5]:
            logger.info(f"  {ds.dataset_id}")
        return True
    except Exception as e:
        logger.error(f"FAIL — {e}")
        return False


def test_information_schema_tables(client: bigquery.Client, project: str) -> bool:
    logger.info("--- Test 2: INFORMATION_SCHEMA.TABLES (first dataset) ---")
    try:
        datasets = list(client.list_datasets(project=project))
        if not datasets:
            logger.warning("No datasets found — skipping table schema test")
            return True
        dataset_id = datasets[0].dataset_id
        query = f"""
            SELECT table_name, table_type, creation_time
            FROM `{project}.{dataset_id}.INFORMATION_SCHEMA.TABLES`
            LIMIT 5
        """
        rows = list(client.query(query).result())
        logger.success(f"OK — queried INFORMATION_SCHEMA.TABLES in {project}.{dataset_id}, {len(rows)} row(s)")
        for row in rows:
            logger.info(f"  {row.table_name} ({row.table_type})")
        return True
    except Exception as e:
        logger.error(f"FAIL — {e}")
        return False


def test_information_schema_columns(client: bigquery.Client, project: str) -> bool:
    logger.info("--- Test 3: INFORMATION_SCHEMA.COLUMNS (first dataset) ---")
    try:
        datasets = list(client.list_datasets(project=project))
        if not datasets:
            logger.warning("No datasets found — skipping column schema test")
            return True
        dataset_id = datasets[0].dataset_id
        query = f"""
            SELECT table_name, column_name, data_type
            FROM `{project}.{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
            LIMIT 5
        """
        rows = list(client.query(query).result())
        logger.success(f"OK — queried INFORMATION_SCHEMA.COLUMNS in {project}.{dataset_id}, {len(rows)} row(s)")
        for row in rows:
            logger.info(f"  {row.table_name}.{row.column_name} {row.data_type}")
        return True
    except Exception as e:
        logger.error(f"FAIL — {e}")
        return False


def test_jobs_by_project(client: bigquery.Client, project: str) -> bool:
    logger.info("--- Test 4: INFORMATION_SCHEMA.JOBS_BY_PROJECT ---")
    try:
        query = f"""
            SELECT job_id, user_email, total_bytes_billed, total_slot_ms, creation_time
            FROM `{project}.region-australia-southeast1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
            WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
            ORDER BY creation_time DESC
            LIMIT 5
        """
        rows = list(client.query(query).result())
        logger.success(f"OK — queried JOBS_BY_PROJECT, {len(rows)} recent job(s)")
        for row in rows:
            logger.info(f"  {row.job_id} by {row.user_email}, billed={row.total_bytes_billed} bytes")
        return True
    except Exception as e:
        logger.error(f"FAIL — {e}")
        return False


def main() -> None:
    project = os.environ.get("GCP_PROJECT", "rea-gcp-dp-dev")
    logger.info(f"Testing roleset permissions against project: {project}")

    client = get_client(project)

    results = {
        "list_datasets": test_list_datasets(client, project),
        "information_schema_tables": test_information_schema_tables(client, project),
        "information_schema_columns": test_information_schema_columns(client, project),
        "jobs_by_project": test_jobs_by_project(client, project),
    }

    logger.info("\n=== Summary ===")
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {status}  {name}")
        if not passed:
            all_passed = False

    if not all_passed:
        logger.error("Some tests failed — check roleset permissions above")
        sys.exit(1)
    logger.success("All permission tests passed!")


if __name__ == "__main__":
    main()
