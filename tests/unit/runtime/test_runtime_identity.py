"""V1 (Issue #64): deterministic Runtime identity/Boundary proof.

Pure-function proof of :mod:`manosube_agent_civilization.runtime.identity` -- no Store, no
Boot, no Adapter. Proves the three distinct identities Issue #64's own minimum-acceptable-
after-state item 1 requires are genuinely distinct, deterministic, and each collision-
sensitive to the fields that define it.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.runtime.identity import (
    runtime_observation_boundary_fingerprint,
    runtime_observation_envelope_id,
    runtime_observation_envelope_semantic_fingerprint,
    runtime_observation_request_identity,
    runtime_observed_content_fingerprint,
    runtime_target_fingerprint,
)

_TARGET_IDENTITY: dict[str, Any] = {
    "provider": "local",
    "deployment_id": "widget-service",
    "instance_identity": "widget-service-1",
    "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-0001"},
    "deployment_fingerprint": "sha256:" + "a" * 64,
}
_BOUNDARY: dict[str, Any] = {
    "observation_method": "HTTP_GET_BOUNDED",
    "endpoint": {"base_url": "http://127.0.0.1:1", "path": "/health"},
    "permitted_fields": ["status"],
    "time_window": {"issued_at": "2026-01-01T00:00:00Z", "expires_at": "2026-01-01T01:00:00Z"},
    "network_scope": {"allowed_hosts": ["127.0.0.1"]},
    "timeout_seconds": 5,
    "redaction_fields": [],
}
_ENVELOPE: dict[str, Any] = {
    "schema_version": "0.1",
    "project_id": "PRJ-0001",
    "target_identity": _TARGET_IDENTITY,
    "target_fingerprint": runtime_target_fingerprint(_TARGET_IDENTITY),
    "boundary": _BOUNDARY,
    "boundary_fingerprint": runtime_observation_boundary_fingerprint(_BOUNDARY),
    "observation_request_identity": runtime_observation_request_identity(
        runtime_target_fingerprint(_TARGET_IDENTITY),
        runtime_observation_boundary_fingerprint(_BOUNDARY),
        _BOUNDARY["time_window"]["issued_at"],
    ),
    "observed_at": "2026-01-01T00:30:00Z",
    "observation_outcome": "OBSERVED",
    "observed_fields": {"status": "ok"},
    "observed_content_fingerprint": runtime_observed_content_fingerprint({"status": "ok"}),
    "adapter_identity": {"adapter": "fake_runtime_adapter", "version": "0.1"},
    "human_authority_ref": {"kind": "human_authority", "id": "AUTH-BIND-0001"},
}


def test_target_fingerprint_is_deterministic() -> None:
    first = runtime_target_fingerprint(deepcopy(_TARGET_IDENTITY))
    second = runtime_target_fingerprint(deepcopy(_TARGET_IDENTITY))
    assert first == second
    assert first.startswith("sha256:")


def test_target_fingerprint_is_sensitive_to_every_field() -> None:
    baseline = runtime_target_fingerprint(deepcopy(_TARGET_IDENTITY))
    for field in _TARGET_IDENTITY:
        mutated = deepcopy(_TARGET_IDENTITY)
        if field == "project_binding_ref":
            mutated[field] = {"kind": "project_binding", "id": "PROJBIND-OTHER"}
        else:
            mutated[field] = mutated[field] + "-MUTATED"
        assert runtime_target_fingerprint(mutated) != baseline, field


def test_boundary_fingerprint_is_deterministic_and_field_sensitive() -> None:
    baseline = runtime_observation_boundary_fingerprint(deepcopy(_BOUNDARY))
    assert baseline == runtime_observation_boundary_fingerprint(deepcopy(_BOUNDARY))

    mutated = deepcopy(_BOUNDARY)
    mutated["timeout_seconds"] = 6
    assert runtime_observation_boundary_fingerprint(mutated) != baseline

    mutated = deepcopy(_BOUNDARY)
    mutated["permitted_fields"] = ["status", "extra"]
    assert runtime_observation_boundary_fingerprint(mutated) != baseline


def test_observation_request_identity_is_stable_before_any_outcome_is_known() -> None:
    """Item 1's own core requirement: the request identity is computable from target +
    Boundary + issued_at alone, independent of whatever the adapter later returns."""

    target_fingerprint = runtime_target_fingerprint(deepcopy(_TARGET_IDENTITY))
    boundary_fingerprint = runtime_observation_boundary_fingerprint(deepcopy(_BOUNDARY))
    first = runtime_observation_request_identity(
        target_fingerprint, boundary_fingerprint, _BOUNDARY["time_window"]["issued_at"]
    )
    second = runtime_observation_request_identity(
        target_fingerprint, boundary_fingerprint, _BOUNDARY["time_window"]["issued_at"]
    )
    assert first == second
    assert first.startswith("RUNTIME-OBSERVATION-REQUEST-")


def test_observation_request_identity_is_sensitive_to_issued_at() -> None:
    target_fingerprint = runtime_target_fingerprint(deepcopy(_TARGET_IDENTITY))
    boundary_fingerprint = runtime_observation_boundary_fingerprint(deepcopy(_BOUNDARY))
    first = runtime_observation_request_identity(
        target_fingerprint, boundary_fingerprint, "2026-01-01T00:00:00Z"
    )
    second = runtime_observation_request_identity(
        target_fingerprint, boundary_fingerprint, "2026-01-01T00:00:01Z"
    )
    assert first != second


def test_envelope_id_and_semantic_fingerprint_are_deterministic() -> None:
    first_id = runtime_observation_envelope_id(deepcopy(_ENVELOPE))
    second_id = runtime_observation_envelope_id(deepcopy(_ENVELOPE))
    assert first_id == second_id
    assert first_id.startswith("RUNTIME-OBSERVATION-")
    assert not first_id.startswith("RUNTIME-OBSERVATION-REQUEST-")

    first_fp = runtime_observation_envelope_semantic_fingerprint(deepcopy(_ENVELOPE))
    second_fp = runtime_observation_envelope_semantic_fingerprint(deepcopy(_ENVELOPE))
    assert first_fp == second_fp
    assert first_fp.startswith("sha256:")


def test_envelope_id_differs_from_request_identity_for_the_identical_observation() -> None:
    """The three identities (target, request, committed fact) are genuinely distinct
    concepts, never collapsed into one value even when computed from the same underlying
    observation."""

    envelope_id = runtime_observation_envelope_id(deepcopy(_ENVELOPE))
    assert envelope_id != _ENVELOPE["observation_request_identity"]
    assert envelope_id != _ENVELOPE["target_fingerprint"]


def test_envelope_identity_is_sensitive_to_every_semantic_field() -> None:
    """Tampering any single semantic field -- including the observed outcome and observed
    content -- must change both the envelope id and its own semantic fingerprint."""

    baseline_id = runtime_observation_envelope_id(deepcopy(_ENVELOPE))
    baseline_fp = runtime_observation_envelope_semantic_fingerprint(deepcopy(_ENVELOPE))

    mutations: dict[str, Any] = {
        "project_id": "PRJ-OTHER",
        "observed_at": "2026-01-01T00:31:00Z",
        "observation_outcome": "NEGATIVE",
        "observed_fields": {"status": "down"},
        "observed_content_fingerprint": runtime_observed_content_fingerprint({"status": "down"}),
        "adapter_identity": {"adapter": "other_adapter", "version": "0.1"},
        "human_authority_ref": {"kind": "human_authority", "id": "AUTH-OTHER"},
    }
    for field, value in mutations.items():
        mutated = deepcopy(_ENVELOPE)
        mutated[field] = value
        assert runtime_observation_envelope_id(mutated) != baseline_id, field
        assert runtime_observation_envelope_semantic_fingerprint(mutated) != baseline_fp, field


def test_observed_content_fingerprint_is_collision_sensitive() -> None:
    first = runtime_observed_content_fingerprint({"status": "ok"})
    second = runtime_observed_content_fingerprint({"status": "ok "})
    assert first != second
    assert first == runtime_observed_content_fingerprint({"status": "ok"})
