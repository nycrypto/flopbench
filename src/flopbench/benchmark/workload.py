"""Load immutable UTF-8/LF benchmark workload definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, Strict, StrictInt, ValidationError

from flopbench.contracts import SemVer, StrictModel

MAX_WORKLOAD_BYTES = 256 * 1024


class WorkloadErrorCode(StrEnum):
    READ_ERROR = "benchmark.workload_read_error"
    TOO_LARGE = "benchmark.workload_too_large"
    INVALID_ENCODING = "benchmark.workload_invalid_encoding"
    INVALID_NEWLINE = "benchmark.workload_invalid_newline"
    INVALID = "benchmark.workload_invalid"


class WorkloadError(RuntimeError):
    def __init__(self, code: WorkloadErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class PromptCase(StrictModel):
    id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9.-]+$")]
    prompt: Annotated[str, Field(min_length=1, max_length=8192)]
    max_tokens: Annotated[int, Strict(), Field(gt=0, le=2048)]


class WorkloadDefinition(StrictModel):
    schema_id: Literal["flopbench-workload-v1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9.-]+$")]
    version: SemVer
    seed: StrictInt
    warmup_runs: Annotated[int, Strict(), Field(ge=0, le=20)]
    measured_runs: Annotated[int, Strict(), Field(gt=0, le=100)]
    prompts: Annotated[list[PromptCase], Field(min_length=1, max_length=100)]


@dataclass(frozen=True)
class LoadedWorkload:
    definition: WorkloadDefinition
    sha256: str
    byte_length: int


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def load_workload(path: Path, *, max_bytes: int = MAX_WORKLOAD_BYTES) -> LoadedWorkload:
    try:
        with path.open("rb") as stream:
            raw = stream.read(max_bytes + 1)
    except OSError as exc:
        raise WorkloadError(WorkloadErrorCode.READ_ERROR, "Workload could not be read") from exc
    if len(raw) > max_bytes:
        raise WorkloadError(WorkloadErrorCode.TOO_LARGE, "Workload exceeds the size limit")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise WorkloadError(WorkloadErrorCode.INVALID_ENCODING, "Workload must not use a BOM")
    if b"\r" in raw:
        raise WorkloadError(WorkloadErrorCode.INVALID_NEWLINE, "Workload must use LF newlines")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise WorkloadError(WorkloadErrorCode.INVALID_ENCODING, "Workload must be UTF-8") from exc
    try:
        definition = WorkloadDefinition.model_validate(
            json.loads(text, object_pairs_hook=_unique_object)
        )
    except (ValueError, ValidationError, RecursionError) as exc:
        raise WorkloadError(WorkloadErrorCode.INVALID, "Workload is invalid") from exc
    return LoadedWorkload(
        definition=definition, sha256=sha256(raw).hexdigest(), byte_length=len(raw)
    )
