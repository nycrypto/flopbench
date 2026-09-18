"""Fail when detect-secrets finds a candidate not present in the reviewed baseline."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

EXCLUDED = re.compile(
    r"^(?:\.secrets\.baseline|pnpm-lock\.yaml|requirements/.*\.txt|"
    r"src/flopbench/web_dist/)"
)
ROOT = Path(__file__).resolve().parents[1]


def tracked_files() -> list[str]:
    completed = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={ROOT.as_posix()}",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        path
        for raw in completed.stdout.splitlines()
        if (path := raw.replace("\\", "/")) and EXCLUDED.match(path) is None
    ]


def scan() -> dict[str, Any]:
    executable = shutil.which("detect-secrets")
    if executable is None:
        sibling = Path(sys.executable).with_name(
            "detect-secrets.exe" if sys.platform == "win32" else "detect-secrets"
        )
        if not sibling.is_file():
            raise RuntimeError("detect-secrets executable is unavailable")
        executable = str(sibling)
    command = [executable, "scan", *tracked_files()]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("detect-secrets output is not an object")
    return value


def candidates(payload: dict[str, Any]) -> set[tuple[str, str, str]]:
    results = payload.get("results")
    if not isinstance(results, dict):
        raise RuntimeError("detect-secrets output has no results object")
    found: set[tuple[str, str, str]] = set()
    for path, entries in results.items():
        if not isinstance(path, str) or not isinstance(entries, list):
            raise RuntimeError("detect-secrets output is malformed")
        for entry in entries:
            if not isinstance(entry, dict):
                raise RuntimeError("detect-secrets entry is malformed")
            secret_hash = entry.get("hashed_secret")
            secret_type = entry.get("type")
            if isinstance(secret_hash, str) and isinstance(secret_type, str):
                found.add((path.replace("\\", "/"), secret_type, secret_hash))
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--write-baseline", action="store_true")
    arguments = parser.parse_args()
    current = scan()
    if arguments.write_baseline:
        with arguments.baseline.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(current, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        print(f"Baseline written with {len(candidates(current))} candidates")
        return
    baseline_value = json.loads(arguments.baseline.read_text(encoding="utf-8"))
    if not isinstance(baseline_value, dict):
        raise RuntimeError("Secret baseline is not an object")
    unexpected = sorted(candidates(current) - candidates(baseline_value))
    if unexpected:
        paths = sorted({item[0] for item in unexpected})
        raise RuntimeError(f"Unreviewed secret candidates detected in: {paths}")
    print("S10-T07 passed: no unreviewed secret candidates")


if __name__ == "__main__":
    main()
