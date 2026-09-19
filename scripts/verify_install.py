"""Verify a built wheel in a clean, disposable virtual environment."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


def run(
    command: list[str], *, cwd: Path, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
        env={**os.environ, "PYTHONUTF8": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"},
    )


def environment_python(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def verify_wheel_contents(wheel: Path) -> None:
    required_exact = {
        "flopbench/data/profiles/flop-teaser-0.1.yaml",
        "flopbench/data/fixtures/hardware/cpu-only.json",
        "flopbench/data/fixtures/reports/benchmark-v2-mock.json",
        "flopbench/data/schemas/report-export-v1.schema.json",
        "flopbench/web_dist/index.html",
        "flopbench/workloads/smoke-v1.json",
        "flopbench/py.typed",
    }
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    missing = sorted(required_exact - names)
    if missing:
        raise RuntimeError(f"Wheel package data is incomplete: {missing}")
    if not any(name.startswith("flopbench/web_dist/assets/") for name in names):
        raise RuntimeError("Wheel contains no built dashboard assets")


def parse_json_output(
    completed: subprocess.CompletedProcess[str], schema: str
) -> dict[str, object]:
    value = json.loads(completed.stdout)
    if not isinstance(value, dict) or value.get("schema") != schema:
        raise RuntimeError(f"Unexpected CLI contract; wanted {schema}")
    return value


def verify_loopback_server(python: Path, root: Path, expected_version: str) -> None:
    """Start the installed dashboard, check health, and always stop its process."""

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [str(python), "-m", "flopbench", "serve", "--port", str(port)],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise RuntimeError(f"Installed dashboard exited early: {stdout} {stderr}")
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/v1/health", timeout=1
                ) as response:
                    health = json.loads(response.read())
                if health != {
                    "status": "ok",
                    "version": expected_version,
                    "scope": "loopback",
                }:
                    raise RuntimeError("Installed dashboard health contract is invalid")
                return
            except ConnectionError, TimeoutError, urllib.error.URLError:
                time.sleep(0.1)
        raise RuntimeError("Installed dashboard did not become healthy")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--expected-version", required=True)
    arguments = parser.parse_args()
    wheel = arguments.wheel.resolve(strict=True)
    runtime_lock = arguments.runtime_lock.resolve(strict=True)
    verify_wheel_contents(wheel)

    with tempfile.TemporaryDirectory(prefix="flopbench-clean-install-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        reports = root / "user-reports"
        reports.mkdir()
        run([sys.executable, "-m", "venv", str(environment)], cwd=root)
        python = environment_python(environment)
        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--require-hashes",
                "-r",
                str(runtime_lock),
            ],
            cwd=root,
        )
        run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)], cwd=root)

        version = run([str(python), "-m", "flopbench", "--version"], cwd=root, capture=True)
        expected = f"flopbench {arguments.expected_version}"
        if version.stdout.strip() != expected:
            raise RuntimeError(f"Installed version mismatch: {version.stdout.strip()!r}")

        path_result = run(
            [
                str(python),
                "-c",
                (
                    "import json;"
                    "from flopbench.webapp import DEFAULT_PROFILE,DEFAULT_WEB_DIST,FIXTURE_ROOT;"
                    "assert DEFAULT_PROFILE.is_file();"
                    "assert (DEFAULT_WEB_DIST/'index.html').is_file();"
                    "print(json.dumps({'fixtures':str(FIXTURE_ROOT)}))"
                ),
            ],
            cwd=root,
            capture=True,
        )
        locations = json.loads(path_result.stdout)
        fixture_root = Path(locations["fixtures"])
        fixture = fixture_root / "hardware" / "cpu-only.json"
        probe = run(
            [
                str(python),
                "-m",
                "flopbench",
                "probe",
                "--fixture",
                str(fixture),
                "--privacy",
                "private",
            ],
            cwd=root,
            capture=True,
        )
        probe_path = reports / "probe.json"
        probe_path.write_text(probe.stdout, encoding="utf-8", newline="\n")
        parse_json_output(probe, "flopbench-probe-v1")

        miner = run(
            [
                str(python),
                "-m",
                "flopbench",
                "check",
                "miner",
                "--fixture",
                str(fixture_root / "hardware" / "linux-nvidia-16gb.json"),
                "--format",
                "json",
            ],
            cwd=root,
            capture=True,
        )
        parse_json_output(miner, "flopbench-readiness-report-v1")
        miner_path = reports / "miner.json"
        miner_path.write_text(miner.stdout, encoding="utf-8", newline="\n")

        validator = run(
            [
                str(python),
                "-m",
                "flopbench",
                "check",
                "validator",
                "--fixture",
                str(fixture_root / "hardware" / "windows-nvidia-24gb.json"),
                "--format",
                "json",
            ],
            cwd=root,
            capture=True,
        )
        parse_json_output(validator, "flopbench-readiness-report-v1")

        doctor = run(
            [
                str(python),
                "-m",
                "flopbench",
                "doctor",
                "validator",
                "--approve",
                "--fixture",
                str(fixture_root / "doctor" / "fast-disk.json"),
                "--format",
                "json",
            ],
            cwd=root,
            capture=True,
        )
        parse_json_output(doctor, "flopbench-validator-doctor-v1")

        benchmark = run(
            [
                str(python),
                "-m",
                "flopbench",
                "benchmark",
                "run",
                "--adapter",
                "mock",
                "--model",
                "flopbench-demo-model",
                "--no-measure-vram",
            ],
            cwd=root,
            capture=True,
        )
        parse_json_output(benchmark, "flopbench-benchmark-report-v2")

        for scenario, final_state in (("success", "settled"), ("validator-mismatch", "rejected")):
            simulation = run(
                [
                    str(python),
                    "-m",
                    "flopbench",
                    "simulate",
                    "run",
                    "--scenario",
                    scenario,
                    "--seed",
                    "11",
                ],
                cwd=root,
                capture=True,
            )
            simulation_value = parse_json_output(simulation, "flopbench-poui-simulation-v1")
            if simulation_value.get("final_state") != final_state:
                raise RuntimeError(f"Unexpected {scenario} final state")

        export_path = reports / "private-export.json"
        run(
            [
                str(python),
                "-m",
                "flopbench",
                "report",
                "export",
                str(miner_path),
                "--privacy",
                "private",
                "--output",
                str(export_path),
            ],
            cwd=root,
        )
        exported = parse_json_output(
            subprocess.CompletedProcess([], 0, export_path.read_text(encoding="utf-8"), ""),
            "flopbench-report-export-v1",
        )
        document = exported.get("document")
        if not isinstance(document, dict) or document.get("privacy_level") != "private":
            raise RuntimeError("Installed report export privacy contract is invalid")

        vector = json.loads(
            (fixture_root / "receipts" / "ed25519-rfc8032-test1.json").read_text(encoding="utf-8")
        )
        signing_request = reports / "signing-request.json"
        run(
            [
                str(python),
                "-m",
                "flopbench",
                "receipt",
                "prepare",
                str(export_path),
                "--did",
                vector["did"],
                "--signed-at",
                "2026-01-01T00:00:00Z",
                "--output",
                str(signing_request),
            ],
            cwd=root,
        )
        external_signature = run(
            [
                str(python),
                "-c",
                (
                    "import base64,json,sys;"
                    "from cryptography.hazmat.primitives.asymmetric.ed25519"
                    " import Ed25519PrivateKey;"
                    "request=json.load(open(sys.argv[1],encoding='utf-8'));"
                    "encoded=request['payload_base64url'];"
                    "message=base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4));"
                    "key=Ed25519PrivateKey.from_private_bytes(bytes.fromhex("
                    "'9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60'));"
                    "print(base64.urlsafe_b64encode(key.sign(message)).rstrip(b'=').decode())"
                ),
                str(signing_request),
            ],
            cwd=root,
            capture=True,
        ).stdout.strip()
        receipt_path = reports / "receipt.json"
        run(
            [
                str(python),
                "-m",
                "flopbench",
                "receipt",
                "create",
                str(signing_request),
                "--signature",
                external_signature,
                "--output",
                str(receipt_path),
            ],
            cwd=root,
        )
        verification = run(
            [
                str(python),
                "-m",
                "flopbench",
                "receipt",
                "verify",
                str(export_path),
                str(receipt_path),
            ],
            cwd=root,
            capture=True,
        )
        verified = parse_json_output(verification, "flopbench-receipt-verification-v1")
        if verified.get("valid") is not True:
            raise RuntimeError("Installed receipt verification failed")

        verify_loopback_server(python, root, arguments.expected_version)
        before = {path.name: path.read_bytes() for path in reports.iterdir()}
        run([str(python), "-m", "pip", "uninstall", "-y", "flopbench"], cwd=root)
        after = {path.name: path.read_bytes() for path in reports.iterdir()}
        if before != after:
            raise RuntimeError("Uninstall changed user-owned reports")
        probe_import = run(
            [
                str(python),
                "-c",
                "import importlib.util; assert importlib.util.find_spec('flopbench') is None",
            ],
            cwd=root,
        )
        if probe_import.returncode != 0:
            raise RuntimeError("FlopBench remained importable after uninstall")

    stage10_id = "S10-T01" if sys.platform == "win32" else "S10-T02"
    stage11_id = "S11-T01" if sys.platform == "win32" else "S11-T09"
    print(
        f"{stage10_id}/S10-T03/{stage11_id}/S11-T08 passed: "
        "clean install, packaged data, and safe uninstall"
    )


if __name__ == "__main__":
    main()
