from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from flopbench.simulator import SimulationScenario, build_session_request, run_simulation
from flopbench.simulator.errors import SimulationError
from flopbench.simulator.machine import ALLOWED_TRANSITIONS, SessionMachine
from flopbench.simulator.models import SessionEvent, SessionState

SESSION_ID = UUID("54a0d26c-22ff-5501-a2bb-491a366c8a06")


def test_initial_event_is_deterministic_and_explicitly_simulated() -> None:
    left = SessionMachine(SESSION_ID)
    right = SessionMachine(SESSION_ID)
    assert left.events == right.events
    assert left.events[0].from_state is None
    assert left.events[0].to_state is SessionState.CREATED
    assert left.events[0].simulated is True


@pytest.mark.parametrize(
    ("source", "target"),
    [(source, target) for source, targets in ALLOWED_TRANSITIONS.items() for target in targets],
)
def test_every_allowed_transition_records_an_event(
    source: SessionState, target: SessionState
) -> None:
    machine = SessionMachine(SESSION_ID)
    machine.state = source
    event = machine.transition(target, actor="simulator", code="test.transition")
    assert event.from_state is source
    assert event.to_state is target
    assert machine.state is target
    assert machine.events[-1] == event


@pytest.mark.parametrize(
    "terminal",
    [
        SessionState.SETTLED,
        SessionState.REJECTED,
        SessionState.TIMED_OUT,
        SessionState.CANCELLED,
    ],
)
def test_terminal_states_reject_further_transitions(terminal: SessionState) -> None:
    machine = SessionMachine(SESSION_ID)
    machine.state = terminal
    with pytest.raises(SimulationError) as caught:
        machine.transition(SessionState.OFFERED, actor="simulator", code="test.invalid")
    assert caught.value.code == "simulation.invalid_transition"


@pytest.mark.parametrize("scenario", list(SimulationScenario))
def test_every_scenario_finishes_and_accounting_balances(scenario: SimulationScenario) -> None:
    result = run_simulation(build_session_request(scenario, 17))
    assert result.final_state in {
        SessionState.SETTLED,
        SessionState.REJECTED,
        SessionState.TIMED_OUT,
        SessionState.CANCELLED,
    }
    accounting = result.accounting
    assert accounting.mock_refunded.amount + accounting.mock_slashed.amount == 100
    assert result.events[-1].to_state is result.final_state


def test_event_timestamp_requires_utc() -> None:
    aware = datetime(2026, 1, 1, tzinfo=UTC)
    data = SessionMachine(SESSION_ID).events[0].model_dump()
    data["recorded_at"] = aware.replace(tzinfo=None)
    with pytest.raises(ValidationError, match="UTC"):
        SessionEvent.model_validate(data)
