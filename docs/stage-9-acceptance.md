# Stage 9 acceptance record

- Date: 2026-09-12
- Stage gate: passed; awaiting explicit user approval to merge
- Base release: `v0.7.0`
- Candidate implementation commit: `73b4c17fb0ef7752776586adfa97caf2edc78102`
- Platform: Windows, Python 3.14.6, Node.js 24.17.0, pnpm 11.19.0

## Delivered scope

- strict PoUI session-request and simulation-result contracts with published
  JSON Schemas;
- deterministic agent, miner, and validator actors plus a finite state machine
  covering all allowed lifecycle transitions;
- success, wrong-model, high-latency, canned-answer, timeout, miner-cancel,
  validator-match, and validator-mismatch scenarios;
- validator sampling, challenge records, and an explicit full re-run mock for
  mismatches;
- deterministic event identifiers, UTC timestamps, ordering, and canonical CLI
  output for a fixed scenario and seed;
- mock-only fee and slashing accounting, with `simulated: true` carried by every
  simulation output object and `official_protocol: false` on the result;
- `flopbench simulate run` and secured loopback `/api/v1/simulations` resources;
- a bilingual, light-first dashboard view with an orange event timeline, concise
  status text, dark-theme support, and no automatic simulation on navigation or
  refresh;
- bilingual usage and boundary documentation plus a dedicated architecture
  decision record.

The simulator is an educational local model. It neither implements nor claims
an official FLOP protocol, and it has no real token, stake, reward, transfer, or
network call path.

## Automated gate

Commands:

```powershell
.\.venv\Scripts\python.exe -m nox -s unit contract security lint typecheck build
$env:CI = 'true'
corepack pnpm install --frozen-lockfile
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
corepack pnpm e2e
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

- Unit/integration: 257 passed; combined line/branch coverage 88.09%.
- Contract: 96 passed, including named `S9-T01` through `S9-T10` paths.
- Security: 145 passed; 100% line and branch coverage across every designated
  critical module, including the complete simulator package.
- Every allowed state-machine edge and invalid terminal transition is covered.
- Ruff formatting/lint and strict mypy: passed across 84 files and 83 source
  files respectively.
- Python wheel and sdist: built; dependency consistency passed.
- Web: ESLint and TypeScript passed; 15 Vitest tests passed with 99.31%
  statement, 88.62% branch, 100% function, and 100% line coverage.
- Chromium: 7 Playwright scenarios passed, including the PoUI flow, explicit
  user-start boundary, refresh safety, XSS checks, keyboard flow, and WCAG 2.2
  AA scans with no serious or critical findings.
- Remote CI: both `ubuntu-latest` and `windows-latest` passed for the candidate
  implementation in
  [run 34653675536](https://github.com/nycrypto/flopbench/actions/runs/34653675536).

During the gate, Ruff found one overlong Nox marker expression, pnpm required
its documented CI mode for non-interactive dependency validation, and the new
Playwright scenario exposed an ambiguous text locator. Each test-infrastructure
issue was corrected, and the affected full gates were rerun successfully.

## Manual acceptance

The real CLI wrote the success scenario twice with scenario `success` and seed
`9`. Both files had the same SHA-256 digest:
`8d521353113f6df9570f6b28e456b3c607b4120edd115a2d0aba2254e1b1d812`.

The real CLI validator-mismatch scenario ended in `rejected`, recorded eight
events, created the `validator_sample_mismatch` challenge, and reported that the
mock full re-run occurred. The result had `simulated: true`,
`official_protocol: false`, and `mock-credit` for requested, charged, and mock
slashed values.

The current package was then installed into the project virtual environment and
served at `127.0.0.1:4173`. The health endpoint returned HTTP 200 with `ok` and
`loopback`; the dashboard returned HTTP 200. A token- and Origin-protected real
POST to `/api/v1/simulations` returned the same eight-event rejected mismatch
flow without disclosing the process-local startup token. Acceptance artifacts
remain in the ignored `.acceptance/stage9` directory and are not committed.

## Security and remaining risk

- Production simulator modules contain no HTTP client, socket, subprocess,
  blockchain SDK, token transfer, or real stake operation.
- The local API retains the startup-token, Origin, strict-body, response-size,
  and loopback-only boundaries established in Stage 7.
- The UI does not start a simulation on navigation or refresh; every run
  requires an explicit button action.
- Event timestamps are deterministic teaching data, not trusted wall-clock
  evidence.
- Mock fees and slashing illustrate state changes only and must not be used as
  financial or eligibility evidence.
- FastAPI's test client still emits the previously recorded upstream Starlette
  `httpx2` migration warning; it does not affect these results.
- Stage 10 packaging and release-candidate work has not started.
- Stage 12 remains blocked until a public, versioned official testnet contract
  exists.

The candidate is ready for user review. It must not be merged into `main` or
tagged as `v0.8.0` until that approval is received.
