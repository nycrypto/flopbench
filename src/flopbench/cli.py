"""FlopBench command-line entry point."""

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

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
from flopbench.validator_doctor.formatters import doctor_json, doctor_terminal
from flopbench.validator_doctor.models import NetworkTarget, TestLimits
from flopbench.validator_doctor.service import (
    DoctorError,
    run_fixture_doctor,
    run_live_doctor,
)

app = typer.Typer(
    add_completion=False,
    help="Unofficial, independent, local-first FlopBench community workbench.",
    no_args_is_help=True,
)
check_app = typer.Typer(help="Evaluate passive probe data against a sourced profile.")
app.add_typer(check_app, name="check")
doctor_app = typer.Typer(help="Run bounded, user-approved active health tests.")
app.add_typer(doctor_app, name="doctor")

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


def _network_target(value: str | None) -> NetworkTarget | None:
    if value is None:
        return None
    try:
        if value.startswith("[") and "]:" in value:
            host, port_text = value[1:].rsplit("]:", maxsplit=1)
        else:
            host, port_text = value.rsplit(":", maxsplit=1)
        return NetworkTarget(host=host, port=int(port_text))
    except (ValueError, ValidationError) as exc:
        raise typer.BadParameter("network target must be host:port") from exc


def _plain_host(value: str | None, *, option_name: str) -> str | None:
    if value is None:
        return None
    if (
        len(value) > 253
        or any(character.isspace() for character in value)
        or "/" in value
        or "\\" in value
    ):
        raise typer.BadParameter(f"{option_name} must be a plain hostname or IP address")
    return value


@doctor_app.command("validator")
def doctor_validator(
    approve: Annotated[
        bool,
        typer.Option("--approve", help="Explicitly approve the displayed active tests."),
    ] = False,
    fixture: Annotated[
        Path | None,
        typer.Option("--fixture", help="Use a deterministic doctor fixture."),
    ] = None,
    temp_root: Annotated[
        Path | None,
        typer.Option("--temp-root", help="Parent for the isolated temporary directory."),
    ] = None,
    disk_bytes: Annotated[
        int,
        typer.Option("--disk-bytes", min=1024, max=64 * 1024**2),
    ] = 8 * 1024**2,
    max_duration: Annotated[
        float,
        typer.Option("--max-duration", min=0.1, max=30.0),
    ] = 10.0,
    network_target_text: Annotated[
        str | None,
        typer.Option("--network-target", help="Explicit TCP target as host:port."),
    ] = None,
    network_attempts: Annotated[
        int,
        typer.Option("--network-attempts", min=1, max=20),
    ] = 5,
    ntp_server: Annotated[
        str | None,
        typer.Option("--ntp-server", help="Explicit NTP server hostname or IP."),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", min=0.1, max=5.0),
    ] = 2.0,
    output_format: Annotated[
        CheckOutputFormat,
        typer.Option("--format", help="Terminal or JSON output."),
    ] = CheckOutputFormat.TERMINAL,
) -> None:
    """Run bounded disk, TCP-connect, and optional NTP health tests."""

    target = _network_target(network_target_text)
    ntp_server = _plain_host(ntp_server, option_name="NTP server")
    limits = TestLimits(
        disk_bytes=disk_bytes,
        disk_chunk_bytes=min(1024**2, disk_bytes),
        max_duration_seconds=max_duration,
        network_attempts=network_attempts,
        network_timeout_seconds=timeout,
    )
    plan_to_stderr = approve
    if fixture is None:
        typer.echo(
            f"Disk: write/read at most {disk_bytes} bytes in an isolated temp directory",
            err=plan_to_stderr,
        )
        typer.echo(
            "Network: "
            + (
                f"TCP connect only to {target.display}; no application payload"
                if target is not None
                else "skipped (no target selected)"
            ),
            err=plan_to_stderr,
        )
        typer.echo(
            f"Clock: 48-byte NTP query to {ntp_server}"
            if ntp_server is not None
            else "Clock: skipped (no server selected)",
            err=plan_to_stderr,
        )
    else:
        typer.echo(
            "Fixture mode: no active disk or network operation will run",
            err=plan_to_stderr,
        )
    if not approve:
        approve = typer.confirm("Run these active tests?", default=False)
        if not approve:
            typer.echo("Active tests cancelled; nothing was written or sent.")
            return
    try:
        report = (
            run_fixture_doctor(fixture, approved=True)
            if fixture is not None
            else run_live_doctor(
                approved=True,
                limits=limits,
                temp_root=temp_root,
                network_target=target,
                ntp_server=ntp_server,
            )
        )
    except DoctorError as exc:
        error = {"code": exc.code.value, "message": str(exc)}
        typer.echo(json.dumps(error, separators=(",", ":"), sort_keys=True), err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(
        doctor_json(report) if output_format is CheckOutputFormat.JSON else doctor_terminal(report)
    )
