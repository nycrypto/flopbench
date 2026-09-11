# ADR 0007: Deterministic PoUI teaching state machine

- Status: Accepted
- Date: 2026-09-12

## Decision

FlopBench represents the proposed inference lifecycle as a pure deterministic
finite-state machine. A validated request and integer seed determine identifiers,
timestamps, scenario observations, the event log, challenge result, and mock
accounting. The simulator performs no I/O.

Every output object is explicitly marked `simulated: true`. Economic-looking
values use the non-financial `mock-credit` unit, and compute uses
`mock-compute-unit`. The output also states that it is not an official protocol.

## Consequences

- Every allowed state transition has a stable event and every invalid transition
  fails with a controlled error.
- Agent, miner, and validator roles are pedagogical actors, not network clients.
- The same fixture and seed are reproducible across CLI, API, and dashboard.
- Future official adapters cannot reuse this module as a hidden network path;
  they require a separate boundary and a new decision record.
