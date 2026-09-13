"""V3: The semantic policy-diff gate (FD4-C1, FD4-C4, FD4-C5).

``classify_operation`` independently recomputes which of the six closed operations a
prior/proposed clause-body pair represents -- never trusting a caller's declared label.
``assert_no_undeclared_policy_change`` refuses a policy term smuggled into an unrelated
record without a ``policy_change: True`` declaration.
"""

from __future__ import annotations

from typing import Any

import pytest

from manosube_agent_civilization.acceptance_policy import (
    AcceptancePolicyValidationError,
    UndeclaredPolicyChangeError,
    assert_no_undeclared_policy_change,
    classify_operation,
)

_PROJECT_ID = "PRJ-AP-0001"


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
        "statement": "s",
        "blocking_effect": {
            "implementation": False,
            "structural_review": False,
            "merge": False,
            "issue_closure": False,
            "phase_completion": False,
            **blocking_overrides,
        },
        "scope": {"project_id": _PROJECT_ID, "affected_phases": [], "affected_prs": []},
        "rationale": "r",
        "existed_in_original_contract": False,
    }
    body.update(overrides)
    return body


def test_classify_operation_add_from_no_predecessor() -> None:
    assert classify_operation(None, _clause("C1")) == "ADD"


def test_classify_operation_remove_from_no_successor() -> None:
    assert classify_operation(_clause("C1"), None) == "REMOVE"


def test_classify_operation_refuses_neither_prior_nor_proposed() -> None:
    with pytest.raises(AcceptancePolicyValidationError):
        classify_operation(None, None)


def test_classify_operation_refuses_a_semantically_identical_pair() -> None:
    prior = _clause("C1")
    proposed = _clause("C1", statement="different prose, same meaning")
    with pytest.raises(UndeclaredPolicyChangeError):
        classify_operation(prior, proposed)


def test_classify_operation_reclassify_on_policy_class_change() -> None:
    prior = _clause("C1", policy_class="AUTHORITY")
    proposed = _clause("C1", policy_class="REQUIRED_EVIDENCE")
    assert classify_operation(prior, proposed) == "RECLASSIFY"


def test_classify_operation_broaden_when_a_blocker_is_added_and_none_removed() -> None:
    prior = _clause("C1", merge=True)
    proposed = _clause("C1", merge=True, issue_closure=True)
    assert classify_operation(prior, proposed) == "BROADEN"


def test_classify_operation_narrow_when_a_blocker_is_removed_and_none_added() -> None:
    prior = _clause("C1", merge=True, issue_closure=True)
    proposed = _clause("C1", merge=True)
    assert classify_operation(prior, proposed) == "NARROW"


def test_classify_operation_replace_when_blockers_both_added_and_removed() -> None:
    prior = _clause("C1", merge=True)
    proposed = _clause("C1", issue_closure=True)
    assert classify_operation(prior, proposed) == "REPLACE"


def test_classify_operation_replace_when_only_scope_changes() -> None:
    prior = _clause("C1", merge=True)
    proposed = dict(prior)
    proposed["scope"] = {"project_id": _PROJECT_ID, "affected_phases": [20], "affected_prs": []}
    assert classify_operation(prior, proposed) == "REPLACE"


def test_reclassify_takes_priority_over_a_simultaneous_blocking_effect_change() -> None:
    prior = _clause("C1", policy_class="AUTHORITY", merge=True)
    proposed = _clause("C1", policy_class="REQUIRED_EVIDENCE", merge=True, issue_closure=True)
    assert classify_operation(prior, proposed) == "RECLASSIFY"


# --- FD4-C4: undeclared policy change smuggled into an unrelated record --------------------- #


def test_assert_no_undeclared_policy_change_admits_a_payload_with_no_known_terms() -> None:
    assert_no_undeclared_policy_change(
        {"finding": "unrelated defect"}, frozenset({"GITHUB_PREMERGE_GATE_GREEN"})
    )


def test_assert_no_undeclared_policy_change_refuses_a_bare_value_mention() -> None:
    payload = {"finding": "unrelated", "cited_gate": "GITHUB_PREMERGE_GATE_GREEN"}
    with pytest.raises(UndeclaredPolicyChangeError):
        assert_no_undeclared_policy_change(payload, frozenset({"GITHUB_PREMERGE_GATE_GREEN"}))


def test_assert_no_undeclared_policy_change_refuses_smuggling_inside_required_proofs() -> None:
    payload = {
        "finding": "some unrelated code finding",
        "required_proofs": {"GITHUB_PREMERGE_GATE_GREEN_REQUIRED": True},
    }
    with pytest.raises(UndeclaredPolicyChangeError):
        assert_no_undeclared_policy_change(payload, frozenset({"GITHUB_PREMERGE_GATE_GREEN"}))


def test_assert_no_undeclared_policy_change_refuses_smuggling_inside_a_handoff() -> None:
    payload = {
        "handoff_id": "HANDOFF_EXAMPLE",
        "adopted_findings": ["GITHUB_PREMERGE_GATE_GREEN"],
    }
    with pytest.raises(UndeclaredPolicyChangeError):
        assert_no_undeclared_policy_change(payload, frozenset({"GITHUB_PREMERGE_GATE_GREEN"}))


def test_assert_no_undeclared_policy_change_refuses_smuggling_inside_a_closure_sweep() -> None:
    payload = {"closure_sweep": {"GITHUB_PREMERGE_GATE_GREEN_STATUS": "PASS"}}
    with pytest.raises(UndeclaredPolicyChangeError):
        assert_no_undeclared_policy_change(payload, frozenset({"GITHUB_PREMERGE_GATE_GREEN"}))


def test_assert_no_undeclared_policy_change_admits_a_declared_change() -> None:
    payload = {
        "policy_change": True,
        "required_proofs": {"GITHUB_PREMERGE_GATE_GREEN_REQUIRED": True},
    }
    assert_no_undeclared_policy_change(payload, frozenset({"GITHUB_PREMERGE_GATE_GREEN"}))


def test_assert_no_undeclared_policy_change_refuses_a_non_object_payload() -> None:
    with pytest.raises(AcceptancePolicyValidationError):
        assert_no_undeclared_policy_change("not a dict", frozenset({"C1"}))
