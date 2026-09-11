"""Finite-state machine with an event for every transition."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from .errors import SimulationError
from .models import ActorRole, SessionEvent, SessionState

ALLOWED_TRANSITIONS: dict[SessionState, frozenset[SessionState]] = {
    SessionState.CREATED: frozenset({SessionState.OFFERED, SessionState.CANCELLED}),
    SessionState.OFFERED: frozenset(
        {
            SessionState.ACCEPTED,
            SessionState.REJECTED,
            SessionState.TIMED_OUT,
            SessionState.CANCELLED,
        }
    ),
    SessionState.ACCEPTED: frozenset(
        {SessionState.RUNNING, SessionState.CANCELLED, SessionState.TIMED_OUT}
    ),
    SessionState.RUNNING: frozenset(
        {SessionState.SUBMITTED, SessionState.CANCELLED, SessionState.TIMED_OUT}
    ),
    SessionState.SUBMITTED: frozenset({SessionState.VALIDATING, SessionState.CHALLENGED}),
    SessionState.VALIDATING: frozenset(
        {SessionState.SETTLED, SessionState.CHALLENGED, SessionState.TIMED_OUT}
    ),
    SessionState.CHALLENGED: frozenset(
        {SessionState.SETTLED, SessionState.REJECTED, SessionState.TIMED_OUT}
    ),
    SessionState.SETTLED: frozenset(),
    SessionState.REJECTED: frozenset(),
    SessionState.TIMED_OUT: frozenset(),
    SessionState.CANCELLED: frozenset(),
}


class SessionMachine:
    """A deterministic state machine; it performs no I/O."""

    def __init__(self, session_id: UUID) -> None:
        self.session_id = session_id
        self.state = SessionState.CREATED
        self.events = [
            self._event(
                actor="agent",
                from_state=None,
                to_state=SessionState.CREATED,
                code="session.created",
            )
        ]

    def _event(
        self,
        *,
        actor: ActorRole,
        from_state: SessionState | None,
        to_state: SessionState,
        code: str,
        observation: str | None = None,
    ) -> SessionEvent:
        index = len(getattr(self, "events", []))
        event_id = uuid5(
            NAMESPACE_URL,
            f"flopbench:poui:{self.session_id}:{index}:{from_state}:{to_state}:{code}",
        )
        return SessionEvent(
            index=index,
            event_id=event_id,
            recorded_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(milliseconds=index),
            actor=actor,
            from_state=from_state,
            to_state=to_state,
            code=code,
            observation=observation,
        )

    def transition(
        self,
        to_state: SessionState,
        *,
        actor: ActorRole,
        code: str,
        observation: str | None = None,
    ) -> SessionEvent:
        if to_state not in ALLOWED_TRANSITIONS[self.state]:
            raise SimulationError(
                "simulation.invalid_transition",
                f"transition {self.state.value} -> {to_state.value} is not allowed",
            )
        previous = self.state
        self.state = to_state
        event = self._event(
            actor=actor,
            from_state=previous,
            to_state=to_state,
            code=code,
            observation=observation,
        )
        self.events.append(event)
        return event
