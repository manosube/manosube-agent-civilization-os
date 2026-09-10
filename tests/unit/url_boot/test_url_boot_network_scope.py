"""P17-C1/P17-C5: the pure, I/O-free URL parsing and network-scope decision.

Mirrors ``tests/unit/runtime/test_runtime_network_scope.py`` exactly, adapted to this package's
own fully-decomposed ``source_identity`` shape (scheme/host/port/path/query/fragment) rather than
Runtime's ``{base_url, path}`` endpoint pair. These tests pin the decision itself -- what
:mod:`~manosube_agent_civilization.url_boot.network` accepts, and every form it refuses, before
any DNS resolution or connection could exist. The real DNS-rebinding/redirect controls live in
``tests/integration/url_boot/test_url_boot_local_http_vertical_proof.py`` and
``tests/integration/url_boot/test_url_boot_failure_tamper_matrix.py``.
"""

from __future__ import annotations

import pytest

from manosube_agent_civilization.url_boot.errors import UrlBootRequirementError
from manosube_agent_civilization.url_boot.network import (
    canonical_source_identity,
    require_source_within_network_scope,
    source_url,
)


def _scope(*, schemes: list[str], hosts: list[str], ports: list[int]) -> dict[str, object]:
    return {
        "admitted_schemes": schemes,
        "admitted_hosts": hosts,
        "admitted_ports": ports,
    }


# ---------------------------------------------------------------------------
# Canonical decomposition and reassembly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "http://127.0.0.1:8080/health",
            {
                "scheme": "http",
                "host": "127.0.0.1",
                "port": 8080,
                "path": "/health",
                "query": None,
                "fragment": None,
            },
        ),
        (
            "https://example.test/a/b?x=1#frag",
            {
                "scheme": "https",
                "host": "example.test",
                "port": 443,
                "path": "/a/b",
                "query": "x=1",
                "fragment": "frag",
            },
        ),
        (
            "http://EXAMPLE.TEST/health",
            {
                "scheme": "http",
                "host": "example.test",
                "port": 80,
                "path": "/health",
                "query": None,
                "fragment": None,
            },
        ),
        (
            "http://example.test",
            {
                "scheme": "http",
                "host": "example.test",
                "port": 80,
                "path": "/",
                "query": None,
                "fragment": None,
            },
        ),
    ],
)
def test_a_url_decomposes_into_exactly_its_canonical_source_identity(
    url: str, expected: dict[str, object]
) -> None:
    assert canonical_source_identity(url) == expected


def test_source_url_reassembly_round_trips_the_exact_string_a_transport_would_open() -> None:
    """The string :func:`source_url` reassembles must be the identical string
    :func:`~manosube_agent_civilization.url_boot.network.fetch_one_hop` actually opens -- a
    reassembly that disagreed with the identity a caller validated would validate one URL and
    reach another."""

    identity = canonical_source_identity("https://example.test:8443/a/b?x=1")
    assert source_url(identity) == "https://example.test:8443/a/b?x=1"

    default_port = canonical_source_identity("http://example.test/health")
    assert source_url(default_port) == "http://example.test/health"


@pytest.mark.parametrize(
    "url",
    [
        "",
        None,
        7,
        "not-a-url",
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
        # a disallowed host character (ambiguous/non-ASCII host encodings)
        "http://ex ample.test/health",
    ],
)
def test_every_ambiguous_or_unsupported_url_is_refused_before_any_resolution(url: object) -> None:
    with pytest.raises(UrlBootRequirementError):
        canonical_source_identity(url)


# ---------------------------------------------------------------------------
# The allowlist itself
# ---------------------------------------------------------------------------


def test_a_source_inside_the_declared_scope_is_accepted() -> None:
    identity = canonical_source_identity("http://127.0.0.1:8080/health")
    require_source_within_network_scope(
        identity, _scope(schemes=["http"], hosts=["127.0.0.1"], ports=[8080])
    )


def test_the_allowlist_host_match_is_case_insensitive_but_otherwise_exact() -> None:
    identity = canonical_source_identity("http://Example.TEST/health")
    require_source_within_network_scope(
        identity, _scope(schemes=["http"], hosts=["example.test"], ports=[80])
    )
    other = canonical_source_identity("http://evil-example.test/health")
    with pytest.raises(UrlBootRequirementError):
        # A superstring/substring is not a match -- no suffix, prefix, or wildcard semantics
        # exist here at all.
        require_source_within_network_scope(
            other, _scope(schemes=["http"], hosts=["example.test"], ports=[80])
        )


def test_a_host_outside_the_declared_scope_is_refused() -> None:
    identity = canonical_source_identity("http://127.0.0.2:8080/health")
    with pytest.raises(UrlBootRequirementError):
        require_source_within_network_scope(
            identity, _scope(schemes=["http"], hosts=["127.0.0.1"], ports=[8080])
        )


def test_a_scheme_outside_the_declared_scope_is_refused() -> None:
    identity = canonical_source_identity("https://example.test/health")
    with pytest.raises(UrlBootRequirementError):
        require_source_within_network_scope(
            identity, _scope(schemes=["http"], hosts=["example.test"], ports=[443])
        )


def test_a_port_outside_the_declared_scope_is_refused() -> None:
    identity = canonical_source_identity("http://example.test:9999/health")
    with pytest.raises(UrlBootRequirementError):
        require_source_within_network_scope(
            identity, _scope(schemes=["http"], hosts=["example.test"], ports=[80])
        )


def test_localhost_and_the_loopback_literal_are_not_interchangeable() -> None:
    """No DNS resolution happens in the pure scope check by design, so ``localhost`` and
    ``127.0.0.1`` are two different declared names -- an allowlist of names, never of resolved
    addresses. This is also what makes the real DNS-rebinding control in the V4 tamper matrix a
    genuine control: a hostname that later *resolves* to a different address is caught at the
    impure, single-resolution boundary in :func:`~manosube_agent_civilization.url_boot.network.
    fetch_one_hop`, never here."""

    identity = canonical_source_identity("http://localhost:8080/health")
    with pytest.raises(UrlBootRequirementError):
        require_source_within_network_scope(
            identity, _scope(schemes=["http"], hosts=["127.0.0.1"], ports=[8080])
        )
