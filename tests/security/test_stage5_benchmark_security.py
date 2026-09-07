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
