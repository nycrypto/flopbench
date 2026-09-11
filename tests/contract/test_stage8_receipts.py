from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from typer.testing import CliRunner

from flopbench.cli import app
from flopbench.contracts import PrivacyLevel, Receipt
from flopbench.receipt.codec import (
    decode_base64url,
    encode_base58btc,
    encode_base64url,
    encode_ed25519_did,
)
from flopbench.receipt.errors import ReceiptError
from flopbench.receipt.models import SigningRequest
from flopbench.receipt.service import (
    create_receipt,
    prepare_receipt,
    render_contract,
    signing_bytes,
    verify_detached,
    verify_receipt,
)
from flopbench.reporting.models import ReportExport
from flopbench.reporting.render import render_json
from flopbench.reporting.service import create_export, load_report

pytestmark = pytest.mark.stage8

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "fixtures" / "reports" / "readiness-valid.json"
RFC8032_FIXTURE = ROOT / "fixtures" / "receipts" / "ed25519-rfc8032-test1.json"
RFC8032_SEED_1 = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
RFC8032_PUBLIC_1 = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
RFC8032_PUBLIC_2 = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
SIGNED_AT = datetime(2026, 9, 11, 10, 0, tzinfo=UTC)


def _material() -> tuple[ReportExport, SigningRequest, Receipt, str]:
    exported = create_export(load_report(SOURCE), PrivacyLevel.PRIVATE)
    private_key = Ed25519PrivateKey.from_private_bytes(RFC8032_SEED_1)
    request = prepare_receipt(exported, encode_ed25519_did(RFC8032_PUBLIC_1), SIGNED_AT)
    signature = encode_base64url(private_key.sign(signing_bytes(request.payload)))
    return exported, request, create_receipt(request, signature), signature


def test_s8_t01_valid_ed25519_fixture_verifies() -> None:
    fixture = json.loads(RFC8032_FIXTURE.read_text(encoding="utf-8"))
    message_text = fixture["message_base64url"]
    message = (
        b""
        if message_text == ""
        else decode_base64url(
            message_text,
            code="receipt.invalid_fixture",
            label="Message",
            max_chars=4096,
        )
    )
    verify_detached(
        fixture["did"],
        message,
        fixture["signature_base64url"],
    )
    exported, _, receipt, _ = _material()
    assert verify_receipt(exported, receipt).valid is True


def test_s8_t02_one_changed_report_value_fails() -> None:
    exported, _, receipt, _ = _material()
    changed_payload = exported.document.payload.model_copy(
        update={"created_at": datetime(2026, 9, 11, 10, 0, 1, tzinfo=UTC)}
    )
    changed = create_export(changed_payload, PrivacyLevel.PRIVATE)
    with pytest.raises(ReceiptError, match="digest"):
        verify_receipt(changed, receipt)


def test_s8_t03_changed_did_fails() -> None:
    exported, _, receipt, _ = _material()
    changed = receipt.model_copy(update={"did": encode_ed25519_did(RFC8032_PUBLIC_2)})
    with pytest.raises(ReceiptError, match="invalid"):
        verify_receipt(exported, changed)


def test_s8_t04_wrong_multicodec_prefix_is_rejected() -> None:
    exported, _, _, _ = _material()
    wrong_did = "did:key:z" + encode_base58btc(b"\xec\x01" + RFC8032_PUBLIC_1)
    with pytest.raises(ReceiptError, match="ed25519-pub"):
        prepare_receipt(exported, wrong_did, SIGNED_AT)


def test_s8_t05_invalid_base58_and_base64url_are_controlled() -> None:
    exported, request, _, _ = _material()
    with pytest.raises(ReceiptError, match="base58btc"):
        prepare_receipt(exported, "did:key:z0", SIGNED_AT)
    with pytest.raises(ReceiptError, match="base64url"):
        create_receipt(request, "!" * 86)


def test_s8_t06_password_cli_argument_is_rejected_without_echoing_value() -> None:
    result = CliRunner().invoke(
        app,
        [
            "receipt",
            "prepare",
            str(SOURCE),
            "--did",
            encode_ed25519_did(RFC8032_PUBLIC_1),
            "--password",
            "do-not-echo-this",
        ],
    )
    assert result.exit_code == 2
    assert "No such option" in result.output
    assert "do-not-echo-this" not in result.output


def test_s8_t07_verify_uses_report_receipt_and_no_private_key(tmp_path: Path) -> None:
    exported, _, receipt, _ = _material()
    report_path = tmp_path / "report.json"
    receipt_path = tmp_path / "receipt.json"
    report_path.write_bytes(render_json(exported))
    receipt_path.write_bytes(render_contract(receipt))

    result = CliRunner().invoke(app, ["receipt", "verify", str(report_path), str(receipt_path)])
    assert result.exit_code == 0
    assert '"valid":true' in result.stdout
    assert "private" not in result.stdout.lower()


def test_s8_t08_cancelled_signature_creates_no_receipt(tmp_path: Path) -> None:
    _, request, _, _ = _material()
    request_path = tmp_path / "request.json"
    output_path = tmp_path / "receipt.json"
    request_path.write_bytes(render_contract(request))

    result = CliRunner().invoke(
        app, ["receipt", "create", str(request_path), "--output", str(output_path)]
    )
    assert result.exit_code == 0
    assert "cancelled" in result.stdout.lower()
    assert not output_path.exists()
