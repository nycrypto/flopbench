# Stage 2 retrospective acceptance record

- Audit date: 2026-09-19
- Gate: passed
- Local platform: Windows, NVIDIA GeForce RTX 5060

## Stage tests

- `S2-T01`: the NVIDIA 24 GiB fixture is detected and normalized to
  `25,769,803,776` bytes.
- `S2-T02`: the NVIDIA 16 GiB fixture is detected and normalized to
  `17,179,869,184` bytes without rounding.
- `S2-T03`: the CPU-only fixture returns `no-supported-gpu` and an empty device
  list without crashing.
- `S2-T04`: missing-driver and unsupported-GPU fixtures return controlled
  `unknown` and `unsupported` states.
- `S2-T05`: malformed provider output returns the safe
  `probe.provider_malformed` error and CLI exit code 2 without a traceback.
- `S2-T06`: the public-output leak trap contains no hostname, user, IP, token,
  private key, device path, PCI identifier, serial number, or OS build value.
- `S2-T07`: the live probe completes while socket connection functions are
  blocked and records no attempted connection.
- `S2-T08`: repeated fixture probes produce byte-identical canonical JSON.

Strict provider and model tests additionally cover NVML initialization,
shutdown, missing bindings, absent devices, shutdown failure, invalid capacity
relationships, safe fixture errors, and the AMD fallback fixture.

## Manual acceptance

The public live probe completed on the local Windows NVIDIA system. It detected
one NVIDIA device through NVML and reported `8,546,942,976` bytes of VRAM. The
public result omitted host, filesystem device, and mount-path fields. No private
probe payload was retained in this record.

GPU-less behavior was confirmed with the deterministic CPU-only fixture. The
same Stage 2 test groups passed in the Ubuntu and Windows jobs of GitHub Actions
[run 35450465145](https://github.com/nycrypto/flopbench/actions/runs/35450465145).

## Result

Focused unit, contract, and security tests: 24 passed. The live Windows NVIDIA
check, CPU-only fixture, public redaction boundary, offline boundary, published
schema validation, and cross-platform CI all passed. No runtime or privacy
correction was required.
