# Stage 3 retrospective acceptance record

- Audit date: 2026-09-19
- Gate: passed
- Source profile: `flop-teaser-0.1` (`draft`)

## Stage tests

- `S3-T01`: a 24 GiB NVIDIA fixture passes the 16 GiB miner VRAM rule.
- `S3-T02`: exactly 16 GiB passes at the byte boundary.
- `S3-T03`: the normalized 15.99 GiB fixture remains below the threshold and
  fails; it is never rounded upward.
- `S3-T04`: unavailable VRAM returns `unknown`, not an automatic failure.
- `S3-T05`: the validator boundary fixture passes CPU, RAM, disk-capacity, and
  disk-kind source checks; the deferred network check is `skipped`.
- `S3-T06`: the low-memory validator fixture fails only the RAM source check.
- `S3-T07`: an unidentifiable disk kind remains `unknown` while its independently
  known capacity can pass.
- `S3-T08`: `draft` appears in both canonical JSON and terminal output.
- `S3-T09`: community headroom remains optional, carries `source_kind:
  community`, and is printed separately from source-profile checks.

Every result contains a stable machine-readable reason code. Model validation
rejects summary counters that do not match the individual checks. Unit coverage
also confirms safe `unsupported` behavior, missing physical-core and disk data,
non-NVMe failure, and community headroom boundaries.

## Live acceptance

The local Windows RTX 5060 was evaluated against the unchanged draft profile.
Its approximately 8 GiB of reported VRAM correctly failed the 16 GiB source
threshold; this is expected behavior and is not an application error. The
community check was separately labeled and did not alter the source result.

The live validator result exposed all six summary counters and retained the
network check as `skipped`. No official score, eligibility, identity, or reward
claim appears in CLI output.

## Result

Focused unit and contract tests: 18 passed. Exact byte comparisons, all six
result states, source/community separation, deterministic JSON, readable CLI
output, and reason-code requirements passed. The full Windows and Ubuntu gate
also passed in the preceding cross-platform CI run. No readiness-engine
correction was required.
