# ADR 0001: Language and toolchain

- Status: Accepted
- Date: 2026-08-29

## Decision

Use Python 3.14.6 for the CLI/core/API and Node.js 24.17.0 with pnpm 11.19.0 for the React/TypeScript dashboard. CI and tool-version files pin those exact versions; package metadata accepts newer Node 24 security patches. Use Hatchling for Python builds, Nox for cross-platform quality sessions, Ruff for Python lint/format checks, mypy for strict type checks, pytest for Python tests, and Vitest for web tests.

GNU Make is an optional alias layer. Windows users have an equivalent PowerShell task runner.

## Consequences

Dependencies and CI versions must be locked. Python support is `>=3.14,<3.15`; widening this range requires a new compatibility decision and CI coverage.
