"""FlopBench command-line entry point."""

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from flopbench import __version__
from flopbench.contracts import PrivacyLevel
from flopbench.probe.service import (
    ProbeError,
    canonical_probe_json,
    run_fixture_probe,
    run_live_probe,
)

app = typer.Typer(
    add_completion=False,
    help="Unofficial, independent, local-first FlopBench community workbench.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print the package version and exit."""
    if value:
        typer.echo(f"flopbench {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version."),
    ] = None,
) -> None:
    """FlopBench is unofficial and does not provide FLOP eligibility or rewards."""


class OutputFormat(StrEnum):
    JSON = "json"


@app.command()
def probe(
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", help="Output format."),
    ] = OutputFormat.JSON,
    fixture: Annotated[
        Path | None,
        typer.Option("--fixture", help="Use a deterministic local JSON fixture."),
    ] = None,
    privacy: Annotated[
        PrivacyLevel,
        typer.Option("--privacy", help="Private or redacted public output."),
    ] = PrivacyLevel.PRIVATE,
) -> None:
    """Passively inspect local capacity without making network requests."""

    del output_format  # Only JSON is intentionally supported in Stage 2.
    try:
        report = run_fixture_probe(fixture, privacy) if fixture else run_live_probe(privacy)
    except ProbeError as exc:
        error = {"code": exc.code.value, "message": str(exc)}
        typer.echo(json.dumps(error, separators=(",", ":"), sort_keys=True), err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(canonical_probe_json(report))
