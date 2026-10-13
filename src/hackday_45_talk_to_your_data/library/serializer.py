from loguru import logger

from client.bq import BigQueryClient
from hackday_45_talk_to_your_data.vector_store import (
    ASSET_CATALOG,
    QUERY_HISTORY,
    QUOTA_METRICS,
    EmbeddingFunction,
    create_client,
    create_collections,
    document_from_row,
    upsert_documents,
)


def ingest_project(
    days: int = 7,
    embedding_function: EmbeddingFunction | None = None,
) -> dict[str, int]:
    bq_client = BigQueryClient()
    logger.info(f"Fetching BigQuery asset catalog metadata for project '{bq_client.project_id}'.")
    asset_rows = bq_client.fetch_bq_asset_catalog_metadata()
    logger.info(f"Fetching query history for the last {days} day(s).")
    query_job_rows = bq_client.fetch_bq_query_history(days=days)
    logger.info("Fetching quota metrics.")
    quota_metric_rows = bq_client.fetch_bq_quota_metrics()

    chroma_client = create_client()
    collections = create_collections(chroma_client, embedding_function)

    asset_count = upsert_documents(collections[ASSET_CATALOG], (document_from_row(row) for row in asset_rows))
    query_job_count = upsert_documents(collections[QUERY_HISTORY], (document_from_row(row) for row in query_job_rows))
    quota_metric_count = upsert_documents(
        collections[QUOTA_METRICS], (document_from_row(row) for row in quota_metric_rows)
    )

    logger.info(
        f"Ingested {asset_count} assets, {query_job_count} query jobs, "
        f"and {quota_metric_count} quota metrics for '{bq_client.project_id}'."
    )
    return {"assets": asset_count, "query_jobs": query_job_count, "quota_metrics": quota_metric_count}
