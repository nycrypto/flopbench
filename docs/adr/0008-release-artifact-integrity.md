# ADR 0008: Verifiable, self-contained release artifacts

- Status: Accepted
- Date: 2026-09-13

## Decision

Each release candidate contains exactly one wheel, one sdist, a CycloneDX JSON
SBOM, a deterministic runtime-license report, and `SHA256SUMS`. The checksum
manifest covers the exact artifact set and verification rejects missing, extra,
unsafe, or modified files.

The wheel embeds the built local dashboard, schemas, source profile, fixtures,
and workload data. Runtime dependencies and release tools use separate
hash-locked requirement files. Clean-install tests create a disposable venv,
exercise packaged data without repository-relative paths, uninstall the package,
and prove that user-owned reports remain byte-identical.

## Consequences

- An installed FlopBench dashboard does not require Node.js or a source checkout.
- Windows and Ubuntu execute the same clean install/removal contract in CI.
- Dependency vulnerability and secret scans are release gates.
- A checksum proves artifact integrity, not publisher identity; signed release
  attestations remain Stage 11 work.
- Release tooling refuses to overwrite an existing output directory.
