"""WU2: Q4/Q5 aggregation per
``docs/validation/dots_production_acceptance/MEASUREMENT_CONTRACT.md`` Sec.B.

The math here is not reinvented -- it is the same ratio-of-sums block bootstrap and
reference-only Clopper-Pearson check
``docs/validation/dots_production_acceptance/verification/verify_measurement_contract.py``
already validated against fixed fixtures (WU1-SR2/SR3); this module is that logic
promoted into a durable, importable, parameterized API with no literal fixture data
baked in. Pure statistics -- no Kernel/Store/dots/GitHub call anywhere.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import random


@dataclass(frozen=True)
class BootstrapCI:
    point: float
    ci_lower: float
    ci_upper: float
    n_estimates: int


def ratio_of_sums_block_bootstrap(
    blocks: Sequence[Mapping[str, int]],
    *,
    seed: int,
    iterations: int = 10000,
    alpha: float = 0.05,
) -> BootstrapCI:
    """MEASUREMENT_CONTRACT.md Sec.B, Q5 method: resample blocks with replacement, then
    for each resample compute ``sum(successes) / sum(totals)`` -- a ratio of sums, never
    a mean of per-block rates, for the CONFIDENCE INTERVAL. *blocks* items need
    ``successes``/``total`` keys; a block with ``total == 0`` contributes ``(0, 0)`` to
    a resample's sums rather than being dropped from the resample or producing a NaN.

    **Point-estimate fix:** ``point`` is the real, observed ``pooled_rate(blocks)`` --
    NOT the mean of the bootstrap resample estimates. The resample mean is a biased
    estimator of the pooled rate for a small number of blocks: for two blocks (1/1,
    94/99), the true pooled rate is 95/100 = 0.95, but the exact expectation over all 4
    equally-likely two-block resamples is 0.9623737... -- a materially different,
    biased number a prior revision of this function reported as "the point estimate"
    (see ``test_contract_aggregator.py``'s own regression test for this exact example).
    The resampling procedure itself is unchanged and is still exactly what the
    confidence interval (``ci_lower``/``ci_upper``) is computed from; only which number
    is labeled the point estimate changes."""

    if not blocks:
        raise ValueError("ratio_of_sums_block_bootstrap requires at least one block")
    rng = random.Random(seed)  # noqa: S311 -- statistical resampling, not security-sensitive
    estimates = []
    for _ in range(iterations):
        resample = [rng.choice(blocks) for _ in blocks]
        successes = sum(block["successes"] for block in resample)
        total = sum(block["total"] for block in resample)
        if total == 0:
            continue
        estimates.append(successes / total)
    if not estimates:
        raise ValueError("every bootstrap resample had zero total -- cannot form a CI")
    estimates.sort()
    lo_idx = int((alpha / 2) * len(estimates))
    hi_idx = int((1 - alpha / 2) * len(estimates)) - 1
    return BootstrapCI(
        point=pooled_rate(blocks),
        ci_lower=estimates[lo_idx],
        ci_upper=estimates[hi_idx],
        n_estimates=len(estimates),
    )


def pooled_rate(blocks: Sequence[Mapping[str, int]]) -> float:
    total = sum(block["total"] for block in blocks)
    if total == 0:
        raise ValueError("pooled_rate requires at least one attempt across blocks")
    return sum(block["successes"] for block in blocks) / total


def clopper_pearson_lower_bound_all_success(n: int, *, alpha: float = 0.05) -> float:
    """Exact Clopper-Pearson lower bound for the ``x == n`` (all-success) case only --
    the case ``MEASUREMENT_CONTRACT.md``'s zero-failure branch is defined over. Closed
    form: ``Beta(n, 1)`` has CDF ``y ** n``, so its ``alpha / 2`` quantile solves
    ``y ** n == alpha / 2``."""

    if n <= 0:
        raise ValueError("clopper_pearson_lower_bound_all_success requires n > 0")
    return (alpha / 2) ** (1 / n)


@dataclass(frozen=True)
class ZeroFailureGateReport:
    n_blocks: int
    pooled_n: int
    bootstrap_ci: tuple[float, float]
    cp_lower_reference_only: float
    reference_reliable: bool
    verdict: str  # always "INCOMPLETE" -- see module/function docstrings


def zero_failure_gate(
    blocks: Sequence[Mapping[str, int]],
    *,
    min_blocks_for_cp_reference: int = 20,
    seed: int,
    iterations: int = 10000,
    alpha: float = 0.05,
) -> ZeroFailureGateReport:
    """MEASUREMENT_CONTRACT.md Sec.B, zero-failure edge case (corrected, third pass): the
    verdict is ALWAYS ``"INCOMPLETE"``. A Clopper-Pearson lower bound assumes
    independent, identically distributed trials -- an assumption this contract does not
    establish for correlated soak-block data, so CP is reported only as a labeled,
    non-binding reference figure, never a PASS condition. *min_blocks_for_cp_reference*
    controls only whether that reference figure is additionally flagged unreliable
    (``reference_reliable=False``), never PASS vs. INCOMPLETE.

    Raises ``ValueError`` if *blocks* is not actually all-success -- this gate is defined
    only for that edge case; a mixed-outcome block set should use
    :func:`ratio_of_sums_block_bootstrap` directly instead."""

    if not blocks:
        raise ValueError("zero_failure_gate requires at least one block")
    total_n = sum(block["total"] for block in blocks)
    total_successes = sum(block["successes"] for block in blocks)
    if total_successes != total_n:
        raise ValueError(
            "zero_failure_gate is defined only for all-success blocks "
            f"(got {total_successes} successes out of {total_n})"
        )
    bootstrap = ratio_of_sums_block_bootstrap(blocks, seed=seed, iterations=iterations, alpha=alpha)
    cp_lower = clopper_pearson_lower_bound_all_success(total_n, alpha=alpha)
    return ZeroFailureGateReport(
        n_blocks=len(blocks),
        pooled_n=total_n,
        bootstrap_ci=(bootstrap.ci_lower, bootstrap.ci_upper),
        cp_lower_reference_only=cp_lower,
        reference_reliable=len(blocks) >= min_blocks_for_cp_reference,
        verdict="INCOMPLETE",
    )


@dataclass(frozen=True)
class PairedComparisonCI:
    point: float
    ci_lower: float
    ci_upper: float
    n_tasks: int


def cluster_bootstrap_paired_difference(
    task_results: Sequence[Mapping[str, float]],
    *,
    seed: int,
    iterations: int = 10000,
    alpha: float = 0.05,
) -> PairedComparisonCI:
    """MEASUREMENT_CONTRACT.md Sec.B, Q4 method: ``case-catalog.json`` fixes
    ``analysis_unit=TASK`` and cluster-bootstraps over the 40 tasks (the 3 repetitions
    per task are correlated, never treated as 120 independent samples). *task_results*
    items need ``baseline_rate``/``treatment_rate`` keys -- each task's own rate over
    its repetitions, precomputed by the driver before this call. This function resamples
    TASKS with replacement, never individual runs, and reports the point estimate and CI
    of the mean paired difference (``treatment_rate - baseline_rate``) across tasks."""

    if not task_results:
        raise ValueError("cluster_bootstrap_paired_difference requires at least one task")
    rng = random.Random(seed)  # noqa: S311 -- statistical resampling, not security-sensitive
    estimates = []
    for _ in range(iterations):
        resample = [rng.choice(task_results) for _ in task_results]
        diffs = [task["treatment_rate"] - task["baseline_rate"] for task in resample]
        estimates.append(sum(diffs) / len(diffs))
    estimates.sort()
    lo_idx = int((alpha / 2) * len(estimates))
    hi_idx = int((1 - alpha / 2) * len(estimates)) - 1
    point = sum(task["treatment_rate"] - task["baseline_rate"] for task in task_results) / len(task_results)
    return PairedComparisonCI(
        point=point,
        ci_lower=estimates[lo_idx],
        ci_upper=estimates[hi_idx],
        n_tasks=len(task_results),
    )
