# ADR 0009: Stable release provenance

- Status: accepted
- Date: 2026-09-18

## Decision

The `v1.0.0` workflow runs only for that exact tag. It builds from locked inputs,
creates a draft GitHub release with verified artifacts, requests first-party
GitHub OIDC build-provenance attestations pinned by action commit SHA, and
publishes the draft only after attestation succeeds.

The attestation is the signed contribution/build proof. No long-lived release
signing key is stored in FlopBench or repository secrets. User report signatures
remain a separate external Ed25519 receipt workflow.

## Consequences

- An attestation failure leaves a non-public draft instead of an unattested
  public stable release.
- Consumers can bind an artifact digest to the repository, workflow, tag, and
  commit using GitHub CLI.
- Provenance does not validate benchmark truth, hardware ownership, identity,
  FLOP eligibility, or rewards.
