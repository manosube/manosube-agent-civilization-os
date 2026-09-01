"""Closed normalized projections defined by the Difference Identity Contract.

Every projection here is total: no field is omitted, and no value is inferred from a
source the contract does not name.
"""

from __future__ import annotations

import re
from typing import Any

from manosube_agent_civilization.observation.errors import ObservationError
from manosube_agent_civilization.observation.normalization import canonical_value

from .canonical import canonical_bytes, canonical_semantic, unordered_set
from .errors import DifferenceError
from .identity import COMPARISON_PROFILE

#: The typed scalar wrappers the Difference Identity Contract declares, and only those.
#:
#: ``DIFFERENCE_IDENTITY.md`` section "expected_value_type" states the total rule as a closed
#: table. A ``{"value_type": ..., "value": ...}`` wrapper appears in it exactly four times --
#: for the types JSON's own shape cannot express. Everything else derives from the value:
#: an *ordinary JSON object* is ``STRUCTURED``, and the two collection types are written
#: with a ``collection_kind`` wrapper, not a ``value_type`` one.
#:
#: Including ``STRUCTURED`` here was a category error with a real consequence: a Target whose
#: literal business value happened to be shaped like ``{"value_type": "STRUCTURED", "value":
#: {...}}`` had its outer object discarded, so a Fact carrying only the inner object
#: satisfied the Target and the required Difference was never derived. A contract test reads
#: the rule out of the Kernel document and asserts this set equals it, in both directions.
TYPED_SCALAR_WRAPPER_TYPES = frozenset(
    {
        "DECIMAL",
        "TIMESTAMP",
        "DURATION",
        "IDENTITY_REFERENCE",
    }
)
SINGLE_VALUE_OPERATORS = frozenset({"equals", "not_equals", "contains"})
KNOWLEDGE_STATUSES = frozenset(
    {"KNOWN", "ABSENT", "EMPTY", "UNKNOWN", "UNOBSERVED", "BLOCKED", "INCOMPLETE", "CONFLICTED"}
)
UNRESOLVED_KNOWLEDGE = frozenset({"UNKNOWN", "UNOBSERVED", "BLOCKED", "INCOMPLETE"})
# Bounded proven absence is evaluable knowledge: ABSENT and EMPTY are conclusions backed
# by bounded Negative Evidence and a complete enumeration, not unresolved observations.
# An unresolved status never joins this set, so NO_RESULT and UNOBSERVED can never become
# proven absence or satisfaction.
PROVEN_ABSENCE = frozenset({"ABSENT", "EMPTY"})
EVALUABLE_KNOWLEDGE = frozenset({"KNOWN"}) | PROVEN_ABSENCE
_DECIMAL = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?")

_NEGATIVE_STATUS_MAP = {
    "NO_RESULT": "UNKNOWN",
    "FAILED": "UNKNOWN",
    "INVALID": "REJECT_OR_QUARANTINE",
}


def negative_knowledge_status(status: str) -> str:
    """Apply the canonical Negative Observation state mapping."""

    return _NEGATIVE_STATUS_MAP.get(status, status)


def derived_value_type(value: Any) -> str:
    """Return the canonical derived type of an untyped JSON value."""

    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "INTEGER"
    if isinstance(value, str):
        return "STRING"
    if isinstance(value, list):
        return "ORDERED_COLLECTION"
    if isinstance(value, dict):
        if value.get("collection_kind") == "ORDERED_LIST":
            return "ORDERED_COLLECTION"
        if value.get("collection_kind") == "UNORDERED_SET":
            return "UNORDERED_COLLECTION"
        return "STRUCTURED"
    return "UNKNOWN"


def normalize_objective_value(value: Any) -> tuple[Any, str]:
    """Split a Target ``expected_value`` into its canonical inner value and declared type.

    Only a contract-declared typed scalar wrapper is unwrapped. Any other object -- however
    much it resembles a wrapper -- is an ordinary structured value and is compared whole.
    """

    if (
        isinstance(value, dict)
        and set(value) == {"value_type", "value"}
        and value["value_type"] in TYPED_SCALAR_WRAPPER_TYPES
    ):
        return value["value"], str(value["value_type"])
    return value, derived_value_type(value)


def value_matches_declared_type(value: Any, value_type: str) -> bool:
    """Return whether *value* conforms to its declared canonical type."""

    return {
        "NULL": value is None,
        "BOOLEAN": isinstance(value, bool),
        "INTEGER": isinstance(value, int) and not isinstance(value, bool),
        "STRING": isinstance(value, str),
        "STRUCTURED": isinstance(value, dict),
        "DECIMAL": isinstance(value, str) and bool(_DECIMAL.fullmatch(value)),
        "TIMESTAMP": isinstance(value, str),
        "DURATION": isinstance(value, str) and value.startswith("P"),
        "IDENTITY_REFERENCE": isinstance(value, dict) and {"kind", "id"} <= value.keys(),
        "ORDERED_COLLECTION": isinstance(value, list)
        or (
            isinstance(value, dict)
            and value.get("collection_kind") == "ORDERED_LIST"
            and isinstance(value.get("members"), list)
        ),
        "UNORDERED_COLLECTION": isinstance(value, list)
        or (
            isinstance(value, dict)
            and value.get("collection_kind") == "UNORDERED_SET"
            and isinstance(value.get("members"), list)
        ),
    }.get(value_type, False)


def project_collection_value(value: Any, value_type: str) -> Any:
    """Project a source wire array into its explicit canonical collection wrapper."""

    if value_type == "ORDERED_COLLECTION" and isinstance(value, list):
        return {"collection_kind": "ORDERED_LIST", "members": [canonical_semantic(i) for i in value]}
    if value_type == "UNORDERED_COLLECTION" and isinstance(value, list):
        return unordered_set(value)
    return canonical_semantic(value)


def reject_noncanonical_typed_value(value: Any, value_type: str) -> None:
    """Reject a declared typed wrapper whose inner value is not already canonical.

    ``DIFFERENCE_IDENTITY.md`` declares the wrapper's inner value as a *canonical* decimal,
    UTC timestamp, duration or identity reference, and says the inner value is **projected**
    into ``expected_value``. Only the shape was checked. A Target declaring
    ``2026-08-30T09:00:00+01:00`` names the same instant as a Fact the Observation element
    normalised to ``2026-08-30T08:00:00Z`` and does not equal it; a malformed decimal,
    duration or identity reference was likewise accepted.

    The canonical form is *not* recomputed onto the Target. The Target is a Human
    Objective's declared value and an identity input: rewriting it would silently change
    what the Objective says and move every Difference identity derived from it. So the
    canonicalisation is compared, and a Target that is not already canonical fails closed.

    The comparison reads the Observation element's own authority, which is what defines a
    canonical value for these types; this module states no second definition.
    """

    if value_type not in TYPED_SCALAR_WRAPPER_TYPES:
        return
    try:
        canonical = canonical_value(value, value_type)
    except ObservationError as error:
        raise DifferenceError(
            f"Target expected_value does not conform to declared {value_type}: {error}"
        ) from error
    if canonical != value:
        raise DifferenceError(
            f"Target expected_value is not in canonical {value_type} form"
        )


def normalize_target_state(predicate: dict[str, Any]) -> dict[str, Any]:
    """Project a Target Predicate into the closed ``normalized_target_state``."""

    expected_value, expected_value_type = normalize_objective_value(predicate["expected_value"])
    reject_noncanonical_typed_value(expected_value, expected_value_type)
    return {
        "subject": predicate["subject"],
        "operator": predicate["operator"],
        "expected_value": canonical_semantic(expected_value),
        "expected_value_type": expected_value_type,
        "observation_scope": predicate["observation_scope"],
        "evidence_requirement": predicate["evidence_requirement"],
        "unknown_policy": predicate["unknown_policy"],
        "criticality": predicate["criticality"],
    }


def effective_boundary(
    scope: dict[str, Any], scope_fingerprint: str, source_snapshot_refs: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return the closed ``OBSERVATION_SCOPE_BOUNDARY`` projection.

    The boundary is generated from the resolved Scope, the Target effective window and the
    Observation source snapshot set. A positive Fact boundary is never reused directly.
    """

    return {
        "kind": "OBSERVATION_SCOPE_BOUNDARY",
        "scope_ref": {"kind": "observation_scope", "id": scope["scope_id"]},
        "resolved_scope_record_sha256": scope_fingerprint,
        "target_effective_window": {
            "start": scope["target_effective_window"]["start"],
            "end": scope["target_effective_window"]["end"],
        },
        "source_snapshot_refs": unordered_set(source_snapshot_refs),
    }


def value_candidate(fact: dict[str, Any], boundary: dict[str, Any]) -> dict[str, Any]:
    """Project one Normalized Fact into a closed observed value candidate."""

    return {
        "value": project_collection_value(fact["value"], fact["value_type"]),
        "value_type": fact["value_type"],
        "unit": fact["unit"],
        "fact_predicate": fact["predicate"],
        "effective_boundary": boundary,
    }


def normalize_observed_state(
    subject: str,
    scope_binding: dict[str, Any],
    boundary: dict[str, Any],
    knowledge_status: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Project State-bound observed input into the closed ``normalized_observed_state``."""

    if knowledge_status not in KNOWLEDGE_STATUSES:
        raise DifferenceError(f"unknown knowledge status: {knowledge_status!r}")
    if knowledge_status != "KNOWN" and knowledge_status != "CONFLICTED" and candidates:
        raise DifferenceError(
            f"knowledge status {knowledge_status} must not carry observed value candidates"
        )
    return {
        "subject": subject,
        "objective_scope_binding": scope_binding,
        "effective_boundary": boundary,
        "knowledge_status": knowledge_status,
        "value_candidates": unordered_set(candidates),
    }


def _collection_members(value: Any) -> list[Any] | None:
    if isinstance(value, list):
        return value
    if (
        isinstance(value, dict)
        and value.get("collection_kind") in {"ORDERED_LIST", "UNORDERED_SET"}
        and isinstance(value.get("members"), list)
    ):
        return list(value["members"])
    return None


def _exact_value_equal(left: Any, right: Any) -> bool:
    return canonical_bytes(left) == canonical_bytes(right)


def _candidate_type_matches_target(candidate: dict[str, Any], target: dict[str, Any]) -> bool:
    operator = target["operator"]
    if operator == "exists":
        return True
    if operator == "contains":
        return candidate["value_type"] in {"ORDERED_COLLECTION", "UNORDERED_COLLECTION"}
    return bool(candidate["value_type"] == target["expected_value_type"])


def target_satisfied(values: list[Any], target: dict[str, Any]) -> bool:
    """Evaluate the Target operator over the observed candidate values."""

    expected = target["expected_value"]
    operator = target["operator"]
    if operator == "equals":
        return bool(values) and all(_exact_value_equal(value, expected) for value in values)
    if operator == "not_equals":
        return bool(values) and all(not _exact_value_equal(value, expected) for value in values)
    if operator == "contains":
        return bool(values) and all(
            (members := _collection_members(value)) is not None
            and any(
                _exact_value_equal(member, expected)
                and value_matches_declared_type(member, target["expected_value_type"])
                for member in members
            )
            for value in values
        )
    if operator == "exists":
        return bool(values)
    if operator == "all":
        return bool(values) and all(_exact_value_equal(value, expected) for value in values)
    if operator == "none":
        return all(not _exact_value_equal(value, expected) for value in values)
    raise DifferenceError(f"unknown Target operator: {operator!r}")


def derive_comparison_and_mismatch(
    observed: dict[str, Any], target: dict[str, Any]
) -> tuple[str, str | None]:
    """Apply the single ordered mismatch rule chain of the Difference Identity Contract."""

    candidates = observed["value_candidates"]["members"]
    values = [item["value"] for item in candidates]
    distinct = {canonical_bytes(value) for value in values}
    operator = target["operator"]
    knowledge = observed["knowledge_status"]
    if knowledge == "CONFLICTED" or (operator in SINGLE_VALUE_OPERATORS and len(distinct) > 1):
        return "UNKNOWN", "CONFLICT"
    if knowledge in UNRESOLVED_KNOWLEDGE:
        return "UNKNOWN", "UNKNOWN"
    if any(not _candidate_type_matches_target(item, target) for item in candidates):
        return "NOT_SATISFIED", "TYPE_MISMATCH"
    comparison = (
        ("SATISFIED" if target_satisfied(values, target) else "NOT_SATISFIED")
        if knowledge in EVALUABLE_KNOWLEDGE
        else "UNKNOWN"
    )
    if not candidates and operator in {"equals", "not_equals", "contains", "exists", "all"}:
        return "NOT_SATISFIED", "MISSING"
    if comparison == "SATISFIED":
        return comparison, None
    if operator == "contains":
        return comparison, "RELATION_MISMATCH"
    if operator == "none":
        return comparison, "UNEXPECTED"
    return comparison, "VALUE_MISMATCH"


def structural_difference(
    observed: dict[str, Any], target: dict[str, Any], comparison: str, mismatch_kind: str
) -> dict[str, Any]:
    """Return the closed ``structural_difference`` projection with no omitted field."""

    # The observed candidates are projected as ORDERED_LIST wrappers whose order is the
    # canonical member order of ``normalized_observed_state.value_candidates``. The order
    # is therefore derived, not incidental: it is stable under any reordering of the
    # source input, while distinct candidates that happen to share a value or a value
    # type are preserved instead of being collapsed by a duplicate-free set.
    candidates = observed["value_candidates"]["members"]
    return {
        "mismatch_kind": mismatch_kind,
        "observed_knowledge_status": observed["knowledge_status"],
        "target_value": target["expected_value"],
        "observed_values": {
            "collection_kind": "ORDERED_LIST",
            "members": [canonical_semantic(item["value"]) for item in candidates],
        },
        "target_value_type": target["expected_value_type"],
        "observed_value_types": {
            "collection_kind": "ORDERED_LIST",
            "members": [str(item["value_type"]) for item in candidates],
        },
        "target_cardinality": None,
        "observed_cardinality": None,
        "comparison_result": comparison,
        "comparison_profile": COMPARISON_PROFILE,
    }
