# FlopBench

> Local-first readiness, benchmarking and proof-of-inference workbench for future FLOP miners, validators and AI agents.

FlopBench is an **independent, community-built project** inspired by the public FLOP Network draft. It is not an official FLOP Labs or Flop Foundation product, miner, validator client, eligibility checker, claim tool, or guarantee of rewards.

## Project status

FlopBench is in Stage 0 (`v0.0.1` development): repository foundations and quality gates. Hardware probing, readiness checks, benchmarking, report signing, and PoUI simulation are not implemented yet.

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

The Stage 0 dashboard is local-only. Build and open it at `http://127.0.0.1:4173`:

```powershell
pnpm --filter @flopbench/web build
pnpm --filter @flopbench/web preview
```

The preview server binds only to loopback; it is not reachable from the public internet or other devices on the network.

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
