# Installation and removal

FlopBench Stage 10 targets Python 3.14.6 on 64-bit Windows and Ubuntu. The
dashboard and source profiles are included in the wheel; Node.js is not required
to run an installed package.

## Verify and install a release candidate

Download every file from the same release-candidate artifact bundle. On Ubuntu,
verify the hashes before installation:

```bash
sha256sum --check SHA256SUMS
python3.14 -m pip install flopbench-0.8.0-py3-none-any.whl
python3.14 -m flopbench.release verify --artifact-dir .
flopbench --version
flopbench probe --fixture cpu-only --privacy private
flopbench serve
```

On Windows, compare `Get-FileHash -Algorithm SHA256 <artifact>` with its
`SHA256SUMS` entry before installing the wheel, then run the packaged exact-set
verifier. The integrated service binds only to `127.0.0.1`; installation does
not publish the dashboard to the internet.

`SHA256SUMS` covers the wheel, sdist, CycloneDX JSON SBOM, and deterministic
license report. Verification rejects a missing, extra, malformed, symlinked, or
modified artifact.

## Removal and user data

```powershell
python -m pip uninstall flopbench
```

Removal deletes package-owned files only. Reports exported to a user-selected
directory remain owned by the user and are preserved. Back up important reports
normally; FlopBench is not a backup service.

## Offline operation

After dependencies and the wheel are installed, fixture/live probes and local
report exports work without network access. Ollama and OpenAI-compatible
benchmark adapters require their explicitly configured endpoint. No adapter is
contacted by `probe` or `report export`.

## Configuration compatibility

`flopbench serve --config config.json` optionally validates the local
compatibility configuration before startup. An absent configuration uses
privacy-first defaults. A config file must be a regular UTF-8 JSON file no
larger than 64 KiB and match
`flopbench-config-v1`; unknown or remote-bind fields produce an explicit error.
Existing `flopbench-benchmark-report-v1` reports remain readable without
rewriting the source file.
