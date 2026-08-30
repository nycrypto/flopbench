from typer.testing import CliRunner

from flopbench import __version__
from flopbench.cli import app


def test_version_is_stage_one_version() -> None:
    assert __version__ == "0.1.0a1"


def test_cli_reports_version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout == "flopbench 0.1.0a1\n"


def test_cli_help_contains_unofficial_boundary() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "unofficial" in result.stdout.lower()
