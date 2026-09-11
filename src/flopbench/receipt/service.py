"""Prepare, assemble, and verify receipts without handling private keys."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import ValidationError

from flopbench.contracts import Receipt, StrictModel
from flopbench.reporting.canonical import canonical_bytes, parse_json
from flopbench.reporting.errors import ReportError
from flopbench.reporting.models import ReportExport

from .codec import decode_ed25519_did, decode_signature, encode_base64url
from .errors import ReceiptError
from .models import (
    ReceiptReportSchema,
    ReceiptSigningPayload,
    SigningRequest,
    VerificationResult,
)

MAX_RECEIPT_BYTES = 64 * 1024


def _report_schema(exported: ReportExport) -> ReceiptReportSchema:
    schema = exported.document.payload.schema_id
    if schema not in {
        "flopbench-readiness-report-v1",
        "flopbench-benchmark-report-v1",
    }:
        raise ReceiptError(
            "receipt.unsupported_report_schema",
            "Receipt signing supports readiness-v1 and benchmark-v1 reports",
        )
    return schema


def signing_bytes(payload: ReceiptSigningPayload) -> bytes:
    """Return the exact domain-separated bytes an external signer signs."""

    return canonical_bytes(payload.model_dump(mode="json", by_alias=True))


def prepare_receipt(
    exported: ReportExport,
    did: str,
    signed_at: datetime,
) -> SigningRequest:
    """Create a deterministic request containing no private material."""

    decode_ed25519_did(did)
    try:
        payload = ReceiptSigningPayload(
            schema="flopbench-receipt-signing-payload-v1",
            report_schema=_report_schema(exported),
            report_sha256=exported.digest.value,
            did=did,
            signed_at=signed_at,
        )
    except ValidationError as exc:
        raise ReceiptError(
            "receipt.invalid_signing_metadata", "Signing metadata is invalid"
        ) from exc
    raw = signing_bytes(payload)
    return SigningRequest(
        schema="flopbench-signing-request-v1",
        payload=payload,
        payload_base64url=encode_base64url(raw),
        payload_sha256=sha256(raw).hexdigest(),
    )


def verify_detached(did: str, message: bytes, signature: str) -> None:
    """Verify a canonical base64url Ed25519 signature against an offline DID."""

    public_key = decode_ed25519_did(did)
    signature_bytes = decode_signature(signature)
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature_bytes, message)
    except (InvalidSignature, ValueError) as exc:
        raise ReceiptError("receipt.signature_invalid", "Receipt signature is invalid") from exc


def create_receipt(request: SigningRequest, signature: str) -> Receipt:
    """Assemble a receipt only after the external signature verifies."""

    raw = signing_bytes(request.payload)
    verify_detached(request.payload.did, raw, signature)
    return Receipt(
        schema="flopbench-receipt-v1",
        report_schema=request.payload.report_schema,
        report_sha256=request.payload.report_sha256,
        did=request.payload.did,
        canonicalization=request.payload.canonicalization,
        signature_algorithm=request.payload.signature_algorithm,
        signature=signature,
        signed_at=request.payload.signed_at,
    )


def verify_receipt(exported: ReportExport, receipt: Receipt) -> VerificationResult:
    """Verify report binding and Ed25519 proof using public data only."""

    if receipt.report_schema != _report_schema(exported):
        raise ReceiptError("receipt.report_schema_mismatch", "Receipt report schema does not match")
    if receipt.report_sha256 != exported.digest.value:
        raise ReceiptError("receipt.report_digest_mismatch", "Receipt report digest does not match")
    try:
        payload = ReceiptSigningPayload(
            schema="flopbench-receipt-signing-payload-v1",
            report_schema=receipt.report_schema,
            report_sha256=receipt.report_sha256,
            did=receipt.did,
            canonicalization=receipt.canonicalization,
            signature_algorithm=receipt.signature_algorithm,
            signed_at=receipt.signed_at,
        )
    except ValidationError as exc:
        raise ReceiptError(
            "receipt.invalid_signing_metadata", "Receipt metadata is invalid"
        ) from exc
    raw = signing_bytes(payload)
    verify_detached(receipt.did, raw, receipt.signature)
    return VerificationResult(
        schema="flopbench-receipt-verification-v1",
        did=receipt.did,
        report_sha256=receipt.report_sha256,
        payload_sha256=sha256(raw).hexdigest(),
    )


def _load_model[ModelT: StrictModel](path: Path, model: type[ModelT]) -> ModelT:
    try:
        if path.is_symlink() or not path.is_file():
            raise ReceiptError("receipt.unsafe_input", "Receipt input must be a regular file")
        if path.stat().st_size > MAX_RECEIPT_BYTES:
            raise ReceiptError("receipt.too_large", "Receipt input exceeds the size limit")
        with path.open("rb") as handle:
            raw = handle.read(MAX_RECEIPT_BYTES + 1)
    except ReceiptError:
        raise
    except OSError as exc:
        raise ReceiptError("receipt.read_error", "Receipt input could not be read") from exc
    if len(raw) > MAX_RECEIPT_BYTES:
        raise ReceiptError("receipt.too_large", "Receipt input exceeds the size limit")
    try:
        return model.model_validate(parse_json(raw))
    except (ValidationError, ReportError) as exc:
        raise ReceiptError("receipt.invalid_json", "Receipt input is invalid") from exc


def load_signing_request(path: Path) -> SigningRequest:
    return _load_model(path, SigningRequest)


def load_receipt(path: Path) -> Receipt:
    receipt = _load_model(path, Receipt)
    decode_ed25519_did(receipt.did)
    decode_signature(receipt.signature)
    return receipt


def render_contract(value: StrictModel) -> bytes:
    return canonical_bytes(value.model_dump(mode="json", by_alias=True)) + b"\n"
