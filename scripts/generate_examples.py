"""Generate the byte-stable public examples shipped with FlopBench v1."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel

from flopbench.benchmark.adapters import DeterministicMockAdapter
from flopbench.benchmark.engine import run_benchmark
from flopbench.benchmark.workload import load_workload
from flopbench.contracts import PrivacyLevel, Role
from flopbench.probe.service import run_fixture_probe
from flopbench.profile_loader import load_profile
from flopbench.readiness.engine import evaluate_readiness
from flopbench.reporting.canonical import canonical_bytes
from flopbench.reporting.render import render_html, render_json
from flopbench.reporting.service import create_export
from flopbench.simulator import SimulationScenario, build_session_request, run_simulation

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "examples" / "reports"
FIXED_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _contract_bytes(value: BaseModel) -> bytes:
    return canonical_bytes(value.model_dump(mode="json", by_alias=True)) + b"\n"


def example_files() -> dict[str, bytes]:
    profile = load_profile(ROOT / "profiles" / "flop-teaser-0.1.yaml")
    miner_probe = run_fixture_probe(
        ROOT / "fixtures" / "hardware" / "linux-nvidia-16gb.json", PrivacyLevel.PUBLIC
    )
    validator_probe = run_fixture_probe(
        ROOT / "fixtures" / "hardware" / "windows-nvidia-24gb.json", PrivacyLevel.PUBLIC
    )
    miner = evaluate_readiness(miner_probe, profile, Role.MINER)
    validator = evaluate_readiness(validator_probe, profile, Role.VALIDATOR)
    benchmark = run_benchmark(
        DeterministicMockAdapter(),
        load_workload(ROOT / "src" / "flopbench" / "workloads" / "smoke-v1.json"),
        "flopbench-demo-model",
        benchmark_id=UUID("00000000-0000-5000-8000-000000000011"),
        now=lambda: FIXED_TIME,
        vram_observer=None,
    )
    agent = run_simulation(build_session_request(SimulationScenario.SUCCESS, seed=11))
    challenge = run_simulation(
        build_session_request(SimulationScenario.VALIDATOR_MISMATCH, seed=11)
    )
    public_export = create_export(miner, PrivacyLevel.PUBLIC)
    return {
        "agent-simulation.json": _contract_bytes(agent),
        "agent-validator-challenge.json": _contract_bytes(challenge),
        "miner-readiness.public.json": _contract_bytes(miner),
        "mock-benchmark.json": _contract_bytes(benchmark),
        "public-readiness-report.html": render_html(public_export),
        "public-readiness-report.json": render_json(public_export) + b"\n",
        "validator-readiness.public.json": _contract_bytes(validator),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    expected = example_files()
    if arguments.check:
        failures = [
            name
            for name, content in expected.items()
            if not (arguments.output / name).is_file()
            or (arguments.output / name).read_bytes() != content
        ]
        if failures:
            print("Stale or missing examples: " + ", ".join(failures))
            return 1
        print(f"Verified {len(expected)} deterministic example files.")
        return 0
    arguments.output.mkdir(parents=True, exist_ok=True)
    for name, content in expected.items():
        (arguments.output / name).write_bytes(content)
    print(f"Generated {len(expected)} example files in {arguments.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
