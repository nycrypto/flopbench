# Schema versioning

## Policy

FlopBench public contracts use immutable names such as
`flopbench-readiness-report-v1`. A published schema file is never changed in a
way that alters which documents it accepts. Additive or breaking contract
changes require a new schema identifier and a new file. Application releases
and contract versions are independent: several application releases may emit
the same contract version.

The `$id` values under `https://schemas.flopbench.dev/v1/` are stable schema
identifiers. They do not imply that a public schema hosting service exists.
Consumers must use the schema files shipped with the same FlopBench release.

## Source profiles

Source profiles are attributable snapshots rather than application defaults.
Their identity is the SHA-256 digest of the exact UTF-8/LF file bytes. If an
upstream source changes, its old profile remains unchanged and a new profile ID
is created. Draft or provisional values must never be silently promoted to
final values.

## Compatibility

- Unknown fields are rejected.
- Required fields cannot be removed within a schema version.
- Capacity uses bytes; network throughput uses decimal bits per second.
- Values are never rounded upward before comparison.
- Timestamps are UTC and JSON Schema validation uses Draft 2020-12.

The checked-in schemas, including `flopbench-probe-v1`, are generated
deterministically from Pydantic models.
Contract tests fail if generated and committed bytes differ.
