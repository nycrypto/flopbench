"""RFC 8785 canonical bytes; sorted Python JSON alone is not JCS."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

import rfc8785

from flopbench.reporting.errors import ReportError


def canonical_bytes(value: Any) -> bytes:
    try:
        return rfc8785.dumps(value)
    except (rfc8785.CanonicalizationError, ValueError, TypeError, RecursionError) as exc:
        raise ReportError(
            "report.invalid_canonical_value", "Report cannot be represented as JCS"
        ) from exc


def canonical_digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("non-finite number")


def parse_json(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
    except (ValueError, RecursionError) as exc:
        raise ReportError("report.invalid_json", "Report must be strict UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ReportError("report.invalid_json", "Report must be a JSON object")
    # Reject unsafe integers, exponent overflow and lone Unicode surrogates before
    # Pydantic can coerce them or any privacy transformation discards them.
    canonical_bytes(payload)
    return payload
