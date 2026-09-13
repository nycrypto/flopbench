"""Verify a built wheel in a clean, disposable virtual environment."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
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
                    "from flopbench.webapp import DEFAULT_PROFILE,DEFAULT_WEB_DIST,FIXTURES;"
                    "assert DEFAULT_PROFILE.is_file();"
                    "assert (DEFAULT_WEB_DIST/'index.html').is_file();"
                    "assert FIXTURES['cpu-only'].is_file();"
                    "print(FIXTURES['cpu-only'])"
                ),
            ],
            cwd=root,
            capture=True,
        )
        fixture = Path(path_result.stdout.strip())
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
        json.loads(probe_path.read_text(encoding="utf-8"))
        export_path = reports / "private-export.json"
        run(
            [
                str(python),
                "-m",
                "flopbench",
                "report",
                "export",
                str(probe_path),
                "--privacy",
                "private",
                "--output",
                str(export_path),
            ],
            cwd=root,
        )
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

    test_id = "S10-T01" if sys.platform == "win32" else "S10-T02"
    print(f"{test_id}/S10-T03 passed: clean install, packaged data, and safe uninstall")


if __name__ == "__main__":
    main()
