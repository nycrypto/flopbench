# Stage 1 retrospective acceptance record

- Audit date: 2026-09-19
- Gate: passed
- Source profile: `flop-teaser-0.1`
- Profile SHA-256: `a58ba933752eff52b876fb3910cb31d824b14987a056fc62f2f919bfbe414f8c`

## Source revalidation

The official [FLOP teaser](https://flop.finance/teaser/) was fetched successfully
during this audit. It still identifies itself as `Version 0.1 (draft)`, reports
`Updated 2026-08-26`, says the figures are provisional, and publishes the same
recommended hardware text represented by the checked-in profile:

- miner: 16 GB+ VRAM per unit;
- validator: 8+ core CPU, 64 GB RAM, 2 TB NVMe, and a 1 Gbps redundant
  connection.

Because the source version, status, update date, and represented values have not
changed, the existing attributable snapshot was not silently edited or replaced.

## Stage tests

- `S1-T01`: the valid teaser profile loads and normalizes binary capacity and
  decimal network values exactly.
- `S1-T02`: a missing source URL is rejected with
  `profile.validation_error` and a safe `source_url` issue path.
- `S1-T03`: negative miner VRAM and validator memory values are rejected.
- `S1-T04`: the same raw UTF-8/LF bytes produce the same SHA-256 digest.
- `S1-T05`: changing even one newline changes the digest.
- `S1-T06`: unknown fields are rejected by the strict Pydantic model and JSON
  Schema contract.
- `S1-T07`: the readiness fixture validates against the committed Draft
  2020-12 schema and typed model.
- `S1-T08`: the receipt fixture validates against the committed schema and
  typed model.

The benchmark fixture and every published schema also validate, and committed
schema bytes exactly match deterministic regeneration. Loader tests additionally
cover BOM, CRLF, malformed UTF-8/YAML, duplicate keys, oversized input, safe
read errors, UTC enforcement, and internally consistent summaries.

## Result

Focused profile/schema tests: 25 passed. No profile value, schema, runtime
behavior, privacy boundary, or external network default required correction.
The schema-versioning policy remains documented in `docs/schema-versioning.md`.
