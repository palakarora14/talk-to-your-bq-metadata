import time
from datetime import datetime
from zoneinfo import ZoneInfo

import typer
from dotenv import load_dotenv
from loguru import logger

from client.bq import BigQueryClient
from hackday_45_talk_to_your_data.library import env, log
from hackday_45_talk_to_your_data.library.serializer import ingest_project

app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def main(required_arg: str, optional_arg: str | None = None) -> None:
    loaded = load_dotenv()
    log.configure()
    if not loaded:
        logger.debug("No .env file loaded. Copy `.env_template` to `.env` to set defaults.")

    run_id = f"{datetime.now(ZoneInfo('Australia/Sydney')).strftime('%Y%m%d-%H%M%S')}"
    t0 = time.perf_counter()

    logger.info(f"Hello! {required_arg=}, {optional_arg=}")
    logger.debug(f"LOG_STDERR_LEVEL={env.get('LOG_STDERR_LEVEL', 'INFO')}")
    logger.debug(f"LOG_FILE_LEVEL={env.get('LOG_FILE_LEVEL', 'DEBUG')}")

    bq_client = BigQueryClient()
    result = bq_client.fetch_bq_asset_catalog_metadata()
    took = time.perf_counter() - t0
    logger.info(f"Fetched {len(result)} rows of asset metadata.")
    logger.info(f"Run {run_id} finished in {took:.2f} seconds.")


@app.command()
def ingest(days: int = 7) -> None:
    loaded = load_dotenv()
    log.configure()
    if not loaded:
        logger.debug("No .env file loaded. Copy `.env_template` to `.env` to set defaults.")

    t0 = time.perf_counter()
    summary = ingest_project(days=days)
    took = time.perf_counter() - t0

    logger.info(f"Ingestion finished in {took:.2f} seconds: {summary}")


if __name__ == "__main__":
    app()
