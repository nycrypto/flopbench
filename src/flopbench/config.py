"""Small, strict local configuration contract for safe release compatibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

from flopbench.contracts import PrivacyLevel, StrictModel

MAX_CONFIG_BYTES = 64 * 1024


class ConfigError(Exception):
    """Controlled configuration failure with a stable reason code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class LocalConfig(StrictModel):
    """Local preferences only; no remote bind or credential fields exist."""

    schema_id: Literal["flopbench-config-v1"] = Field(default="flopbench-config-v1", alias="schema")
    default_privacy: PrivacyLevel = PrivacyLevel.PRIVATE
    dashboard_theme: Literal["system", "light", "dark"] = "system"


def load_config(path: Path | None = None) -> LocalConfig:
    """Load strict JSON, or return privacy-first defaults when no file is configured."""

    if path is None:
        return LocalConfig()
    try:
        if path.is_symlink():
            raise ConfigError("config.unsafe_input", "Config must be a regular file")
        if not path.exists():
            return LocalConfig()
        if not path.is_file():
            raise ConfigError("config.unsafe_input", "Config must be a regular file")
        if path.stat().st_size > MAX_CONFIG_BYTES:
            raise ConfigError("config.too_large", "Config exceeds the size limit")
        raw = path.read_bytes()
    except ConfigError:
        raise
    except OSError as exc:
        raise ConfigError("config.read_error", "Config could not be read") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
        return LocalConfig.model_validate(data)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise ConfigError("config.invalid", "Config is not valid flopbench-config-v1 JSON") from exc
