# v1.0.0 release checklist

This is the two-person gate for the stable release. `Implementer` is completed
only after local and remote evidence is recorded in the Stage 11 acceptance
report. `User` remains pending until the user reviews that report and explicitly
approves publication.

| Check | Implementer | User |
|---|---|---|
| Stable SemVer and changelog | Complete (2026-09-18) | Approved (2026-09-19) |
| Windows and Ubuntu CI | Complete (2026-09-18) | Approved (2026-09-19) |
| Unit, contract, security, web, E2E, lint, typecheck, build | Complete (2026-09-18) | Approved (2026-09-19) |
| Clean install, use, and uninstall with reports preserved | Complete (2026-09-18) | Approved (2026-09-19) |
| Wheel/sdist, SBOM, licenses, checksums, audits | Complete (2026-09-18) | Approved (2026-09-19) |
| Miner, validator, benchmark, receipt, and PoUI acceptance | Complete (2026-09-18) | Approved (2026-09-19) |
| README commands, links, examples, and demo media | Complete (2026-09-18) | Approved (2026-09-19) |
| Draft/provisional/simulated/unofficial labels | Complete (2026-09-18) | Approved (2026-09-19) |
| Security contact, privacy, methodology, limitations | Complete (2026-09-18) | Approved (2026-09-19) |
| Tag workflow creates attestations before publication | Complete (2026-09-18) | Approved (2026-09-19) |

No `v1.0.0` tag or public stable GitHub release may be created while any cell is
pending or failed.

Implementer evidence is recorded in the
[Stage 11 acceptance record](./stage-11-acceptance.md). The final row means the
workflow's fail-closed draft/attest/publish ordering has been reviewed and
tested; the actual attestation can only be created after the approved tag is
pushed.

The user reviewed the Stage 11 result and explicitly approved merge, tag, and
stable GitHub publication on 2026-09-19.
