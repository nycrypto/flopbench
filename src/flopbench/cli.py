"""FlopBench command-line entry point."""

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from flopbench import __version__
from flopbench.contracts import PrivacyLevel, Role
from flopbench.probe.service import (
    ProbeError,
    canonical_probe_json,
    run_fixture_probe,
    run_live_probe,
)
from flopbench.profile_loader import ProfileLoadError, load_profile
from flopbench.readiness.engine import evaluate_readiness
from flopbench.readiness.formatters import readiness_json, readiness_terminal

app = typer.Typer(
    add_completion=False,
    help="Unofficial, independent, local-first FlopBench community workbench.",
    no_args_is_help=True,
)
check_app = typer.Typer(help="Evaluate passive probe data against a sourced profile.")
app.add_typer(check_app, name="check")

DEFAULT_PROFILE = Path("profiles/flop-teaser-0.1.yaml")


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


class CheckOutputFormat(StrEnum):
    TERMINAL = "terminal"
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


def _run_check(
    role: Role,
    fixture: Path | None,
    profile_path: Path,
    privacy: PrivacyLevel,
    output_format: CheckOutputFormat,
) -> None:
    try:
        probe_report = run_fixture_probe(fixture, privacy) if fixture else run_live_probe(privacy)
        report = evaluate_readiness(probe_report, load_profile(profile_path), role)
    except (ProbeError, ProfileLoadError) as exc:
        error = {"code": exc.code.value, "message": str(exc)}
        typer.echo(json.dumps(error, separators=(",", ":"), sort_keys=True), err=True)
        raise typer.Exit(code=2) from exc
    output = (
        readiness_json(report)
        if output_format is CheckOutputFormat.JSON
        else readiness_terminal(report)
    )
    typer.echo(output)


@check_app.command("miner")
def check_miner(
    fixture: Annotated[
        Path | None,
        typer.Option("--fixture", help="Use a deterministic local hardware fixture."),
    ] = None,
    profile_path: Annotated[
        Path,
        typer.Option("--profile", help="Use this versioned source profile."),
    ] = DEFAULT_PROFILE,
    privacy: Annotated[
        PrivacyLevel,
        typer.Option("--privacy", help="Private or redacted public probe input."),
    ] = PrivacyLevel.PUBLIC,
    output_format: Annotated[
        CheckOutputFormat,
        typer.Option("--format", help="Terminal or JSON output."),
    ] = CheckOutputFormat.TERMINAL,
) -> None:
    """Evaluate miner VRAM readiness and separately labeled community headroom."""

    _run_check(Role.MINER, fixture, profile_path, privacy, output_format)


@check_app.command("validator")
def check_validator(
    fixture: Annotated[
        Path | None,
        typer.Option("--fixture", help="Use a deterministic local hardware fixture."),
    ] = None,
    profile_path: Annotated[
        Path,
        typer.Option("--profile", help="Use this versioned source profile."),
    ] = DEFAULT_PROFILE,
    privacy: Annotated[
        PrivacyLevel,
        typer.Option("--privacy", help="Private or redacted public probe input."),
    ] = PrivacyLevel.PUBLIC,
    output_format: Annotated[
        CheckOutputFormat,
        typer.Option("--format", help="Terminal or JSON output."),
    ] = CheckOutputFormat.TERMINAL,
) -> None:
    """Evaluate passive validator CPU, RAM, disk, and deferred network readiness."""

    _run_check(Role.VALIDATOR, fixture, profile_path, privacy, output_format)
