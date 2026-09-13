# Stage 10 acceptance record

- Date: 2026-09-13
- Stage gate: passed; user approved on 2026-09-13
- Candidate implementation commit: `09456e275d1bf42fba7efcbbb0b4592ddea5147b`
- Approved distribution version: `0.9.0rc1`; tool/release tag: `0.9.0-rc.1`
- Local platform: Windows, Python 3.14.6, Node.js 24.17.0, pnpm 11.19.0

## Delivered scope

- wheel and sdist builds with the dashboard, profile, schemas, fixtures, and
  workload embedded as package data;
- clean disposable-venv install/removal verification on Windows and Ubuntu;
- byte-for-byte preservation of user-owned reports after uninstall;
- separate hash-locked runtime, development, and release-tool dependencies;
- CycloneDX JSON SBOM generation and strict dependency vulnerability auditing;
- deterministic runtime-license compatibility report covering all 27 locked
  dependencies;
- exact-set SHA-256 manifests that reject missing, extra, malformed, symlinked,
  oversized, or modified artifacts;
- reviewed secret baseline with new-candidate rejection in CI;
- strict, bounded `flopbench-config-v1` parsing and `flopbench serve --config`;
- unchanged loading of existing `flopbench-benchmark-report-v1` reports;
- offline probe/report verification and a bounded simulation performance budget;
- bilingual Windows/Ubuntu installation and removal documentation;
- a SHA-pinned GitHub Actions release-candidate artifact job.

## Automated gate

Principal commands:

```powershell
.\.venv\Scripts\python.exe -m nox -s unit contract security lint typecheck build install
.\.venv\Scripts\python.exe -m nox -s audit
$env:CI = 'true'
corepack pnpm install --frozen-lockfile
corepack pnpm --filter @flopbench/web lint
corepack pnpm --filter @flopbench/web typecheck
corepack pnpm --filter @flopbench/web test
corepack pnpm --filter @flopbench/web build
corepack pnpm --filter @flopbench/web e2e
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

- Unit/integration: 274 passed, 1 platform-permission skip; combined line/branch
  coverage 89.20%.
- Contract: 113 passed, 1 platform-permission skip, including `S10-T04` through
  `S10-T09`. `S10-T01`, `S10-T02`, and `S10-T03` are exercised by the clean
  installation script on the applicable CI operating system.
- Security: 162 passed, 1 platform-permission skip; 100% line and branch
  coverage across all designated critical modules, including configuration and
  release integrity.
- Ruff formatting/lint: passed across 90 files. Strict mypy: passed across 89
  source files.
- Python wheel/sdist and packaged-dashboard digest checks: passed.
- Windows clean install/removal: `S10-T01/S10-T03` passed locally and remotely.
- Ubuntu clean install/removal: `S10-T02/S10-T03` passed remotely.
- Dependency audit: no known vulnerabilities. Secret scan: no unreviewed
  candidates. License policy: 27/27 compatible runtime dependencies.
- Web: 15 Vitest tests passed with 99.31% statements, 88.62% branches, 100%
  functions, and 100% lines; 7 Chromium E2E/WCAG scenarios passed.
- Dependency consistency and whitespace checks: passed.

Remote CI run
[34774366500](https://github.com/nycrypto/flopbench/actions/runs/34774366500)
completed successfully for all three jobs:

- `Quality (ubuntu-latest)`;
- `Quality (windows-latest)`;
- `Release candidate integrity`.

The verified `flopbench-release-candidate` artifact was published as artifact
`10322433983` (553,052 bytes), with retention through 2026-09-27.

## Manual acceptance

The final local wheel was built from the candidate source, installed with all
27 runtime dependencies into a new disposable virtual environment, and executed
without repository-relative data paths. The installed CLI reported the candidate
version, loaded the embedded CPU-only fixture and source profile, wrote a valid
private probe and private report export, then uninstalled. Both user report files
remained byte-identical and the package was no longer importable.

The release pipeline produced exactly one wheel, one sdist, one CycloneDX SBOM,
one license report, and `SHA256SUMS`. Verification passed, then a synthetic wheel
modification was rejected by the checksum tests. A socket-denied test proved
that fixture probing and report export perform no network call. Five hundred
deterministic success simulations completed inside the three-second regression
budget.

The local Codex sandbox did not automatically terminate Playwright's child
preview process after its test worker completed. Stopping only that exact test
server PID returned `7 passed` and exit code 0. This was environment-specific:
both clean GitHub Windows and Ubuntu runners completed the identical E2E command
and automatic teardown successfully.

## Security, privacy, and remaining risk

- Release finalization rejects an SBOM containing any known vulnerability or a
  missing/mismatched locked runtime version.
- Checksum verification rejects directory symlinks, artifact symlinks, nested
  entries, unexpected files, malformed manifests, and tampering. A checksum
  proves integrity, not publisher identity; signed release attestations remain
  Stage 11 work.
- The secret baseline contains only public test vectors, deterministic digests,
  and synthetic negative-test traps. Candidate values are not reproduced in the
  review document, and every new hashed candidate fails CI.
- Installed commands retain the local-only loopback boundary. Probe/report
  acceptance is offline, and uninstall never targets user report directories.
- The Windows host did not permit creation of a real test symlink, so one
  platform-specific case was skipped locally. The fail-closed branch remained
  covered by a deterministic test, and the real symlink case ran on Ubuntu CI.
- FastAPI's test client still emits the recorded upstream Starlette `httpx2`
  migration warning; it does not affect these results.
- The GitHub artifact has a 14-day CI retention period. Stage 11 will create the
  durable signed GitHub release only after Stage 10 approval and RC versioning.
- Stage 11 has not started. Stage 12 remains blocked until a public, versioned
  official testnet contract exists.

The Stage 10 candidate passed its gate and the user approved this acceptance
record on 2026-09-13. Version finalization, merge, and tagging may proceed before
Stage 11 starts.
