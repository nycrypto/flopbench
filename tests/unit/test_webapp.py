"""Focused edge cases for the Stage 7 local web app."""

from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from flopbench.cli import app as cli_app
from flopbench.webapp import create_app


def test_missing_static_build_has_clear_response() -> None:
    client = TestClient(
        create_app(token="test-token", static_dir=Path("missing-web-dist")),
        base_url="http://127.0.0.1:4173",
    )
    assert client.get("/").status_code == 503


def test_origin_port_must_match_dashboard_port() -> None:
    client = TestClient(
        create_app(token="test-token", static_dir=None),
        base_url="http://127.0.0.1:4173",
    )
    response = client.get(
        "/api/v1/profiles",
        headers={
            "X-FlopBench-Token": "test-token",
            "Origin": "http://127.0.0.1:9999",
        },
    )
    assert response.status_code == 403


def test_malformed_host_is_rejected() -> None:
    client = TestClient(
        create_app(token="test-token", static_dir=None),
        base_url="http://127.0.0.1:4173",
    )
    response = client.get("/", headers={"Host": "[::1"})
    assert response.status_code == 400


def test_cli_rejects_remote_bind_before_starting_server() -> None:
    result = CliRunner().invoke(cli_app, ["serve", "--host", "0.0.0.0"])
    assert result.exit_code == 2
    assert "remote binding is not supported" in result.output
