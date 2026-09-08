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
) -> dict[str, Any]:
    """Return one canonical, schema-valid Projection Envelope record.

    Every argument must already be real: *subject_fingerprint* and
    *projection_payload_fingerprint* must already be recomputed by the caller from the real
    subject/payload (this function does not recompute either -- it only asserts the assembled
    record is internally self-consistent and schema-valid), and *external_artifact_ref* must
    already be what a real :class:`~manosube_agent_civilization.projection.types.
    GitHubAdapter.materialize` call returned. This function mints no external artifact and
    performs no Store I/O of any kind.
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
