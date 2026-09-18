"""Fail when a repository Markdown link points outside the tree or is missing."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

LINK = re.compile(r"!?\[[^\]]*\]\((?P<target><[^>]+>|[^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)")
IGNORED_PARTS = {
    ".git",
    ".venv",
    ".nox",
    "node_modules",
    "dist",
    ".acceptance",
    ".cache",
}


def markdown_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if not any(part in IGNORED_PARTS for part in path.relative_to(root).parts)
    )


def broken_links(root: Path, paths: list[Path] | None = None) -> list[str]:
    """Return deterministic diagnostics for unsafe or missing local links."""

    repository = root.resolve()
    problems: list[str] = []
    for document in paths or markdown_files(repository):
        text = document.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in LINK.finditer(line):
                raw_target = match.group("target").strip("<>")
                parsed = urlsplit(raw_target)
                if parsed.scheme in {"http", "https", "mailto"} or raw_target.startswith("#"):
                    continue
                if parsed.scheme or parsed.netloc:
                    location = f"{document.relative_to(repository)}:{line_number}"
                    problems.append(f"{location}: unsupported link {raw_target}")
                    continue
                # URL separators are portable; rebuild the path without treating a leading slash
                # as a drive/root escape on Windows.
                parts = [part for part in unquote(parsed.path).split("/") if part not in {"", "."}]
                target = (document.parent / Path(*parts)).resolve()
                try:
                    target.relative_to(repository)
                except ValueError:
                    location = f"{document.relative_to(repository)}:{line_number}"
                    problems.append(f"{location}: link escapes repository {raw_target}")
                    continue
                if not target.exists():
                    location = f"{document.relative_to(repository)}:{line_number}"
                    problems.append(f"{location}: missing target {raw_target}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    arguments = parser.parse_args()
    problems = broken_links(arguments.root)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"Markdown links valid across {len(markdown_files(arguments.root.resolve()))} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
