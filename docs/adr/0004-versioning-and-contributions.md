# ADR 0004: Versioning and contribution policy

- Status: Accepted
- Date: 2026-08-29

## Decision

Use Semantic Versioning, Conventional Commits, stage-labeled branches, and a changelog. A stage is merged and tagged only after its automated and manual gates pass and the stage report is approved.

Dependencies are updated through reviewed pull requests. Production and CI configurations may not use floating `latest` tags.
