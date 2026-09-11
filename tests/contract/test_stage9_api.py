"""Stage 9 local simulation API contract tests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from flopbench.webapp import create_app

pytestmark = pytest.mark.stage9

TOKEN = "stage9-test-token"
BASE_URL = "http://127.0.0.1:4173"


def _client(tmp_path: Path) -> TestClient:
    static = tmp_path / "dist"
    static.mkdir()
    (static / "index.html").write_text(
        '<meta name="flopbench-token" content="__FLOPBENCH_TOKEN__">', encoding="utf-8"
    )
    return TestClient(create_app(token=TOKEN, static_dir=static), base_url=BASE_URL)


def _headers() -> dict[str, str]:
    return {"X-FlopBench-Token": TOKEN, "Origin": BASE_URL}


def test_simulation_create_list_and_detail_are_deterministic(tmp_path: Path) -> None:
    client = _client(tmp_path)
    payload = {"scenario": "validator-mismatch", "seed": 42}
    first = client.post("/api/v1/simulations", headers=_headers(), json=payload)
    second = client.post("/api/v1/simulations", headers=_headers(), json=payload)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert first.json()["challenge"]["validator_action"] == "full-rerun"

    session_id = first.json()["request"]["session_id"]
    listed = client.get("/api/v1/simulations", headers=_headers()).json()["simulations"]
    assert listed == [first.json()]
    assert (
        client.get(f"/api/v1/simulations/{session_id}", headers=_headers()).json() == first.json()
    )
    assert client.get("/api/v1/simulations/missing", headers=_headers()).status_code == 404


def test_simulation_api_rejects_unknown_fields_and_bad_seed(tmp_path: Path) -> None:
    client = _client(tmp_path)
    unknown = client.post(
        "/api/v1/simulations",
        headers=_headers(),
        json={"scenario": "success", "seed": 9, "wallet": "forbidden"},
    )
    bad_seed = client.post(
        "/api/v1/simulations",
        headers=_headers(),
        json={"scenario": "success", "seed": -1},
    )
    assert unknown.status_code == 422
    assert bad_seed.status_code == 422
