"""V1 (Issue #64): deterministic Runtime identity/Boundary proof.

Pure-function proof of :mod:`manosube_agent_civilization.runtime.identity` -- no Store, no
Boot, no Adapter. Proves the three distinct identities Issue #64's own minimum-acceptable-
after-state item 1 requires are genuinely distinct, deterministic, and each collision-
sensitive to the fields that define it.

Structural Review Round 2 (P15-R2-F2) adds the Runtime Deployment Declaration's own *signing
payload* to what is proved here: the exact bytes a genuine Human Authority signature must cover
are the exact bytes both of that record's digests are computed over, and neither the signature
nor either digest is ever covered by itself.

Structural Review Round 3 adds two more derivations, proved the identical way: the Runtime Root
Admission's own identity/fingerprint/signing payload (P15-R3-F1) -- including the load-bearing
*absence* of any Human Authority or key field on that record -- and the deployment target key
(P15-R3-F2), which both sides of the route's own current-declaration pointer comparison derive
independently, and which deliberately excludes ``deployment_fingerprint``.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from typing import Any

from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.identity import (
    ROOT_ADMISSION_SEMANTIC_FIELDS,
    runtime_deployment_declaration_id,
    runtime_deployment_declaration_semantic_fingerprint,
    runtime_deployment_declaration_signing_payload,
    runtime_deployment_target_key,
    runtime_observation_boundary_fingerprint,
    runtime_observation_envelope_id,
    runtime_observation_envelope_semantic_fingerprint,
    runtime_observation_request_identity,
    runtime_observed_content_fingerprint,
    runtime_root_admission_id,
    runtime_root_admission_semantic_fingerprint,
    runtime_root_admission_signing_payload,
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
    # P15-R2-F2: ``status`` participates in the signed/addressed payload; ``signature`` never
    # does (a signature cannot cover its own value).
    "status": "ACTIVE",
    "declared_at": "2026-09-08T00:00:00Z",
    # P15-R3-F2: the validity window participates too, for the identical reason ``declared_at``
    # does -- a window not covered by both digests and by the signature could be silently
    # re-dated after signing, which is exactly what a validity window exists to prevent.
    "valid_from": "2026-01-01T00:00:00Z",
    "valid_until": "2026-12-31T23:59:59Z",
    # P15-R4-F2: a declaration's own place in its target's transition chain is a *signed* claim,
    # not committer bookkeeping -- so both chain fields participate in the identical single
    # derivation. A successor whose ``predecessor_ref`` were outside the payload could be re-aimed
    # at a different head after the Human Authority signed it, and "monotonic" would be a
    # convention rather than a fact.
    "generation": 0,
    "predecessor_ref": None,
}
_ROOT_ADMISSION: dict[str, Any] = {
    "schema_version": "0.1",
    "project_id": "PRJ-0001",
    "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-0001"},
    "status": "ACTIVE",
    "declared_at": "2026-09-08T00:00:00Z",
    # P15-R4-F1: the identical chain fields, covered by the deployment trust anchor's own
    # signature instead of a Human Authority's.
    "generation": 0,
    "predecessor_ref": None,
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
        "status": "REVOKED",
        "declared_at": "2026-09-08T00:00:01Z",
        "valid_from": "2026-01-02T00:00:00Z",
        "valid_until": "2026-12-30T23:59:59Z",
        "generation": 1,
        "predecessor_ref": {
            "kind": "runtime_deployment_declaration",
            "id": "RUNTIME-DEPLOYMENT-DECLARATION-" + "0" * 64,
        },
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

    for field in (
        "project_id",
        "provider",
        "deployment_fingerprint",
        "human_authority_ref",
        "status",
        "generation",
        "predecessor_ref",
    ):
        incomplete = deepcopy(_DEPLOYMENT_DECLARATION)
        incomplete.pop(field)
        try:
            runtime_deployment_declaration_id(incomplete)
        except RuntimeRequirementError:
            continue
        raise AssertionError(f"a declaration missing {field!r} was addressed anyway")


# ---------------------------------------------------------------------------
# Runtime Deployment Declaration signing payload (P15-R2-F2)
# ---------------------------------------------------------------------------


def test_the_signing_payload_is_exactly_what_both_digests_are_computed_over() -> None:
    """The shared-derivation discipline ``binding/identity.py``'s own declaration payloads
    already establish: the content address, the semantic fingerprint, and the signed message are
    one derivation, so no field can ever be covered by one and not the others."""

    payload = runtime_deployment_declaration_signing_payload(deepcopy(_DEPLOYMENT_DECLARATION))
    assert isinstance(payload, bytes)
    assert payload == runtime_deployment_declaration_signing_payload(
        deepcopy(_DEPLOYMENT_DECLARATION)
    )

    expected_id = "RUNTIME-DEPLOYMENT-DECLARATION-" + hashlib.sha256(payload).hexdigest().upper()
    expected_fingerprint = "sha256:" + hashlib.sha256(payload).hexdigest()
    assert runtime_deployment_declaration_id(_DEPLOYMENT_DECLARATION) == expected_id
    assert (
        runtime_deployment_declaration_semantic_fingerprint(_DEPLOYMENT_DECLARATION)
        == expected_fingerprint
    )


def test_the_signing_payload_never_covers_the_signature_or_either_digest() -> None:
    """A signature cannot cover its own value, and an identity cannot be computed over itself --
    exactly the three exclusions ``binding/identity.py``'s own payload tuples make. Restating any
    of the three inside the record must therefore leave the payload byte-identical."""

    baseline = runtime_deployment_declaration_signing_payload(deepcopy(_DEPLOYMENT_DECLARATION))
    restated = deepcopy(_DEPLOYMENT_DECLARATION)
    restated["signature"] = {
        "algorithm": "ed25519",
        "key_id": "AUTH-KEY-0001",
        "value": "f" * 128,
    }
    restated["runtime_deployment_declaration_id"] = "RUNTIME-DEPLOYMENT-DECLARATION-" + "0" * 64
    restated["runtime_deployment_declaration_semantic_fingerprint"] = "sha256:" + "0" * 64
    assert runtime_deployment_declaration_signing_payload(restated) == baseline


def test_the_signing_payload_is_sensitive_to_status_and_to_the_declaration_instant() -> None:
    """``status`` participates because a revocation must not validate under a signature issued
    for an ACTIVE declaration; ``declared_at`` participates because a signature that never bound
    *when* would validate identically at any later replay instant."""

    baseline = runtime_deployment_declaration_signing_payload(deepcopy(_DEPLOYMENT_DECLARATION))
    for field, value in (
        ("status", "REVOKED"),
        ("declared_at", "2026-09-08T00:00:01Z"),
        # P15-R3-F2: both validity bounds are covered by the identical single derivation, so a
        # declaration cannot be re-dated after signing without breaking its own identity *and*
        # its own signature.
        ("valid_from", "2026-01-02T00:00:00Z"),
        ("valid_until", "2026-12-30T23:59:59Z"),
        # P15-R4-F2: and both chain fields, for the reason above -- an unsigned generation or
        # predecessor would let a committer, or anyone able to write a Store record, re-point an
        # already-signed body at a different predecessor.
        ("generation", 7),
        (
            "predecessor_ref",
            {
                "kind": "runtime_deployment_declaration",
                "id": "RUNTIME-DEPLOYMENT-DECLARATION-" + "0" * 64,
            },
        ),
    ):
        mutated = deepcopy(_DEPLOYMENT_DECLARATION)
        mutated[field] = value
        assert runtime_deployment_declaration_signing_payload(mutated) != baseline, field


# ---------------------------------------------------------------------------
# Runtime Root Admission identity and signing payload (P15-R3-F1)
# ---------------------------------------------------------------------------


def test_root_admission_identity_is_deterministic_and_correctly_shaped() -> None:
    admission_id = runtime_root_admission_id(_ROOT_ADMISSION)
    fingerprint = runtime_root_admission_semantic_fingerprint(_ROOT_ADMISSION)
    assert admission_id == runtime_root_admission_id(deepcopy(_ROOT_ADMISSION))
    assert fingerprint == runtime_root_admission_semantic_fingerprint(deepcopy(_ROOT_ADMISSION))
    assert re.fullmatch(r"RUNTIME-ROOT-ADMISSION-[0-9A-F]{64}", admission_id)
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint)


def test_the_root_admission_signing_payload_is_exactly_what_both_digests_cover() -> None:
    """The identical shared-derivation discipline this module's own deployment declaration
    already keeps: one payload, hashed twice under two encodings, and signed once."""

    payload = runtime_root_admission_signing_payload(deepcopy(_ROOT_ADMISSION))
    assert isinstance(payload, bytes)
    assert payload == runtime_root_admission_signing_payload(deepcopy(_ROOT_ADMISSION))
    assert (
        runtime_root_admission_id(_ROOT_ADMISSION)
        == "RUNTIME-ROOT-ADMISSION-" + hashlib.sha256(payload).hexdigest().upper()
    )
    assert (
        runtime_root_admission_semantic_fingerprint(_ROOT_ADMISSION)
        == "sha256:" + hashlib.sha256(payload).hexdigest()
    )


def test_the_root_admission_payload_never_covers_the_signature_or_either_digest() -> None:
    baseline = runtime_root_admission_signing_payload(deepcopy(_ROOT_ADMISSION))
    restated = deepcopy(_ROOT_ADMISSION)
    restated["signature"] = {
        "algorithm": "ed25519",
        "key_id": "TRUST-ANCHOR-0001",
        "value": "f" * 128,
    }
    restated["runtime_root_admission_id"] = "RUNTIME-ROOT-ADMISSION-" + "0" * 64
    restated["runtime_root_admission_semantic_fingerprint"] = "sha256:" + "0" * 64
    assert runtime_root_admission_signing_payload(restated) == baseline


def test_root_admission_identity_is_collision_sensitive_in_every_semantic_field() -> None:
    """Every field this record carries decides *which* world is admitted, so every one must be
    covered -- an admission whose project or Binding could be changed without changing its own
    address or signature would be exactly the unbounded trust grant P15-R3-F1 forbids."""

    baseline_id = runtime_root_admission_id(_ROOT_ADMISSION)
    baseline_fp = runtime_root_admission_semantic_fingerprint(_ROOT_ADMISSION)
    mutations: dict[str, Any] = {
        "project_id": "PRJ-OTHER",
        "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-OTHER"},
        "status": "REVOKED",
        "declared_at": "2026-09-08T00:00:01Z",
        "generation": 1,
        "predecessor_ref": {
            "kind": "runtime_root_admission",
            "id": "RUNTIME-ROOT-ADMISSION-" + "0" * 64,
        },
    }
    for field, value in mutations.items():
        mutated = deepcopy(_ROOT_ADMISSION)
        mutated[field] = value
        assert runtime_root_admission_id(mutated) != baseline_id, field
        assert runtime_root_admission_semantic_fingerprint(mutated) != baseline_fp, field


def test_a_root_admission_missing_a_semantic_field_cannot_be_identified_at_all() -> None:
    for field in (
        "project_id",
        "project_binding_ref",
        "status",
        "declared_at",
        "generation",
        "predecessor_ref",
    ):
        incomplete = deepcopy(_ROOT_ADMISSION)
        incomplete.pop(field)
        try:
            runtime_root_admission_id(incomplete)
        except RuntimeRequirementError:
            continue
        raise AssertionError(f"an admission missing {field!r} was addressed anyway")


def test_the_root_admission_record_carries_no_human_authority_field_at_all() -> None:
    """The load-bearing *absence* (P15-R3-F1). An admission record must be verifiable against a
    trust anchor that is not resolvable from inside the Store being admitted -- so it names no
    Human Authority and no key. If it did, an attacker's fully self-consistent alternate world
    could simply self-sign a matching record with its own internally legitimate Authority key
    and pass, which is the self-referential defect this record kind exists to avoid."""

    assert "human_authority_ref" not in ROOT_ADMISSION_SEMANTIC_FIELDS
    assert not any("key" in field for field in ROOT_ADMISSION_SEMANTIC_FIELDS)


# ---------------------------------------------------------------------------
# Runtime deployment target key (P15-R3-F2)
# ---------------------------------------------------------------------------


def test_the_target_key_is_deterministic_and_derives_identically_from_both_sides() -> None:
    """The route derives this key twice from two independently checked copies -- once from the
    ``target_identity`` a caller supplied, once (in the committer) from the declaration's own
    restated fields. Both must land on the identical key or the pointer could never match."""

    from_target = runtime_deployment_target_key(deepcopy(_TARGET_IDENTITY))
    from_declaration = runtime_deployment_target_key(deepcopy(_DEPLOYMENT_DECLARATION))
    assert from_target == from_declaration
    assert re.fullmatch(r"RUNTIME-DEPLOYMENT-TARGET-[0-9A-F]{64}", from_target)


def test_the_target_key_changes_with_every_field_that_names_a_different_target() -> None:
    baseline = runtime_deployment_target_key(deepcopy(_TARGET_IDENTITY))
    for field, value in (
        ("project_binding_ref", {"kind": "project_binding", "id": "PROJBIND-OTHER"}),
        ("provider", "elsewhere"),
        ("deployment_id", "billing-service"),
        ("instance_identity", "widget-service-2"),
    ):
        mutated = deepcopy(_TARGET_IDENTITY)
        mutated[field] = value
        assert runtime_deployment_target_key(mutated) != baseline, field


def test_the_target_key_deliberately_ignores_the_deployment_fingerprint() -> None:
    """The one field excluded, and the exclusion is the point (P15-R3-F2). A
    ``deployment_fingerprint`` says *what this target currently is*, not *which target this is*.
    A legitimate rotation re-declares the identical provider/deployment/instance under a new
    fingerprint and must **supersede** the previous declaration; if the fingerprint were part of
    the key, every rotation would fork the pointer space and leave the superseded declaration
    permanently current for its own old key -- which is precisely the ineffective-revocation
    defect this round closes."""

    rotated = deepcopy(_TARGET_IDENTITY)
    rotated["deployment_fingerprint"] = "sha256:" + "b" * 64
    assert runtime_deployment_target_key(rotated) == runtime_deployment_target_key(
        deepcopy(_TARGET_IDENTITY)
    )
