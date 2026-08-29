# Contributing to FlopBench

Thank you for helping build FlopBench. The project follows the normative charter in `flopbench künye.md` and develops one gated stage at a time.

## Ground rules

- Keep the project independent and clearly unofficial.
- Never introduce eligibility, airdrop, reward, wallet-seed, or real slashing behavior.
- Keep network access opt-in and document every external destination.
- Use synthetic fixtures; never commit real hostnames, user names, IP/MAC addresses, serial numbers, API keys, tokens, private prompts, or local paths.
- Label draft, provisional, estimated, and simulated values explicitly.

## Workflow

1. Create a focused branch using Conventional Commits.
2. Add unit tests and at least one failure or edge-case test.
3. Run `scripts/tasks.ps1 test-all`, `lint`, `typecheck`, and `build`.
4. Update English documentation and, for user-visible behavior, Turkish documentation.
5. Describe security, privacy, schema, and compatibility impact in the pull request.

The project uses Semantic Versioning. A feature is not complete until its stage-specific acceptance criteria pass on Windows and Ubuntu.
