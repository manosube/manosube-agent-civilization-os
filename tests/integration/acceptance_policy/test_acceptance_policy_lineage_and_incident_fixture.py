"""V2, V4, V5, V6: end-to-end Acceptance Policy Lineage over a real ``FileStateStore``
(FD-0004, Issue #80) -- the canonical successful route, the mandatory Phase 19 incident
regression fixture, the decisive negative/tamper/substitution matrix, and the Structural
Review Round 1 (PR #82) corrections P82-R1-F1/F2/F3/F5 and Round 2 corrections
P82-R2-F1/F2/F3/F4.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest
from tests.fixtures.acceptance_policy_world import (
    bound_world,
    clause,
    governance_adoption_record,
    source_reference,
)
from tests.fixtures.product_binding import human_authority_signing_key

from manosube_agent_civilization.acceptance_policy import (
    AcceptancePolicyValidationError,
    ConflictingPolicyReplayError,
    PolicyLineageConflictError,
    PolicyProvenanceError,
    UnauthorizedPolicyAdoptionError,
    UndeclaredPolicyChangeError,
    adopt_acceptance_policy_transition,
    assert_no_undeclared_policy_change_in_payload,
    engine as ap_engine,
    identity,
    open_acceptance_policy_baseline,
    preview_acceptance_policy_transition,
    propose_acceptance_policy_transition,
    resolve_and_verify_adoption,
    resolve_and_verify_baseline,
    resolve_and_verify_effective_policy,
    resolve_and_verify_transition,
    route as ap_route,
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
    world: dict[str, Any],
    *,
    adopted_ref: dict[str, str],
    comment_id: str,
    decided_at: str,
    governing_issue: int = GOVERNING_ISSUE,
    path: str = "issues/80",
) -> dict[str, Any]:
    sr = source_reference(comment_id, source_kind="AUTHORITY_ADOPTION", path=path)
    return adopt_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=governing_issue,
        adopted_ref=adopted_ref,
        decision_owner="SHUKOU",
        source_reference=sr,
        governance_adoption_record=governance_adoption_record(
            project_id=world["project_id"],
            governing_issue=governing_issue,
            adopted_ref=adopted_ref,
            source_reference=sr,
            project_binding_id=world["project_binding_id"],
            decided_at=decided_at,
        ),
        project_binding_id=world["project_binding_id"],
        decided_at=decided_at,
        committed_at=decided_at,
    )


def _adopt_baseline(
    world: dict[str, Any],
    baseline: dict[str, Any],
    *,
    comment_id: str = "10011",
    decided_at: str = "2026-09-11T13:00:01Z",
) -> dict[str, Any]:
    """P82-R1-F2: a baseline's own clauses are not effective until this exact act happens --
    every test that needs the genesis baseline's own clauses to be *effective* (not merely
    committed) must call this first."""

    return _adopt(
        world, adopted_ref=_baseline_ref(baseline), comment_id=comment_id, decided_at=decided_at
    )


def _open_and_adopt_baseline(world: dict[str, Any]) -> dict[str, Any]:
    baseline = _open_baseline(world)
    _adopt_baseline(world, baseline)
    return baseline


# --- canonical successful route (V2) ---------------------------------------------------------- #


def test_baseline_clauses_are_effective_only_after_baseline_adoption(tmp_path: Path) -> None:
    """P82-R1-F2: a committed-but-not-yet-adopted genesis baseline contributes no effective
    clauses at all -- only the identity-bound Human-Authority adoption of the baseline itself
    activates it."""

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)

    view_before_adoption = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref
    )
    assert view_before_adoption["effective_clauses"] == []

    _adopt_baseline(world, baseline)
    view_after_adoption = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref
    )
    assert [c["clause_id"] for c in view_after_adoption["effective_clauses"]] == [
        _ACTIONS_CLAUSE_ID
    ]
    assert view_after_adoption["effective_clauses"][0]["provenance_chain"] == [baseline_ref]


def test_propose_then_adopt_makes_a_new_clause_effective(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
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
        world["store"], world["project_id"], baseline_ref
    )
    assert _GATE_CLAUSE_ID not in {
        c["clause_id"] for c in view_before_adoption["effective_clauses"]
    }

    _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": transition["acceptance_policy_transition_id"],
        },
        comment_id="1003",
        decided_at="2026-09-11T13:10:00Z",
    )
    # P82-R1-F1: the effective view is derived entirely from Store-owned state -- no
    # adoption_refs argument exists any more for a caller to omit, subset, or reorder.
    view_after = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref
    )
    assert {c["clause_id"] for c in view_after["effective_clauses"]} == {
        _ACTIONS_CLAUSE_ID,
        _GATE_CLAUSE_ID,
    }


def test_impact_preview_shows_the_exact_before_after_and_new_blocker(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    view = resolve_and_verify_effective_policy(world["store"], world["project_id"], baseline_ref)
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
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("1004", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="revert",
        committed_at="2026-09-11T13:06:00Z",
    )
    preview = preview_acceptance_policy_transition(
        world["store"], world["project_id"], baseline_ref, candidate
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
    # P82-R1-F5: the candidate transition itself must appear in the after-policy clause's own
    # provenance -- an ADD's chain starts with it, since there is no prior chain to extend.
    gate_after = next(c for c in preview["after_policy"] if c["clause_id"] == _GATE_CLAUSE_ID)
    assert gate_after["provenance_chain"] == [
        {
            "kind": "acceptance_policy_transition",
            "id": candidate["acceptance_policy_transition_id"],
        }
    ]
    # the unrelated baseline clause's own provenance is untouched
    actions_after = next(c for c in preview["after_policy"] if c["clause_id"] == _ACTIONS_CLAUSE_ID)
    assert actions_after["provenance_chain"] == [baseline_ref]


def test_impact_preview_provenance_extends_prior_chain_for_a_modifying_operation(
    tmp_path: Path,
) -> None:
    """P82-R1-F5: REPLACE/NARROW/BROADEN/RECLASSIFY extend the *prior* effective clause's own
    provenance with the candidate transition -- never merely restate it unchanged."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    broadened = clause(
        _ACTIONS_CLAUSE_ID,
        policy_class="AUTHORITY",
        project_id=world["project_id"],
        existed_in_original_contract=False,
        structural_review=True,
    )
    candidate = propose_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_ACTIONS_CLAUSE_ID,
        policy_operation="BROADEN",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=broadened,
        source_reference=source_reference("1005", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="revert",
        committed_at="2026-09-11T13:07:00Z",
    )
    preview = preview_acceptance_policy_transition(
        world["store"], world["project_id"], baseline_ref, candidate
    )
    actions_after = next(c for c in preview["after_policy"] if c["clause_id"] == _ACTIONS_CLAUSE_ID)
    assert actions_after["provenance_chain"] == [
        baseline_ref,
        {
            "kind": "acceptance_policy_transition",
            "id": candidate["acceptance_policy_transition_id"],
        },
    ]


def test_impact_preview_removed_clause_has_no_surviving_provenance(tmp_path: Path) -> None:
    """P82-R1-F5: REMOVE has no surviving effective clause -- there is nothing left to attribute
    provenance to."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    candidate = propose_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_ACTIONS_CLAUSE_ID,
        policy_operation="REMOVE",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=None,
        source_reference=source_reference("1006", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="revert",
        committed_at="2026-09-11T13:08:00Z",
    )
    preview = preview_acceptance_policy_transition(
        world["store"], world["project_id"], baseline_ref, candidate
    )
    assert _ACTIONS_CLAUSE_ID not in {c["clause_id"] for c in preview["after_policy"]}


# --- V5: the mandatory Phase 19 incident regression fixture ---------------------------------- #


def test_phase19_incident_reconstructs_as_three_distinct_facts_never_contradictory(
    tmp_path: Path,
) -> None:
    """ORIGINAL_ISSUE_77_CLAUSE (Actions is not acceptance Authority) and
    ROUND_5_ADOPTED_SUPPLEMENT (the premerge gate is required Evidence) are not contradictory,
    because Authority and required Evidence are separate dimensions (FD4-C3/FD4-C4)."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
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
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=round5_supplement,
        source_reference=source_reference("2001", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="remove if Actions infrastructure proves unreliable",
        committed_at="2026-09-12T00:00:00Z",
    )
    _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_add["acceptance_policy_transition_id"],
        },
        comment_id="2002",
        decided_at="2026-09-12T00:05:00Z",
    )

    view_with_gate = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref
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
    _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_remove["acceptance_policy_transition_id"],
        },
        comment_id="2004",
        decided_at="2026-09-13T12:05:00Z",
    )

    final_view = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref
    )
    assert {c["clause_id"] for c in final_view["effective_clauses"]} == {_ACTIONS_CLAUSE_ID}

    # the original baseline clause was never rewritten to claim the gate always existed
    baseline_clause_ids = {c["clause_id"] for c in baseline["clauses"]}
    assert baseline_clause_ids == {_ACTIONS_CLAUSE_ID}

    # replay determinism (V6): the identical fold, recomputed, is the identical view
    replayed = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref
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
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    with pytest.raises(AcceptancePolicyValidationError):
        propose_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            baseline_ref=baseline_ref,
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
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    view = resolve_and_verify_effective_policy(world["store"], world["project_id"], baseline_ref)
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
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    view_before = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref
    )
    # no route in this package accepts a CI/Actions status argument at all -- the absence of
    # such a parameter on every public route function is itself the proof; recomputing the
    # identical fold demonstrates it is deterministic irrespective of any external event.
    view_after = resolve_and_verify_effective_policy(
        world["store"], world["project_id"], baseline_ref
    )
    assert (
        view_before["effective_view_semantic_fingerprint"]
        == view_after["effective_view_semantic_fingerprint"]
    )


# --- decisive negative / tamper / substitution matrix (V4, V6) ------------------------------- #


def test_undeclared_add_smuggled_inside_a_code_finding_refuses(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    with pytest.raises(UndeclaredPolicyChangeError):
        assert_no_undeclared_policy_change_in_payload(
            world["store"],
            world["project_id"],
            baseline_ref,
            {"finding": "some unrelated code defect", "cited_control": _ACTIONS_CLAUSE_ID},
        )


def test_undeclared_add_smuggled_only_inside_required_proofs_refuses(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    with pytest.raises(UndeclaredPolicyChangeError):
        assert_no_undeclared_policy_change_in_payload(
            world["store"],
            world["project_id"],
            baseline_ref,
            {"required_proofs": {f"{_ACTIONS_CLAUSE_ID}_REQUIRED": True}},
        )


def test_a_handoff_cannot_activate_a_gate_not_present_in_effective_policy(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    # the gate has never been proposed or adopted -- referencing it in a handoff-shaped
    # payload without declaring policy_change is refused exactly like any other mention
    with pytest.raises(UndeclaredPolicyChangeError):
        assert_no_undeclared_policy_change_in_payload(
            world["store"],
            world["project_id"],
            baseline_ref,
            {"handoff_id": "HANDOFF_X", "activates": _ACTIONS_CLAUSE_ID},
        )


def test_wrong_human_authority_decision_owner_refuses(tmp_path: Path) -> None:
    from manosube_agent_civilization.acceptance_policy import AcceptancePolicyValidationError

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    sr = source_reference("3001", source_kind="AUTHORITY_ADOPTION")
    with pytest.raises(AcceptancePolicyValidationError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=baseline_ref,
            decision_owner="CLAUDE_CODE",
            source_reference=sr,
            governance_adoption_record=governance_adoption_record(
                project_id=world["project_id"],
                governing_issue=GOVERNING_ISSUE,
                adopted_ref=baseline_ref,
                source_reference=sr,
                project_binding_id=world["project_binding_id"],
                decided_at="2026-09-13T00:00:00Z",
                decision_owner="CLAUDE_CODE",
            ),
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T00:00:00Z",
            committed_at="2026-09-13T00:00:00Z",
        )


def test_wrong_comment_author_association_refuses(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    sr = source_reference(
        "3002", source_kind="AUTHORITY_ADOPTION", comment_author_association="MEMBER"
    )
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=baseline_ref,
            decision_owner="SHUKOU",
            source_reference=sr,
            governance_adoption_record=governance_adoption_record(
                project_id=world["project_id"],
                governing_issue=GOVERNING_ISSUE,
                adopted_ref=baseline_ref,
                source_reference=sr,
                project_binding_id=world["project_binding_id"],
                decided_at="2026-09-13T00:00:00Z",
            ),
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T00:00:00Z",
            committed_at="2026-09-13T00:00:00Z",
        )


def test_wrong_project_substitution_refuses(tmp_path: Path) -> None:
    """A record genuinely committed into this project's own Store namespace, but whose own
    declared ``project_id`` field names a different project, refuses on resolution -- proving
    the resolver independently re-checks the field rather than trusting the Store's own
    per-project namespacing alone."""

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
    """An adoption genuinely committed into the Store, whose own ``adopted_ref`` names a
    transition that was never itself committed, refuses on effective-policy resolution -- this
    can only be constructed by bypassing ``adopt_acceptance_policy_transition``'s own
    resolve-before-build check directly at the engine/Store boundary, exactly like the
    project-substitution forgery above."""

    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)

    forged_transition_ref = {
        "kind": "acceptance_policy_transition",
        "id": "AP-TRANS-" + "0" * 64,
    }
    sr = source_reference("7001", source_kind="AUTHORITY_ADOPTION")
    forged_adoption = ap_engine.build_adoption(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=forged_transition_ref,
        decision_owner="SHUKOU",
        source_reference=sr,
        governance_adoption_record=governance_adoption_record(
            project_id=project_id,
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=forged_transition_ref,
            source_reference=sr,
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T00:00:00Z",
        ),
        project_binding_id=world["project_binding_id"],
        signing_key=human_authority_signing_key(),
        decided_at="2026-09-13T00:00:00Z",
    )
    ap_route._commit_one_record(
        store,
        project_id,
        "acceptance_policy_adoption",
        forged_adoption["acceptance_policy_adoption_id"],
        forged_adoption,
        "2026-09-13T00:00:00Z",
    )
    with pytest.raises(PolicyProvenanceError):
        resolve_and_verify_effective_policy(store, project_id, baseline_ref)


def test_a_fork_two_transitions_claiming_the_same_predecessor_refuses(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
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
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed_b,
        source_reference=source_reference("4002", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T00:01:00Z",
    )
    _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_a["acceptance_policy_transition_id"],
        },
        comment_id="4003",
        decided_at="2026-09-13T00:02:00Z",
    )
    # P82-R2-F2: the second, forked adoption is now refused at its own commit time -- the
    # pre-commit poisoning simulation catches the conflict before any durable write, never
    # only later when someone resolves the effective policy against an already-poisoned set.
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    with pytest.raises(PolicyLineageConflictError):
        _adopt(
            world,
            adopted_ref={
                "kind": "acceptance_policy_transition",
                "id": t_b["acceptance_policy_transition_id"],
            },
            comment_id="4004",
            decided_at="2026-09-13T00:03:00Z",
        )
    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after


def test_reordered_adoption_sequence_refuses(tmp_path: Path) -> None:
    """P82-R1-F1: a caller can no longer supply (and therefore no longer reorder) the adoption
    set at all -- ``resolve_and_verify_effective_policy`` always derives it in genuine Store
    commit order. ``engine.derive_effective_policy`` itself, given adoptions out of their own
    canonical order directly (the one way a reorder can still be expressed, entirely below the
    Store-derivation boundary), still refuses -- defense in depth at the pure-function layer."""

    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    proposed = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=project_id,
        existed_in_original_contract=False,
        merge=True,
    )
    t_add = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
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
    t_remove = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
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

    resolved_baseline = resolve_and_verify_baseline(store, project_id, baseline_ref["id"])
    baseline_adoption_id = next(
        record_id
        for record_id in store.list_committed_record_ids(project_id, "acceptance_policy_adoption")
        if resolve_and_verify_adoption(store, project_id, record_id)["adopted_ref"]["kind"]
        == "acceptance_policy_baseline"
    )
    baseline_adoption = resolve_and_verify_adoption(store, project_id, baseline_adoption_id)
    a_add_full = resolve_and_verify_adoption(
        store, project_id, a_add["acceptance_policy_adoption_id"]
    )
    a_remove_full = resolve_and_verify_adoption(
        store, project_id, a_remove["acceptance_policy_adoption_id"]
    )
    transitions_by_id = {
        t_add["acceptance_policy_transition_id"]: resolve_and_verify_transition(
            store, project_id, t_add["acceptance_policy_transition_id"]
        ),
        t_remove["acceptance_policy_transition_id"]: resolve_and_verify_transition(
            store, project_id, t_remove["acceptance_policy_transition_id"]
        ),
    }
    with pytest.raises(PolicyLineageConflictError):
        # the REMOVE adoption folded before its own ADD predecessor
        ap_engine.derive_effective_policy(
            resolved_baseline,
            transitions_by_id,
            [baseline_adoption, a_remove_full, a_add_full],
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
    forged_baseline["source_reference"] = dict(baseline["source_reference"])
    forged_baseline["source_reference"]["comment_id"] = "9999999"

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

    baseline = _open_baseline(world)
    forged = dict(baseline)
    forged["source_reference"] = dict(baseline["source_reference"])
    forged["source_reference"]["comment_id"] = "9999998"
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

    sr = source_reference(
        "6001", source_kind="AUTHORITY_ADOPTION", comment_author_association="MEMBER"
    )
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=baseline_ref,
            decision_owner="SHUKOU",
            source_reference=sr,
            governance_adoption_record=governance_adoption_record(
                project_id=world["project_id"],
                governing_issue=GOVERNING_ISSUE,
                adopted_ref=baseline_ref,
                source_reference=sr,
                project_binding_id=world["project_binding_id"],
                decided_at="2026-09-13T00:00:00Z",
            ),
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T00:00:00Z",
            committed_at="2026-09-13T00:00:00Z",
        )

    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after


# --- P82-R1-F1: canonical Store-derived adoption lineage ------------------------------------- #


def test_adoptions_from_a_different_governing_issue_are_excluded_from_this_lineage(
    tmp_path: Path,
) -> None:
    """P82-R1-F1: two independent work units can share one project's Store namespace -- an
    adoption committed for a *different* ``governing_issue`` must never be folded into this
    lineage's own effective policy, proving the canonical adoption set is scoped, not merely
    "every adoption this project ever committed"."""

    other_issue = GOVERNING_ISSUE + 1000
    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)

    other_baseline = open_acceptance_policy_baseline(
        world["store"],
        world["project_id"],
        governing_issue=other_issue,
        source_reference=source_reference("8001", source_kind="ORIGINAL_ISSUE", path="issues/9999"),
        clauses=[
            clause(
                "UNRELATED_WORK_UNIT_CLAUSE",
                policy_class="AUTHORITY",
                project_id=world["project_id"],
                existed_in_original_contract=True,
            )
        ],
        committed_at="2026-09-13T00:00:00Z",
    )
    other_sr = source_reference("8002", source_kind="AUTHORITY_ADOPTION", path="issues/9999")
    other_baseline_ref = {
        "kind": "acceptance_policy_baseline",
        "id": other_baseline["acceptance_policy_baseline_id"],
    }
    adopt_acceptance_policy_transition(
        world["store"],
        world["project_id"],
        governing_issue=other_issue,
        adopted_ref=other_baseline_ref,
        decision_owner="SHUKOU",
        source_reference=other_sr,
        governance_adoption_record=governance_adoption_record(
            project_id=world["project_id"],
            governing_issue=other_issue,
            adopted_ref=other_baseline_ref,
            source_reference=other_sr,
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T00:00:01Z",
        ),
        project_binding_id=world["project_binding_id"],
        decided_at="2026-09-13T00:00:01Z",
        committed_at="2026-09-13T00:00:01Z",
    )

    view = resolve_and_verify_effective_policy(world["store"], world["project_id"], baseline_ref)
    assert [c["clause_id"] for c in view["effective_clauses"]] == [_ACTIONS_CLAUSE_ID]


# --- P82-R1-F2: baseline-activation ordering ------------------------------------------------- #


def test_duplicate_baseline_adoption_refuses(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)

    sr = source_reference("10012", source_kind="AUTHORITY_ADOPTION")
    second_adoption = ap_engine.build_adoption(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=baseline_ref,
        decision_owner="SHUKOU",
        source_reference=sr,
        governance_adoption_record=governance_adoption_record(
            project_id=project_id,
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=baseline_ref,
            source_reference=sr,
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-11T13:00:02Z",
        ),
        project_binding_id=world["project_binding_id"],
        signing_key=human_authority_signing_key(),
        decided_at="2026-09-11T13:00:02Z",
    )
    ap_route._commit_one_record(
        store,
        project_id,
        "acceptance_policy_adoption",
        second_adoption["acceptance_policy_adoption_id"],
        second_adoption,
        "2026-09-11T13:00:02Z",
    )
    with pytest.raises(PolicyLineageConflictError):
        resolve_and_verify_effective_policy(store, project_id, baseline_ref)


def test_transition_adoption_before_baseline_adoption_refuses(tmp_path: Path) -> None:
    """P82-R1-F2: a transition's own adoption, committed before the genesis baseline's own
    adoption, refuses -- there is no activated predecessor state for it to extend yet, even
    though the transition itself was validly proposed against the (not-yet-effective) baseline."""

    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    baseline = _open_baseline(world)
    baseline_ref = _baseline_ref(baseline)

    proposed = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=project_id,
        existed_in_original_contract=False,
        merge=True,
    )
    transition = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("10022", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-11T13:00:03Z",
    )
    # P82-R2-F2: the baseline itself is never adopted in this test -- the pre-commit poisoning
    # simulation now refuses this adoption at its own commit time, before any durable write,
    # never only later when someone resolves the effective policy against an already-poisoned
    # (transition-before-baseline) adoption set.
    revision_before = store.load_current(project_id)["state_revision"]
    with pytest.raises(PolicyLineageConflictError):
        _adopt(
            world,
            adopted_ref={
                "kind": "acceptance_policy_transition",
                "id": transition["acceptance_policy_transition_id"],
            },
            comment_id="10032",
            decided_at="2026-09-11T13:00:04Z",
        )
    revision_after = store.load_current(project_id)["state_revision"]
    assert revision_before == revision_after


# --- P82-R1-F3: singleton genesis baseline --------------------------------------------------- #


def test_second_baseline_with_different_content_for_the_same_work_unit_refuses(
    tmp_path: Path,
) -> None:
    """P82-R1-F3: two different baseline bodies proposed for the identical
    ``(project_id, governing_issue)`` collide at the identical narrow-natural-key identity --
    the second commit is refused as a conflicting replay, before any durable write, with no
    second schema or locking primitive."""

    world = bound_world(tmp_path)
    _open_baseline(world)
    with pytest.raises(ConflictingPolicyReplayError):
        open_acceptance_policy_baseline(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            source_reference=source_reference("10013", source_kind="ORIGINAL_ISSUE"),
            clauses=[
                clause(
                    _GATE_CLAUSE_ID,
                    policy_class="REQUIRED_EVIDENCE",
                    project_id=world["project_id"],
                    existed_in_original_contract=True,
                )
            ],
            committed_at="2026-09-11T13:00:05Z",
        )


def test_second_baseline_for_a_different_governing_issue_is_a_distinct_genesis(
    tmp_path: Path,
) -> None:
    """The narrow natural-key identity is scoped to ``(project_id, governing_issue)`` -- a
    second, genuinely distinct work unit in the same project gets its own genesis baseline,
    never refused as a conflicting replay of the first."""

    world = bound_world(tmp_path)
    first = _open_baseline(world)
    second = open_acceptance_policy_baseline(
        world["store"],
        world["project_id"],
        governing_issue=GOVERNING_ISSUE + 1,
        source_reference=source_reference("10014", source_kind="ORIGINAL_ISSUE", path="issues/78"),
        clauses=[
            clause(
                _GATE_CLAUSE_ID,
                policy_class="REQUIRED_EVIDENCE",
                project_id=world["project_id"],
                existed_in_original_contract=True,
            )
        ],
        committed_at="2026-09-11T13:00:06Z",
    )
    assert first["acceptance_policy_baseline_id"] != second["acceptance_policy_baseline_id"]


# --- P82-R1-F4: schema validation at construction and Store-resolve boundaries --------------- #


def test_a_baseline_with_a_schema_invalid_governing_issue_refuses_before_any_commit(
    tmp_path: Path,
) -> None:
    """P82-R1-F4: ``engine.build_baseline`` performs no ``governing_issue`` range check of its
    own -- the route's own construction-boundary schema validation (against the unchanged,
    86-schema canonical registry) is what catches a schema-invalid ``governing_issue`` (must be
    >= 1) before any Store commit is attempted."""

    from manosube_agent_civilization.acceptance_policy import AcceptancePolicyValidationError

    world = bound_world(tmp_path)
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    with pytest.raises(AcceptancePolicyValidationError):
        open_acceptance_policy_baseline(
            world["store"],
            world["project_id"],
            governing_issue=0,
            source_reference=source_reference("10015", source_kind="ORIGINAL_ISSUE"),
            clauses=[
                clause(
                    _ACTIONS_CLAUSE_ID,
                    policy_class="AUTHORITY",
                    project_id=world["project_id"],
                    existed_in_original_contract=True,
                )
            ],
            committed_at="2026-09-11T13:00:07Z",
        )
    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after


def test_a_malformed_record_on_disk_refuses_at_resolve_time_not_only_at_commit_time(
    tmp_path: Path,
) -> None:
    """P82-R1-F4: schema validation runs again on every Store-resolve, not only at construction
    -- a record that was somehow committed in a schema-invalid shape (simulated here by
    committing directly through the Store bypass, below this package's own construction
    boundary) is refused on resolution rather than trusted."""

    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    baseline = ap_engine.build_baseline(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        source_reference=source_reference("10016", source_kind="ORIGINAL_ISSUE"),
        clauses=[
            clause(
                _ACTIONS_CLAUSE_ID,
                policy_class="AUTHORITY",
                project_id=project_id,
                existed_in_original_contract=True,
            )
        ],
    )
    malformed = dict(baseline)
    malformed["unexpected_extra_field"] = "not part of the schema"
    ap_route._commit_one_record(
        store,
        project_id,
        "acceptance_policy_baseline",
        malformed["acceptance_policy_baseline_id"],
        malformed,
        "2026-09-11T13:00:07Z",
    )
    from manosube_agent_civilization.acceptance_policy import AcceptancePolicyValidationError

    with pytest.raises(AcceptancePolicyValidationError):
        resolve_and_verify_baseline(store, project_id, malformed["acceptance_policy_baseline_id"])


# --- P82-R2-F1: compose with the real Governance Adoption Record owner ----------------------- #


def test_forged_owner_governance_adoption_record_refuses_before_any_commit(
    tmp_path: Path,
) -> None:
    """F1: a ``governance_adoption_record`` whose own ``decision_authority`` is not SHUKOU is
    refused by the existing ``evaluate_adoption_record`` owner -- never merely by this
    package's own caller-supplied ``decision_owner`` string, which is a separate field."""

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    sr = source_reference("20001", source_kind="AUTHORITY_ADOPTION")
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=_baseline_ref(baseline),
            decision_owner="SHUKOU",
            source_reference=sr,
            governance_adoption_record=governance_adoption_record(
                project_id=world["project_id"],
                governing_issue=GOVERNING_ISSUE,
                adopted_ref=_baseline_ref(baseline),
                source_reference=sr,
                project_binding_id=world["project_binding_id"],
                decided_at="2026-09-13T01:00:00Z",
                decision_authority="CLAUDE_CODE",
            ),
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T01:00:00Z",
            committed_at="2026-09-13T01:00:00Z",
        )
    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after


def test_forged_read_back_receipt_governance_adoption_record_refuses_before_any_commit(
    tmp_path: Path,
) -> None:
    """F1: a receipt that disagrees with the record's own declared ``reviewed_sha`` proves the
    record and its own cited read-back are not describing the same thing -- refused, never
    silently accepted because the top-level fields alone look correct."""

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    sr = source_reference("20002", source_kind="AUTHORITY_ADOPTION")
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=_baseline_ref(baseline),
            decision_owner="SHUKOU",
            source_reference=sr,
            governance_adoption_record=governance_adoption_record(
                project_id=world["project_id"],
                governing_issue=GOVERNING_ISSUE,
                adopted_ref=_baseline_ref(baseline),
                source_reference=sr,
                project_binding_id=world["project_binding_id"],
                decided_at="2026-09-13T01:00:01Z",
                receipt_overrides={"reviewed_sha": "b" * 40},
            ),
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T01:00:01Z",
            committed_at="2026-09-13T01:00:01Z",
        )
    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after


def test_forged_comment_governance_adoption_record_refuses_before_any_commit(
    tmp_path: Path,
) -> None:
    """F1: an admitted record built for a *different* comment than this adoption's own
    ``source_reference.comment_url`` is not authority for this adoption -- checked by
    ``engine.verify_governance_adoption_record`` itself, independent of whatever
    ``evaluate_adoption_record`` alone would say about the record in isolation."""

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    a_different_comment_url = source_reference("9999997", source_kind="AUTHORITY_ADOPTION")[
        "comment_url"
    ]
    sr = source_reference("20003", source_kind="AUTHORITY_ADOPTION")
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=_baseline_ref(baseline),
            decision_owner="SHUKOU",
            source_reference=sr,
            governance_adoption_record=governance_adoption_record(
                project_id=world["project_id"],
                governing_issue=GOVERNING_ISSUE,
                adopted_ref=_baseline_ref(baseline),
                source_reference=sr,
                project_binding_id=world["project_binding_id"],
                decided_at="2026-09-13T01:00:02Z",
                comment_url=a_different_comment_url,
            ),
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T01:00:02Z",
            committed_at="2026-09-13T01:00:02Z",
        )
    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after


def test_forged_target_governance_adoption_record_refuses_before_any_commit(
    tmp_path: Path,
) -> None:
    """F1: an admitted record whose own ``governing_issue`` names a different work unit than
    this exact adoption's own is not authority for this adoption, even though the record is
    otherwise internally consistent and would be admitted for its own declared work unit."""

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    sr = source_reference("20004", source_kind="AUTHORITY_ADOPTION")
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=_baseline_ref(baseline),
            decision_owner="SHUKOU",
            source_reference=sr,
            governance_adoption_record=governance_adoption_record(
                project_id=world["project_id"],
                governing_issue=GOVERNING_ISSUE + 5000,
                adopted_ref=_baseline_ref(baseline),
                source_reference=sr,
                project_binding_id=world["project_binding_id"],
                decided_at="2026-09-13T01:00:03Z",
            ),
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T01:00:03Z",
            committed_at="2026-09-13T01:00:03Z",
        )
    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after


def test_forged_sha_governance_adoption_record_refuses_before_any_commit(tmp_path: Path) -> None:
    """F1: a record whose own ``reviewed_sha`` disagrees with its own ``authorized_target_sha``
    -- both individually well-shaped commit SHAs, but naming different commits -- is refused:
    the record does not consistently name one exact reviewed/authorized commit."""

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    sr = source_reference("20005", source_kind="AUTHORITY_ADOPTION")
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=_baseline_ref(baseline),
            decision_owner="SHUKOU",
            source_reference=sr,
            governance_adoption_record=governance_adoption_record(
                project_id=world["project_id"],
                governing_issue=GOVERNING_ISSUE,
                adopted_ref=_baseline_ref(baseline),
                source_reference=sr,
                project_binding_id=world["project_binding_id"],
                decided_at="2026-09-13T01:00:04Z",
                reviewed_sha="a" * 40,
                authorized_target_sha="c" * 40,
            ),
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T01:00:04Z",
            committed_at="2026-09-13T01:00:04Z",
        )
    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after


def test_forged_repository_governance_adoption_record_refuses_before_any_commit(
    tmp_path: Path,
) -> None:
    """F1: a record whose ``comment_url`` -- and its own agreeing receipt -- names a comment
    hosted in a *different* repository is refused by ``evaluate_adoption_record``'s own
    repository-scoped comment URL grammar, even though it agrees exactly with this adoption's
    own (identically-forged) ``source_reference.comment_url``: the two sides "agreeing" with
    each other is not the same as either of them naming a real comment in this repository."""

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    foreign_comment_url = (
        "https://github.com/some-other-owner/some-other-repo/issues/1#issuecomment-1"
    )
    forged_source_reference = source_reference("20006", source_kind="AUTHORITY_ADOPTION")
    forged_source_reference["comment_url"] = foreign_comment_url
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=_baseline_ref(baseline),
            decision_owner="SHUKOU",
            source_reference=forged_source_reference,
            governance_adoption_record=governance_adoption_record(
                project_id=world["project_id"],
                governing_issue=GOVERNING_ISSUE,
                adopted_ref=_baseline_ref(baseline),
                source_reference=forged_source_reference,
                project_binding_id=world["project_binding_id"],
                decided_at="2026-09-13T01:00:05Z",
                comment_url=foreign_comment_url,
            ),
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T01:00:05Z",
            committed_at="2026-09-13T01:00:05Z",
        )
    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after


def test_a_well_formed_admitted_governance_adoption_record_is_reverified_on_every_read(
    tmp_path: Path,
) -> None:
    """F1 positive control: a genuinely well-formed, admitted record commits and adopts
    normally, and ``resolve_and_verify_adoption`` independently re-evaluates it again on every
    subsequent read -- never trusting the commit-time check alone."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    view = resolve_and_verify_effective_policy(world["store"], world["project_id"], baseline_ref)
    assert [c["clause_id"] for c in view["effective_clauses"]] == [_ACTIONS_CLAUSE_ID]

    baseline_adoption_id = next(
        record_id
        for record_id in world["store"].list_committed_record_ids(
            world["project_id"], "acceptance_policy_adoption"
        )
    )
    resolved_twice_first = resolve_and_verify_adoption(
        world["store"], world["project_id"], baseline_adoption_id
    )
    resolved_twice_second = resolve_and_verify_adoption(
        world["store"], world["project_id"], baseline_adoption_id
    )
    assert (
        resolved_twice_first["governance_adoption_record"]
        == resolved_twice_second["governance_adoption_record"]
    )


# --- P82-R2-F2: reject cross-work-unit/stale/forked/duplicate lineage before any commit ------- #


def test_adopting_a_transition_from_a_different_work_unit_refuses_before_any_commit(
    tmp_path: Path,
) -> None:
    """F2: a transition genuinely proposed and committed under a *different* work unit's own
    baseline cannot be adopted under this work unit's own ``governing_issue`` -- refused before
    any commit, never merely excluded later at resolve time the way an already-committed
    different-work-unit *baseline* adoption is (see the P82-R1-F1 exclusion test above)."""

    other_issue = GOVERNING_ISSUE + 2000
    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    other_baseline = open_acceptance_policy_baseline(
        store,
        project_id,
        governing_issue=other_issue,
        source_reference=source_reference(
            "21001", source_kind="ORIGINAL_ISSUE", path="issues/9998"
        ),
        clauses=[
            clause(
                "OTHER_WORK_UNIT_CLAUSE",
                policy_class="AUTHORITY",
                project_id=project_id,
                existed_in_original_contract=True,
            )
        ],
        committed_at="2026-09-13T02:00:00Z",
    )
    _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_baseline",
            "id": other_baseline["acceptance_policy_baseline_id"],
        },
        comment_id="21002",
        decided_at="2026-09-13T02:00:01Z",
        governing_issue=other_issue,
        path="issues/9998",
    )
    other_baseline_ref = {
        "kind": "acceptance_policy_baseline",
        "id": other_baseline["acceptance_policy_baseline_id"],
    }
    proposed = clause(
        "OTHER_WORK_UNIT_GATE",
        policy_class="REQUIRED_EVIDENCE",
        project_id=project_id,
        existed_in_original_contract=False,
        merge=True,
    )
    other_transition = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=other_issue,
        baseline_ref=other_baseline_ref,
        clause_id="OTHER_WORK_UNIT_GATE",
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference(
            "21003", source_kind="STRUCTURAL_REVIEW", path="issues/9998"
        ),
        rollback_condition="r",
        committed_at="2026-09-13T02:00:02Z",
    )

    revision_before = store.load_current(project_id)["state_revision"]
    sr = source_reference("21004", source_kind="AUTHORITY_ADOPTION")
    cross_target_ref = {
        "kind": "acceptance_policy_transition",
        "id": other_transition["acceptance_policy_transition_id"],
    }
    with pytest.raises(PolicyLineageConflictError):
        adopt_acceptance_policy_transition(
            store,
            project_id,
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=cross_target_ref,
            decision_owner="SHUKOU",
            source_reference=sr,
            governance_adoption_record=governance_adoption_record(
                project_id=project_id,
                governing_issue=GOVERNING_ISSUE,
                adopted_ref=cross_target_ref,
                source_reference=sr,
                project_binding_id=world["project_binding_id"],
                decided_at="2026-09-13T02:00:03Z",
            ),
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T02:00:03Z",
            committed_at="2026-09-13T02:00:03Z",
        )
    revision_after = store.load_current(project_id)["state_revision"]
    assert revision_before == revision_after


def test_adopting_a_transition_through_the_real_route_still_refuses_a_duplicate_baseline_adoption_before_any_commit(
    tmp_path: Path,
) -> None:
    """F2: unlike ``test_duplicate_baseline_adoption_refuses`` above (which bypasses
    ``adopt_acceptance_policy_transition`` entirely to prove :func:`engine.derive_effective_
    policy`'s own defense-in-depth), a second baseline adoption attempted through the *real*
    public route is refused at its own commit time by the pre-commit poisoning simulation --
    never only discovered later when someone resolves the effective policy."""

    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)

    revision_before = store.load_current(project_id)["state_revision"]
    with pytest.raises(PolicyLineageConflictError):
        _adopt(
            world,
            adopted_ref=baseline_ref,
            comment_id="21005",
            decided_at="2026-09-13T02:00:04Z",
        )
    revision_after = store.load_current(project_id)["state_revision"]
    assert revision_before == revision_after


def test_same_work_unit_adoption_still_succeeds_under_the_poisoning_simulation(
    tmp_path: Path,
) -> None:
    """F2 positive control: a genuine, non-poisoning adoption for this exact work unit's own
    lineage still commits and becomes effective normally -- the pre-commit simulation refuses
    only real conflicts, never a legitimate adoption."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
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
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("21006", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T02:00:05Z",
    )
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": transition["acceptance_policy_transition_id"],
        },
        comment_id="21007",
        decided_at="2026-09-13T02:00:06Z",
    )
    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_after > revision_before
    view = resolve_and_verify_effective_policy(world["store"], world["project_id"], baseline_ref)
    assert {c["clause_id"] for c in view["effective_clauses"]} == {
        _ACTIONS_CLAUSE_ID,
        _GATE_CLAUSE_ID,
    }


# --- P82-R2-F3: detach, schema/identity/fingerprint/lineage-verify the preview candidate ------ #


def test_preview_refuses_a_candidate_transition_with_a_forged_id(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
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
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("22001", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T03:00:00Z",
    )
    forged = deepcopy(candidate)
    forged["acceptance_policy_transition_id"] = "AP-TRANS-" + "F" * 64
    with pytest.raises(PolicyProvenanceError):
        preview_acceptance_policy_transition(
            world["store"], world["project_id"], baseline_ref, forged
        )


def test_preview_refuses_a_candidate_transition_with_a_forged_fingerprint(tmp_path: Path) -> None:
    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
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
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("22002", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T03:00:01Z",
    )
    forged = deepcopy(candidate)
    forged["transition_semantic_fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(PolicyProvenanceError):
        preview_acceptance_policy_transition(
            world["store"], world["project_id"], baseline_ref, forged
        )


def test_preview_refuses_a_candidate_transition_bound_to_a_different_project(
    tmp_path: Path,
) -> None:
    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
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
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("22003", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T03:00:02Z",
    )
    forged = deepcopy(candidate)
    forged["project_id"] = "PRJ-SUBSTITUTED-0001"
    forged["transition_semantic_fingerprint"] = identity.transition_semantic_fingerprint(forged)
    forged["acceptance_policy_transition_id"] = identity.transition_id(forged)
    with pytest.raises(PolicyLineageConflictError):
        preview_acceptance_policy_transition(
            world["store"], world["project_id"], baseline_ref, forged
        )


def test_preview_refuses_a_candidate_transition_bound_to_a_different_governing_issue(
    tmp_path: Path,
) -> None:
    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
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
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("22004", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T03:00:03Z",
    )
    forged = deepcopy(candidate)
    forged["governing_issue"] = GOVERNING_ISSUE + 3000
    forged["transition_semantic_fingerprint"] = identity.transition_semantic_fingerprint(forged)
    forged["acceptance_policy_transition_id"] = identity.transition_id(forged)
    with pytest.raises(PolicyLineageConflictError):
        preview_acceptance_policy_transition(
            world["store"], world["project_id"], baseline_ref, forged
        )


def test_preview_refuses_a_candidate_transition_bound_to_a_different_baseline(
    tmp_path: Path,
) -> None:
    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
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
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("22005", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T03:00:04Z",
    )
    forged = deepcopy(candidate)
    forged["baseline_ref"] = {
        "kind": "acceptance_policy_baseline",
        "id": "AP-BASE-" + "9" * 64,
    }
    forged["transition_semantic_fingerprint"] = identity.transition_semantic_fingerprint(forged)
    forged["acceptance_policy_transition_id"] = identity.transition_id(forged)
    with pytest.raises(PolicyLineageConflictError):
        preview_acceptance_policy_transition(
            world["store"], world["project_id"], baseline_ref, forged
        )


def test_preview_refuses_a_candidate_transition_with_a_stale_predecessor(tmp_path: Path) -> None:
    """F3: a candidate proposed against an earlier effective view, previewed *after* a
    different adoption has since advanced the real current predecessor for its own clause_id,
    is refused -- its own ``prior_clause_binding`` no longer names the currently-effective
    predecessor, exactly the same stale-base check :func:`engine.derive_effective_policy`
    itself already enforces at fold time, now proven at preview time too."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    proposed_add = clause(
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
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed_add,
        source_reference=source_reference("22006", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T03:00:05Z",
    )
    # a REPLACE proposed against the pre-ADD view -- its own prior_clause_binding still points
    # at the baseline, since GATE_CLAUSE_ID did not exist as an effective clause yet when this
    # was proposed. This is schema/diff-valid *at proposal time* (REPLACE for a clause with no
    # live predecessor is refused as ADD-mismatched by build_transition, so instead this stale
    # candidate is minted as its own valid ADD, then the *real* lineage is advanced past it by
    # adopting t_add first, before the stale candidate is ever previewed.)
    _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_add["acceptance_policy_transition_id"],
        },
        comment_id="22007",
        decided_at="2026-09-13T03:00:06Z",
    )
    # t_add's own prior_clause_binding pointed at the baseline -- now stale, since the real
    # current predecessor for _GATE_CLAUSE_ID is t_add's own adoption, not the baseline.
    stale_replacement = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=world["project_id"],
        existed_in_original_contract=False,
        merge=True,
        issue_closure=True,
    )
    forged = deepcopy(t_add)
    forged["policy_operation"] = "BROADEN"
    forged["proposed_clause"] = stale_replacement
    forged["transition_semantic_fingerprint"] = identity.transition_semantic_fingerprint(forged)
    forged["acceptance_policy_transition_id"] = identity.transition_id(forged)
    with pytest.raises(PolicyLineageConflictError):
        preview_acceptance_policy_transition(
            world["store"], world["project_id"], baseline_ref, forged
        )


def test_preview_refuses_a_candidate_transition_with_a_wrong_declared_operation(
    tmp_path: Path,
) -> None:
    """F3: a candidate whose declared ``policy_operation`` does not match the independently
    recomputed semantic diff between the real current predecessor and its own proposed clause
    is refused -- reproduced at preview time exactly like :func:`engine.assert_transition_
    operation_matches_diff` already proves at construction time."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
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
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("22008", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T03:00:07Z",
    )
    forged = deepcopy(candidate)
    # RECLASSIFY is not what an ADD (no live predecessor) independently recomputes to -- the
    # declared operation and the recomputed diff now disagree.
    forged["policy_operation"] = "RECLASSIFY"
    forged["transition_semantic_fingerprint"] = identity.transition_semantic_fingerprint(forged)
    forged["acceptance_policy_transition_id"] = identity.transition_id(forged)
    with pytest.raises(UndeclaredPolicyChangeError):
        preview_acceptance_policy_transition(
            world["store"], world["project_id"], baseline_ref, forged
        )


def test_mutating_the_callers_own_candidate_after_minting_is_caught_not_silently_reused(
    tmp_path: Path,
) -> None:
    """F3: the candidate is detached (deep-copied) before verification -- proven here by
    mutating the caller's own retained object's nested ``proposed_clause`` in place *after* it
    was minted, without recomputing its own id/fingerprint, and showing this inconsistent
    object is refused on its own semantic-fingerprint reproduction check, never silently
    trusted as whatever the caller's object currently reads as."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
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
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("22009", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T03:00:08Z",
    )
    first_preview = preview_acceptance_policy_transition(
        world["store"], world["project_id"], baseline_ref, candidate
    )
    # mutate the caller's own retained object in place, without recomputing its own identity
    # or fingerprint -- exactly the shape of bug P82-R2-F3 closes: this must never silently
    # change an already-returned preview, nor be silently reused as if it were still valid.
    candidate["proposed_clause"]["blocking_effect"]["issue_closure"] = True
    assert first_preview["new_blockers"] == [
        {"clause_id": _GATE_CLAUSE_ID, "blocking_effect_field": "merge"}
    ]
    with pytest.raises(PolicyProvenanceError):
        preview_acceptance_policy_transition(
            world["store"], world["project_id"], baseline_ref, candidate
        )


def test_preview_matrix_covers_all_six_semantic_operations(tmp_path: Path) -> None:
    """F3: the complete ADD/REMOVE/REPLACE/NARROW/BROADEN/RECLASSIFY preview matrix, each
    independently verified and previewed through the real route in sequence over one evolving
    lineage."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    project_id = world["project_id"]
    store = world["store"]
    clock = iter(range(1, 50))

    def _next_timestamp() -> str:
        return f"2026-09-13T04:{next(clock):02d}:00Z"

    # ADD
    added = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=project_id,
        existed_in_original_contract=False,
        merge=True,
    )
    t_add = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=added,
        source_reference=source_reference("23001", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at=_next_timestamp(),
    )
    preview_add = preview_acceptance_policy_transition(store, project_id, baseline_ref, t_add)
    assert preview_add["proposed_change"]["policy_operation"] == "ADD"
    _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_add["acceptance_policy_transition_id"],
        },
        comment_id="23002",
        decided_at=_next_timestamp(),
    )

    # RECLASSIFY (policy_class changes, blocking_effect unchanged)
    reclassified = clause(
        _GATE_CLAUSE_ID,
        policy_class="AUTHORITY",
        project_id=project_id,
        existed_in_original_contract=False,
        merge=True,
    )
    t_reclassify = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="RECLASSIFY",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=reclassified,
        source_reference=source_reference("23003", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at=_next_timestamp(),
    )
    preview_reclassify = preview_acceptance_policy_transition(
        store, project_id, baseline_ref, t_reclassify
    )
    assert preview_reclassify["proposed_change"]["policy_operation"] == "RECLASSIFY"
    _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_reclassify["acceptance_policy_transition_id"],
        },
        comment_id="23004",
        decided_at=_next_timestamp(),
    )

    # BROADEN (same policy_class, a blocking field is added with none removed)
    broadened = clause(
        _GATE_CLAUSE_ID,
        policy_class="AUTHORITY",
        project_id=project_id,
        existed_in_original_contract=False,
        merge=True,
        issue_closure=True,
    )
    t_broaden = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="BROADEN",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=broadened,
        source_reference=source_reference("23005", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at=_next_timestamp(),
    )
    preview_broaden = preview_acceptance_policy_transition(
        store, project_id, baseline_ref, t_broaden
    )
    assert preview_broaden["proposed_change"]["policy_operation"] == "BROADEN"
    _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_broaden["acceptance_policy_transition_id"],
        },
        comment_id="23006",
        decided_at=_next_timestamp(),
    )

    # NARROW (same policy_class, a blocking field is removed with none added)
    narrowed = clause(
        _GATE_CLAUSE_ID,
        policy_class="AUTHORITY",
        project_id=project_id,
        existed_in_original_contract=False,
        issue_closure=True,
    )
    t_narrow = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="NARROW",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=narrowed,
        source_reference=source_reference("23007", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at=_next_timestamp(),
    )
    preview_narrow = preview_acceptance_policy_transition(store, project_id, baseline_ref, t_narrow)
    assert preview_narrow["proposed_change"]["policy_operation"] == "NARROW"
    _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_narrow["acceptance_policy_transition_id"],
        },
        comment_id="23008",
        decided_at=_next_timestamp(),
    )

    # REPLACE (same policy_class, one blocking field added and a different one removed)
    replaced = clause(
        _GATE_CLAUSE_ID,
        policy_class="AUTHORITY",
        project_id=project_id,
        existed_in_original_contract=False,
        phase_completion=True,
    )
    t_replace = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="REPLACE",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=replaced,
        source_reference=source_reference("23009", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at=_next_timestamp(),
    )
    preview_replace = preview_acceptance_policy_transition(
        store, project_id, baseline_ref, t_replace
    )
    assert preview_replace["proposed_change"]["policy_operation"] == "REPLACE"
    _adopt(
        world,
        adopted_ref={
            "kind": "acceptance_policy_transition",
            "id": t_replace["acceptance_policy_transition_id"],
        },
        comment_id="23010",
        decided_at=_next_timestamp(),
    )

    # REMOVE
    t_remove = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="REMOVE",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=None,
        source_reference=source_reference("23011", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at=_next_timestamp(),
    )
    preview_remove = preview_acceptance_policy_transition(store, project_id, baseline_ref, t_remove)
    assert preview_remove["proposed_change"]["policy_operation"] == "REMOVE"
    assert _GATE_CLAUSE_ID not in {c["clause_id"] for c in preview_remove["after_policy"]}


# --- Structural Review Round 3 (PR #82): P82-R3-F1/F2/F3 required decisive controls --------- #


class _CompetitorInjectingStore:
    """P82-R3-F2: deterministically simulate a competing commit landing *inside* the exact
    resolve -> verify Authority -> simulate-fold -> commit window a single ``adopt_acceptance_
    policy_transition`` call holds open, by hooking the one Store call that window's own final
    write goes through (``commit``) and injecting the competitor's own complete, independent
    commit immediately before delegating to the real one. A true concurrent race is
    nondeterministic; this hook makes the one interleaving P82-R3-F2 is about -- a competitor
    landing between this call's own simulation and its own write -- reproducible every time."""

    def __init__(self, real_store: Any, on_first_commit: Any) -> None:
        self._real_store = real_store
        self._on_first_commit = on_first_commit
        self._triggered = False

    def commit(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if not self._triggered:
            self._triggered = True
            self._on_first_commit()
        return cast(dict[str, Any], self._real_store.commit(*args, **kwargs))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real_store, name)


class _MutatingReadStore:
    """P82-R3-F3: a Store wrapper whose ``resolve_record`` -- the one Store call ``resolve_
    and_verify_baseline`` makes as ``preview_acceptance_policy_transition``'s own first Store
    call -- mutates a caller-held object in place, once, before delegating to the real Store.
    Used to prove the preview boundary never observes that mutation: only the value it
    detached as its own literal first operation, before any Store call at all, is ever
    verified or previewed."""

    def __init__(self, real_store: Any, on_first_resolve_record: Any) -> None:
        self._real_store = real_store
        self._on_first_resolve_record = on_first_resolve_record
        self._triggered = False

    def resolve_record(self, *args: Any, **kwargs: Any) -> Any:
        if not self._triggered:
            self._triggered = True
            self._on_first_resolve_record()
        return self._real_store.resolve_record(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real_store, name)


def test_forged_signature_governance_adoption_record_refuses_before_any_commit(
    tmp_path: Path,
) -> None:
    """F1: a ``governance_adoption_record`` that is otherwise well-formed and admitted, whose
    own ``signature.value`` is not a genuine Ed25519 signature over the bound payload at all
    (garbage of the correct shape), is refused -- an internally-consistent claim alone is
    never sufficient Human Authority proof."""

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    adopted_ref = _baseline_ref(baseline)
    sr = source_reference("30101", source_kind="AUTHORITY_ADOPTION")
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=adopted_ref,
            decision_owner="SHUKOU",
            source_reference=sr,
            governance_adoption_record=governance_adoption_record(
                project_id=world["project_id"],
                governing_issue=GOVERNING_ISSUE,
                adopted_ref=adopted_ref,
                source_reference=sr,
                project_binding_id=world["project_binding_id"],
                decided_at="2026-09-13T05:00:00Z",
                signature_override={
                    "algorithm": "ed25519",
                    "key_id": human_authority_signing_key()["key_id"],
                    "value": "00" * 64,
                },
            ),
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T05:00:00Z",
            committed_at="2026-09-13T05:00:00Z",
        )
    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after


def test_a_locally_fabricated_but_internally_self_consistent_signature_refuses(
    tmp_path: Path,
) -> None:
    """F1: an attacker who owns their own genuine Ed25519 keypair, and genuinely signs their
    own well-formed record with it -- passing every check ``evaluate_adoption_record`` and
    this package's own comment_url/governing_issue binding would ever perform -- is still
    refused, because the signature does not verify against the real, Store-resolved Project
    Binding's own trusted public key, which the attacker's own private key never held. Never
    merely an unknown ``key_id``: this record even claims the real key's own ``key_id``
    label."""

    world = bound_world(tmp_path)
    baseline = _open_baseline(world)
    adopted_ref = _baseline_ref(baseline)
    sr = source_reference("30102", source_kind="AUTHORITY_ADOPTION")
    reviewed_sha = "a" * 40
    decided_at = "2026-09-13T05:00:01Z"

    attacker_key = Ed25519PrivateKey.from_private_bytes(b"\x07" * 32)
    # the attacker's own record core, self-consistent, over which they genuinely sign --
    # identical shape to what governance_adoption_record() itself would build.
    attacker_record_core = {
        "schema_version": "0.1",
        "adoption_id": "ADOPT_TEST_FIXTURE",
        "governing_issue": f"#{GOVERNING_ISSUE}",
        "comment_url": sr["comment_url"],
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
        "api_read_back_receipt": {
            "adoption_id": "ADOPT_TEST_FIXTURE",
            "governing_issue": f"#{GOVERNING_ISSUE}",
            "reviewed_sha": reviewed_sha,
            "comment_url": sr["comment_url"],
            "decision_authority": "SHUKOU",
            "decision_status": "RATIFIED",
        },
        "reviewed_sha": reviewed_sha,
        "authorized_target_sha": reviewed_sha,
    }
    payload = identity.governance_adoption_authority_signing_payload(
        {
            "project_id": world["project_id"],
            "governing_issue": GOVERNING_ISSUE,
            "adopted_ref": adopted_ref,
            "decision_owner": "SHUKOU",
            "source_reference": sr,
            "governance_adoption_record_core": attacker_record_core,
            "project_binding_id": world["project_binding_id"],
            "decided_at": decided_at,
        }
    )
    attacker_signature = {
        "algorithm": "ed25519",
        "key_id": human_authority_signing_key()["key_id"],
        "value": attacker_key.sign(payload).hex(),
    }
    revision_before = world["store"].load_current(world["project_id"])["state_revision"]
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            world["store"],
            world["project_id"],
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=adopted_ref,
            decision_owner="SHUKOU",
            source_reference=sr,
            governance_adoption_record={**attacker_record_core, "signature": attacker_signature},
            project_binding_id=world["project_binding_id"],
            decided_at=decided_at,
            committed_at=decided_at,
        )
    revision_after = world["store"].load_current(world["project_id"])["state_revision"]
    assert revision_before == revision_after


def test_a_valid_signed_adoption_record_reused_unchanged_for_a_different_target_refuses(
    tmp_path: Path,
) -> None:
    """F1: the exact byte-identical ``governance_adoption_record`` -- including its own
    genuine signature -- that genuinely authorized adopting one transition is reused,
    unchanged, as the ``governance_adoption_record`` for adopting a *different* transition
    under the identical ``comment_url``/``governing_issue``/``decision_owner``. Refused before
    any commit: the signature's own bound payload includes ``adopted_ref``, so a signature
    genuinely produced for one exact target can never verify for a substituted one."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    project_id = world["project_id"]
    store = world["store"]

    clause_one_id = "REPLAY_TARGET_CLAUSE_ONE"
    clause_two_id = "REPLAY_TARGET_CLAUSE_TWO"
    t1 = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=clause_one_id,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=clause(
            clause_one_id,
            policy_class="REQUIRED_EVIDENCE",
            project_id=project_id,
            existed_in_original_contract=False,
        ),
        source_reference=source_reference("30201", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T05:00:02Z",
    )
    t2 = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=clause_two_id,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=clause(
            clause_two_id,
            policy_class="REQUIRED_EVIDENCE",
            project_id=project_id,
            existed_in_original_contract=False,
        ),
        source_reference=source_reference("30202", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T05:00:03Z",
    )

    sr = source_reference("30203", source_kind="AUTHORITY_ADOPTION")
    t1_ref = {"kind": "acceptance_policy_transition", "id": t1["acceptance_policy_transition_id"]}
    t2_ref = {"kind": "acceptance_policy_transition", "id": t2["acceptance_policy_transition_id"]}
    shared_record = governance_adoption_record(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=t1_ref,
        source_reference=sr,
        project_binding_id=world["project_binding_id"],
        decided_at="2026-09-13T05:00:04Z",
    )

    adopt_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=t1_ref,
        decision_owner="SHUKOU",
        source_reference=sr,
        governance_adoption_record=shared_record,
        project_binding_id=world["project_binding_id"],
        decided_at="2026-09-13T05:00:04Z",
        committed_at="2026-09-13T05:00:04Z",
    )

    revision_before = store.load_current(project_id)["state_revision"]
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        adopt_acceptance_policy_transition(
            store,
            project_id,
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=t2_ref,
            decision_owner="SHUKOU",
            source_reference=sr,
            governance_adoption_record=deepcopy(shared_record),
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T05:00:05Z",
            committed_at="2026-09-13T05:00:05Z",
        )
    revision_after = store.load_current(project_id)["state_revision"]
    assert revision_before == revision_after


def test_full_cycle_restart_catches_a_competitor_that_poisons_the_stale_candidate_mid_commit_window(
    tmp_path: Path,
) -> None:
    """P82-R3-F2: a competing adoption that lands inside the exact resolve-verify-simulate-
    commit window this call holds open -- after this call's own poisoning simulation ran
    against the pre-competitor State, but before this call's own final write reaches the
    Store -- is still caught. The Store's own Compare-And-Swap rejects this call's now-stale
    write, and the *complete* cycle (including the poisoning simulation) restarts against
    genuinely fresh State, which now correctly finds this call's own candidate poisoned by the
    competitor -- exactly the fork shape ``test_a_fork_two_transitions_claiming_the_same_
    predecessor_refuses`` already proves is poisoning when adopted sequentially. A shallow fix
    that retried only the low-level write (never re-ran the simulation) would let this land as
    a silent fork instead."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    project_id = world["project_id"]
    real_store = world["store"]

    proposed_a = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=project_id,
        existed_in_original_contract=False,
        merge=True,
    )
    proposed_b = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=project_id,
        existed_in_original_contract=False,
        issue_closure=True,
    )
    t_a = propose_acceptance_policy_transition(
        real_store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed_a,
        source_reference=source_reference("30501", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T06:20:00Z",
    )
    t_b = propose_acceptance_policy_transition(
        real_store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed_b,
        source_reference=source_reference("30502", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T06:20:01Z",
    )

    def _inject_forking_competitor() -> None:
        # a real, independent, fully-successful adoption -- landing on the real store,
        # exactly as a genuinely concurrent second process's commit would -- inside the
        # window between the worker's own simulation and its own write.
        _adopt(
            world,
            adopted_ref={
                "kind": "acceptance_policy_transition",
                "id": t_a["acceptance_policy_transition_id"],
            },
            comment_id="30503",
            decided_at="2026-09-13T06:20:02Z",
        )

    wrapped_store = _CompetitorInjectingStore(real_store, _inject_forking_competitor)
    revision_before = real_store.load_current(project_id)["state_revision"]

    with pytest.raises(PolicyLineageConflictError):
        _adopt(
            {**world, "store": wrapped_store},
            adopted_ref={
                "kind": "acceptance_policy_transition",
                "id": t_b["acceptance_policy_transition_id"],
            },
            comment_id="30504",
            decided_at="2026-09-13T06:20:03Z",
        )

    revision_after = real_store.load_current(project_id)["state_revision"]
    # exactly one commit landed -- the injected competitor's own adoption of t_a -- and never
    # a second one for t_b's own now-poisoned, correctly-refused adoption attempt.
    assert revision_after == revision_before + 1
    assert (
        len(real_store.list_committed_record_ids(project_id, "acceptance_policy_adoption")) == 2
    )  # the genesis baseline's own adoption, plus t_a's -- never t_b's


def test_full_cycle_restart_succeeds_past_unrelated_contention_and_stays_idempotent_on_replay(
    tmp_path: Path,
) -> None:
    """P82-R3-F2: a competing adoption that lands inside the same commit window, but that
    targets a wholly unrelated clause and so never actually poisons this call's own candidate,
    never spuriously fails this call -- the restarted cycle re-simulates against fresh State,
    finds no poisoning, and durably commits on its own second attempt (the "worker wins"
    outcome). The record the restarted cycle actually commits is then proven still correctly
    content-addressed and replay-safe: an identical repeat call afterward (on the real,
    unwrapped store -- the race has already happened) is still the same idempotent no-op
    FD4-C9 guarantees everywhere else in this package."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    project_id = world["project_id"]
    real_store = world["store"]

    worker_clause_id = "RACE_WORKER_CLAUSE"
    competitor_clause_id = "RACE_COMPETITOR_CLAUSE"
    worker_transition = propose_acceptance_policy_transition(
        real_store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=worker_clause_id,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=clause(
            worker_clause_id,
            policy_class="REQUIRED_EVIDENCE",
            project_id=project_id,
            existed_in_original_contract=False,
        ),
        source_reference=source_reference("30401", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T06:10:00Z",
    )
    competitor_transition = propose_acceptance_policy_transition(
        real_store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=competitor_clause_id,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=clause(
            competitor_clause_id,
            policy_class="REQUIRED_EVIDENCE",
            project_id=project_id,
            existed_in_original_contract=False,
        ),
        source_reference=source_reference("30402", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T06:10:01Z",
    )

    def _inject_unrelated_competitor() -> None:
        _adopt(
            world,
            adopted_ref={
                "kind": "acceptance_policy_transition",
                "id": competitor_transition["acceptance_policy_transition_id"],
            },
            comment_id="30403",
            decided_at="2026-09-13T06:10:02Z",
        )

    wrapped_store = _CompetitorInjectingStore(real_store, _inject_unrelated_competitor)
    sr = source_reference("30404", source_kind="AUTHORITY_ADOPTION")
    worker_ref = {
        "kind": "acceptance_policy_transition",
        "id": worker_transition["acceptance_policy_transition_id"],
    }
    revision_before = real_store.load_current(project_id)["state_revision"]

    worker_record = governance_adoption_record(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=worker_ref,
        source_reference=sr,
        project_binding_id=world["project_binding_id"],
        decided_at="2026-09-13T06:10:03Z",
    )
    worker_adoption = adopt_acceptance_policy_transition(
        wrapped_store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=worker_ref,
        decision_owner="SHUKOU",
        source_reference=sr,
        governance_adoption_record=worker_record,
        project_binding_id=world["project_binding_id"],
        decided_at="2026-09-13T06:10:03Z",
        committed_at="2026-09-13T06:10:03Z",
    )
    revision_after = real_store.load_current(project_id)["state_revision"]
    # exactly two new commits landed: the injected unrelated competitor's own adoption, then
    # this call's own retried-and-succeeded adoption -- never more (no phantom duplicate
    # commits survive the restart) and never fewer (the retry genuinely completed).
    assert revision_after == revision_before + 2

    effective_view = resolve_and_verify_effective_policy(real_store, project_id, baseline_ref)
    effective_clause_ids = {c["clause_id"] for c in effective_view["effective_clauses"]}
    assert worker_clause_id in effective_clause_ids
    assert competitor_clause_id in effective_clause_ids

    replayed = adopt_acceptance_policy_transition(
        real_store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=worker_ref,
        decision_owner="SHUKOU",
        source_reference=source_reference("30404", source_kind="AUTHORITY_ADOPTION"),
        governance_adoption_record=deepcopy(worker_record),
        project_binding_id=world["project_binding_id"],
        decided_at="2026-09-13T06:10:03Z",
        committed_at="2026-09-13T06:10:03Z",
    )
    assert replayed == worker_adoption
    assert real_store.load_current(project_id)["state_revision"] == revision_after


def test_preview_detaches_before_any_store_call_surviving_a_mid_call_mutation_of_the_original(
    tmp_path: Path,
) -> None:
    """P82-R3-F3: ``preview_acceptance_policy_transition`` detaches (deep-copies)
    ``candidate_transition`` as its own literal first operation, before ``resolve_and_verify_
    baseline``'s own first Store call. Proven here by mutating the caller's *original*,
    still-retained ``candidate_transition`` object in place, from inside a Store hook that
    fires during that very first Store call -- the resulting preview must still reflect the
    value exactly as it stood before the mutation, never the mutated one, because only the
    already-detached copy is ever used from that point on."""

    world = bound_world(tmp_path)
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)
    project_id = world["project_id"]
    real_store = world["store"]

    proposed = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=project_id,
        existed_in_original_contract=False,
        merge=True,
    )
    candidate_transition = propose_acceptance_policy_transition(
        real_store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("30601", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T06:30:00Z",
    )

    def _mutate_the_callers_original_candidate() -> None:
        # a mid-call mutation of the caller's own retained object -- never the already-
        # detached copy, if the fix is correct.
        candidate_transition["proposed_clause"]["blocking_effect"]["merge"] = False

    wrapped_store = _MutatingReadStore(real_store, _mutate_the_callers_original_candidate)

    preview = preview_acceptance_policy_transition(
        wrapped_store, project_id, baseline_ref, candidate_transition
    )

    # the hook genuinely fired and genuinely corrupted the caller's own retained object --
    # otherwise this test would be vacuous.
    assert candidate_transition["proposed_clause"]["blocking_effect"]["merge"] is False
    # the preview itself reflects the value exactly as it stood at the moment
    # preview_acceptance_policy_transition was called -- proving the detach happened before
    # this Store call had any chance to influence what was actually verified/previewed.
    assert preview["new_blockers"] == [
        {"clause_id": _GATE_CLAUSE_ID, "blocking_effect_field": "merge"}
    ]


# --- Structural Review Round 4 (PR #82, P82-R4-F1..F4) -------------------------------------- #


def test_a_second_project_binding_under_the_same_project_label_with_an_attacker_key_refuses(
    tmp_path: Path,
) -> None:
    """P82-R4-F1: an additional, internally-valid ``project_binding`` record -- committed
    under this project's own namespace, but never part of its own ``TX-GENESIS`` manifest --
    carrying an attacker-controlled ``human_authority_signing_key``, is never selected as the
    trusted signing authority merely because a caller names its own ``project_binding_id``.
    The adoption below is *fully* self-consistent: genuinely signed by the attacker's own
    private key, over exactly the bound payload this package would recompute, naming the
    attacker's own real, resolvable, schema-valid, identity-verified ``project_binding_id`` --
    everything a resolver that selected by caller choice would accept. It still refuses,
    because the trusted signing key is derived only from the project's own genesis manifest
    membership, never from this caller-supplied id."""

    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from tests.fixtures.product_binding import bind_project_kwargs

    from manosube_agent_civilization.binding.engine import assemble_project_binding

    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    baseline = _open_baseline(world)
    adopted_ref = _baseline_ref(baseline)

    attacker_private_key = Ed25519PrivateKey.from_private_bytes(b"\x09" * 32)
    attacker_public_bytes = attacker_private_key.public_key().public_bytes(
        encoding=Encoding.Raw, format=PublicFormat.Raw
    )
    attacker_signing_key = {
        "algorithm": "ed25519",
        "key_id": "AUTH-KEY-ATTACKER",
        "public_key": attacker_public_bytes.hex(),
    }

    kwargs = bind_project_kwargs()
    attacker_binding = assemble_project_binding(
        project_id=project_id,
        objective_revision_ref={
            "kind": "objective_revision",
            "id": kwargs["objective_revision"]["objective_revision_id"],
        },
        boundary=kwargs["boundary"],
        authority_policy_ref=kwargs["authority_policy_ref"],
        source_registrations=kwargs["source_registrations"],
        command_policy=kwargs["command_policy"],
        secret_exclusion_policy=kwargs["secret_exclusion_policy"],
        human_authority_ref=kwargs["human_authority_ref"],
        human_authority_signing_key=attacker_signing_key,
        bound_at="2026-09-13T07:00:00Z",
    )
    # a real, resolvable, schema-valid, identity-verified record under this project's own
    # namespace -- but never through TX-GENESIS, and never selected by this package's own
    # trust-root derivation, which reads only the genesis manifest's own membership.
    ap_route._commit_one_record(
        store,
        project_id,
        "project_binding",
        attacker_binding["project_binding_id"],
        attacker_binding,
        "2026-09-13T07:00:00Z",
    )

    sr = source_reference("40001", source_kind="AUTHORITY_ADOPTION")
    reviewed_sha = "a" * 40
    decided_at = "2026-09-13T07:00:01Z"
    record_core = {
        "schema_version": "0.1",
        "adoption_id": "ADOPT_ATTACKER",
        "governing_issue": f"#{GOVERNING_ISSUE}",
        "comment_url": sr["comment_url"],
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
        "api_read_back_receipt": {
            "adoption_id": "ADOPT_ATTACKER",
            "governing_issue": f"#{GOVERNING_ISSUE}",
            "reviewed_sha": reviewed_sha,
            "comment_url": sr["comment_url"],
            "decision_authority": "SHUKOU",
            "decision_status": "RATIFIED",
        },
        "reviewed_sha": reviewed_sha,
        "authorized_target_sha": reviewed_sha,
    }
    payload = identity.governance_adoption_authority_signing_payload(
        {
            "project_id": project_id,
            "governing_issue": GOVERNING_ISSUE,
            "adopted_ref": adopted_ref,
            "decision_owner": "SHUKOU",
            "source_reference": sr,
            "governance_adoption_record_core": record_core,
            "project_binding_id": attacker_binding["project_binding_id"],
            "decided_at": decided_at,
        }
    )
    attacker_signature = {
        "algorithm": "ed25519",
        "key_id": attacker_signing_key["key_id"],
        "value": attacker_private_key.sign(payload).hex(),
    }
    forged_record = {**record_core, "signature": attacker_signature}

    revision_before = store.load_current(project_id)["state_revision"]
    with pytest.raises(PolicyProvenanceError):
        adopt_acceptance_policy_transition(
            store,
            project_id,
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=adopted_ref,
            decision_owner="SHUKOU",
            source_reference=sr,
            governance_adoption_record=forged_record,
            project_binding_id=attacker_binding["project_binding_id"],
            decided_at=decided_at,
            committed_at=decided_at,
        )
    revision_after = store.load_current(project_id)["state_revision"]
    assert revision_before == revision_after


def test_a_genuine_signature_cannot_be_reused_after_mutating_the_gars_own_identity_project_binding_id_source_reference_or_decided_at(
    tmp_path: Path,
) -> None:
    """P82-R4-F2: the signed Human-Authority payload binds the complete act -- the Governance
    Adoption Record's own ``adoption_id``/receipt identity, this adoption's own
    ``project_binding_id``, its complete ``source_reference``, and ``decided_at`` -- not merely
    Round 3's narrower comment/reviewed/authorized-target-only projection. Each of the four
    mutations below leaves a genuine signature standing but changes one field the signed
    payload now covers; every one refuses."""

    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    baseline = _open_baseline(world)
    adopted_ref = _baseline_ref(baseline)
    project_binding_id = world["project_binding_id"]

    def _attempt(
        *,
        comment_id: str,
        decided_at: str,
        mutate_record: Any = None,
        record_project_binding_id: str | None = None,
        record_decided_at: str | None = None,
        record_source_kind: str | None = None,
    ) -> None:
        sr = source_reference(comment_id, source_kind="AUTHORITY_ADOPTION")
        signing_source_reference = (
            {**sr, "source_kind": record_source_kind} if record_source_kind is not None else sr
        )
        record = governance_adoption_record(
            project_id=project_id,
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=adopted_ref,
            source_reference=signing_source_reference,
            project_binding_id=(
                record_project_binding_id
                if record_project_binding_id is not None
                else project_binding_id
            ),
            decided_at=record_decided_at if record_decided_at is not None else decided_at,
        )
        if mutate_record is not None:
            record = mutate_record(deepcopy(record))
        revision_before = store.load_current(project_id)["state_revision"]
        with pytest.raises(UnauthorizedPolicyAdoptionError):
            adopt_acceptance_policy_transition(
                store,
                project_id,
                governing_issue=GOVERNING_ISSUE,
                adopted_ref=adopted_ref,
                decision_owner="SHUKOU",
                source_reference=sr,
                governance_adoption_record=record,
                project_binding_id=project_binding_id,
                decided_at=decided_at,
                committed_at=decided_at,
            )
        revision_after = store.load_current(project_id)["state_revision"]
        assert revision_before == revision_after

    def _mutate_adoption_id_and_receipt(record: dict[str, Any]) -> dict[str, Any]:
        # the record's own adoption_id/receipt mutated *after* it was genuinely signed --
        # still internally self-consistent (receipt mutated alongside adoption_id, so
        # evaluate_adoption_record itself would still admit it), but no longer the exact
        # content the signature was produced over.
        record["adoption_id"] = "ADOPT_MUTATED"
        record["api_read_back_receipt"] = {
            **record["api_read_back_receipt"],
            "adoption_id": "ADOPT_MUTATED",
        }
        return record

    # the record's own adoption_id/receipt identity was mutated after signing.
    _attempt(
        comment_id="40101",
        decided_at="2026-09-13T07:10:00Z",
        mutate_record=_mutate_adoption_id_and_receipt,
    )
    # the record was genuinely signed for a *different* project_binding_id than this
    # adoption's own real, canonical one.
    _attempt(
        comment_id="40102",
        decided_at="2026-09-13T07:10:01Z",
        record_project_binding_id="PROJBIND-" + "9" * 64,
    )
    # the record was genuinely signed for a *different* decided_at than this adoption's own.
    _attempt(
        comment_id="40103",
        decided_at="2026-09-13T07:10:02Z",
        record_decided_at="2026-01-01T00:00:00Z",
    )
    # the record was genuinely signed for a source_reference carrying the identical
    # comment_url (so the record's own embedded comment_url field still agrees) but
    # different other source metadata than this adoption's own complete source_reference.
    _attempt(
        comment_id="40104",
        decided_at="2026-09-13T07:10:03Z",
        record_source_kind="ORIGINAL_ISSUE",
    )


def test_resolve_and_verify_adoption_refuses_when_the_adopted_target_is_missing(
    tmp_path: Path,
) -> None:
    """P82-R4-F3: ``resolve_and_verify_adoption`` re-resolves *adopted_ref* itself, not merely
    the Adoption's own schema/id/fingerprint/signature -- a cryptographically valid Adoption
    whose own referenced Baseline was never committed still refuses on direct read."""

    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]

    missing_baseline_ref = {
        "kind": "acceptance_policy_baseline",
        "id": "AP-BASE-" + "0" * 64,
    }
    sr = source_reference("40201", source_kind="AUTHORITY_ADOPTION")
    forged_adoption = ap_engine.build_adoption(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=missing_baseline_ref,
        decision_owner="SHUKOU",
        source_reference=sr,
        governance_adoption_record=governance_adoption_record(
            project_id=project_id,
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=missing_baseline_ref,
            source_reference=sr,
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T07:20:00Z",
        ),
        project_binding_id=world["project_binding_id"],
        signing_key=human_authority_signing_key(),
        decided_at="2026-09-13T07:20:00Z",
    )
    ap_route._commit_one_record(
        store,
        project_id,
        "acceptance_policy_adoption",
        forged_adoption["acceptance_policy_adoption_id"],
        forged_adoption,
        "2026-09-13T07:20:00Z",
    )
    with pytest.raises(PolicyProvenanceError):
        resolve_and_verify_adoption(
            store, project_id, forged_adoption["acceptance_policy_adoption_id"]
        )


def test_resolve_and_verify_adoption_refuses_when_the_adopted_target_is_schema_invalid(
    tmp_path: Path,
) -> None:
    """P82-R4-F3: an Adoption whose own referenced Baseline genuinely resolves, but is itself
    schema-invalid (committed by bypassing this package's own construction boundary, exactly
    as ``test_a_malformed_record_on_disk_refuses_at_resolve_time_not_only_at_commit_time``
    constructs its own malformed baseline), still refuses on direct
    ``resolve_and_verify_adoption`` -- never only when someone separately resolves the
    baseline on its own."""

    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]

    malformed_baseline = ap_engine.build_baseline(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        source_reference=source_reference("40202", source_kind="ORIGINAL_ISSUE"),
        clauses=[
            clause(
                _ACTIONS_CLAUSE_ID,
                policy_class="AUTHORITY",
                project_id=project_id,
                existed_in_original_contract=True,
            )
        ],
    )
    malformed_baseline["unexpected_extra_field"] = "not part of the schema"
    ap_route._commit_one_record(
        store,
        project_id,
        "acceptance_policy_baseline",
        malformed_baseline["acceptance_policy_baseline_id"],
        malformed_baseline,
        "2026-09-13T07:20:01Z",
    )
    malformed_baseline_ref = {
        "kind": "acceptance_policy_baseline",
        "id": malformed_baseline["acceptance_policy_baseline_id"],
    }
    sr = source_reference("40203", source_kind="AUTHORITY_ADOPTION")
    forged_adoption = ap_engine.build_adoption(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=malformed_baseline_ref,
        decision_owner="SHUKOU",
        source_reference=sr,
        governance_adoption_record=governance_adoption_record(
            project_id=project_id,
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=malformed_baseline_ref,
            source_reference=sr,
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T07:20:02Z",
        ),
        project_binding_id=world["project_binding_id"],
        signing_key=human_authority_signing_key(),
        decided_at="2026-09-13T07:20:02Z",
    )
    ap_route._commit_one_record(
        store,
        project_id,
        "acceptance_policy_adoption",
        forged_adoption["acceptance_policy_adoption_id"],
        forged_adoption,
        "2026-09-13T07:20:02Z",
    )
    with pytest.raises(AcceptancePolicyValidationError):
        resolve_and_verify_adoption(
            store, project_id, forged_adoption["acceptance_policy_adoption_id"]
        )


def test_resolve_and_verify_adoption_refuses_when_the_adopted_target_is_a_different_work_unit(
    tmp_path: Path,
) -> None:
    """P82-R4-F3: an Adoption whose own ``governing_issue`` names this work unit, but whose
    ``adopted_ref`` resolves to a Baseline genuinely committed for a *different* work unit,
    refuses on direct ``resolve_and_verify_adoption`` -- the cross-work-unit check is part of
    re-resolving the target, not merely a side effect of effective-policy folding."""

    other_issue = GOVERNING_ISSUE + 9000
    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]

    other_baseline = open_acceptance_policy_baseline(
        store,
        project_id,
        governing_issue=other_issue,
        source_reference=source_reference(
            "40204", source_kind="ORIGINAL_ISSUE", path="issues/9997"
        ),
        clauses=[
            clause(
                "CROSS_WORK_UNIT_CLAUSE",
                policy_class="AUTHORITY",
                project_id=project_id,
                existed_in_original_contract=True,
            )
        ],
        committed_at="2026-09-13T07:20:03Z",
    )
    other_baseline_ref = {
        "kind": "acceptance_policy_baseline",
        "id": other_baseline["acceptance_policy_baseline_id"],
    }
    sr = source_reference("40205", source_kind="AUTHORITY_ADOPTION")
    forged_adoption = ap_engine.build_adoption(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=other_baseline_ref,
        decision_owner="SHUKOU",
        source_reference=sr,
        governance_adoption_record=governance_adoption_record(
            project_id=project_id,
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=other_baseline_ref,
            source_reference=sr,
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T07:20:04Z",
        ),
        project_binding_id=world["project_binding_id"],
        signing_key=human_authority_signing_key(),
        decided_at="2026-09-13T07:20:04Z",
    )
    ap_route._commit_one_record(
        store,
        project_id,
        "acceptance_policy_adoption",
        forged_adoption["acceptance_policy_adoption_id"],
        forged_adoption,
        "2026-09-13T07:20:04Z",
    )
    with pytest.raises(PolicyLineageConflictError):
        resolve_and_verify_adoption(
            store, project_id, forged_adoption["acceptance_policy_adoption_id"]
        )


def test_resolve_and_verify_adoption_refuses_when_a_transitions_own_baseline_lineage_is_missing(
    tmp_path: Path,
) -> None:
    """P82-R4-F3: for a Transition target, its own canonical Baseline lineage is
    independently resolved and reproduced too -- an Adoption naming a Transition whose own
    ``baseline_ref`` has been tampered to point at a Baseline that was never committed
    refuses on direct ``resolve_and_verify_adoption``."""

    world = bound_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)

    proposed = clause(
        _GATE_CLAUSE_ID,
        policy_class="REQUIRED_EVIDENCE",
        project_id=project_id,
        existed_in_original_contract=False,
        merge=True,
    )
    real_transition = propose_acceptance_policy_transition(
        store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=_GATE_CLAUSE_ID,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=proposed,
        source_reference=source_reference("40206", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T07:20:05Z",
    )
    tampered_transition = deepcopy(real_transition)
    tampered_transition["baseline_ref"] = {
        "kind": "acceptance_policy_baseline",
        "id": "AP-BASE-" + "7" * 64,
    }
    tampered_transition["transition_semantic_fingerprint"] = (
        identity.transition_semantic_fingerprint(tampered_transition)
    )
    tampered_transition["acceptance_policy_transition_id"] = identity.transition_id(
        tampered_transition
    )
    ap_route._commit_one_record(
        store,
        project_id,
        "acceptance_policy_transition",
        tampered_transition["acceptance_policy_transition_id"],
        tampered_transition,
        "2026-09-13T07:20:06Z",
    )
    tampered_transition_ref = {
        "kind": "acceptance_policy_transition",
        "id": tampered_transition["acceptance_policy_transition_id"],
    }
    sr = source_reference("40207", source_kind="AUTHORITY_ADOPTION")
    forged_adoption = ap_engine.build_adoption(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=tampered_transition_ref,
        decision_owner="SHUKOU",
        source_reference=sr,
        governance_adoption_record=governance_adoption_record(
            project_id=project_id,
            governing_issue=GOVERNING_ISSUE,
            adopted_ref=tampered_transition_ref,
            source_reference=sr,
            project_binding_id=world["project_binding_id"],
            decided_at="2026-09-13T07:20:07Z",
        ),
        project_binding_id=world["project_binding_id"],
        signing_key=human_authority_signing_key(),
        decided_at="2026-09-13T07:20:07Z",
    )
    ap_route._commit_one_record(
        store,
        project_id,
        "acceptance_policy_adoption",
        forged_adoption["acceptance_policy_adoption_id"],
        forged_adoption,
        "2026-09-13T07:20:07Z",
    )
    with pytest.raises(PolicyProvenanceError):
        resolve_and_verify_adoption(
            store, project_id, forged_adoption["acceptance_policy_adoption_id"]
        )


class _FirstLoadMutatingStore:
    """P82-R4-F4: a Store wrapper whose ``load_current`` -- the literal first Store call
    ``adopt_acceptance_policy_transition``'s own retry loop makes -- mutates the caller's
    original, still-retained ``adopted_ref``/``source_reference``/``governance_adoption_
    record`` objects in place, once, before delegating to the real Store. Used to prove the
    adoption boundary never observes that mutation: only the values already detached as this
    function's own literal first operations, before ``_require_source_reference`` or any
    Store call at all, are ever built, simulated, or committed."""

    def __init__(self, real_store: Any, on_first_load_current: Any) -> None:
        self._real_store = real_store
        self._on_first_load_current = on_first_load_current
        self._triggered = False

    def load_current(self, *args: Any, **kwargs: Any) -> Any:
        if not self._triggered:
            self._triggered = True
            self._on_first_load_current()
        return self._real_store.load_current(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real_store, name)


def test_adopt_detaches_all_three_caller_owned_inputs_before_any_store_call_surviving_a_mid_call_mutation(
    tmp_path: Path,
) -> None:
    """P82-R4-F4: ``adopted_ref``, ``source_reference``, and ``governance_adoption_record``
    are detached (deep-copied) as ``adopt_acceptance_policy_transition``'s own literal first
    operations. Proven here by mutating the caller's *original*, still-retained objects for
    all three in place, from inside a Store hook that fires during ``load_current`` -- this
    function's own first Store call, deep inside its retry loop -- to a different, fully
    valid, correctly re-signed target B. The adoption actually committed still names the
    original target A; B's own adoption is never committed at all."""

    world = bound_world(tmp_path)
    real_store = world["store"]
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]
    baseline = _open_and_adopt_baseline(world)
    baseline_ref = _baseline_ref(baseline)

    original_clause_id = "MUTATION_TARGET_ORIGINAL"
    substituted_clause_id = "MUTATION_TARGET_SUBSTITUTED"
    t_original = propose_acceptance_policy_transition(
        real_store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=original_clause_id,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=clause(
            original_clause_id,
            policy_class="REQUIRED_EVIDENCE",
            project_id=project_id,
            existed_in_original_contract=False,
        ),
        source_reference=source_reference("40301", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T07:30:00Z",
    )
    t_substituted = propose_acceptance_policy_transition(
        real_store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        baseline_ref=baseline_ref,
        clause_id=substituted_clause_id,
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        proposed_clause=clause(
            substituted_clause_id,
            policy_class="REQUIRED_EVIDENCE",
            project_id=project_id,
            existed_in_original_contract=False,
        ),
        source_reference=source_reference("40302", source_kind="STRUCTURAL_REVIEW"),
        rollback_condition="r",
        committed_at="2026-09-13T07:30:01Z",
    )

    original_adopted_ref = {
        "kind": "acceptance_policy_transition",
        "id": t_original["acceptance_policy_transition_id"],
    }
    original_sr = source_reference("40303", source_kind="AUTHORITY_ADOPTION")
    original_decided_at = "2026-09-13T07:30:02Z"
    original_record = governance_adoption_record(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=original_adopted_ref,
        source_reference=original_sr,
        project_binding_id=project_binding_id,
        decided_at=original_decided_at,
    )

    substituted_adopted_ref = {
        "kind": "acceptance_policy_transition",
        "id": t_substituted["acceptance_policy_transition_id"],
    }
    substituted_sr = source_reference("40304", source_kind="AUTHORITY_ADOPTION")
    substituted_decided_at = "2026-09-13T07:30:03Z"
    substituted_record = governance_adoption_record(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=substituted_adopted_ref,
        source_reference=substituted_sr,
        project_binding_id=project_binding_id,
        decided_at=substituted_decided_at,
    )
    substituted_adoption_preview = ap_engine.build_adoption(
        project_id=project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=substituted_adopted_ref,
        decision_owner="SHUKOU",
        source_reference=substituted_sr,
        governance_adoption_record=substituted_record,
        project_binding_id=project_binding_id,
        signing_key=human_authority_signing_key(),
        decided_at=substituted_decided_at,
    )

    def _substitute_b_for_a() -> None:
        # a mid-call mutation of the caller's own retained objects -- never the already-
        # detached copies, if the fix is correct.
        original_adopted_ref.clear()
        original_adopted_ref.update(substituted_adopted_ref)
        original_sr.clear()
        original_sr.update(substituted_sr)
        original_record.clear()
        original_record.update(substituted_record)

    wrapped_store = _FirstLoadMutatingStore(real_store, _substitute_b_for_a)

    committed_adoption = adopt_acceptance_policy_transition(
        wrapped_store,
        project_id,
        governing_issue=GOVERNING_ISSUE,
        adopted_ref=original_adopted_ref,
        decision_owner="SHUKOU",
        source_reference=original_sr,
        governance_adoption_record=original_record,
        project_binding_id=project_binding_id,
        decided_at=original_decided_at,
        committed_at=original_decided_at,
    )

    # the hook genuinely fired and genuinely corrupted the caller's own retained objects --
    # otherwise this test would be vacuous.
    assert original_adopted_ref == substituted_adopted_ref
    assert original_sr == substituted_sr
    assert original_record == substituted_record

    # the adoption actually committed still names the original target A, never B.
    assert committed_adoption["adopted_ref"] == {
        "kind": "acceptance_policy_transition",
        "id": t_original["acceptance_policy_transition_id"],
    }
    assert committed_adoption["source_reference"]["comment_id"] == "40303"

    # B's own adoption -- fully valid, and would have committed cleanly on its own -- was
    # never committed at all.
    assert (
        real_store.resolve_record(
            project_id,
            "acceptance_policy_adoption",
            substituted_adoption_preview["acceptance_policy_adoption_id"],
        )
        is None
    )

    view = resolve_and_verify_effective_policy(real_store, project_id, baseline_ref)
    effective_clause_ids = {c["clause_id"] for c in view["effective_clauses"]}
    assert original_clause_id in effective_clause_ids
    assert substituted_clause_id not in effective_clause_ids
