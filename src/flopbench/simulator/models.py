"""Strict public contracts for the offline PoUI teaching simulation."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, Strict, field_validator

from flopbench.contracts import Sha256Hex, StrictModel

PositiveInt = Annotated[int, Strict(), Field(gt=0)]
NonNegativeInt = Annotated[int, Strict(), Field(ge=0)]
Seed = Annotated[int, Strict(), Field(ge=0, le=2_147_483_647)]
ActorRole = Literal["agent", "miner", "validator", "simulator"]
ChallengeReason = Literal[
    "model_digest_mismatch",
    "latency_limit_exceeded",
    "canned_answer_detected",
    "validator_sample_mismatch",
]
SimulationDisclaimer = Literal[
    (
        "Educational local simulation; not an official FLOP protocol, token, stake, "
        "or reward operation."
    )
]


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC")
    return value


class SessionState(StrEnum):
    CREATED = "created"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    RUNNING = "running"
    SUBMITTED = "submitted"
    VALIDATING = "validating"
    SETTLED = "settled"
    CHALLENGED = "challenged"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class SimulationScenario(StrEnum):
    SUCCESS = "success"
    WRONG_MODEL = "wrong-model"
    HIGH_LATENCY = "high-latency"
    CANNED_ANSWER = "canned-answer"
    TIMEOUT = "timeout"
    MINER_CANCEL = "miner-cancel"
    VALIDATOR_MATCH = "validator-match"
    VALIDATOR_MISMATCH = "validator-mismatch"


class SimulatedModel(StrictModel):
    simulated: Literal[True] = True
    name: str
    digest_algorithm: Literal["sha256"] = "sha256"
    digest: Sha256Hex


class ComputeEstimate(StrictModel):
    simulated: Literal[True] = True
    amount: PositiveInt
    unit: Literal["mock-compute-unit"] = "mock-compute-unit"


class MockAmount(StrictModel):
    simulated: Literal[True] = True
    amount: NonNegativeInt
    unit: Literal["mock-credit"] = "mock-credit"


class SimulationSessionRequest(StrictModel):
    schema_id: Literal["flopbench-poui-session-request-v1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    simulated: Literal[True] = True
    session_id: UUID
    scenario: SimulationScenario
    seed: Seed
    model: SimulatedModel
    max_latency_ms: PositiveInt
    compute_estimate: ComputeEstimate
    confidentiality: Literal["local-simulation"] = "local-simulation"
    mock_fee: MockAmount


class Actor(StrictModel):
    simulated: Literal[True] = True
    role: Literal["agent", "miner", "validator"]
    actor_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]+$")]


class SimulationActors(StrictModel):
    simulated: Literal[True] = True
    agent: Actor
    miner: Actor
    validator: Actor


class SessionEvent(StrictModel):
    simulated: Literal[True] = True
    index: NonNegativeInt
    event_id: UUID
    recorded_at: datetime
    actor: ActorRole
    from_state: SessionState | None
    to_state: SessionState
    code: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]+$")]
    observation: str | None = None

    _recorded_at_utc = field_validator("recorded_at")(_require_utc)


class ChallengeResult(StrictModel):
    simulated: Literal[True] = True
    reason_code: ChallengeReason
    validator_action: Literal["sample", "full-rerun"]
    full_rerun_performed: bool
    outcome: Literal["settled", "rejected"]


class SimulationAccounting(StrictModel):
    simulated: Literal[True] = True
    requested_fee: MockAmount
    charged_fee: MockAmount
    mock_stake: MockAmount
    mock_slashed: MockAmount
    mock_refunded: MockAmount


class SimulationResult(StrictModel):
    schema_id: Literal["flopbench-poui-simulation-v1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    simulated: Literal[True] = True
    official_protocol: Literal[False] = False
    disclaimer: SimulationDisclaimer = (
        "Educational local simulation; not an official FLOP protocol, token, stake, "
        "or reward operation."
    )
    request: SimulationSessionRequest
    actors: SimulationActors
    events: Annotated[list[SessionEvent], Field(min_length=2)]
    challenge: ChallengeResult | None
    accounting: SimulationAccounting
    final_state: SessionState
