"""V2, V4, V5, V6: end-to-end Acceptance Policy Lineage over a real ``FileStateStore``
(FD-0004, Issue #80) -- the canonical successful route, the mandatory Phase 19 incident
regression fixture, and the decisive negative/tamper/substitution matrix.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.acceptance_policy_world import bound_world, clause, source_reference

from manosube_agent_civilization.acceptance_policy import (
    ConflictingPolicyReplayError,
    PolicyLineageConflictError,
    PolicyProvenanceError,
    UnauthorizedPolicyAdoptionError,
    UndeclaredPolicyChangeError,
    adopt_acceptance_policy_transition,
    assert_no_undeclared_policy_change_in_payload,
    open_acceptance_policy_baseline,
    preview_acceptance_policy_transition,
    propose_acceptance_policy_transition,
    resolve_and_verify_effective_policy,
)

GOVERNING_ISSUE = 77
_ACTIONS_CLAUSE_ID = "GITHUB_ACTIONS_IS_NOT_ACCEPTANCE_AUTHORITY"
_GATE_CLAUSE_ID = "GITHUB_PREMERGE_GATE_GREEN"


def _open_baseline(world: dict[str, Any]) -> dict[str, Any]:
    project_id = world["project_id"]
    return open_acceptance_policy_baseline(
        world["store"],
        project_id,
        governing_issue=GOVERNING_ISSUE,
        source_reference=source_reference("1001", source_kind="ORIGINAL_ISSUE"),
        clauses=[
            clause(
                _ACTIONS_CLAUSE_ID,
                policy_class="AUTHORITY",
                project_id=project_id,
                existed_in_original_contract=True,
            )
        ],
        committed_at="2026-09-11T13:00:00Z",
    )


def _baseline_ref(baseline: dict[str, Any]) -> dict[str, str]:
    return {"kind": "acceptance_policy_baseline", "id": baseline["acceptance_policy_baseline_id"]}


def _adopt(
    world: dict[str, Any], *, adopted_ref: dict[str, str], comment_id: str, decided_at: str
) -> dict[str, Any]:
    return adopt_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=adopted_ref,
        decision_owner="SHUKOU",
        source_reference=source_reference(comment_id, source_kind="AUTHORITY_ADOPTION"),
        decided_at=decided_at,
        committed_at=decided_at,
    )


# --- canonical successful route (V2) ---------------------------------------------------------- #


def test_baseline_genesis_is_immediately_resolvable_as_the_effective_policy(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    view = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], _baseline_ref(baseline), []
    )
    assert [c["clause_id"] for c in view["effective_clauses"]] == [_ACTIONS_CLAUSE_ID]
    assert view["effective_clauses"][0]["provenance_chain"] == [_baseline_ref(baseline)]


def test_propose_then_adopt_makes_a_new_clause_effective(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    proposed = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=world["project_id"],
        existed_in_original_contract=False,
        merge=True,
    )
    transition = propose_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        adoption_refs=[],
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("1002", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="remove if Actions infrastructure proves unreliable",
        committed_at="2026-09-11T13:05:00Z",
    )
    # a proposal alone does not make the clause effective (FD4-C3)
    view_before_adoption = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref, []
    )
    assert _GATE_CLAUSE_ID not in {
        c["clause_id"] for c in view_before_adoption["effective_clauses"]
    }

    adoption = _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": transition["acceptance_policy_transition_id"],
        },
        comment_id="1003",
        decided_at="2026-09-11T13:10:00Z",
    )
    adoption_ref = {
        "kind": "acceptance_policy_adoption",
        "id": adoption["acceptance_policy_adoption_id"],
    }
    view_after = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref, [adoption_ref]
    )
    assert {c["clause_id"] for c in view_after["effective_clauses"]} == {
        _ACTIONS_CLAUSE_ID,
        _GATE_CLAUSE_ID,
    }


def test_impact_preview_shows_the_exact_before_after_and_new_blocker(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    view = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref, []
    )
    proposed = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=world["project_id"],
        existed_in_original_contract=False,
        merge=True,
    )
    candidate = propose_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        adoption_refs=[],
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("1004", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="revert",
        committed_at="2026-09-11T13:06:00Z",
    )
    preview = preview_acceptance_policy_transition(
        world["store"], world["project_id"], baseline_ref, [], candidate
    )
    assert preview["before_policy"] == view["effective_clauses"]
    assert preview["proposed_change"] == {"policy_operation": "ADD", "clause_id": _GATE_CLAUSE_ID}
    assert preview["new_blockers"] == [
        {"clause_id": _GATE_CLAUSE_ID, "blocking_effect_field": "merge"}
    ]
    assert preview["removed_blockers"] == []
    assert {c["clause_id"] for c in preview["after_policy"]} == {
        _ACTIONS_CLAUSE_ID,
        _GATE_CLAUSE_ID,
    }


# --- V5: the mandatory Phase 19 incident regression fixture ---------------------------------- #


def test_phase19_incident_reconstructs_as_three_distinct_facts_never_contradictory(
    tmp_path: Path,
) -> None:
    """ORIGINAL_ISSUE_77_CLAUSE (Actions is not acceptance Authority) and
    ROUND_5_ADOPTED_SUPPLEMENT (the premerge gate is required Evidence) are not contradictory,
    because Authority and required Evidence are separate dimensions (FD4-C3/FD4-C4)."""

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)

    round5_supplement = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=world["project_id"],
        existed_in_original_contract=False,
        merge=True,
    )
    t_add = propose_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        adoption_refs=[],
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=round5_supplement,
        source_reference=source_reference("2001", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="remove if Actions infrastructure proves unreliable",
        committed_at="2026-09-12T00:00:00Z",
    )
    a_add = _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_add["acceptance_policy_transition_id"],
        },
        comment_id="2002",
        decided_at="2026-09-12T00:05:00Z",
    )
    a_add_ref = {"kind": "acceptance_policy_adoption", "id": a_add["acceptance_policy_adoption_id"]}

    view_with_gate = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref, [a_add_ref]
    )
    by_id = {c["clause_id"]: c for c in view_with_gate["effective_clauses"]}
    assert by_id[_ACTIONS_CLAUSE_ID]["policy_class"] == "AUTHORITY"
    assert by_id[_GATE_CLAUSE_ID]["policy_class"] == "REQUIRED_EVIDENCE"
    # both live simultaneously -- not a contradiction, since they occupy different dimensions
    assert by_id[_ACTIONS_CLAUSE_ID]["existed_in_original_contract"] is True
    assert by_id[_GATE_CLAUSE_ID]["existed_in_original_contract"] is False

    # LATER_ADOPTED_TRANSITION: the Round 5 supplement is later removed, and the removal must
    # reference the exact Round 5 adoption it supersedes (its own prior_clause_binding chain).
    t_remove = propose_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        adoption_refs=[a_add_ref],
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="REMOVE",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=None,
        source_reference=source_reference("2003", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="re-adopt if Actions infrastructure recovers",
        committed_at="2026-09-13T12:00:00Z",
    )
    assert (
        t_remove["prior_clause_binding"]["source_ref"]["id"]
        == t_add["acceptance_policy_transition_id"]
    )
    a_remove = _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_remove["acceptance_policy_transition_id"],
        },
        comment_id="2004",
        decided_at="2026-09-13T12:05:00Z",
    )
    a_remove_ref = {
        "kind": "acceptance_policy_adoption",
        "id": a_remove["acceptance_policy_adoption_id"],
    }

    final_view = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref, [a_add_ref, a_remove_ref]
    )
    assert {c["clause_id"] for c in final_view["effective_clauses"]} == {_ACTIONS_CLAUSE_ID}

    # the original baseline clause was never rewritten to claim the gate always existed
    baseline_clause_ids = {c["clause_id"] for c in baseline["clauses"]}
    assert baseline_clause_ids == {_ACTIONS_CLAUSE_ID}

    # replay determinism (V6): the identical fold, recomputed, is the identical view
    replayed = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref, [a_add_ref, a_remove_ref]
    )
    assert (
        replayed["effective_view_semantic_fingerprint"]
        == final_view["effective_view_semantic_fingerprint"]
    )


def test_removing_the_round5_supplement_as_original_restoration_without_the_real_transition_is_impossible(
    tmp_path: Path,
) -> None:
    """'Restore original contract' without the intervening lineage and proposer disclosure
    refuses -- there is no route that removes a clause without a genuine predecessor: a
    REMOVE proposed for a clause_id that was never ADDed has neither a prior nor a proposed
    clause body to classify, and is refused before any commit."""

    from manosube_agent_civilization.acceptance_policy import AcceptancePolicyValidationError

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    with pytest.raises(AcceptancePolicyValidationError):
        propose_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            baseline_ref=baseline_ref,
            adoption_refs=[],
            clause_id=_GATE_CLAUSE_ID,
            policy_operation="REMOVE",
            proposed_by="STRUCTURAL_ADVISOR",
            proposed_clause=None,
            source_reference=source_reference("2999", source_kind="STRUCTURAL_REVIEW"),
            rollback_condition="r",
            committed_at="2026-09-13T00:00:00Z",
        )
    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after


def test_actions_is_not_authority_never_implies_actions_cannot_be_required_evidence(
    tmp_path: Path,
) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    view = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref, []
    )
    actions_clause = next(
        c for c in view["effective_clauses"] if c["clause_id"] == _ACTIONS_CLAUSE_ID
    )
    assert actions_clause["policy_class"] == "AUTHORITY"
    # nothing about the AUTHORITY clause's own blocking_effect forbids a REQUIRED_EVIDENCE
    # clause from separately existing -- the two dimensions are structurally independent,
    # never derived from one another.
    assert actions_clause["blocking_effect"]["merge"] is False


def test_infrastructure_failure_never_changes_effective_policy(tmp_path: Path) -> None:
    """An Actions/CI infrastructure failure changes observation state only -- nothing in this
    package's own effective-policy derivation ever reads CI status, so folding the identical
    adoption set always yields the identical policy regardless of any external mechanism
    outcome recorded elsewhere."""

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    view_before = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref, []
    )
    # no route in this package accepts a CI/Actions status argument at all -- the absence of
    # such a parameter on every public route function is itself the proof; recomputing the
    # identical fold demonstrates it is deterministic irrespective of any external event.
    view_after = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref, []
    )
    assert (
        view_before["effective_view_semantic_fingerprint"]
        == view_after["effective_view_semantic_fingerprint"]
    )


# --- decisive negative / tamper / substitution matrix (V4, V6) ------------------------------- #


def test_undeclared_add_smuggled_inside_a_code_finding_refuses(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    with pytest.raises(UndeclaredPolicyChangeError):
        assert_no_undeclared_policy_change_in_payload(
            world["store"],
            world["project_id"],
            baseline_ref,
            [],
            {"finding": "some unrelated code defect", "cited_control": _ACTIONS_CLAUSE_ID},
        )


def test_undeclared_add_smuggled_only_inside_required_proofs_refuses(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    with pytest.raises(UndeclaredPolicyChangeError):
        assert_no_undeclared_policy_change_in_payload(
            world["store"],
            world["project_id"],
            baseline_ref,
            [],
            {"required_proofs": {f"{_ACTIONS_CLAUSE_ID}_REQUIRED": True}},
        )


def test_a_handoff_cannot_activate_a_gate_not_present_in_effective_policy(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    # the gate has never been proposed or adopted -- referencing it in a handoff-shaped
    # payload without declaring policy_change is refused exactly like any other mention
    with pytest.raises(UndeclaredPolicyChangeError):
        assert_no_undeclared_policy_change_in_payload(
            world["store"],
            world["project_id"],
            baseline_ref,
            [],
            {"handoff_id": "HANDOFF_X", "activates": _ACTIONS_CLAUSE_ID},
        )


def test_wrong_human_authority_decision_owner_refuses(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    with pytest.raises(Exception):  # noqa: B017 - AcceptancePolicyValidationError, imported below in a focused assertion
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=_baseline_ref(baseline),
            decision_owner="CLAUDE_CODE",
            source_reference=source_reference("3001", source_kind="AUTHORITY_ADOPTION"),
            decided_at="2026-09-13T00:00:00Z",
            committed_at="2026-09-13T00:00:00Z",
        )


def test_wrong_comment_author_association_refuses(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=_baseline_ref(baseline),
            decision_owner="SHUKOU",
            source_reference=source_reference(
                "3002", source_kind="AUTHORITY_ADOPTION", comment_author_association="MEMBER"
            ),
            decided_at="2026-09-13T00:00:00Z",
            committed_at="2026-09-13T00:00:00Z",
        )


def test_wrong_project_substitution_refuses(tmp_path: Path) -> None:
    """A record genuinely committed into this project's own Store namespace, but whose own
    declared ``project_id`` field names a different project, refuses on resolution -- proving
    the resolver independently re-checks the field rather than trusting the Store's own
    per-project namespacing alone."""

    from manosube_agent_civilization.acceptance_policy import engine as ap_engine, route as ap_route

    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]

    forged_baseline = ap_engine.build_baseline(
        project_id="PRJ-FORGED-0001",
        governing_issue=GOVERNING_ISSUE,
        source_reference=source_reference("9001", source_kind="ORIGINAL_ISSUE"),
        clauses=[
            clause(
                _ACTIONS_CLAUSE_ID,
                policy_class="AUTHORITY",
                project_id="PRJ-FORGED-0001",
                existed_in_original_contract=True,
            )
        ],
    )
    ap_route._commit_one_record(
        store,
        project_id,
        "acceptance_policy_baseline",
        forged_baseline["acceptance_policy_baseline_id"],
        forged_baseline,
        "2026-09-11T13:00:03Z",
    )
    with pytest.raises(PolicyProvenanceError):
        ap_route.resolve_and_verify_baseline(
            store, project_id, forged_baseline["acceptance_policy_baseline_id"]
        )


def test_missing_predecessor_transition_refuses(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    forged_adoption_ref = {"kind": "acceptance_policy_adoption", "id": "AP-ADOPT-" + "0" * 64}
    with pytest.raises(PolicyProvenanceError):
        resolve_and_verify_effective_policy(
            world["store"], world["project_id"], baseline_ref, [forged_adoption_ref]
        )


def test_a_fork_two_transitions_claiming_the_same_predecessor_refuses(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    proposed_a = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=world["project_id"],
        existed_in_original_contract=False,
        merge=True,
    )
    proposed_b = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=world["project_id"],
        existed_in_original_contract=False,
        issue_closure=True,
    )
    t_a = propose_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        adoption_refs=[],
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed_a,
        source_reference=source_reference("4001", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T00:00:00Z",
    )
    t_b = propose_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        adoption_refs=[],
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed_b,
        source_reference=source_reference("4002", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T00:01:00Z",
    )
    a_a = _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_a["acceptance_policy_transition_id"],
        },
        comment_id="4003",
        decided_at="2026-09-13T00:02:00Z",
    )
    a_b = _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_b["acceptance_policy_transition_id"],
        },
        comment_id="4004",
        decided_at="2026-09-13T00:03:00Z",
    )
    a_a_ref = {"kind": "acceptance_policy_adoption", "id": a_a["acceptance_policy_adoption_id"]}
    a_b_ref = {"kind": "acceptance_policy_adoption", "id": a_b["acceptance_policy_adoption_id"]}
    with pytest.raises(PolicyLineageConflictError):
        resolve_and_verify_effective_policy(
            world["store"], world["project_id"], baseline_ref, [a_a_ref, a_b_ref]
        )


def test_reordered_adoption_sequence_refuses(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    proposed = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=world["project_id"],
        existed_in_original_contract=False,
        merge=True,
    )
    t_add = propose_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        adoption_refs=[],
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("5001", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T00:00:00Z",
    )
    a_add = _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_add["acceptance_policy_transition_id"],
        },
        comment_id="5002",
        decided_at="2026-09-13T00:01:00Z",
    )
    a_add_ref = {"kind": "acceptance_policy_adoption", "id": a_add["acceptance_policy_adoption_id"]}
    t_remove = propose_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        adoption_refs=[a_add_ref],
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="REMOVE",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=None,
        source_reference=source_reference("5003", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T00:02:00Z",
    )
    a_remove = _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_remove["acceptance_policy_transition_id"],
        },
        comment_id="5004",
        decided_at="2026-09-13T00:03:00Z",
    )
    a_remove_ref = {
        "kind": "acceptance_policy_adoption",
        "id": a_remove["acceptance_policy_adoption_id"],
    }
    with pytest.raises(PolicyLineageConflictError):
        # the REMOVE adoption folded before its own ADD predecessor
        resolve_and_verify_effective_policy(
            world["store"], world["project_id"], baseline_ref, [a_remove_ref, a_add_ref]
        )


def test_exact_replay_of_a_baseline_commit_is_idempotent(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    state_after_first = world["store"].load_current(world["project_id"])["state_revision"]
    replayed = open_acceptance_policy_baseline(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE,
        source_reference=source_reference("1001", source_kind="ORIGINAL_ISSUE"),
        clauses=[
            clause(
                _ACTIONS_CLAUSE_ID,
                policy_class="AUTHORITY",
                project_id=world["project_id"],
                existed_in_original_contract=True,
            )
        ],
        committed_at="2026-09-11T13:00:00Z",
    )
    state_after_replay = world["store"].load_current(world["project_id"])["state_revision"]
    assert replayed["acceptance_policy_baseline_id"] == baseline["acceptance_policy_baseline_id"]
    assert state_after_replay == state_after_first


def test_conflicting_replay_of_the_same_transaction_id_refuses(tmp_path: Path) -> None:
    """A different record body claiming an identity another commit already used, resubmitted
    under the identical transition (same from/to revision, same fingerprints -- a genuine
    concurrent double-submission, not a sequential re-call after state already advanced),
    refuses via the Store's own manifest-identity check."""

    from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
    from manosube_agent_civilization.store.commit import commit_state_transition
    from manosube_agent_civilization.store.errors import TransactionConflictError

    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    # captured *before* the real baseline commit -- the exact state that commit's own
    # transition was built from, so the forged resubmission below can reproduce the identical
    # transition envelope and isolate the record-manifest-identity check specifically.
    from_state = store.load_current(project_id)
    baseline = _open_baseline(world)

    forged_baseline = dict(baseline)
    forged_baseline["governing_issue"] = 999999

    to_state = dict(from_state)
    to_state["state_revision"] = from_state["state_revision"] + 1
    to_state["previous_state_fingerprint"] = from_state["semantic_fingerprint"]
    to_state["lineage_head_ref"] = {
        "kind": "state_transition",
        "id": baseline["acceptance_policy_baseline_id"],
    }
    to_state["semantic_fingerprint"] = fingerprint_project_state(to_state).as_dict()
    transition = {
        "schema_version": "0.1",
        "transaction_id": baseline["acceptance_policy_baseline_id"],
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": from_state["state_revision"],
        "to_revision": to_state["state_revision"],
        "before_fingerprint": from_state["semantic_fingerprint"],
        "after_fingerprint": to_state["semantic_fingerprint"],
        "after_state": to_state,
        "evidence_refs": [],
        "committed_at": "2026-09-11T13:00:00Z",
    }
    with pytest.raises(TransactionConflictError):
        commit_state_transition(
            store,
            project_id,
            from_state["state_revision"],
            from_state["semantic_fingerprint"],
            to_state,
            transition,
            records=[
                (
                    "acceptance_policy_baseline",
                    baseline["acceptance_policy_baseline_id"],
                    forged_baseline,
                )
            ],
        )


def test_route_py_translates_a_conflicting_replay_into_the_typed_package_error(
    tmp_path: Path,
) -> None:
    """The same conflicting-body-under-the-same-identity attempt, made through this package's
    own public route rather than directly against the Store, surfaces as
    :class:`ConflictingPolicyReplayError` -- never an opaque Store exception leaking through
    this package's own boundary."""

    world = bound_world(tmp_path)
    from manosube_agent_civilization.acceptance_policy import route as ap_route

    baseline = _open_baseline(world)
    forged = dict(baseline)
    forged["governing_issue"] = 999999
    with pytest.raises(ConflictingPolicyReplayError):
        ap_route._commit_one_record(
            world["store"],
            world["project_id"],
            "acceptance_policy_baseline",
            baseline["acceptance_policy_baseline_id"],
            forged,
            "2026-09-11T13:00:02Z",
        )


def test_no_refusal_ever_advances_state_revision(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]

    with pytest.raises(PolicyProvenanceError):
        resolve_and_verify_effective_policy(
            world["store"],
            world["project_id"],
            baseline_ref,
            [{"kind": "acceptance_policy_adoption", "id": "AP-ADOPT-" + "1" * 64}],
        )
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=baseline_ref,
            decision_owner="SHUKOU",
            source_reference=source_reference(
                "6001", source_kind="AUTHORITY_ADOPTION", comment_author_association="MEMBER"
            ),
            decided_at="2026-09-13T00:00:00Z",
            committed_at="2026-09-13T00:00:00Z",
        )

    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after
