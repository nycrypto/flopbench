# v1.0.0 release checklist

This is the two-person gate for the stable release. `Implementer` is completed
only after local and remote evidence is recorded in the Stage 11 acceptance
report. `User` remains pending until the user reviews that report and explicitly
approves publication.

| Check | Implementer | User |
|---|---|---|
| Stable SemVer and changelog | Complete (2026-09-18) | Pending |
| Windows and Ubuntu CI | Complete (2026-09-18) | Pending |
| Unit, contract, security, web, E2E, lint, typecheck, build | Complete (2026-09-18) | Pending |
| Clean install, use, and uninstall with reports preserved | Complete (2026-09-18) | Pending |
| Wheel/sdist, SBOM, licenses, checksums, audits | Complete (2026-09-18) | Pending |
| Miner, validator, benchmark, receipt, and PoUI acceptance | Complete (2026-09-18) | Pending |
| README commands, links, examples, and demo media | Complete (2026-09-18) | Pending |
| Draft/provisional/simulated/unofficial labels | Complete (2026-09-18) | Pending |
| Security contact, privacy, methodology, limitations | Complete (2026-09-18) | Pending |
| Tag workflow creates attestations before publication | Complete (2026-09-18) | Pending |

No `v1.0.0` tag or public stable GitHub release may be created while any cell is
pending or failed.

Implementer evidence is recorded in the
[Stage 11 acceptance record](./stage-11-acceptance.md). The final row means the
workflow's fail-closed draft/attest/publish ordering has been reviewed and
tested; the actual attestation can only be created after the approved tag is
pushed.
