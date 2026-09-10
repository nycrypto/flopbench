# Stage 7 acceptance record

- Date: 2026-09-10
- Stage gate: passed; the user approved the tested candidate on 2026-09-10
- Release: `v0.6.0`
- Candidate implementation commit: `91f53376aa7148cebdd408c28c635058e2b01699`
- Platform: Windows, NVIDIA GeForce RTX 5060, driver 610.88

## Delivered scope

- a FastAPI service bound to literal loopback addresses only;
- startup-token, `Host`, and `Origin` checks for the local API;
- a bilingual Turkish/English React dashboard with remembered language choice;
- a light default, optional dark mode, and restrained orange visual system;
- live miner and validator readiness views with explicit fail, unknown, skipped,
  and unsupported states;
- user-initiated mock benchmark results with TTFT, throughput, latency, and a
  compact run chart;
- public-report privacy preview with excluded-field categories and digest;
- production assets served by the same local process without a public bind.

The dashboard remains an unofficial local diagnostic. It does not prove FLOP
eligibility, identity, hardware ownership, or rewards.

## Automated gate

Commands:

```powershell
.\.venv\Scripts\python.exe -m nox -s unit contract security lint typecheck build
$env:CI = 'true'
corepack pnpm install --frozen-lockfile
corepack pnpm run lint
corepack pnpm run typecheck
corepack pnpm run test
corepack pnpm run build
corepack pnpm run e2e
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

- Unit: 188 passed; combined line/branch coverage 87.24%.
- Contract: 75 passed, including the named `S7-T01` through `S7-T09` paths.
- Security: 71 passed; 100% line/branch coverage across the critical privacy,
  endpoint, transport, response-limit, and redaction modules.
- Ruff and strict mypy: passed.
- Python wheel and sdist: built; dependency consistency passed.
- Web: ESLint and TypeScript passed; 12 Vitest tests passed with 99.23%
  statement, 89.04% branch, 100% function, and 100% line coverage.
- Chromium: 5 Playwright scenarios passed, including keyboard navigation, XSS,
  refresh safety, public-preview redaction, and a basic WCAG 2.2 AA axe scan
  with zero serious or critical findings.
- Remote CI: both `ubuntu-latest` and `windows-latest` jobs passed for the
  candidate implementation in
  [run 34524609314](https://github.com/nycrypto/flopbench/actions/runs/34524609314).

The final gate exposed one repository configuration defect before acceptance:
Vitest also discovered the Playwright specification. The suites now have
explicitly separate discovery scopes, and every web gate was rerun. Headless
Chromium also required permission to start outside the workspace sandbox; once
started, all five scenarios completed in 6.0 seconds.

## Manual acceptance

The integrated server returned HTTP 200 for the dashboard and health endpoint.
The browser was exercised in Turkish and English, in light and dark modes, and
with keyboard-accessible navigation. Miner and validator views used a fresh
passive probe from the local machine.

The live NVIDIA GeForce RTX 5060 reported 8 GiB VRAM. The miner view correctly
reported that this is below the draft 16 GiB source threshold; this expected
failure is not an application error. The validator view kept unavailable disk
type and unrun network checks distinct from a failure.

The mock benchmark ran only after an explicit button press. Refreshing returned
to the overview without starting another benchmark. The public-report preview
listed device/user names, local paths, access tokens, and raw model responses as
not shared. The dashboard was returned to Turkish and light mode for review.

## Security and remaining risk

- External and hostname-based binds are rejected; v1 has no remote-bind mode.
- API mutation requires the per-process startup token and an allowed origin.
- Fixture selection is allowlisted and cannot accept an arbitrary local path.
- Adversarial model text renders as text and does not create executable markup.
- No public hosting, analytics, remote telemetry, or signing key storage was
  added.
- FastAPI's test client emits an upstream Starlette warning that its current
  `httpx` compatibility layer will move to `httpx2`. It does not affect runtime
  behavior or test results, but remains a dependency-maintenance item.
- Stage 8 signing, Stage 9 simulation, release packaging, and release work have
  not started. Stage 12 remains blocked on an official versioned testnet
  contract.

The approved candidate is ready to merge into `main` and receive the `v0.6.0`
release tag. Stage 8 remains a separate gated branch.
