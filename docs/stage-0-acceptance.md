# Stage 0 retrospective acceptance record

- Audit date: 2026-09-19
- Gate: passed after retrospective corrections
- Audited stable baseline: `v1.0.0`
- Local platform: Windows, Python 3.14.6, Node.js 24.17.0, pnpm 11.19.0

## Scope and evidence

- The public Git repository, Apache-2.0 license, English/Turkish README files,
  security, contribution, conduct, changelog, architecture, limitations, and
  immutable normative charter are present.
- Python and web toolchains are pinned. Python requirements are hash-locked and
  pnpm uses a committed frozen lockfile.
- Nox, Make, and PowerShell expose lint, typecheck, contract/integration, test,
  documentation, build, install, audit, and release tasks without stale
  placeholder behavior.
- GitHub Actions runs the quality suite on Windows and Ubuntu. Official actions
  use commit SHA references. Dependabot and a high-severity dependency-review
  gate are configured.
- ADRs record toolchain, identity/license, local-first boundaries, versioning,
  dashboard design, signing, simulation, artifact integrity, and stable release
  provenance decisions.
- The normative `flopbench künye.md` byte digest remains
  `09291f685413fe0329dd6f7f237b1e91e040f49060cfebe9821f0ef77d55a725`.

## Stage tests

- `S0-T01`: pinned Python installation contract and locked dependencies.
- `S0-T02`: pinned Node/pnpm installation contract and frozen lockfile.
- `S0-T03`: Ruff lint gate wired through Nox, Make, PowerShell, and CI.
- `S0-T04`: strict mypy gate wired through Nox, Make, PowerShell, and CI.
- `S0-T05`: unit/contract/security smoke suite runs on Windows and Ubuntu.
- `S0-T06`: license, mandatory documents, dependency policy, disclaimers, and
  normative-charter integrity.

## Corrections made during this audit

- Updated architecture and limitations wording from pre-release candidate state
  to the published `v1.0.0` state.
- Replaced the obsolete `test-integration` placeholder with the contract suite,
  which contains the cross-component API and lifecycle integration checks.
- Added explicit `S0-T01` through `S0-T06` traceability tests.

No product data collection, network default, schema, or public API behavior was
changed by these corrections.
