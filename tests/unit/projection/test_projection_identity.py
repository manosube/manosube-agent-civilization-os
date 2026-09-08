"""Phase 14 (Issue #62), V1: deterministic Kernel proof for Projection Envelope identity.

Proves: stable identity across repeated derivation, canonical serialization (key-order
insensitivity), semantic sensitivity (a changed field changes the semantic fingerprint), the
deliberate mapping-key/semantic-fingerprint split (``PROJECTION_CONTRACT.md`` §3: identical
subject/kind/target with a different payload keeps the *same* ``projection_envelope_id`` but
changes the semantic fingerprint), and typed rejection of malformed inputs.
"""

from __future__ import annotations

import pytest

from manosube_agent_civilization.projection.engine import derive_projection_envelope
from manosube_agent_civilization.projection.errors import ProjectionRequirementError
from manosube_agent_civilization.projection.identity import (
    projection_envelope_id,
    projection_envelope_semantic_fingerprint,
    projection_mapping_key,
    projection_payload_fingerprint,
)

_SUBJECT_REF = {"kind": "observation_evidence", "id": "EVIDENCE-AAAA"}
_SUBJECT_FINGERPRINT = "sha256:" + "a" * 64
_TARGET_REPOSITORY = {"host": "github", "owner": "acme", "repo": "widget"}
_EXTERNAL_ARTIFACT_REF = {
    "host": "github",
    "owner": "acme",
    "repo": "widget",
    "artifact_kind": "artifact",
    "external_id": "1",
    "url": "https://github.com/acme/widget/artifact/1",
}
_AUTHORITY_REF = {"kind": "human_authority", "id": "AUTH-0001"}


def _envelope(**overrides: object) -> dict:
    kwargs = {
        "subject_ref": _SUBJECT_REF,
        "subject_fingerprint": _SUBJECT_FINGERPRINT,
        "projection_kind": "EVIDENCE_ARTIFACT",
        "target_repository": _TARGET_REPOSITORY,
        "projection_payload": {"title": "t", "body": "b"},
        "projection_payload_fingerprint": projection_payload_fingerprint(
            {"title": "t", "body": "b"}
        ),
        "external_artifact_ref": _EXTERNAL_ARTIFACT_REF,
        "github_authority_ref": _AUTHORITY_REF,
        "materialized_at": "2026-01-01T00:00:00Z",
        "claim_token": "PROJECTION-ATTEMPT-IDENTITY-0001",
    }
    kwargs.update(overrides)
    return derive_projection_envelope(**kwargs)  # type: ignore[arg-type]


def test_derivation_is_stable_across_repeated_calls() -> None:
    first = _envelope()
    second = _envelope()
    assert first == second
    assert first["projection_envelope_id"] == second["projection_envelope_id"]
    assert (
        first["projection_envelope_semantic_fingerprint"]
        == second["projection_envelope_semantic_fingerprint"]
    )


def test_canonical_serialization_is_key_order_insensitive() -> None:
    envelope_a = {
        "subject_ref": _SUBJECT_REF,
        "subject_fingerprint": _SUBJECT_FINGERPRINT,
        "projection_kind": "EVIDENCE_ARTIFACT",
        "target_repository": _TARGET_REPOSITORY,
    }
    envelope_b = {
        "target_repository": dict(_TARGET_REPOSITORY),
        "projection_kind": "EVIDENCE_ARTIFACT",
        "subject_fingerprint": _SUBJECT_FINGERPRINT,
        "subject_ref": dict(_SUBJECT_REF),
    }
    key_a = projection_mapping_key(
        envelope_a["subject_ref"],
        envelope_a["subject_fingerprint"],
        envelope_a["projection_kind"],
        envelope_a["target_repository"],
    )
    key_b = projection_mapping_key(
        envelope_b["subject_ref"],
        envelope_b["subject_fingerprint"],
        envelope_b["projection_kind"],
        envelope_b["target_repository"],
    )
    assert key_a == key_b


def test_different_subject_id_changes_the_mapping_key() -> None:
    base = _envelope()
    other = _envelope(subject_ref={"kind": "observation_evidence", "id": "EVIDENCE-BBBB"})
    assert base["projection_envelope_id"] != other["projection_envelope_id"]


def test_different_target_repository_changes_the_mapping_key() -> None:
    base = _envelope()
    other = _envelope(target_repository={"host": "github", "owner": "other", "repo": "widget"})
    assert base["projection_envelope_id"] != other["projection_envelope_id"]


def test_different_payload_keeps_the_identical_mapping_key_but_changes_the_semantic_fingerprint() -> (
    None
):
    """``PROJECTION_CONTRACT.md`` §3's own frozen decision: the mapping key (``projection_
    envelope_id``) never varies with payload -- only the semantic fingerprint does. This is
    what makes a route's own reuse-vs-conflict lookup possible by identity alone, before the
    payload is even compared."""

    base = _envelope()
    other_payload = {"title": "DIFFERENT", "body": "b"}
    other = _envelope(
        projection_payload=other_payload,
        projection_payload_fingerprint=projection_payload_fingerprint(other_payload),
    )
    assert base["projection_envelope_id"] == other["projection_envelope_id"]
    assert (
        base["projection_envelope_semantic_fingerprint"]
        != other["projection_envelope_semantic_fingerprint"]
    )


def test_projection_payload_fingerprint_is_deterministic_and_key_order_insensitive() -> None:
    fingerprint_a = projection_payload_fingerprint({"title": "t", "body": "b"})
    fingerprint_b = projection_payload_fingerprint({"body": "b", "title": "t"})
    assert fingerprint_a == fingerprint_b
    assert fingerprint_a.startswith("sha256:")


def test_derive_projection_envelope_rejects_unrecognized_projection_kind() -> None:
    with pytest.raises(ProjectionRequirementError):
        _envelope(projection_kind="NOT_A_REAL_KIND")


def test_derive_projection_envelope_rejects_unrecognized_subject_kind() -> None:
    with pytest.raises(ProjectionRequirementError):
        _envelope(subject_ref={"kind": "not_a_real_kind", "id": "X"})


def test_derive_projection_envelope_rejects_unrecognized_artifact_kind() -> None:
    bad_ref = dict(_EXTERNAL_ARTIFACT_REF)
    bad_ref["artifact_kind"] = "not_a_real_kind"
    with pytest.raises(ProjectionRequirementError):
        _envelope(external_artifact_ref=bad_ref)


def test_derived_envelope_is_schema_valid() -> None:
    envelope = _envelope()
    assert envelope["schema_version"] == "0.1"
    assert envelope["projection_envelope_id"].startswith("PROJECTION-")
    assert envelope["projection_envelope_semantic_fingerprint"].startswith("sha256:")
    assert projection_envelope_id(envelope) == envelope["projection_envelope_id"]
    assert (
        projection_envelope_semantic_fingerprint(envelope)
        == envelope["projection_envelope_semantic_fingerprint"]
    )
