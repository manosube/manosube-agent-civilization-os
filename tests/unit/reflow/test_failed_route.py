"""The ratified FAILED route (Phase 6, ADR-0030), carried one step further into Reflow.

```text
observe()               FAILED Observation
derive_differences()    UNKNOWN Difference
derive_evidence()       FAILED / E0 Observation Evidence
evaluate_sufficiency()  INSUFFICIENT
reflow()                State N+1 committed; no CLOSED event; no completion record
```

Issue #39 names this explicitly as a route that "must be retained." Phase 6's own
``tests/integration/evidence/test_public_failed_round_trip.py`` proves everything through
``evaluate_sufficiency()``; this file reuses the identical fixture composition and proves
the one step Phase 6 does not own -- that Reflow commits this INSUFFICIENT result as a real,
schema-valid, non-closing State transition rather than leaving it stranded.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from tests.difference_helpers import (
    negative_claim,
    observation_request,
    observation_scope,
    state_fingerprint,
)
from tests.evidence_helpers import BEFORE_REVISION, difference_request, observation_evidence_request
from tests.reflow_helpers import GIT_TREE_REF
from tests.state_helpers import SCHEMA_ROOT, initial_state

from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.validation import (
    DIFFERENCE_SCHEMA_BASE,
    validate_record,
)
from manosube_agent_civilization.evidence import evaluate_sufficiency
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

FAILURE_CLASS = "SOURCE_ERROR"


def _failed_observation_request() -> dict[str, Any]:
    request = observation_request(
        observation_scope(),
        [],
        state_fingerprint(),
        BEFORE_REVISION,
        negative_claims=[negative_claim("FAILED")],
    )
    request["attempts"][0]["result"] = "FAILED"
    request["attempts"][0]["failure_class"] = FAILURE_CLASS
    return request


def _first_derivation() -> dict[str, Any]:
    request = difference_request()
    request["bindings"][0]["observation_bundle"] = observe(_failed_observation_request())
    return derive_differences(request)


def _insufficient_sufficiency_request(first: dict[str, Any]) -> dict[str, Any]:
    from tests.evidence_helpers import sufficiency_request

    return sufficiency_request(
        difference_id=first["differences"][0]["difference_id"],
        policy=first["policies"][0],
        evidence_requests=[
            observation_evidence_request(observation=_failed_observation_request())
        ],
    )


def test_failed_route_reaches_insufficient_before_reflow_sees_it() -> None:
    first = _first_derivation()
    difference = first["differences"][0]
    assert difference["normalized_observed_state"]["knowledge_status"] == "UNKNOWN"

    result = evaluate_sufficiency(_insufficient_sufficiency_request(first))
    assert result["evidence_sufficiency_result"]["result"] == "INSUFFICIENT"


def test_failed_route_commits_state_without_closing_or_completing(tmp_path: Path) -> None:
    first = _first_derivation()
    difference = first["differences"][0]
    policy = first["policies"][0]

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = initial_state()
    project_state["project_id"] = difference["project_id"]
    project_state["semantic_fingerprint"] = fingerprint_project_state(
        project_state, schema_root=SCHEMA_ROOT
    ).as_dict()
    store.initialize(project_state["project_id"], project_state)

    closure_request = {
        "difference": difference,
        "current_status": "VERIFYING",
        "policy": policy,
        "difference_event_head_ref": deepcopy(difference["genesis_event_ref"]),
        "current_state": {
            "revision": project_state["state_revision"],
            "fingerprint": project_state["semantic_fingerprint"],
        },
        "kernel_source_ref": deepcopy(GIT_TREE_REF),
        "base_kernel_source_ref": deepcopy(GIT_TREE_REF),
        "resolution_mode": None,
        "change_refs": [],
        "change_result_evidence_refs": [],
        "change_result_evidence_requests": [],
        "change_free_verification_evidence_refs": [],
        "reobservation": None,
        "evidence_sufficiency_request": _insufficient_sufficiency_request(first),
        "after_state_semantic_state": None,
        "source_snapshot_refs": [],
        "producing_change_refs": [],
        "candidate_invariant_evaluation_bindings": [],
        "candidate_claim_evaluation_bindings": [],
        "candidate_claim_evaluation_events": [],
        "invariant_evaluations": [],
        "kernel_source_witness": None,
        "material_contradictions": [],
        "terminal_reason_evidence_refs": [
            {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
        ],
        "proposed_terminal_status": "BLOCKED",
        "evaluated_at": "2026-08-30T12:00:00Z",
    }

    result = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        closure_request=closure_request,
        observation_refs=[],
        reflow_instant="2026-08-30T12:00:00Z",
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

    # The two ratified prohibitions from ADR-0030, now proven one step further downstream:
    # no CLOSED event, no completion record -- here, no closure_evaluation_ref at all, since
    # the evaluation never reached SATISFIED.
    assert result["decision"]["to_status"] == "BLOCKED"
    # closure_evaluation.schema.json's own result enum has no INSUFFICIENT value -- that is
    # Evidence Sufficiency's vocabulary. The candidate-free TERMINAL_POLICY_ONLY route this
    # missing-candidate closure request takes always resolves to BLOCKED; the INSUFFICIENT
    # verdict is checked directly, above, against Evidence's own result.
    assert result["evaluation"]["result"] == "BLOCKED"
    assert result["event"]["to_status"] == "BLOCKED"
    assert result["event"]["reflow_transition_ref"] is None
    validate_record(
        result["event"], "difference_lifecycle_event.schema.json", base=DIFFERENCE_SCHEMA_BASE
    )
    # The State transition still committed for real: R-005, FAILED_AND_BLOCKED_RESULTS_REFLOWED.
    assert result["committed_state"]["state_revision"] == project_state["state_revision"] + 1
    assert {"kind": "difference", "id": difference["difference_id"]} in (
        result["committed_state"]["semantic_state"]["open_differences"]
    )
    assert store.load_current(project_state["project_id"]) == result["committed_state"]
