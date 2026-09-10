"""Loopback-only FastAPI composition root for the local dashboard."""

from __future__ import annotations

import ipaddress
import secrets
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated, Literal, cast
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from flopbench import __version__
from flopbench.benchmark.adapters import DeterministicMockAdapter
from flopbench.benchmark.engine import run_benchmark
from flopbench.benchmark.workload import load_workload
from flopbench.contracts import PrivacyLevel, Role, StrictModel
from flopbench.probe.models import ProbeReport
from flopbench.probe.service import run_fixture_probe, run_live_probe
from flopbench.profile_loader import load_profile
from flopbench.readiness.engine import evaluate_readiness
from flopbench.reporting.service import create_export, load_report


def _discover_project_root() -> Path:
    """Prefer the source checkout until Stage 10 packages data and web assets."""

    working_directory = Path.cwd().resolve()
    if (working_directory / "profiles" / "flop-teaser-0.1.yaml").is_file():
        return working_directory
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = _discover_project_root()
DEFAULT_PROFILE = PROJECT_ROOT / "profiles" / "flop-teaser-0.1.yaml"
DEFAULT_WORKLOAD = Path(__file__).resolve().parent / "workloads" / "smoke-v1.json"
DEFAULT_WEB_DIST = PROJECT_ROOT / "apps" / "web" / "dist"
FIXTURES = {
    "cpu-only": PROJECT_ROOT / "fixtures" / "hardware" / "cpu-only.json",
    "miner": PROJECT_ROOT / "fixtures" / "hardware" / "miner-vram-15-99gb.json",
    "unsupported": PROJECT_ROOT / "fixtures" / "hardware" / "unsupported-gpu.json",
}
REPORT_FIXTURE = PROJECT_ROOT / "fixtures" / "reports" / "benchmark-v2-mock.json"


class ProbeRequest(StrictModel):
    fixture: Literal["live", "cpu-only", "miner", "unsupported"] = "live"


class BenchmarkRequest(StrictModel):
    adapter: Literal["mock"] = "mock"
    model_name: Annotated[str, Field(min_length=1, max_length=200)] = "fixture-model"


class ReportPreviewRequest(StrictModel):
    privacy: Literal["private", "support", "public"] = "public"


def validate_bind_host(host: str) -> str:
    """Accept literal loopback addresses only; remote binding is not a v1 feature."""

    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError("host must be a literal loopback address") from exc
    if not address.is_loopback:
        raise ValueError("remote binding is not supported")
    return host


def _request_host(header: str) -> tuple[str, int | None] | None:
    try:
        parsed = urlsplit(f"//{header}")
        if parsed.hostname is None:
            return None
        return parsed.hostname, parsed.port
    except ValueError:
        return None


def _is_loopback_host(header: str) -> bool:
    parsed = _request_host(header)
    if parsed is None:
        return False
    try:
        return ipaddress.ip_address(parsed[0]).is_loopback
    except ValueError:
        return False


def _origin_matches(origin: str, host_header: str) -> bool:
    request_host = _request_host(host_header)
    try:
        parsed = urlsplit(origin)
        origin_host = parsed.hostname
        if parsed.scheme not in {"http", "https"} or origin_host is None:
            return False
        if not ipaddress.ip_address(origin_host).is_loopback:
            return False
        origin_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return False
    if request_host is None or origin_host != request_host[0]:
        return False
    return request_host[1] is None or request_host[1] == origin_port


def _probe_for(request: ProbeRequest) -> ProbeReport:
    if request.fixture == "live":
        return run_live_probe(PrivacyLevel.PUBLIC)
    return run_fixture_probe(FIXTURES[request.fixture], PrivacyLevel.PUBLIC)


def _as_json(model: BaseModel) -> dict[str, object]:
    return cast(dict[str, object], model.model_dump(mode="json", by_alias=True))


def create_app(
    *,
    token: str | None = None,
    static_dir: Path | None = DEFAULT_WEB_DIST,
) -> FastAPI:
    """Create one process-local app with an unlogged startup token."""

    startup_token = token or secrets.token_urlsafe(32)
    app = FastAPI(
        title="FlopBench local API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.startup_token = startup_token
    app.state.benchmarks = {}

    @app.middleware("http")
    async def local_boundary(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        host_header = request.headers.get("host", "")
        if not _is_loopback_host(host_header):
            return JSONResponse({"code": "api.host_rejected"}, status_code=400)
        if request.url.path.startswith("/api/v1"):
            origin = request.headers.get("origin")
            if origin is not None and not _origin_matches(origin, host_header):
                return JSONResponse({"code": "api.origin_rejected"}, status_code=403)
            if request.url.path != "/api/v1/health":
                supplied = request.headers.get("x-flopbench-token", "")
                if not secrets.compare_digest(supplied, startup_token):
                    return JSONResponse({"code": "api.token_rejected"}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__, "scope": "loopback"}

    @app.get("/api/v1/profiles")
    def profiles() -> dict[str, object]:
        profile = load_profile(DEFAULT_PROFILE)
        return {
            "profiles": [
                {
                    **profile.profile.model_dump(mode="json", by_alias=True),
                    "sha256": profile.sha256,
                }
            ]
        }

    @app.post("/api/v1/probe")
    def probe(payload: ProbeRequest) -> object:
        return _as_json(_probe_for(payload))

    @app.post("/api/v1/checks/{role}")
    def checks(role: Role, payload: ProbeRequest) -> dict[str, object]:
        probe_report = _probe_for(payload)
        readiness = evaluate_readiness(probe_report, load_profile(DEFAULT_PROFILE), role)
        return {"probe": _as_json(probe_report), "readiness": _as_json(readiness)}

    @app.get("/api/v1/benchmarks")
    def benchmarks() -> dict[str, object]:
        return {"benchmarks": list(app.state.benchmarks.values())}

    @app.post("/api/v1/benchmarks", status_code=201)
    def benchmark(payload: BenchmarkRequest) -> object:
        report = run_benchmark(
            DeterministicMockAdapter(),
            load_workload(DEFAULT_WORKLOAD),
            payload.model_name,
        )
        serialized = _as_json(report)
        app.state.benchmarks[str(report.benchmark_id)] = serialized
        return serialized

    @app.get("/api/v1/benchmarks/{benchmark_id}")
    def benchmark_detail(benchmark_id: str) -> object:
        try:
            return app.state.benchmarks[benchmark_id]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="benchmark not found") from exc

    @app.post("/api/v1/reports/preview")
    def report_preview(payload: ReportPreviewRequest) -> dict[str, object]:
        privacy = PrivacyLevel(payload.privacy)
        exported = create_export(load_report(REPORT_FIXTURE), privacy)
        hidden = (
            ["host identifiers", "local paths", "access tokens", "raw response content"]
            if privacy is not PrivacyLevel.PRIVATE
            else []
        )
        return {"export": _as_json(exported), "redacted_fields": hidden}

    resolved_static = static_dir.resolve() if static_dir is not None else None
    if resolved_static is not None and (resolved_static / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=resolved_static / "assets"), name="assets")

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> HTMLResponse:
        if resolved_static is None or not (resolved_static / "index.html").is_file():
            raise HTTPException(status_code=503, detail="dashboard assets are not built")
        source = (resolved_static / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(source.replace("__FLOPBENCH_TOKEN__", startup_token))

    @app.get("/{path:path}", response_class=FileResponse)
    def static_file(path: str) -> FileResponse:
        if resolved_static is None:
            raise HTTPException(status_code=404)
        candidate = (resolved_static / path).resolve()
        if resolved_static not in candidate.parents or not candidate.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(candidate)

    return app
