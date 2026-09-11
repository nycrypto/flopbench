"""Strict multibase/base58btc DID and canonical base64url codecs."""

from __future__ import annotations

import base64
import binascii
import re

from .errors import ReceiptError

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE58_INDEX = {character: index for index, character in enumerate(BASE58_ALPHABET)}
ED25519_PUB_MULTICODEC = b"\xed\x01"
ED25519_PUBLIC_KEY_BYTES = 32
ED25519_SIGNATURE_BYTES = 64
CANONICAL_SIGNATURE_LENGTH = 86
_BASE64URL = re.compile(r"^[A-Za-z0-9_-]+$")


def encode_base58btc(raw: bytes) -> str:
    """Encode bytes with the canonical Bitcoin base58 alphabet."""

    leading_zeroes = len(raw) - len(raw.lstrip(b"\x00"))
    number = int.from_bytes(raw, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = BASE58_ALPHABET[remainder] + encoded
    return ("1" * leading_zeroes) + encoded


def decode_base58btc(value: str) -> bytes:
    """Decode one short, canonical base58btc value."""

    if not value or len(value) > 128:
        raise ReceiptError("receipt.invalid_base58", "DID key must use bounded base58btc")
    number = 0
    try:
        for character in value:
            number = number * 58 + BASE58_INDEX[character]
    except KeyError as exc:
        raise ReceiptError("receipt.invalid_base58", "DID key is not valid base58btc") from exc
    decoded = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    leading_zeroes = len(value) - len(value.lstrip("1"))
    return (b"\x00" * leading_zeroes) + decoded


def encode_ed25519_did(public_key: bytes) -> str:
    """Encode an existing Ed25519 public key; no key generation occurs."""

    if len(public_key) != ED25519_PUBLIC_KEY_BYTES:
        raise ReceiptError("receipt.invalid_public_key", "Ed25519 public key must be 32 bytes")
    return "did:key:z" + encode_base58btc(ED25519_PUB_MULTICODEC + public_key)


def decode_ed25519_did(did: str) -> bytes:
    """Resolve a did:key Ed25519 public key fully offline."""

    prefix = "did:key:z"
    if not did.startswith(prefix):
        raise ReceiptError("receipt.invalid_did", "DID must use did:key with base58btc")
    decoded = decode_base58btc(did[len(prefix) :])
    if not decoded.startswith(ED25519_PUB_MULTICODEC):
        raise ReceiptError(
            "receipt.unsupported_multicodec", "DID must contain an ed25519-pub multicodec key"
        )
    public_key = decoded[len(ED25519_PUB_MULTICODEC) :]
    if len(public_key) != ED25519_PUBLIC_KEY_BYTES:
        raise ReceiptError("receipt.invalid_public_key", "Ed25519 public key must be 32 bytes")
    return public_key


def encode_base64url(raw: bytes) -> str:
    """Return canonical, unpadded base64url."""

    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode_base64url(value: str, *, code: str, label: str, max_chars: int) -> bytes:
    """Strictly decode bounded, unpadded, canonical base64url."""

    if not value or len(value) > max_chars or _BASE64URL.fullmatch(value) is None:
        raise ReceiptError(code, f"{label} is not valid unpadded base64url")
    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        raw = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ReceiptError(code, f"{label} is not valid unpadded base64url") from exc
    if encode_base64url(raw) != value:
        raise ReceiptError(code, f"{label} is not canonical base64url")
    return raw


def decode_signature(value: str) -> bytes:
    """Decode Technocore-compatible canonical Ed25519 signature text."""

    if len(value) != CANONICAL_SIGNATURE_LENGTH:
        raise ReceiptError(
            "receipt.invalid_signature_encoding",
            "Ed25519 signature must be 86 canonical base64url characters",
        )
    return decode_base64url(
        value,
        code="receipt.invalid_signature_encoding",
        label="Signature",
        max_chars=CANONICAL_SIGNATURE_LENGTH,
    )
