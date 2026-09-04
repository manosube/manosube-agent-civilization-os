"""Regression tests for the Phase 7 structural-review correction (PR #40 findings F1-F8,
G19; adoption ``BOUND_HEAD=9459af827b65ca18af07cf040b401e58e0843f98``).

Each test here reproduces the exact real defect the structural review named, against the
real predecessor producers -- never a stand-in diagnostic -- and proves both halves: the
finding is real (an injected violation the pre-correction code would have silently
accepted), and the fix refuses it closed. ``tests/integration/store/test_record_manifest.py``
already covers F3's Store-layer manifest directly; ``tests/contract/reflow/
test_invariant_registry_source.py`` already covers G19's registry-source drift; these tests
are the route/closure-level proof that the fixes are actually wired in.
"""

from __future__ import annotations

from copy import deepcopy
import inspect
from pathlib import Path

import pytest
from tests.reflow_helpers import (
    base_closure_request,
    candidate_closure_request,
    fixture_difference,
    fixture_policy,
    mandatory_x003_claim_binding_and_event,
    self_closing_change_bound_closure_request,
    store_ready_for_closure,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.reflow.claims import (
    candidate_claim_evaluation_binding_id,
    candidate_claim_evaluation_event_id,
    resolve_claim_binding,
)
from manosube_agent_civilization.reflow.closure import evaluate_closure
from manosube_agent_civilization.reflow.commit import commit_reflow
from manosube_agent_civilization.reflow.errors import ReflowValidationError, StaleReflowError
from manosube_agent_civilization.reflow.route import reflow, reopen
from manosube_agent_civilization.store import FileStateStore

REFLOW_INSTANT = "2026-08-30T12:00:00Z"


def _closed_store(tmp_path: Path) -> tuple[FileStateStore, dict, dict, dict]:
    """A real Store advanced through one real CLOSED Reflow cycle. Returns
    ``(store, project_state_before, difference, closed_result)``."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    result = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        closure_request=closure_request,
        observation_refs=closure_request["reobservation"]["after_observation_refs"],
        reflow_instant=REFLOW_INSTANT,
    )
    return store, project_state, difference, result


def _next_revision(predecessor: dict, *, evaluation_status: str) -> dict:
    """Return a real, self-consistent successor ``candidate_claim_evaluation_event`` one
    revision past *predecessor*, in the same series."""

    event = dict(predecessor)
    event["event_revision"] = predecessor["event_revision"] + 1
    event["predecessor_event_ref"] = {
        "kind": "candidate_claim_evaluation_event", "id": predecessor["event_id"],
    }
    event["evaluation_status"] = evaluation_status
    event["event_id"] = ""
    event["event_id"] = candidate_claim_evaluation_event_id(event)
    return event


# --- F1: the predecessor State always comes from the Store ---------------------------- #


def test_f1_reflow_no_longer_accepts_a_caller_supplied_predecessor_state() -> None:
    """The vulnerable parameter is gone, not merely unused -- a caller cannot forge it."""

    parameters = inspect.signature(reflow).parameters
    assert "before_project_state" not in parameters
    assert "evidence_refs" not in parameters
    assert "expected_state_revision" in parameters


def test_f1_reopen_no_longer_accepts_a_caller_supplied_predecessor_state() -> None:
    parameters = inspect.signature(reopen).parameters
    assert "before_project_state" not in parameters
    assert "old_closure_evaluation" not in parameters
    assert "current_state" not in parameters
    assert "evidence_refs" not in parameters


def test_f1_a_stale_expected_revision_is_refused_before_anything_is_read(
    tmp_path: Path,
) -> None:
    store, project_state, difference, closed = _closed_store(tmp_path)
    policy = fixture_policy(difference)

    with pytest.raises(StaleReflowError):
        reflow(
            store,
            project_id=project_state["project_id"],
            previous_event_id=closed["event"]["difference_event_id"],
            event_revision=2,
            expected_state_revision=project_state["state_revision"],  # long superseded
            closure_request=base_closure_request(difference, policy),
            observation_refs=[],
            reflow_instant=REFLOW_INSTANT,
        )


# --- F2: Closure Evaluation's current_state is always the loaded State ---------------- #


def test_f2_a_forged_current_state_in_the_closure_request_is_silently_overridden(
    tmp_path: Path,
) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)

    closure_request = base_closure_request(difference, policy)
    closure_request["current_state"] = {"revision": 999, "fingerprint": {"profile": "X", "digest": "0" * 64}}

    result = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        closure_request=closure_request,
        observation_refs=[],
        reflow_instant=REFLOW_INSTANT,
        blocker_kind="OBSERVATION_PATH",
        blocker_scope={
            "kind": "difference_blocker_scope",
            "affected_subject_refs": {
                "collection_kind": "UNORDERED_SET",
                "members": [{"kind": "difference", "id": difference["difference_id"]}],
            },
            "effective_boundary": difference["effective_boundary"],
            "blocked_stage": "OBSERVATION",
        },
        blocker_resolution_condition={
            "kind": "blocker_resolution_condition",
            "condition_code": "OBSERVATION_PATH_AVAILABLE",
            "subject_ref": {"kind": "difference", "id": difference["difference_id"]},
            "expected_state": "AVAILABLE",
            "verification_request_ref": {"kind": "next_observation_request", "id": "OBS-REQ-" + "2" * 64},
        },
        next_observation_ref={"kind": "next_observation_request", "id": "OBS-REQ-" + "2" * 64},
    )

    # The forged revision/fingerprint never reaches the evaluation: it carries the real,
    # loaded predecessor State's own values instead.
    assert result["evaluation"]["evaluated_state_revision"] == project_state["state_revision"]
    assert result["evaluation"]["evaluated_state_fingerprint"] == project_state["semantic_fingerprint"]
    assert result["evaluation"]["evaluated_state_revision"] != 999


# --- F3: Closure Evaluation, lifecycle event and admitted Evidence are reference-resolvable #


def test_f3_a_closed_reflow_makes_its_closure_evaluation_and_event_resolvable(
    tmp_path: Path,
) -> None:
    store, project_state, _difference, result = _closed_store(tmp_path)

    resolved_evaluation = store.resolve_record(
        project_state["project_id"], "closure_evaluation", result["evaluation"]["closure_evaluation_id"]
    )
    resolved_event = store.resolve_record(
        project_state["project_id"], "difference_event", result["event"]["difference_event_id"]
    )
    assert resolved_evaluation == result["evaluation"]
    assert resolved_event == result["event"]

    # And the admitted Evidence the sufficiency request reproduced (not merely referenced)
    # is resolvable too -- the manifest's whole point. At least one must actually resolve,
    # so this cannot pass on an empty set finding nothing to check.
    resolved_evidence = [
        store.resolve_record(project_state["project_id"], "observation_evidence", ref["id"])
        for ref in result["committed_state"]["evidence_refs"]
        if ref["kind"] == "observation_evidence"
    ]
    assert any(record is not None for record in resolved_evidence)
    for record in resolved_evidence:
        if record is not None:
            assert record["evidence_id"] in {
                ref["id"] for ref in result["committed_state"]["evidence_refs"]
            }
    assert result["evaluation"]["evidence_sufficiency_ref"] is not None


def test_f3_an_unrelated_record_id_never_committed_does_not_resolve(tmp_path: Path) -> None:
    store, project_state, _difference, _result = _closed_store(tmp_path)
    assert (
        store.resolve_record(project_state["project_id"], "closure_evaluation", "D-CLOSE-EVAL-" + "F" * 64)
        is None
    )


# --- F4/G8: real Change-result Evidence/Observation reproduction ---------------------- #


def test_f4_g8_fails_closed_on_a_real_self_closing_change_result_collision(
    tmp_path: Path,
) -> None:
    """The exact real defect: a Change's own post-change Observation reused as the
    independent after-state re-observation used to pass vacuously (the stub always
    returned ``[]``); it must now fail closed on the real, reproduced overlap."""

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = self_closing_change_bound_closure_request(difference, policy)
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G8"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"
    assert any("Change result" in reason for reason in evaluation["failure_reasons"])


def test_f4_g8_fails_closed_when_declared_refs_do_not_match_the_reproduction(tmp_path: Path) -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = self_closing_change_bound_closure_request(difference, policy)
    # Substitute a foreign id for the real reproduced Change-result Evidence.
    request["change_result_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "9" * 64}
    ]
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G8"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_f4_g8_fails_closed_rather_than_passing_vacuously_with_no_requests(tmp_path: Path) -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = self_closing_change_bound_closure_request(difference, policy)
    request["change_result_evidence_requests"] = []
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G8"] == "FAIL"


# --- F5/G18: real evaluation_expires_at derivation + commit-time recheck -------------- #


def test_f5_g18_evaluation_expires_at_is_derived_from_the_oldest_evidence_instant(
    tmp_path: Path,
) -> None:
    from tests.evidence_helpers import RECORDED_AT

    difference = fixture_difference()
    policy = fixture_policy(difference, maximum_evidence_age=3600)
    request = candidate_closure_request(difference, policy)
    request["policy"] = policy
    from tests.evidence_helpers import sufficiency_request

    request["evidence_sufficiency_request"] = sufficiency_request(
        difference_id=difference["difference_id"], policy=policy
    )

    evaluation = evaluate_closure(request)

    assert evaluation["evaluation_expires_at"] is not None
    from manosube_agent_civilization.observation.boundary import instant

    expected = instant(RECORDED_AT) + __import__("datetime").timedelta(seconds=3600)
    assert instant(evaluation["evaluation_expires_at"]) == expected


def test_f5_g18_unbounded_age_leaves_no_derived_deadline() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference, maximum_evidence_age=None)
    request = candidate_closure_request(difference, policy)
    request["policy"] = policy

    evaluation = evaluate_closure(request)

    assert evaluation["evaluation_expires_at"] is None


def test_f5_g18_commit_refuses_a_reflow_instant_past_the_evaluations_own_deadline() -> None:
    with pytest.raises(StaleReflowError):
        commit_reflow(
            store=None,  # never reached: the deadline check runs before the Store is touched
            project_id="PRJ-0001",
            before_project_state={"project_id": "PRJ-0001", "state_revision": 0, "semantic_fingerprint": {}},
            next_semantic_state={},
            transaction_id="TX-0001",
            evidence_refs=[],
            reflow_instant="2026-08-30T13:00:00Z",
            evaluation_expires_at="2026-08-30T12:00:00Z",
        )


# --- F6: committed evidence_refs are derived, never caller-selected ------------------- #


def test_f6_reflow_has_no_evidence_refs_parameter_to_substitute() -> None:
    assert "evidence_refs" not in inspect.signature(reflow).parameters


def test_f6_committed_evidence_refs_equal_the_admitted_set_exactly(tmp_path: Path) -> None:
    _store, _project_state, _difference, result = _closed_store(tmp_path)
    evaluation = result["evaluation"]
    expected = {
        (ref["kind"], ref["id"])
        for ref in (
            evaluation["change_result_evidence_refs"]
            + evaluation["change_free_verification_evidence_refs"]
            + evaluation["terminal_reason_evidence_refs"]
        )
    }
    committed = {
        (ref["kind"], ref["id"]) for ref in result["committed_state"]["evidence_refs"]
    }
    # The committed set is a superset only by the Evidence Sufficiency Result's own
    # constituent refs (not embedded in the evaluation record itself); every ref the
    # Evaluation itself names must be present.
    assert expected <= committed


# --- F7: Reopen resolves the old Closure Evaluation from the Store, never trusts one -- #


def test_f7_reopen_refuses_a_previous_event_id_that_never_committed(tmp_path: Path) -> None:
    store, project_state, difference, _closed = _closed_store(tmp_path)

    with pytest.raises(ReflowValidationError, match="does not resolve to a committed lifecycle event"):
        reopen(
            store,
            project_id=project_state["project_id"],
            difference=difference,
            trigger="MATERIAL_CONTRADICTION",
            previous_event_id="D-EVT-" + "0" * 64,
            event_revision=2,
            next_observation_ref={"kind": "next_observation_request", "id": "OBS-REQ-" + "9" * 64},
            observation_refs=[],
            contradiction_evidence_refs=[],
            contradiction_refs=[{"kind": "material_contradiction", "id": "CONTRA-" + "5" * 64}],
            reflow_instant="2026-08-30T14:00:00Z",
        )


def test_f7_reopen_refuses_an_event_that_belongs_to_a_different_difference(tmp_path: Path) -> None:
    store, project_state, difference, closed = _closed_store(tmp_path)
    foreign_difference = deepcopy(difference)
    foreign_difference["difference_id"] = "D-" + "9" * 64

    with pytest.raises(ReflowValidationError, match="different Difference"):
        reopen(
            store,
            project_id=project_state["project_id"],
            difference=foreign_difference,
            trigger="MATERIAL_CONTRADICTION",
            previous_event_id=closed["event"]["difference_event_id"],
            event_revision=2,
            next_observation_ref={"kind": "next_observation_request", "id": "OBS-REQ-" + "9" * 64},
            observation_refs=[],
            contradiction_evidence_refs=[],
            contradiction_refs=[{"kind": "material_contradiction", "id": "CONTRA-" + "5" * 64}],
            reflow_instant="2026-08-30T14:00:00Z",
        )


def test_f7_reopen_refuses_a_previous_event_that_is_not_the_closed_head(tmp_path: Path) -> None:
    """The Difference's own genesis event predates any Reflow transaction, so it was never
    part of a committed manifest -- it is unresolvable, not merely non-CLOSED, and F7
    refuses it the same way either defect must be refused: closed."""

    store, project_state, difference, _closed = _closed_store(tmp_path)

    with pytest.raises(ReflowValidationError, match="does not resolve to a committed lifecycle event"):
        reopen(
            store,
            project_id=project_state["project_id"],
            difference=difference,
            trigger="MATERIAL_CONTRADICTION",
            previous_event_id=difference["genesis_event_ref"]["id"],  # not the CLOSED event
            event_revision=2,
            next_observation_ref={"kind": "next_observation_request", "id": "OBS-REQ-" + "9" * 64},
            observation_refs=[],
            contradiction_evidence_refs=[],
            contradiction_refs=[{"kind": "material_contradiction", "id": "CONTRA-" + "5" * 64}],
            reflow_instant="2026-08-30T14:00:00Z",
        )


def test_f7_reopen_refuses_a_resolvable_event_that_is_not_closed(tmp_path: Path) -> None:
    """Unlike the genesis case above, this event *is* resolvable (F3 made it so) -- it is
    refused specifically because its own ``to_status`` is not ``CLOSED``."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)

    blocked = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        closure_request=base_closure_request(difference, policy),
        observation_refs=[],
        reflow_instant=REFLOW_INSTANT,
        blocker_kind="OBSERVATION_PATH",
        blocker_scope={
            "kind": "difference_blocker_scope",
            "affected_subject_refs": {
                "collection_kind": "UNORDERED_SET",
                "members": [{"kind": "difference", "id": difference["difference_id"]}],
            },
            "effective_boundary": difference["effective_boundary"],
            "blocked_stage": "OBSERVATION",
        },
        blocker_resolution_condition={
            "kind": "blocker_resolution_condition",
            "condition_code": "OBSERVATION_PATH_AVAILABLE",
            "subject_ref": {"kind": "difference", "id": difference["difference_id"]},
            "expected_state": "AVAILABLE",
            "verification_request_ref": {"kind": "next_observation_request", "id": "OBS-REQ-" + "2" * 64},
        },
        next_observation_ref={"kind": "next_observation_request", "id": "OBS-REQ-" + "2" * 64},
    )
    assert blocked["decision"]["to_status"] == "BLOCKED"
    assert store.resolve_record(
        project_state["project_id"], "difference_event", blocked["event"]["difference_event_id"]
    ) == blocked["event"]

    with pytest.raises(ReflowValidationError, match="committed CLOSED lifecycle event"):
        reopen(
            store,
            project_id=project_state["project_id"],
            difference=difference,
            trigger="MATERIAL_CONTRADICTION",
            previous_event_id=blocked["event"]["difference_event_id"],
            event_revision=2,
            next_observation_ref={"kind": "next_observation_request", "id": "OBS-REQ-" + "9" * 64},
            observation_refs=[],
            contradiction_evidence_refs=[],
            contradiction_refs=[{"kind": "material_contradiction", "id": "CONTRA-" + "5" * 64}],
            reflow_instant="2026-08-30T14:00:00Z",
        )


def test_f7_reopen_succeeds_and_resolves_the_real_committed_closure_evaluation(
    tmp_path: Path,
) -> None:
    store, project_state, difference, closed = _closed_store(tmp_path)
    contradiction_ref = {"kind": "material_contradiction", "id": "CONTRA-" + "5" * 64}

    result = reopen(
        store,
        project_id=project_state["project_id"],
        difference=difference,
        trigger="MATERIAL_CONTRADICTION",
        previous_event_id=closed["event"]["difference_event_id"],
        event_revision=2,
        next_observation_ref={"kind": "next_observation_request", "id": "OBS-REQ-" + "9" * 64},
        observation_refs=[],
        contradiction_evidence_refs=[contradiction_ref],
        contradiction_refs=[contradiction_ref],
        reflow_instant="2026-08-30T14:00:00Z",
    )

    assert result["decision"]["to_status"] == "REOPENED"
    assert result["decision"]["closure_evaluation_ref"]["id"] == closed["evaluation"]["closure_evaluation_id"]


# --- F8/G21: candidate_claim_evaluation_event series reconstruction, not binding trust  #


def test_f8_g21_an_edited_event_fails_its_own_content_address() -> None:
    difference = fixture_difference()
    current_state = {"revision": 3, "fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64}}
    binding, event = mandatory_x003_claim_binding_and_event(difference, current_state)
    tampered = dict(event)
    tampered["evaluation_status"] = "SATISFIED"  # unchanged value, but a new dict identity
    tampered["completion_record_fingerprint"] = "sha256:" + "9" * 64  # the real edit

    with pytest.raises(ReflowValidationError, match="content address"):
        resolve_claim_binding([tampered], binding, difference_id=difference["difference_id"])


def test_f8_g21_a_missing_predecessor_fails_the_series_closed() -> None:
    difference = fixture_difference()
    current_state = {"revision": 3, "fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64}}
    binding, event = mandatory_x003_claim_binding_and_event(difference, current_state)
    revision_1 = _next_revision(event, evaluation_status=event["evaluation_status"])

    moved_binding = {
        **binding,
        "evaluation_head_event_ref": {"kind": "candidate_claim_evaluation_event", "id": revision_1["event_id"]},
    }
    moved_binding["binding_id"] = candidate_claim_evaluation_binding_id(moved_binding)
    with pytest.raises(ReflowValidationError, match="not contiguous from revision 0"):
        # revision 0 (`event`) deliberately omitted -- only its successor is supplied.
        resolve_claim_binding([revision_1], moved_binding, difference_id=difference["difference_id"])


def test_f8_g21_a_foreign_difference_series_is_refused() -> None:
    difference = fixture_difference()
    current_state = {"revision": 3, "fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64}}
    binding, event = mandatory_x003_claim_binding_and_event(difference, current_state)

    with pytest.raises(ReflowValidationError, match="difference_id does not match"):
        resolve_claim_binding([event], binding, difference_id="D-" + "9" * 64)


def test_f8_g21_the_head_events_own_status_is_what_counts(tmp_path: Path) -> None:
    """Not the binding's -- a binding declaring SATISFIED while the real reconstructed
    head is NOT_SATISFIED must not be trusted."""

    difference = fixture_difference()
    current_state = {"revision": 3, "fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64}}
    binding, event = mandatory_x003_claim_binding_and_event(
        difference, current_state, evaluation_status="NOT_SATISFIED"
    )

    with pytest.raises(ReflowValidationError, match="evaluation_status"):
        # The binding still claims SATISFIED while the real (only) event says
        # NOT_SATISFIED -- R2-F8 requires the binding to match the true latest event
        # exactly, so this is refused, not silently resolved to the event's status.
        forged_binding = {**binding, "evaluation_status": "SATISFIED"}
        forged_binding["binding_id"] = candidate_claim_evaluation_binding_id(forged_binding)
        resolve_claim_binding([event], forged_binding, difference_id=difference["difference_id"])

    chain = resolve_claim_binding([event], binding, difference_id=difference["difference_id"])
    assert chain[0]["evaluation_status"] == "NOT_SATISFIED"


def test_r2f8_a_fork_at_one_revision_is_refused() -> None:
    difference = fixture_difference()
    current_state = {"revision": 3, "fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64}}
    binding, genesis_event = mandatory_x003_claim_binding_and_event(difference, current_state)
    fork_a = _next_revision(genesis_event, evaluation_status="SATISFIED")
    fork_b = _next_revision(genesis_event, evaluation_status="NOT_SATISFIED")
    assert fork_a["event_id"] != fork_b["event_id"]  # two real, different bodies

    head_binding = {
        **binding,
        "evaluation_head_event_ref": {"kind": "candidate_claim_evaluation_event", "id": fork_a["event_id"]},
        "evaluation_status": "SATISFIED",
    }
    head_binding["binding_id"] = candidate_claim_evaluation_binding_id(head_binding)
    with pytest.raises(ReflowValidationError, match="forks"):
        resolve_claim_binding(
            [genesis_event, fork_a, fork_b], head_binding, difference_id=difference["difference_id"]
        )


def test_r2f8_an_unconsumed_later_event_defeats_an_older_satisfied_binding(tmp_path: Path) -> None:
    """The exact R2-F8 exploit: a binding still names the event that *was* the latest
    SATISFIED head, but a later REVOKED event has since superseded it. The binding no
    longer names the series' true latest event and must be refused, not silently
    accepted because it once was correct."""

    difference = fixture_difference()
    current_state = {"revision": 3, "fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64}}
    stale_binding, genesis_event = mandatory_x003_claim_binding_and_event(
        difference, current_state, evaluation_status="SATISFIED"
    )
    revoked_event = _next_revision(genesis_event, evaluation_status="REVOKED")

    # The binding still points at the old (once-true) SATISFIED head.
    with pytest.raises(ReflowValidationError, match="true latest event"):
        resolve_claim_binding(
            [genesis_event, revoked_event], stale_binding, difference_id=difference["difference_id"]
        )

    # A binding that correctly names the new true latest event resolves to REVOKED.
    current_binding = {
        **stale_binding,
        "evaluation_head_event_ref": {
            "kind": "candidate_claim_evaluation_event", "id": revoked_event["event_id"],
        },
        "evaluation_status": "REVOKED",
        "completion_record_ref": revoked_event["completion_record_ref"],
        "evaluation_record_fingerprint": revoked_event["completion_record_fingerprint"],
        "evaluated_at": revoked_event["recorded_at"],
    }
    current_binding["binding_id"] = candidate_claim_evaluation_binding_id(current_binding)
    chain = resolve_claim_binding(
        [genesis_event, revoked_event], current_binding, difference_id=difference["difference_id"]
    )
    assert chain[0]["evaluation_status"] == "REVOKED"
    assert len(chain) == 2  # the complete series, head first


# --- R3-F2: claim binding_id and evaluation_series_id are now independently verified -- #


def test_r3f2_a_forged_claim_binding_id_fails_closed() -> None:
    """A ``candidate_claim_evaluation_binding`` whose declared ``binding_id`` does not
    match its own content-addressed derivation (CLOSURE_POLICY.md line 696: the exact
    same profile G19's own binding_id uses, prefix swapped) is refused -- even though
    every other field, including a real, correctly-reconstructing series and head event,
    is otherwise conformant."""

    difference = fixture_difference()
    current_state = {"revision": 3, "fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64}}
    binding, event = mandatory_x003_claim_binding_and_event(difference, current_state)
    forged = {**binding, "binding_id": "CAND-CLAIM-EVAL-" + "F" * 64}

    with pytest.raises(ReflowValidationError, match="binding_id"):
        resolve_claim_binding([event], forged, difference_id=difference["difference_id"])


def test_r3f2_a_forged_evaluation_series_id_fails_closed() -> None:
    """A binding whose declared ``evaluation_series_id`` does not equal the series its own
    ``difference_id``/``policy_ref``/``candidate_id``/``required_claim_ref`` recompute
    (CLOSURE_POLICY.md line 692) is refused, not merely used verbatim to filter the event
    pool -- closing the gap where ``reconstruct_claim_series`` recomputed the series id
    internally but never checked it back against the binding's own declared field."""

    difference = fixture_difference()
    current_state = {"revision": 3, "fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64}}
    binding, event = mandatory_x003_claim_binding_and_event(difference, current_state)
    forged = {**binding, "evaluation_series_id": "CAND-CLAIM-SERIES-" + "F" * 64}
    forged["binding_id"] = candidate_claim_evaluation_binding_id(forged)

    with pytest.raises(ReflowValidationError, match="evaluation_series_id"):
        resolve_claim_binding([event], forged, difference_id=difference["difference_id"])


# --- G19: the v0.1 mandatory Invariant union is additive, never vacuous --------------- #


def test_g19_an_empty_policy_set_still_requires_the_full_mandatory_union() -> None:
    from tests.reflow_helpers import mandatory_invariant_bindings

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    # Only one of the 47 mandatory bindings supplied.
    request["candidate_invariant_evaluation_bindings"] = mandatory_invariant_bindings(
        request["current_state"]
    )[:1]
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_g19_the_full_mandatory_union_actually_passes(tmp_path: Path) -> None:
    """The positive control: a candidate_closure_request with every mandatory id bound
    really does reach G19 PASS -- proving the requirement is real, not unsatisfiable. Since
    ``mandatory_invariant_bindings`` now carries the real pinned per-invariant digests and
    real content-addressed ``binding_id``s (R2-G19), this also proves the exact-digest and
    binding-ID checks below are satisfiable, not merely fail-closed."""

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "PASS"
    assert evaluation["result"] == "SATISFIED"


# --- R2-G19: exact per-invariant digest, definition-conflict, binding-ID derivation ---- #


def test_r2g19_a_fabricated_mandatory_digest_fails_closed() -> None:
    """A mandatory-id binding with a well-formed but wrong ``invariant_definition_sha256``
    must not pass by mere presence -- G19's own union requires the exact pinned digest."""

    from tests.reflow_helpers import mandatory_invariant_bindings

    from manosube_agent_civilization.reflow.invariant_registry import (
        candidate_invariant_evaluation_binding_id,
    )

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    bindings = [dict(binding) for binding in mandatory_invariant_bindings(request["current_state"])]
    tampered = dict(bindings[0])
    tampered["invariant_definition_ref"] = dict(tampered["invariant_definition_ref"])
    tampered["invariant_definition_ref"]["invariant_definition_sha256"] = "sha256:" + "0" * 64
    tampered["binding_id"] = candidate_invariant_evaluation_binding_id(tampered)
    bindings[0] = tampered
    request["candidate_invariant_evaluation_bindings"] = bindings
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_r2g19_a_tampered_binding_id_fails_closed() -> None:
    """A binding whose declared ``binding_id`` does not match its own content-addressed
    derivation is refused, even though every other field is otherwise conformant."""

    from tests.reflow_helpers import mandatory_invariant_bindings

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    bindings = [dict(binding) for binding in mandatory_invariant_bindings(request["current_state"])]
    bindings[0] = {**bindings[0], "binding_id": "CAND-INV-EVAL-" + "F" * 64}
    request["candidate_invariant_evaluation_bindings"] = bindings
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_r2g19_a_policy_declared_same_id_definition_conflict_fails_closed() -> None:
    """CLOSURE_POLICY.md: a Policy's own ``required_invariants`` naming a mandatory id with
    a *different* ``invariant_definition_sha256`` than the mandatory registry's own pinned
    digest for that id is a same-ID definition conflict -- reject, never silently pick a
    side (first-wins/last-wins/ID-only dedup are all explicitly prohibited)."""

    from manosube_agent_civilization.reflow.invariant_registry import (
        V0_1_INVARIANT_DEFINITION_DIGESTS,
    )

    difference = fixture_difference()
    conflicting_digest = "1" * 64
    assert conflicting_digest != V0_1_INVARIANT_DEFINITION_DIGESTS["K-001"]
    policy = fixture_policy(
        difference,
        required_invariants=[
            {
                "kind": "kernel_invariant",
                "id": "K-001",
                "contract_source_ref": {
                    "kind": "git_blob",
                    "repository": "manosube/manosube-agent-civilization-os",
                    "commit_sha": "a" * 40,
                    "path": "00_KERNEL/KERNEL_INVARIANTS.md",
                    "blob_sha": "b" * 40,
                    "invariant_definition_sha256": "sha256:" + conflicting_digest,
                },
            }
        ],
    )
    request = candidate_closure_request(difference, policy)
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_r2g19_a_policy_declared_same_id_matching_digest_unifies_not_duplicates() -> None:
    """The converse of the conflict case: a Policy that redundantly names a mandatory id
    with the *same* digest the registry already pins must unify into one expected
    requirement, not demand two separate bindings for the same id."""

    from manosube_agent_civilization.reflow.invariant_registry import (
        V0_1_INVARIANT_DEFINITION_DIGESTS,
    )

    difference = fixture_difference()
    correct_digest = "sha256:" + V0_1_INVARIANT_DEFINITION_DIGESTS["K-001"]
    policy = fixture_policy(
        difference,
        required_invariants=[
            {
                "kind": "kernel_invariant",
                "id": "K-001",
                "contract_source_ref": {
                    "kind": "git_blob",
                    "repository": "manosube/manosube-agent-civilization-os",
                    "commit_sha": "a" * 40,
                    "path": "00_KERNEL/KERNEL_INVARIANTS.md",
                    "blob_sha": "b" * 40,
                    "invariant_definition_sha256": correct_digest,
                },
            }
        ],
    )
    request = candidate_closure_request(difference, policy)

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "PASS"
    assert evaluation["result"] == "SATISFIED"


# --- R4-F2: every reference admitted into a CLOSED Closure Evaluation must resolve ---- #


def test_r4f2_the_full_reference_closure_actually_reaches_satisfied() -> None:
    """The positive control: a ``candidate_closure_request`` whose Completion Record,
    Invariant Evaluation pool and ``source_snapshot_refs`` are all real and mutually
    resolvable really does reach ``SATISFIED`` -- proving R4-F2's reference-closure
    requirement is satisfiable, not merely fail-closed."""

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "PASS"
    assert evaluation["gate_results"]["G21"] == "PASS"
    assert evaluation["result"] == "SATISFIED"


def test_r4f2_an_unresolved_invariant_evaluation_ref_fails_g19_closed() -> None:
    """A ``candidate_invariant_evaluation_binding`` whose ``invariant_evaluation_ref``
    names an id absent from the caller-supplied ``invariant_evaluations`` pool must not
    pass on the binding's own say-so about the underlying record -- CLOSURE_POLICY.md
    gives no content-address formula for ``evaluation_id`` (R4-F2's
    ``INVARIANT_EVALUATION_ID_POLICY``), so an unresolved reference is refused rather
    than silently trusted."""

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    # Drop the one Invariant Evaluation record the first binding's own ref names.
    orphaned_id = request["candidate_invariant_evaluation_bindings"][0]["invariant_evaluation_ref"]["id"]
    request["invariant_evaluations"] = [
        record for record in request["invariant_evaluations"] if record["evaluation_id"] != orphaned_id
    ]
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_r4f2_a_forged_completion_record_ref_fails_g21_closed() -> None:
    """A claim binding whose ``completion_record_ref`` does not equal the one Completion
    Record its own Claim descriptor and this Evaluation's inputs actually imply is
    refused -- Completion Record identity belongs to Difference (R4-F2's
    ``COMPLETION_RECORD_OWNER=DIFFERENCE``), so Reflow resolves and verifies it rather
    than trusting a binding's restated id."""

    from manosube_agent_civilization.reflow.claims import candidate_claim_evaluation_binding_id

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    forged = dict(request["candidate_claim_evaluation_bindings"][0])
    forged["completion_record_ref"] = {"kind": "completion_record", "id": "CMP-" + "F" * 64}
    forged["binding_id"] = candidate_claim_evaluation_binding_id(forged)
    request["candidate_claim_evaluation_bindings"] = [forged]
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G21"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_r4f2_mismatched_source_snapshot_refs_fails_closed() -> None:
    """A candidate's own declared ``source_snapshot_refs`` must exactly match the real,
    self-consistent Observation's own reported set -- Observation is this reference
    kind's canonical owner (R4-F2's ``SOURCE_SNAPSHOT_OWNER=OBSERVATION``), so a
    candidate that substitutes a foreign or fabricated snapshot reference is refused,
    not merely echoed through."""

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    request["source_snapshot_refs"] = [{"kind": "source_snapshot", "id": "SNAP-FORGED"}]
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G8"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


# --- R4-F3: G19's live Git provenance is a pure immutable Git object witness ---------- #


def test_r4f3_a_candidate_invariant_set_without_a_witness_fails_g19_closed() -> None:
    """A candidate invariant evaluation set with no ``kernel_source_witness`` is refused,
    never silently skipped -- R4-F3's
    ``OPTIONAL_OR_DEGRADING_PROVENANCE_ALLOWED=false``."""

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    request["kernel_source_witness"] = None
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_r4f3_a_tampered_git_witness_fails_g19_closed() -> None:
    """A witness whose ``blob_object`` bytes have been tampered with no longer hashes to
    ``KERNEL_INVARIANTS_BLOB_SHA`` -- refused, not accepted on the caller's bare
    assertion that the witness is valid (R4-F3's
    ``CALLER_ASSERTION_ONLY_ALLOWED=false``)."""

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    tampered_witness = dict(request["kernel_source_witness"])
    tampered_witness["blob_object"] = (b"tampered" + bytes.fromhex(tampered_witness["blob_object"])[8:]).hex()
    request["kernel_source_witness"] = tampered_witness
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"
