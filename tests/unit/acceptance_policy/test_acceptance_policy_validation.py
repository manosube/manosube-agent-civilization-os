"""P82-R1-F4: schema validation for the Acceptance Policy Lineage record kinds.

Each of the five record kinds this package ever constructs and Store-resolves (baseline,
transition, adoption, effective view, impact preview) must validate against its own unchanged
(``SCHEMA_COUNT=86``) canonical schema -- both a positive control (a genuinely well-formed
record passes) and a decisive negative control (a schema-invalid shape is refused) per kind.
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
    engine as ap_engine,
    validation as ap_validation,
)

_PROJECT_ID = "PRJ-AP-0001"
_PROJECT_BINDING_ID = "PROJBIND-" + "A" * 64

_SOURCE_REFERENCE = {
    "comment_url": "https://github.com/manosube/manosube-agent-civilization-os/issues/77#issuecomment-1",
    "comment_id": "1",
    "comment_author": "manosube",
    "comment_author_association": "OWNER",
    "source_kind": "ORIGINAL_ISSUE",
}
_ADOPTION_SOURCE_REFERENCE = {**_SOURCE_REFERENCE, "source_kind": "AUTHORITY_ADOPTION"}


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
        source_reference=_SOURCE_REFERENCE,
        clauses=[_clause("ORIGINAL_CLAUSE")],
    )


def _adopted_baseline_ref() -> dict[str, str]:
    return {
        "kind": "acceptance_policy_baseline",
        "id": _baseline()["acceptance_policy_baseline_id"],
    }


def _governance_adoption_record(
    *,
    adopted_ref: dict[str, str] | None = None,
    comment_url: str = _SOURCE_REFERENCE["comment_url"],
    governing_issue: int = 77,
    source_reference: dict[str, Any] = _ADOPTION_SOURCE_REFERENCE,
    project_binding_id: str = _PROJECT_BINDING_ID,
    decided_at: str = "2026-09-13T14:00:00Z",
) -> dict[str, Any]:
    reviewed_sha = "a" * 40
    governing_issue_str = f"#{governing_issue}"
    core = {
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
    }
    signature = sign_governance_adoption_authority(
        project_id=_PROJECT_ID,
        governing_issue=governing_issue,
        adopted_ref=adopted_ref if adopted_ref is not None else _adopted_baseline_ref(),
        decision_owner="SHUKOU",
        source_reference=source_reference,
        project_binding_id=project_binding_id,
        decided_at=decided_at,
        governance_adoption_record_core=core,
    )
    return {**core, "signature": signature}


def test_a_well_formed_baseline_validates() -> None:
    ap_validation.validate_record(_baseline(), "acceptance_policy_baseline.schema.json")


def test_a_baseline_with_an_unknown_top_level_field_refuses() -> None:
    baseline = _baseline()
    baseline["not_a_real_field"] = "smuggled"
    with pytest.raises(AcceptancePolicyValidationError):
        ap_validation.validate_record(baseline, "acceptance_policy_baseline.schema.json")


def test_a_well_formed_transition_validates() -> None:
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
        source_reference=_SOURCE_REFERENCE,
        rollback_condition="revert on demand",
    )
    ap_validation.validate_record(transition, "acceptance_policy_transition.schema.json")


def test_a_transition_with_an_unknown_policy_operation_refuses() -> None:
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
        source_reference=_SOURCE_REFERENCE,
        rollback_condition="revert on demand",
    )
    transition["policy_operation"] = "SOMETHING_NOT_IN_THE_ENUM"
    with pytest.raises(AcceptancePolicyValidationError):
        ap_validation.validate_record(transition, "acceptance_policy_transition.schema.json")


def test_a_well_formed_adoption_validates() -> None:
    adoption = build_adoption(
        project_id=_PROJECT_ID,
        governing_issue=77,
        adopted_ref={
            "kind": "acceptance_policy_baseline",
            "id": _baseline()["acceptance_policy_baseline_id"],
        },
        decision_owner="SHUKOU",
        source_reference={**_SOURCE_REFERENCE, "source_kind": "AUTHORITY_ADOPTION"},
        governance_adoption_record=_governance_adoption_record(),
        project_binding_id=_PROJECT_BINDING_ID,
        signing_key=human_authority_signing_key(),
        decided_at="2026-09-13T14:00:00Z",
    )
    ap_validation.validate_record(adoption, "acceptance_policy_adoption.schema.json")


def test_an_adoption_missing_a_required_field_refuses() -> None:
    adoption = build_adoption(
        project_id=_PROJECT_ID,
        governing_issue=77,
        adopted_ref={
            "kind": "acceptance_policy_baseline",
            "id": _baseline()["acceptance_policy_baseline_id"],
        },
        decision_owner="SHUKOU",
        source_reference={**_SOURCE_REFERENCE, "source_kind": "AUTHORITY_ADOPTION"},
        governance_adoption_record=_governance_adoption_record(),
        project_binding_id=_PROJECT_BINDING_ID,
        signing_key=human_authority_signing_key(),
        decided_at="2026-09-13T14:00:00Z",
    )
    del adoption["decided_at"]
    with pytest.raises(AcceptancePolicyValidationError):
        ap_validation.validate_record(adoption, "acceptance_policy_adoption.schema.json")


def test_a_well_formed_effective_view_validates() -> None:
    baseline = _baseline()
    view = ap_engine.derive_effective_policy(
        baseline,
        {},
        [
            build_adoption(
                project_id=_PROJECT_ID,
                governing_issue=77,
                adopted_ref={
                    "kind": "acceptance_policy_baseline",
                    "id": baseline["acceptance_policy_baseline_id"],
                },
                decision_owner="SHUKOU",
                source_reference={**_SOURCE_REFERENCE, "source_kind": "AUTHORITY_ADOPTION"},
                governance_adoption_record=_governance_adoption_record(),
                project_binding_id=_PROJECT_BINDING_ID,
                signing_key=human_authority_signing_key(),
                decided_at="2026-09-13T14:00:00Z",
            )
        ],
    )
    ap_validation.validate_record(view, "acceptance_policy_effective_view.schema.json")


def test_an_effective_view_with_a_wrong_typed_field_refuses() -> None:
    baseline = _baseline()
    view = ap_engine.derive_effective_policy(
        baseline,
        {},
        [
            build_adoption(
                project_id=_PROJECT_ID,
                governing_issue=77,
                adopted_ref={
                    "kind": "acceptance_policy_baseline",
                    "id": baseline["acceptance_policy_baseline_id"],
                },
                decision_owner="SHUKOU",
                source_reference={**_SOURCE_REFERENCE, "source_kind": "AUTHORITY_ADOPTION"},
                governance_adoption_record=_governance_adoption_record(),
                project_binding_id=_PROJECT_BINDING_ID,
                signing_key=human_authority_signing_key(),
                decided_at="2026-09-13T14:00:00Z",
            )
        ],
    )
    view["governing_issue"] = "not-an-integer"
    with pytest.raises(AcceptancePolicyValidationError):
        ap_validation.validate_record(view, "acceptance_policy_effective_view.schema.json")


def test_a_well_formed_impact_preview_validates() -> None:
    baseline = _baseline()
    view = {"project_id": _PROJECT_ID, "governing_issue": 77, "effective_clauses": []}
    candidate = build_transition(
        project_id=_PROJECT_ID,
        governing_issue=77,
        baseline=baseline,
        clause_id="C1",
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        prior_clause_binding={
            "source": "BASELINE",
            "source_ref": {
                "kind": "acceptance_policy_baseline",
                "id": baseline["acceptance_policy_baseline_id"],
            },
        },
        proposed_clause=_clause("C1", existed_in_original_contract=False, merge=True),
        prior_clause=None,
        declared_existed_in_original_contract=False,
        source_reference=_SOURCE_REFERENCE,
        rollback_condition="r",
    )
    preview = build_impact_preview(view, candidate)
    ap_validation.validate_record(preview, "acceptance_policy_impact_preview.schema.json")


def test_an_impact_preview_with_a_missing_required_field_refuses() -> None:
    baseline = _baseline()
    view = {"project_id": _PROJECT_ID, "governing_issue": 77, "effective_clauses": []}
    candidate = build_transition(
        project_id=_PROJECT_ID,
        governing_issue=77,
        baseline=baseline,
        clause_id="C1",
        policy_operation="ADD",
        proposed_by="STRUCTURAL_ADVISOR",
        prior_clause_binding={
            "source": "BASELINE",
            "source_ref": {
                "kind": "acceptance_policy_baseline",
                "id": baseline["acceptance_policy_baseline_id"],
            },
        },
        proposed_clause=_clause("C1", existed_in_original_contract=False, merge=True),
        prior_clause=None,
        declared_existed_in_original_contract=False,
        source_reference=_SOURCE_REFERENCE,
        rollback_condition="r",
    )
    preview = build_impact_preview(view, candidate)
    del preview["rollback_condition"]
    with pytest.raises(AcceptancePolicyValidationError):
        ap_validation.validate_record(preview, "acceptance_policy_impact_preview.schema.json")


def test_an_unregistered_schema_name_refuses() -> None:
    with pytest.raises(AcceptancePolicyValidationError):
        ap_validation.validate_record({}, "acceptance_policy_does_not_exist.schema.json")


def test_an_adoption_with_a_governance_adoption_record_missing_a_required_key_refuses() -> None:
    """P82-R2-F4: the new ``governance_adoption_record`` field is itself schema-validated --
    a missing required key is caught at the wire-shape layer, independent of whatever
    ``evaluate_adoption_record`` itself would separately decide."""

    adoption = build_adoption(
        project_id=_PROJECT_ID,
        governing_issue=77,
        adopted_ref={
            "kind": "acceptance_policy_baseline",
            "id": _baseline()["acceptance_policy_baseline_id"],
        },
        decision_owner="SHUKOU",
        source_reference={**_SOURCE_REFERENCE, "source_kind": "AUTHORITY_ADOPTION"},
        governance_adoption_record=_governance_adoption_record(),
        project_binding_id=_PROJECT_BINDING_ID,
        signing_key=human_authority_signing_key(),
        decided_at="2026-09-13T14:00:00Z",
    )
    del adoption["governance_adoption_record"]["authorized_target_sha"]
    with pytest.raises(AcceptancePolicyValidationError):
        ap_validation.validate_record(adoption, "acceptance_policy_adoption.schema.json")


def test_an_adoption_with_a_governance_adoption_record_carrying_an_unknown_key_refuses() -> None:
    adoption = build_adoption(
        project_id=_PROJECT_ID,
        governing_issue=77,
        adopted_ref={
            "kind": "acceptance_policy_baseline",
            "id": _baseline()["acceptance_policy_baseline_id"],
        },
        decision_owner="SHUKOU",
        source_reference={**_SOURCE_REFERENCE, "source_kind": "AUTHORITY_ADOPTION"},
        governance_adoption_record=_governance_adoption_record(),
        project_binding_id=_PROJECT_BINDING_ID,
        signing_key=human_authority_signing_key(),
        decided_at="2026-09-13T14:00:00Z",
    )
    adoption["governance_adoption_record"]["unexpected_extra_field"] = "smuggled"
    with pytest.raises(AcceptancePolicyValidationError):
        ap_validation.validate_record(adoption, "acceptance_policy_adoption.schema.json")
