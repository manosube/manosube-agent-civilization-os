"""The single typed validation boundary for caller-supplied predecessor context.

Three successive reviews found the same shape of defect: a carried record was accepted
because *some* check happened to cover the field that was forged, and rejected only when a
later review named the next uncovered field. The cause was structural — predecessor context
was admitted by a growing set of partial checks rather than by a boundary that every record
must cross.

This module is that boundary. It states, once, which record types the Difference Engine is
permitted to carry, and it puts each of them through the same ordered gate:

```text
1. group every supplied record by its canonical type
2. reject an unknown section outright
3. schema-validate every record against its canonical schema
4. recompute every content-addressed identity with its existing single authority
5. enforce the type-specific cross-field and status invariants
6. reject same-identity/different-payload records inside the context itself
7. (after absorption) resolve every reference the carried records carry
8. only then is a record part of the returned bundle
```

Steps 1-6 need nothing but the context itself and run **before** any record is merged.
Step 7 runs on the merged set, because a reference may legitimately resolve to a record the
current derivation supplies rather than one the caller re-sent -- the nuance ADR-0005
recorded. Nothing is returned before both gates pass, and nothing is ever repaired: a
record that fails is a forgery or an incomplete lineage, and either fails closed.

Where a record belongs to a later phase whose semantic contract this phase does not own,
the boundary schema-validates it, recomputes any identity a current authority provides, and
requires its references to resolve. It does **not** invent semantics for it, and
`LATER_PHASE_SECTIONS` names exactly those types so the non-claim is explicit rather than
implied.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from manosube_agent_civilization.observation.identity import (
    binding_identity,
    deterministic_id,
    fact_evaluation_identity,
    fact_identity,
    observation_identity,
)

from .canonical import canonical_bytes, content_address
from .errors import DifferenceError, IdentityCollisionError
from .identity import (
    closure_policy_id,
    difference_id as derive_difference_id,
    lifecycle_event_id,
)
from .lifecycle import blocker_payload_errors, next_observation_binding_errors
from .validation import SCHEMA_BASE, require_schema_version, validate_record

DIFFERENCE_SCHEMA_BASE = SCHEMA_BASE + "difference/"
OBSERVATION_SCHEMA_BASE = SCHEMA_BASE + "observation/"


def _negative_observation_identity(record: dict[str, Any]) -> str:
    return deterministic_id(
        "NEG",
        {
            "observation_id": record["observation_id"],
            "subject": record["subject"],
            "predicate": record["predicate"],
            "effective_boundary": record["effective_boundary"],
        },
    )


def _negative_evaluation_identity(record: dict[str, Any]) -> str:
    return deterministic_id(
        "NEG-EVAL",
        {
            "negative_observation_id": record["negative_observation_id"],
            "evaluation_revision": record["evaluation_revision"],
        },
    )


def _request_identity(record: dict[str, Any]) -> str:
    return content_address("OBS-REQ-", record, "observation_request_id")


def _method_identity(record: dict[str, Any]) -> str:
    return content_address("OBS-METHOD-", record, "observation_method_id")


def _policy_identity(record: dict[str, Any]) -> str:
    subject = record["subject_difference_ref"]
    identity = subject.get("id") if isinstance(subject, dict) else None
    return closure_policy_id(record["policy_semantic_fingerprint"], str(identity))


@dataclass(frozen=True)
class CarriedType:
    """One canonical record type the Engine is permitted to carry."""

    key: str
    #: ``None`` when this repository defines no canonical schema for the type yet.
    schema: str | None
    base: str
    identity: Callable[[dict[str, Any]], str] | None = None
    #: Reference fields whose targets must resolve, as ``field -> section``.
    references: tuple[tuple[str, str], ...] = ()
    later_phase: bool = False


#: Every predecessor-context section the Difference Engine accepts. A section absent from
#: this table is rejected rather than silently ignored, so a new carried type cannot be
#: introduced without passing the boundary.
CARRIED_TYPES: dict[str, CarriedType] = {
    "observations": CarriedType(
        "observation_id", "observation.schema.json", OBSERVATION_SCHEMA_BASE,
        observation_identity,
    ),
    "normalized_facts": CarriedType(
        "fact_id", "normalized_fact.schema.json", OBSERVATION_SCHEMA_BASE, fact_identity,
    ),
    "fact_observation_bindings": CarriedType(
        "binding_id", "fact_observation_binding.schema.json", OBSERVATION_SCHEMA_BASE,
        binding_identity,
    ),
    "fact_evaluations": CarriedType(
        "evaluation_id", "fact_evaluation.schema.json", OBSERVATION_SCHEMA_BASE,
        fact_evaluation_identity,
    ),
    "negative_observations": CarriedType(
        "negative_observation_id", "negative_observation.schema.json", OBSERVATION_SCHEMA_BASE,
        _negative_observation_identity,
    ),
    "negative_observation_evaluations": CarriedType(
        "evaluation_id", "negative_observation_evaluation.schema.json", OBSERVATION_SCHEMA_BASE,
        _negative_evaluation_identity,
    ),
    "observation_scopes": CarriedType(
        "scope_id", "observation_scope.schema.json", OBSERVATION_SCHEMA_BASE,
    ),
    "objective_revisions": CarriedType(
        "objective_revision_id", "objective_revision.schema.json", SCHEMA_BASE + "objective/",
    ),
    "policies": CarriedType(
        "closure_policy_id", "closure_policy.schema.json", DIFFERENCE_SCHEMA_BASE,
        _policy_identity,
    ),
    "next_observation_requests": CarriedType(
        "observation_request_id", "next_observation_request.schema.json", DIFFERENCE_SCHEMA_BASE,
        _request_identity,
    ),
    "observation_methods": CarriedType(
        "observation_method_id", "observation_method.schema.json", DIFFERENCE_SCHEMA_BASE,
        _method_identity,
    ),
    "evaluations": CarriedType(
        "closure_evaluation_id", "closure_evaluation.schema.json", DIFFERENCE_SCHEMA_BASE,
        later_phase=True,
    ),
    "reopen_condition_evaluations": CarriedType(
        "evaluation_id", "reopen_condition_evaluation.schema.json", DIFFERENCE_SCHEMA_BASE,
        later_phase=True,
    ),
    "candidate_completion_records": CarriedType(
        "completion_id", "candidate_completion_record.schema.json", DIFFERENCE_SCHEMA_BASE,
        later_phase=True,
    ),
    "candidate_claim_evaluation_events": CarriedType(
        "event_id", "candidate_claim_evaluation_event.schema.json", DIFFERENCE_SCHEMA_BASE,
        later_phase=True,
    ),
    "invariant_evaluations": CarriedType(
        "evaluation_id", "invariant_evaluation.schema.json", DIFFERENCE_SCHEMA_BASE,
        later_phase=True,
    ),
    "evidence_sufficiency_results": CarriedType(
        "evidence_sufficiency_id", "evidence_sufficiency_result.schema.json",
        DIFFERENCE_SCHEMA_BASE, later_phase=True,
    ),
    # 01_SCHEMA/change/ and 01_SCHEMA/reflow/ are empty in v0.1: these two types have no
    # canonical schema in this repository yet, so there is nothing to validate them
    # against. They are still admitted only as carried provenance, are still subject to
    # identity-collision and reference-resolution gates, and the non-claim is explicit.
    "changes": CarriedType("change_id", None, "", later_phase=True),
    "reflow_transitions": CarriedType("transaction_id", None, "", later_phase=True),
}

#: Types whose semantic contract belongs to a later phase. For these the boundary proves
#: schema conformance, identity where an authority exists, and reference resolution -- and
#: claims nothing more. Their own rules are their owner's to enforce.
LATER_PHASE_SECTIONS: frozenset[str] = frozenset(
    section for section, carried in CARRIED_TYPES.items() if carried.later_phase
)

#: Sections this repository defines no canonical schema for. They are carried as opaque
#: provenance: identity collisions and unresolved references still fail closed, but no
#: schema or semantic conformance is claimed for them.
NO_CANONICAL_SCHEMA_SECTIONS: frozenset[str] = frozenset(
    section for section, carried in CARRIED_TYPES.items() if carried.schema is None
)

#: Sections carried without a content-addressed identity authority reachable in this phase.
#: A caller-assigned identity is proven only to name its own record, not to be derivable.
CALLER_ASSIGNED_IDENTITY_SECTIONS: frozenset[str] = frozenset(
    section
    for section, carried in CARRIED_TYPES.items()
    if carried.identity is None
)


#: The returned bundle's own envelope and derived outputs. Handing a previous bundle back
#: as predecessor context is the canonical usage, so these keys are accepted and ignored.
#: They are never carried: a Difference, a lifecycle event or a Supersession Relation
#: enters the returned bundle only through the predecessor's own ``difference`` and
#: ``events`` keys, or by being derived here. Ignoring them is fail-safe -- no unvalidated
#: record is admitted by that route.
BUNDLE_ENVELOPE_SECTIONS: frozenset[str] = frozenset(
    {
        "schema_version",
        "identity_profile",
        "comparison_profile",
        "normalization_profile",
        "current_state_ref",
        "differences",
        "events",
        "supersession_relations",
        "materialized_status",
        "satisfied_target_predicates",
    }
)


def _describe(section: str, identity: Any) -> str:
    return f"{section}[{identity}]"


def validate_carried_records(context: dict[str, Any]) -> None:
    """Apply steps 1-6 of the boundary to one caller-supplied predecessor context.

    Every check here is decided by the record alone, so it runs before any record is
    merged into the returned bundle.
    """

    unknown = set(context) - set(CARRIED_TYPES) - BUNDLE_ENVELOPE_SECTIONS
    if unknown:
        raise DifferenceError(
            f"predecessor context carries unknown sections: {sorted(unknown)}"
        )

    for section, carried in CARRIED_TYPES.items():
        records = context.get(section, [])
        if not isinstance(records, list):
            raise DifferenceError(f"predecessor context section is not a list: {section}")
        seen: dict[str, bytes] = {}
        for record in records:
            if not isinstance(record, dict):
                raise DifferenceError(f"predecessor context record is not an object: {section}")
            if carried.schema is not None:
                validate_record(record, carried.schema, base=carried.base)
                require_schema_version(record, _describe(section, record.get(carried.key)))
            identity = record.get(carried.key)
            if not isinstance(identity, str) or not identity:
                raise DifferenceError(
                    f"carried record has no canonical identity: {section}.{carried.key}"
                )
            if carried.identity is not None and identity != carried.identity(record):
                raise IdentityCollisionError(
                    f"carried record identity does not recompute: "
                    f"{_describe(section, identity)}"
                )
            payload = canonical_bytes(record)
            existing = seen.get(identity)
            if existing is not None and existing != payload:
                raise IdentityCollisionError(
                    f"same-ID different-payload conflict inside predecessor context: "
                    f"{_describe(section, identity)}"
                )
            seen[identity] = payload


def validate_carried_difference(difference: dict[str, Any]) -> None:
    """Validate one carried Difference record: schema, then identity, then payload.

    Identity recomputation covers only the closed semantic identity tuple, so a caller can
    retain ``difference_id`` while corrupting ``impact``, ``risk_class``,
    ``authority_required`` or another non-identity field. The canonical schema is what
    decides those, and it is applied before the record is read or copied.
    """

    validate_record(difference, "difference.schema.json", base=DIFFERENCE_SCHEMA_BASE)
    require_schema_version(difference, f"difference {difference.get('difference_id')}")
    if difference["difference_id"] != derive_difference_id(difference):
        raise IdentityCollisionError("predecessor Difference identity does not recompute")
    expected_policy = closure_policy_id(
        difference["closure_policy"]["semantic_fingerprint"], difference["difference_id"]
    )
    if difference["closure_policy"]["id"] != expected_policy:
        raise IdentityCollisionError(
            "predecessor Closure Policy identity does not recompute: "
            f"{difference['closure_policy']['id']}"
        )


def validate_carried_event(
    event: dict[str, Any],
    difference: dict[str, Any] | None,
    requests: dict[str, dict[str, Any]] | None = None,
    methods: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Validate one carried lifecycle event's schema, identity and status payload.

    The blocker payload and the Next Observation Request binding sit **outside** lifecycle
    event identity, so a schema-valid event can retain its ``difference_event_id`` while
    either is forged. Both are decided by the single shared lifecycle authority that the
    independent cross-record validator also uses, so no second rule set exists.
    """

    validate_record(
        event, "difference_lifecycle_event.schema.json", base=DIFFERENCE_SCHEMA_BASE
    )
    require_schema_version(event, f"event {event.get('difference_event_id')}")
    if event["difference_event_id"] != lifecycle_event_id(event):
        raise DifferenceError(
            f"predecessor event identity does not recompute: {event['difference_event_id']}"
        )
    if difference is not None and event["difference_id"] != difference["difference_id"]:
        raise DifferenceError(
            f"predecessor event names another Difference: {event['difference_event_id']}"
        )
    errors = blocker_payload_errors(event, difference)
    if requests is not None and methods is not None:
        errors.extend(
            next_observation_binding_errors(
                event, difference, requests, methods, content_address
            )
        )
    if errors:
        raise DifferenceError(f"carried lifecycle event payload is invalid: {sorted(errors)[0]}")
