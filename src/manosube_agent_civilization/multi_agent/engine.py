"""The pure Multi-Agent Dynamic Execution record builder (Phase 19, Issue #77).

```text
REAL, STORE-RESOLVED DIFFERENCE + LIVE PHASE 12 CONTRACT + REUSED MODEL RUNTIME WORK UNIT
→ CANONICAL, CONTENT-ADDRESSED MULTI-AGENT DYNAMIC EXECUTION PLAN
→ PER-SLOT ATTEMPT IDENTITY (computable before any Agent exists)
→ CANONICAL MULTI-AGENT SLOT OUTPUT (one per slot's own attempt)
→ CANONICAL MULTI-AGENT AGENT RELEASE RECEIPT (one per slot)
→ CANONICAL MULTI-AGENT CONFLICT SET (one per plan)
→ CANONICAL MULTI-AGENT EVIDENCE AGGREGATION INPUT (one per plan)
→ CANONICAL MULTI-AGENT ORCHESTRATION RECEIPT (one per plan)
```

This module builds and schema-validates canonical records from already-resolved, already-
verified inputs. It resolves nothing itself, calls no Store, no Boot, no Temporary Agent, no
Authority, no Adapter, and no existing Evidence owner --
:mod:`~manosube_agent_civilization.multi_agent.route` and
:mod:`~manosube_agent_civilization.multi_agent.evidence_handoff` own every one of those calls
and are the only callers of the ``derive_*`` functions below. This is the identical
"derivation is pure, resolution is the route's job" discipline every other Kernel engine in
this repository already keeps (compare
:func:`~manosube_agent_civilization.model_runtime.engine.derive_model_execution_envelope`).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
    validate_subrecord as _validate_canonical_subrecord,
)

from .errors import MultiAgentReleaseIncompleteError, MultiAgentRequirementError
from .identity import (
    AGGREGATION_INPUT_SEMANTIC_FIELDS,
    CONFLICT_SET_SEMANTIC_FIELDS,
    ORCHESTRATION_RECEIPT_SEMANTIC_FIELDS,
    RELEASE_RECEIPT_SEMANTIC_FIELDS,
    SLOT_OUTPUT_SEMANTIC_FIELDS,
    multi_agent_agent_release_receipt_id,
    multi_agent_agent_release_receipt_semantic_fingerprint,
    multi_agent_attempt_id,
    multi_agent_conflict_set_id,
    multi_agent_conflict_set_semantic_fingerprint,
    multi_agent_dynamic_execution_plan_id,
    multi_agent_dynamic_execution_plan_semantic_fingerprint,
    multi_agent_evidence_aggregation_input_id,
    multi_agent_evidence_aggregation_input_semantic_fingerprint,
    multi_agent_orchestration_receipt_id,
    multi_agent_orchestration_receipt_semantic_fingerprint,
    multi_agent_slot_output_id,
    multi_agent_slot_output_semantic_fingerprint,
)
from .types import MULTI_AGENT_SLOT_OUTCOMES, ORCHESTRATION_OUTCOMES, RELEASE_STATUSES

MULTI_AGENT_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "multi_agent/"
SCHEMA_VERSION = "0.1"

PLAN_SCHEMA_NAME = "multi_agent_dynamic_execution_plan.schema.json"
SLOT_OUTPUT_SCHEMA_NAME = "multi_agent_slot_output.schema.json"
RELEASE_RECEIPT_SCHEMA_NAME = "multi_agent_agent_release_receipt.schema.json"
CONFLICT_SET_SCHEMA_NAME = "multi_agent_conflict_set.schema.json"
AGGREGATION_INPUT_SCHEMA_NAME = "multi_agent_evidence_aggregation_input.schema.json"
ORCHESTRATION_RECEIPT_SCHEMA_NAME = "multi_agent_orchestration_receipt.schema.json"


def _require_schema_valid_record(value: Any, schema_name: str, context: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MultiAgentRequirementError(f"{context} must be an explicit mapping: {value!r}")
    body = dict(value)
    try:
        _validate_canonical_record(body, schema_name, base=MULTI_AGENT_SCHEMA_BASE)
    except DifferenceValidationError as error:
        raise MultiAgentRequirementError(f"{context} is not schema-valid: {error}") from error
    return body


def require_valid_timestamp(value: Any, context: str) -> str:
    """Require *value* to be one canonical UTC ``Z``-suffixed timestamp -- proved before any
    Agent is constructed, the identical discipline every other package's own ``engine.py``
    already establishes for itself."""

    try:
        _validate_canonical_subrecord(
            value, PLAN_SCHEMA_NAME, "#/properties/opened_at", base=MULTI_AGENT_SCHEMA_BASE
        )
    except DifferenceValidationError as error:
        raise MultiAgentRequirementError(
            f"{context} is not a canonical UTC timestamp: {value!r}"
        ) from error
    return str(value)


def require_valid_semantic_fingerprint(value: Any, context: str) -> dict[str, Any]:
    """Require *value* to be one canonical State semantic fingerprint object."""

    try:
        _validate_canonical_subrecord(
            value,
            PLAN_SCHEMA_NAME,
            "#/properties/boot_semantic_fingerprint",
            base=MULTI_AGENT_SCHEMA_BASE,
        )
    except DifferenceValidationError as error:
        raise MultiAgentRequirementError(
            f"{context} is not a canonical State semantic fingerprint: {value!r}"
        ) from error
    return dict(value)


def require_valid_adapter_identity(value: Any, context: str) -> dict[str, Any]:
    """Require *value* to be the complete, closed ``adapter_identity`` shape -- exactly
    ``adapter``/``version``, both non-empty strings, no other property."""

    try:
        _validate_canonical_subrecord(
            value, PLAN_SCHEMA_NAME, "#/$defs/adapter_identity", base=MULTI_AGENT_SCHEMA_BASE
        )
    except DifferenceValidationError as error:
        raise MultiAgentRequirementError(
            f"{context} is not the canonical closed adapter_identity shape (exactly 'adapter' "
            f"and 'version', both non-empty strings, no other property): {value!r}"
        ) from error
    return dict(value)


def require_valid_multi_agent_dynamic_execution_plan(plan: Any) -> dict[str, Any]:
    return _require_schema_valid_record(
        plan, PLAN_SCHEMA_NAME, "resolved multi_agent_dynamic_execution_plan"
    )


def require_valid_multi_agent_slot_output(slot_output: Any) -> dict[str, Any]:
    return _require_schema_valid_record(
        slot_output, SLOT_OUTPUT_SCHEMA_NAME, "resolved multi_agent_slot_output"
    )


def require_valid_multi_agent_agent_release_receipt(receipt: Any) -> dict[str, Any]:
    return _require_schema_valid_record(
        receipt, RELEASE_RECEIPT_SCHEMA_NAME, "resolved multi_agent_agent_release_receipt"
    )


def require_valid_multi_agent_conflict_set(conflict_set: Any) -> dict[str, Any]:
    return _require_schema_valid_record(
        conflict_set, CONFLICT_SET_SCHEMA_NAME, "resolved multi_agent_conflict_set"
    )


def require_valid_multi_agent_evidence_aggregation_input(aggregation_input: Any) -> dict[str, Any]:
    return _require_schema_valid_record(
        aggregation_input,
        AGGREGATION_INPUT_SCHEMA_NAME,
        "resolved multi_agent_evidence_aggregation_input",
    )


def require_valid_multi_agent_orchestration_receipt(receipt: Any) -> dict[str, Any]:
    return _require_schema_valid_record(
        receipt, ORCHESTRATION_RECEIPT_SCHEMA_NAME, "resolved multi_agent_orchestration_receipt"
    )


def derive_multi_agent_dynamic_execution_plan(
    *,
    project_id: str,
    project_binding_ref: dict[str, Any],
    boot_state_revision: int,
    boot_semantic_fingerprint: dict[str, Any],
    difference_ref: dict[str, Any],
    capability_selection_fingerprint: str,
    slots: tuple[dict[str, Any], ...],
    model_work_unit_ref: dict[str, Any],
    authority_ref: dict[str, Any],
    adapter_identity: dict[str, Any],
    execution_order: str,
    execution_bounds: dict[str, Any],
    conflict_policy: str,
    release_policy: str,
    opened_at: str,
    expires_at: str,
) -> dict[str, Any]:
    """Return one canonical, schema-valid, content-addressed Multi-Agent Dynamic Execution
    Plan record (P19-C2).

    Every argument must already be real: the Difference must already have been Store-resolved,
    schema-validated and identity-recomputed by the caller; *slots* must already be
    :func:`~manosube_agent_civilization.multi_agent.selection.select_agent_slots`'s own bounded,
    deterministic output; *model_work_unit_ref* and *authority_ref* must already name a real,
    committed Model Work Unit and the Authority Decision it itself reproduced (reused from the
    existing Model Runtime owner, never re-evaluated here). This function performs no Store I/O
    of any kind, reaches no Adapter, and evaluates no Authority.
    """

    plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "project_binding_ref": dict(project_binding_ref),
        "boot_state_revision": boot_state_revision,
        "boot_semantic_fingerprint": dict(boot_semantic_fingerprint),
        "difference_ref": dict(difference_ref),
        "capability_selection_fingerprint": capability_selection_fingerprint,
        "slots": [dict(slot) for slot in slots],
        "model_work_unit_ref": dict(model_work_unit_ref),
        "authority_ref": dict(authority_ref),
        "adapter_identity": dict(adapter_identity),
        "execution_order": execution_order,
        "execution_bounds": dict(execution_bounds),
        "conflict_policy": conflict_policy,
        "release_policy": release_policy,
        "opened_at": opened_at,
        "expires_at": expires_at,
    }
    plan["multi_agent_dynamic_execution_plan_id"] = multi_agent_dynamic_execution_plan_id(plan)
    plan["multi_agent_dynamic_execution_plan_semantic_fingerprint"] = (
        multi_agent_dynamic_execution_plan_semantic_fingerprint(plan)
    )
    _validate_canonical_record(plan, PLAN_SCHEMA_NAME, base=MULTI_AGENT_SCHEMA_BASE)
    return plan


def compute_attempt_id(
    *, project_id: str, plan_ref: dict[str, Any], slot_index: int, attempt_ordinal: int = 1
) -> str:
    """The one attempt identity a slot's own single attempt in this delivery ever carries --
    see :func:`~manosube_agent_civilization.multi_agent.identity.multi_agent_attempt_id`'s own
    docstring. Exposed here, at the engine layer, so the route can resolve it *before*
    constructing an Agent or reaching an adapter (P19-C9's own replay requirement)."""

    return multi_agent_attempt_id(
        plan_ref=plan_ref,
        slot_index=slot_index,
        attempt_ordinal=attempt_ordinal,
        project_id=project_id,
        schema_version=SCHEMA_VERSION,
    )


def compute_slot_output_id(
    *, project_id: str, plan_ref: dict[str, Any], slot_index: int, attempt_ordinal: int = 1
) -> str:
    """The narrow, natural-key Store primary key one slot's own attempt record will occupy --
    computable from the identical five inputs :func:`compute_attempt_id` itself hashes, under
    this record kind's own ``MULTI-AGENT-SLOT-OUTPUT-`` prefix rather than ``attempt_id``'s own
    ``MULTI-AGENT-ATTEMPT-`` one.

    This is the one function P19-C9's own replay-before-execution check actually resolves by:
    a plain Store lookup at this exact key, before any Agent is constructed or any adapter is
    reached, is how a replayed call finds an already-recorded attempt without ever re-running
    it. Deliberately a *different* string from :func:`compute_attempt_id`'s own return value
    (same digest, different prefix -- see :mod:`~manosube_agent_civilization.multi_agent.
    identity`'s own module docstring): ``attempt_id`` is the record's own stated field and the
    identity every release receipt and conflict-set member refers to it by; this is the raw
    Store key its own record is filed under.
    """

    return multi_agent_slot_output_id(
        {
            "schema_version": SCHEMA_VERSION,
            "project_id": project_id,
            "plan_ref": dict(plan_ref),
            "slot_index": slot_index,
            "attempt_ordinal": attempt_ordinal,
        }
    )


def derive_multi_agent_slot_output(
    *,
    project_id: str,
    plan_ref: dict[str, Any],
    slot_index: int,
    capability: str,
    attempt_ordinal: int,
    model_execution_envelope_ref: dict[str, Any] | None,
    outcome: str,
    result_fingerprint: str | None,
    outcome_detail: str | None,
    started_at: str,
    ended_at: str,
    execution_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Return one canonical, schema-valid Multi-Agent Slot Output record for one slot's own
    attempt (P19-C5).

    *outcome* must already be one of :data:`~manosube_agent_civilization.multi_agent.types.
    MULTI_AGENT_SLOT_OUTCOMES` -- the caller's own already-resolved, real Model Execution
    Envelope outcome, or an honest ``UNAVAILABLE`` classification of a caught operational
    error the route itself never lets escape as a lost slot (see ``route.py``'s own per-slot
    ``try/except`` disclosure).

    *execution_snapshot* (Structural Review Round 1, P19-R1-F1) must already be the caller's
    plan's own ``{"state_revision": plan["boot_state_revision"], "semantic_fingerprint":
    plan["boot_semantic_fingerprint"]}`` -- the one immutable snapshot every slot of one plan
    shares by construction, since every slot's own call reads it from the identical, already-
    committed, genesis-once ``plan`` record rather than from any live re-observation at this
    slot's own adapter-call time. This is deliberately *not* the live State revision Model
    Runtime's own unchanged ``execute_model_work_unit`` itself reads when actually reaching the
    adapter (which legitimately advances slot to slot -- each slot's own Model Execution
    Envelope commit is what advances it, an accepted, disclosed Model Runtime behaviour this
    package neither can nor should alter): this field is this package's own bound, order-
    invariant fact about *which execution this slot's attempt belongs to*, never a claim about
    what Model Runtime's own request happened to observe live.
    """

    if outcome not in MULTI_AGENT_SLOT_OUTCOMES:
        raise MultiAgentRequirementError(f"outcome is not a recognized outcome: {outcome!r}")
    if not isinstance(execution_snapshot, Mapping) or set(execution_snapshot) != {
        "state_revision",
        "semantic_fingerprint",
    }:
        raise MultiAgentRequirementError(
            f"execution_snapshot must be exactly {{'state_revision', 'semantic_fingerprint'}}: "
            f"{execution_snapshot!r}"
        )

    attempt_id = compute_attempt_id(
        project_id=project_id,
        plan_ref=plan_ref,
        slot_index=slot_index,
        attempt_ordinal=attempt_ordinal,
    )
    slot_output: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "plan_ref": dict(plan_ref),
        "slot_index": slot_index,
        "capability": capability,
        "attempt_id": attempt_id,
        "attempt_ordinal": attempt_ordinal,
        "model_execution_envelope_ref": (
            None if model_execution_envelope_ref is None else dict(model_execution_envelope_ref)
        ),
        "outcome": outcome,
        "result_fingerprint": result_fingerprint,
        "outcome_detail": outcome_detail,
        "started_at": started_at,
        "ended_at": ended_at,
        "execution_snapshot": {
            "state_revision": int(execution_snapshot["state_revision"]),
            "semantic_fingerprint": dict(execution_snapshot["semantic_fingerprint"]),
        },
    }
    slot_output["multi_agent_slot_output_id"] = multi_agent_slot_output_id(slot_output)
    slot_output["multi_agent_slot_output_semantic_fingerprint"] = (
        multi_agent_slot_output_semantic_fingerprint(slot_output)
    )
    _validate_canonical_record(slot_output, SLOT_OUTPUT_SCHEMA_NAME, base=MULTI_AGENT_SCHEMA_BASE)
    return slot_output


def derive_multi_agent_agent_release_receipt(
    *,
    project_id: str,
    plan_ref: dict[str, Any],
    slot_index: int,
    attempt_id: str | None,
    release_status: str,
    released_at: str,
) -> dict[str, Any]:
    """Return one canonical, schema-valid Multi-Agent Agent Release Receipt (P19-C8)."""

    if release_status not in RELEASE_STATUSES:
        raise MultiAgentRequirementError(
            f"release_status is not a recognized status: {release_status!r}"
        )
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "plan_ref": dict(plan_ref),
        "slot_index": slot_index,
        "attempt_id": attempt_id,
        "release_status": release_status,
        "released_at": released_at,
    }
    receipt["multi_agent_agent_release_receipt_id"] = multi_agent_agent_release_receipt_id(receipt)
    receipt["multi_agent_agent_release_receipt_semantic_fingerprint"] = (
        multi_agent_agent_release_receipt_semantic_fingerprint(receipt)
    )
    _validate_canonical_record(receipt, RELEASE_RECEIPT_SCHEMA_NAME, base=MULTI_AGENT_SCHEMA_BASE)
    return receipt


def derive_multi_agent_conflict_set(
    *,
    project_id: str,
    plan_ref: dict[str, Any],
    considered_slot_output_refs: list[dict[str, Any]],
    members: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return one canonical, schema-valid Multi-Agent Conflict Set (P19-C6).

    *members* must already have been classified by the caller under this delivery's one
    conflict/aggregation policy (exact ``result_fingerprint`` equality within a
    ``(plan, capability)`` group is "agreeing"; two or more distinct non-null fingerprints is
    "contradicting", with full membership preserved; any slot whose own attempt did not reach
    ``CANDIDATE_ACCEPTED`` is an ``ABSENT`` member, never silently dropped) -- this function
    performs no classification of its own, it only assembles and schema-validates the record.
    """

    conflict_set: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "plan_ref": dict(plan_ref),
        "considered_slot_output_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [dict(ref) for ref in considered_slot_output_refs],
        },
        "members": [dict(member) for member in members],
    }
    conflict_set["multi_agent_conflict_set_id"] = multi_agent_conflict_set_id(conflict_set)
    conflict_set["multi_agent_conflict_set_semantic_fingerprint"] = (
        multi_agent_conflict_set_semantic_fingerprint(conflict_set)
    )
    _validate_canonical_record(conflict_set, CONFLICT_SET_SCHEMA_NAME, base=MULTI_AGENT_SCHEMA_BASE)
    return conflict_set


def derive_multi_agent_evidence_aggregation_input(
    *,
    project_id: str,
    plan_ref: dict[str, Any],
    conflict_set_ref: dict[str, Any],
    admitted_slot_output_refs: list[dict[str, Any]],
    unresolved_capabilities: list[str],
    absent_slot_output_refs: list[dict[str, Any]],
    release_receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return one canonical, schema-valid Multi-Agent Evidence Aggregation Input (P19-C7).

    Refuses -- with nothing constructed -- unless *release_receipts* is non-empty and every one
    of them declares ``release_status == "RELEASED"`` (P19-C8's own "blocks the orchestration
    attempt from claiming clean terminal completion" requirement, enforced at the one place an
    aggregation input can ever come into existence).
    """

    if not release_receipts:
        raise MultiAgentRequirementError(
            "no release receipts were supplied -- an Evidence aggregation input can never be "
            "constructed for a plan with no accounted-for Agent release"
        )
    unreleased = [
        receipt for receipt in release_receipts if receipt.get("release_status") != "RELEASED"
    ]
    if unreleased:
        raise MultiAgentReleaseIncompleteError(
            "one or more constructed temporary Agents for this plan do not carry a "
            f"release_status of RELEASED: {sorted(str(r.get('slot_index')) for r in unreleased)} -- "
            "refusing to construct an Evidence aggregation input while any release remains "
            "unaccounted for"
        )

    aggregation_input: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "plan_ref": dict(plan_ref),
        "conflict_set_ref": dict(conflict_set_ref),
        "admitted_slot_output_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [dict(ref) for ref in admitted_slot_output_refs],
        },
        "unresolved_capabilities": sorted(set(unresolved_capabilities)),
        "absent_slot_output_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [dict(ref) for ref in absent_slot_output_refs],
        },
        "release_receipt_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [
                {
                    "kind": "multi_agent_agent_release_receipt",
                    "id": receipt["multi_agent_agent_release_receipt_id"],
                }
                for receipt in release_receipts
            ],
        },
    }
    aggregation_input["multi_agent_evidence_aggregation_input_id"] = (
        multi_agent_evidence_aggregation_input_id(aggregation_input)
    )
    aggregation_input["multi_agent_evidence_aggregation_input_semantic_fingerprint"] = (
        multi_agent_evidence_aggregation_input_semantic_fingerprint(aggregation_input)
    )
    _validate_canonical_record(
        aggregation_input, AGGREGATION_INPUT_SCHEMA_NAME, base=MULTI_AGENT_SCHEMA_BASE
    )
    return aggregation_input


def derive_multi_agent_orchestration_receipt(
    *,
    project_id: str,
    plan_ref: dict[str, Any],
    slot_output_refs: list[dict[str, Any]],
    release_receipt_refs: list[dict[str, Any]],
    conflict_set_ref: dict[str, Any],
    aggregation_input_ref: dict[str, Any],
    evidence_refs: list[dict[str, Any]],
    orchestration_outcome: str,
    completed_at: str,
) -> dict[str, Any]:
    """Return one canonical, schema-valid Multi-Agent Orchestration Receipt -- the terminal
    fact P19-C8/P19-C9 describe."""

    if orchestration_outcome not in ORCHESTRATION_OUTCOMES:
        raise MultiAgentRequirementError(
            f"orchestration_outcome is not a recognized outcome: {orchestration_outcome!r}"
        )
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "plan_ref": dict(plan_ref),
        "slot_output_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [dict(ref) for ref in slot_output_refs],
        },
        "release_receipt_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [dict(ref) for ref in release_receipt_refs],
        },
        "conflict_set_ref": dict(conflict_set_ref),
        "aggregation_input_ref": dict(aggregation_input_ref),
        "evidence_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [dict(ref) for ref in evidence_refs],
        },
        "orchestration_outcome": orchestration_outcome,
        "completed_at": completed_at,
    }
    receipt["multi_agent_orchestration_receipt_id"] = multi_agent_orchestration_receipt_id(receipt)
    receipt["multi_agent_orchestration_receipt_semantic_fingerprint"] = (
        multi_agent_orchestration_receipt_semantic_fingerprint(receipt)
    )
    _validate_canonical_record(
        receipt, ORCHESTRATION_RECEIPT_SCHEMA_NAME, base=MULTI_AGENT_SCHEMA_BASE
    )
    return receipt


__all__ = [
    "AGGREGATION_INPUT_SCHEMA_NAME",
    "AGGREGATION_INPUT_SEMANTIC_FIELDS",
    "CONFLICT_SET_SCHEMA_NAME",
    "CONFLICT_SET_SEMANTIC_FIELDS",
    "MULTI_AGENT_SCHEMA_BASE",
    "ORCHESTRATION_RECEIPT_SCHEMA_NAME",
    "ORCHESTRATION_RECEIPT_SEMANTIC_FIELDS",
    "PLAN_SCHEMA_NAME",
    "RELEASE_RECEIPT_SCHEMA_NAME",
    "RELEASE_RECEIPT_SEMANTIC_FIELDS",
    "SCHEMA_VERSION",
    "SLOT_OUTPUT_SCHEMA_NAME",
    "SLOT_OUTPUT_SEMANTIC_FIELDS",
    "compute_attempt_id",
    "compute_slot_output_id",
    "derive_multi_agent_agent_release_receipt",
    "derive_multi_agent_conflict_set",
    "derive_multi_agent_dynamic_execution_plan",
    "derive_multi_agent_evidence_aggregation_input",
    "derive_multi_agent_orchestration_receipt",
    "derive_multi_agent_slot_output",
    "require_valid_adapter_identity",
    "require_valid_multi_agent_agent_release_receipt",
    "require_valid_multi_agent_conflict_set",
    "require_valid_multi_agent_dynamic_execution_plan",
    "require_valid_multi_agent_evidence_aggregation_input",
    "require_valid_multi_agent_orchestration_receipt",
    "require_valid_multi_agent_slot_output",
    "require_valid_semantic_fingerprint",
    "require_valid_timestamp",
]
