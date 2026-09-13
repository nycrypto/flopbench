"""Synchronize or verify the built dashboard copied into the Python package."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "apps" / "web" / "dist"
TARGET = ROOT / "src" / "flopbench" / "web_dist"


def digest_tree(root: Path) -> dict[str, str]:
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError(f"Dashboard directory is missing or unsafe: {root}")
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"Dashboard assets may not contain symlinks: {path}")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if "index.html" not in files or not any(name.startswith("assets/") for name in files):
        names = ", ".join(files) if files else "<none>"
        raise RuntimeError(f"Dashboard build is incomplete in {root}: {names}")
    return files


def synchronize() -> None:
    digest_tree(SOURCE)
    expected_parent = (ROOT / "src" / "flopbench").resolve()
    if TARGET.parent.resolve() != expected_parent:
        raise RuntimeError("Refusing to write outside the FlopBench package")
    with tempfile.TemporaryDirectory(prefix="flopbench-web-assets-", dir=TARGET.parent) as temp:
        staged = Path(temp) / "web_dist"
        shutil.copytree(SOURCE, staged)
        if TARGET.exists():
            if TARGET.is_symlink() or not TARGET.is_dir():
                raise RuntimeError("Packaged dashboard target is unsafe")
            shutil.rmtree(TARGET)
        staged.rename(TARGET)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.check:
        if digest_tree(SOURCE) != digest_tree(TARGET):
            raise RuntimeError("Packaged dashboard assets are stale; run sync_web_assets.py")
        print("Packaged dashboard assets match the Vite build")
        return
    synchronize()
    print("Packaged dashboard assets synchronized")


if __name__ == "__main__":
    main()
