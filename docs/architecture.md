# Architecture

## Status

Stage 7 local dashboard is complete. Versioned contracts, passive hardware collection,
explainable readiness rules, consent-gated bounded health tests,
provider-independent inference benchmarking, privacy-aware exports, and
compatibility-gated comparison are implemented. A startup-token-protected
loopback API and bilingual functional dashboard now compose these capabilities.
Signing and PoUI simulation remain future boundaries.

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
- `src/flopbench/readiness`: pure profile-versus-probe rules and output formatting.
- `src/flopbench/validator_doctor`: approval-gated active tests and bounded adapters.
- `src/flopbench/reporting`: typed redaction, JCS digests, offline renderers, diff, and comparison.
- `src/flopbench/webapp.py`: FastAPI composition root with literal-loopback,
  Host, Origin, startup-token, and browser security-header controls.
- `apps/web`: bilingual local React dashboard; it receives no private signing material.
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
