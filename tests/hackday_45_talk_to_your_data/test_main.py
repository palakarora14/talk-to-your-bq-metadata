from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

# Stub out client.bq and its transitive dependency src.config.constants
# before importing main, since that legacy module requires PYTHONPATH=.
_mock_bq_module = MagicMock()
_mock_config_module = MagicMock()

with (
    patch.dict(
        "sys.modules",
        {
            "client": MagicMock(),
            "client.bq": _mock_bq_module,
            "src": MagicMock(),
            "src.config": MagicMock(),
            "src.config.constants": _mock_config_module,
        },
    ),
):
    from hackday_45_talk_to_your_data.main import app  # noqa: E402

runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_bigquery_client() -> Any:
    mock_client = MagicMock()
    mock_client.fetch_bq_asset_catalog_metadata.return_value = [{"asset": "test_asset"}]
    with patch("hackday_45_talk_to_your_data.main.BigQueryClient", return_value=mock_client):
        yield mock_client


def test_app_with_required_arg() -> None:
    result = runner.invoke(app, ["main", "hello"])
    assert result.exit_code == 0


def test_app_with_required_and_optional_args() -> None:
    result = runner.invoke(app, ["main", "hello", "--optional-arg", "world"])
    assert result.exit_code == 0


def test_app_missing_required_arg() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code != 0
