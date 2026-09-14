"""V1: Schema identity and semantic-fingerprint totality (FD-0004, Issue #80).

Every one of the five committed/derived record kinds -- Baseline, Clause (embedded),
Transition, Adoption, Effective View, Impact Preview -- gets a deterministic id and/or
semantic fingerprint whose own declared value always reproduces from the record's own content,
and which changes the moment any semantic field changes (never a lifecycle/provenance field).
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.fixtures.product_binding import (
    human_authority_signing_key,
    sign_governance_adoption_authority,
)

from manosube_agent_civilization.acceptance_policy import (
    AcceptancePolicyValidationError,
    build_adoption,
    build_baseline,
    build_impact_preview,
    build_transition,
    identity as ap_identity,
    require_valid_clause,
)

_PROJECT_ID = "PRJ-AP-0001"
_PROJECT_BINDING_ID = "PROJBIND-" + "A" * 64


_BLOCKING_FIELDS = (
    "implementation",
    "structural_review",
    "merge",
    "issue_closure",
    "phase_completion",
)


def _clause(clause_id: str, **overrides: Any) -> dict[str, Any]:
    blocking_overrides = {
        field: overrides.pop(field) for field in _BLOCKING_FIELDS if field in overrides
    }
    body = {
        "clause_id": clause_id,
        "policy_class": "AUTHORITY",
        "statement": "statement",
        "blocking_effect": {
            "implementation": False,
            "structural_review": False,
            "merge": False,
            "issue_closure": False,
            "phase_completion": False,
            **blocking_overrides,
        },
        "scope": {"project_id": _PROJECT_ID, "affected_phases": [19], "affected_prs": [78]},
        "rationale": "rationale",
        "existed_in_original_contract": True,
    }
    body.update(overrides)
    return body


def _baseline() -> dict[str, Any]:
    return build_baseline(
        project_id=_PROJECT_ID,
        governing_issue=77,
        source_reference={
            "comment_url": "https://github.com/manosube/manosube-agent-civilization-os/issues/77#issuecomment-1",
            "comment_id": "1",
            "comment_author": "manosube",
            "comment_author_association": "OWNER",
            "source_kind": "ORIGINAL_ISSUE",
        },
        clauses=[_clause("ORIGINAL_CLAUSE")],
    )


def _governance_adoption_record(
    *,
    adopted_ref: dict[str, str],
    decision_owner: str = "SHUKOU",
    comment_url: str = "https://github.com/manosube/manosube-agent-civilization-os/issues/77#issuecomment-1",
    governing_issue: int = 77,
) -> dict[str, Any]:
    reviewed_sha = "a" * 40
    governing_issue_str = f"#{governing_issue}"
    signature = sign_governance_adoption_authority(
        project_id=_PROJECT_ID,
        governing_issue=governing_issue,
        adopted_ref=adopted_ref,
        decision_owner=decision_owner,
        comment_url=comment_url,
        reviewed_sha=reviewed_sha,
        authorized_target_sha=reviewed_sha,
    )
    return {
        "schema_version": "0.1",
        "adoption_id": "ADOPT_TEST_FIXTURE",
        "governing_issue": governing_issue_str,
        "comment_url": comment_url,
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
        "api_read_back_receipt": {
            "adoption_id": "ADOPT_TEST_FIXTURE",
            "governing_issue": governing_issue_str,
            "reviewed_sha": reviewed_sha,
            "comment_url": comment_url,
            "decision_authority": "SHUKOU",
            "decision_status": "RATIFIED",
        },
        "reviewed_sha": reviewed_sha,
        "authorized_target_sha": reviewed_sha,
        "signature": signature,
    }


def test_require_valid_clause_accepts_a_well_formed_clause() -> None:
    require_valid_clause(_clause("C1"))


def test_require_valid_clause_refuses_missing_keys() -> None:
    body = _clause("C1")
    del body["scope"]
    with pytest.raises(AcceptancePolicyValidationError):
        require_valid_clause(body)


def test_require_valid_clause_refuses_unknown_keys() -> None:
    body = _clause("C1")
    body["extra"] = "not part of the schema"
    with pytest.raises(AcceptancePolicyValidationError):
        require_valid_clause(body)


def test_require_valid_clause_refuses_unknown_policy_class() -> None:
    with pytest.raises(AcceptancePolicyValidationError):
        require_valid_clause(_clause("C1", policy_class="SOMETHING_ELSE"))


def test_require_valid_clause_refuses_incomplete_blocking_effect() -> None:
    body = _clause("C1")
    del body["blocking_effect"]["merge"]
    with pytest.raises(AcceptancePolicyValidationError):
        require_valid_clause(body)


def test_baseline_id_and_fingerprint_reproduce_from_their_own_content() -> None:
    baseline = _baseline()
    assert ap_identity.baseline_id(baseline) == baseline["acceptance_policy_baseline_id"]
    assert (
        ap_identity.baseline_semantic_fingerprint(baseline)
        == baseline["baseline_semantic_fingerprint"]
    )


def test_baseline_id_is_a_narrow_natural_key_stable_across_different_clause_content() -> None:
    """P82-R1-F3: the baseline's own identity is a narrow ``(project_id, governing_issue)``
    natural key, not a full-content hash -- two different clause sets proposed for the
    identical work unit collide at the identical id (so the Store's own manifest-identity
    check is what refuses the second one as a conflicting replay), while their own semantic
    fingerprints still differ and still independently verify the full content on every read."""

    baseline_a = _baseline()
    baseline_b = build_baseline(
        project_id=_PROJECT_ID,
        governing_issue=77,
        source_reference=baseline_a["source_reference"],
        clauses=[_clause("ORIGINAL_CLAUSE", merge=True)],
    )
    assert (
        baseline_a["acceptance_policy_baseline_id"] == baseline_b["acceptance_policy_baseline_id"]
    )
    assert (
        baseline_a["baseline_semantic_fingerprint"] != baseline_b["baseline_semantic_fingerprint"]
    )


def test_baseline_id_changes_for_a_different_governing_issue() -> None:
    baseline_a = _baseline()
    baseline_b = build_baseline(
        project_id=_PROJECT_ID,
        governing_issue=78,
        source_reference=baseline_a["source_reference"],
        clauses=[_clause("ORIGINAL_CLAUSE")],
    )
    assert (
        baseline_a["acceptance_policy_baseline_id"] != baseline_b["acceptance_policy_baseline_id"]
    )


def test_baseline_id_changes_for_a_different_project() -> None:
    baseline_a = _baseline()
    baseline_b = build_baseline(
        project_id="PRJ-AP-0002",
        governing_issue=77,
        source_reference=baseline_a["source_reference"],
        clauses=[_clause("ORIGINAL_CLAUSE")],
    )
    assert (
        baseline_a["acceptance_policy_baseline_id"] != baseline_b["acceptance_policy_baseline_id"]
    )


def test_baseline_id_is_stable_under_identical_reconstruction() -> None:
    assert (
        _baseline()["acceptance_policy_baseline_id"] == _baseline()["acceptance_policy_baseline_id"]
    )


def test_baseline_refuses_empty_clause_list() -> None:
    with pytest.raises(AcceptancePolicyValidationError):
        build_baseline(
            project_id=_PROJECT_ID,
            governing_issue=77,
            source_reference=_baseline()["source_reference"],
            clauses=[],
        )


def test_baseline_refuses_duplicate_clause_ids() -> None:
    with pytest.raises(AcceptancePolicyValidationError):
        build_baseline(
            project_id=_PROJECT_ID,
            governing_issue=77,
            source_reference=_baseline()["source_reference"],
            clauses=[_clause("SAME"), _clause("SAME", merge=True)],
        )


def test_baseline_refuses_a_clause_not_declaring_existed_in_original_contract() -> None:
    with pytest.raises(AcceptancePolicyValidationError):
        build_baseline(
            project_id=_PROJECT_ID,
            governing_issue=77,
            source_reference=_baseline()["source_reference"],
            clauses=[_clause("C1", existed_in_original_contract=False)],
        )


def test_transition_id_and_fingerprint_reproduce_and_bind_to_baseline() -> None:
    baseline = _baseline()
    proposed = _clause(
        "NEW_CLAUSE",
        policy_class="REQUIRED_EVIDENCE",
        existed_in_original_contract=False,
        merge=True,
    )
    transition = build_transition(
        project_id=_PROJECT_ID,
        governing_issue=77,
        baseline=baseline,
        clause_id="NEW_CLAUSE",
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        prior_clause_binding={
            "source": "BASELINE",
            "source_ref": {
                "kind": "acceptance_policy_baseline",
                "id": baseline["acceptance_policy_baseline_id"],
            },
        },
        proposed_clause=proposed,
        prior_clause=None,
        declared_existed_in_original_contract=False,
        source_reference=baseline["source_reference"],
        rollback_condition="revert on demand",
    )
    assert ap_identity.transition_id(transition) == transition["acceptance_policy_transition_id"]
    assert (
        ap_identity.transition_semantic_fingerprint(transition)
        == transition["transition_semantic_fingerprint"]
    )
    assert transition["baseline_ref"]["id"] == baseline["acceptance_policy_baseline_id"]


def test_adoption_id_and_fingerprint_reproduce_and_require_shukou() -> None:
    adopted_ref = {
        "kind": "acceptance_policy_baseline",
        "id": _baseline()["acceptance_policy_baseline_id"],
    }
    adoption = build_adoption(
        project_id=_PROJECT_ID,
        governing_issue=77,
        adopted_ref=adopted_ref,
        decision_owner="SHUKOU",
        source_reference=_baseline()["source_reference"],
        governance_adoption_record=_governance_adoption_record(adopted_ref=adopted_ref),
        project_binding_id=_PROJECT_BINDING_ID,
        signing_key=human_authority_signing_key(),
        decided_at="2026-09-13T14:00:00Z",
    )
    assert ap_identity.adoption_id(adoption) == adoption["acceptance_policy_adoption_id"]
    assert (
        ap_identity.adoption_semantic_fingerprint(adoption)
        == adoption["adoption_semantic_fingerprint"]
    )


def test_build_adoption_refuses_a_non_shukou_decision_owner() -> None:
    adopted_ref = {
        "kind": "acceptance_policy_baseline",
        "id": _baseline()["acceptance_policy_baseline_id"],
    }
    with pytest.raises(AcceptancePolicyValidationError):
        build_adoption(
            project_id=_PROJECT_ID,
            governing_issue=77,
            adopted_ref=adopted_ref,
            decision_owner="CLAUDE_CODE",
            source_reference=_baseline()["source_reference"],
            governance_adoption_record=_governance_adoption_record(
                adopted_ref=adopted_ref, decision_owner="CLAUDE_CODE"
            ),
            project_binding_id=_PROJECT_BINDING_ID,
            signing_key=human_authority_signing_key(),
            decided_at="2026-09-13T14:00:00Z",
        )


def test_build_adoption_refuses_a_governance_adoption_record_that_is_not_admitted() -> None:
    """P82-R2-F1: even a correctly-shaped ``decision_owner="SHUKOU"`` is not sufficient any
    more -- the composed ``governance_adoption_record`` must independently evaluate to
    ``ADOPTION_RECORD_ADMITTED`` through the existing, non-substitutable
    ``development_binding.adoption_record`` owner."""

    from manosube_agent_civilization.acceptance_policy import UnauthorizedPolicyAdoptionError

    adopted_ref = {
        "kind": "acceptance_policy_baseline",
        "id": _baseline()["acceptance_policy_baseline_id"],
    }
    forged_record = _governance_adoption_record(adopted_ref=adopted_ref)
    forged_record["decision_authority"] = "STRUCTURAL_ADVISOR"
    forged_record["api_read_back_receipt"] = {
        **forged_record["api_read_back_receipt"],
        "decision_authority": "STRUCTURAL_ADVISOR",
    }
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        build_adoption(
            project_id=_PROJECT_ID,
            governing_issue=77,
            adopted_ref=adopted_ref,
            decision_owner="SHUKOU",
            source_reference=_baseline()["source_reference"],
            governance_adoption_record=forged_record,
            project_binding_id=_PROJECT_BINDING_ID,
            signing_key=human_authority_signing_key(),
            decided_at="2026-09-13T14:00:00Z",
        )


def test_build_adoption_refuses_a_governance_adoption_record_for_a_different_comment() -> None:
    """P82-R2-F1: an admitted record is not authority for *this* adoption unless its own
    comment_url agrees with this exact adoption's own source_reference.comment_url."""

    from manosube_agent_civilization.acceptance_policy import UnauthorizedPolicyAdoptionError

    adopted_ref = {
        "kind": "acceptance_policy_baseline",
        "id": _baseline()["acceptance_policy_baseline_id"],
    }
    mismatched_record = _governance_adoption_record(
        adopted_ref=adopted_ref,
        comment_url="https://github.com/manosube/manosube-agent-civilization-os/issues/77#issuecomment-999",
    )
    with pytest.raises(UnauthorizedPolicyAdoptionError):
        build_adoption(
            project_id=_PROJECT_ID,
            governing_issue=77,
            adopted_ref=adopted_ref,
            decision_owner="SHUKOU",
            source_reference=_baseline()["source_reference"],
            governance_adoption_record=mismatched_record,
            project_binding_id=_PROJECT_BINDING_ID,
            signing_key=human_authority_signing_key(),
            decided_at="2026-09-13T14:00:00Z",
        )


def test_impact_preview_fingerprint_reproduces() -> None:
    view = {
        "project_id": _PROJECT_ID,
        "governing_issue": 77,
        "effective_clauses": [],
    }
    candidate = build_transition(
        project_id=_PROJECT_ID,
        governing_issue=77,
        baseline=_baseline(),
        clause_id="C1",
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        prior_clause_binding={
            "source": "BASELINE",
            "source_ref": {
                "kind": "acceptance_policy_baseline",
                "id": _baseline()["acceptance_policy_baseline_id"],
            },
        },
        proposed_clause=_clause("C1", existed_in_original_contract=False, merge=True),
        prior_clause=None,
        declared_existed_in_original_contract=False,
        source_reference=_baseline()["source_reference"],
        rollback_condition="r",
    )
    preview = build_impact_preview(view, candidate)
    assert (
        ap_identity.impact_preview_semantic_fingerprint(preview)
        == preview["preview_semantic_fingerprint"]
    )
    assert preview["new_blockers"] == [{"clause_id": "C1", "blocking_effect_field": "merge"}]
    assert preview["removed_blockers"] == []
