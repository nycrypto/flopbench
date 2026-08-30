from __future__ import annotations

from pathlib import Path

import pytest

from flopbench.contracts import ResultStatus
from flopbench.validator_doctor.disk import run_disk_test
from flopbench.validator_doctor.models import TestLimits as DoctorLimits


def test_symlink_temp_root_is_rejected_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Path.is_symlink

    def is_symlink(path: Path) -> bool:
        return path == tmp_path or original(path)

    monkeypatch.setattr(Path, "is_symlink", is_symlink)
    result = run_disk_test(DoctorLimits(disk_bytes=1024, disk_chunk_bytes=1024), temp_root=tmp_path)

    assert result.status is ResultStatus.UNSUPPORTED
    assert list(tmp_path.iterdir()) == []
