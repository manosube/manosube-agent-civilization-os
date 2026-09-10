"""V1 (Issue #69): deterministic URL Boot identity proof.

Pure-function proof of :mod:`manosube_agent_civilization.url_boot.identity` -- no Store, no
Boot, no Adapter. Proves the four distinct identities this package's own module docstring
declares are genuinely distinct, deterministic, and each collision-sensitive to the fields that
define it -- the identical discipline ``tests/unit/runtime/test_runtime_identity.py`` already
establishes for its own three.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.url_boot.identity import (
    ENVELOPE_SEMANTIC_FIELDS,
    url_boundary_fingerprint,
    url_observed_content_fingerprint,
    url_source_fingerprint,
    url_source_observation_envelope_id,
    url_source_observation_envelope_semantic_fingerprint,
    url_source_request_identity,
)

_SOURCE_IDENTITY: dict[str, Any] = {
    "scheme": "https",
    "host": "example.test",
    "port": 443,
    "path": "/status",
    "query": "x=1",
    "fragment": None,
}
_BOUNDARY: dict[str, Any] = {
    "fetch_method": "HTTP_GET_BOUNDED",
    "network_scope": {
        "admitted_schemes": ["https"],
        "admitted_hosts": ["example.test"],
        "admitted_ports": [443],
    },
    "redirect_policy": {"max_redirects": 3},
    "timeout_seconds": 5,
    "max_response_bytes": 65536,
    "admitted_content_types": ["application/json"],
    "permitted_fields": ["status"],
    "time_window": {"issued_at": "2026-09-10T00:00:00Z", "expires_at": "2026-09-10T00:05:00Z"},
    "redaction_fields": [],
    "credentials_permitted": False,
}
_REQUESTED_FINGERPRINT = url_source_fingerprint(_SOURCE_IDENTITY)
_BOUNDARY_FINGERPRINT = url_boundary_fingerprint(_BOUNDARY)
_ENVELOPE: dict[str, Any] = {
    "project_id": "PRJ-0001",
    "project_binding_ref": {"kind": "project_binding", "id": "PB-0001"},
    "boot_state_fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64},
    "requested_source_identity": _SOURCE_IDENTITY,
    "requested_source_fingerprint": _REQUESTED_FINGERPRINT,
    "effective_source_identity": _SOURCE_IDENTITY,
    "effective_source_fingerprint": _REQUESTED_FINGERPRINT,
    "boundary": _BOUNDARY,
    "boundary_fingerprint": _BOUNDARY_FINGERPRINT,
    "source_request_identity": url_source_request_identity(
        _REQUESTED_FINGERPRINT, _BOUNDARY_FINGERPRINT, _BOUNDARY["time_window"]["issued_at"]
    ),
    "retrieved_at": "2026-09-10T00:00:01Z",
    "fetch_outcome": "OBSERVED",
    "response_status": 200,
    "redirect_hop_count": 0,
    "resolution_provenance": [
        {"host": "example.test", "port": 443, "resolved_address": "203.0.113.10"}
    ],
    "observed_fields": {"status": "ok"},
    "observed_content_fingerprint": url_observed_content_fingerprint({"status": "ok"}),
    "adapter_identity": {"adapter": "fake_url_source_adapter", "version": "0.1"},
    "human_authority_ref": {"kind": "human_authority", "id": "AUTH-BIND-0001"},
}


def test_source_fingerprint_is_deterministic_and_field_sensitive() -> None:
    baseline = url_source_fingerprint(deepcopy(_SOURCE_IDENTITY))
    assert baseline == url_source_fingerprint(deepcopy(_SOURCE_IDENTITY))
    assert baseline.startswith("sha256:")
    for field, value in (
        ("scheme", "http"),
        ("host", "other.test"),
        ("port", 8443),
        ("path", "/other"),
        ("query", "x=2"),
        ("fragment", "frag"),
    ):
        mutated = deepcopy(_SOURCE_IDENTITY)
        mutated[field] = value
        assert url_source_fingerprint(mutated) != baseline, field


def test_boundary_fingerprint_is_deterministic_and_field_sensitive() -> None:
    baseline = url_boundary_fingerprint(deepcopy(_BOUNDARY))
    assert baseline == url_boundary_fingerprint(deepcopy(_BOUNDARY))

    mutated = deepcopy(_BOUNDARY)
    mutated["timeout_seconds"] = 6
    assert url_boundary_fingerprint(mutated) != baseline

    mutated = deepcopy(_BOUNDARY)
    mutated["permitted_fields"] = ["status", "extra"]
    assert url_boundary_fingerprint(mutated) != baseline

    mutated = deepcopy(_BOUNDARY)
    mutated["network_scope"] = dict(mutated["network_scope"])
    mutated["network_scope"]["admitted_hosts"] = ["other.test"]
    assert url_boundary_fingerprint(mutated) != baseline


def test_source_request_identity_is_stable_before_any_outcome_is_known() -> None:
    """The request identity is computable from source + Boundary + issued_at alone, independent
    of whatever the adapter later returns."""

    first = url_source_request_identity(
        _REQUESTED_FINGERPRINT, _BOUNDARY_FINGERPRINT, _BOUNDARY["time_window"]["issued_at"]
    )
    second = url_source_request_identity(
        _REQUESTED_FINGERPRINT, _BOUNDARY_FINGERPRINT, _BOUNDARY["time_window"]["issued_at"]
    )
    assert first == second
    assert first.startswith("URL-SOURCE-OBSERVATION-REQUEST-")


def test_source_request_identity_is_sensitive_to_issued_at() -> None:
    first = url_source_request_identity(
        _REQUESTED_FINGERPRINT, _BOUNDARY_FINGERPRINT, "2026-01-01T00:00:00Z"
    )
    second = url_source_request_identity(
        _REQUESTED_FINGERPRINT, _BOUNDARY_FINGERPRINT, "2026-01-01T00:00:01Z"
    )
    assert first != second


def test_observed_content_fingerprint_is_collision_sensitive_and_none_when_unset() -> None:
    first = url_observed_content_fingerprint({"status": "ok"})
    second = url_observed_content_fingerprint({"status": "ok "})
    assert first != second
    assert first == url_observed_content_fingerprint({"status": "ok"})
    assert url_observed_content_fingerprint(None) is None


def test_envelope_id_and_semantic_fingerprint_are_deterministic() -> None:
    first_id = url_source_observation_envelope_id(deepcopy(_ENVELOPE))
    second_id = url_source_observation_envelope_id(deepcopy(_ENVELOPE))
    assert first_id == second_id
    assert first_id.startswith("URL-SOURCE-OBSERVATION-")
    assert not first_id.startswith("URL-SOURCE-OBSERVATION-REQUEST-")

    first_fp = url_source_observation_envelope_semantic_fingerprint(deepcopy(_ENVELOPE))
    second_fp = url_source_observation_envelope_semantic_fingerprint(deepcopy(_ENVELOPE))
    assert first_fp == second_fp
    assert first_fp.startswith("sha256:")


def test_envelope_id_differs_from_the_request_identity_and_the_source_fingerprint() -> None:
    """The four identities this package derives are genuinely distinct concepts, never
    collapsed into one value even when computed from the same underlying observation."""

    envelope_id = url_source_observation_envelope_id(deepcopy(_ENVELOPE))
    assert envelope_id != _ENVELOPE["source_request_identity"]
    assert envelope_id != _ENVELOPE["requested_source_fingerprint"]


def test_envelope_identity_ignores_its_own_two_digest_fields() -> None:
    with_digests = deepcopy(_ENVELOPE)
    with_digests["url_source_observation_envelope_id"] = "URL-SOURCE-OBSERVATION-" + "0" * 64
    with_digests["url_source_observation_semantic_fingerprint"] = "sha256:" + "0" * 64
    assert url_source_observation_envelope_id(with_digests) == url_source_observation_envelope_id(
        _ENVELOPE
    )


def test_envelope_identity_is_sensitive_to_every_semantic_field() -> None:
    baseline_id = url_source_observation_envelope_id(deepcopy(_ENVELOPE))
    baseline_fp = url_source_observation_envelope_semantic_fingerprint(deepcopy(_ENVELOPE))

    other_source_identity = dict(_SOURCE_IDENTITY, path="/other")
    other_content_fingerprint = url_observed_content_fingerprint({"status": "down"})
    mutations: dict[str, Any] = {
        "project_id": "PRJ-OTHER",
        "project_binding_ref": {"kind": "project_binding", "id": "PB-OTHER"},
        "boot_state_fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "1" * 64},
        "effective_source_identity": other_source_identity,
        "effective_source_fingerprint": url_source_fingerprint(other_source_identity),
        "source_request_identity": "URL-SOURCE-OBSERVATION-REQUEST-" + "0" * 64,
        "retrieved_at": "2026-09-10T00:00:02Z",
        # identity.py itself validates no enum -- a pure content-address function is sensitive
        # to any field content, including a value the engine/schema would themselves refuse.
        "fetch_outcome": "DNS_FAILURE",
        "response_status": 201,
        "redirect_hop_count": 1,
        "resolution_provenance": [
            {"host": "example.test", "port": 443, "resolved_address": "203.0.113.99"}
        ],
        "observed_fields": {"status": "down"},
        "observed_content_fingerprint": other_content_fingerprint,
        "adapter_identity": {"adapter": "other_adapter", "version": "0.1"},
        "human_authority_ref": {"kind": "human_authority", "id": "AUTH-OTHER"},
    }
    for field, value in mutations.items():
        mutated = deepcopy(_ENVELOPE)
        mutated[field] = value
        assert url_source_observation_envelope_id(mutated) != baseline_id, field
        assert url_source_observation_envelope_semantic_fingerprint(mutated) != baseline_fp, field


def test_an_envelope_missing_a_semantic_field_cannot_be_identified_at_all() -> None:
    """Refuses rather than silently addressing a partial record -- an identity computed over
    "whatever fields happened to be present" would let two different envelopes share one content
    address."""

    for field in ENVELOPE_SEMANTIC_FIELDS:
        incomplete = deepcopy(_ENVELOPE)
        incomplete.pop(field)
        try:
            url_source_observation_envelope_id(incomplete)
        except KeyError:
            continue
        raise AssertionError(f"an envelope missing {field!r} was addressed anyway")
