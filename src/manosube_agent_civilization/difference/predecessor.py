"""The typed validation boundary for caller-supplied predecessor context.

Three successive reviews found the same shape of defect: a carried record was accepted
because *some* check happened to cover the field that was forged, and rejected only when a
later review named the next uncovered field. The cause was structural -- predecessor
context was admitted by a growing set of partial checks rather than by a boundary that
every record must cross.

This module is that boundary. The record types, their canonical schemas and their identity
authorities live once in :mod:`difference.conformance`; this module states which of them a
predecessor context may carry, and puts each supplied record through the same ordered gate:

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
recorded. Nothing is returned before both gates pass, and nothing is ever repaired.

The same table also backs the final output conformance gate, so a record type cannot be
admitted on one route and unvalidated on the other.
"""

from __future__ import annotations

from typing import Any

from . import readability
from .canonical import canonical_bytes, content_address
from .conformance import (
    CARRIED_SECTIONS,
    RECORD_TYPES,
    validate_typed_record,
)
from .errors import DifferenceError, IdentityCollisionError
from .identity import (
    closure_policy_id,
    difference_id as derive_difference_id,
    lifecycle_event_id,
)
from .lifecycle import blocker_payload_errors, next_observation_binding_errors
from .validation import SCHEMA_BASE, require_schema_version, validate_record

DIFFERENCE_SCHEMA_BASE = SCHEMA_BASE + "difference/"

#: Every predecessor-context section the Difference Engine accepts, from the single
#: canonical record-type table. A section absent from it is rejected rather than silently
#: ignored, so a new carried type cannot be introduced without passing the boundary.
CARRIED_TYPES: dict[str, Any] = {
    section: RECORD_TYPES[type_name] for section, type_name in CARRIED_SECTIONS.items()
}

#: Types whose semantic contract belongs to a later phase. For these the boundary proves
#: schema conformance, identity where an authority exists, and reference resolution -- and
#: claims nothing more. Their own rules are their owner's to enforce.
LATER_PHASE_SECTIONS: frozenset[str] = frozenset(
    {
        "evaluations",
        "reopen_condition_evaluations",
        "candidate_completion_records",
        "candidate_claim_evaluation_events",
        "invariant_evaluations",
        "evidence_sufficiency_results",
        "changes",
        "reflow_transitions",
    }
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
    section for section, carried in CARRIED_TYPES.items() if carried.identity is None
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


#: The predecessor's own key set, declared once and closed in both directions. A closed key
#: set is two rules -- no section the boundary does not know, and no section it does know
#: missing -- and only the first was ever stated, so the required ones were indexed before
#: anything established they were there. ``context`` is genuinely optional: a predecessor
#: whose lineage the Observation bundle supplies in full carries none.
PREDECESSOR_SECTIONS: frozenset[str] = frozenset({"difference", "events", "context"})
REQUIRED_PREDECESSOR_SECTIONS: frozenset[str] = frozenset({"difference", "events"})


def _describe(section: str, identity: Any) -> str:
    return f"{section}[{identity}]"


def validate_carried_records(context: dict[str, Any]) -> None:
    """Apply steps 1-6 of the boundary to one caller-supplied predecessor context.

    Every check here is decided by the record alone, so it runs before any record is
    merged into the returned bundle.

    The first thing the boundary owes is that there is something to apply itself to. It
    read the context's own key set before establishing the context was a mapping, which is
    the same defect as the ones below it, one level further out.
    """

    if not isinstance(context, dict):
        raise DifferenceError("predecessor context is not a canonical object")
    unknown = set(context) - set(CARRIED_TYPES) - BUNDLE_ENVELOPE_SECTIONS
    if unknown:
        raise DifferenceError(
            f"predecessor context carries unknown sections: {sorted(unknown)}"
        )

    for section, carried in CARRIED_TYPES.items():
        records = context.get(section, [])
        if not readability.is_record_list(records):
            raise DifferenceError(f"predecessor context section is not a list: {section}")
        seen: dict[str, bytes] = {}
        for record in records:
            if readability.of_record_by_key(record, carried.key).reason == readability.NOT_AN_OBJECT:
                raise DifferenceError(f"predecessor context record is not an object: {section}")
            validate_typed_record(
                record,
                CARRIED_SECTIONS[section],
                _describe(section, record.get(carried.key)),
            )
            identity = record[carried.key]
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
