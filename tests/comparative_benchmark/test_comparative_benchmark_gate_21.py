"""Phase 21 Comparative Benchmark -- Gate 21 positive proof (Issue #89 section 9,
``ADOPT_PHASE_21_COMPARATIVE_BENCHMARK``): every one of the 7 required Gate 21 booleans is true
by direct evidence produced from one real, end-to-end run (:func:`tests.comparative_benchmark.
orchestrator.run_comparative_benchmark`, shared across this file via the session-scoped
``comparative_benchmark_run`` fixture -- see ``tests/comparative_benchmark/conftest.py``).

``SAME_AGENT_COMPARISON_AVAILABLE``, ``CONTROL_GROUPS_DEFINED``, ``METRICS_PREDECLARED``,
``RAW_RESULTS_PUBLIC``, ``FAILURES_INCLUDED``, ``THIRD_PARTY_REPRODUCIBLE``,
``CLAIMS_BOUNDED_BY_EVIDENCE``."""

from __future__ import annotations

import inspect
from typing import Any

from tests.fixtures import comparative_benchmark as cb

from manosube_agent_civilization.comparative_benchmark import route as cb_route
from manosube_agent_civilization.comparative_benchmark.engine import (
    aggregate_metrics,
    build_protocol_freeze,
    derive_bounded_claims,
)
from manosube_agent_civilization.comparative_benchmark.types import TASK_OUTCOMES

# --- SAME_AGENT_COMPARISON_AVAILABLE --------------------------------------------------------- #


def test_gate21_same_agent_comparison_available_by_declared_label_and_real_route(
    comparative_benchmark_run: dict[str, Any],
) -> None:
    protocol_freeze = comparative_benchmark_run["protocol_freeze"]
    groups = {g["comparison_group_id"]: g for g in protocol_freeze["comparison_groups"]}
    present = groups[cb.PRESENT_GROUP_ID]
    same_agent_absent = groups["claude_code_alone"]

    # The one real structural fact SAME_AGENT_COMPARISON_AVAILABLE rests on: the identical
    # declared Agent identity, present in one group and absent in the other.
    assert present["agent_label"] == same_agent_absent["agent_label"]
    assert present["mechanism_identity"] != same_agent_absent["mechanism_identity"]
    assert present["comparison_group_role"] == "MANOSUBE_PRESENT"
    assert same_agent_absent["comparison_group_role"] == "MANOSUBE_ABSENT"

    # The PRESENT group's own raw events came from the real natural route, never a stub: every
    # CLOSED task genuinely advanced this project's own committed State (a stub could not).
    store = comparative_benchmark_run["store"]
    from tests.fixtures import long_running_proof as lrp

    final_state = store.load_current(lrp.PROJECT_ID)
    closed_task_count = sum(
        1 for outcome in cb.PRESENT_TASK_PLAN.values() if outcome in ("CLOSED", "RETAINED")
    )
    assert final_state["state_revision"] >= closed_task_count
    reconstructed = store.reconstruct(lrp.PROJECT_ID)
    assert reconstructed == final_state


# --- CONTROL_GROUPS_DEFINED ------------------------------------------------------------------- #


def test_gate21_control_groups_defined_matches_issue_89_section_4() -> None:
    """The 4 comparison groups Issue #89 section 4 itself requires: ``Codex alone``, ``Claude
    Code alone``, ``existing agent framework``, ``MANOSUBE + the same Agent``."""

    groups = cb.comparison_groups()
    assert len(groups) == 4
    agent_families = {g["agent_label"]["agent_family"] for g in groups}
    assert agent_families == {"codex", "claude_code", "existing_agent_framework"}
    roles = {g["comparison_group_role"] for g in groups}
    assert roles == {"MANOSUBE_PRESENT", "MANOSUBE_ABSENT"}
    present_groups = [g for g in groups if g["comparison_group_role"] == "MANOSUBE_PRESENT"]
    assert len(present_groups) == 1
    absent_groups = [g for g in groups if g["comparison_group_role"] == "MANOSUBE_ABSENT"]
    assert len(absent_groups) == 3


# --- METRICS_PREDECLARED ----------------------------------------------------------------------- #


def test_gate21_metrics_predeclared_before_any_result_exists(
    comparative_benchmark_run: dict[str, Any],
) -> None:
    protocol_freeze = comparative_benchmark_run["protocol_freeze"]
    assert len(protocol_freeze["metric_definitions"]) >= 1
    assert len(protocol_freeze["numeric_thresholds"]) >= 1

    # Structural: build_protocol_freeze's own signature takes no raw_events/metrics/claims
    # parameter at all -- a protocol freeze cannot even be constructed *from* a result.
    freeze_params = set(inspect.signature(build_protocol_freeze).parameters)
    assert "raw_events" not in freeze_params
    assert "metrics" not in freeze_params
    assert "claims" not in freeze_params

    # The result bundle's own protocol_freeze_ref names exactly the freeze this run committed
    # first, before any task ran.
    result_bundle = comparative_benchmark_run["result_bundle"]
    assert (
        result_bundle["protocol_freeze_ref"]["protocol_freeze_id"]
        == protocol_freeze["protocol_freeze_id"]
    )


# --- RAW_RESULTS_PUBLIC ------------------------------------------------------------------------ #


def test_gate21_raw_results_public_durably_resolvable_from_the_ledger(
    comparative_benchmark_run: dict[str, Any],
) -> None:
    store = comparative_benchmark_run["store"]
    result_bundle = comparative_benchmark_run["result_bundle"]
    assert len(result_bundle["raw_events"]) >= 1

    resolved = cb_route.resolve_result_bundle(
        store, project_id=cb.PROJECT_ID, result_bundle_id=result_bundle["result_bundle_id"]
    )
    assert resolved == result_bundle
    assert resolved is not None
    assert resolved["raw_events"] == result_bundle["raw_events"]


# --- FAILURES_INCLUDED ------------------------------------------------------------------------- #


def test_gate21_failures_included_real_non_success_outcomes_present(
    comparative_benchmark_run: dict[str, Any],
) -> None:
    raw_events = comparative_benchmark_run["result_bundle"]["raw_events"]
    present_outcomes = {
        e["outcome"] for e in raw_events if e["comparison_group_id"] == cb.PRESENT_GROUP_ID
    }
    non_success = present_outcomes - {"COMPLETED_VERIFIED"}
    assert non_success, "expected at least one non-COMPLETED_VERIFIED outcome"
    assert non_success <= TASK_OUTCOMES
    assert {"REFUSED", "RETAINED_INCOMPLETE", "FAILED"} <= present_outcomes


# --- THIRD_PARTY_REPRODUCIBLE -------------------------------------------------------------------- #


def test_gate21_third_party_reproducible_independent_receipt_matches(
    comparative_benchmark_run: dict[str, Any],
) -> None:
    store = comparative_benchmark_run["store"]
    receipt = comparative_benchmark_run["reproduction_receipt"]
    assert receipt["agreement"] == "MATCH"
    assert receipt["reproducer_identity"]["is_original_author"] is False

    resolved = cb_route.resolve_reproduction_receipt(
        store,
        project_id=cb.PROJECT_ID,
        reproduction_receipt_id=receipt["reproduction_receipt_id"],
    )
    assert resolved == receipt


# --- CLAIMS_BOUNDED_BY_EVIDENCE + raw -> metric -> claim rederivation ------------------------- #


def test_gate21_claims_bounded_by_evidence_and_rederivation_matches_byte_for_byte(
    comparative_benchmark_run: dict[str, Any],
) -> None:
    protocol_freeze = comparative_benchmark_run["protocol_freeze"]
    result_bundle = comparative_benchmark_run["result_bundle"]

    declared_claim_ids = {c["claim_id"] for c in protocol_freeze["claim_vocabulary"]}
    stored_claim_ids = {c["claim_id"] for c in result_bundle["claims"]}
    assert stored_claim_ids == declared_claim_ids
    assert declared_claim_ids, "expected at least one predeclared claim"

    # Required rederivation proof: recompute aggregate_metrics/derive_bounded_claims
    # independently from the resolved bundle's own raw_events, and assert byte-equality
    # (RAW_TO_METRIC_TO_CLAIM_REDERIVATION_REQUIRED) with its stored metrics/claims.
    rederived_metrics = aggregate_metrics(result_bundle["raw_events"], protocol_freeze)
    assert rederived_metrics == result_bundle["metrics"]
    rederived_claims = derive_bounded_claims(rederived_metrics, protocol_freeze)
    assert rederived_claims == result_bundle["claims"]
