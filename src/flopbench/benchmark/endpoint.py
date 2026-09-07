"""SSRF-resistant endpoint policy for local inference runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from ipaddress import ip_address
from typing import Literal
from urllib.parse import unquote, urlsplit


class EndpointErrorCode(StrEnum):
    INVALID = "benchmark.endpoint_invalid"
    NOT_ALLOWED = "benchmark.endpoint_not_allowed"


class EndpointError(ValueError):
    def __init__(self, code: EndpointErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SafeEndpoint:
    scheme: str
    host: str
    port: int
    base_path: str
    scope: Literal["loopback", "allowlisted_external"]

    @property
    def authority(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"{host}:{self.port}"


def _is_loopback(host: str) -> bool:
    if host.casefold() == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def validate_endpoint(
    value: str,
    *,
    allow_external: bool = False,
    allowlist: tuple[str, ...] = (),
) -> SafeEndpoint:
    """Accept loopback by default and exact, approved external hosts only."""

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise EndpointError(EndpointErrorCode.INVALID, "Endpoint must be an HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise EndpointError(EndpointErrorCode.INVALID, "Endpoint credentials are not allowed")
    if parsed.query or parsed.fragment:
        raise EndpointError(
            EndpointErrorCode.INVALID, "Endpoint query and fragment are not allowed"
        )
    host = parsed.hostname.casefold().rstrip(".")
    if not host or any(character.isspace() for character in host):
        raise EndpointError(EndpointErrorCode.INVALID, "Endpoint host is invalid")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise EndpointError(EndpointErrorCode.INVALID, "Endpoint port is invalid") from exc
    if not 1 <= port <= 65535:
        raise EndpointError(EndpointErrorCode.INVALID, "Endpoint port is invalid")
    scope: Literal["loopback", "allowlisted_external"]
    if _is_loopback(host):
        scope = "loopback"
    else:
        normalized_allowlist = {item.casefold().rstrip(".") for item in allowlist}
        if not allow_external or host not in normalized_allowlist:
            raise EndpointError(
                EndpointErrorCode.NOT_ALLOWED,
                "External endpoint requires explicit approval and an exact allowlist entry",
            )
        scope = "allowlisted_external"
    base_path = parsed.path.rstrip("/")
    if ".." in unquote(base_path).split("/"):
        raise EndpointError(EndpointErrorCode.INVALID, "Endpoint path traversal is not allowed")
    return SafeEndpoint(
        scheme=parsed.scheme,
        host=host,
        port=port,
        base_path=base_path,
        scope=scope,
    )
