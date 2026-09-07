from __future__ import annotations

import pytest

from flopbench.benchmark.endpoint import EndpointError, validate_endpoint

pytestmark = pytest.mark.stage5


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1:8000/v1",
        "http://example.com:8000/v1",
        "http://localhost.evil:8000/v1",
    ],
)
def test_ssrf_targets_are_rejected_without_exact_approval(endpoint: str) -> None:
    with pytest.raises(EndpointError):
        validate_endpoint(endpoint)


def test_endpoint_credentials_are_rejected_without_secret_disclosure() -> None:
    secret = "stage5-secret-token"

    with pytest.raises(EndpointError) as caught:
        validate_endpoint(f"http://user:{secret}@localhost:8000/v1")

    assert secret not in str(caught.value)


@pytest.mark.parametrize(
    "value",
    [
        "\nhttp://localhost",
        "http://local\thost",
        "http://localhost/秘密",
        "http://[broken",
        "http:///v1",
        "ftp://localhost",
        "http://localhost?key=secret",
        "http://localhost#secret",
        "http://.:8000",
        "http://local%68ost",
        "http://[::1%25eth0]",
        "http://localhost:abc",
        "http://localhost:65536",
        "http://localhost:0",
        "http://localhost/a/../b",
        "http://localhost/%2e%2e",
        "http://localhost/%252e%252e",
        "http://localhost/a\\b",
        "http://localhost/a//b",
    ],
)
def test_url_parser_ambiguities_cannot_reach_transport(value: str) -> None:
    with pytest.raises(EndpointError):
        validate_endpoint(value)


@pytest.mark.parametrize(
    ("value", "host", "port"),
    [
        ("http://LOCALHOST./v1", "127.0.0.1", 80),
        ("https://127.0.0.1", "127.0.0.1", 443),
        ("http://[::1]:8000", "::1", 8000),
    ],
)
def test_loopback_policy_pins_localhost_without_dns(value: str, host: str, port: int) -> None:
    endpoint = validate_endpoint(value)
    assert endpoint.host == host
    assert endpoint.port == port
    assert endpoint.scope == "loopback"
    assert endpoint.authority == (f"[{host}]:{port}" if ":" in host else f"{host}:{port}")


def test_external_host_requires_both_exact_allowlist_and_approval() -> None:
    value = "https://runtime.example/v1"
    with pytest.raises(EndpointError):
        validate_endpoint(value, allowlist=("runtime.example",))
    with pytest.raises(EndpointError):
        validate_endpoint(value, allow_external=True, allowlist=("other.example",))
    endpoint = validate_endpoint(value, allow_external=True, allowlist=("Runtime.Example.",))
    assert endpoint.scope == "allowlisted_external"
