from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from flopbench.cli import app
from flopbench.receipt.errors import ReceiptError
from flopbench.receipt.service import load_receipt, load_signing_request

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DID = "did:key:z6MktwupdmLXVVqTzCw4i46r4uGyosGXRnR3XjN4Zq7oMMsw"


def test_production_receipt_code_has_no_private_key_operation() -> None:
    receipt_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "src" / "flopbench" / "receipt").glob("*.py"))
    )
    assert "Ed25519PrivateKey" not in receipt_source
    assert "private_bytes" not in receipt_source
    assert "generate_private" not in receipt_source


@pytest.mark.parametrize("option", ["--password", "--private-key", "--key-file", "--seed"])
def test_secret_bearing_cli_options_are_rejected_without_value_leak(option: str) -> None:
    secret = "stage8-secret-must-not-appear"
    result = CliRunner().invoke(
        app,
        ["receipt", "prepare", "report.json", "--did", PUBLIC_DID, option, secret],
    )
    assert result.exit_code == 2
    assert "No such option" in result.output
    assert secret not in result.output


def test_receipt_symlink_input_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "receipt.json"
    source.write_text("{}", encoding="utf-8")
    original = Path.is_symlink

    def pretend_symlink(path: Path) -> bool:
        return path == source or original(path)

    monkeypatch.setattr(Path, "is_symlink", pretend_symlink)
    with pytest.raises(ReceiptError) as receipt_error:
        load_receipt(source)
    with pytest.raises(ReceiptError) as request_error:
        load_signing_request(source)
    assert receipt_error.value.code == "receipt.unsafe_input"
    assert request_error.value.code == "receipt.unsafe_input"


def test_receipt_errors_do_not_echo_sensitive_paths(tmp_path: Path) -> None:
    sensitive = tmp_path / "hostname-user-token-private-key.json"
    with pytest.raises(ReceiptError) as caught:
        load_receipt(sensitive)
    assert str(sensitive) not in str(caught.value)
    assert "hostname" not in str(caught.value)
    assert "token" not in str(caught.value)
