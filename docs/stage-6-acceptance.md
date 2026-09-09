# Stage 6 acceptance record

- Date: 2026-09-09
- Stage gate: passed; the user supplied visual confirmation of the offline report
- Release: `v0.5.0`
- Candidate implementation commit: `a080a555da34525c7cdf95da492bab2e9f009060`
- Platform: Windows, NVIDIA GeForce RTX 5060, driver 610.88

## Delivered scope

- strict private, support, and public disclosure profiles;
- RFC 8785/JCS canonical JSON and SHA-256 document digest;
- provenance with source tool, exporter, canonicalizer, privacy policy, and profile binding;
- standalone, script-free, external-resource-free HTML and terminal summary output;
- bounded structural report diff;
- benchmark comparison gated by exact profile, workload, model, adapter, unit, and confidence;
- public file writes bound to an exact digest from a prior explicit preview;
- bounded strict input parsing, symbolic-link refusal, and non-overwriting output.

The digest detects changes. It is not a signature and does not prove identity,
hardware ownership, FLOP eligibility, or rewards.

## Automated gate

Commands:

```powershell
.\.venv\Scripts\python.exe -m nox -s unit contract security lint typecheck build
pnpm --filter @flopbench/web lint
pnpm --filter @flopbench/web typecheck
pnpm --filter @flopbench/web test
pnpm --filter @flopbench/web build
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

- Unit: 177 passed; combined line/branch coverage 87.00%.
- Contract: 68 passed, including the named `S6-T01` through `S6-T08` tests.
- Security: 68 passed; 100% line/branch coverage across 260 statements and
  86 branches in the critical privacy, endpoint, transport, response-limit, and
  Stage 6 redaction modules.
- Ruff and strict mypy: passed.
- Python wheel and sdist: built; dependency consistency passed.
- Web shell: ESLint, TypeScript, 2 tests, and Vite production build passed.
- Remote CI: both `ubuntu-latest` and `windows-latest` jobs passed for the
  candidate implementation in
  [run 34157050506](https://github.com/nycrypto/flopbench/actions/runs/34157050506).

An initial full-gate attempt exposed two issues before acceptance: stale Nox
temporary-directory ownership on Windows and an unbounded list-removal branch in
report diff. Each invocation now uses a unique test directory, diff writes are
bounded in every branch, and the entire gate was rerun successfully.

## Manual acceptance

A fresh live probe was collected on the local Windows/RTX 5060 machine. A public
HTML preview was produced and writing without its exact preview digest was
rejected. Writing with the displayed digest succeeded. Five non-empty live
hostname, user, OS-version, disk-path/device, and GPU bus/serial identifier
values were checked against the HTML; zero matches were found.

The generated file was opened directly from a `file:///` URL without a server.
On 2026-09-09 the user supplied a screenshot confirming that its title,
unofficial warning, public privacy level, JCS digest, and payload rendered in the
browser. This completes `S6-T07`; the file needs no network or external asset.

Local evidence remains under Git-ignored `.acceptance/stage6/`. It is not part
of the release. The HTML report is intentionally a restrained technical export,
not the Stage 7 dashboard or project website. Stage 7 visual work remains gated
on the user's theme selection.
