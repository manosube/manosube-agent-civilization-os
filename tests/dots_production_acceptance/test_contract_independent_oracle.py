"""Contract tests for independent_oracle.py per PROTOCOL.md Sec.7.

Tracks #116 (WU2). Confirms the oracle never substitutes the model's or the Kernel's
own claim for its own judgment, and never coerces UNKNOWN into a specific verdict.
"""

from __future__ import annotations

import pytest
from tests.dots_production_acceptance import independent_oracle as oracle


def test_pre_register_feasibility_requires_case_id_and_rationale() -> None:
    judgment = oracle.pre_register_feasibility("CASE-1", feasible=True, rationale="reachable target repo")
    assert judgment.case_id == "CASE-1"
    assert judgment.feasible is True
    assert judgment.judged_at

    with pytest.raises(oracle.IndependentOracleError):
        oracle.pre_register_feasibility("", feasible=True, rationale="x")
    with pytest.raises(oracle.IndependentOracleError):
        oracle.pre_register_feasibility("CASE-1", feasible=True, rationale="")


def test_judge_from_readback_default_axis_evaluator_reports_unknown_not_false() -> None:
    verdict = oracle.judge_from_readback(
        "CASE-1",
        model_claimed_outcome="SUCCEEDED",
        kernel_recorded_outcome="SUCCEEDED",
        external_readback={},
        expected_spec={},
    )
    assert set(verdict.axis_judgments) == set(oracle.EVALUATION_AXES)
    assert all(value is None for value in verdict.axis_judgments.values())
    # Nothing in expected_spec -> the oracle's own outcome judgment must be UNKNOWN,
    # never silently defaulted to NOT_SATISFIED.
    assert verdict.oracle_judged_outcome == "UNKNOWN"


def test_judge_from_readback_never_substitutes_model_or_kernel_claim_for_its_own_judgment() -> None:
    # Both the model and the Kernel claim success; the independent readback disagrees.
    # The oracle's own judgment must follow the readback, not either claim.
    verdict = oracle.judge_from_readback(
        "CASE-1",
        model_claimed_outcome="SUCCEEDED",
        kernel_recorded_outcome="SUCCEEDED",
        external_readback={"target_file_contents": "old content, unchanged"},
        expected_spec={
            "required_readback_keys": ["target_file_contents"],
            "check": lambda rb: rb["target_file_contents"] == "new content",
        },
    )
    assert verdict.oracle_judged_outcome == "NOT_SATISFIED"
    assert verdict.model_claimed_outcome == "SUCCEEDED"
    assert verdict.kernel_recorded_outcome == "SUCCEEDED"
    # No discrepancy_evaluator supplied -- the oracle's own SATISFIED/NOT_SATISFIED/
    # UNKNOWN vocabulary is never bare-string-compared against the model's/Kernel's own
    # differently-shaped vocabulary, so discrepancy is left unevaluated (None), not
    # guessed from a meaningless comparison.
    assert verdict.discrepancy is None


def test_judge_from_readback_discrepancy_only_computed_via_an_explicit_cross_vocabulary_evaluator() -> None:
    # A caller that DOES have a real mapping between vocabularies can supply one; only
    # then is discrepancy actually evaluated.
    def claims_success(outcome: str) -> bool:
        return outcome in ("SUCCEEDED", "SATISFIED")

    def disagrees(oracle_outcome: str, model_outcome: str, kernel_outcome: str) -> bool:
        return claims_success(oracle_outcome) != claims_success(model_outcome) or claims_success(
            oracle_outcome
        ) != claims_success(kernel_outcome)

    agreeing = oracle.judge_from_readback(
        "CASE-1",
        model_claimed_outcome="SUCCEEDED",
        kernel_recorded_outcome="SUCCEEDED",
        external_readback={"target_file_contents": "new content"},
        expected_spec={
            "required_readback_keys": ["target_file_contents"],
            "check": lambda rb: rb["target_file_contents"] == "new content",
        },
        discrepancy_evaluator=disagrees,
    )
    assert agreeing.oracle_judged_outcome == "SATISFIED"
    assert agreeing.discrepancy is False

    disagreeing = oracle.judge_from_readback(
        "CASE-1",
        model_claimed_outcome="SUCCEEDED",
        kernel_recorded_outcome="SUCCEEDED",
        external_readback={"target_file_contents": "old content, unchanged"},
        expected_spec={
            "required_readback_keys": ["target_file_contents"],
            "check": lambda rb: rb["target_file_contents"] == "new content",
        },
        discrepancy_evaluator=disagrees,
    )
    assert disagreeing.oracle_judged_outcome == "NOT_SATISFIED"
    assert disagreeing.discrepancy is True


def test_judge_from_readback_missing_required_key_is_unknown_never_not_satisfied() -> None:
    verdict = oracle.judge_from_readback(
        "CASE-1",
        model_claimed_outcome="SUCCEEDED",
        kernel_recorded_outcome="SUCCEEDED",
        external_readback={},
        expected_spec={
            "required_readback_keys": ["target_file_contents"],
            "check": lambda rb: rb["target_file_contents"] == "new content",
        },
    )
    assert verdict.oracle_judged_outcome == "UNKNOWN"


def test_judge_from_readback_check_exception_is_unknown_never_raises() -> None:
    verdict = oracle.judge_from_readback(
        "CASE-1",
        model_claimed_outcome="SUCCEEDED",
        kernel_recorded_outcome="SUCCEEDED",
        external_readback={"x": 1},
        expected_spec={"required_readback_keys": ["x"], "check": lambda rb: rb["y"]},
    )
    assert verdict.oracle_judged_outcome == "UNKNOWN"


def test_judge_from_readback_custom_axis_evaluator_is_used_per_axis() -> None:
    calls: list[str] = []

    def evaluator(axis: str, readback: dict, spec: dict) -> bool | None:
        calls.append(axis)
        return axis == "evidence_completeness"

    verdict = oracle.judge_from_readback(
        "CASE-1",
        model_claimed_outcome="SUCCEEDED",
        kernel_recorded_outcome="SUCCEEDED",
        external_readback={},
        expected_spec={},
        axis_evaluator=evaluator,
    )
    assert set(calls) == set(oracle.EVALUATION_AXES)
    assert verdict.axis_judgments["evidence_completeness"] is True
    assert verdict.axis_judgments["rework"] is False


def test_judge_from_readback_requires_case_id() -> None:
    with pytest.raises(oracle.IndependentOracleError):
        oracle.judge_from_readback(
            "",
            model_claimed_outcome="SUCCEEDED",
            kernel_recorded_outcome="SUCCEEDED",
            external_readback={},
            expected_spec={},
        )
