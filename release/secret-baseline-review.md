# Secret baseline review

- Reviewed: 2026-09-13
- Scanner: detect-secrets 1.5.0
- Policy: every new candidate fails CI until separately reviewed

The baseline contains only deliberate test material and non-secret digests. No
credential, private production key, wallet seed, access token, or password is
approved. The reviewed candidate locations are:

- `fixtures/hardware/secret-leak-trap.json`: synthetic redaction trap;
- `fixtures/receipts/ed25519-rfc8032-test1.json`: public RFC 8032 vector;
- readiness and simulation fixtures: deterministic SHA-256 model/profile digests;
- `src/flopbench/receipt/codec.py`: public base-encoding alphabet constant;
- repository, benchmark, Stage 2, Stage 5, Stage 6, and Stage 8 tests: synthetic
  hashes, authorization text, and fake key/secret markers used by negative tests.

The review intentionally records paths and purpose without reproducing candidate
values. `scripts/check_secrets.py` compares hashed candidates, so changing or
adding a value cannot silently inherit this review.
