# FlopBench

> Local-first readiness, benchmarking and proof-of-inference workbench for future FLOP miners, validators and AI agents.

FlopBench is an **independent, community-built project** inspired by the public FLOP Network draft. It is not an official FLOP Labs or Flop Foundation product, miner, validator client, eligibility checker, claim tool, or guarantee of rewards.

## Project status

FlopBench has completed Stage 7 (`v0.6.0`) and has a Stage 8 externally signed DID receipt candidate under acceptance. Strict data contracts, passive hardware inspection, explainable readiness checks, consent-gated bounded health tests, inference benchmarks, privacy-aware reports, and a secured bilingual local dashboard are available. PoUI simulation is not implemented yet. See the [dashboard documentation](./docs/dashboard.md), [receipt security model](./docs/receipt-security.md), and [Stage 7 acceptance record](./docs/stage-7-acceptance.md).

The normative project charter is [`flopbench künye.md`](./flopbench%20k%C3%BCnye.md). Public FLOP parameters are provisional and will be stored in versioned source profiles rather than embedded throughout the code.

## Requirements

- Python 3.14.6
- Node.js 24.17.0
- pnpm 11.19.0
- Git

Docker and GNU Make are optional. Every quality task is available through Python/Nox, pnpm, and PowerShell.

Benchmark behavior, metric definitions, and endpoint safety rules are documented in [`docs/benchmarks.md`](./docs/benchmarks.md).

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements/dev.txt
pnpm install --frozen-lockfile
```

On Linux, replace `.venv\Scripts\python` with `.venv/bin/python`.

## Local dashboard

Build the dashboard and start its integrated local API at `http://127.0.0.1:4173`:

```powershell
pnpm --filter @flopbench/web build
flopbench serve
```

The service accepts literal loopback addresses only; it is not reachable from the public internet or other devices on the network. The UI supports English and Turkish, uses the browser language on first visit, and saves explicit language/theme preferences locally.

## Passive hardware probe

Run a private local probe or a redacted public probe without network access:

```powershell
flopbench probe --format json --privacy private
flopbench probe --format json --privacy public
flopbench probe --fixture fixtures/hardware/cpu-only.json --format json
```

Public output removes hostnames, user names, IP addresses, local paths, OS build
strings, GPU serial numbers, and PCI bus identifiers. See
[`docs/privacy.md`](./docs/privacy.md).

## Readiness checks

Evaluate live hardware or a deterministic fixture against the versioned source
profile:

```powershell
flopbench check miner
flopbench check validator
flopbench check miner --fixture fixtures/hardware/linux-nvidia-16gb.json --format json
```

Source-profile decisions and FlopBench community health checks are kept in
separate fields and terminal sections. Every decision has a stable reason code;
`unknown` and `unsupported` are not converted to hardware failures. The bundled
profile is visibly marked `draft`. See [`docs/readiness.md`](./docs/readiness.md).

## Active validator health tests

Review the displayed disk limit, network target, and transmitted data, then
approve the plan interactively or with an explicit flag:

```powershell
flopbench doctor validator
flopbench doctor validator --approve --disk-bytes 1048576 --format json
flopbench doctor validator --network-target 127.0.0.1:443 --ntp-server 127.0.0.1
```

No network or clock test runs unless its target is explicitly supplied. Disk
files live only in an isolated temporary directory and are removed after
success, failure, timeout, or cancellation. See
[`docs/active-tests.md`](./docs/active-tests.md).

## Externally signed receipts

Prepare exact JCS bytes for an existing Ed25519 DID, sign them with a tool that
runs outside FlopBench, then assemble and verify the receipt:

```powershell
flopbench receipt prepare report.json --did did:key:z6Mk... --output request.json
flopbench receipt create request.json --signature BASE64URL_SIGNATURE --output receipt.json
flopbench receipt verify report.json receipt.json
```

FlopBench never accepts a private key, seed, PEM, key file, or password. A valid
receipt proves possession of the DID key only. See the
[receipt security model](./docs/receipt-security.md).

## Quality gates

```powershell
.\scripts\tasks.ps1 lint
.\scripts\tasks.ps1 typecheck
.\scripts\tasks.ps1 test-unit
.\scripts\tasks.ps1 test-contract
.\scripts\tasks.ps1 test-web
.\scripts\tasks.ps1 test-all
.\scripts\tasks.ps1 build
```

Equivalent `make lint`, `make typecheck`, `make test-all`, and `make build` aliases are provided where Make is available.

## Privacy and network defaults

FlopBench is local-first. Future probe and report commands will not send system data over the network by default. Private keys, wallet seeds, hostnames, user names, IP/MAC addresses, serial numbers, and local paths are protected data and will never be part of a public report by default.

## License

Licensed under the Apache License 2.0. See [LICENSE](./LICENSE).
