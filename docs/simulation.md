# PoUI teaching simulation

FlopBench Stage 9 models an inference session as a deterministic, local teaching
exercise. It is not an implementation of an official FLOP protocol. It makes no
network, wallet, testnet, token, stake, reward, or real slashing operation.

## Run a scenario

```powershell
flopbench simulate run --scenario success --seed 9
flopbench simulate run --scenario validator-mismatch --seed 9 --output simulation.json
```

Available scenarios are `success`, `wrong-model`, `high-latency`,
`canned-answer`, `timeout`, `miner-cancel`, `validator-match`, and
`validator-mismatch`. The same validated request and seed produce the same
canonical event log byte for byte.

## Lifecycle

The normal path is:

```text
created -> offered -> accepted -> running -> submitted -> validating -> settled
```

Policy and validation paths may terminate as `challenged`, `rejected`,
`timed_out`, or `cancelled`. Every creation and transition creates a stable event
with an actor, previous state, next state, code, deterministic identifier, and
UTC simulation timestamp. Invalid transitions are rejected.

The agent creates and accepts the request, the miner offers and submits a mock
inference result, and the validator samples it. A validator mismatch explicitly
performs a mock full re-run. Wrong-model, high-latency, and canned-answer paths
open challenges before rejection.

## Simulation boundary

Every object in a simulation output contains `"simulated": true`. Accounting is
denominated only in `mock-credit`; compute is expressed only in
`mock-compute-unit`. These values are educational counters and are never FLOP,
fiat, token, stake, reward, eligibility, or economic estimates.

The local dashboard provides the same scenarios as a compact event timeline.
It always displays the unofficial simulation notice before a run starts.
