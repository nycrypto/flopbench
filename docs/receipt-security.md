# Receipt signing security model

FlopBench receipts add an offline-verifiable Ed25519 proof to the canonical
SHA-256 digest of a report export. The proof establishes possession of the
private key corresponding to the receipt's `did:key`. It does not establish a
person's identity, hardware ownership, report truth, FLOP eligibility, rewards,
or a trusted time.

## Trust boundary

FlopBench is not a signer and has no key-management feature. It does not
generate, import, upload, read, store, log, or receive a private key or key
password. Users keep their existing DID and signing tool outside every
FlopBench process.

The three-step contract is:

1. `flopbench receipt prepare REPORT --did DID --output request.json` validates
   the report export and DID, then produces a bounded signing request.
2. An external Ed25519 signer base64url-decodes `payload_base64url`, signs those
   exact bytes, and returns one canonical unpadded base64url signature. The
   signer itself remains outside FlopBench.
3. `flopbench receipt create request.json --signature SIGNATURE --output
   receipt.json` verifies the signature before writing a new receipt.
   `flopbench receipt verify REPORT receipt.json` later needs only public data.

Omitting `--signature` cancels creation and writes no receipt. Options such as
`--password`, `--private-key`, and `--key-file` do not exist and are rejected.

## Signed bytes

The external signer signs the RFC 8785/JCS canonical UTF-8 bytes of
`flopbench-receipt-signing-payload-v1`. The payload binds:

- the report schema;
- the SHA-256 digest of the report export's canonical `document` object;
- the existing `did:key` identifier;
- the `jcs-rfc8785` and `Ed25519` algorithm identifiers;
- the locally declared UTC `signed_at` value.

The signing request carries the same bytes as canonical unpadded base64url plus
their SHA-256 digest for human/tool comparison. Changing any bound field changes
the signed bytes.

## Encoding rules

- DID method: `did:key` only.
- Multibase: `z` base58btc only.
- Multicodec: varint bytes `0xed 0x01` (`ed25519-pub`) followed by exactly 32
  public-key bytes.
- Signature: exactly 64 bytes encoded as exactly 86 canonical, unpadded
  base64url characters.
- Resolution and verification are offline; no registry or DID resolver is
  contacted.

These choices match Technocore's Ed25519 DID format. Technocore room nonces,
sequence numbers, server timestamps, and message-specific signing strings are
not part of a FlopBench receipt.

## File and failure handling

Signing requests and receipts are strict JSON objects with unknown fields
rejected. Inputs are limited to 64 KiB, symbolic links and non-regular files are
rejected, output files are never overwritten, and malformed input returns a
stable error without echoing secrets. Report exports retain their existing 8
MiB bound and internal JCS digest check.

RFC 8032 section 7.1 vectors are used as the independent Ed25519 oracle. The
dashboard intentionally contains no private-key upload control.

## References

- [RFC 8032: Edwards-Curve Digital Signature Algorithm](https://www.rfc-editor.org/rfc/rfc8032)
- [W3C did:key method](https://w3c-ccg.github.io/did-key-spec/)
- [Technocore authentication and signing model](https://technocore.chat/auth.md)
