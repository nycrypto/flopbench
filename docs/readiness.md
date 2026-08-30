# Readiness methodology

Stage 3 compares normalized passive-probe values with one exact, hashed source
profile. It performs no network requests and does not modify the host.

## Decision states

Every check returns exactly one of `pass`, `warn`, `fail`, `unknown`, `skipped`,
or `unsupported`, plus at least one stable machine-readable reason code.
`unknown` means a reliable value was unavailable. `unsupported` describes the
provider or platform and is not treated as insufficient hardware.

## Source profile checks

- Miner VRAM uses the largest reported device capacity and compares raw bytes.
- Validator CPU uses physical core count; an unavailable physical count remains
  `unknown`.
- Validator RAM and largest-disk capacity use raw bytes.
- Validator disk kind must be reported as NVMe; an unreliable kind remains
  `unknown`.
- Validator network capacity remains `skipped` until the user-approved Stage 4
  active test runs.

Values are never rounded upward. The 16 GiB miner threshold is therefore
17,179,869,184 bytes; a normalized 15.99 GiB value remains below it.

## Community checks

Community checks use `source_kind: community`, are not required source-profile
conditions, and appear in a separate terminal section. Stage 3 includes a miner
VRAM headroom advisory: less than 25% headroom above the source threshold is a
warning. It is not combined with the source-profile result into a score.

The profile ID, raw-file SHA-256 digest, and `draft`/`provisional`/`final`
source status are included in every readiness report.
