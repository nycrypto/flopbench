"""FlopBench command-line entry point."""

import json
import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Never

import typer
from pydantic import ValidationError

from flopbench import __version__
from flopbench.benchmark.adapters import AdapterError, DeterministicMockAdapter
from flopbench.benchmark.endpoint import EndpointError, validate_endpoint
from flopbench.benchmark.engine import (
    BenchmarkCancelledError,
    canonical_benchmark_json,
    run_benchmark,
)
from flopbench.benchmark.http_adapters import OllamaAdapter, OpenAICompatibleAdapter
from flopbench.benchmark.vram import NvidiaVramObserver
from flopbench.benchmark.workload import WorkloadError, load_workload
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
from flopbench.receipt.errors import ReceiptError
from flopbench.receipt.service import (
    create_receipt,
    load_receipt,
    load_signing_request,
    prepare_receipt,
    render_contract,
    verify_receipt,
)
from flopbench.reporting.canonical import canonical_bytes
from flopbench.reporting.compare import compare_benchmarks, diff_exports
from flopbench.reporting.errors import ReportError
from flopbench.reporting.render import render_html, render_json, render_terminal
from flopbench.reporting.service import create_export, load_export, load_report, write_new_file
from flopbench.validator_doctor.formatters import doctor_json, doctor_terminal
from flopbench.validator_doctor.models import NetworkTarget, TestLimits
from flopbench.validator_doctor.service import (
    DoctorError,
    run_fixture_doctor,
    run_live_doctor,
)
from flopbench.webapp import DEFAULT_WEB_DIST, create_app, validate_bind_host

app = typer.Typer(
    add_completion=False,
    help="Unofficial, independent, local-first FlopBench community workbench.",
    no_args_is_help=True,
)
check_app = typer.Typer(help="Evaluate passive probe data against a sourced profile.")
app.add_typer(check_app, name="check")
doctor_app = typer.Typer(help="Run bounded, user-approved active health tests.")
app.add_typer(doctor_app, name="doctor")
benchmark_app = typer.Typer(help="Run provider-independent inference benchmarks.")
app.add_typer(benchmark_app, name="benchmark")
report_app = typer.Typer(help="Export, inspect, and compare privacy-aware reports.")
app.add_typer(report_app, name="report")
receipt_app = typer.Typer(help="Prepare and verify externally signed DID receipts.")
app.add_typer(receipt_app, name="receipt")

DEFAULT_PROFILE = Path("profiles/flop-teaser-0.1.yaml")
DEFAULT_WORKLOAD = Path(__file__).resolve().parent / "workloads" / "smoke-v1.json"


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


@app.command()
def serve(
    host: Annotated[
        str,
        typer.Option("--host", help="Literal loopback address (127.0.0.1 or ::1)."),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", min=1024, max=65535, help="Local dashboard port."),
    ] = 4173,
) -> None:
    """Serve the secured local API and built dashboard on loopback."""

    try:
        bind_host = validate_bind_host(host)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--host") from exc
    if not (DEFAULT_WEB_DIST / "index.html").is_file():
        typer.echo("Dashboard assets are missing; run the web build first.", err=True)
        raise typer.Exit(code=2)
    import uvicorn

    display_host = f"[{bind_host}]" if ":" in bind_host else bind_host
    typer.echo(f"FlopBench dashboard: http://{display_host}:{port}")
    uvicorn.run(create_app(), host=bind_host, port=port, log_level="warning")


class OutputFormat(StrEnum):
    JSON = "json"


class CheckOutputFormat(StrEnum):
    TERMINAL = "terminal"
    JSON = "json"


class BenchmarkAdapterName(StrEnum):
    MOCK = "mock"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai-compatible"


class ReportOutputFormat(StrEnum):
    JSON = "json"
    HTML = "html"
    TERMINAL = "terminal"


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


@benchmark_app.command("run")
def benchmark_run(
    adapter_name: Annotated[
        BenchmarkAdapterName,
        typer.Option("--adapter", help="mock, ollama, or openai-compatible."),
    ] = BenchmarkAdapterName.MOCK,
    model: Annotated[
        str | None,
        typer.Option("--model", help="Runtime model name."),
    ] = None,
    workload_path: Annotated[
        Path,
        typer.Option("--workload", help="Versioned workload JSON file."),
    ] = DEFAULT_WORKLOAD,
    endpoint_url: Annotated[
        str | None,
        typer.Option("--endpoint", help="Explicit runtime base URL."),
    ] = None,
    allow_host: Annotated[
        list[str] | None,
        typer.Option("--allow-host", help="Exact external endpoint host allowlist entry."),
    ] = None,
    approve_external: Annotated[
        bool,
        typer.Option("--approve-external", help="Approve the allowlisted external endpoint."),
    ] = False,
    model_digest: Annotated[
        str | None,
        typer.Option("--model-digest", help="Required SHA-256 for OpenAI-compatible models."),
    ] = None,
    runtime_version: Annotated[
        str,
        typer.Option("--runtime-version", help="OpenAI-compatible runtime version label."),
    ] = "unknown",
    api_key_env: Annotated[
        str,
        typer.Option("--api-key-env", help="Environment variable holding an optional API key."),
    ] = "FLOPBENCH_OPENAI_API_KEY",
    timeout: Annotated[
        float,
        typer.Option("--timeout", min=0.1, max=600.0, help="Per-request timeout in seconds."),
    ] = 60.0,
    measure_vram: Annotated[
        bool,
        typer.Option("--measure-vram/--no-measure-vram", help="Sample NVIDIA VRAM per request."),
    ] = True,
    gpu_index: Annotated[
        int,
        typer.Option("--gpu-index", min=0, help="NVIDIA device index for VRAM sampling."),
    ] = 0,
) -> None:
    """Run warmups and measured requests, emitting a strict v2 JSON report."""

    try:
        workload = load_workload(workload_path)
        adapter: DeterministicMockAdapter | OllamaAdapter | OpenAICompatibleAdapter
        if adapter_name is BenchmarkAdapterName.MOCK:
            if endpoint_url is not None:
                raise typer.BadParameter("mock adapter does not accept --endpoint")
            adapter = DeterministicMockAdapter()
            observer = None
            selected_model = model or "fixture-model"
        else:
            default_endpoint = (
                "http://127.0.0.1:11434"
                if adapter_name is BenchmarkAdapterName.OLLAMA
                else "http://127.0.0.1:8000/v1"
            )
            endpoint = validate_endpoint(
                endpoint_url or default_endpoint,
                allow_external=approve_external,
                allowlist=tuple(allow_host or ()),
            )
            typer.echo(
                f"Runtime target: {endpoint.scheme}://{endpoint.authority}{endpoint.base_path} "
                f"({endpoint.scope}); redirects disabled",
                err=True,
            )
            if adapter_name is BenchmarkAdapterName.OLLAMA:
                adapter = OllamaAdapter(endpoint)
                selected_model = model or "llama3.2:3b"
            else:
                if model is None:
                    raise typer.BadParameter("--model is required for openai-compatible adapter")
                if model_digest is None:
                    raise typer.BadParameter(
                        "--model-digest is required for openai-compatible adapter"
                    )
                adapter = OpenAICompatibleAdapter(
                    endpoint,
                    model_digest=model_digest,
                    runtime_version=runtime_version,
                    api_key=os.environ.get(api_key_env),
                )
                selected_model = model
            observer = NvidiaVramObserver(device_index=gpu_index) if measure_vram else None
        report = run_benchmark(
            adapter,
            workload,
            selected_model,
            timeout_seconds=timeout,
            vram_observer=observer,
        )
    except ValidationError as exc:
        typer.echo(
            json.dumps(
                {
                    "code": "benchmark.configuration_invalid",
                    "message": "Benchmark configuration is invalid",
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            err=True,
        )
        raise typer.Exit(code=2) from exc
    except (AdapterError, EndpointError, WorkloadError, BenchmarkCancelledError) as exc:
        code = getattr(exc, "code", "benchmark.cancelled")
        typer.echo(
            json.dumps({"code": code, "message": str(exc)}, separators=(",", ":"), sort_keys=True),
            err=True,
        )
        raise typer.Exit(code=2) from exc
    except KeyboardInterrupt as exc:
        typer.echo(
            '{"code":"benchmark.cancelled","message":"Benchmark cancelled by user"}',
            err=True,
        )
        raise typer.Exit(code=130) from exc
    typer.echo(canonical_benchmark_json(report))
    if any(run.outcome == "cancelled" for run in report.runs):
        raise typer.Exit(code=130)


def _report_failure(exc: ReportError) -> Never:
    typer.echo(
        json.dumps({"code": exc.code, "message": str(exc)}, separators=(",", ":"), sort_keys=True),
        err=True,
    )
    raise typer.Exit(code=2) from exc


@report_app.command("export")
def report_export(
    source: Annotated[Path, typer.Argument(help="Source FlopBench JSON report.")],
    privacy: Annotated[
        PrivacyLevel, typer.Option("--privacy", help="private, support, or public disclosure.")
    ] = PrivacyLevel.PRIVATE,
    output_format: Annotated[
        ReportOutputFormat, typer.Option("--format", help="json, html, or terminal.")
    ] = ReportOutputFormat.JSON,
    output: Annotated[
        Path | None, typer.Option("--output", help="Write a new output file.")
    ] = None,
    profile_path: Annotated[
        Path | None, typer.Option("--profile", help="Bind a benchmark to this source profile.")
    ] = None,
    confirm_preview: Annotated[
        str | None,
        typer.Option(
            "--confirm-preview",
            help="For public writes, the exact digest shown by a prior preview.",
        ),
    ] = None,
) -> None:
    """Preview or export a deterministic, redacted report."""

    try:
        loaded_profile = load_profile(profile_path) if profile_path is not None else None
        exported = create_export(load_report(source), privacy, profile=loaded_profile)
        if output_format is ReportOutputFormat.JSON:
            rendered = render_json(exported)
        elif output_format is ReportOutputFormat.HTML:
            rendered = render_html(exported)
        else:
            rendered = render_terminal(exported).encode("utf-8")
        if output is None:
            typer.echo(rendered.decode("utf-8"))
            typer.echo(f"Preview digest: {exported.digest.value}", err=True)
            return
        if privacy is PrivacyLevel.PUBLIC and confirm_preview != exported.digest.value:
            raise ReportError(
                "report.public_preview_required",
                "Public output requires its exact preview digest",
            )
        write_new_file(output, rendered)
        typer.echo(f"Wrote {output.name}; digest sha256:{exported.digest.value}")
    except ProfileLoadError as exc:
        _report_failure(ReportError(str(exc.code), str(exc)))
    except ReportError as exc:
        _report_failure(exc)
    except ValueError:
        _report_failure(
            ReportError("report.secret_detected", "Report contains credential-like material")
        )


@report_app.command("diff")
def report_diff(
    left: Annotated[Path, typer.Argument(help="First report export.")],
    right: Annotated[Path, typer.Argument(help="Second report export.")],
) -> None:
    """Show a bounded structural diff between verified exports."""

    try:
        result = diff_exports(load_export(left), load_export(right))
    except ReportError as exc:
        _report_failure(exc)
    typer.echo(canonical_bytes(result.model_dump(mode="json", by_alias=True)).decode("utf-8"))


@report_app.command("compare")
def report_compare(
    left: Annotated[Path, typer.Argument(help="First benchmark export.")],
    right: Annotated[Path, typer.Argument(help="Second benchmark export.")],
) -> None:
    """Compare only benchmarks with identical methodology context."""

    try:
        result = compare_benchmarks(load_export(left), load_export(right))
    except ReportError as exc:
        _report_failure(exc)
    typer.echo(canonical_bytes(result.model_dump(mode="json", by_alias=True)).decode("utf-8"))


def _receipt_failure(exc: ReceiptError | ReportError) -> Never:
    typer.echo(
        json.dumps({"code": exc.code, "message": str(exc)}, separators=(",", ":"), sort_keys=True),
        err=True,
    )
    raise typer.Exit(code=2) from exc


def _signed_at(value: str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReceiptError(
            "receipt.invalid_signed_at", "signed-at must be an RFC3339 UTC timestamp"
        ) from exc
    offset = parsed.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise ReceiptError(
            "receipt.invalid_signed_at", "signed-at must be an RFC3339 UTC timestamp"
        )
    return parsed


@receipt_app.command("prepare")
def receipt_prepare(
    report: Annotated[Path, typer.Argument(help="Verified FlopBench report export.")],
    did: Annotated[str, typer.Option("--did", help="Existing Ed25519 did:key identifier.")],
    signed_at_text: Annotated[
        str | None,
        typer.Option("--signed-at", help="Optional RFC3339 UTC local signing declaration."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", help="Write a new signing-request JSON file.")
    ] = None,
) -> None:
    """Prepare JCS bytes for a signer that runs outside FlopBench."""

    try:
        request = prepare_receipt(load_export(report), did, _signed_at(signed_at_text))
        rendered = render_contract(request)
        if output is not None:
            write_new_file(output, rendered)
    except (ReceiptError, ReportError) as exc:
        _receipt_failure(exc)
    typer.echo(f"Report digest: sha256:{request.payload.report_sha256}", err=True)
    typer.echo(f"Signer DID: {request.payload.did}", err=True)
    typer.echo(f"Signing payload: sha256:{request.payload_sha256}", err=True)
    typer.echo(
        "Use your existing DID. FlopBench does not generate, read, or store private keys.",
        err=True,
    )
    typer.echo(
        "signed_at is a local declaration, not a trusted timestamp or identity proof.", err=True
    )
    if output is None:
        typer.echo(rendered.decode("utf-8"), nl=False)
    else:
        typer.echo(f"Wrote {output.name}; pass its payload to an external Ed25519 signer.")


@receipt_app.command("create")
def receipt_create(
    request_path: Annotated[Path, typer.Argument(help="Prepared signing-request JSON file.")],
    signature: Annotated[
        str | None,
        typer.Option("--signature", help="External canonical base64url Ed25519 signature."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", help="Write a new receipt JSON file.")
    ] = None,
) -> None:
    """Create a receipt from an external signature; cancellation writes nothing."""

    if signature is None:
        typer.echo("No signature supplied; receipt creation cancelled.")
        return
    try:
        receipt = create_receipt(load_signing_request(request_path), signature)
        rendered = render_contract(receipt)
        if output is not None:
            write_new_file(output, rendered)
    except (ReceiptError, ReportError) as exc:
        _receipt_failure(exc)
    if output is None:
        typer.echo(rendered.decode("utf-8"), nl=False)
    else:
        typer.echo(f"Wrote {output.name}; external signature verified.")


@receipt_app.command("verify")
def receipt_verify(
    report: Annotated[Path, typer.Argument(help="Verified FlopBench report export.")],
    receipt_path: Annotated[Path, typer.Argument(help="Receipt JSON file.")],
) -> None:
    """Verify the report binding and DID signature using public data only."""

    try:
        result = verify_receipt(load_export(report), load_receipt(receipt_path))
    except (ReceiptError, ReportError) as exc:
        _receipt_failure(exc)
    typer.echo(render_contract(result).decode("utf-8"), nl=False)
