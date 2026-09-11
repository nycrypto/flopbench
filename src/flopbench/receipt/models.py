"""Strict public contracts for the external receipt signer workflow."""

from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from flopbench.contracts import Sha256Hex, StrictModel
from flopbench.reporting.canonical import canonical_bytes

from .codec import decode_base64url, decode_ed25519_did, encode_base64url
from .errors import ReceiptError

ReceiptReportSchema = Literal["flopbench-readiness-report-v1", "flopbench-benchmark-report-v1"]


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC")
    return value


class ReceiptSigningPayload(StrictModel):
    """Domain-separated JCS payload signed by an external Ed25519 signer."""

    schema_id: Literal["flopbench-receipt-signing-payload-v1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    report_schema: ReceiptReportSchema
    report_sha256: Sha256Hex
    did: Annotated[str, Field(min_length=20, max_length=128)]
    canonicalization: Literal["jcs-rfc8785"] = "jcs-rfc8785"
    signature_algorithm: Literal["Ed25519"] = "Ed25519"
    signed_at: datetime

    _signed_at_utc = field_validator("signed_at")(_require_utc)


class SigningRequest(StrictModel):
    """Portable request passed to a signer that lives outside FlopBench."""

    schema_id: Literal["flopbench-signing-request-v1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    payload: ReceiptSigningPayload
    payload_encoding: Literal["jcs-rfc8785+base64url"] = "jcs-rfc8785+base64url"
    payload_base64url: Annotated[
        str, Field(min_length=1, max_length=4096, pattern=r"^[A-Za-z0-9_-]+$")
    ]
    payload_sha256: Sha256Hex
    signer_contract: Literal["external-ed25519-v1"] = "external-ed25519-v1"

    @model_validator(mode="after")
    def payload_matches_claims(self) -> Self:
        expected = canonical_bytes(self.payload.model_dump(mode="json", by_alias=True))
        try:
            supplied = decode_base64url(
                self.payload_base64url,
                code="receipt.invalid_payload_encoding",
                label="Signing payload",
                max_chars=4096,
            )
        except ReceiptError as exc:
            raise ValueError(str(exc)) from exc
        if supplied != expected or encode_base64url(expected) != self.payload_base64url:
            raise ValueError("signing payload does not match its claims")
        if sha256(expected).hexdigest() != self.payload_sha256:
            raise ValueError("signing payload digest does not match its claims")
        decode_ed25519_did(self.payload.did)
        return self


class VerificationResult(StrictModel):
    """Machine-readable success result; failures are controlled errors."""

    schema_id: Literal["flopbench-receipt-verification-v1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    valid: Literal[True] = True
    did: str
    report_sha256: Sha256Hex
    payload_sha256: Sha256Hex
    proof: Literal["ed25519-key-possession"] = "ed25519-key-possession"
    authenticity: Literal["report-claims-not-independently-verified"] = (
        "report-claims-not-independently-verified"
    )
