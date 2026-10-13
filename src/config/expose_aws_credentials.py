import os
from typing import Protocol, cast

import boto3  # pyright: ignore[reportMissingTypeStubs]
from loguru import logger


class FrozenCredentials(Protocol):
    access_key: str | None
    secret_key: str | None
    token: str | None


class Credentials(Protocol):
    def get_frozen_credentials(self) -> FrozenCredentials: ...


def set_credentials() -> None:
    """
    In AWS environments, credentials are not explicitly exported as env vars. Typically that info is taken
    from an internal endpoint in EC2 instances and that is what Google SDK typically uses.
    In case of AWS fargate, the credentials and endpoints are different
    and Google SDK struggles to find the credentials from AWS ECS Fargate containers metadata.

    Feature requst from 2023: https://github.com/googleapis/google-auth-library-nodejs/issues/1594

    Instead of relying on Google SDK to read the instance metadata, this function is a workaround by explicitly
    exporting AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN as env variables so the SDK can work.
    """

    # Get the relative URI for the container credentials

    session = boto3.Session()
    cred_instance = cast(Credentials | None, session.get_credentials())

    if cred_instance is None:
        logger.warning("No AWS credentials found. Skipping credential setup.")
        return

    creds = cred_instance.get_frozen_credentials()

    if not creds.access_key or not creds.secret_key or not creds.token:
        logger.warning("Incomplete AWS credentials found. Skipping credential setup.")
        return

    os.environ["AWS_ACCESS_KEY_ID"] = creds.access_key
    os.environ["AWS_SECRET_ACCESS_KEY"] = creds.secret_key
    os.environ["AWS_SESSION_TOKEN"] = creds.token
    logger.info("Successfully set AWS credentials as environment variables.")
