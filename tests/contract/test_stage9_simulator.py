"""Stage 9 deterministic PoUI simulation acceptance tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from flopbench.cli import app
from flopbench.reporting.canonical import canonical_bytes
from flopbench.simulator import SimulationScenario, build_session_request, run_simulation
from flopbench.simulator.errors import SimulationError
from flopbench.simulator.machine import SessionMachine
from flopbench.simulator.models import SessionState, SimulationResult, SimulationSessionRequest

pytestmark = pytest.mark.stage9

ROOT = Path(__file__).resolve().parents[2]
REQUEST_FIXTURE = ROOT / "fixtures" / "simulations" / "session-request-valid.json"


def _run(scenario: SimulationScenario) -> SimulationResult:
    return run_simulation(build_session_request(scenario, 9))


def test_s9_t01_normal_flow_reaches_settled() -> None:
    result = _run(SimulationScenario.SUCCESS)
    assert result.request.model.digest_algorithm == "sha256"
    assert result.request.max_latency_ms == 500
    assert result.request.compute_estimate.unit == "mock-compute-unit"
    assert result.request.confidentiality == "local-simulation"
    assert result.request.mock_fee.unit == "mock-credit"
    assert {result.actors.agent.role, result.actors.miner.role, result.actors.validator.role} == {
        "agent",
        "miner",
        "validator",
    }
    assert [event.to_state for event in result.events] == [
        SessionState.CREATED,
        SessionState.OFFERED,
        SessionState.ACCEPTED,
        SessionState.RUNNING,
        SessionState.SUBMITTED,
        SessionState.VALIDATING,
        SessionState.SETTLED,
    ]


def test_s9_t02_invalid_transition_is_rejected() -> None:
    machine = SessionMachine(build_session_request().session_id)
    with pytest.raises(SimulationError) as caught:
        machine.transition(SessionState.SETTLED, actor="validator", code="invalid.settlement")
    assert caught.value.code == "simulation.invalid_transition"


def test_s9_t03_wrong_model_digest_creates_challenge() -> None:
    result = _run(SimulationScenario.WRONG_MODEL)
    assert result.challenge is not None
    assert result.challenge.reason_code == "model_digest_mismatch"
    assert SessionState.CHALLENGED in [event.to_state for event in result.events]


def test_s9_t04_latency_limit_creates_policy_challenge() -> None:
    result = _run(SimulationScenario.HIGH_LATENCY)
    assert result.challenge is not None
    assert result.challenge.reason_code == "latency_limit_exceeded"
    assert result.final_state is SessionState.REJECTED


def test_s9_t05_miner_cancel_does_not_leave_open_session() -> None:
    result = _run(SimulationScenario.MINER_CANCEL)
    assert result.final_state is SessionState.CANCELLED
    assert result.events[-1].code == "miner.cancelled"


def test_s9_t06_matching_validator_sample_settles() -> None:
    result = _run(SimulationScenario.VALIDATOR_MATCH)
    assert result.final_state is SessionState.SETTLED
    assert result.challenge is None
    assert result.events[-2].code == "validator.sample"


def test_s9_t07_mismatch_runs_full_rerun_mock() -> None:
    result = _run(SimulationScenario.VALIDATOR_MISMATCH)
    assert result.challenge is not None
    assert result.challenge.validator_action == "full-rerun"
    assert result.challenge.full_rerun_performed is True


def test_canned_answer_and_timeout_scenarios_are_explicit() -> None:
    canned = _run(SimulationScenario.CANNED_ANSWER)
    timed_out = _run(SimulationScenario.TIMEOUT)
    assert canned.challenge is not None
    assert canned.challenge.reason_code == "canned_answer_detected"
    assert timed_out.final_state is SessionState.TIMED_OUT
    assert timed_out.events[-1].code == "policy.execution_timeout"


def _assert_all_objects_simulated(value: object) -> None:
    if isinstance(value, dict):
        assert value.get("simulated") is True
        for nested in value.values():
            _assert_all_objects_simulated(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_all_objects_simulated(nested)


def test_s9_t08_every_simulation_object_is_marked_simulated() -> None:
    data = _run(SimulationScenario.VALIDATOR_MISMATCH).model_dump(mode="json", by_alias=True)
    _assert_all_objects_simulated(data)
    assert data["official_protocol"] is False
    assert data["accounting"]["requested_fee"]["unit"] == "mock-credit"


def test_s9_t09_same_seed_and_fixture_produce_identical_event_log() -> None:
    fixture = SimulationSessionRequest.model_validate_json(REQUEST_FIXTURE.read_bytes())
    left = run_simulation(fixture)
    right = run_simulation(fixture)
    assert left.events == right.events
    assert canonical_bytes(left.model_dump(mode="json", by_alias=True)) == canonical_bytes(
        right.model_dump(mode="json", by_alias=True)
    )


def test_s9_t10_has_no_real_token_stake_or_network_code_path() -> None:
    imported_modules: set[str] = set()
    for path in sorted((ROOT / "src" / "flopbench" / "simulator").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module.split(".")[0])
    assert imported_modules.isdisjoint(
        {"requests", "httpx", "urllib", "socket", "subprocess", "web3"}
    )

    cli = CliRunner().invoke(app, ["simulate", "run", "--scenario", "success", "--seed", "9"])
    assert cli.exit_code == 0
    payload = json.loads(cli.stdout)
    assert payload["simulated"] is True
    assert payload["official_protocol"] is False
