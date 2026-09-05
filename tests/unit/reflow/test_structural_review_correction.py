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
from typing import Any

import pytest
from tests.difference_helpers import objective_revision
from tests.reflow_helpers import (
    base_closure_request,
    candidate_closure_request,
    fixture_difference,
    fixture_policy,
    mandatory_x003_claim_binding_and_event,
    real_terminal_reason_evidence_fields,
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
from manosube_agent_civilization.reflow.git_witness import build_kernel_source_witness_record
from manosube_agent_civilization.reflow.invariant_registry import (
    KERNEL_INVARIANTS_BLOB_SHA,
    KERNEL_INVARIANTS_PATH,
)
from manosube_agent_civilization.reflow.route import reflow, reopen
from manosube_agent_civilization.store import STAGES, FileStateStore
from manosube_agent_civilization.store.errors import SimulatedCrash

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
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

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
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G8"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_f4_g8_fails_closed_rather_than_passing_vacuously_with_no_requests(tmp_path: Path) -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = self_closing_change_bound_closure_request(difference, policy)
    request["change_result_evidence_requests"] = []
    request["proposed_terminal_status"] = "RETAINED"
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

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


def _placeholder_after_state_candidate(binding: dict[str, Any]) -> dict[str, Any]:
    """A real ``after_state_candidate`` that matches *binding*'s own placeholder candidate
    fields exactly -- these unit tests are about chain reconstruction, not candidate
    identity (R6-F2's own check, now inside :func:`resolve_claim_binding` itself, is
    covered by its own dedicated tests below)."""

    return {
        "candidate_id": binding["candidate_id"],
        "semantic_fingerprint": binding["candidate_semantic_fingerprint"],
    }


def test_f8_g21_an_edited_event_fails_its_own_content_address() -> None:
    difference = fixture_difference()
    current_state = {"revision": 3, "fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64}}
    binding, event = mandatory_x003_claim_binding_and_event(difference, current_state)
    tampered = dict(event)
    tampered["evaluation_status"] = "SATISFIED"  # unchanged value, but a new dict identity
    tampered["completion_record_fingerprint"] = "sha256:" + "9" * 64  # the real edit

    with pytest.raises(ReflowValidationError, match="content address"):
        resolve_claim_binding(
            [tampered],
            binding,
            difference_id=difference["difference_id"],
            after_state_candidate=_placeholder_after_state_candidate(binding),
        )


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
        resolve_claim_binding(
            [revision_1],
            moved_binding,
            difference_id=difference["difference_id"],
            after_state_candidate=_placeholder_after_state_candidate(moved_binding),
        )


def test_f8_g21_a_foreign_difference_series_is_refused() -> None:
    difference = fixture_difference()
    current_state = {"revision": 3, "fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64}}
    binding, event = mandatory_x003_claim_binding_and_event(difference, current_state)

    with pytest.raises(ReflowValidationError, match="difference_id does not match"):
        resolve_claim_binding(
            [event],
            binding,
            difference_id="D-" + "9" * 64,
            after_state_candidate=_placeholder_after_state_candidate(binding),
        )


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
        resolve_claim_binding(
            [event],
            forged_binding,
            difference_id=difference["difference_id"],
            after_state_candidate=_placeholder_after_state_candidate(forged_binding),
        )

    chain = resolve_claim_binding(
        [event],
        binding,
        difference_id=difference["difference_id"],
        after_state_candidate=_placeholder_after_state_candidate(binding),
    )
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
            [genesis_event, fork_a, fork_b],
            head_binding,
            difference_id=difference["difference_id"],
            after_state_candidate=_placeholder_after_state_candidate(head_binding),
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
            [genesis_event, revoked_event],
            stale_binding,
            difference_id=difference["difference_id"],
            after_state_candidate=_placeholder_after_state_candidate(stale_binding),
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
        [genesis_event, revoked_event],
        current_binding,
        difference_id=difference["difference_id"],
        after_state_candidate=_placeholder_after_state_candidate(current_binding),
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
        resolve_claim_binding(
            [event],
            forged,
            difference_id=difference["difference_id"],
            after_state_candidate=_placeholder_after_state_candidate(forged),
        )


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
        resolve_claim_binding(
            [event],
            forged,
            difference_id=difference["difference_id"],
            after_state_candidate=_placeholder_after_state_candidate(forged),
        )


# --- G19: the v0.1 mandatory Invariant union is additive, never vacuous --------------- #


def test_g19_an_empty_policy_set_still_requires_the_full_mandatory_union() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    # Only one of the 47 mandatory bindings supplied.
    request["candidate_invariant_evaluation_bindings"] = request[
        "candidate_invariant_evaluation_bindings"
    ][:1]
    request["proposed_terminal_status"] = "RETAINED"
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

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

    from manosube_agent_civilization.reflow.invariant_registry import (
        candidate_invariant_evaluation_binding_id,
    )

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    bindings = [dict(binding) for binding in request["candidate_invariant_evaluation_bindings"]]
    tampered = dict(bindings[0])
    tampered["invariant_definition_ref"] = dict(tampered["invariant_definition_ref"])
    tampered["invariant_definition_ref"]["invariant_definition_sha256"] = "sha256:" + "0" * 64
    tampered["binding_id"] = candidate_invariant_evaluation_binding_id(tampered)
    bindings[0] = tampered
    request["candidate_invariant_evaluation_bindings"] = bindings
    request["proposed_terminal_status"] = "RETAINED"
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_r2g19_a_tampered_binding_id_fails_closed() -> None:
    """A binding whose declared ``binding_id`` does not match its own content-addressed
    derivation is refused, even though every other field is otherwise conformant."""

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    bindings = [dict(binding) for binding in request["candidate_invariant_evaluation_bindings"]]
    bindings[0] = {**bindings[0], "binding_id": "CAND-INV-EVAL-" + "F" * 64}
    request["candidate_invariant_evaluation_bindings"] = bindings
    request["proposed_terminal_status"] = "RETAINED"
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

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
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

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
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

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
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

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
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

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
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

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
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


# --- R5-F1: candidate bindings must name the real after_state_candidate, never a bare id  #


def test_r5f1_the_real_candidate_closure_request_binds_the_true_after_state_candidate() -> None:
    """The positive control: ``candidate_closure_request``'s own bindings really do carry
    the real, content-addressed ``after_state_candidate``'s own ``candidate_id``/
    ``semantic_fingerprint`` -- proving R5-F1's binding requirement is satisfiable, and that
    the request this whole file's other positive controls already reach ``SATISFIED``
    through was never a coincidental id collision."""

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)

    evaluation = evaluate_closure(request)

    real_candidate = evaluation["after_state_candidate"]
    for binding in request["candidate_invariant_evaluation_bindings"]:
        assert binding["candidate_id"] == real_candidate["candidate_id"]
        assert binding["candidate_semantic_fingerprint"] == real_candidate["semantic_fingerprint"]
    for binding in request["candidate_claim_evaluation_bindings"]:
        assert binding["candidate_id"] == real_candidate["candidate_id"]
        assert binding["candidate_semantic_fingerprint"] == real_candidate["semantic_fingerprint"]
    assert evaluation["result"] == "SATISFIED"


def test_r5f1_an_invariant_binding_naming_a_foreign_candidate_fails_g19_closed() -> None:
    """A ``candidate_invariant_evaluation_binding`` whose own ``candidate_id`` does not
    match the real ``after_state_candidate`` this Evaluation is actually for is refused,
    even though it is otherwise a well-formed, self-consistent binding (its own
    ``binding_id`` still matches its own content-addressed derivation)."""

    from manosube_agent_civilization.reflow.invariant_registry import (
        candidate_invariant_evaluation_binding_id,
    )

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    bindings = [dict(binding) for binding in request["candidate_invariant_evaluation_bindings"]]
    forged = dict(bindings[0])
    forged["candidate_id"] = "STATE-CANDIDATE-" + "9" * 64
    forged["binding_id"] = candidate_invariant_evaluation_binding_id(forged)
    bindings[0] = forged
    request["candidate_invariant_evaluation_bindings"] = bindings
    request["proposed_terminal_status"] = "RETAINED"
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_r5f1_a_claim_binding_naming_a_foreign_candidate_fingerprint_fails_g21_closed() -> None:
    """A ``candidate_claim_evaluation_binding`` whose own ``candidate_semantic_fingerprint``
    does not match the real ``after_state_candidate``'s own ``semantic_fingerprint`` is
    refused -- a forged fingerprint alone, with a correct ``candidate_id``, is not enough to
    pass on the strength of the id alone."""

    from manosube_agent_civilization.reflow.claims import candidate_claim_evaluation_binding_id

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    forged = dict(request["candidate_claim_evaluation_bindings"][0])
    forged["candidate_semantic_fingerprint"] = {
        "profile": "MANOSUBE-STATE-SHA256-0.1",
        "digest": "9" * 64,
    }
    forged["binding_id"] = candidate_claim_evaluation_binding_id(forged)
    request["candidate_claim_evaluation_bindings"] = [forged]
    request["proposed_terminal_status"] = "RETAINED"
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    request["terminal_reason_evidence_requests"] = [_terminal_request]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G21"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


# --- R5-F2: the Completion Record and every Invariant Evaluation persist in the same    #
# --- transaction as a real CLOSED cycle, and resolve afterward, not only at evaluation  #
# --- time -----------------------------------------------------------------------------#


def test_r5f2_a_real_closed_reflow_makes_the_completion_record_and_all_invariant_evaluations_resolvable(
    tmp_path: Path,
) -> None:
    """The positive control this Round 5 finding demanded: after a real, committed CLOSED
    Reflow cycle (not merely a passing ``evaluate_closure`` call in memory), the Completion
    Record and all 47 mandatory Invariant Evaluation records the admitted bindings reference
    actually resolve from the Store -- proving the reference closure R4-F2 only verified is
    now also persisted, in the same atomic transaction, exactly where a later reader (a
    crash-recovery replay, a subsequent audit) would need to find them."""

    store, project_state, _difference, result = _closed_store(tmp_path)
    evaluation = result["evaluation"]

    invariant_bindings = evaluation["candidate_invariant_evaluation_bindings"]
    assert len(invariant_bindings) == 47
    for binding in invariant_bindings:
        ref = binding["invariant_evaluation_ref"]
        resolved = store.resolve_record(project_state["project_id"], ref["kind"], ref["id"])
        assert resolved is not None, f"invariant_evaluation {ref['id']} did not persist"
        assert resolved["evaluation_id"] == ref["id"]

    claim_bindings = evaluation["candidate_claim_evaluation_bindings"]
    assert len(claim_bindings) == 1
    completion_ref = claim_bindings[0]["completion_record_ref"]
    resolved_completion = store.resolve_record(
        project_state["project_id"], completion_ref["kind"], completion_ref["id"]
    )
    assert resolved_completion is not None
    assert resolved_completion["completion_id"] == completion_ref["id"]
    # The persisted record's own post-commit lineage field is the real transition this
    # cycle actually committed under -- not left null the way the pre-commit projection
    # G21 itself verified against necessarily is.
    assert resolved_completion["reflow_transition_ref"] == result["state_transition_ref"]


# --- R5-F4: an atomic preflight re-resolves every admitted record immediately before   #
# --- commit, never trusting evaluate_closure's own already-computed result across time #


def test_r5f4_preflight_reresolution_catches_a_post_evaluation_invariant_pool_mismatch(
    tmp_path: Path,
) -> None:
    """Even though ``evaluate_closure`` itself already verified every admitted Invariant
    Evaluation reference at evaluation time, Atomic Reflow re-resolves the exact same
    references one more time immediately before commit. Proven by making the Closure
    Evaluation ``reflow()`` receives claim a binding resolves against an
    ``invariant_evaluation_ref`` the real ``closure_request`` pool it is committing no
    longer supports (a genuine evaluate-time/commit-time divergence) -- the commit is
    refused, not promoted on the stale, already-computed result."""

    import manosube_agent_civilization.reflow.route as route_module

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    real_evaluate_closure = route_module.evaluate_closure  # type: ignore[attr-defined]

    def tampering_evaluate_closure(request: dict[str, Any]) -> dict[str, Any]:
        evaluation = real_evaluate_closure(request)
        tampered = dict(evaluation)
        bindings = [dict(binding) for binding in tampered["candidate_invariant_evaluation_bindings"]]
        bindings[0] = dict(bindings[0])
        bindings[0]["invariant_evaluation_ref"] = {
            "kind": "invariant_evaluation",
            "id": "INV-EVAL-" + "9" * 64,
        }
        tampered["candidate_invariant_evaluation_bindings"] = bindings
        return tampered

    route_module.evaluate_closure = tampering_evaluate_closure  # type: ignore[attr-defined]
    try:
        with pytest.raises(StaleReflowError, match="atomic preflight"):
            reflow(
                store,
                project_id=project_state["project_id"],
                closure_request=closure_request,
                previous_event_id=difference["genesis_event_ref"]["id"],
                event_revision=1,
                observation_refs=[],
                reflow_instant=REFLOW_INSTANT,
            )
    finally:
        route_module.evaluate_closure = real_evaluate_closure  # type: ignore[attr-defined]

    # The refused commit never advanced the Store.
    assert store.load_current(project_state["project_id"])["state_revision"] == project_state["state_revision"]


def test_r5f4_preflight_reresolution_catches_a_post_evaluation_witness_mismatch(
    tmp_path: Path,
) -> None:
    """The same preflight also re-verifies the Git provenance witness, not only the
    Invariant Evaluation pool -- a Closure Evaluation claiming G19 passed against a witness
    the real ``closure_request`` no longer carries intact is refused at commit time too."""

    import manosube_agent_civilization.reflow.route as route_module

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    real_evaluate_closure = route_module.evaluate_closure  # type: ignore[attr-defined]

    def tampering_evaluate_closure(request: dict[str, Any]) -> dict[str, Any]:
        # Compute the real, correctly-SATISFIED Evaluation first, against the real witness
        # -- then tamper *request* itself (the same object ``route.reflow`` holds as
        # ``closure_request`` and later re-reads for the preflight) in place, simulating the
        # real witness having been substituted out from under an already-computed
        # Evaluation. The returned Evaluation is the real one, untouched -- it already
        # passed G19 honestly; only what the preflight re-reads has since changed.
        evaluation = real_evaluate_closure(request)
        request["kernel_source_witness"] = dict(request["kernel_source_witness"])
        request["kernel_source_witness"]["blob_object"] = (
            b"tampered" + bytes.fromhex(request["kernel_source_witness"]["blob_object"])[8:]
        ).hex()
        return evaluation

    route_module.evaluate_closure = tampering_evaluate_closure  # type: ignore[attr-defined]
    try:
        with pytest.raises(StaleReflowError, match="atomic preflight"):
            reflow(
                store,
                project_id=project_state["project_id"],
                closure_request=closure_request,
                previous_event_id=difference["genesis_event_ref"]["id"],
                event_revision=1,
                observation_refs=[],
                reflow_instant=REFLOW_INSTANT,
            )
    finally:
        route_module.evaluate_closure = real_evaluate_closure  # type: ignore[attr-defined]


# --- R6-F4: the verified Git provenance witness (not only the {commit_sha, tree_sha}     #
# --- claim) is persisted as its own immutable kernel_source_witness record, resolvable   #
# --- after a process restart, not left as an ephemeral request field                     #


def test_r6f4_a_real_closed_reflow_persists_a_resolvable_kernel_source_witness(
    tmp_path: Path,
) -> None:
    """The positive control this Round 6 finding demanded: after a real, committed CLOSED
    Reflow cycle, the Closure Evaluation's own ``kernel_source_witness_ref`` resolves a real
    ``kernel_source_witness`` record from a *fresh* ``FileStateStore`` instance pointed at
    the same backend directory -- a restart-equivalent lookup -- carrying the same verified
    COMMIT/TREE/BLOB object bytes ``closure_request`` supplied, proving G19's proof survives
    a process restart rather than existing only as an ephemeral request field."""

    _store, project_state, _difference, result = _closed_store(tmp_path)
    evaluation = result["evaluation"]

    witness_ref = evaluation["kernel_source_witness_ref"]
    assert witness_ref is not None
    assert witness_ref["kind"] == "kernel_source_witness"

    fresh_store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    resolved = fresh_store.resolve_record(
        project_state["project_id"], witness_ref["kind"], witness_ref["id"]
    )
    assert resolved is not None
    assert resolved["kernel_source_witness_id"] == witness_ref["id"]
    assert resolved["commit_sha"] == evaluation["kernel_source_ref_evaluated"]["commit_sha"]
    assert resolved["tree_sha"] == evaluation["kernel_source_ref_evaluated"]["tree_sha"]


def test_r6f4_a_tampered_witness_never_reaches_the_store(tmp_path: Path) -> None:
    """When the caller-supplied witness does not verify, ``evaluate_closure`` already
    leaves ``kernel_source_witness_ref`` ``None`` (G19 fails closed on the same tampering) --
    proving Reflow never persists a ``kernel_source_witness`` record from an unverified
    request field, only from a reference the evaluation itself established.

    R9-F2 (SHUKOU Round 9) sharpens what happens one layer up, through ``reflow.route.
    reflow``: ``kernel_source_witness`` is the one real Git witness this vertical ever has
    for the Kernel source (G4's own unconditional floor already requires ``base_kernel_
    source_ref`` and ``kernel_source_ref`` to be the identical commit/tree, so there is no
    second, independently-corruptible witness to distinguish) -- ``_resolve_base_kernel_
    source_ref`` re-verifies that same witness against the canonical State's own committed
    Source Snapshot chain *before* ``evaluate_closure`` ever runs, so a tampered witness now
    fails the whole cycle closed (``ReflowValidationError``, nothing committed) rather than
    only degrading ``evaluate_closure``'s own ``kernel_source_witness_ref`` to ``None`` while
    the cycle still quietly commits a BLOCKED transition.
    """

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    closure_request["kernel_source_witness"] = dict(closure_request["kernel_source_witness"])
    closure_request["kernel_source_witness"]["blob_object"] = "00" * 4
    closure_request["proposed_terminal_status"] = "BLOCKED"
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    closure_request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    closure_request["terminal_reason_evidence_requests"] = [_terminal_request]

    evaluation = evaluate_closure(closure_request)
    assert evaluation["kernel_source_witness_ref"] is None

    with pytest.raises(ReflowValidationError, match="base Kernel provenance"):
        reflow(
            store,
            project_id=project_state["project_id"],
            closure_request=closure_request,
            previous_event_id=difference["genesis_event_ref"]["id"],
            event_revision=1,
            observation_refs=closure_request["reobservation"]["after_observation_refs"],
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
                "verification_request_ref": {
                    "kind": "next_observation_request",
                    "id": "OBS-REQ-" + "6" * 64,
                },
            },
            next_observation_ref={"kind": "next_observation_request", "id": "OBS-REQ-" + "6" * 64},
        )

    # Nothing committed at all -- the Store's own current State is untouched, and the id the
    # *untampered* witness would have produced never reached the Store either.
    assert store.load_current(project_state["project_id"]) == project_state
    untampered_request = candidate_closure_request(difference, policy, current_state=current_state)
    untampered_id = build_kernel_source_witness_record(
        commit_sha=untampered_request["kernel_source_ref"]["commit_sha"],
        tree_sha=untampered_request["kernel_source_ref"]["tree_sha"],
        blob_sha=KERNEL_INVARIANTS_BLOB_SHA,
        path=KERNEL_INVARIANTS_PATH,
        witness=untampered_request["kernel_source_witness"],
    )["kernel_source_witness_id"]
    assert (
        store.resolve_record(project_state["project_id"], "kernel_source_witness", untampered_id) is None
    )


# --- R6-F3: Invariant Evaluation records bind to the real proposed Candidate, not only   #
# --- the base State they were evaluated from                                             #


def test_r6f3_real_invariant_evaluations_bind_to_the_real_candidate(tmp_path: Path) -> None:
    """The positive control this Round 6 finding demanded: after a real, committed CLOSED
    Reflow cycle, every resolved ``invariant_evaluation`` record's own ``candidate_id``/
    ``candidate_semantic_fingerprint`` equals the Closure Evaluation's own real
    ``after_state_candidate`` -- not merely schema-shaped, the exact same Candidate this
    cycle actually closed against."""

    store, project_state, _difference, result = _closed_store(tmp_path)
    evaluation = result["evaluation"]
    after_state_candidate = evaluation["after_state_candidate"]
    assert after_state_candidate is not None

    invariant_bindings = evaluation["candidate_invariant_evaluation_bindings"]
    assert len(invariant_bindings) == 47
    for binding in invariant_bindings:
        ref = binding["invariant_evaluation_ref"]
        resolved = store.resolve_record(project_state["project_id"], ref["kind"], ref["id"])
        assert resolved is not None
        assert resolved["candidate_id"] == after_state_candidate["candidate_id"]
        assert resolved["candidate_semantic_fingerprint"] == after_state_candidate["semantic_fingerprint"]


def test_r6f3_tampered_invariant_evaluation_candidate_id_fails_g19(tmp_path: Path) -> None:
    """A caller-supplied ``invariant_evaluation`` record whose ``candidate_id`` names a
    different Candidate than the one this Evaluation is actually for no longer resolves --
    G19 fails, even though ``state_revision``/``state_fingerprint`` (the base State) still
    match exactly. Before R6-F3 this record would have resolved and passed regardless."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    closure_request["invariant_evaluations"] = [
        dict(closure_request["invariant_evaluations"][0]),
        *closure_request["invariant_evaluations"][1:],
    ]
    closure_request["invariant_evaluations"][0]["candidate_id"] = "STATE-CANDIDATE-" + "9" * 64
    closure_request["proposed_terminal_status"] = "BLOCKED"
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    closure_request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    closure_request["terminal_reason_evidence_requests"] = [_terminal_request]

    evaluation = evaluate_closure(closure_request)
    assert evaluation["result"] != "SATISFIED"


def test_r6f3_preflight_reresolution_catches_a_post_evaluation_candidate_mismatch(
    tmp_path: Path,
) -> None:
    """The atomic preflight also re-verifies each admitted Invariant Evaluation's own
    ``candidate_id``/``candidate_semantic_fingerprint`` against the real Candidate, not only
    its reference chain -- a Closure Evaluation claiming G19 passed against a pool the real
    ``closure_request`` no longer carries an intact candidate binding for is refused at
    commit time too."""

    import manosube_agent_civilization.reflow.route as route_module

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    real_evaluate_closure = route_module.evaluate_closure  # type: ignore[attr-defined]

    def tampering_evaluate_closure(request: dict[str, Any]) -> dict[str, Any]:
        evaluation = real_evaluate_closure(request)
        request["invariant_evaluations"] = [
            dict(request["invariant_evaluations"][0]),
            *request["invariant_evaluations"][1:],
        ]
        request["invariant_evaluations"][0]["candidate_id"] = "STATE-CANDIDATE-" + "9" * 64
        return evaluation

    route_module.evaluate_closure = tampering_evaluate_closure  # type: ignore[attr-defined]
    try:
        with pytest.raises(StaleReflowError, match="atomic preflight"):
            reflow(
                store,
                project_id=project_state["project_id"],
                closure_request=closure_request,
                previous_event_id=difference["genesis_event_ref"]["id"],
                event_revision=1,
                observation_refs=[],
                reflow_instant=REFLOW_INSTANT,
            )
    finally:
        route_module.evaluate_closure = real_evaluate_closure  # type: ignore[attr-defined]

    assert store.load_current(project_state["project_id"])["state_revision"] == project_state["state_revision"]


# --- R6-F1a: source_snapshot_refs resolve to a real, content-addressed source_snapshot   #
# --- body (Observation-owned), not only an ID-only cross-reference                       #


def test_r6f1a_a_real_closed_reflow_persists_a_resolvable_source_snapshot(tmp_path: Path) -> None:
    """The positive control this Round 6 finding demanded: after a real, committed CLOSED
    Reflow cycle, every declared ``source_snapshot_refs`` entry resolves a real
    ``source_snapshot`` record from a *fresh* ``FileStateStore`` instance pointed at the
    same backend directory -- a restart-equivalent lookup -- not merely an opaque {kind, id}
    pair no schema anywhere ever backed."""

    _store, project_state, _difference, result = _closed_store(tmp_path)
    evaluation = result["evaluation"]
    snapshot_refs = evaluation["after_state_candidate"]["source_snapshot_refs"]["members"]
    assert len(snapshot_refs) == 1

    fresh_store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    resolved = fresh_store.resolve_record(
        project_state["project_id"], snapshot_refs[0]["kind"], snapshot_refs[0]["id"]
    )
    assert resolved is not None
    assert resolved["source_snapshot_id"] == snapshot_refs[0]["id"]


def test_r6f1a_a_tampered_source_snapshot_fails_g8_closed(tmp_path: Path) -> None:
    """A caller-supplied ``source_snapshot`` record whose content no longer produces the id
    it is filed under no longer resolves -- G8 fails, even though the declared
    ``source_snapshot_refs`` id-string still exactly matches the real Observation's own
    reported set. Before R6-F1a, ID-only cross-reference would have accepted this."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    closure_request["source_snapshots"] = [dict(closure_request["source_snapshots"][0])]
    closure_request["source_snapshots"][0]["content_digest"] = "sha256:" + "0" * 64
    closure_request["proposed_terminal_status"] = "BLOCKED"
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    closure_request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    closure_request["terminal_reason_evidence_requests"] = [_terminal_request]

    evaluation = evaluate_closure(closure_request)
    assert evaluation["result"] != "SATISFIED"


def test_r6f1a_preflight_reresolution_catches_a_post_evaluation_snapshot_mismatch(
    tmp_path: Path,
) -> None:
    """The atomic preflight also re-verifies every declared source_snapshot_refs entry
    against the real content-addressed pool, not only at evaluation time -- a Closure
    Evaluation claiming G8 passed against a pool the real closure_request no longer carries
    an intact snapshot body for is refused at commit time too."""

    import manosube_agent_civilization.reflow.route as route_module

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    real_evaluate_closure = route_module.evaluate_closure  # type: ignore[attr-defined]

    def tampering_evaluate_closure(request: dict[str, Any]) -> dict[str, Any]:
        evaluation = real_evaluate_closure(request)
        request["source_snapshots"] = [dict(request["source_snapshots"][0])]
        request["source_snapshots"][0]["content_digest"] = "sha256:" + "0" * 64
        return evaluation

    route_module.evaluate_closure = tampering_evaluate_closure  # type: ignore[attr-defined]
    try:
        with pytest.raises(StaleReflowError, match="atomic preflight"):
            reflow(
                store,
                project_id=project_state["project_id"],
                closure_request=closure_request,
                previous_event_id=difference["genesis_event_ref"]["id"],
                event_revision=1,
                observation_refs=[],
                reflow_instant=REFLOW_INSTANT,
            )
    finally:
        route_module.evaluate_closure = real_evaluate_closure  # type: ignore[attr-defined]

    assert store.load_current(project_state["project_id"])["state_revision"] == project_state["state_revision"]


# --- R6-F1b: change_free_verification_evidence_refs resolve to a real Evidence record   #
# --- (Evidence's own new CHANGE_FREE_VERIFICATION_EVIDENCE position), not only a bare   #
# --- reference nothing backs                                                            #


def test_r6f1b_a_real_closed_reflow_persists_a_resolvable_change_free_verification_evidence(
    tmp_path: Path,
) -> None:
    """The positive control this Round 6 finding demanded: after a real, committed CLOSED
    Reflow cycle, the declared ``change_free_verification_evidence_refs`` entry resolves a
    real Evidence record -- Evidence's own new ``CHANGE_FREE_VERIFICATION_EVIDENCE``
    position -- from a *fresh* ``FileStateStore`` instance, not merely an opaque
    ``{kind, id}`` pair no schema anywhere ever backed."""

    _store, project_state, _difference, result = _closed_store(tmp_path)
    evaluation = result["evaluation"]
    refs = evaluation["change_free_verification_evidence_refs"]
    assert len(refs) == 1

    fresh_store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    resolved = fresh_store.resolve_record(project_state["project_id"], refs[0]["kind"], refs[0]["id"])
    assert resolved is not None
    assert resolved["evidence_position"] == "CHANGE_FREE_VERIFICATION_EVIDENCE"
    assert resolved["after_state"] is not None
    assert resolved["change_identity"] is None


def test_r6f1b_an_unreproducible_change_free_verification_evidence_fails_g8_closed(
    tmp_path: Path,
) -> None:
    """A declared ``change_free_verification_evidence_refs`` entry with no real request to
    reproduce it from no longer resolves -- G8 fails. Before R6-F1b, a bare reference
    string was never resolved against anything and this would not have been caught."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    closure_request["change_free_verification_evidence_requests"] = []
    closure_request["proposed_terminal_status"] = "BLOCKED"
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    closure_request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    closure_request["terminal_reason_evidence_requests"] = [_terminal_request]

    evaluation = evaluate_closure(closure_request)
    assert evaluation["result"] != "SATISFIED"


# --- R6-F2: candidate identity for Claim bindings lives inside the shared resolver       #
# --- resolve_claim_binding itself now, so G21 and the atomic preflight can never again   #
# --- silently diverge on it the way they did for Invariant Evaluation bindings (R6-F3)   #


def test_r6f2_preflight_reresolution_catches_a_post_evaluation_claim_candidate_mismatch(
    tmp_path: Path,
) -> None:
    """The exact real defect this Round 6 finding named: before this fix, the atomic
    preflight called ``resolve_claim_binding``/``resolve_completion_record`` for every
    admitted Claim binding, but the candidate_id/candidate_semantic_fingerprint check R5-F1
    added lived only inline in ``_evaluate_g21``'s loop body -- never inherited by the
    preflight, exactly the same way R6-F3 found for Invariant Evaluation bindings.
    Reproduced with a working exploit: a Closure Evaluation whose own Claim binding is
    tampered to name a foreign Candidate (with a correctly recomputed ``binding_id`` so
    nothing else catches it) after ``evaluate_closure`` already returned SATISFIED/CLOSED --
    before this fix, ``reflow()`` promoted it anyway."""

    import manosube_agent_civilization.reflow.route as route_module

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    real_evaluate_closure = route_module.evaluate_closure  # type: ignore[attr-defined]

    def tampering_evaluate_closure(request: dict[str, Any]) -> dict[str, Any]:
        # Compute the real, correctly-SATISFIED Evaluation first, then return a tampered
        # *copy* of it -- the Evaluation reflow() itself holds and later re-derives the
        # preflight's own bindings from, exactly like the R5-F4/R6-F3 exploits above.
        evaluation = real_evaluate_closure(request)
        tampered = dict(evaluation)
        bindings = [dict(binding) for binding in tampered["candidate_claim_evaluation_bindings"]]
        bindings[0]["candidate_id"] = "STATE-CANDIDATE-" + "9" * 64
        bindings[0]["binding_id"] = candidate_claim_evaluation_binding_id(bindings[0])
        tampered["candidate_claim_evaluation_bindings"] = bindings
        return tampered

    route_module.evaluate_closure = tampering_evaluate_closure  # type: ignore[attr-defined]
    try:
        with pytest.raises(StaleReflowError, match="atomic preflight"):
            reflow(
                store,
                project_id=project_state["project_id"],
                closure_request=closure_request,
                previous_event_id=difference["genesis_event_ref"]["id"],
                event_revision=1,
                observation_refs=[],
                reflow_instant=REFLOW_INSTANT,
            )
    finally:
        route_module.evaluate_closure = real_evaluate_closure  # type: ignore[attr-defined]

    assert store.load_current(project_state["project_id"])["state_revision"] == project_state["state_revision"]


# --- R6-F2: Evidence (change_result_evidence_refs / change_free_verification_evidence_refs) #
# --- is re-reproduced by the atomic preflight too, not only at evaluation time            #


def test_r6f2_preflight_reresolution_catches_an_emptied_change_free_verification_evidence(
    tmp_path: Path,
) -> None:
    """The atomic preflight re-reproduces ``change_free_verification_evidence_requests`` and
    checks the result against ``change_free_verification_evidence_refs`` by full set
    equality -- an emptied requests list against a still-declared refs list is refused, not
    silently skipped (a one-directional membership check would miss exactly this)."""

    import manosube_agent_civilization.reflow.route as route_module

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    real_evaluate_closure = route_module.evaluate_closure  # type: ignore[attr-defined]

    def tampering_evaluate_closure(request: dict[str, Any]) -> dict[str, Any]:
        evaluation = real_evaluate_closure(request)
        request["change_free_verification_evidence_requests"] = []
        return evaluation

    route_module.evaluate_closure = tampering_evaluate_closure  # type: ignore[attr-defined]
    try:
        with pytest.raises(StaleReflowError, match="atomic preflight"):
            reflow(
                store,
                project_id=project_state["project_id"],
                closure_request=closure_request,
                previous_event_id=difference["genesis_event_ref"]["id"],
                event_revision=1,
                observation_refs=[],
                reflow_instant=REFLOW_INSTANT,
            )
    finally:
        route_module.evaluate_closure = real_evaluate_closure  # type: ignore[attr-defined]

    assert store.load_current(project_state["project_id"])["state_revision"] == project_state["state_revision"]


# --- R7-F1: Invariant Evaluation status is independently derived, never a caller assertion --- #


def test_r7f1_verify_invariant_independently_derives_the_real_verdict() -> None:
    """The dispatch this module's fix relies on returns a real, non-fabricated verdict from
    *context* alone -- never a caller's own restated status. Tampering one real fact
    (``proposed_terminal_status`` set to a fourth, lifecycle-illegal value -- R-005's own
    real ``FAILED_AND_BLOCKED_RESULTS_REFLOWED`` check, R8-F1) flips only that one
    invariant's own verdict, proving the check is not vacuous."""

    from manosube_agent_civilization.difference.invariant_verifiers import (
        build_invariant_verification_context,
        verify_invariant,
    )

    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {"revision": 5, "fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "1" * 64}}
    context = build_invariant_verification_context(
        policy=policy,
        difference=difference,
        current_state=current_state,
        after_state_candidate={"base_state_ref": {"kind": "state", **current_state}},
        resolution_mode="CHANGE_FREE",
        change_result_evidence=[],
        change_free_evidence=[],
        after_observation_ids=set(),
        source_snapshot_refs=[],
        source_snapshots=[],
        sufficiency=None,
        material_contradictions=[],
        blocking_contradictions=[],
        proposed_terminal_status="CLOSED",
        evaluated_at=REFLOW_INSTANT,
        request_contract_keys=frozenset(),
    )
    status, evidence_refs = verify_invariant("R-005", context)
    assert status == "PASS"
    assert evidence_refs == []

    tampered_context = dict(context)
    tampered_context["proposed_terminal_status"] = "UNKNOWN"
    tampered_status, tampered_refs = verify_invariant("R-005", tampered_context)
    assert tampered_status == "FAIL"
    assert tampered_refs == []

    # An invariant id no verifier is implemented for fails closed too (the disposition's own
    # explicit escape valve), never fabricates a PASS by simple absence.
    unimplemented_status, unimplemented_refs = verify_invariant("Z-999", context)
    assert unimplemented_status == "FAIL"
    assert unimplemented_refs == []


def test_r7f1_a_caller_declared_pass_that_disagrees_with_the_real_verifier_fails_g19(
    tmp_path: Path,
) -> None:
    """R7-F1's own exploit: before this fix, a caller-supplied Invariant Evaluation record
    declaring ``status=PASS`` (with a correctly recomputed fingerprint, candidate binding and
    State binding) was accepted regardless of whether anything real backed that status. Here
    a real, well-formed golden request is built first (so every Invariant Evaluation record
    genuinely PASSed against its own real construction-time context, R8-F1), then
    ``evidence_sufficiency_request`` is withdrawn -- the one input E-001's real check
    (``EVIDENCE_SUFFICIENCY_RESULT_BOUND``) actually reads at G19-recompute time. The frozen
    E-001 record, built earlier against the real Sufficiency that no longer exists, still
    declares its original ``PASS``/``observed`` untouched. G19 must now fail on that
    disagreement; before this fix it would have passed on the caller's bare say-so."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    # G19 is now expected to fail (real_observed disagrees with the frozen record), so this
    # Evaluation can no longer honestly propose CLOSED -- a real caller preparing for either
    # outcome supplies real terminal reason Evidence too.
    closure_request["evidence_sufficiency_request"] = None
    closure_request["proposed_terminal_status"] = "BLOCKED"
    _terminal_request, _terminal_evidence_id = real_terminal_reason_evidence_fields()
    closure_request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": _terminal_evidence_id}
    ]
    closure_request["terminal_reason_evidence_requests"] = [_terminal_request]

    evaluation = evaluate_closure(closure_request)
    assert evaluation["gate_results"]["G19"] == "FAIL"
    assert evaluation["result"] != "SATISFIED"


def test_r7f1_the_real_v01_mandatory_union_independently_verifies_for_a_genuine_candidate(
    tmp_path: Path,
) -> None:
    """The positive control: for a real, well-formed natural-cycle Candidate, every one of
    the 47 v0.1 mandatory Invariant Evaluations independently re-verifies as PASS -- R7-F1's
    fix does not merely reject forged records, it also does not fail closed on the honest
    case (CLOSED must remain reachable)."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)

    evaluation = evaluate_closure(closure_request)
    assert evaluation["gate_results"]["G19"] == "PASS"
    assert evaluation["result"] == "SATISFIED"


# --- R7-F2: change-free verification Evidence must prove the same Target -------------------- #


def test_r7f2_change_free_verification_evidence_for_a_foreign_target_is_refused() -> None:
    """A ``verification_observation_request`` that observes a *different* Target than the
    base Observation this Evidence is otherwise about no longer derives -- before this fix
    the only independence check was "not literally the same Observation", which a foreign
    Target's own distinct Observation trivially satisfied."""

    from tests.difference_helpers import (
        observation_request,
        observation_scope,
        raw_fact,
        state_fingerprint,
    )
    from tests.evidence_helpers import (
        BEFORE_REVISION,
        before_observation_request,
        difference_request,
    )

    from manosube_agent_civilization.evidence.engine import derive_evidence
    from manosube_agent_civilization.evidence.errors import EvidenceError

    foreign_verification_request = observation_request(
        observation_scope(target_identity="FOREIGN-TARGET-0002"),
        [raw_fact(value="NOT-READY")],
        state_fingerprint(),
        BEFORE_REVISION,
    )
    request = {
        "schema_version": "0.1",
        "recorded_at": "2026-08-30T09:00:00Z",
        "observation_request": before_observation_request(),
        "difference_request": difference_request(),
        "change_request": None,
        "post_change_observation_request": None,
        "verification_observation_request": foreign_verification_request,
        "artifact_references": [],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }

    with pytest.raises(EvidenceError, match="does not match"):
        derive_evidence(request)


def test_r7f2_a_genuine_change_free_verification_evidence_still_derives() -> None:
    """The positive control: a verification Observation of the *same* Target as the base
    Observation still derives a real ``CHANGE_FREE_VERIFICATION_EVIDENCE`` record."""

    from tests.evidence_helpers import change_free_verification_evidence_request

    from manosube_agent_civilization.evidence.engine import (
        CHANGE_FREE_VERIFICATION_EVIDENCE,
        derive_evidence,
    )

    record = derive_evidence(change_free_verification_evidence_request())
    assert record["evidence_position"] == CHANGE_FREE_VERIFICATION_EVIDENCE


# --- R7-F3: G3/G4 objective and kernel-source bindings are actually evaluated --------------- #


def test_r7f3_g3_fails_when_the_current_states_objective_revision_id_disagrees() -> None:
    """A committed State whose own ``objective_revision_id`` no longer names the Objective
    this Difference was derived against fails G3 closed -- before this fix G3 unconditionally
    passed regardless of what either side actually named."""

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = base_closure_request(difference, policy)
    request["objective_revision_id"] = "OBJ-REV-FOREIGN-0002"

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G3"] == "FAIL"
    assert evaluation["result"] == "BLOCKED"


def test_r7f3_g4_fails_when_base_kernel_source_ref_disagrees_with_kernel_source_ref() -> None:
    """Phase 7 does not permit a Kernel source change mid-cycle: a ``base_kernel_source_ref``
    naming a different commit/tree than ``kernel_source_ref`` fails G4 closed -- before this
    fix G4 unconditionally passed regardless of whether the two agreed."""

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = base_closure_request(difference, policy)
    request["base_kernel_source_ref"] = {**request["base_kernel_source_ref"], "commit_sha": "f" * 40}

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G4"] == "FAIL"
    assert evaluation["result"] == "BLOCKED"


def test_r7f3_g3_and_g4_both_pass_for_the_real_fixture_candidate(tmp_path: Path) -> None:
    """The positive control: the real fixture's committed State objective binding and the
    unchanged Kernel source both verify."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)

    evaluation = evaluate_closure(closure_request)
    assert evaluation["gate_results"]["G3"] == "PASS"
    assert evaluation["gate_results"]["G4"] == "PASS"


# --- R8-F2: G3/G4 bind to the real Objective Revision body and a verified Kernel source ----- #


def test_r8f2_g3_fails_when_the_real_objective_revision_body_disagrees(tmp_path: Path) -> None:
    """R8-F2's own exploit: before this fix, G3 compared only the top-level
    ``objective_revision_id`` strings -- the real Objective Revision body actually present at
    ``reobservation.derivation_request.objective_revision`` (SHUKOU Round 8's explicit
    correction to Round 7's own disclosed non-claim that no such body exists at this layer)
    was never independently validated or fingerprinted. Here that real body's own content is
    tampered (a different ``statement``, same ``objective_revision_id`` as the untouched
    Difference's own ``objective_revision_ref``) -- the bare id-equality above would still
    agree, so before this fix G3 would have passed on the caller's restated id alone. The
    real, independently recomputed semantic fingerprint now disagrees and G3 must fail."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)

    tampered_objective = objective_revision(statement="A materially different objective statement.")
    assert (
        tampered_objective["objective_revision_id"]
        == closure_request["reobservation"]["derivation_request"]["objective_revision"]["objective_revision_id"]
    )
    closure_request = deepcopy(closure_request)
    closure_request["reobservation"]["derivation_request"]["objective_revision"] = tampered_objective
    closure_request["proposed_terminal_status"] = "BLOCKED"
    terminal_request, terminal_evidence_id = real_terminal_reason_evidence_fields()
    closure_request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": terminal_evidence_id}
    ]
    closure_request["terminal_reason_evidence_requests"] = [terminal_request]

    evaluation = evaluate_closure(closure_request)
    assert evaluation["gate_results"]["G3"] == "FAIL"
    assert evaluation["result"] != "SATISFIED"


def test_r8f2_g3_fails_when_the_objective_revision_body_is_entirely_absent(tmp_path: Path) -> None:
    """A candidate evaluation whose reobservation carries no ``objective_revision`` body at
    all (a malformed or stripped derivation request) has nothing for G3 to independently
    validate and fails closed rather than falling back to the bare id-equality alone."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    closure_request = deepcopy(closure_request)
    del closure_request["reobservation"]["derivation_request"]["objective_revision"]
    closure_request["proposed_terminal_status"] = "BLOCKED"
    terminal_request, terminal_evidence_id = real_terminal_reason_evidence_fields()
    closure_request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": terminal_evidence_id}
    ]
    closure_request["terminal_reason_evidence_requests"] = [terminal_request]

    evaluation = evaluate_closure(closure_request)
    assert evaluation["gate_results"]["G3"] == "FAIL"
    assert evaluation["result"] != "SATISFIED"


def test_r8f2_g4_fails_when_the_kernel_source_witness_does_not_verify(tmp_path: Path) -> None:
    """R8-F2's other own exploit: before this fix, G4 accepted any two matching
    ``base_kernel_source_ref``/``kernel_source_ref`` strings regardless of whether either was
    ever independently proven to be a genuine Git object -- ``kernel_source_witness`` was
    verified elsewhere (feeding only the Closure Evaluation's own output reference) but its
    result never fed G4's own PASS/FAIL decision. Here the witness bytes are corrupted while
    ``base_kernel_source_ref``/``kernel_source_ref`` still agree with each other exactly --
    before this fix G4 would still have passed on that bare agreement alone."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    closure_request = deepcopy(closure_request)
    closure_request["kernel_source_witness"]["blob_object"] = "00" * 4
    closure_request["proposed_terminal_status"] = "BLOCKED"
    terminal_request, terminal_evidence_id = real_terminal_reason_evidence_fields()
    closure_request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": terminal_evidence_id}
    ]
    closure_request["terminal_reason_evidence_requests"] = [terminal_request]

    evaluation = evaluate_closure(closure_request)
    assert evaluation["gate_results"]["G4"] == "FAIL"
    assert evaluation["result"] != "SATISFIED"


def test_r8f2_g3_and_g4_still_pass_for_the_real_fixture_candidate_after_the_deeper_checks(
    tmp_path: Path,
) -> None:
    """The positive control: the real fixture's Objective Revision body independently
    validates and recomputes to match, and its Kernel source witness genuinely verifies --
    CLOSED remains reachable through the deeper R8-F2 checks, not only the bare floors."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)

    evaluation = evaluate_closure(closure_request)
    assert evaluation["gate_results"]["G3"] == "PASS"
    assert evaluation["gate_results"]["G4"] == "PASS"
    assert evaluation["result"] == "SATISFIED"


# --- R7-F4: terminal reason Evidence resolves to a real, reproducible record ---------------- #


def test_r7f4_a_bare_terminal_reason_evidence_ref_with_no_backing_request_fails_closed() -> None:
    """A ``terminal_reason_evidence_refs`` entry with no matching
    ``terminal_reason_evidence_requests`` entry to reproduce it from -- the same "reference
    without substance" R6-F1b already refused elsewhere -- is refused, not silently
    accepted."""

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = base_closure_request(difference, policy)
    request["terminal_reason_evidence_requests"] = []

    with pytest.raises(ReflowValidationError, match="terminal_reason_evidence_requests"):
        evaluate_closure(request)


def test_r7f4_a_real_blocked_reflow_persists_a_resolvable_terminal_reason_evidence(
    tmp_path: Path,
) -> None:
    """The positive control: after a real, committed BLOCKED Reflow cycle, every declared
    ``terminal_reason_evidence_refs`` entry resolves a real ``observation_evidence`` record
    from a *fresh* ``FileStateStore`` instance -- proving the reference survives a process
    restart rather than staying permanently opaque."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    closure_request = base_closure_request(difference, policy)

    result = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
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
    assert result["decision"]["to_status"] == "BLOCKED"
    refs = result["evaluation"]["terminal_reason_evidence_refs"]
    assert refs

    fresh_store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    for ref in refs:
        resolved = fresh_store.resolve_record(project_state["project_id"], ref["kind"], ref["id"])
        assert resolved is not None
        assert resolved["evidence_id"] == ref["id"]


def test_r7f4_preflight_reresolution_catches_an_emptied_terminal_reason_evidence_requests(
    tmp_path: Path,
) -> None:
    """The atomic preflight also re-reproduces ``terminal_reason_evidence_requests``
    immediately before commit, for *every* outcome (not only ``CLOSED``) -- a
    post-evaluation tamper that empties the requests while the Evaluation's own declared
    refs stay non-empty is refused, not silently promoted."""

    import manosube_agent_civilization.reflow.route as route_module

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    closure_request = base_closure_request(difference, policy)
    real_evaluate_closure = route_module.evaluate_closure  # type: ignore[attr-defined]

    def tampering_evaluate_closure(request: dict[str, Any]) -> dict[str, Any]:
        evaluation = real_evaluate_closure(request)
        request["terminal_reason_evidence_requests"] = []
        return evaluation

    route_module.evaluate_closure = tampering_evaluate_closure  # type: ignore[attr-defined]
    try:
        with pytest.raises(StaleReflowError, match="atomic preflight"):
            reflow(
                store,
                project_id=project_state["project_id"],
                closure_request=closure_request,
                previous_event_id=difference["genesis_event_ref"]["id"],
                event_revision=1,
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
    finally:
        route_module.evaluate_closure = real_evaluate_closure  # type: ignore[attr-defined]

    assert store.load_current(project_state["project_id"])["state_revision"] == project_state["state_revision"]


# --- R8-F3: terminal reason Evidence binds to the real Difference/project ------------------- #


def test_r8f3_a_legitimate_evidence_for_a_different_difference_is_refused() -> None:
    """R8-F3's own exploit: before this fix, only Evidence ID regeneration and
    reference-set equality were checked -- a real, correctly-reproducing, self-consistent
    Evidence record about a *different* Difference satisfied both just as well as one about
    the right Difference. Here a genuine second Difference (a real re-observation of the same
    Target with a different observed fact) grounds a real Evidence record, substituted whole
    as this request's terminal reason -- it reproduces perfectly and would have passed the
    old check. The real, independently-derived ``difference_ref`` on that Evidence names the
    *other* Difference, not this one, and must now be refused."""

    from tests.difference_helpers import (
        observation_request,
        observation_scope,
        raw_fact,
        state_fingerprint,
    )
    from tests.evidence_helpers import (
        BEFORE_REVISION,
        difference_request,
        observation_evidence_request,
    )

    from manosube_agent_civilization.evidence.engine import derive_evidence

    foreign_observation = observation_request(
        observation_scope(), [raw_fact(value="STILL-NOT-READY")], state_fingerprint(), BEFORE_REVISION
    )
    foreign_request = observation_evidence_request(observation=foreign_observation, difference=difference_request())
    foreign_evidence = derive_evidence(foreign_request)

    difference = fixture_difference()
    policy = fixture_policy(difference)
    assert foreign_evidence["difference_ref"]["id"] != difference["difference_id"]
    request = base_closure_request(difference, policy)
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": foreign_evidence["evidence_id"]}
    ]
    request["terminal_reason_evidence_requests"] = [foreign_request]

    with pytest.raises(ReflowValidationError, match="different Difference"):
        evaluate_closure(request)


def test_r8f3_a_real_blocked_reflow_still_persists_the_matching_terminal_reason_evidence(
    tmp_path: Path,
) -> None:
    """The positive control: the fixture's own real, matching terminal reason Evidence still
    resolves and commits through a real Reflow cycle after the deeper R8-F3 binding checks
    (unchanged from R7-F4's own positive control, run again against the tightened resolver)."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    closure_request = base_closure_request(difference, policy)

    result = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
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
    assert result["decision"]["to_status"] == "BLOCKED"
    refs = result["evaluation"]["terminal_reason_evidence_refs"]
    assert refs

    fresh_store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    for ref in refs:
        resolved = fresh_store.resolve_record(project_state["project_id"], ref["kind"], ref["id"])
        assert resolved is not None
        assert resolved["difference_ref"]["id"] == difference["difference_id"]


# --- R7-F5: resolve_transaction only publishes COMMITTED transactions ---------------------- #


@pytest.mark.parametrize("stage", list(STAGES))
def test_r7f5_resolve_transaction_is_invisible_before_recovery_and_converges_after(
    stage: str, tmp_path: Path
) -> None:
    """Before this fix, ``resolve_transaction`` published any event that had merely reached
    the append-only lineage log -- real for every stage from ``AFTER_LINEAGE_APPEND``
    onward, since ``commit``'s own sequence appends to the lineage *before* it promotes that
    transaction's records or writes its recovery journal's ``COMMITTED`` marker. For every
    one of the 9 crash stages, the ``COMMITTED`` marker is the very last thing ``commit``
    writes -- so a crash at any of them leaves it durably absent, and ``resolve_transaction``
    must report the transaction as not-yet-visible until :meth:`recover` actually completes
    it (or the transaction turns out to have been abandoned, for a crash before
    ``AFTER_COMMIT_INTENT``)."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    evaluation = evaluate_closure(closure_request)

    from manosube_agent_civilization.reflow.identity import (
        closure_evaluation_decision_fingerprint,
        transaction_id,
    )

    tx = transaction_id(
        project_id=project_state["project_id"],
        difference_id=difference["difference_id"],
        closure_decision_fingerprint=closure_evaluation_decision_fingerprint(evaluation),
        evidence_sufficiency_id=evaluation["evidence_sufficiency_ref"]["id"],
        expected_revision=project_state["state_revision"],
        reflow_instant=REFLOW_INSTANT,
    )

    def fault(current: str) -> None:
        if current == stage:
            raise SimulatedCrash(stage)

    with pytest.raises(SimulatedCrash):
        commit_reflow(
            store,
            project_id=project_state["project_id"],
            before_project_state=project_state,
            next_semantic_state=evaluation["after_state_candidate"]["semantic_state"],
            transaction_id=tx,
            evidence_refs=closure_request["change_free_verification_evidence_refs"],
            reflow_instant=REFLOW_INSTANT,
            fault=fault,
        )

    # Invisible before recovery, at every crash stage -- COMMITTED is durably absent.
    assert store.resolve_transaction(project_state["project_id"], tx) is None

    store.recover(project_state["project_id"])
    early_stage = stage in STAGES[: STAGES.index("AFTER_COMMIT_INTENT")]
    resolved = store.resolve_transaction(project_state["project_id"], tx)
    if early_stage:
        # Abandoned, not completed -- recovery never promotes a transaction whose own
        # COMMIT_INTENT was never durably written.
        assert resolved is None
    else:
        assert resolved is not None
        assert resolved["transaction_id"] == tx


def test_r7f5_a_genesis_transaction_and_a_fully_committed_one_both_resolve(tmp_path: Path) -> None:
    """The positive control: a transaction with no recovery journal at all (the one genesis
    transaction) and a real, fully-committed transaction both resolve -- this fix narrows
    visibility to COMMITTED transactions, it does not narrow it further than that."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    assert store.resolve_transaction(project_state["project_id"], "TX-GENESIS") is not None

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
    tx = result["state_transition_ref"]["id"]
    resolved = store.resolve_transaction(project_state["project_id"], tx)
    assert resolved is not None
    assert resolved["transaction_id"] == tx


# --- R7-F6: resolve_source_snapshot enforces the same locator validation as the producer ---- #


def test_r7f6_resolve_source_snapshot_rejects_a_mutable_locator_even_with_a_recomputed_id() -> None:
    """A caller who assembles a ``source_snapshot`` record directly (bypassing
    ``build_source_snapshot``) with a mutable, credential-bearing locator, and correctly
    recomputes its own content-addressed id, no longer resolves -- before this fix schema
    validity and identity recomputation alone were sufficient."""

    from manosube_agent_civilization.observation.errors import ScopeViolationError
    from manosube_agent_civilization.observation.source_snapshot import (
        resolve_source_snapshot,
        source_snapshot_identity,
    )

    forged: dict[str, Any] = {
        "schema_version": "0.1",
        "source_snapshot_id": "",
        "source_locator": "https://mutable.example/branch/main?token=secret",
        "content_digest": "sha256:" + "1" * 64,
        "captured_at": "2026-08-30T09:00:00Z",
        "git_provenance": None,
    }
    forged["source_snapshot_id"] = source_snapshot_identity(forged)
    ref = {"kind": "source_snapshot", "id": forged["source_snapshot_id"]}

    with pytest.raises(ScopeViolationError):
        resolve_source_snapshot(ref, [forged])


def test_r7f6_resolve_source_snapshot_still_accepts_a_genuine_immutable_locator() -> None:
    """The positive control: a real, immutable, non-secret-bearing locator still resolves."""

    from tests.difference_helpers import REAL_SNAPSHOT_RECORD, REAL_SNAPSHOT_REF

    from manosube_agent_civilization.observation.source_snapshot import resolve_source_snapshot

    resolved = resolve_source_snapshot(REAL_SNAPSHOT_REF, [REAL_SNAPSHOT_RECORD])
    assert resolved["source_snapshot_id"] == REAL_SNAPSHOT_REF["id"]


# =========================================================================================== #
# Phase 7 structural-review round 9 (R9-F1/R9-F2/R9-F3)
# =========================================================================================== #

# --- R9-F2: base Kernel provenance resolved from the canonical State's own Source Snapshot -- #


def _fresh_store_missing_kernel_provenance(tmp_path: Path) -> tuple[FileStateStore, dict]:
    """A real Store whose genesis carries no ``state_metadata.source_snapshot_refs`` entry
    naming the Kernel path at all -- the ``MISSING`` half of R9-F2's fail-closed table."""

    from tests.difference_helpers import objective_revision as _objective_revision
    from tests.state_helpers import initial_state

    from manosube_agent_civilization.state.fingerprint import fingerprint_project_state

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = initial_state()
    project_state["state_metadata"]["source_snapshot_refs"] = []
    project_state["objective_revision_id"] = _objective_revision()["objective_revision_id"]
    project_state["semantic_fingerprint"] = fingerprint_project_state(
        project_state, schema_root=SCHEMA_ROOT
    ).as_dict()
    store.initialize(project_state["project_id"], project_state)
    return store, project_state


def test_r9f2_reflow_fails_closed_when_genesis_names_no_kernel_source_snapshot(
    tmp_path: Path,
) -> None:
    """R9-F2: ``GENESIS_KERNEL_PROVENANCE_REQUIRED=true`` -- a genesis State whose own
    ``state_metadata.source_snapshot_refs`` names nothing at the Kernel path fails the very
    first Reflow cycle closed, before ``evaluate_closure`` ever runs, rather than silently
    trusting the caller's own ``base_kernel_source_ref`` claim."""

    store, project_state = _fresh_store_missing_kernel_provenance(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)

    with pytest.raises(ReflowValidationError, match="base Kernel provenance"):
        reflow(
            store,
            project_id=project_state["project_id"],
            previous_event_id=difference["genesis_event_ref"]["id"],
            event_revision=1,
            closure_request=base_closure_request(difference, policy),
            observation_refs=[],
            reflow_instant=REFLOW_INSTANT,
        )
    # Nothing committed at all.
    assert store.load_current(project_state["project_id"]) == project_state


def test_r9f2_reflow_fails_closed_on_kernel_source_snapshot_git_provenance_mismatch(
    tmp_path: Path,
) -> None:
    """R9-F2: a genesis State naming a Kernel Source Snapshot whose own ``git_provenance.
    blob_sha`` disagrees with the pinned ``KERNEL_INVARIANTS_BLOB_SHA`` fails closed -- a
    Kernel-source inconsistency, not merely an absent reference."""

    from tests.difference_helpers import objective_revision as _objective_revision
    from tests.state_helpers import initial_state, real_kernel_git_objects

    from manosube_agent_civilization.observation.source_snapshot import build_source_snapshot
    from manosube_agent_civilization.reflow.invariant_registry import KERNEL_INVARIANTS_PATH
    from manosube_agent_civilization.state.fingerprint import fingerprint_project_state

    # A wholly self-consistent Source Snapshot (its own id genuinely recomputes from its own
    # content) that simply claims the wrong blob for the pinned Kernel path -- the
    # "Kernel-source inconsistency" R9-F2 names, distinct from an unresolvable reference.
    kernel_source_ref, _ = real_kernel_git_objects()
    tampered_snapshot = build_source_snapshot(
        source_locator=KERNEL_INVARIANTS_PATH,
        content_digest="sha256:" + "0" * 64,
        captured_at="2026-08-29T09:00:00Z",
        git_provenance={
            "repository": kernel_source_ref["repository"],
            "commit_sha": kernel_source_ref["commit_sha"],
            "tree_sha": kernel_source_ref["tree_sha"],
            "path": KERNEL_INVARIANTS_PATH,
            "blob_sha": "0" * 40,
        },
    )

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = initial_state()
    project_state["state_metadata"]["source_snapshot_refs"] = [
        {"kind": "source_snapshot", "id": tampered_snapshot["source_snapshot_id"]}
    ]
    project_state["objective_revision_id"] = _objective_revision()["objective_revision_id"]
    project_state["semantic_fingerprint"] = fingerprint_project_state(
        project_state, schema_root=SCHEMA_ROOT
    ).as_dict()
    # R10-F1: the Store must actually adopt the tampered snapshot itself, so this test still
    # reaches its own intended "Kernel-source inconsistency" (blob_sha mismatch) failure --
    # not merely the earlier "unresolvable reference" failure an un-adopted id would now hit.
    store.initialize(
        project_state["project_id"],
        project_state,
        records=[
            ("source_snapshot", tampered_snapshot["source_snapshot_id"], tampered_snapshot)
        ],
    )

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = base_closure_request(difference, policy)
    request["source_snapshots"] = [tampered_snapshot]

    with pytest.raises(ReflowValidationError, match="base Kernel provenance"):
        reflow(
            store,
            project_id=project_state["project_id"],
            previous_event_id=difference["genesis_event_ref"]["id"],
            event_revision=1,
            closure_request=request,
            observation_refs=[],
            reflow_instant=REFLOW_INSTANT,
        )


def test_r9f2_a_real_closed_cycle_resolves_base_kernel_provenance_from_the_store(
    tmp_path: Path,
) -> None:
    """The positive control: a genuine Reflow cycle through a real Store whose genesis
    already names the real Kernel Source Snapshot resolves ``base_kernel_source_ref`` for
    real and reaches CLOSED -- R9-F2 wired all the way through, not merely refusing forgeries."""

    _store, _project_state, _difference, result = _closed_store(tmp_path)
    assert result["decision"]["to_status"] == "CLOSED"
    evaluated = result["evaluation"]["base_kernel_source_ref_evaluated"]
    assert evaluated["commit_sha"] == result["evaluation"]["kernel_source_ref_evaluated"]["commit_sha"]


# --- R9-F1: real per-invariant verification, not a single mechanical local-field proxy ------ #


def _real_g19_context() -> dict[str, Any]:
    """A real, fully-wired G19 verification context -- the same shape ``candidate_closure_
    request`` builds internally, exposed here for direct ``verify_invariant`` calls."""

    from tests.difference_helpers import state_fingerprint
    from tests.reflow_helpers import AFTER_REVISION, EVALUATED_AT, real_kernel_source_witness
    from tests.state_helpers import initial_state

    from manosube_agent_civilization.difference.invariant_verifiers import (
        build_invariant_verification_context,
    )
    from manosube_agent_civilization.reflow.closure import REQUEST_KEYS, build_after_state_candidate
    from manosube_agent_civilization.state.fingerprint import fingerprint_semantic_state

    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {"revision": AFTER_REVISION, "fingerprint": state_fingerprint("KNOWN")}
    kernel_source_ref, _ = real_kernel_source_witness()
    semantic_state = initial_state()["semantic_state"]
    after_state_candidate = build_after_state_candidate(
        current_state=current_state,
        kernel_source_ref=kernel_source_ref,
        semantic_state=semantic_state,
        semantic_fingerprint=fingerprint_semantic_state(semantic_state).as_dict(),
        source_snapshot_refs=[],
        producing_change_refs=[],
    )
    return build_invariant_verification_context(
        policy=policy,
        difference=difference,
        current_state=current_state,
        after_state_candidate=after_state_candidate,
        resolution_mode="CHANGE_FREE",
        change_result_evidence=[],
        change_free_evidence=[],
        after_observation_ids=set(),
        source_snapshot_refs=[],
        source_snapshots=[],
        sufficiency=None,
        material_contradictions=[],
        blocking_contradictions=[],
        proposed_terminal_status="CLOSED",
        evaluated_at=EVALUATED_AT,
        request_contract_keys=REQUEST_KEYS,
    ), after_state_candidate


def test_r9f1_k001_k002_k003_pass_on_the_real_installed_topology() -> None:
    """The positive control: against this vertical's own real, single-owner installed
    package, K-001/K-002/K-003's now-real Static topology check genuinely passes -- proving
    the deepening is not merely a stricter check that never PASSes."""

    from manosube_agent_civilization.difference.invariant_verifiers import verify_invariant

    ctx, _ = _real_g19_context()
    for invariant_id in ("K-001", "K-002", "K-003"):
        status, _ = verify_invariant(invariant_id, ctx)
        assert status == "PASS", invariant_id


def test_r9f1_k001_reports_unknown_when_the_topology_inventory_cannot_be_computed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R9-F1: ``UNPROVEN_INVARIANT_MUST_BE_UNKNOWN=true`` -- when the Static topology
    inventory itself cannot be computed, K-001 reports ``UNKNOWN``, never a silently
    rounded-up ``PASS`` nor a conflated-with-a-real-violation ``FAIL``."""

    from manosube_agent_civilization import topology
    from manosube_agent_civilization.difference import invariant_verifiers
    from manosube_agent_civilization.difference.invariant_verifiers import verify_invariant

    def _raise() -> None:
        raise RuntimeError("simulated introspection failure")

    monkeypatch.setattr(topology, "k001_single_kernel_entry_point", _raise)
    monkeypatch.setattr(invariant_verifiers, "k001_single_kernel_entry_point", _raise)
    ctx, _ = _real_g19_context()
    status, evidence_refs = verify_invariant("K-001", ctx)
    assert status == "UNKNOWN"
    assert evidence_refs == []


def test_r9f1_s002_catches_a_semantic_fingerprint_that_does_not_really_recompute() -> None:
    """R9-F1 deepening: S-002 used to accept any present, shaped-like-a-fingerprint value.
    Now it independently recomputes the Candidate's own semantic fingerprint and requires an
    exact match -- a Candidate whose declared fingerprint does not match its own semantic_
    state content fails closed, which the pre-deepening proxy would have silently passed."""

    from manosube_agent_civilization.difference.invariant_verifiers import verify_invariant

    ctx, after_state_candidate = _real_g19_context()
    tampered_candidate = dict(after_state_candidate)
    tampered_candidate["semantic_fingerprint"] = {
        "profile": "MANOSUBE-STATE-SHA256-0.1",
        "digest": "9" * 64,
    }
    tampered_ctx = dict(ctx)
    tampered_ctx["after_state_candidate"] = tampered_candidate
    status, _ = verify_invariant("S-002", tampered_ctx)
    assert status == "FAIL"
    # The positive control: the real, untampered candidate still passes.
    status, _ = verify_invariant("S-002", ctx)
    assert status == "PASS"


def test_r9f1_a003_fails_when_the_grounding_evidence_postdates_the_evaluation() -> None:
    """R9-F1 deepening: A-003's real freshness check -- the grounding Change-result
    Evidence's own ``timestamp`` may not postdate this Evaluation's own ``evaluated_at``. v0.1
    has no executor to order an authority-grant against an execution-start, but an Evidence
    record recorded *after* the Evaluation that relies on it is a real, checkable
    impossibility this deepening now catches."""

    from tests.evidence_helpers import change_result_evidence_request

    from manosube_agent_civilization.difference.invariant_verifiers import verify_invariant
    from manosube_agent_civilization.evidence.engine import derive_evidence

    ctx, _after_state_candidate = _real_g19_context()
    future_request = change_result_evidence_request(recorded_at="2099-01-01T00:00:00Z")
    future_record = derive_evidence(future_request)
    tampered_ctx = dict(ctx)
    tampered_ctx["resolution_mode"] = "CHANGE_BOUND"
    tampered_ctx["change_result_evidence"] = [future_record]
    status, _ = verify_invariant("A-003", tampered_ctx)
    assert status == "FAIL"


def test_r9f1_a004_no_longer_asserts_authoritys_own_vocabulary() -> None:
    """R9-F1 correction: A-004 must never itself become a second module asserting one of
    Authority's own three decision-value literals -- ``tests/contract/authority/
    test_authority_authority.py``'s own totality sweep is the independent proof; this test
    pins the narrower, direct fact for this module."""

    import ast
    import inspect as _inspect

    from manosube_agent_civilization import authority
    from manosube_agent_civilization.authority import levels
    from manosube_agent_civilization.difference import invariant_verifiers

    source = _inspect.getsource(invariant_verifiers)
    tree = ast.parse(source)
    literal_decisions = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value in levels.DECISIONS
    }
    assert literal_decisions == set()
    assert authority  # imported only to prove the module itself is reachable for this check


# --- R9-F3: typed terminal-cause binding per blocker_kind ------------------------------------ #


def test_r9f3_blocker_kind_must_match_its_own_canonical_condition_code() -> None:
    """R9-F3: ``blocker_kind`` and ``blocker_resolution_condition.condition_code`` used to
    be two independently free fields -- a caller could declare ``OBSERVATION_PATH`` alongside
    ``INVARIANTS_PASS`` and nothing checked the two actually name the same real blocker. The
    canonical pairing table now refuses that combination closed."""

    from manosube_agent_civilization.reflow.lifecycle import mint_transition_event

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = base_closure_request(difference, policy)

    _terminal_request, terminal_evidence_id = real_terminal_reason_evidence_fields()
    evaluation = evaluate_closure(
        {
            **request,
            "terminal_reason_evidence_refs": [
                {"kind": "observation_evidence", "id": terminal_evidence_id}
            ],
            "terminal_reason_evidence_requests": [_terminal_request],
        }
    )
    # mint_transition_event's own last step already calls blocker_payload_errors and refuses
    # to mint a payload it flags -- so a mismatched pairing never reaches a returned event at
    # all, caught here at the earliest possible point.
    with pytest.raises(ReflowValidationError, match="does not match its own canonical condition_code"):
        mint_transition_event(
            difference=difference,
            current_status="VERIFYING",
            previous_event_id=difference["genesis_event_ref"]["id"],
            event_revision=1,
            decision={
                "to_status": "BLOCKED",
                "reason_code": "OBSERVATION_UNAVAILABLE",
                "reason": "",
                "closure_evaluation_ref": None,
            },
            evaluation=evaluation,
            observation_refs=[],
            evidence_refs=[{"kind": "observation_evidence", "id": terminal_evidence_id}],
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
                "condition_code": "INVARIANTS_PASS",
                "subject_ref": {"kind": "difference", "id": difference["difference_id"]},
                "expected_state": "PASS",
                "verification_request_ref": {
                    "kind": "next_observation_request", "id": "OBS-REQ-" + "7" * 64
                },
            },
            next_observation_ref={"kind": "next_observation_request", "id": "OBS-REQ-" + "7" * 64},
        )


def test_r9f3_differing_blocker_kind_never_collides_on_the_same_event_identity() -> None:
    """R9-F3: ``blocker_kind``/``blocker_scope`` are now part of ``difference_event_id``
    itself -- two otherwise-identical events differing only in which terminal cause they
    name can no longer share the same identity (before this fix they always did, since the
    blocker payload sat entirely outside the content address)."""

    from manosube_agent_civilization.difference.identity import lifecycle_event_id

    difference = fixture_difference()
    base_event = {
        "difference_id": difference["difference_id"],
        "event_kind": "TRANSITION",
        "event_revision": 1,
        "previous_event_id": difference["genesis_event_ref"]["id"],
        "from_status": "VERIFYING",
        "to_status": "BLOCKED",
        "state_revision_evaluated": 3,
        "state_fingerprint_evaluated": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "1" * 64},
        "reason_code": "OBSERVATION_UNAVAILABLE",
        "observation_refs": [],
        "evidence_refs": [{"kind": "observation_evidence", "id": "EVID-0001"}],
    }
    subject_ref = {"kind": "difference", "id": difference["difference_id"]}
    scope = {
        "kind": "difference_blocker_scope",
        "affected_subject_refs": {"collection_kind": "UNORDERED_SET", "members": [subject_ref]},
        "effective_boundary": difference["effective_boundary"],
        "blocked_stage": "OBSERVATION",
    }
    observation_event = {**base_event, "blocker_kind": "OBSERVATION_PATH", "blocker_scope": scope}
    evidence_event = {
        **base_event,
        "blocker_kind": "EVIDENCE_INSUFFICIENT",
        "blocker_scope": {**scope, "blocked_stage": "DIFFERENCE_EVALUATION"},
    }
    assert lifecycle_event_id(observation_event) != lifecycle_event_id(evidence_event)


# =========================================================================================== #
# Phase 7 structural-review round 10 (R10-F1)
# =========================================================================================== #

# --- R10-F1: Canonical State references must close to a Store-adopted committed Record ------ #


def _terminal_policy_only_blocker_kwargs(difference: dict[str, Any]) -> dict[str, Any]:
    """The ``blocker_kind``/``blocker_scope``/``blocker_resolution_condition``/
    ``next_observation_ref`` kwargs a ``TERMINAL_POLICY_ONLY`` (candidate-free) request needs
    to mint a real ``BLOCKED`` transition through ``reflow()`` -- the identical shape
    ``tests/unit/reflow/test_failed_route.py`` already uses for this same route."""

    return {
        "blocker_kind": "EVIDENCE_INSUFFICIENT",
        "blocker_scope": {
            "kind": "difference_blocker_scope",
            "affected_subject_refs": {
                "collection_kind": "UNORDERED_SET",
                "members": [{"kind": "difference", "id": difference["difference_id"]}],
            },
            "effective_boundary": difference["effective_boundary"],
            "blocked_stage": "DIFFERENCE_EVALUATION",
        },
        "blocker_resolution_condition": {
            "kind": "blocker_resolution_condition",
            "condition_code": "REQUIRED_EVIDENCE_AVAILABLE",
            "subject_ref": {"kind": "difference", "id": difference["difference_id"]},
            "expected_state": "AVAILABLE",
            "verification_request_ref": {
                "kind": "next_observation_request", "id": "OBS-REQ-" + "9" * 64
            },
        },
        "next_observation_ref": {"kind": "next_observation_request", "id": "OBS-REQ-" + "9" * 64},
    }


def test_r10f1_reflow_resolves_kernel_provenance_from_the_store_even_with_an_empty_caller_pool(
    tmp_path: Path,
) -> None:
    """R10-F1: ``STATE_REFERENCE_TO_CALLER_POOL_IS_CANONICAL_RESOLUTION=false`` -- a real
    Reflow cycle resolves its base Kernel provenance purely from the Store's own
    genesis-adopted record. An entirely empty ``closure_request["source_snapshots"]`` (never
    restating the genesis snapshot at all) does not stop it -- the caller pool was never the
    authority, so its absence cannot be either. Uses the same ``TERMINAL_POLICY_ONLY`` shape
    the R9-F2 negative controls above already use, so this stays isolated to base-Kernel-
    provenance resolution alone, never entangled with G19's own separate re-verification of
    ``source_snapshots`` for a candidate."""

    from tests.state_helpers import real_kernel_git_objects

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = base_closure_request(difference, policy)
    request["source_snapshots"] = []

    result = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        closure_request=request,
        observation_refs=[],
        reflow_instant=REFLOW_INSTANT,
        **_terminal_policy_only_blocker_kwargs(difference),
    )
    assert result["decision"]["to_status"] == "BLOCKED"
    kernel_source_ref, _ = real_kernel_git_objects()
    assert (
        result["evaluation"]["base_kernel_source_ref_evaluated"]["commit_sha"]
        == kernel_source_ref["commit_sha"]
    )


def test_r10f1_a_forged_caller_pool_entry_under_the_correct_id_cannot_override_the_stores_body(
    tmp_path: Path,
) -> None:
    """R10-F1: ``CALLER_SELF_CONSISTENCY_NE_COMMITTED_PREDECESSOR=true`` -- a caller-supplied
    ``source_snapshots`` entry stamped under the genesis snapshot's own real id, but carrying
    a tampered ``git_provenance.blob_sha`` (so it no longer even recomputes its own id), is
    never consulted at all: resolution reads only the Store's own adopted body, so the
    poisoned pool entry changes nothing about the outcome."""

    from tests.state_helpers import real_kernel_source_snapshot

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = base_closure_request(difference, policy)

    poisoned = deepcopy(real_kernel_source_snapshot())
    poisoned["git_provenance"]["blob_sha"] = "0" * 40
    request["source_snapshots"] = [poisoned]

    result = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        closure_request=request,
        observation_refs=[],
        reflow_instant=REFLOW_INSTANT,
        **_terminal_policy_only_blocker_kwargs(difference),
    )
    assert result["decision"]["to_status"] == "BLOCKED"
    assert (
        result["evaluation"]["base_kernel_source_ref_evaluated"]["commit_sha"]
        == result["evaluation"]["kernel_source_ref_evaluated"]["commit_sha"]
    )


def test_r10f1_reflow_fails_closed_when_genesis_names_a_snapshot_the_store_never_adopted(
    tmp_path: Path,
) -> None:
    """R10-F1: ``GENESIS_DANGLING_CANONICAL_REFERENCE_ALLOWED=false`` -- a genesis State
    naming a real, well-formed Kernel Source Snapshot id that the Store itself never adopted
    (``store.initialize`` called with no ``records=``) fails closed even though the caller's
    own ``closure_request["source_snapshots"]`` supplies a perfectly self-consistent record
    under that exact id -- a caller pool can never substitute for the Store's own adoption of
    a predecessor reference."""

    from tests.difference_helpers import objective_revision as _objective_revision
    from tests.state_helpers import initial_state, real_kernel_source_snapshot

    from manosube_agent_civilization.state.fingerprint import fingerprint_project_state

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = initial_state()
    project_state["objective_revision_id"] = _objective_revision()["objective_revision_id"]
    project_state["semantic_fingerprint"] = fingerprint_project_state(
        project_state, schema_root=SCHEMA_ROOT
    ).as_dict()
    # Deliberately no records= -- the genesis reference is left dangling at the Store.
    store.initialize(project_state["project_id"], project_state)

    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = base_closure_request(difference, policy)
    request["source_snapshots"] = [real_kernel_source_snapshot()]

    with pytest.raises(ReflowValidationError, match="does not resolve to a Store-adopted"):
        reflow(
            store,
            project_id=project_state["project_id"],
            previous_event_id=difference["genesis_event_ref"]["id"],
            event_revision=1,
            closure_request=request,
            observation_refs=[],
            reflow_instant=REFLOW_INSTANT,
        )
    # Nothing committed at all.
    assert store.load_current(project_state["project_id"]) == project_state


def test_r10f1_genesis_adopted_snapshot_still_resolves_identically_after_a_real_reflow_cycle(
    tmp_path: Path,
) -> None:
    """R10-F1: the genesis-adopted Kernel Source Snapshot record's own identity survives a
    real committed Reflow cycle unchanged -- persistence, not merely one-shot resolution at
    genesis time."""

    from tests.state_helpers import real_kernel_source_snapshot

    from manosube_agent_civilization.observation.source_snapshot import resolve_source_snapshot

    store, project_state, _difference, result = _closed_store(tmp_path)
    assert result["decision"]["to_status"] == "CLOSED"

    snapshot = real_kernel_source_snapshot()
    resolved = store.resolve_record(
        project_state["project_id"], "source_snapshot", snapshot["source_snapshot_id"]
    )
    assert resolved == snapshot
    ref = {"kind": "source_snapshot", "id": snapshot["source_snapshot_id"]}
    assert resolve_source_snapshot(ref, [resolved])["source_snapshot_id"] == snapshot["source_snapshot_id"]


@pytest.mark.parametrize("stage", list(STAGES))
def test_r10f1_genesis_with_records_is_invisible_before_recovery_and_converges_after(
    stage: str, tmp_path: Path
) -> None:
    """R10-F1 crash-recovery boundary, sharpened R11-F1 into a real joint check across all
    four public read surfaces: a genesis carrying ``records`` is staged and promoted through
    the identical manifest/journal mechanism ``commit`` already uses (mirrored fault hook,
    identical named :data:`STAGES`), so a crash at any of the 9 stages either leaves genesis
    cleanly abandoned (retryable, for a crash before ``AFTER_COMMIT_INTENT``) or recoverable
    to the identical committed State, transaction and record through the same generic
    ``recover`` -- no second recovery mechanism for this one new path.

    R11-F1: Round 10's own version of this test only checked ``resolve_record`` before
    recovery for a late-stage crash -- ``resolve_transaction``/``reconstruct``/
    ``load_current`` were never exercised there, which is exactly how the real R11-F1 defect
    (``_transaction_committed``'s blanket ``transaction_id == GENESIS_TRANSACTION_ID``
    trusting the *name* alone, regardless of whether *this* genesis's own journal was ever
    actually completed) escaped Round 10's own coverage. All four surfaces are now checked
    together, both before and after recovery, at every one of the 9 stages --
    ``GENESIS_PARTIAL_VISIBILITY_ALLOWED=false``."""

    from tests.difference_helpers import objective_revision as _objective_revision
    from tests.state_helpers import genesis_source_snapshot_records, initial_state

    from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
    from manosube_agent_civilization.store.errors import CorruptStoreError, StateNotFoundError

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = initial_state()
    project_state["objective_revision_id"] = _objective_revision()["objective_revision_id"]
    project_state["semantic_fingerprint"] = fingerprint_project_state(
        project_state, schema_root=SCHEMA_ROOT
    ).as_dict()
    records = genesis_source_snapshot_records(project_state)
    assert records, "this fixture must actually reference the real Kernel snapshot"
    snapshot_kind, snapshot_id, _snapshot_body = records[0]
    project_id = project_state["project_id"]

    def fault(current: str) -> None:
        if current == stage:
            raise SimulatedCrash(stage)

    with pytest.raises(SimulatedCrash):
        store.initialize(project_id, project_state, records=records, fault=fault)

    # Joint pre-recovery check, at every one of the 9 crash stages: none of the four public
    # read surfaces may expose this genesis until its own COMMITTED marker exists, whether or
    # not the event already reached the raw lineage log (AFTER_LINEAGE_APPEND onward).
    assert store.resolve_record(project_id, snapshot_kind, snapshot_id) is None
    assert store.resolve_transaction(project_id, "TX-GENESIS") is None
    with pytest.raises(CorruptStoreError, match="lineage has no genesis"):
        store.reconstruct(project_id)
    with pytest.raises(CorruptStoreError, match="lineage has no genesis"):
        store.load_current(project_id)

    early_stage = stage in STAGES[: STAGES.index("AFTER_COMMIT_INTENT")]
    if early_stage:
        # Abandoned, not completed -- genesis's own COMMIT_INTENT was never durably
        # written, so recover() has nothing to complete. The project stays cleanly
        # uninitialized (StateNotFoundError, not corruption), and a caller may safely
        # retry initialize() from scratch.
        with pytest.raises(StateNotFoundError):
            store.recover(project_id)
        assert store.resolve_record(project_id, snapshot_kind, snapshot_id) is None
        assert store.resolve_transaction(project_id, "TX-GENESIS") is None
        store.initialize(project_id, project_state, records=records)
        assert store.load_current(project_id) == project_state
    else:
        store.recover(project_id)
        # Joint post-recovery check: all four surfaces now agree, together, on the same
        # completed genesis transaction.
        resolved = store.resolve_record(project_id, snapshot_kind, snapshot_id)
        assert resolved is not None
        assert resolved["source_snapshot_id"] == snapshot_id
        transaction = store.resolve_transaction(project_id, "TX-GENESIS")
        assert transaction is not None
        assert transaction["transaction_id"] == "TX-GENESIS"
        assert store.reconstruct(project_id) == project_state
        assert store.load_current(project_id) == project_state
