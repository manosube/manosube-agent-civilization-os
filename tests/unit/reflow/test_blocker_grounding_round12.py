"""R12-F3 (Phase 7 Final Closure Round): fail-closed admission for a BLOCKED transition's
specific ``blocker_kind``.

``blocker_payload_errors`` (``difference/lifecycle.py``) already proves a BLOCKED event's
``blocker_kind``/``blocker_resolution_condition.condition_code`` pair is *self-consistent* --
before this round, that self-consistency was the only proof route.reflow ever required.
``blocker_kind_grounding_error`` closes the remaining gap: a *specific*, non-
``OTHER_STRUCTURAL`` cause is refused, before any state mutation, unless this cycle's own
Closure Evaluation actually contains the fact that grounds it
(``PAIRING_TABLE_NE_ACTUAL_GROUNDING_PROOF=true``). ``FULL_NINE_KIND_TYPED_GROUNDING_
REQUIRED_IN_PHASE_7=false`` -- this is a bounded, fail-closed admission check over the eight
kinds this Phase can mechanically ground from data Reflow already computes, not a claim to
ground every conceivable real-world cause.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.reflow_helpers import (
    base_closure_request,
    fixture_difference,
    fixture_genesis_lifecycle_event,
    fixture_policy,
)
from tests.state_helpers import SCHEMA_ROOT, genesis_source_snapshot_records, initial_state

from manosube_agent_civilization.difference.lifecycle import (
    BLOCKER_KIND_GROUNDING_PREDICATE,
    BLOCKER_KIND_VALUES,
    blocker_kind_grounding_error,
    blocker_payload_errors,
)
from manosube_agent_civilization.reflow.errors import ReflowValidationError
from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

REFLOW_INSTANT = "2026-08-30T12:00:00Z"

_GROUNDED_BASELINE: dict[str, Any] = {
    "evaluation": {"result": "NOT_SATISFIED", "gate_results": {"G19": "PASS", "G21": "PASS"}},
    "sufficiency": {"result": "SUFFICIENT"},
    "authority_ref": {"kind": "authority_decision", "id": "A-" + "1" * 64},
    "change_refs": [{"kind": "change", "id": "C-" + "1" * 64}],
    "observation_refs": [{"kind": "observation", "id": "O-" + "1" * 64}],
    "reobservation": {"after_observation_refs": [{"kind": "observation", "id": "O-" + "1" * 64}]},
}


# --- OTHER_STRUCTURAL/None are exempt, never a ninth kind this Phase claims to ground ------- #


def test_r12f3_other_structural_is_always_exempt() -> None:
    assert blocker_kind_grounding_error("OTHER_STRUCTURAL", **_GROUNDED_BASELINE) is None
    # Exempt even against the worst possible (fully ungrounded) Evaluation.
    ungrounded = dict(_GROUNDED_BASELINE)
    ungrounded["evaluation"] = {"result": "NOT_SATISFIED", "gate_results": {}}
    ungrounded["sufficiency"] = None
    ungrounded["authority_ref"] = None
    ungrounded["change_refs"] = []
    ungrounded["observation_refs"] = []
    ungrounded["reobservation"] = None
    assert blocker_kind_grounding_error("OTHER_STRUCTURAL", **ungrounded) is None


def test_r12f3_a_null_blocker_kind_is_a_no_op() -> None:
    assert blocker_kind_grounding_error(None, **_GROUNDED_BASELINE) is None


def test_r12f3_this_module_never_claims_full_nine_kind_grounding() -> None:
    """FULL_NINE_KIND_TYPED_GROUNDING_REQUIRED_IN_PHASE_7=false, made explicit: the grounding
    predicate table names exactly the eight kinds this Phase mechanically grounds --
    ``OTHER_STRUCTURAL`` is not a ninth entry silently added to it, it is exempt by design."""

    assert "OTHER_STRUCTURAL" not in BLOCKER_KIND_GROUNDING_PREDICATE
    assert set(BLOCKER_KIND_GROUNDING_PREDICATE) == BLOCKER_KIND_VALUES - {"OTHER_STRUCTURAL"}


def test_r12f3_an_unrecognized_blocker_kind_is_refused_outright() -> None:
    error = blocker_kind_grounding_error("NOT_A_REAL_KIND", **_GROUNDED_BASELINE)
    assert error is not None
    assert "not a recognized value" in error


# --- every one of the eight typed kinds: refused when ungrounded ---------------------------- #


@pytest.mark.parametrize("kind", sorted(BLOCKER_KIND_VALUES - {"OTHER_STRUCTURAL"}))
def test_r12f3_every_specific_kind_is_refused_when_ungrounded(kind: str) -> None:
    """UNVERIFIED_SPECIFIC_BLOCKER_CAUSE_COMMIT_ALLOWED=false: an Evaluation carrying none of
    a kind's own grounding fact refuses it -- a caller's bare assertion is never enough."""

    ungrounded = dict(_GROUNDED_BASELINE)
    ungrounded["evaluation"] = {
        "result": "NOT_SATISFIED",
        "gate_results": {"G19": "PASS", "G21": "PASS"},
    }
    ungrounded["sufficiency"] = {"result": "SUFFICIENT"}
    ungrounded["authority_ref"] = {"kind": "authority_decision", "id": "A-" + "1" * 64}
    ungrounded["change_refs"] = [{"kind": "change", "id": "C-" + "1" * 64}]
    ungrounded["observation_refs"] = [{"kind": "observation", "id": "O-" + "1" * 64}]
    ungrounded["reobservation"] = {
        "after_observation_refs": [{"kind": "observation", "id": "O-" + "1" * 64}]
    }

    error = blocker_kind_grounding_error(kind, **ungrounded)
    assert error is not None
    assert kind in error


# --- every one of the eight typed kinds: admitted when genuinely grounded -------------------- #


@pytest.mark.parametrize(
    "kind,overrides",
    [
        ("EVIDENCE_INSUFFICIENT", {"sufficiency": {"result": "INSUFFICIENT"}}),
        ("STALE_BINDING", {"sufficiency": {"result": "STALE"}}),
        ("MATERIAL_CONFLICT", {"evaluation": {"result": "CONTRADICTED", "gate_results": {}}}),
        (
            "INVARIANT_FAILURE",
            {
                "evaluation": {
                    "result": "NOT_SATISFIED",
                    "gate_results": {"G19": "FAIL", "G21": "PASS"},
                }
            },
        ),
        (
            "CLAIM_FAILURE",
            {
                "evaluation": {
                    "result": "NOT_SATISFIED",
                    "gate_results": {"G19": "PASS", "G21": "FAIL"},
                }
            },
        ),
        ("AUTHORITY_PATH", {"authority_ref": None}),
        ("EXECUTION_PATH", {"change_refs": []}),
        ("OBSERVATION_PATH", {"observation_refs": [], "reobservation": None}),
    ],
)
def test_r12f3_every_specific_kind_is_admitted_when_grounded(
    kind: str, overrides: dict[str, Any]
) -> None:
    grounded = dict(_GROUNDED_BASELINE)
    grounded.update(overrides)
    assert blocker_kind_grounding_error(kind, **grounded) is None


# --- self-consistency is not grounding proof ------------------------------------------------- #


def test_r12f3_a_self_consistent_blocker_kind_condition_code_pairing_is_not_grounding_proof() -> (
    None
):
    """PAIRING_TABLE_NE_ACTUAL_GROUNDING_PROOF=true, proven directly: an event whose
    ``blocker_kind``/``condition_code`` pairing is perfectly self-consistent -- passing
    ``blocker_payload_errors`` outright -- is still refused by ``blocker_kind_grounding_error``
    when nothing in this cycle's own Evaluation actually grounds that specific cause."""

    subject_ref = {"kind": "difference", "id": "D-" + "1" * 64}
    next_observation_ref = {"kind": "next_observation_request", "id": "OBS-REQ-" + "9" * 64}
    event = {
        "difference_event_id": "test-identity",
        "to_status": "BLOCKED",
        "evidence_refs": [{"kind": "observation_evidence", "id": "EV-" + "1" * 64}],
        "blocker_kind": "INVARIANT_FAILURE",
        "blocker_scope": {
            "kind": "difference_blocker_scope",
            "affected_subject_refs": {"collection_kind": "UNORDERED_SET", "members": [subject_ref]},
            "effective_boundary": {"kind": "objective_scope", "id": "SCOPE-1"},
            "blocked_stage": "DIFFERENCE_EVALUATION",
        },
        "blocker_resolution_condition": {
            "kind": "blocker_resolution_condition",
            "condition_code": "INVARIANTS_PASS",
            "subject_ref": subject_ref,
            "expected_state": "PASS",
            "verification_request_ref": next_observation_ref,
        },
        "next_observation_ref": next_observation_ref,
    }

    # The pairing is fully self-consistent -- the existing validator finds nothing wrong.
    assert blocker_payload_errors(event, None) == []

    # But nothing in this cycle's own Evaluation actually failed G19: the caller's
    # blocker_kind is an unverified assertion, and grounding refuses it regardless.
    error = blocker_kind_grounding_error(
        "INVARIANT_FAILURE",
        evaluation={"result": "NOT_SATISFIED", "gate_results": {"G19": "PASS", "G21": "PASS"}},
        sufficiency=None,
        authority_ref={"kind": "authority_decision", "id": "A-" + "1" * 64},
        change_refs=[{"kind": "change", "id": "C-" + "1" * 64}],
        observation_refs=[{"kind": "observation", "id": "O-" + "1" * 64}],
        reobservation=None,
    )
    assert error is not None


# --- end-to-end: zero state mutation on refusal, and a real positive control ---------------- #


def _fresh_store(tmp_path: Path) -> tuple[FileStateStore, dict[str, Any]]:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = initial_state()
    difference = fixture_difference()
    project_state["objective_revision_id"] = difference["objective_revision_ref"]["id"]
    project_state["semantic_fingerprint"] = fingerprint_project_state(
        project_state, schema_root=SCHEMA_ROOT
    ).as_dict()
    store.initialize(
        project_state["project_id"],
        project_state,
        records=genesis_source_snapshot_records(project_state),
    )
    return store, project_state


def test_r12f3_an_ungrounded_specific_cause_is_refused_before_any_state_mutation(
    tmp_path: Path,
) -> None:
    """R12_F3_REFUSAL_HAS_ZERO_STATE_MUTATION=true, proven end-to-end: a real ``reflow()``
    call whose caller asserts ``EVIDENCE_INSUFFICIENT`` with no real
    ``evidence_sufficiency_request`` behind it at all raises before committing anything -- the
    Store's current State is left completely untouched."""

    store, project_state = _fresh_store(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    closure_request = base_closure_request(difference, policy)

    with pytest.raises(ReflowValidationError, match="not mechanically grounded"):
        reflow(
            store,
            project_id=project_state["project_id"],
            previous_event_id=difference["genesis_event_ref"]["id"],
            genesis_lifecycle_event=fixture_genesis_lifecycle_event(difference),
            event_revision=1,
            closure_request=closure_request,
            observation_refs=[],
            reflow_instant=REFLOW_INSTANT,
            blocker_kind="EVIDENCE_INSUFFICIENT",
            blocker_scope={
                "kind": "difference_blocker_scope",
                "affected_subject_refs": {
                    "collection_kind": "UNORDERED_SET",
                    "members": [{"kind": "difference", "id": difference["difference_id"]}],
                },
                "effective_boundary": difference["effective_boundary"],
                "blocked_stage": "DIFFERENCE_EVALUATION",
            },
            blocker_resolution_condition={
                "kind": "blocker_resolution_condition",
                "condition_code": "REQUIRED_EVIDENCE_AVAILABLE",
                "subject_ref": {"kind": "difference", "id": difference["difference_id"]},
                "expected_state": "AVAILABLE",
                "verification_request_ref": {
                    "kind": "next_observation_request",
                    "id": "OBS-REQ-" + "9" * 64,
                },
            },
            next_observation_ref={"kind": "next_observation_request", "id": "OBS-REQ-" + "9" * 64},
        )

    assert store.load_current(project_state["project_id"]) == project_state


def test_r12f3_a_mechanically_grounded_cause_is_admitted_end_to_end(tmp_path: Path) -> None:
    """Positive control: ``AUTHORITY_PATH`` is mechanically grounded whenever this cycle's own
    ``authority_ref`` is genuinely absent -- ``reflow()`` is never given one here -- so the
    transition commits rather than being refused."""

    store, project_state = _fresh_store(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    closure_request = base_closure_request(difference, policy)

    result = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
        genesis_lifecycle_event=fixture_genesis_lifecycle_event(difference),
        event_revision=1,
        closure_request=closure_request,
        observation_refs=[],
        reflow_instant=REFLOW_INSTANT,
        blocker_kind="AUTHORITY_PATH",
        blocker_scope={
            "kind": "difference_blocker_scope",
            "affected_subject_refs": {
                "collection_kind": "UNORDERED_SET",
                "members": [{"kind": "difference", "id": difference["difference_id"]}],
            },
            "effective_boundary": difference["effective_boundary"],
            "blocked_stage": "EXTERNAL_AUTHORITY_PATH",
        },
        blocker_resolution_condition={
            "kind": "blocker_resolution_condition",
            "condition_code": "AUTHORITY_PATH_AVAILABLE",
            "subject_ref": {"kind": "difference", "id": difference["difference_id"]},
            "expected_state": "AVAILABLE",
            "verification_request_ref": {
                "kind": "next_observation_request",
                "id": "OBS-REQ-" + "9" * 64,
            },
        },
        next_observation_ref={"kind": "next_observation_request", "id": "OBS-REQ-" + "9" * 64},
    )
    assert result["decision"]["to_status"] == "BLOCKED"
    assert store.load_current(project_state["project_id"]) == result["committed_state"]
