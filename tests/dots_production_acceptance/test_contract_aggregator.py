"""Contract tests for aggregator.py -- the promoted MEASUREMENT_CONTRACT.md Sec.B logic.

Tracks #116 (WU2). Pure statistics; no Kernel/Store/dots/GitHub call anywhere.
"""

from __future__ import annotations

import pytest
from tests.dots_production_acceptance import aggregator as agg


def test_ratio_of_sums_beats_mean_of_rates_on_unequal_sized_blocks() -> None:
    # Unequal block sizes are exactly where mean-of-rates (the bug WU1-SR1 fixed)
    # diverges from the true pooled rate.
    blocks = [
        {"successes": 2, "total": 2},
        {"successes": 5, "total": 5},
        {"successes": 38, "total": 40},
    ]
    true_rate = agg.pooled_rate(blocks)
    wrong = sum(b["successes"] / b["total"] for b in blocks) / len(blocks)
    boot = agg.ratio_of_sums_block_bootstrap(blocks, seed=7, iterations=5000)

    assert abs(boot.point - true_rate) < abs(wrong - true_rate)


def test_ratio_of_sums_block_bootstrap_requires_at_least_one_block() -> None:
    with pytest.raises(ValueError, match="at least one block"):
        agg.ratio_of_sums_block_bootstrap([], seed=1)


def test_clopper_pearson_lower_bound_increases_toward_one_with_more_trials() -> None:
    low_n = agg.clopper_pearson_lower_bound_all_success(5)
    high_n = agg.clopper_pearson_lower_bound_all_success(500)
    assert 0.0 < low_n < high_n < 1.0


@pytest.mark.parametrize("n_blocks", [5, 21])
def test_zero_failure_gate_verdict_is_always_incomplete_regardless_of_block_count(n_blocks: int) -> None:
    blocks = [{"successes": 20, "total": 20} for _ in range(n_blocks)]
    report = agg.zero_failure_gate(blocks, seed=1, min_blocks_for_cp_reference=20)

    # The exact SR3 fix: PASS must never be reachable through this gate, no matter how
    # many blocks or how high the CP lower bound reads.
    assert report.verdict == "INCOMPLETE"
    assert report.n_blocks == n_blocks
    assert 0.0 < report.cp_lower_reference_only < 1.0


def test_zero_failure_gate_reference_reliable_flag_tracks_block_count_only() -> None:
    many_blocks = [{"successes": 20, "total": 20} for _ in range(21)]
    few_blocks = [{"successes": 20, "total": 20} for _ in range(5)]

    many = agg.zero_failure_gate(many_blocks, seed=1, min_blocks_for_cp_reference=20)
    few = agg.zero_failure_gate(few_blocks, seed=1, min_blocks_for_cp_reference=20)

    assert many.reference_reliable is True
    assert few.reference_reliable is False
    # Both are INCOMPLETE regardless -- the flag affects reference-figure reliability
    # only, never the verdict.
    assert many.verdict == few.verdict == "INCOMPLETE"


def test_zero_failure_gate_refuses_a_mixed_outcome_block_set() -> None:
    blocks = [{"successes": 19, "total": 20}]
    with pytest.raises(ValueError, match="defined only for all-success blocks"):
        agg.zero_failure_gate(blocks, seed=1)


def test_cluster_bootstrap_paired_difference_resamples_tasks_not_runs() -> None:
    task_results = [
        {"baseline_rate": 0.5, "treatment_rate": 0.9},
        {"baseline_rate": 0.4, "treatment_rate": 0.8},
        {"baseline_rate": 0.6, "treatment_rate": 0.6},
    ]
    ci = agg.cluster_bootstrap_paired_difference(task_results, seed=3, iterations=5000)

    expected_point = sum(t["treatment_rate"] - t["baseline_rate"] for t in task_results) / len(task_results)
    assert ci.point == pytest.approx(expected_point)
    assert ci.n_tasks == 3
    assert ci.ci_lower <= ci.point <= ci.ci_upper


def test_bootstrap_is_deterministic_for_a_fixed_seed() -> None:
    blocks = [{"successes": 9, "total": 10} for _ in range(10)]
    first = agg.ratio_of_sums_block_bootstrap(blocks, seed=42, iterations=2000)
    second = agg.ratio_of_sums_block_bootstrap(blocks, seed=42, iterations=2000)
    assert first == second
