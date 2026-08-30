"""Deterministically export the committed Stage 1 JSON Schemas."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from flopbench.contracts import BenchmarkReport, ReadinessReport, Receipt, SourceProfile

SCHEMA_BASE = "https://schemas.flopbench.dev/v1"
SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "profile-v1.schema.json": SourceProfile,
    "readiness-report-v1.schema.json": ReadinessReport,
    "benchmark-report-v1.schema.json": BenchmarkReport,
    "receipt-v1.schema.json": Receipt,
}


def schema_bytes(filename: str, model: type[BaseModel]) -> bytes:
    """Generate stable UTF-8/LF Draft 2020-12 schema bytes."""

    schema = model.model_json_schema(by_alias=True, mode="serialization")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"{SCHEMA_BASE}/{filename}"
    return (json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def export_schemas(directory: Path) -> None:
    """Write all public schemas to an existing directory."""

    directory.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMA_MODELS.items():
        (directory / filename).write_bytes(schema_bytes(filename, model))


if __name__ == "__main__":
    export_schemas(Path("schemas"))
