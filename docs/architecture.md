# Architecture

## Status

Stage 2 passive probe candidate. Versioned contracts and passive
OS/CPU/RAM/disk/GPU collection are implemented. Rule, active-test, benchmark,
API, and functional dashboard features remain future boundaries.

## Component boundaries

```text
Web UI (loopback only)
        |
Local API (read-only by default)
        |
Probe | Readiness | Benchmark | PoUI simulator
        |
Schemas | Profiles | Redaction | Reports | Receipts
        |
Optional external signer / future official testnet adapter
```

- `src/flopbench`: Python CLI and domain core.
- `apps/api`: future FastAPI composition root; it must bind only to loopback.
- `apps/web`: local React dashboard; it receives no private signing material.
- `schemas`, `profiles`, and `fixtures`: versioned contracts and deterministic test data added from Stage 1 onward.
- `tests`: unit, contract, integration, security, and E2E suites.

## Trust boundaries

- Passive local inspection is separate from user-approved active tests.
- External endpoints and network destinations are untrusted input.
- Provider output, model names, report contents, and imported fixtures are untrusted data.
- DID private keys remain outside the web application, API process, logs, reports, and command-line arguments.
- A future official testnet adapter remains optional and isolated from probe, benchmark, and report generation.

## Architectural decisions

Decisions are recorded in `docs/adr`. An accepted ADR is changed by a superseding ADR rather than silent edits.
