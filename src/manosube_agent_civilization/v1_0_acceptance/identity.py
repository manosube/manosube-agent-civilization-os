"""Deterministic identity and content-addressing for the v1.0 Acceptance package
(Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

Follows the same narrow-id/broad-fingerprint split every other package's own
`identity.py` in this repository establishes: the *id* excludes genuinely
nondeterministic fields (`generated_at`) so a same-body re-commit collides at the
identical slot (idempotent replay); the *semantic fingerprint* is a full content
address over every field, the record's own tamper-detection value.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

#: A v1.0 acceptance bundle's own identity: every predeclared field except
#: `schema_version` and `generated_at` -- a change to the bound repository/project
#: identity, any Gate 22 rederivation result, Difference disposition, or release
#: identity mints a genuinely new bundle identity, never a same-id collision across a
#: materially different acceptance state.
ACCEPTANCE_BUNDLE_ID_FIELDS: tuple[str, ...] = (
    "repository_project",
    "authorized_base_main_sha",
    "delivery_head",
    "gate_22_predicate_matrix",
    "v1_0_blocking_difference_disposition",
    "negative_control_results",
    "release_identity",
)

ACCEPTANCE_BUNDLE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    *ACCEPTANCE_BUNDLE_ID_FIELDS,
    "generated_at",
)


def _digest(value: Any, fields: tuple[str, ...]) -> str:
    if not isinstance(value, Mapping):
        raise TypeError(f"expected a mapping, got {type(value).__name__}")
    projected = {field: value[field] for field in fields if field in value}
    return hashlib.sha256(canonical_json_bytes(projected)).hexdigest()


def compute_acceptance_bundle_id(bundle: Mapping[str, Any]) -> str:
    """The bundle's narrow identity -- excludes `generated_at`."""
    return _digest(bundle, ACCEPTANCE_BUNDLE_ID_FIELDS)


def compute_acceptance_bundle_semantic_fingerprint(bundle: Mapping[str, Any]) -> str:
    """The bundle's full content address, including `generated_at`."""
    return _digest(bundle, ACCEPTANCE_BUNDLE_SEMANTIC_FIELDS)


__all__ = [
    "ACCEPTANCE_BUNDLE_ID_FIELDS",
    "ACCEPTANCE_BUNDLE_SEMANTIC_FIELDS",
    "compute_acceptance_bundle_id",
    "compute_acceptance_bundle_semantic_fingerprint",
]
