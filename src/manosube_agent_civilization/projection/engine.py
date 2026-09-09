"""The one Projection Envelope deriver (Phase 14, Issue #62).

```text
REAL, RESOLVED CANONICAL SUBJECT
→ SUBJECT FINGERPRINT RECOMPUTED (never trusted from a caller)
→ PROJECTION MAPPING KEY (subject + kind + target)
→ PROJECTION PAYLOAD FINGERPRINT RECOMPUTED (never trusted from a caller)
→ CANONICAL PROJECTION ENVELOPE
```

This module builds and schema-validates one Projection Envelope from already-resolved,
already-verified inputs. It resolves nothing itself, calls no Store, no Boot, no Authority,
and no Adapter -- :mod:`~manosube_agent_civilization.projection.route` owns every one of
those calls and is the only caller of :func:`derive_projection_envelope`. This split is the
identical "derivation is pure, resolution is the route's job" discipline every other Kernel
engine in this repository already keeps.
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)

from .errors import ProjectionRequirementError
from .identity import (
    projection_envelope_id,
    projection_envelope_semantic_fingerprint,
    projection_mapping_key,
)
from .types import ARTIFACT_KINDS, PROJECTION_KINDS, SUBJECT_REF_KINDS

PROJECTION_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "projection/"
SCHEMA_VERSION = "0.1"


def derive_projection_envelope(
    *,
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str,
    target_repository: dict[str, Any],
    projection_payload: dict[str, Any],
    projection_payload_fingerprint: str,
    external_artifact_ref: dict[str, Any],
    github_authority_ref: dict[str, Any],
    materialized_at: str,
    claim_token: str,
) -> dict[str, Any]:
    """Return one canonical, schema-valid Projection Envelope record.

    Every argument must already be real: *subject_fingerprint* and
    *projection_payload_fingerprint* must already be recomputed by the caller from the real
    subject/payload (this function does not recompute either -- it only asserts the assembled
    record is internally self-consistent and schema-valid), and *external_artifact_ref* must
    already be what a real :class:`~manosube_agent_civilization.projection.types.
    GitHubAdapter.materialize` call returned. This function mints no external artifact and
    performs no Store I/O of any kind.

    *claim_token* (Structural Review Round 4, Issue #62, P14-R4-F1) is the winning attempt's
    own ``attempt_claim_token`` -- carried on the terminal Envelope itself so a route can later
    tell a genuine same-attempt retry (an identical ``claim_token`` presented again) apart from
    a distinct caller reaching an already-terminal mapping slot. It is deliberately excluded
    from :data:`~manosube_agent_civilization.projection.identity.MAPPING_KEY_FIELDS` -- which
    attempt happened to win never changes *which projection slot* is addressed, so
    ``projection_envelope_id`` stays a pure function of subject/kind/target alone. It is,
    however, deliberately **included** in :data:`~manosube_agent_civilization.projection.
    identity.SEMANTIC_FIELDS` (Structural Review Round 5, Issue #62, P14-R5-F1): the winning
    claim is exactly the terminal fact ``project_to_github``'s own reuse path later trusts to
    classify a caller as the same attempt versus a distinct, explicitly separate semantic
    reuse, so tampering it alone -- leaving every mapping-key field and the payload untouched
    -- must still change ``projection_envelope_semantic_fingerprint`` and so be detectable.
    """

    if projection_kind not in PROJECTION_KINDS:
        raise ProjectionRequirementError(
            f"projection_kind is not a recognized kind: {projection_kind!r}"
        )
    if not isinstance(subject_ref, dict) or subject_ref.get("kind") not in SUBJECT_REF_KINDS:
        raise ProjectionRequirementError(f"subject_ref names an unrecognized kind: {subject_ref!r}")
    if not isinstance(external_artifact_ref, dict) or (
        external_artifact_ref.get("artifact_kind") not in ARTIFACT_KINDS
    ):
        raise ProjectionRequirementError(
            f"external_artifact_ref names an unrecognized artifact_kind: {external_artifact_ref!r}"
        )

    envelope = {
        "schema_version": SCHEMA_VERSION,
        "subject_ref": dict(subject_ref),
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": dict(target_repository),
        "projection_payload": projection_payload,
        "projection_payload_fingerprint": projection_payload_fingerprint,
        "external_artifact_ref": dict(external_artifact_ref),
        "github_authority_ref": dict(github_authority_ref),
        "materialized_at": materialized_at,
        "claim_token": claim_token,
    }
    envelope["projection_envelope_id"] = projection_envelope_id(envelope)
    envelope["projection_envelope_semantic_fingerprint"] = projection_envelope_semantic_fingerprint(
        envelope
    )

    expected_mapping_key = projection_mapping_key(
        subject_ref, subject_fingerprint, projection_kind, target_repository
    )
    if envelope["projection_envelope_id"] != expected_mapping_key:
        raise ProjectionRequirementError(
            "assembled envelope's own recomputed identity does not equal the mapping key its "
            f"own fields imply: {envelope['projection_envelope_id']!r} != {expected_mapping_key!r}"
        )

    _validate_canonical_record(
        envelope, "projection_envelope.schema.json", base=PROJECTION_SCHEMA_BASE
    )
    return envelope


def _derive_claim_record(
    *,
    id_field: str,
    schema_name: str,
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str,
    target_repository: dict[str, Any],
    project_id: str,
    materialized_at: str,
    claim_token: str,
) -> dict[str, Any]:
    """Shared body for :func:`derive_projection_intent` and
    :func:`derive_projection_materialize_attempt` (Structural Review Round 2, Issue #62,
    P14-R2-F2) -- both are the identical shape, differing only in which durable fact they
    record and therefore which record kind/id field/schema they use. Each record's own id is
    *not* a hash of its full content the way every other Kernel record's own id is -- it is
    always exactly :func:`~manosube_agent_civilization.projection.identity.
    projection_mapping_key`, the *slot* this record claims, so a second attempt at the
    identical slot commits at the identical (kind, id) and is caught by the Store's own
    ``RecordConflictError`` the moment its content differs -- that collision *is* the
    concurrency barrier this pair of record kinds exists to provide.

    *claim_token* (Structural Review Round 3, Issue #62, P14-R3-F1) is the explicit attempt
    identity that content -- never ``materialized_at`` alone, which two genuinely distinct
    callers may legitimately share (a caller-supplied instant, not a uniqueness primitive).
    Two attempts sharing an identical ``materialized_at`` but carrying *different*
    ``claim_token`` values now produce genuinely different record content at the identical
    (kind, id) slot, so the Store's own same-key/different-content rejection distinguishes
    them correctly; two attempts sharing both fields are, and only then are, treated as the
    identical caller's own idempotent retry.
    """

    if projection_kind not in PROJECTION_KINDS:
        raise ProjectionRequirementError(
            f"projection_kind is not a recognized kind: {projection_kind!r}"
        )
    if not isinstance(subject_ref, dict) or subject_ref.get("kind") not in SUBJECT_REF_KINDS:
        raise ProjectionRequirementError(f"subject_ref names an unrecognized kind: {subject_ref!r}")

    mapping_key = projection_mapping_key(
        subject_ref, subject_fingerprint, projection_kind, target_repository
    )
    record = {
        "schema_version": SCHEMA_VERSION,
        id_field: mapping_key,
        "project_id": project_id,
        "subject_ref": dict(subject_ref),
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": dict(target_repository),
        "materialized_at": materialized_at,
        "claim_token": claim_token,
    }
    _validate_canonical_record(record, schema_name, base=PROJECTION_SCHEMA_BASE)
    return record


def derive_projection_intent(
    *,
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str,
    target_repository: dict[str, Any],
    project_id: str,
    materialized_at: str,
    claim_token: str,
) -> dict[str, Any]:
    """Return one canonical, schema-valid Projection Intent record -- the durable claim a
    route commits *before* ever calling ``adapter.find_by_correlation_key``/``materialize``
    for a given (subject, kind, target) slot (Structural Review Round 2, P14-R2-F2). Its id
    equals that slot's own :func:`~manosube_agent_civilization.projection.identity.
    projection_mapping_key`, never a hash of the full record. *claim_token* is the explicit
    attempt identity Structural Review Round 3 (P14-R3-F1) requires -- see
    :func:`_derive_claim_record`."""

    return _derive_claim_record(
        id_field="projection_intent_id",
        schema_name="projection_intent.schema.json",
        subject_ref=subject_ref,
        subject_fingerprint=subject_fingerprint,
        projection_kind=projection_kind,
        target_repository=target_repository,
        project_id=project_id,
        materialized_at=materialized_at,
        claim_token=claim_token,
    )


def derive_projection_materialize_attempt(
    *,
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str,
    target_repository: dict[str, Any],
    project_id: str,
    materialized_at: str,
    claim_token: str,
) -> dict[str, Any]:
    """Return one canonical, schema-valid Projection Materialize Attempt record -- the
    durable marker a route commits *before* ever calling ``adapter.materialize`` itself
    (Structural Review Round 2, P14-R2-F2), once it already owns the slot's
    :func:`derive_projection_intent` claim. Its presence with no discoverable external
    artifact and no committed Envelope is the genuinely ambiguous state a route must refuse
    to resolve by blindly re-calling ``materialize`` (see :class:`~.errors.
    ProjectionReconciliationRequiredError`). *claim_token* is the explicit attempt identity
    Structural Review Round 3 (P14-R3-F1) requires -- see :func:`_derive_claim_record`."""

    return _derive_claim_record(
        id_field="projection_materialize_attempt_id",
        schema_name="projection_materialize_attempt.schema.json",
        subject_ref=subject_ref,
        subject_fingerprint=subject_fingerprint,
        projection_kind=projection_kind,
        target_repository=target_repository,
        project_id=project_id,
        materialized_at=materialized_at,
        claim_token=claim_token,
    )
