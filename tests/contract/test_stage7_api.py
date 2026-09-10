"""Stage 7 local API contract and security acceptance tests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from flopbench.webapp import create_app, validate_bind_host

pytestmark = pytest.mark.stage7

TOKEN = "stage7-test-token"
BASE_URL = "http://127.0.0.1:4173"


def _client(tmp_path: Path) -> TestClient:
    static = tmp_path / "dist"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text(
        '<meta name="flopbench-token" content="__FLOPBENCH_TOKEN__">',
        encoding="utf-8",
    )
    (static / "assets" / "app.js").write_text("export {};", encoding="utf-8")
    return TestClient(create_app(token=TOKEN, static_dir=static), base_url=BASE_URL)


def _headers(*, origin: str = BASE_URL) -> dict[str, str]:
    return {"X-FlopBench-Token": TOKEN, "Origin": origin}


def test_s7_t01_and_t02_only_literal_loopback_bind_is_supported() -> None:
    assert validate_bind_host("127.0.0.1") == "127.0.0.1"
    assert validate_bind_host("::1") == "::1"
    with pytest.raises(ValueError, match="remote binding"):
        validate_bind_host("0.0.0.0")
    with pytest.raises(ValueError, match="literal loopback"):
        validate_bind_host("localhost")


def test_host_origin_token_and_security_headers(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.get("/api/v1/health").json()["scope"] == "loopback"
    assert client.get("/api/v1/profiles").status_code == 403
    assert client.get("/api/v1/profiles", headers={"X-FlopBench-Token": "wrong"}).status_code == 403
    rejected_origin = client.get(
        "/api/v1/profiles", headers=_headers(origin="https://attacker.example")
    )
    assert rejected_origin.status_code == 403

    response = client.get("/api/v1/profiles", headers=_headers())
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]

    rebound = client.get("/", headers={"Host": "attacker.example"})
    assert rebound.status_code == 400
    assert rebound.json() == {"code": "api.host_rejected"}


def test_dashboard_injects_token_without_api_disclosure(tmp_path: Path) -> None:
    client = _client(tmp_path)
    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert TOKEN in dashboard.text
    assert "__FLOPBENCH_TOKEN__" not in dashboard.text
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/missing.js").status_code == 404


def test_s7_t03_miner_fixture_and_s7_t05_draft_profile(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/api/v1/checks/miner",
        headers=_headers(),
        json={"fixture": "miner"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["probe"]["gpu"]["devices"][0]["name"]
    assert data["readiness"]["role"] == "miner"
    assert data["readiness"]["profile"]["source_status"] == "draft"
    assert data["readiness"]["summary"].keys() == {
        "pass",
        "warn",
        "fail",
        "unknown",
        "skipped",
        "unsupported",
    }


def test_s7_t04_cpu_only_and_unsupported_are_explicit(tmp_path: Path) -> None:
    client = _client(tmp_path)
    cpu_only = client.post(
        "/api/v1/checks/miner", headers=_headers(), json={"fixture": "cpu-only"}
    ).json()
    unsupported = client.post(
        "/api/v1/checks/miner", headers=_headers(), json={"fixture": "unsupported"}
    ).json()
    assert cpu_only["probe"]["gpu"]["status"] == "no-supported-gpu"
    assert cpu_only["readiness"]["checks"][0]["status"] == "fail"
    assert unsupported["probe"]["gpu"]["status"] == "unsupported"
    assert unsupported["readiness"]["checks"][0]["status"] == "unsupported"


def test_s7_t06_model_name_is_data_and_s7_t09_get_does_not_restart(tmp_path: Path) -> None:
    client = _client(tmp_path)
    malicious = '<img src=x onerror="window.__xss=1">'
    created = client.post(
        "/api/v1/benchmarks",
        headers=_headers(),
        json={"adapter": "mock", "model_name": malicious},
    )
    assert created.status_code == 201
    assert created.json()["model"]["name"] == malicious

    first_list = client.get("/api/v1/benchmarks", headers=_headers()).json()["benchmarks"]
    second_list = client.get("/api/v1/benchmarks", headers=_headers()).json()["benchmarks"]
    assert len(first_list) == len(second_list) == 1
    benchmark_id = created.json()["benchmark_id"]
    assert client.get(f"/api/v1/benchmarks/{benchmark_id}", headers=_headers()).status_code == 200
    assert client.get("/api/v1/benchmarks/missing", headers=_headers()).status_code == 404


def test_s7_t08_public_report_preview_lists_redactions(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/api/v1/reports/preview",
        headers=_headers(),
        json={"privacy": "public"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["export"]["document"]["privacy_level"] == "public"
    assert data["export"]["document"]["provenance"]["source_jcs_sha256"] is None
    assert "host identifiers" in data["redacted_fields"]
    assert len(data["export"]["digest"]["value"]) == 64
