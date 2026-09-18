# FlopBench roadmap

This roadmap records intent, not eligibility, token, reward, testnet, or release
promises. FlopBench remains an independent community project.

## v1.0 — local workbench

- Stable offline-first CLI and loopback-only bilingual dashboard.
- Passive probe, source-profile readiness, opt-in validator health tests, and
  deterministic mock or user-approved local inference benchmarks.
- Redacted JCS reports, external Ed25519 receipt verification, and the explicitly
  simulated PoUI teaching flow.
- Reproducible Windows/Ubuntu packages with checksums, SBOM, license inventory,
  secret/dependency audits, and GitHub build-provenance attestations.

## Next maintenance work

- Correctness, accessibility, security, privacy, and documentation fixes for v1.
- Additional versioned inference workloads without changing existing report
  contracts.
- Optional GPU provider adapters that preserve CPU-only operation and fail closed.
- Report schema additions only through a new schema ID and compatibility guide.

## Blocked: official testnet adapter

Stage 12 cannot begin until FLOP publishes a public, versioned official testnet
contract. Any future adapter must be optional, isolated, consent-gated, and must
not reinterpret community readiness results as official eligibility. No endpoint,
wallet, claim, reward, or transaction behavior is being inferred in advance.

Please use the repository's issue templates for proposals and include relevant
stage/test identifiers where applicable.
