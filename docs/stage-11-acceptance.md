# Stage 11 acceptance record

- Date: 2026-09-18
- Stage gate: candidate passed; user approval and publication pending
- Candidate implementation commit: `9f6a009f8bbc0e7d628c442b279b36ebcb981442`
- Candidate distribution and intended tag: `1.0.0` / `v1.0.0`
- Local platform: Windows, Python 3.14.6, Node.js 24.17.0, pnpm 11.19.0

## Delivered scope

- stable `1.0.0` package metadata and a bilingual release-ready project status;
- deterministic fixture-only public examples for miner, validator, benchmark,
  report, receipt-adjacent provenance, and PoUI simulation review;
- an offline public HTML example and a Playwright-recorded fixture-only dashboard
  demonstration;
- bilingual installation guidance plus security, privacy, methodology,
  limitations, roadmap, demo, and release-attestation documentation;
- byte-stable example generation and verification, local Markdown link checks,
  expanded clean-install acceptance, and Stage 11 contract coverage;
- an exact-tag `v1.0.0` release workflow that validates the tag and main-branch
  ancestry, rebuilds locked artifacts, creates a draft release, obtains GitHub
  OIDC build-provenance attestations, and publishes only after attestation;
- SHA-pinned official GitHub Actions and a two-person stable-release checklist.

The original `flopbench künye.md` remains unchanged. The dashboard remains
local-only and is not hosted as a public demo.

## Automated gate

Principal commands:

```powershell
.\.venv\Scripts\python.exe -m nox -s unit contract security lint typecheck docs build install
.\.venv\Scripts\python.exe -m nox -s audit
$env:CI = 'true'
corepack pnpm install --frozen-lockfile
corepack pnpm --filter @flopbench/web lint
corepack pnpm --filter @flopbench/web typecheck
corepack pnpm --filter @flopbench/web test
corepack pnpm --filter @flopbench/web build
corepack pnpm --filter @flopbench/web e2e
.\.venv\Scripts\python.exe scripts/generate_examples.py --check
.\.venv\Scripts\python.exe scripts/check_links.py
git diff --check
```

- Unit/integration: 288 passed, 1 Windows symlink-permission skip; combined
  general line/branch coverage 89.20%.
- Contract: 127 passed, 1 Windows symlink-permission skip, including 14 Stage 11
  release, documentation, example, demo, and workflow checks (`S11-T01` through
  `S11-T09`).
- Security: 162 passed, 1 Windows symlink-permission skip; 100% line and branch
  coverage across all designated critical modules.
- Ruff formatting/lint: passed across 95 files. Strict mypy: passed across 94
  source files.
- Documentation: 51 Markdown files had valid local links; all 7 generated
  examples reproduced byte-for-byte.
- Web: 15 Vitest tests passed with 99.31% statements, 88.62% branches, and 100%
  functions/lines; 7 Chromium E2E and baseline WCAG 2.2 AA scenarios passed.
- Python wheel/sdist, embedded dashboard, SBOM, licenses, exact-set checksums,
  dependency audit, secret scan, and clean installation/removal: passed.
- Expanded installed-product flow passed for probe, miner and validator checks,
  validator doctor, mock benchmark, public report export, external receipt
  signing/assembly/verification, two PoUI scenarios, loopback dashboard health,
  uninstall, and byte-identical preservation of user-owned reports.
- Dependency audit found no known vulnerabilities; the reviewed secret scan
  found no unreviewed candidates.

Remote CI run
[35368394361](https://github.com/nycrypto/flopbench/actions/runs/35368394361)
completed successfully for all three jobs:

- `Quality (windows-latest)`;
- `Quality (ubuntu-latest)`;
- `Release candidate integrity`.

The verified `flopbench-release-candidate` artifact is artifact `10557517819`
(979,414 bytes), digest
`sha256:da67d663f6f8e49e16c882dd2d9984bd15e93829ee30ecfccd74fbae40e7b4eb`,
with retention through 2026-10-02.

## Manual acceptance

The candidate wheel was installed into a fresh disposable virtual environment
and exercised without repository-relative package data. The installed CLI
completed the primary user journeys listed above. The dashboard was started on
literal loopback, its health response was checked, and its process was always
terminated. Package removal left user-owned output byte-identical and made the
package no longer importable.

The fixture-only dashboard demonstration was recorded from the real React
interface and checked as a valid WebM file. The public examples contain
synthetic hardware and deterministic fixture data only. English and Turkish
navigation, light/dark preference behavior, concise readiness messaging, and
the orange visual system remain covered by the Stage 7 dashboard tests.

The release-candidate pipeline produced exactly one wheel, one sdist, one
CycloneDX SBOM, one license report, and `SHA256SUMS`, then verified their exact
set and hashes. The tag workflow itself is intentionally not triggered until
the user completes the second-person gate.

## Security, privacy, and remaining risk

- No private key enters a FlopBench process. The installed receipt acceptance
  used an external subprocess and the public RFC 8032 test vector.
- Public examples and demo media use fixtures. Public-report redaction and all
  designated critical security paths retain 100% branch coverage.
- Release publication is fail-closed: it remains a draft until GitHub's OIDC
  artifact attestation succeeds. That attestation proves build provenance, not
  benchmark truth, hardware identity, FLOP eligibility, or rewards.
- The Windows host could not create a real test symlink, so one local case was
  skipped. Its fail-closed branch is covered deterministically and the real
  filesystem case passed on Ubuntu CI.
- FastAPI's test client retains the documented upstream Starlette `httpx2`
  migration warning; it did not affect acceptance.
- In the local Codex environment, Playwright's preview child occasionally
  required termination by its exact PID after all 7 tests passed. Clean GitHub
  Windows and Ubuntu runners completed the same E2E command and teardown.
- No `v1.0.0` tag, stable GitHub release, or release attestation exists yet.
  These are deliberately withheld until the user reviews this record and
  explicitly approves publication.
- Stage 12 remains blocked until a public, versioned official testnet contract
  is available and separately reviewed.

The implementer side of the two-person checklist is complete. The user side is
pending; therefore the branch must not be merged, tagged, or published yet.
