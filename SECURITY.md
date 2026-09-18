# Security Policy

## Supported versions

The latest stable `1.x` release and the latest commit on `main` receive security
fixes. Release candidates receive fixes only until their corresponding stable
release is published.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or include secrets, private keys, wallet material, host identifiers, or unredacted reports in an issue.

Use the repository's [private GitHub security advisory form](https://github.com/nycrypto/flopbench/security/advisories/new).
Include the affected version, a minimal reproduction using synthetic data,
expected impact, and any suggested mitigation.

Maintainers will acknowledge a complete report within seven calendar days and
provide an initial severity/triage decision within fourteen calendar days.
Status updates are sent at least every fourteen days while a confirmed issue is
open. Coordinated disclosure happens after a fix is available; critical issues
target a fix or documented mitigation within seven days, high-severity issues
within thirty days, and lower-severity issues in the next planned release.

FlopBench will never ask for a wallet seed, wallet private key, or DID private key as part of vulnerability triage.

The complete trust and threat model is in
[`docs/security-model.md`](./docs/security-model.md).
