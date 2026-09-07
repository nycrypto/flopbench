# Privacy

FlopBench probes are local-first and make no network requests. Probe data is
printed to the local terminal only; it is not uploaded or transmitted.

## Private output

`--privacy private` may contain the local hostname, user name, OS build,
filesystem device, mount path, GPU PCI bus identifier, and GPU serial number.
It should be treated as sensitive support data and must not be published
without review.

## Public output

`--privacy public` removes all private-only fields at the model boundary:

- hostname, user name, and IP addresses;
- OS build/version strings;
- filesystem devices and mount paths;
- GPU PCI bus identifiers and serial numbers.

CPU model, aggregate capacity, GPU product name, VRAM, and driver version remain
because they are required to interpret the hardware result. Stage 2 tests use a
deliberate secret-leak fixture and require zero matching sensitive values. The
redaction module has a mandatory 100% branch-coverage gate.

## Network boundary

The passive probe calls Python platform APIs, `psutil`, filesystem capacity
APIs, and NVIDIA NVML. It does not enumerate network interfaces and does not
open sockets. Active disk, network, and clock tests are outside Stage 2 and
require explicit user approval in Stage 4.

Stage 5 benchmark adapters contact only the endpoint selected for that run.
Loopback is the default; external hosts require an exact allowlist entry and an
explicit approval flag. Redirects are not followed. Runtime response content
is not stored in the report; only a SHA-256 digest of the bounded response is
retained. Optional OpenAI-compatible API keys are read from the selected
environment variable and are not serialized.

## Stage 6 report exports

Report exports add a `support` level between private and public. Support output
removes host, user, IP, path, device, GPU serial/bus, active-test target, and NTP
server fields while retaining OS version details. Public output also removes the
OS version. All levels reject credential-like strings that remain after their
redaction transform.

Public files require a digest-bound preview confirmation and are never written
by the export command without it. Offline HTML contains no scripts or external
resources and escapes all report values. See [reporting.md](./reporting.md).
