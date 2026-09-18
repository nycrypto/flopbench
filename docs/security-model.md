# Security model

## Scope and guarantees

FlopBench measures a local machine, renders local reports, and can call an
explicitly selected inference runtime. It is not a wallet, miner/validator
client, eligibility checker, claim tool, or official FLOP service. Reports are
unverified local observations unless an independent verifier establishes more.

The security objectives are:

- keep private keys, wallet seeds, credentials, host identifiers, and local paths
  out of public output;
- keep the dashboard and API on literal loopback addresses;
- make every network destination explicit, bounded, and user approved;
- treat providers, fixtures, report files, redirects, and browser origins as
  untrusted input;
- make release files reproducible, checksummed, dependency-audited, and traceable
  to a GitHub workflow and commit.

## Trust boundaries

The passive probe has no network path. Active disk/network/clock tests require
consent and enforce time/resource limits. Benchmark adapters accept loopback by
default; external hosts require an exact allowlist entry and approval, and
redirects are rejected. The FastAPI service validates Host and Origin, requires
its startup token for `/api/v1`, caps request/response sizes, and never supports
remote bind in v1.

Ed25519 signing occurs outside FlopBench. The CLI accepts only the public DID,
canonical signing request, and detached signature. A valid receipt proves key
possession and report binding; it does not prove identity, machine ownership,
measurement honesty, FLOP eligibility, or a trusted timestamp.

## Release provenance

The stable tag workflow builds from the tagged commit with locked dependencies,
verifies checksums/SBOM/licenses, creates a draft GitHub release, and requests a
GitHub OIDC-backed build-provenance attestation for every release file. The draft
is published only after attestation succeeds. This attestation proves repository
workflow provenance; it does not certify runtime measurements. See
[`release-attestations.md`](./release-attestations.md).

## Residual risks

- GPU/OS drivers may misreport hardware and other processes can affect benchmark
  measurements.
- Local malware or a compromised runtime can falsify data before collection.
- A public report can still be identifying through unusual non-secret hardware
  combinations; users must preview it before sharing.
- GitHub, package registries, and upstream dependencies remain supply-chain trust
  dependencies during development and release.
- The current FLOP source profile is a versioned draft snapshot, not a stable
  protocol contract.

Report vulnerabilities through the private process and response policy in
[`SECURITY.md`](../SECURITY.md).
