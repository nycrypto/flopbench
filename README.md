# FlopBench

> Local-first readiness, benchmarking and proof-of-inference workbench for future FLOP miners, validators and AI agents.

FlopBench is an **independent, community-built project** inspired by the public FLOP Network draft. It is not an official FLOP Labs or Flop Foundation product, miner, validator client, eligibility checker, claim tool, or guarantee of rewards.

## Project status

FlopBench has completed Stage 2 (`v0.1.0`). Strict data contracts and passive local OS/CPU/RAM/disk/GPU inspection are available; readiness rule evaluation, benchmarking, report signing, and PoUI simulation are not implemented yet.

The normative project charter is [`flopbench künye.md`](./flopbench%20k%C3%BCnye.md). Public FLOP parameters are provisional and will be stored in versioned source profiles rather than embedded throughout the code.

## Requirements

- Python 3.14.6
- Node.js 24.17.0
- pnpm 11.19.0
- Git

Docker and GNU Make are optional. Every quality task is available through Python/Nox, pnpm, and PowerShell.

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements/dev.txt
pnpm install --frozen-lockfile
```

On Linux, replace `.venv\Scripts\python` with `.venv/bin/python`.

## Local dashboard

The dashboard is still a local-only foundation shell; the functional dashboard is scheduled for Stage 7. Build and open the current shell at `http://127.0.0.1:4173`:

```powershell
pnpm --filter @flopbench/web build
pnpm --filter @flopbench/web preview
```

The preview server binds only to loopback; it is not reachable from the public internet or other devices on the network.

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
