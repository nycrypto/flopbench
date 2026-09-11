from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from flopbench.contracts import PrivacyLevel, Receipt
from flopbench.receipt.codec import (
    decode_base58btc,
    decode_base64url,
    decode_ed25519_did,
    decode_signature,
    encode_base58btc,
    encode_base64url,
    encode_ed25519_did,
)
from flopbench.receipt.errors import ReceiptError
from flopbench.receipt.models import SigningRequest
from flopbench.receipt.service import (
    MAX_RECEIPT_BYTES,
    create_receipt,
    load_receipt,
    load_signing_request,
    prepare_receipt,
    render_contract,
    signing_bytes,
    verify_detached,
    verify_receipt,
)
from flopbench.reporting.models import ReportExport
from flopbench.reporting.service import create_export, load_report

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "fixtures" / "reports" / "readiness-valid.json"
BENCHMARK_SOURCE = ROOT / "fixtures" / "reports" / "benchmark-valid.json"
BENCHMARK_V2_SOURCE = ROOT / "fixtures" / "reports" / "benchmark-v2-mock.json"
RFC8032_SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
SIGNED_AT = datetime(2026, 9, 11, 9, 30, tzinfo=UTC)
NAIVE_SIGNED_AT = SIGNED_AT.replace(tzinfo=None)


def _signed() -> tuple[ReportExport, SigningRequest, Receipt, str]:
    exported = create_export(load_report(SOURCE), PrivacyLevel.PRIVATE)
    private_key = Ed25519PrivateKey.from_private_bytes(RFC8032_SEED)
    public_key = private_key.public_key().public_bytes_raw()
    request = prepare_receipt(exported, encode_ed25519_did(public_key), SIGNED_AT)
    signature = encode_base64url(private_key.sign(signing_bytes(request.payload)))
    receipt = create_receipt(request, signature)
    return exported, request, receipt, signature


def test_base58_round_trip_preserves_leading_zeroes() -> None:
    raw = b"\x00\x00\xed\x01" + bytes(range(32))
    assert decode_base58btc(encode_base58btc(raw)) == raw


@pytest.mark.parametrize("value", ["", "0", "x" * 129])
def test_base58_rejects_invalid_or_unbounded_text(value: str) -> None:
    with pytest.raises(ReceiptError, match="base58btc"):
        decode_base58btc(value)


def test_did_codec_rejects_bad_shape_codec_and_key_length() -> None:
    with pytest.raises(ReceiptError, match="did:key"):
        decode_ed25519_did("https://example.test/key")
    wrong_codec = "did:key:z" + encode_base58btc(b"\xec\x01" + bytes(32))
    with pytest.raises(ReceiptError, match="ed25519-pub"):
        decode_ed25519_did(wrong_codec)
    short_key = "did:key:z" + encode_base58btc(b"\xed\x01" + bytes(31))
    with pytest.raises(ReceiptError, match="32 bytes"):
        decode_ed25519_did(short_key)
    with pytest.raises(ReceiptError, match="32 bytes"):
        encode_ed25519_did(bytes(31))


def test_base64url_codec_is_strict_and_canonical() -> None:
    raw = bytes(range(64))
    encoded = encode_base64url(raw)
    assert decode_signature(encoded) == raw
    with pytest.raises(ReceiptError, match="86"):
        decode_signature("AA")
    with pytest.raises(ReceiptError, match="base64url"):
        decode_base64url("A=", code="receipt.bad", label="Value", max_chars=8)
    with pytest.raises(ReceiptError, match="base64url"):
        decode_base64url("A", code="receipt.bad", label="Value", max_chars=8)
    with pytest.raises(ReceiptError, match="canonical"):
        decode_base64url("AB", code="receipt.bad", label="Value", max_chars=8)


def test_prepare_create_and_verify_round_trip() -> None:
    exported, request, receipt, _ = _signed()
    assert request.payload_base64url == encode_base64url(signing_bytes(request.payload))
    assert verify_receipt(exported, receipt).valid is True
    assert render_contract(receipt).endswith(b"\n")


def test_signing_request_rejects_payload_mismatch() -> None:
    _, request, _, _ = _signed()
    data = request.model_dump(mode="json", by_alias=True)
    data["payload_base64url"] = "AA"
    with pytest.raises(ValidationError, match="does not match"):
        SigningRequest.model_validate(data)

    data = request.model_dump(mode="json", by_alias=True)
    data["payload_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="digest does not match"):
        SigningRequest.model_validate(data)

    data = request.model_dump(mode="json", by_alias=True)
    data["payload_base64url"] = "A"
    with pytest.raises(ValidationError, match="valid unpadded base64url"):
        SigningRequest.model_validate(data)


def test_prepare_rejects_invalid_metadata_and_unsupported_report_schema() -> None:
    exported, request, _, _ = _signed()
    with pytest.raises(ReceiptError) as invalid_time:
        prepare_receipt(exported, request.payload.did, NAIVE_SIGNED_AT)
    assert invalid_time.value.code == "receipt.invalid_signing_metadata"

    unsupported = create_export(load_report(BENCHMARK_V2_SOURCE), PrivacyLevel.PRIVATE)
    with pytest.raises(ReceiptError) as unsupported_schema:
        prepare_receipt(unsupported, request.payload.did, SIGNED_AT)
    assert unsupported_schema.value.code == "receipt.unsupported_report_schema"


def test_invalid_detached_signature_is_controlled() -> None:
    _, request, _, signature = _signed()
    replacement = ("A" if signature[0] != "A" else "B") + signature[1:]
    with pytest.raises(ReceiptError, match="invalid"):
        verify_detached(request.payload.did, signing_bytes(request.payload), replacement)


def test_verify_rejects_schema_mismatch_and_invalid_metadata() -> None:
    exported, _, receipt, _ = _signed()
    benchmark = create_export(load_report(BENCHMARK_SOURCE), PrivacyLevel.PRIVATE)
    with pytest.raises(ReceiptError) as schema_mismatch:
        verify_receipt(benchmark, receipt)
    assert schema_mismatch.value.code == "receipt.report_schema_mismatch"

    invalid = Receipt.model_construct(**{**receipt.__dict__, "signed_at": NAIVE_SIGNED_AT})
    with pytest.raises(ReceiptError) as invalid_metadata:
        verify_receipt(exported, invalid)
    assert invalid_metadata.value.code == "receipt.invalid_signing_metadata"


def test_receipt_loaders_reject_unsafe_large_and_malformed_input(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(ReceiptError, match="regular file"):
        load_receipt(missing)

    too_large = tmp_path / "large.json"
    too_large.write_bytes(b"x" * (MAX_RECEIPT_BYTES + 1))
    with pytest.raises(ReceiptError, match="size limit"):
        load_signing_request(too_large)

    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"schema":', encoding="utf-8")
    with pytest.raises(ReceiptError, match="invalid"):
        load_receipt(malformed)


def test_receipt_loaders_accept_valid_contracts(tmp_path: Path) -> None:
    _, request, receipt, _ = _signed()
    request_path = tmp_path / "request.json"
    receipt_path = tmp_path / "receipt.json"
    request_path.write_bytes(render_contract(request))
    receipt_path.write_bytes(render_contract(receipt))
    assert load_signing_request(request_path) == request
    assert load_receipt(receipt_path) == receipt


def test_receipt_loader_controls_os_error_and_growth_race(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unreadable = tmp_path / "unreadable.json"
    unreadable.write_text("{}", encoding="utf-8")
    original_is_file = Path.is_file

    def fail_is_file(path: Path) -> bool:
        if path == unreadable:
            raise OSError("sensitive operating-system detail")
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", fail_is_file)
    with pytest.raises(ReceiptError) as read_error:
        load_receipt(unreadable)
    assert read_error.value.code == "receipt.read_error"
    monkeypatch.setattr(Path, "is_file", original_is_file)

    growing = tmp_path / "growing.json"
    growing.write_bytes(b"x" * (MAX_RECEIPT_BYTES + 1))
    original_stat = Path.stat

    def stale_stat(path: Path, *, follow_symlinks: bool = True) -> object:
        if path == growing:
            return SimpleNamespace(st_size=0)
        return original_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", stale_stat)
    with pytest.raises(ReceiptError) as too_large:
        load_receipt(growing)
    assert too_large.value.code == "receipt.too_large"
