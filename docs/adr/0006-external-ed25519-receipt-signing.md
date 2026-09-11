# ADR 0006: External Ed25519 receipt signing

- Status: Accepted
- Date: 2026-09-11

## Decision

FlopBench prepares and verifies receipt payloads but never performs private-key
operations. An external signer signs a domain-separated RFC 8785/JCS payload
that binds the report document's canonical SHA-256 digest, report schema,
existing Ed25519 `did:key`, algorithms, and local signing-time declaration.

The DID is resolved offline as base58btc multibase containing the
`ed25519-pub` multicodec prefix and a 32-byte public key. Signatures are accepted
only as canonical unpadded base64url encoding of 64 bytes.

## Consequences

- FlopBench has no key generation, key import, password, seed, PEM, or private
  key path interface.
- Receipt creation fails before writing if the external signature is invalid or
  absent.
- Verification requires only the report export and public receipt.
- A valid receipt proves key possession only; report assertions and identity
  remain unverified.
- Technocore's DID encoding is compatible, but its room-specific nonce/message
  format is deliberately outside the receipt protocol.
