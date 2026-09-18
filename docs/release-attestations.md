# Release attestations

FlopBench stable artifacts are published by the tag-only GitHub Actions workflow
in [`.github/workflows/release.yml`](../.github/workflows/release.yml). The
workflow uses locked build dependencies and GitHub's first-party OIDC attestation
action pinned to an immutable commit.

## What is signed

Each wheel, source distribution, CycloneDX SBOM, license report, and checksum
manifest is a subject of the build-provenance attestation. The attestation binds
the artifact digest to the public repository, tagged commit, workflow, and run.
This is the signed contribution/build proof required by the v1 release gate.
No maintainer private signing key is stored in FlopBench or GitHub secrets.

## Verify a downloaded release

First validate the offline checksums from the extracted/download directory:

```powershell
python -m flopbench.release verify --artifact-dir .
```

Then, while online with GitHub CLI installed, verify an individual artifact's
repository provenance:

```powershell
gh attestation verify flopbench-1.0.0-py3-none-any.whl --repo nycrypto/flopbench
```

Also confirm that the release tag is `v1.0.0` and the digest printed by the
attestation matches the file you inspected. A valid artifact attestation does not
authenticate a user's benchmark or readiness report; report receipts have the
separate limits described in [`receipt-security.md`](./receipt-security.md).
