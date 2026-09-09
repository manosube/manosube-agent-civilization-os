"""P15-R1-F1: the pure, I/O-free network-scope decision.

Structural Review Round 1 found that ``LocalHttpRuntimeAdapter.observe`` constructed and
opened ``boundary["endpoint"]`` without ever consulting
``boundary["network_scope"]["allowed_hosts"]`` -- so a Boundary could name one allowed host
and the GET could still be sent to another, and ``OBSERVATION_BOUNDARY_CLOSED=true`` was not
actually true. These tests pin the decision itself: what
:mod:`~manosube_agent_civilization.runtime.network` accepts, and every form it refuses,
before any connection could exist. The zero-call proofs that this decision is genuinely
reached before an adapter is invoked live in ``tests/contract/runtime/
test_runtime_boundary_enforcement.py``; the real redirect control lives in
``tests/integration/runtime/test_runtime_local_http_vertical_proof.py``.
"""

from __future__ import annotations

import pytest

from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.network import (
    canonical_endpoint_host,
    canonical_endpoint_url,
    require_endpoint_within_network_scope,
)


def _endpoint(base_url: str, path: str = "/health") -> dict[str, str]:
    return {"base_url": base_url, "path": path}


def _scope(*hosts: str) -> dict[str, list[str]]:
    return {"allowed_hosts": list(hosts)}


# ---------------------------------------------------------------------------
# Canonical assembly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("base_url", "path", "expected"),
    [
        ("http://127.0.0.1:8080", "/health", "http://127.0.0.1:8080/health"),
        ("http://127.0.0.1:8080/", "health", "http://127.0.0.1:8080/health"),
        ("http://127.0.0.1:8080/", "/health", "http://127.0.0.1:8080/health"),
        ("https://example.test", "/a/b", "https://example.test/a/b"),
    ],
)
def test_the_canonical_url_is_assembled_with_exactly_one_separator(
    base_url: str, path: str, expected: str
) -> None:
    """The string this module validates must be the identical string a transport would open --
    a canonicalization that disagreed with the adapter's own assembly would validate one URL
    and open another."""

    assert canonical_endpoint_url(_endpoint(base_url, path)) == expected


@pytest.mark.parametrize(
    "endpoint",
    [
        "not-a-mapping",
        {"path": "/health"},
        {"base_url": "", "path": "/health"},
        {"base_url": "http://127.0.0.1", "path": ""},
        {"base_url": 7, "path": "/health"},
        {"base_url": "http://127.0.0.1", "path": None},
    ],
)
def test_a_malformed_endpoint_is_refused_before_any_canonicalization(endpoint: object) -> None:
    with pytest.raises(RuntimeRequirementError):
        canonical_endpoint_url(endpoint)


# ---------------------------------------------------------------------------
# Host canonicalization and the ambiguous/unsupported forms
# ---------------------------------------------------------------------------


def test_the_host_is_canonicalized_case_insensitively() -> None:
    assert canonical_endpoint_host("http://LOCALHOST:8080/health") == "localhost"
    assert canonical_endpoint_host("https://Example.TEST/health") == "example.test"


@pytest.mark.parametrize(
    "url",
    [
        # userinfo: the classic "https://allowed.example@attacker.example/" confusion
        "http://allowed.test@attacker.test/health",
        "https://user:password@127.0.0.1:8080/health",
        # unsupported schemes
        "file:///etc/passwd",
        "ftp://127.0.0.1/health",
        "gopher://127.0.0.1/health",
        "127.0.0.1/health",
        # no readable host
        "http:///health",
        # malformed ports
        "http://127.0.0.1:abc/health",
        "http://127.0.0.1:0/health",
        "http://127.0.0.1:65536/health",
        "http://127.0.0.1:99999/health",
        "http://127.0.0.1:/health",
        # ambiguous host encodings
        "http://127.0.0.%31/health",
        "http://ex%41mple.test/health",
    ],
)
def test_every_ambiguous_or_unsupported_destination_is_refused(url: str) -> None:
    with pytest.raises(RuntimeRequirementError):
        canonical_endpoint_host(url)


def test_a_bracketed_ipv6_literal_with_and_without_a_port_is_readable() -> None:
    assert canonical_endpoint_host("http://[::1]:8080/health") == "::1"
    assert canonical_endpoint_host("http://[::1]/health") == "::1"


# ---------------------------------------------------------------------------
# The allowlist itself
# ---------------------------------------------------------------------------


def test_an_endpoint_inside_the_declared_scope_returns_its_canonical_url() -> None:
    url = require_endpoint_within_network_scope(
        _endpoint("http://127.0.0.1:8080"), _scope("127.0.0.1")
    )
    assert url == "http://127.0.0.1:8080/health"


def test_the_allowlist_match_is_case_insensitive_but_otherwise_exact() -> None:
    assert require_endpoint_within_network_scope(
        _endpoint("http://Example.TEST"), _scope("example.test")
    )
    with pytest.raises(RuntimeRequirementError):
        # A superstring/substring is not a match -- no suffix, prefix, or wildcard semantics
        # exist here at all.
        require_endpoint_within_network_scope(
            _endpoint("http://evil-example.test"), _scope("example.test")
        )


def test_a_host_outside_the_declared_scope_is_refused() -> None:
    with pytest.raises(RuntimeRequirementError):
        require_endpoint_within_network_scope(
            _endpoint("http://127.0.0.2:8080"), _scope("127.0.0.1")
        )


def test_localhost_and_the_loopback_literal_are_not_interchangeable() -> None:
    """No DNS resolution happens here by design, so ``localhost`` and ``127.0.0.1`` are two
    different declared names -- an allowlist of names, never of resolved addresses. This is
    also exactly what makes the real redirect control in the V3 vertical proof a genuine
    control: a redirect from an allowed ``127.0.0.1`` to a disallowed ``localhost`` reaches
    the same machine, and must still never be followed."""

    with pytest.raises(RuntimeRequirementError):
        require_endpoint_within_network_scope(
            _endpoint("http://localhost:8080"), _scope("127.0.0.1")
        )


@pytest.mark.parametrize(
    "network_scope",
    [
        "not-a-mapping",
        {},
        {"allowed_hosts": []},
        {"allowed_hosts": "127.0.0.1"},
        {"allowed_hosts": [""]},
        {"allowed_hosts": [None]},
        {"allowed_hosts": [127]},
    ],
)
def test_a_malformed_network_scope_is_refused_rather_than_treated_as_permissive(
    network_scope: object,
) -> None:
    with pytest.raises(RuntimeRequirementError):
        require_endpoint_within_network_scope(_endpoint("http://127.0.0.1:8080"), network_scope)
