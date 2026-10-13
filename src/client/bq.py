"""
This module provides functionality to interact with Google BigQuery using the
Google Cloud client library.

The `google.cloud.bigquery` module is used for:
- Managing datasets, tables, and views
- Querying data using SQL
- Loading, exporting, and copying data
- Controlling access and setting policies
- Handling job operations such as running queries and loading data
"""

import os
from typing import Any

from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
from loguru import logger

from src.config.constants import (
    GCP_DP_DEV_PROJECT,
    GCP_DP_PROD_PROJECT,
    GCP_REGION,
)


class BigQueryClient:
    """
    A client to interact with Google BigQuery.

    This client handles the insertion of rows into a specified BigQuery table.
    """

    def __init__(self) -> None:
        """
        Initializes the BigQueryClient with project, dataset, and table information.
        """
        self.project_id = GCP_DP_PROD_PROJECT if os.environ.get("ENV") == "prod" else GCP_DP_DEV_PROJECT
        self.client = bigquery.Client(project=self.project_id)
        logger.info(f"Successfully initialized BigQuery client for {self.project_id}.")

    def execute_query(self, query: str, query_params: list[dict[str, Any]] | None = None) -> list[dict[str, Any]] | int:
        """
        Executes a SQL query against BigQuery.
        Handles both DQL (Data Query Language) and DML (Data Manipulation Language) operations.

        :param query: SQL query to execute.
        :param query_params: Optional list of parameter dictionaries.
        :return: For queries (SELECT): List of result rows as dictionaries.
                 For DML (UPDATE, INSERT, DELETE): Number of affected rows.
        """
        try:
            substituted_query = query
            if query_params:
                # Sort parameters by name length (descending) to avoid partial replacements
                # This ensures @resource_id_10 is replaced before @resource_id_1
                sorted_params = sorted(query_params, key=lambda p: len(p.get("name", "")), reverse=True)

                for param in sorted_params:
                    param_name = param.get("name", "")
                    param_value = param.get("parameterValue", {}).get("value", "")

                    # Handle None values
                    if param_value is None:
                        display_value = "NULL"
                    else:
                        # Wrap string values in quotes for readability
                        display_value = f"'{param_value}'"

                    # Use word boundary replacement to avoid partial matches
                    # Replace @param_name with the value, ensuring we match the whole parameter
                    import re

                    pattern = r"@" + re.escape(param_name) + r"\b"
                    substituted_query = re.sub(pattern, display_value, substituted_query)

            logger.debug(f"Query with substituted parameters:\n{substituted_query}")
            job_config = bigquery.QueryJobConfig()
            if query_params:
                job_config.query_parameters = [
                    bigquery.ScalarQueryParameter(
                        param["name"],
                        param["parameterType"]["type"],
                        param["parameterValue"]["value"],
                    )
                    for param in query_params
                ]

            # Execute the query
            query_job = self.client.query(query, job_config=job_config, location=GCP_REGION)

            # Wait for the query to complete
            query_job.result()

            # Determine if this is a DML operation by checking the query type
            # DML operations start with UPDATE, INSERT, DELETE, MERGE
            is_dml = any(query.strip().upper().startswith(op) for op in ["UPDATE ", "INSERT ", "DELETE ", "MERGE "])

            if is_dml:
                # For DML operations, return the number of affected rows
                num_affected = query_job.num_dml_affected_rows
                assert num_affected is not None
                logger.info(f"DML operation affected {num_affected} rows.")
                return num_affected
            else:
                # For queries, return the results as a list of dictionaries
                rows: list[dict[str, Any]] = [dict(row) for row in query_job]
                logger.info(f"Query returned {len(rows)} rows.")
                return rows

        except GoogleCloudError as e:
            logger.error(f"Google API call error: {e} in fetching rows")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error: {e} in fetching rows")
            raise e

    def fetch_bq_asset_catalog_metadata(self) -> list[dict[str, Any]]:
        """
        Fetches metadata about BigQuery assets (datasets and tables) in the project.
        """
        query = rf"""
        with
            column_details as (
                select
                    table_catalog as project_id,
                    table_schema as dataset_id,
                    table_name,

                    string_agg(
                        format(
                            'Column: %s | Type: %s | Nullable: %s | Partitioning: %s | Cluster position: %s',
                            column_name,
                            data_type,
                            is_nullable,
                            is_partitioning_column,
                            coalesce(cast(clustering_ordinal_position as string), 'N/A')
                        ),
                        '\n'
                        order by ordinal_position
                    ) as schema_text,

                    string_agg(
                        if(is_partitioning_column = 'YES', column_name, null),
                        ', '
                        order by ordinal_position
                    ) as partition_columns

                from `{self.project_id}.region-{GCP_REGION}.INFORMATION_SCHEMA.COLUMNS`
                group by project_id, dataset_id, table_name
            ),

            nested_details as (
                select
                    table_catalog as project_id,
                    table_schema as dataset_id,
                    table_name,

                    string_agg(
                        format(
                            'Field path: %s | Type: %s | Description: %s',
                            field_path,
                            data_type,
                            coalesce(description, 'No description')
                        ),
                        '\n'
                        order by field_path
                    ) as nested_schema_text

                from `{self.project_id}.region-{GCP_REGION}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`
                group by project_id, dataset_id, table_name
            )

        select
            concat(
                'asset:', t.table_catalog, '.', t.table_schema, '.', t.table_name
            ) as document_id,

            'bq_asset_catalog' as collection_name,
            'table_schema' as document_type,

            t.table_catalog as project_id,
            t.table_schema as dataset_id,
            t.table_name as table_name,
            t.table_type,
            t.creation_time,

            coalesce(c.partition_columns, 'NONE') as partition_columns,

            format(
                'BigQuery asset: %s.%s.%s\nTable type: %s\nPartition columns: %s\nSchema:\n%s\nNested schema:\n%s',
                t.table_catalog,
                t.table_schema,
                t.table_name,
                t.table_type,
                coalesce(c.partition_columns, 'NONE'),
                coalesce(c.schema_text, 'No schema found'),
                coalesce(n.nested_schema_text, 'No nested fields found')
            ) as document_text,

            current_timestamp() as extracted_at

        from `{self.project_id}.region-{GCP_REGION}.INFORMATION_SCHEMA.TABLES` as t
        left join
            column_details as c
            on t.table_catalog = c.project_id
            and t.table_schema = c.dataset_id
            and t.table_name = c.table_name
        left join
            nested_details as n
            on t.table_catalog = n.project_id
            and t.table_schema = n.dataset_id
            and t.table_name = n.table_name;
        """

        result = self.execute_query(query)
        if not isinstance(result, list):
            logger.error("fetch_bq_asset_catalog_metadata: Unexpected result type, expected list.")
            return []
        logger.info(f"Fetched {len(result)} rows of BigQuery asset catalog metadata.")
        return result

    def fetch_bq_query_history(self, days: int = 7) -> list[dict[str, Any]]:
        """
        Fetches the query history from BigQuery for the specified number of days.

        :param days: Number of days to look back for query history.
        :return: List of dictionaries containing query history metadata.
        """

        query = rf"""
        select
            concat('query:', project_id, ':', job_id) as document_id,
            'bq_query_history' as collection_name,
            'query_execution' as document_type,
            project_id,
            job_id,
            user_email,
            creation_time,
            start_time,
            end_time,
            state,
            statement_type,
            cache_hit,
            final_execution_duration_ms,

            coalesce(
                query_info.query_hashes.normalized_literals, to_hex(md5(query))
            ) as query_fingerprint,

            array_to_string(
                array(
                    select format('%s.%s.%s', ref.project_id, ref.dataset_id, ref.table_id)
                    from unnest(referenced_tables) as ref
                ),
                ', '
            ) as referenced_assets,

            timestamp_diff(
                coalesce(end_time, current_timestamp()),
                coalesce(start_time, creation_time),
                second
            ) as duration_seconds,

            total_bytes_processed,
            total_bytes_billed,
            total_slot_ms,
            query,

            format(
                concat(
                    'Query executed in project %s. Job ID: %s. State: %s. User: %s. Duration: %d seconds.',
                    '\nReferenced assets: %s. Bytes billed: %d. Slot milliseconds: %d. SQL: %s'
                ),
                project_id,
                job_id,
                state,
                user_email,
                timestamp_diff(
                    coalesce(end_time, current_timestamp()),
                    coalesce(start_time, creation_time),
                    second
                ),
                coalesce(
                    array_to_string(
                        array(
                            select
                                format('%s.%s.%s', ref.project_id, ref.dataset_id, ref.table_id)
                            from unnest(referenced_tables) as ref
                        ),
                        ', '
                    ),
                    'No referenced assets'
                ),
                coalesce(total_bytes_billed, 0),
                coalesce(total_slot_ms, 0),
                query
            ) as document_text,

            current_timestamp() as extracted_at

        from `{self.project_id}.region-{GCP_REGION}.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
        where
            creation_time >= timestamp_sub(current_timestamp(), interval {days} day)
            and job_type = 'QUERY'
            and query is not null
            and (statement_type is null or statement_type <> 'SCRIPT');
        """

        result = self.execute_query(query)
        if not isinstance(result, list):
            logger.error("fetch_bq_query_history: Unexpected result type, expected list.")
            return []
        logger.info(f"Fetched {len(result)} rows of BigQuery query history metadata.")
        return result

    def fetch_bq_quota_metrics(self) -> list[dict[str, Any]]:
        """
        Fetches quota metrics from BigQuery for the last 7 days.

        :return: List of dictionaries containing quota metrics.
        """
        query = rf"""
        with
            recent_jobs as (
                select
                    project_id,
                    job_id,
                    user_email,
                    creation_time,
                    query,

                    coalesce(
                        query_info.query_hashes.normalized_literals, to_hex(md5(query))
                    ) as query_fingerprint,

                    timestamp_diff(
                        coalesce(end_time, current_timestamp()),
                        coalesce(start_time, creation_time),
                        second
                    ) as duration_seconds,

                    coalesce(total_bytes_billed, 0) as total_bytes_billed,
                    coalesce(total_slot_ms, 0) as total_slot_ms,
                    state

                from
                    `{self.project_id}.region-{GCP_REGION}.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
                where
                    creation_time >= timestamp_sub(current_timestamp(), interval 7 day)
                    and job_type = 'QUERY'
                    and query is not null
                    and (statement_type is null or statement_type <> 'SCRIPT')
            ),

            costly_queries as (
                select *, row_number() over (order by total_bytes_billed desc) as rank
                from recent_jobs
                where state = 'DONE'
            ),

            frequent_queries as (
                select
                    project_id,
                    query_fingerprint,
                    count(*) as execution_count,
                    avg(duration_seconds) as average_duration_seconds,
                    sum(total_bytes_billed) as total_bytes_billed,
                    sum(total_slot_ms) as total_slot_ms,
                    any_value(query) as sample_query,

                    row_number() over (order by count(*) desc) as rank

                from recent_jobs
                where state = 'DONE'
                group by project_id, query_fingerprint
            ),

            long_running_queries as (
                select *, row_number() over (order by duration_seconds desc) as rank
                from recent_jobs
            ),

            project_cost as (
                select
                    project_id,
                    count(*) as query_count,
                    sum(total_bytes_billed) as total_bytes_billed,
                    sum(total_slot_ms) as total_slot_ms,

                    row_number() over (order by sum(total_bytes_billed) desc) as rank

                from recent_jobs
                where state = 'DONE'
                group by project_id
            ),

            active_projects as (
                select
                    project_id,
                    countif(state = 'RUNNING') as running_queries,
                    countif(state = 'PENDING') as pending_queries,
                    count(*) as active_queries,

                    row_number() over (order by count(*) desc) as rank

                from
                    `{self.project_id}.region-{GCP_REGION}.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
                where
                    creation_time >= timestamp_sub(current_timestamp(), interval 7 day)
                    and job_type = 'QUERY'
                    and state in ('RUNNING', 'PENDING')
                group by project_id
            )

        select
            'quota:top-costly-queries-7d' as document_id,
            'bq_quota_metrics' as collection_name,
            'top_costly_queries_7d' as metric_type,
            current_timestamp() as metric_time,

            string_agg(
                format(
                    concat(
                        'Rank %d | Project: %s | Job: %s | User: %s | Duration: %d seconds',
                        ' | Bytes billed: %d | Slot milliseconds: %d | SQL: %s'
                    ),
                    rank,
                    project_id,
                    job_id,
                    user_email,
                    duration_seconds,
                    total_bytes_billed,
                    total_slot_ms,
                    query
                ),
                '\n'
                order by rank
            ) as document_text,

            current_timestamp() as extracted_at

        from costly_queries
        where rank <= 10

        union all

        select
            'quota:most-frequent-queries-7d',
            'bq_quota_metrics',
            'most_frequent_queries_7d',
            current_timestamp(),

            string_agg(
                format(
                    concat(
                        'Rank %d | Project: %s | Executions: %d | Average duration: %.2f seconds',
                        ' | Bytes billed: %d | Slot milliseconds: %d',
                        ' | Query fingerprint: %s | Sample SQL: %s'
                    ),
                    rank,
                    project_id,
                    execution_count,
                    average_duration_seconds,
                    total_bytes_billed,
                    total_slot_ms,
                    query_fingerprint,
                    sample_query
                ),
                '\n'
                order by rank
            ),

            current_timestamp()

        from frequent_queries
        where rank <= 20

        union all

        select
            'quota:long-running-queries-7d',
            'bq_quota_metrics',
            'long_running_queries_7d',
            current_timestamp(),

            string_agg(
                format(
                    'Rank %d | Project: %s | Job: %s | State: %s | Duration: %d seconds | Bytes billed: %d | SQL: %s',
                    rank,
                    project_id,
                    job_id,
                    state,
                    duration_seconds,
                    total_bytes_billed,
                    query
                ),
                '\n'
                order by rank
            ),

            current_timestamp()

        from long_running_queries
        where rank <= 20

        union all

        select
            'quota:project-query-cost-7d',
            'bq_quota_metrics',
            'project_query_cost_7d',
            current_timestamp(),

            string_agg(
                format(
                    'Rank %d | Project: %s | Query count: %d | Total bytes billed: %d | Total slot milliseconds: %d',
                    rank,
                    project_id,
                    query_count,
                    total_bytes_billed,
                    total_slot_ms
                ),
                '\n'
                order by rank
            ),

            current_timestamp()

        from project_cost

        union all

        select
            'quota:active-queries-by-project',
            'bq_quota_metrics',
            'active_queries_by_project',
            current_timestamp(),

            string_agg(
                format(
                    'Rank %d | Project: %s | Running queries: %d | Pending queries: %d | Active queries: %d',
                    rank,
                    project_id,
                    running_queries,
                    pending_queries,
                    active_queries
                ),
                '\n'
                order by rank
            ),

            current_timestamp()

        from active_projects;
        """

        result = self.execute_query(query)
        if not isinstance(result, list):
            logger.error("fetch_bq_quota_metrics: Unexpected result type, expected list.")
            return []
        logger.info(f"Fetched {len(result)} rows of BigQuery quota metrics.")
        return result


class BigQueryClientError(Exception):
    pass
