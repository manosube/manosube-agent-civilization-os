"""Deterministic Multi-Agent Dynamic Execution identities (Phase 19, Issue #77).

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- and this
module reads it rather than restating it, exactly as every other owner's own ``identity.py``
already does.

**A disclosed deviation from the usual "id == full-content hash" convention.** Every other
identity module in this repository computes a record's own ``<kind>_id`` from a projection of
*the whole record* (minus the two digest fields themselves), so "the same record" and "the same
content" are the same fact. Five of this package's six kinds deliberately use a *narrower*
"natural key" projection for their own ``<kind>_id`` instead -- the fields that name *which slot
of which plan this is*, never the outcome or timing those slots later carry:

```text
multi_agent_slot_output_id              <- (schema_version, project_id, plan_ref, slot_index,
                                             attempt_ordinal)      == the attempt's own identity
multi_agent_agent_release_receipt_id    <- (schema_version, project_id, plan_ref, slot_index)
multi_agent_conflict_set_id             <- (schema_version, project_id, plan_ref)
multi_agent_evidence_aggregation_input_id <- (schema_version, project_id, plan_ref)
multi_agent_orchestration_receipt_id    <- (schema_version, project_id, plan_ref)
```

Each kind's own ``<kind>_semantic_fingerprint`` still covers the *complete* record (every field
except the two digest fields), so full-content tamper detection is exactly as strong as
elsewhere -- a record whose outcome, timing, or membership was altered after commit is still
caught, by the fingerprint recompute, independently of its own narrow id.

This is deliberate, and it is what makes three of P19-C9's own requirements *native Store
behaviour* rather than application-level bookkeeping this package would otherwise have to
reimplement:

```text
REPLAY WITHOUT RE-RUNNING   resolving a slot's own attempt_id before ever constructing an Agent
                            or calling an adapter is a plain Store lookup by primary key, not a
                            secondary index this package must build and keep consistent.
CONFLICTING REUSE REFUSES   two attempts, release receipts, conflict sets, aggregation inputs
                            or orchestration receipts for the identical natural key, but with
                            genuinely different content, collide at the Store's own
                            content-addressed commit path (``RecordConflictError``) -- refused
                            by the Store itself, never by a bespoke equality check here.
ONE PER (PLAN, SLOT) / PLAN a slot has exactly one attempt (this delivery's own single-attempt-
                            per-slot model, see ``attempt_ordinal``'s own docstring below), and
                            a plan has exactly one conflict set, aggregation input and
                            orchestration receipt -- exactly what these five kinds' own narrow
                            keys already assert as a fact about the Store, not merely as a
                            runtime convention this package promises to honour.
```

:func:`multi_agent_dynamic_execution_plan_id` is the one exception, and is **not** a deviation:
P19-C2 itself requires "every field that can widen execution or change provenance" to
participate in the plan's own identity, so the plan's ``<kind>_id`` is the ordinary full-content
projection every other Kernel record already uses.
"""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .errors import MultiAgentRequirementError

#: Every field a Multi-Agent Dynamic Execution Plan's own identity and semantic fingerprint are
#: computed over -- the complete record minus the two digest fields themselves, so tampering
#: any field (the Boot snapshot it was opened against, the Difference it is about, the exact
#: slot/capability assignment, the shared Model Work Unit it binds, the reproduced Authority
#: reference, the admitted adapter identity, the ordering/bounds/policy declarations, or the
#: validity window) is detectable by either digest.
PLAN_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "boot_state_revision",
    "boot_semantic_fingerprint",
    "difference_ref",
    "capability_selection_fingerprint",
    "slots",
    "model_work_unit_ref",
    "authority_ref",
    "adapter_identity",
    "execution_order",
    "execution_bounds",
    "conflict_policy",
    "release_policy",
    "opened_at",
    "expires_at",
)

#: The narrow, natural-key projection every one of a slot's own attempt records addresses --
#: see this module's own docstring for why this is deliberately narrower than "every field".
SLOT_OUTPUT_KEY_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "plan_ref",
    "slot_index",
    "attempt_ordinal",
)

#: Every field a Multi-Agent Slot Output's own semantic fingerprint is computed over -- the
#: complete record minus the two digest fields themselves.
SLOT_OUTPUT_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "plan_ref",
    "slot_index",
    "capability",
    "attempt_id",
    "attempt_ordinal",
    "model_execution_envelope_ref",
    "outcome",
    "result_fingerprint",
    "outcome_detail",
    "started_at",
    "ended_at",
)

#: The narrow, natural-key projection a slot's own release receipt addresses -- one release per
#: (plan, slot), never per attempt (this delivery releases the Agent exactly once per slot,
#: regardless of which attempt ordinal it executed).
RELEASE_RECEIPT_KEY_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "plan_ref",
    "slot_index",
)

RELEASE_RECEIPT_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "plan_ref",
    "slot_index",
    "attempt_id",
    "release_status",
    "released_at",
)

#: The narrow, natural-key projection the three plan-scoped terminal records (conflict set,
#: aggregation input, orchestration receipt) each address -- one of each per plan.
PLAN_KEYED_FIELDS: tuple[str, ...] = ("schema_version", "project_id", "plan_ref")

CONFLICT_SET_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "plan_ref",
    "considered_slot_output_refs",
    "members",
)

AGGREGATION_INPUT_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "plan_ref",
    "conflict_set_ref",
    "admitted_slot_output_refs",
    "unresolved_capabilities",
    "absent_slot_output_refs",
    "release_receipt_refs",
)

ORCHESTRATION_RECEIPT_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "plan_ref",
    "slot_output_refs",
    "release_receipt_refs",
    "conflict_set_ref",
    "aggregation_input_ref",
    "evidence_refs",
    "orchestration_outcome",
    "completed_at",
)


def _projection(
    record: dict[str, Any], fields: tuple[str, ...], record_kind: str
) -> dict[str, Any]:
    missing = [field for field in fields if field not in record]
    if missing:
        raise MultiAgentRequirementError(
            f"{record_kind} carries no readable {', '.join(missing)} -- its own identity cannot "
            "be recomputed"
        )
    return {field: record[field] for field in fields}


def _address(prefix: str, projection: dict[str, Any]) -> str:
    return prefix + hashlib.sha256(canonical_json_bytes(projection)).hexdigest().upper()


def _digest(projection: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def multi_agent_dynamic_execution_plan_id(plan: dict[str, Any]) -> str:
    """The content address of a canonical Multi-Agent Dynamic Execution Plan -- a pure function
    of the complete, real record content, never of a caller-declared value (P19-C2)."""

    return _address(
        "MULTI-AGENT-PLAN-",
        _projection(plan, PLAN_SEMANTIC_FIELDS, "multi_agent_dynamic_execution_plan"),
    )


def multi_agent_dynamic_execution_plan_semantic_fingerprint(plan: dict[str, Any]) -> str:
    """The digest of a Multi-Agent Dynamic Execution Plan's full meaning -- the identical
    projection :func:`multi_agent_dynamic_execution_plan_id` hashes."""

    return _digest(_projection(plan, PLAN_SEMANTIC_FIELDS, "multi_agent_dynamic_execution_plan"))


def capability_selection_fingerprint(
    slots: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> str:
    """The content-addressed fingerprint of the exact ``(capability, slot_index)`` tuple this
    plan's own selection derived (P19-C1/P19-C2) -- addressing the *derivation's own output*,
    never only its input, so a tampered slot list is independently detectable even if the
    resolved Difference's own ``risk_class`` were somehow left unchanged."""

    payload = {
        "slots": [
            {"slot_index": int(slot["slot_index"]), "capability": str(slot["capability"])}
            for slot in slots
        ]
    }
    return _digest(payload)


def multi_agent_attempt_id(
    *,
    plan_ref: dict[str, Any],
    slot_index: int,
    attempt_ordinal: int,
    project_id: str,
    schema_version: str,
) -> str:
    """The content address of one attempt identity -- ``(project_id, plan_ref, slot_index,
    attempt_ordinal)`` -- computed *before* any Agent is constructed or any adapter is reached,
    exactly as :func:`~manosube_agent_civilization.model_runtime.identity.
    model_execution_request_identity` is computable before its own adapter call.

    This is the value P19-C9's own "conflicting reuse of a plan, slot, or attempt identity must
    refuse" actually checks: it is also this record's own primary Store key (see this module's
    own docstring), so resolving it is how a replayed call finds the already-recorded attempt
    without ever re-running it.
    """

    payload = {
        "schema_version": schema_version,
        "project_id": project_id,
        "plan_ref": dict(plan_ref),
        "slot_index": int(slot_index),
        "attempt_ordinal": int(attempt_ordinal),
    }
    return _address("MULTI-AGENT-ATTEMPT-", payload)


def multi_agent_slot_output_id(slot_output: dict[str, Any]) -> str:
    """The narrow, natural-key content address of a Multi-Agent Slot Output -- see this
    module's own docstring for why this is not a full-content projection."""

    return _address(
        "MULTI-AGENT-SLOT-OUTPUT-",
        _projection(slot_output, SLOT_OUTPUT_KEY_FIELDS, "multi_agent_slot_output"),
    )


def multi_agent_slot_output_semantic_fingerprint(slot_output: dict[str, Any]) -> str:
    """The full-content digest of a Multi-Agent Slot Output -- covers every field, including
    the outcome and result fingerprint the narrow id above deliberately excludes."""

    return _digest(_projection(slot_output, SLOT_OUTPUT_SEMANTIC_FIELDS, "multi_agent_slot_output"))


def multi_agent_agent_release_receipt_id(receipt: dict[str, Any]) -> str:
    """The narrow, natural-key content address of a Multi-Agent Agent Release Receipt -- one
    per ``(plan, slot)``."""

    return _address(
        "MULTI-AGENT-RELEASE-",
        _projection(receipt, RELEASE_RECEIPT_KEY_FIELDS, "multi_agent_agent_release_receipt"),
    )


def multi_agent_agent_release_receipt_semantic_fingerprint(receipt: dict[str, Any]) -> str:
    return _digest(
        _projection(receipt, RELEASE_RECEIPT_SEMANTIC_FIELDS, "multi_agent_agent_release_receipt")
    )


def multi_agent_conflict_set_id(conflict_set: dict[str, Any]) -> str:
    """The narrow, natural-key content address of a Multi-Agent Conflict Set -- one per plan."""

    return _address(
        "MULTI-AGENT-CONFLICT-",
        _projection(conflict_set, PLAN_KEYED_FIELDS, "multi_agent_conflict_set"),
    )


def multi_agent_conflict_set_semantic_fingerprint(conflict_set: dict[str, Any]) -> str:
    return _digest(
        _projection(conflict_set, CONFLICT_SET_SEMANTIC_FIELDS, "multi_agent_conflict_set")
    )


def multi_agent_evidence_aggregation_input_id(aggregation_input: dict[str, Any]) -> str:
    """The narrow, natural-key content address of a Multi-Agent Evidence Aggregation Input --
    one per plan."""

    return _address(
        "MULTI-AGENT-AGGREGATION-",
        _projection(aggregation_input, PLAN_KEYED_FIELDS, "multi_agent_evidence_aggregation_input"),
    )


def multi_agent_evidence_aggregation_input_semantic_fingerprint(
    aggregation_input: dict[str, Any],
) -> str:
    return _digest(
        _projection(
            aggregation_input,
            AGGREGATION_INPUT_SEMANTIC_FIELDS,
            "multi_agent_evidence_aggregation_input",
        )
    )


def multi_agent_orchestration_receipt_id(receipt: dict[str, Any]) -> str:
    """The narrow, natural-key content address of a Multi-Agent Orchestration Receipt -- one
    per plan."""

    return _address(
        "MULTI-AGENT-ORCHESTRATION-",
        _projection(receipt, PLAN_KEYED_FIELDS, "multi_agent_orchestration_receipt"),
    )


def multi_agent_orchestration_receipt_semantic_fingerprint(receipt: dict[str, Any]) -> str:
    return _digest(
        _projection(
            receipt, ORCHESTRATION_RECEIPT_SEMANTIC_FIELDS, "multi_agent_orchestration_receipt"
        )
    )
