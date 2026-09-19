# Stage 4 retrospective acceptance record

- Audit date: 2026-09-19
- Gate: passed
- Live targets: loopback only (`127.0.0.1`)

## Stage tests

- `S4-T01`: the fast-disk fixture reports exact bytes, decimal throughput, and
  nearest-rank p95 latency.
- `S4-T02`: the slow-disk fixture returns `warn` with the stable low-margin
  reason code.
- `S4-T03`: an unavailable temporary parent returns controlled `unsupported`.
- `S4-T04`: rejecting the consent prompt starts no test and creates no file.
- `S4-T05`: cooperative interruption removes the isolated file and directory
  before returning `skipped`.
- `S4-T06`: a fully offline network adapter returns `unknown` with 100% loss
  and does not crash.
- `S4-T07`: the high-jitter fixture uses nearest-rank p95 and returns `warn`.
- `S4-T08`: an unreachable NTP source returns `unknown` and no offset value.

Additional tests cover resource-limit validation, invalid network targets,
impossible counters, symlink rejection, safe fixture errors, exact status
boundaries, deterministic JSON, and the visible consent description.

## Live acceptance

A user-approved live doctor run exercised the bounded 8 MiB disk test and used
loopback-only network and clock targets. The disk test completed with `pass` and
reported exactly `8,388,608` tested bytes. The closed TCP target and unavailable
loopback NTP source both correctly returned `unknown`; neither produced a false
success. The temporary directory was removed by the service.

The command displayed the disk limit, exact TCP target, absence of application
payload, exact NTP server, and 48-byte query before starting. No external host
was contacted during this retrospective acceptance run.

## Result

Focused unit, contract, and security tests: 31 passed. Consent gating,
duration/resource caps, temporary-path containment, interruption cleanup,
offline behavior, p95 calculation, safe errors, and schema validation passed.
No active-test implementation correction was required.
