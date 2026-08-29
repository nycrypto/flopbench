# ADR 0003: Local-first security boundary

- Status: Accepted
- Date: 2026-08-29

## Decision

The v1 web/API service binds only to loopback. Passive probing performs no network requests. Active tests require an explicit user action, show their destination and resource impact, and use bounded execution. Signing keys are never accepted by the browser or API.

External services and the future official testnet integration are adapters, not core dependencies. The public demo remains out of scope for v1.
