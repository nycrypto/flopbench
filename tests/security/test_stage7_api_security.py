"""Adversarial Stage 7 local API boundary checks."""

from fastapi.testclient import TestClient

from flopbench.webapp import create_app

TOKEN = "security-test-token"


def _client() -> TestClient:
    return TestClient(
        create_app(token=TOKEN, static_dir=None),
        base_url="http://127.0.0.1:4173",
    )


def test_dns_rebinding_origin_and_token_attacks_are_rejected() -> None:
    client = _client()
    rebound = client.get("/api/v1/profiles", headers={"Host": "flopbench.attacker.test"})
    assert rebound.status_code == 400
    assert (
        client.get(
            "/api/v1/profiles",
            headers={"X-FlopBench-Token": TOKEN, "Origin": "null"},
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/v1/profiles",
            headers={"X-FlopBench-Token": TOKEN, "Origin": "http://localhost:4173"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/benchmarks",
            headers={"Origin": "http://127.0.0.1:4173"},
            json={"adapter": "mock"},
        ).status_code
        == 403
    )


def test_api_rejects_unknown_fields_and_oversized_model_names() -> None:
    client = _client()
    headers = {"X-FlopBench-Token": TOKEN, "Origin": "http://127.0.0.1:4173"}
    assert (
        client.post(
            "/api/v1/checks/miner",
            headers=headers,
            json={"fixture": "live", "path": "C:/private/file.json"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/benchmarks",
            headers=headers,
            json={"adapter": "mock", "model_name": "x" * 201},
        ).status_code
        == 422
    )


def test_api_metadata_and_browser_headers_do_not_expose_token() -> None:
    client = _client()
    health = client.get("/api/v1/health")
    assert TOKEN not in health.text
    assert health.headers["cache-control"] == "no-store"
    assert health.headers["referrer-policy"] == "no-referrer"
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
