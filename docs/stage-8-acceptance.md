# Stage 8 acceptance record

- Date: 2026-09-11
- Stage gate: passed; the user approved the tested candidate on 2026-09-11
- Release: `v0.7.0`
- Candidate implementation commit: `2b5205b1602050187e0e24dde3da19f39715a1cf`
- Platform: Windows, Python 3.14.6, Node.js 24.17.0, pnpm 11.19.0

## Delivered scope

- a domain-separated RFC 8785/JCS receipt signing payload bound to the report
  schema, canonical document SHA-256 digest, signer DID, algorithms, and local
  UTC signing declaration;
- strict `did:key` Ed25519 resolution using base58btc and the `ed25519-pub`
  multicodec prefix;
- canonical unpadded base64url Ed25519 signature verification performed fully
  offline;
- `flopbench receipt prepare`, `receipt create`, and `receipt verify` commands;
- an external-signer request contract that carries the exact signing bytes and
  their digest without handling a private key;
- bounded, regular-file-only request and receipt inputs with controlled errors;
- bilingual security documentation, a dedicated ADR, and published JSON
  Schemas;
- an RFC 8032 section 7.1 interoperability fixture.

A valid receipt proves possession of the private key corresponding to the
stated DID only. It does not prove identity, report truth, hardware ownership,
FLOP eligibility, rewards, or a trusted timestamp.

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

- Unit/integration: 210 passed; combined line/branch coverage 87.39%.
- Contract: 83 passed, including named `S8-T01` through `S8-T08` paths.
- Security: 100 passed; 100% line and branch coverage across all designated
  critical modules, including the receipt codec, models, and service.
- Ruff formatting/lint and strict mypy: passed.
- Python wheel and sdist: built; dependency consistency passed.
- Web: ESLint and TypeScript passed; 13 Vitest tests passed with 99.23%
  statement, 89.04% branch, 100% function, and 100% line coverage.
- Chromium: 6 Playwright scenarios passed, including `S8-T09` and the existing
  WCAG 2.2 AA, XSS, keyboard, and refresh checks.
- Remote CI: both `ubuntu-latest` and `windows-latest` passed for the candidate
  implementation in
  [run 34609990689](https://github.com/nycrypto/flopbench/actions/runs/34609990689).

The first clean security run exposed missing negative-path coverage rather than
a runtime defect. Tests were added for invalid metadata, unsupported report
schemas, malformed payload encodings, file read failures, and a file-growth
race; the entire security gate was rerun at 100% branch coverage. A stale schema
generation invocation and two test-only Ruff findings were also corrected, then
all gates were rerun.

## Manual acceptance

A private readiness report was exported through the real CLI. The CLI then
prepared a request for the existing RFC 8032 Test 1 DID and displayed the report
digest, signer DID, signing-payload digest, key-boundary warning, and untrusted
time warning before signing.

An acceptance-only external process signed the exact decoded request payload
using the public RFC 8032 test material. FlopBench received only the resulting
86-character public signature, verified it before writing the receipt, and then
verified the report and receipt using public data only. The final verification
returned `valid: true` with the explicit `ed25519-key-possession` proof type and
`report-claims-not-independently-verified` authenticity statement.

Running `receipt create` without a signature returned a concise cancellation
message and left no output file. The acceptance artifacts remain under the
ignored `.acceptance/stage8/manual-20260911` directory and are not committed.

## Security and remaining risk

- Production receipt code imports only Ed25519 public-key verification APIs; it
  contains no key generation, key import, private-key file, seed, PEM, or
  password interface.
- Secret-bearing CLI options are rejected without echoing their supplied value.
- Malformed base58btc, base64url, DID codecs, signatures, oversized files,
  symlinks, and report mismatches return controlled failures.
- Receipt verification is offline and performs no DID-registry or network call.
- The dashboard has no private-key file input or upload control.
- DID key rotation and revocation are outside the offline `did:key` model; users
  must retain the receipt, report, and historical key context they rely on.
- `signed_at` is signer-controlled metadata, not a trusted timestamp.
- FastAPI's test client still emits the previously recorded upstream Starlette
  `httpx2` migration warning; it does not affect these results.
- Stage 9 simulation has not started. Stage 12 remains blocked on a public,
  versioned official testnet contract.

The approved candidate is ready to merge into `main` and receive the `v0.7.0`
release tag. Stage 9 remains a separate gated branch.
