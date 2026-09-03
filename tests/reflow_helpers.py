"""Shared fixtures for Reflow's Closure Evaluation producer tests.

Every Difference, Closure Policy and Evidence Sufficiency request here is exactly the
Phase 4/6 fixture family in ``tests/difference_helpers.py`` and ``tests/evidence_helpers.py``
-- nothing is hand-built that those public predecessor routes already produce.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    objective_revision,
    observation_scope,
    semantic_state,
    state_fingerprint,
)
from tests.evidence_helpers import (
    AFTER_REVISION,
    after_observation_request,
    closure_policy,
    evidenced_difference,
    sufficiency_request,
)

from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.reflow.closure import MANDATORY_X003_CLAIM_REF
from manosube_agent_civilization.reflow.identity import material_contradiction_id

GIT_TREE_REF: dict[str, Any] = {
    "kind": "git_tree",
    "repository": "manosube/manosube-agent-civilization-os",
    "commit_sha": "a" * 40,
    "tree_sha": "b" * 40,
}

EVALUATED_AT = "2026-08-30T11:05:00Z"


def fixture_difference() -> dict[str, Any]:
    """The canonical NOT-READY Difference every closure test evaluates against."""

    return evidenced_difference()


def fixture_policy(difference: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return closure_policy(difference["difference_id"], **kwargs)


def satisfied_reobservation(
    difference: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return ``(derivation_request, after_observation_ref, later_state_fingerprint)``.

    The re-observation is a real, independent Observation run through the public
    Observation Engine (``after_observation_request`` -> ``observe``), re-derived through
    the real ``derive_differences`` producer -- never a hand-written "satisfied" record.
    """

    after_bundle = observe(after_observation_request())
    observation_ref = {
        "kind": "observation",
        "id": after_bundle["observations"][0]["observation_id"],
    }
    later_fingerprint = state_fingerprint("KNOWN")
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": observation_scope(),
                "observation_bundle": after_bundle,
            }
        ],
        later_fingerprint,
        AFTER_REVISION,
    )
    return request, observation_ref, later_fingerprint


def mandatory_x003_claim_binding(
    difference: dict[str, Any],
    current_state: dict[str, Any],
    *,
    evaluation_status: str = "SATISFIED",
    claim_ref: dict[str, str] | None = None,
) -> dict[str, Any]:
    """One conformant ``candidate_claim_evaluation_binding`` for the mandatory X-003 claim."""

    return {
        "kind": "candidate_claim_evaluation_binding",
        "binding_id": "CAND-CLAIM-EVAL-" + "0" * 64,
        "difference_id": difference["difference_id"],
        "policy_ref": deepcopy(difference["closure_policy"]),
        "candidate_id": "STATE-CANDIDATE-" + "1" * 64,
        "candidate_semantic_fingerprint": {
            "profile": "MANOSUBE-STATE-SHA256-0.1",
            "digest": "1" * 64,
        },
        "base_state_ref": {
            "kind": "state",
            "revision": current_state["revision"],
            "fingerprint": current_state["fingerprint"],
        },
        "required_claim_ref": claim_ref if claim_ref is not None else MANDATORY_X003_CLAIM_REF,
        "evaluation_series_id": "CAND-CLAIM-SERIES-" + "2" * 64,
        "evaluation_head_event_ref": {
            "kind": "candidate_claim_evaluation_event",
            "id": "CAND-CLAIM-EVT-" + "3" * 64,
        },
        "completion_record_ref": {"kind": "completion_record", "id": "CMP-" + "4" * 64},
        "evaluation_record_fingerprint": "sha256:" + "5" * 64,
        "evaluation_status": evaluation_status,
        "evaluation_evidence_refs": {"collection_kind": "UNORDERED_SET", "members": []},
        "evaluated_at": EVALUATED_AT,
    }


def base_closure_request(
    difference: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    """A candidate-free (``TERMINAL_POLICY_ONLY``-shaped) request every test starts from."""

    return {
        "difference": difference,
        "current_status": "VERIFYING",
        "policy": policy,
        "difference_event_head_ref": deepcopy(difference["genesis_event_ref"]),
        "current_state": {
            "revision": AFTER_REVISION,
            "fingerprint": state_fingerprint("KNOWN"),
        },
        "kernel_source_ref": deepcopy(GIT_TREE_REF),
        "base_kernel_source_ref": deepcopy(GIT_TREE_REF),
        "resolution_mode": None,
        "change_refs": [],
        "change_result_evidence_refs": [],
        "change_free_verification_evidence_refs": [],
        "reobservation": None,
        "evidence_sufficiency_request": None,
        "after_state_semantic_state": None,
        "source_snapshot_refs": [],
        "producing_change_refs": [],
        "candidate_invariant_evaluation_bindings": [],
        "candidate_claim_evaluation_bindings": [],
        "material_contradictions": [],
        "terminal_reason_evidence_refs": [
            {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
        ],
        "proposed_terminal_status": "BLOCKED",
        "evaluated_at": EVALUATED_AT,
    }


def candidate_closure_request(difference: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """A fully wired ``CANDIDATE_CLOSURE``-eligible request: every gate should PASS."""

    reobservation_request, after_ref, later_fingerprint = satisfied_reobservation(difference)
    current_state = {"revision": AFTER_REVISION, "fingerprint": later_fingerprint}
    request = base_closure_request(difference, policy)
    request.update(
        {
            "current_state": current_state,
            "resolution_mode": "CHANGE_FREE",
            "change_free_verification_evidence_refs": [
                {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
            ],
            "reobservation": {
                "derivation_request": reobservation_request,
                "after_observation_refs": [after_ref],
            },
            "evidence_sufficiency_request": sufficiency_request(
                difference_id=difference["difference_id"], policy=policy
            ),
            "after_state_semantic_state": semantic_state("KNOWN"),
            "source_snapshot_refs": [{"kind": "source_snapshot", "id": "SNAP-0001"}],
            "candidate_claim_evaluation_bindings": [
                mandatory_x003_claim_binding(difference, current_state)
            ],
            "terminal_reason_evidence_refs": [],
            "proposed_terminal_status": "CLOSED",
        }
    )
    return request


def material_contradiction_record(
    *,
    impact: str = "MATERIAL",
    project_id: str = "PRJ-0001",
    detected_at_state_revision: int = AFTER_REVISION,
    detected_at_state_fingerprint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One schema-valid ``material_contradiction`` record, addressed by its own identity."""

    record: dict[str, Any] = {
        "schema_version": "0.1",
        "material_contradiction_id": "",
        "project_id": project_id,
        "contradiction_kind": "EVIDENCE_EVIDENCE",
        "subject_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [
                {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64},
                {"kind": "observation_evidence", "id": "EVIDENCE-" + "2" * 64},
            ],
        },
        "impact": impact,
        "reason": "two Observation Evidence records disagree on the same Target subject",
        "detected_at_state_revision": detected_at_state_revision,
        "detected_at_state_fingerprint": (
            detected_at_state_fingerprint
            if detected_at_state_fingerprint is not None
            else state_fingerprint("KNOWN")
        ),
        "material_contradiction_semantic_fingerprint": "sha256:" + "3" * 64,
    }
    record["material_contradiction_id"] = material_contradiction_id(record)
    return record
