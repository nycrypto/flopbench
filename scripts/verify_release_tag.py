"""Validate that a stable release tag matches every versioned release document."""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path

SEMVER = re.compile(r"^v(?P<version>(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*))$")


def verify(root: Path, tag: str) -> list[str]:
    match = SEMVER.fullmatch(tag)
    if match is None:
        return ["release tag must be a stable vMAJOR.MINOR.PATCH SemVer"]
    version = match.group("version")
    with (root / "pyproject.toml").open("rb") as stream:
        package_version = tomllib.load(stream)["project"]["version"]
    source = (root / "src" / "flopbench" / "__init__.py").read_text(encoding="utf-8")
    notes = root / "docs" / "releases" / f"v{version}.md"
    checklist = root / "docs" / f"release-checklist-v{version}.md"
    errors: list[str] = []
    if package_version != version:
        errors.append(f"pyproject version {package_version!r} does not match {tag}")
    if f'__version__ = "{version}"' not in source:
        errors.append("runtime version does not match release tag")
    if not notes.is_file():
        errors.append(f"release notes are missing: {notes.relative_to(root)}")
    if not checklist.is_file():
        errors.append(f"release checklist is missing: {checklist.relative_to(root)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    arguments = parser.parse_args()
    errors = verify(arguments.root.resolve(), arguments.tag)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Release tag {arguments.tag} matches package, runtime, notes, and checklist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
