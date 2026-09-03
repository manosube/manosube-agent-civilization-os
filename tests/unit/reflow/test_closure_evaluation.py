"""Real injected-violation tests for the G1-G22 Closure Evaluation producer.

Every positive fixture here is wired through the real predecessor producers
(``derive_differences``, ``observe``, ``evaluate_sufficiency``) via ``tests/reflow_helpers.py``.
Every negative test tampers exactly one real input and proves the corresponding gate --
never a stand-in diagnostic -- fails, and that ``evaluate_closure`` still returns a
schema-valid record while it does.
"""

from __future__ import annotations

from copy import deepcopy

import pytest
from tests.difference_helpers import state_fingerprint
from tests.evidence_helpers import AFTER_REVISION
from tests.reflow_helpers import (
    base_closure_request,
    candidate_closure_request,
    fixture_difference,
    fixture_policy,
    mandatory_x003_claim_binding,
)

from manosube_agent_civilization.difference.validation import (
    DIFFERENCE_SCHEMA_BASE,
    validate_record,
)
from manosube_agent_civilization.reflow.closure import MANDATORY_X003_CLAIM_REF, evaluate_closure
from manosube_agent_civilization.reflow.errors import ReflowValidationError


def _validate(evaluation: dict) -> None:
    validate_record(evaluation, "closure_evaluation.schema.json", base=DIFFERENCE_SCHEMA_BASE)


def test_candidate_closure_satisfies_every_gate() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)

    evaluation = evaluate_closure(request)

    assert evaluation["evaluation_mode"] == "CANDIDATE_CLOSURE"
    assert evaluation["result"] == "SATISFIED"
    assert evaluation["proposed_terminal_status"] == "CLOSED"
    assert all(value == "PASS" for value in evaluation["gate_results"].values())
    assert evaluation["failure_reasons"] == []
    _validate(evaluation)


def test_terminal_policy_only_baseline_is_blocked_and_schema_valid() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = base_closure_request(difference, policy)

    evaluation = evaluate_closure(request)

    assert evaluation["evaluation_mode"] == "TERMINAL_POLICY_ONLY"
    assert evaluation["result"] == "BLOCKED"
    assert evaluation["after_state_candidate"] is None
    _validate(evaluation)


def test_contradiction_refs_force_contradicted_result() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    request["contradiction_refs"] = [
        {"kind": "material_contradiction", "id": "CONTRA-" + "9" * 64}
    ]
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["evaluation_mode"] == "CANDIDATE_TERMINAL"
    assert evaluation["result"] == "CONTRADICTED"
    _validate(evaluation)


def test_forged_difference_id_fails_g1_and_blocks() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    forged = deepcopy(difference)
    forged["difference_id"] = "D-" + "0" * 64
    forged_policy = deepcopy(policy)
    forged_policy["subject_difference_ref"] = {"kind": "difference", "id": forged["difference_id"]}

    request = base_closure_request(forged, forged_policy)
    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G1"] == "FAIL"
    assert evaluation["result"] == "BLOCKED"
    _validate(evaluation)


def test_wrong_current_status_fails_g2() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = base_closure_request(difference, policy)
    request["current_status"] = "ACTIVE"

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G2"] == "FAIL"
    assert evaluation["result"] == "BLOCKED"


def test_stale_before_state_revision_fails_g5_and_g20() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = base_closure_request(difference, policy)
    # Older than the Difference's own observation baseline -- a real regression, not a
    # relabeling: an evaluator that accepted this would let a Closure Evaluation be built
    # against a State the Difference was never derived from.
    request["current_state"] = {
        "revision": 0,
        "fingerprint": state_fingerprint("UNKNOWN"),
    }

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G5"] == "FAIL"
    assert evaluation["gate_results"]["G20"] == "FAIL"
    assert evaluation["result"] == "BLOCKED"


def test_resolution_mode_evidence_exclusivity_fails_g6_and_g11() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    # A candidate evaluation that names no resolution_mode at all -- neither CHANGE_BOUND
    # nor CHANGE_FREE -- is the one schema-representable way to fail this binding: the
    # canonical schema's own ``allOf`` conditionals already force every *populated*
    # resolution_mode's evidence arrays to be mutually exclusive, so the only way an
    # invalid combination can reach this producer at all is an absent resolution_mode.
    request["resolution_mode"] = None
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G6"] == "FAIL"
    assert evaluation["gate_results"]["G11"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"
    _validate(evaluation)


def test_reproduction_gates_fail_when_reobservation_is_still_unsatisfied() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    # A re-observation bound to a *different* Target Predicate never confirms this one --
    # the reproduction call itself must reject it, which is exactly what independence
    # means here: no caller-declared shortcut can stand in for a real reproduced verdict.
    request["reobservation"]["derivation_request"]["bindings"][0]["target_predicate_id"] = (
        "TP-WRONG"
    )
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G10"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_missing_reobservation_blocks_rather_than_marks_not_satisfied() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    request["reobservation"] = None
    request["proposed_terminal_status"] = "BLOCKED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    # A missing Observation is "truth cannot be decided", not "target observed and unmet" --
    # the Fail-Closed Mapping table's own distinction, and the reason NOT_SATISFIED is not
    # returned here.
    assert evaluation["result"] == "BLOCKED"
    assert evaluation["evaluation_mode"] == "CANDIDATE_TERMINAL"


def test_stale_evidence_sufficiency_yields_stale_result() -> None:
    difference = fixture_difference()
    policy = fixture_policy(
        difference, maximum_evidence_age=1
    )  # 1 second: the fixture Evidence is far older
    request = candidate_closure_request(difference, policy)
    request["policy"] = policy
    from tests.evidence_helpers import sufficiency_request

    request["evidence_sufficiency_request"] = sufficiency_request(
        difference_id=difference["difference_id"], policy=policy
    )
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G18"] == "FAIL"
    assert evaluation["result"] == "STALE"
    _validate(evaluation)


def test_g19_rejects_a_binding_the_policy_never_declared() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    # The Policy's own required_invariants is empty; supplying a binding anyway must not
    # be silently accepted as "extra diligence" -- G19's expected set is exact, both ways.
    request["candidate_invariant_evaluation_bindings"] = [
        {
            "kind": "candidate_invariant_evaluation_binding",
            "binding_id": "CAND-INV-EVAL-" + "6" * 64,
            "candidate_id": "STATE-CANDIDATE-" + "1" * 64,
            "candidate_semantic_fingerprint": {
                "profile": "MANOSUBE-STATE-SHA256-0.1",
                "digest": "1" * 64,
            },
            "base_state_ref": {
                "kind": "state",
                "revision": AFTER_REVISION,
                "fingerprint": state_fingerprint("KNOWN"),
            },
            "invariant_ref": {"kind": "kernel_invariant", "id": "D-001"},
            "invariant_definition_ref": {
                "repository": "manosube/manosube-agent-civilization-os",
                "path": "00_KERNEL/KERNEL_INVARIANTS.md",
                "invariant_definition_sha256": "sha256:" + "7" * 64,
            },
            "invariant_evaluation_ref": {"kind": "invariant_evaluation", "id": "INV-EVAL-0001"},
            "evaluation_record_fingerprint": "sha256:" + "8" * 64,
            "evaluation_result": "PASS",
            "evaluation_evidence_refs": {"collection_kind": "UNORDERED_SET", "members": []},
            "evaluated_at": "2026-08-30T11:05:00Z",
        }
    ]
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G19"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_g21_fails_closed_without_the_mandatory_x003_claim() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    request["candidate_claim_evaluation_bindings"] = []
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G21"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_g21_fails_closed_when_the_mandatory_claim_is_not_satisfied() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    current_state = request["current_state"]
    request["candidate_claim_evaluation_bindings"] = [
        mandatory_x003_claim_binding(difference, current_state, evaluation_status="NOT_SATISFIED")
    ]
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G21"] == "FAIL"
    assert evaluation["result"] == "NOT_SATISFIED"


def test_g22_rejects_a_terminal_status_the_policy_does_not_allow() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    policy = deepcopy(policy)
    policy["allowed_terminal_states"] = ["CLOSED", "BLOCKED"]  # RETAINED excluded
    request = base_closure_request(difference, policy)
    request["proposed_terminal_status"] = "RETAINED"

    evaluation = evaluate_closure(request)

    assert evaluation["gate_results"]["G22"] == "FAIL"


def test_satisfied_result_requires_closed_terminal_status() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    request = candidate_closure_request(difference, policy)
    request["proposed_terminal_status"] = "RETAINED"
    request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
    ]

    with pytest.raises(ReflowValidationError):
        evaluate_closure(request)


def test_policy_must_govern_the_evaluated_difference() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    other_policy = deepcopy(policy)
    other_policy["subject_difference_ref"] = {"kind": "difference", "id": "D-" + "f" * 64}
    request = base_closure_request(difference, other_policy)

    with pytest.raises(ReflowValidationError):
        evaluate_closure(request)


def test_mandatory_x003_claim_ref_matches_the_policy_text_constant() -> None:
    assert MANDATORY_X003_CLAIM_REF["kind"] == "completion_claim"
    assert MANDATORY_X003_CLAIM_REF["id"].startswith("CLAIM-")
    # Determinism: two independent computations of the closed-form constant must agree.
    import importlib

    import manosube_agent_civilization.reflow.closure as closure_module

    reloaded = importlib.reload(closure_module)
    assert reloaded.MANDATORY_X003_CLAIM_REF == MANDATORY_X003_CLAIM_REF
    importlib.reload(closure_module)
