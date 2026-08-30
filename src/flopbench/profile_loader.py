"""Safe, deterministic loading for versioned FLOP source profiles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError
from yaml.constructor import ConstructorError  # type: ignore[import-untyped]

from flopbench.contracts import SourceProfile

MAX_PROFILE_BYTES = 1024 * 1024


class ProfileErrorCode(StrEnum):
    """Stable machine-readable profile loader failure codes."""

    READ_ERROR = "profile.read_error"
    TOO_LARGE = "profile.too_large"
    INVALID_ENCODING = "profile.invalid_encoding"
    INVALID_NEWLINE = "profile.invalid_newline"
    YAML_PARSE_ERROR = "profile.yaml_parse_error"
    DUPLICATE_FIELD = "profile.duplicate_field"
    VALIDATION_ERROR = "profile.validation_error"


@dataclass(frozen=True, slots=True)
class ProfileValidationIssue:
    """A safe, concise Pydantic validation issue."""

    path: str
    kind: str


class ProfileLoadError(ValueError):
    """Public loader error that never includes profile values or file contents."""

    def __init__(
        self,
        code: ProfileErrorCode,
        message: str,
        issues: tuple[ProfileValidationIssue, ...] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.issues = issues


@dataclass(frozen=True, slots=True)
class LoadedProfile:
    """Validated model plus identity of the exact source bytes."""

    profile: SourceProfile
    sha256: str
    byte_length: int


class _DuplicateFieldError(ConstructorError):  # type: ignore[misc]
    pass


class _UniqueKeySafeLoader(yaml.SafeLoader):  # type: ignore[misc]
    pass


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise _DuplicateFieldError(
                "while constructing a mapping",
                node.start_mark,
                "found a duplicate field",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_profile(path: Path, *, max_bytes: int = MAX_PROFILE_BYTES) -> LoadedProfile:
    """Load a strict UTF-8/LF profile and hash its original bytes.

    The digest is calculated over the raw file, before YAML parsing or any
    normalization.  This makes the profile identity byte-for-byte reproducible.
    """

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ProfileLoadError(ProfileErrorCode.READ_ERROR, "Profile could not be read") from exc

    if len(raw) > max_bytes:
        raise ProfileLoadError(ProfileErrorCode.TOO_LARGE, "Profile exceeds the size limit")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ProfileLoadError(
            ProfileErrorCode.INVALID_ENCODING, "Profile must be UTF-8 without a BOM"
        )
    if b"\r" in raw:
        raise ProfileLoadError(ProfileErrorCode.INVALID_NEWLINE, "Profile must use LF newlines")

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ProfileLoadError(
            ProfileErrorCode.INVALID_ENCODING, "Profile must be valid UTF-8"
        ) from exc

    try:
        payload = yaml.load(text, Loader=_UniqueKeySafeLoader)
    except _DuplicateFieldError as exc:
        raise ProfileLoadError(
            ProfileErrorCode.DUPLICATE_FIELD, "Profile contains a duplicate field"
        ) from exc
    except yaml.YAMLError as exc:
        raise ProfileLoadError(
            ProfileErrorCode.YAML_PARSE_ERROR, "Profile contains invalid YAML"
        ) from exc

    try:
        profile = SourceProfile.model_validate(payload)
    except ValidationError as exc:
        issues = tuple(
            ProfileValidationIssue(
                path=".".join(str(part) for part in error["loc"]),
                kind=str(error["type"]),
            )
            for error in exc.errors(include_url=False, include_context=False, include_input=False)
        )
        raise ProfileLoadError(
            ProfileErrorCode.VALIDATION_ERROR,
            "Profile does not satisfy flopbench-source-profile-v1",
            issues,
        ) from exc

    return LoadedProfile(profile=profile, sha256=sha256(raw).hexdigest(), byte_length=len(raw))
