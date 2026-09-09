"""V1 (Issue #64): deterministic Runtime identity/Boundary proof.

Pure-function proof of :mod:`manosube_agent_civilization.runtime.identity` -- no Store, no
Boot, no Adapter. Proves the three distinct identities Issue #64's own minimum-acceptable-
after-state item 1 requires are genuinely distinct, deterministic, and each collision-
sensitive to the fields that define it.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.identity import (
    runtime_deployment_declaration_id,
    runtime_deployment_declaration_semantic_fingerprint,
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
    "deployment_declaration_ref": {
        "kind": "runtime_deployment_declaration",
        "id": "RUNTIME-DEPLOYMENT-DECLARATION-" + "A" * 64,
    },
    "deployment_fingerprint": "sha256:" + "a" * 64,
}
_DEPLOYMENT_DECLARATION: dict[str, Any] = {
    "schema_version": "0.1",
    "project_id": "PRJ-0001",
    "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-0001"},
    "provider": "local",
    "deployment_id": "widget-service",
    "instance_identity": "widget-service-1",
    "deployment_fingerprint": "sha256:" + "a" * 64,
    "human_authority_ref": {"kind": "human_authority", "id": "AUTH-BIND-0001"},
    "declared_at": "2026-09-08T00:00:00Z",
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
        elif field == "deployment_declaration_ref":
            mutated[field] = {
                "kind": "runtime_deployment_declaration",
                "id": "RUNTIME-DEPLOYMENT-DECLARATION-" + "B" * 64,
            }
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


# ---------------------------------------------------------------------------
# Runtime Deployment Declaration identity (P15-R1-F6)
# ---------------------------------------------------------------------------


def test_deployment_declaration_identity_is_deterministic_and_correctly_shaped() -> None:
    identity = runtime_deployment_declaration_id(_DEPLOYMENT_DECLARATION)
    fingerprint = runtime_deployment_declaration_semantic_fingerprint(_DEPLOYMENT_DECLARATION)
    assert identity == runtime_deployment_declaration_id(deepcopy(_DEPLOYMENT_DECLARATION))
    assert fingerprint == runtime_deployment_declaration_semantic_fingerprint(
        deepcopy(_DEPLOYMENT_DECLARATION)
    )
    assert identity.startswith("RUNTIME-DEPLOYMENT-DECLARATION-")
    assert len(identity) == len("RUNTIME-DEPLOYMENT-DECLARATION-") + 64
    assert fingerprint.startswith("sha256:")
    assert identity != fingerprint


def test_deployment_declaration_identity_ignores_its_own_two_digest_fields() -> None:
    """The identity is a pure function of the declaration's own meaning -- restating either
    digest inside the record cannot change what that record's identity is."""

    with_digests = deepcopy(_DEPLOYMENT_DECLARATION)
    with_digests["runtime_deployment_declaration_id"] = "RUNTIME-DEPLOYMENT-DECLARATION-" + "0" * 64
    with_digests["runtime_deployment_declaration_semantic_fingerprint"] = "sha256:" + "0" * 64
    assert runtime_deployment_declaration_id(with_digests) == runtime_deployment_declaration_id(
        _DEPLOYMENT_DECLARATION
    )


def test_deployment_declaration_identity_is_collision_sensitive_in_every_semantic_field() -> None:
    baseline_id = runtime_deployment_declaration_id(_DEPLOYMENT_DECLARATION)
    baseline_fp = runtime_deployment_declaration_semantic_fingerprint(_DEPLOYMENT_DECLARATION)
    mutations: dict[str, Any] = {
        "project_id": "PRJ-OTHER",
        "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-OTHER"},
        "provider": "elsewhere",
        "deployment_id": "billing-service",
        "instance_identity": "widget-service-2",
        "deployment_fingerprint": "sha256:" + "b" * 64,
        "human_authority_ref": {"kind": "human_authority", "id": "AUTH-OTHER"},
        "declared_at": "2026-09-08T00:00:01Z",
    }
    for field, value in mutations.items():
        mutated = deepcopy(_DEPLOYMENT_DECLARATION)
        mutated[field] = value
        assert runtime_deployment_declaration_id(mutated) != baseline_id, field
        assert runtime_deployment_declaration_semantic_fingerprint(mutated) != baseline_fp, field


def test_a_declaration_missing_a_semantic_field_cannot_be_identified_at_all() -> None:
    """Refuses rather than silently addressing a partial record -- an identity computed over
    "whatever fields happened to be present" would let two different declarations share one
    content address."""

    for field in ("project_id", "provider", "deployment_fingerprint", "human_authority_ref"):
        incomplete = deepcopy(_DEPLOYMENT_DECLARATION)
        incomplete.pop(field)
        try:
            runtime_deployment_declaration_id(incomplete)
        except RuntimeRequirementError:
            continue
        raise AssertionError(f"a declaration missing {field!r} was addressed anyway")
