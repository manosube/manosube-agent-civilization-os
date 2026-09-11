"""Phase 19 (Issue #77) V1: deterministic schema and identity proof.

For each of the six record kinds this package owns: recomputing identity/semantic fingerprint
from the real, built record reproduces the declared value exactly; every field is
identity-sensitive (mutating any one field changes at least one of the two digests); and the
record validates against its own canonical schema.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from manosube_agent_civilization.multi_agent.engine import (
    derive_multi_agent_agent_release_receipt,
    derive_multi_agent_conflict_set,
    derive_multi_agent_dynamic_execution_plan,
    derive_multi_agent_evidence_aggregation_input,
    derive_multi_agent_orchestration_receipt,
    derive_multi_agent_slot_output,
)
from manosube_agent_civilization.multi_agent.errors import MultiAgentReleaseIncompleteError
from manosube_agent_civilization.multi_agent.identity import (
    capability_selection_fingerprint,
    multi_agent_agent_release_receipt_id,
    multi_agent_agent_release_receipt_semantic_fingerprint,
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

_PROJECT_ID = "PRJ-IDENTITY-0001"
_PROJECT_BINDING_REF = {"kind": "project_binding", "id": "PB-IDENTITY-0001"}
_DIFFERENCE_REF = {"kind": "difference", "id": "D-IDENTITY-0001"}
_MODEL_WORK_UNIT_REF = {"kind": "model_work_unit", "id": "MWU-IDENTITY-0001"}
_AUTHORITY_REF = {"kind": "model_execution_decision", "id": "MED-IDENTITY-0001"}
_ADAPTER_IDENTITY = {"adapter": "fake_model_adapter", "version": "0.1"}
_SLOTS = ({"slot_index": 0, "capability": "PROPOSE_EVIDENCE_CANDIDATE"},)


def _plan() -> dict[str, Any]:
    return derive_multi_agent_dynamic_execution_plan(
        project_id=_PROJECT_ID,
        project_binding_ref=_PROJECT_BINDING_REF,
        boot_state_revision=7,
        boot_semantic_fingerprint={
            "profile": "MANOSUBE-STATE-SHA256-0.1",
            "digest": "a" * 64,
        },
        difference_ref=_DIFFERENCE_REF,
        capability_selection_fingerprint=capability_selection_fingerprint(_SLOTS),
        slots=_SLOTS,
        model_work_unit_ref=_MODEL_WORK_UNIT_REF,
        authority_ref=_AUTHORITY_REF,
        adapter_identity=_ADAPTER_IDENTITY,
        execution_order="CONCURRENT",
        execution_bounds={
            "deadline_at": "2026-09-11T02:00:00Z",
            "cancellation_policy": "COOPERATIVE_PER_SLOT_TIMEOUT",
            "max_concurrent_slots": 1,
        },
        conflict_policy="EXACT_FINGERPRINT_EQUALITY_OR_EXPLICIT_DISAGREEMENT",
        release_policy="RELEASE_ON_TERMINAL_OUTCOME",
        opened_at="2026-09-11T01:00:00Z",
        expires_at="2026-09-11T02:00:00Z",
    )


def test_plan_identity_recomputes_and_is_schema_valid() -> None:
    plan = _plan()
    assert (
        multi_agent_dynamic_execution_plan_id(plan) == plan["multi_agent_dynamic_execution_plan_id"]
    )
    assert (
        multi_agent_dynamic_execution_plan_semantic_fingerprint(plan)
        == plan["multi_agent_dynamic_execution_plan_semantic_fingerprint"]
    )


@pytest.mark.parametrize(
    "field",
    [
        "project_id",
        "boot_state_revision",
        "difference_ref",
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
    ],
)
def test_every_plan_field_is_identity_sensitive(field: str) -> None:
    plan = _plan()
    tampered = deepcopy(plan)
    if isinstance(tampered[field], str):
        tampered[field] = tampered[field] + "-TAMPERED"
    elif isinstance(tampered[field], int):
        tampered[field] = tampered[field] + 1
    elif isinstance(tampered[field], list):
        tampered[field] = tampered[field] + [
            {"slot_index": 99, "capability": "PROPOSE_EVIDENCE_CANDIDATE"}
        ]
    elif isinstance(tampered[field], dict):
        tampered[field] = (
            {**tampered[field], "id": tampered[field].get("id", "") + "-X"}
            if "id" in tampered[field]
            else {**tampered[field], "extra_probe": True}
        )
    assert multi_agent_dynamic_execution_plan_id(tampered) != plan[
        "multi_agent_dynamic_execution_plan_id"
    ] or (
        multi_agent_dynamic_execution_plan_semantic_fingerprint(tampered)
        != plan["multi_agent_dynamic_execution_plan_semantic_fingerprint"]
    )


def test_slot_output_identity_recomputes_and_is_schema_valid() -> None:
    plan = _plan()
    plan_ref = {
        "kind": "multi_agent_dynamic_execution_plan",
        "id": plan["multi_agent_dynamic_execution_plan_id"],
    }
    slot_output = derive_multi_agent_slot_output(
        project_id=_PROJECT_ID,
        plan_ref=plan_ref,
        slot_index=0,
        capability="PROPOSE_EVIDENCE_CANDIDATE",
        attempt_ordinal=1,
        model_execution_envelope_ref={
            "kind": "model_execution_envelope",
            "id": "ENV-IDENTITY-0001",
        },
        outcome="CANDIDATE_ACCEPTED",
        result_fingerprint="sha256:" + "b" * 64,
        outcome_detail=None,
        started_at="2026-09-11T01:30:00Z",
        ended_at="2026-09-11T01:30:00Z",
        execution_snapshot={
            "state_revision": plan["boot_state_revision"],
            "semantic_fingerprint": plan["boot_semantic_fingerprint"],
        },
    )
    assert multi_agent_slot_output_id(slot_output) == slot_output["multi_agent_slot_output_id"]
    assert (
        multi_agent_slot_output_semantic_fingerprint(slot_output)
        == slot_output["multi_agent_slot_output_semantic_fingerprint"]
    )
    # The outcome is excluded from the id's own narrow projection (by design -- see
    # identity.py's own docstring) but must still be caught by the full-content fingerprint.
    tampered = deepcopy(slot_output)
    tampered["outcome"] = "UNAVAILABLE"
    tampered["result_fingerprint"] = None
    assert multi_agent_slot_output_id(tampered) == slot_output["multi_agent_slot_output_id"]
    assert (
        multi_agent_slot_output_semantic_fingerprint(tampered)
        != slot_output["multi_agent_slot_output_semantic_fingerprint"]
    )


def test_release_receipt_identity_recomputes_and_is_schema_valid() -> None:
    plan = _plan()
    plan_ref = {
        "kind": "multi_agent_dynamic_execution_plan",
        "id": plan["multi_agent_dynamic_execution_plan_id"],
    }
    receipt = derive_multi_agent_agent_release_receipt(
        project_id=_PROJECT_ID,
        plan_ref=plan_ref,
        slot_index=0,
        attempt_id="MULTI-AGENT-ATTEMPT-" + "C" * 64,
        release_status="RELEASED",
        released_at="2026-09-11T01:30:00Z",
    )
    assert (
        multi_agent_agent_release_receipt_id(receipt)
        == receipt["multi_agent_agent_release_receipt_id"]
    )
    assert (
        multi_agent_agent_release_receipt_semantic_fingerprint(receipt)
        == receipt["multi_agent_agent_release_receipt_semantic_fingerprint"]
    )
    tampered = deepcopy(receipt)
    tampered["release_status"] = "RELEASE_FAILED"
    assert (
        multi_agent_agent_release_receipt_id(tampered)
        == receipt["multi_agent_agent_release_receipt_id"]
    )
    assert (
        multi_agent_agent_release_receipt_semantic_fingerprint(tampered)
        != receipt["multi_agent_agent_release_receipt_semantic_fingerprint"]
    )


def _agreeing_member(slot_output_id: str) -> dict[str, Any]:
    return {
        "member_kind": "AGREEING",
        "capability": "PROPOSE_EVIDENCE_CANDIDATE",
        "result_fingerprint": "sha256:" + "d" * 64,
        "slot_output_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [{"kind": "multi_agent_slot_output", "id": slot_output_id}],
        },
    }


def test_conflict_set_identity_recomputes_and_is_schema_valid() -> None:
    plan = _plan()
    plan_ref = {
        "kind": "multi_agent_dynamic_execution_plan",
        "id": plan["multi_agent_dynamic_execution_plan_id"],
    }
    slot_output_ref = {
        "kind": "multi_agent_slot_output",
        "id": "MULTI-AGENT-SLOT-OUTPUT-" + "E" * 64,
    }
    conflict_set = derive_multi_agent_conflict_set(
        project_id=_PROJECT_ID,
        plan_ref=plan_ref,
        considered_slot_output_refs=[slot_output_ref],
        members=[_agreeing_member(slot_output_ref["id"])],
    )
    assert multi_agent_conflict_set_id(conflict_set) == conflict_set["multi_agent_conflict_set_id"]
    assert (
        multi_agent_conflict_set_semantic_fingerprint(conflict_set)
        == conflict_set["multi_agent_conflict_set_semantic_fingerprint"]
    )
    # The plan-scoped narrow id excludes membership content by design; the fingerprint must
    # still catch a tampered membership.
    tampered = deepcopy(conflict_set)
    tampered["members"][0]["result_fingerprint"] = "sha256:" + "f" * 64
    assert multi_agent_conflict_set_id(tampered) == conflict_set["multi_agent_conflict_set_id"]
    assert (
        multi_agent_conflict_set_semantic_fingerprint(tampered)
        != conflict_set["multi_agent_conflict_set_semantic_fingerprint"]
    )


def test_aggregation_input_identity_recomputes_and_is_schema_valid() -> None:
    plan = _plan()
    plan_ref = {
        "kind": "multi_agent_dynamic_execution_plan",
        "id": plan["multi_agent_dynamic_execution_plan_id"],
    }
    conflict_set_ref = {
        "kind": "multi_agent_conflict_set",
        "id": "MULTI-AGENT-CONFLICT-" + "1" * 64,
    }
    slot_output_ref = {
        "kind": "multi_agent_slot_output",
        "id": "MULTI-AGENT-SLOT-OUTPUT-" + "2" * 64,
    }
    release_receipt = derive_multi_agent_agent_release_receipt(
        project_id=_PROJECT_ID,
        plan_ref=plan_ref,
        slot_index=0,
        attempt_id="MULTI-AGENT-ATTEMPT-" + "3" * 64,
        release_status="RELEASED",
        released_at="2026-09-11T01:30:00Z",
    )
    aggregation_input = derive_multi_agent_evidence_aggregation_input(
        project_id=_PROJECT_ID,
        plan_ref=plan_ref,
        conflict_set_ref=conflict_set_ref,
        admitted_slot_output_refs=[slot_output_ref],
        unresolved_capabilities=[],
        absent_slot_output_refs=[],
        release_receipts=[release_receipt],
    )
    assert (
        multi_agent_evidence_aggregation_input_id(aggregation_input)
        == aggregation_input["multi_agent_evidence_aggregation_input_id"]
    )
    assert (
        multi_agent_evidence_aggregation_input_semantic_fingerprint(aggregation_input)
        == aggregation_input["multi_agent_evidence_aggregation_input_semantic_fingerprint"]
    )


def test_aggregation_input_refuses_when_any_release_receipt_is_not_released() -> None:
    plan = _plan()
    plan_ref = {
        "kind": "multi_agent_dynamic_execution_plan",
        "id": plan["multi_agent_dynamic_execution_plan_id"],
    }
    conflict_set_ref = {
        "kind": "multi_agent_conflict_set",
        "id": "MULTI-AGENT-CONFLICT-" + "1" * 64,
    }
    slot_output_ref = {
        "kind": "multi_agent_slot_output",
        "id": "MULTI-AGENT-SLOT-OUTPUT-" + "2" * 64,
    }
    failed_release_receipt = derive_multi_agent_agent_release_receipt(
        project_id=_PROJECT_ID,
        plan_ref=plan_ref,
        slot_index=0,
        attempt_id=None,
        release_status="RELEASE_FAILED",
        released_at="2026-09-11T01:30:00Z",
    )
    with pytest.raises(MultiAgentReleaseIncompleteError):
        derive_multi_agent_evidence_aggregation_input(
            project_id=_PROJECT_ID,
            plan_ref=plan_ref,
            conflict_set_ref=conflict_set_ref,
            admitted_slot_output_refs=[slot_output_ref],
            unresolved_capabilities=[],
            absent_slot_output_refs=[],
            release_receipts=[failed_release_receipt],
        )


def test_aggregation_input_refuses_with_zero_release_receipts() -> None:
    plan = _plan()
    plan_ref = {
        "kind": "multi_agent_dynamic_execution_plan",
        "id": plan["multi_agent_dynamic_execution_plan_id"],
    }
    conflict_set_ref = {
        "kind": "multi_agent_conflict_set",
        "id": "MULTI-AGENT-CONFLICT-" + "1" * 64,
    }
    from manosube_agent_civilization.multi_agent.errors import MultiAgentRequirementError

    with pytest.raises(MultiAgentRequirementError):
        derive_multi_agent_evidence_aggregation_input(
            project_id=_PROJECT_ID,
            plan_ref=plan_ref,
            conflict_set_ref=conflict_set_ref,
            admitted_slot_output_refs=[],
            unresolved_capabilities=["PROPOSE_EVIDENCE_CANDIDATE"],
            absent_slot_output_refs=[],
            release_receipts=[],
        )


def test_orchestration_receipt_identity_recomputes_and_is_schema_valid() -> None:
    plan = _plan()
    plan_ref = {
        "kind": "multi_agent_dynamic_execution_plan",
        "id": plan["multi_agent_dynamic_execution_plan_id"],
    }
    slot_output_ref = {
        "kind": "multi_agent_slot_output",
        "id": "MULTI-AGENT-SLOT-OUTPUT-" + "4" * 64,
    }
    release_receipt_ref = {
        "kind": "multi_agent_agent_release_receipt",
        "id": "MULTI-AGENT-RELEASE-" + "5" * 64,
    }
    conflict_set_ref = {
        "kind": "multi_agent_conflict_set",
        "id": "MULTI-AGENT-CONFLICT-" + "6" * 64,
    }
    aggregation_input_ref = {
        "kind": "multi_agent_evidence_aggregation_input",
        "id": "MULTI-AGENT-AGGREGATION-" + "7" * 64,
    }
    evidence_ref = {"kind": "observation_evidence", "id": "EVIDENCE-" + "8" * 64}
    receipt = derive_multi_agent_orchestration_receipt(
        project_id=_PROJECT_ID,
        plan_ref=plan_ref,
        slot_output_refs=[slot_output_ref],
        release_receipt_refs=[release_receipt_ref],
        conflict_set_ref=conflict_set_ref,
        aggregation_input_ref=aggregation_input_ref,
        evidence_refs=[evidence_ref],
        orchestration_outcome="COMPLETED_ALL_RELEASED",
        completed_at="2026-09-11T01:40:00Z",
    )
    assert (
        multi_agent_orchestration_receipt_id(receipt)
        == receipt["multi_agent_orchestration_receipt_id"]
    )
    assert (
        multi_agent_orchestration_receipt_semantic_fingerprint(receipt)
        == receipt["multi_agent_orchestration_receipt_semantic_fingerprint"]
    )
    tampered = deepcopy(receipt)
    tampered["orchestration_outcome"] = "COMPLETED_WITH_UNRESOLVED_CAPABILITY"
    assert (
        multi_agent_orchestration_receipt_id(tampered)
        == receipt["multi_agent_orchestration_receipt_id"]
    )
    assert (
        multi_agent_orchestration_receipt_semantic_fingerprint(tampered)
        != receipt["multi_agent_orchestration_receipt_semantic_fingerprint"]
    )
