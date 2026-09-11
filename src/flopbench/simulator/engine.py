"""Deterministic agent/miner/validator scenarios with mock-only accounting."""

from __future__ import annotations

from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from .machine import SessionMachine
from .models import (
    Actor,
    ChallengeReason,
    ChallengeResult,
    ComputeEstimate,
    MockAmount,
    SessionState,
    SimulatedModel,
    SimulationAccounting,
    SimulationActors,
    SimulationResult,
    SimulationScenario,
    SimulationSessionRequest,
)

EXPECTED_MODEL_DIGEST = sha256(b"flopbench-poui-fixture-model-v1").hexdigest()
REQUESTED_FEE = 25
MOCK_STAKE = 100
MOCK_SLASH = 40


def _amount(value: int) -> MockAmount:
    return MockAmount(amount=value)


def build_session_request(
    scenario: SimulationScenario = SimulationScenario.SUCCESS,
    seed: int = 9,
) -> SimulationSessionRequest:
    """Build a stable request for a local teaching scenario."""

    session_id = uuid5(NAMESPACE_URL, f"flopbench:poui:{scenario.value}:{seed}")
    return SimulationSessionRequest(
        schema="flopbench-poui-session-request-v1",
        session_id=session_id,
        scenario=scenario,
        seed=seed,
        model=SimulatedModel(name="fixture-model", digest=EXPECTED_MODEL_DIGEST),
        max_latency_ms=500,
        compute_estimate=ComputeEstimate(amount=120),
        mock_fee=_amount(REQUESTED_FEE),
    )


def _actors() -> SimulationActors:
    return SimulationActors(
        agent=Actor(role="agent", actor_id="agent-fixture"),
        miner=Actor(role="miner", actor_id="miner-fixture"),
        validator=Actor(role="validator", actor_id="validator-fixture"),
    )


def _accounting(final_state: SessionState) -> SimulationAccounting:
    settled = final_state is SessionState.SETTLED
    rejected = final_state is SessionState.REJECTED
    slashed = MOCK_SLASH if rejected else 0
    return SimulationAccounting(
        requested_fee=_amount(REQUESTED_FEE),
        charged_fee=_amount(REQUESTED_FEE if settled else 0),
        mock_stake=_amount(MOCK_STAKE),
        mock_slashed=_amount(slashed),
        mock_refunded=_amount(MOCK_STAKE - slashed),
    )


def run_simulation(request: SimulationSessionRequest) -> SimulationResult:
    """Run one deterministic scenario without network, wallet, or token operations."""

    machine = SessionMachine(request.session_id)
    machine.transition(SessionState.OFFERED, actor="miner", code="miner.offer")
    machine.transition(SessionState.ACCEPTED, actor="agent", code="agent.accept")
    machine.transition(SessionState.RUNNING, actor="miner", code="miner.start")

    scenario = request.scenario
    challenge: ChallengeResult | None = None
    if scenario is SimulationScenario.MINER_CANCEL:
        machine.transition(SessionState.CANCELLED, actor="miner", code="miner.cancelled")
    elif scenario is SimulationScenario.TIMEOUT:
        machine.transition(
            SessionState.TIMED_OUT,
            actor="simulator",
            code="policy.execution_timeout",
            observation=f"limit={request.max_latency_ms}ms",
        )
    else:
        submitted_digest = (
            sha256(b"wrong-fixture-model").hexdigest()
            if scenario is SimulationScenario.WRONG_MODEL
            else request.model.digest
        )
        observed_latency = 750 if scenario is SimulationScenario.HIGH_LATENCY else 240
        answer_kind = "canned" if scenario is SimulationScenario.CANNED_ANSWER else "generated"
        machine.transition(
            SessionState.SUBMITTED,
            actor="miner",
            code="miner.submitted",
            observation=(
                f"model={submitted_digest};latency_ms={observed_latency};answer={answer_kind}"
            ),
        )
        machine.transition(SessionState.VALIDATING, actor="validator", code="validator.sample")

        reason: ChallengeReason | None = None
        if scenario is SimulationScenario.WRONG_MODEL:
            reason = "model_digest_mismatch"
        elif scenario is SimulationScenario.HIGH_LATENCY:
            reason = "latency_limit_exceeded"
        elif scenario is SimulationScenario.CANNED_ANSWER:
            reason = "canned_answer_detected"
        elif scenario is SimulationScenario.VALIDATOR_MISMATCH:
            reason = "validator_sample_mismatch"

        if reason is None:
            machine.transition(SessionState.SETTLED, actor="validator", code="validator.settled")
        else:
            machine.transition(
                SessionState.CHALLENGED,
                actor="validator",
                code=f"challenge.{reason}",
            )
            full_rerun = scenario is SimulationScenario.VALIDATOR_MISMATCH
            challenge = ChallengeResult(
                reason_code=reason,
                validator_action="full-rerun" if full_rerun else "sample",
                full_rerun_performed=full_rerun,
                outcome="rejected",
            )
            machine.transition(SessionState.REJECTED, actor="validator", code="challenge.rejected")

    return SimulationResult(
        schema="flopbench-poui-simulation-v1",
        request=request,
        actors=_actors(),
        events=machine.events,
        challenge=challenge,
        accounting=_accounting(machine.state),
        final_state=machine.state,
    )
