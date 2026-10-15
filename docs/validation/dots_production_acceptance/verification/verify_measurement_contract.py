#!/usr/bin/env python3
"""Design-validation script for MEASUREMENT_CONTRACT.md's statistical/classification
rules (WU1-SR2, Issue #116 / PR #117).

SCOPE DISCLAIMER: this is NOT a WU2 implementation artifact. It makes no Kernel call,
no Store call, no dots/GitHub connection, and is not part of tests/dots_production_
acceptance/ (WU2's own future test suite target per WU2_PLAN.md). It exists solely to
prove, with executable code and fixed, committed input data, that the corrected rules
described in MEASUREMENT_CONTRACT.md Sec.B actually compute what that document claims
they compute -- so a reviewer (Codex, at a fixed SHA) can re-run it and get the
identical printed output, rather than re-deriving the math from prose alone.

Dependencies: Python 3 standard library only (no scipy, no third-party packages) --
deliberately, so reproduction never depends on what happens to be `pip install`-able in
the reviewing environment. The exact Clopper-Pearson lower bound for the all-successes
case (x = n) has a closed form requiring no special-function library at all:

    Beta(n, 1) has CDF F(y) = y**n on [0, 1], so its alpha/2 quantile solves
    y**n = alpha/2  =>  y = (alpha/2) ** (1/n)

which is exactly the case this contract's own "zero-failure edge case" is defined
over (zero observed failures = x equals n), so no incomplete-beta-inverse
approximation is needed anywhere in this script.

Run with:
    python3 docs/validation/dots_production_acceptance/verification/verify_measurement_contract.py

Exact saved output of that command, from this exact script and these exact input
files, is committed alongside as output.txt.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Fixed at the top of the script, not re-rolled per run -- mirrors
# RUN_MANIFEST_TEMPLATE.json's own bootstrap_random_seed field being a frozen,
# disclosed manifest value, never tuned after seeing data.
BOOTSTRAP_RANDOM_SEED = 20261015
BOOTSTRAP_ITERATIONS = 10000
MIN_BLOCKS_FOR_ZERO_FAILURE_PASS = 20
CI_ALPHA = 0.05


def load_blocks(name: str) -> list[dict]:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def ratio_of_sums_bootstrap(blocks: list[dict], *, seed: int, iterations: int) -> dict:
    """The CORRECTED method: resample blocks with replacement, then for each resample
    compute sum(successes)/sum(totals) -- a ratio of sums, never an average of
    per-block rates."""

    rng = random.Random(seed)
    estimates = []
    for _ in range(iterations):
        resample = [rng.choice(blocks) for _ in blocks]
        succ = sum(b["successes"] for b in resample)
        tot = sum(b["total"] for b in resample)
        # A block with zero denominator-eligible attempts contributes (0, 0) to the
        # resample's sums (never a NaN propagated, never silently dropped) -- there is
        # no such block in these fixtures, but the guard matches the contract's own
        # stated rule.
        if tot == 0:
            continue
        estimates.append(succ / tot)
    estimates.sort()
    lo_idx = int((CI_ALPHA / 2) * len(estimates))
    hi_idx = int((1 - CI_ALPHA / 2) * len(estimates)) - 1
    return {
        "point": sum(estimates) / len(estimates),
        "ci_lower": estimates[lo_idx],
        "ci_upper": estimates[hi_idx],
        "n_estimates": len(estimates),
    }


def mean_of_rates(blocks: list[dict]) -> float:
    """The PRIOR, INCORRECT method this revision replaces -- kept here only to prove,
    by direct comparison, that the correction actually changes the computed number."""

    return sum(b["successes"] / b["total"] for b in blocks) / len(blocks)


def pooled_rate(blocks: list[dict]) -> float:
    return sum(b["successes"] for b in blocks) / sum(b["total"] for b in blocks)


def clopper_pearson_lower_bound_all_success(n: int, *, alpha: float = CI_ALPHA) -> float:
    """Exact Clopper-Pearson lower bound for x successes out of n trials, restricted to
    the x == n (all-success) case this contract's zero-failure edge case is defined
    over. Closed form, no dependencies -- see module docstring for the derivation."""

    return (alpha / 2) ** (1 / n)


def section_1_denominator_demo() -> None:
    print("=" * 78)
    print("SECTION 1: denominator formula + UNRESOLVED_AT_WINDOW_CLOSE scoring")
    print("=" * 78)
    attempts = json.loads((HERE / "attempts_denominator_demo.json").read_text(encoding="utf-8"))

    headline_denominator = []
    headline_successes = 0
    excluded_line_denominator = []
    excluded_line_successes = 0

    for a in attempts:
        cls = a["case_classification"]
        if cls == "INTENTIONAL_REFUSAL_TEST":
            continue  # never enters any denominator here, regardless of run_state
        if not a["oracle_feasible"]:
            continue  # oracle-infeasible tasks never enter the denominator
        if cls not in ("NORMAL_OPERATION", "ENVIRONMENT_FAULT"):
            continue

        if a["run_state"] == "RESOLVED":
            outcome = a["outcome"]
        else:
            outcome = "UNRESOLVED_AT_WINDOW_CLOSE"
        is_success = outcome == "SUCCEEDED"

        if cls == "ENVIRONMENT_FAULT" and a.get("environment_fault_independently_excluded"):
            excluded_line_denominator.append(a["id"])
            excluded_line_successes += int(is_success)
            continue  # on the parallel excluded line, not the headline denominator

        headline_denominator.append((a["id"], outcome))
        headline_successes += int(is_success)

    print(f"Headline denominator (ENVIRONMENT_FAULT included by default): "
          f"{[x[0] for x in headline_denominator]}")
    print(f"Headline outcomes: {headline_denominator}")
    print(f"Headline success rate: {headline_successes}/{len(headline_denominator)} "
          f"= {headline_successes/len(headline_denominator):.4f}")
    print(f"Parallel infrastructure-excluded line: {excluded_line_denominator} "
          f"(reported alongside, never replacing, the headline number)")

    # Assertions proving the corrected rules actually hold:
    assert "A5" not in [x[0] for x in headline_denominator], \
        "INTENTIONAL_REFUSAL_TEST (A5) must never enter the denominator"
    assert "A8" not in [x[0] for x in headline_denominator], \
        "oracle-infeasible attempt (A8) must never enter the denominator"
    assert ("A3", "UNRESOLVED_AT_WINDOW_CLOSE") in headline_denominator, \
        "A3 (still PENDING_HUMAN_APPROVAL at window close) must be scored as a non-success, not left out"
    assert ("A6", "FAILED") in headline_denominator, \
        "A6 (ENVIRONMENT_FAULT, not independently excluded) must be in the HEADLINE denominator by default -- this is the exact formula bug this revision fixes"
    assert "A7" in excluded_line_denominator, \
        "A7 (ENVIRONMENT_FAULT, independently confirmed excluded) must be on the parallel excluded line"
    assert "A7" not in [x[0] for x in headline_denominator], \
        "A7 must NOT also appear in the headline denominator once independently excluded"
    print("\nPASS: all 6 assertions hold -- the corrected denominator formula and the "
          "UNRESOLVED_AT_WINDOW_CLOSE rule behave exactly as MEASUREMENT_CONTRACT.md now specifies.")


def section_2_ratio_of_sums_vs_mean_of_rates() -> None:
    print("\n" + "=" * 78)
    print("SECTION 2: corrected ratio-of-sums bootstrap vs. the prior mean-of-rates bug")
    print("=" * 78)
    blocks = load_blocks("blocks_q5_realistic.json")
    true_rate = pooled_rate(blocks)
    wrong = mean_of_rates(blocks)
    boot = ratio_of_sums_bootstrap(blocks, seed=BOOTSTRAP_RANDOM_SEED, iterations=BOOTSTRAP_ITERATIONS)

    print(f"Input: {len(blocks)} blocks (docs/.../verification/blocks_q5_realistic.json), "
          f"unequal sizes (total attempts per block: {sorted({b['total'] for b in blocks})})")
    print(f"True pooled rate (sum successes / sum totals):         {true_rate:.4f}")
    print(f"WRONG method (mean of per-block rates):                {wrong:.4f}  "
          f"(error: {wrong - true_rate:+.4f})")
    print(f"CORRECTED method (ratio-of-sums bootstrap, seed={BOOTSTRAP_RANDOM_SEED}, "
          f"B={BOOTSTRAP_ITERATIONS}):")
    print(f"  point estimate: {boot['point']:.4f}  (error: {boot['point'] - true_rate:+.4f})")
    print(f"  95% CI: [{boot['ci_lower']:.4f}, {boot['ci_upper']:.4f}]")

    assert abs(boot["point"] - true_rate) < abs(wrong - true_rate), (
        "the corrected method must be closer to the true pooled rate than the wrong "
        "mean-of-rates method on this fixed input"
    )
    print("\nPASS: corrected method's error is smaller than the wrong method's error on "
          "this fixed input (exact numbers above, not a general claim about 'percent "
          "improvement' -- this is one deterministic input, not an operational-performance claim).")


def section_3_zero_failure_pass_case() -> None:
    print("\n" + "=" * 78)
    print("SECTION 3: zero-failure edge case -- PASS branch (enough blocks)")
    print("=" * 78)
    blocks = load_blocks("blocks_zero_failure_pass.json")
    n_blocks = len(blocks)
    total_n = sum(b["total"] for b in blocks)
    total_succ = sum(b["successes"] for b in blocks)
    assert total_succ == total_n, "this fixture must be all-success by construction"

    boot = ratio_of_sums_bootstrap(blocks, seed=BOOTSTRAP_RANDOM_SEED, iterations=BOOTSTRAP_ITERATIONS)
    cp_lower = clopper_pearson_lower_bound_all_success(total_n)

    print(f"Input: {n_blocks} all-success blocks, pooled n={total_n}")
    print(f"Degenerate bootstrap CI: [{boot['ci_lower']:.6f}, {boot['ci_upper']:.6f}] "
          f"(point mass at 1.0, exactly the failure mode the contract warns about -- "
          f"NEVER used alone to declare PASS)")
    print(f"Exact Clopper-Pearson 95% lower bound (x=n={total_n}), "
          f"CP_ASSUMES_IID_NOT_ESTABLISHED_FOR_THIS_DATA: {cp_lower:.4f}")
    print(f"Block-count check: {n_blocks} >= min_blocks_for_zero_failure_pass="
          f"{MIN_BLOCKS_FOR_ZERO_FAILURE_PASS}: {n_blocks >= MIN_BLOCKS_FOR_ZERO_FAILURE_PASS}")

    verdict = (
        "PASS"
        if n_blocks >= MIN_BLOCKS_FOR_ZERO_FAILURE_PASS and cp_lower >= 0.9
        else "INCOMPLETE"
    )
    print(f"Gate verdict per the corrected decision rule: {verdict}")
    assert verdict == "PASS", "this fixture is constructed to satisfy both conditions"
    print("\nPASS: with enough blocks AND a CP lower bound >= 0.9, the corrected rule "
          "reports PASS -- never from the degenerate bootstrap interval alone.")


def section_4_zero_failure_incomplete_case() -> None:
    print("\n" + "=" * 78)
    print("SECTION 4: zero-failure edge case -- INCOMPLETE branch (too few blocks)")
    print("=" * 78)
    blocks = load_blocks("blocks_zero_failure_incomplete.json")
    n_blocks = len(blocks)
    total_n = sum(b["total"] for b in blocks)
    total_succ = sum(b["successes"] for b in blocks)
    assert total_succ == total_n, "this fixture must be all-success by construction"

    cp_lower = clopper_pearson_lower_bound_all_success(total_n)
    print(f"Input: {n_blocks} all-success blocks, pooled n={total_n}")
    print(f"Exact Clopper-Pearson 95% lower bound: {cp_lower:.4f}  "
          f"(this alone looks like it would pass -- that is exactly why block count must ALSO gate)")
    print(f"Block-count check: {n_blocks} >= min_blocks_for_zero_failure_pass="
          f"{MIN_BLOCKS_FOR_ZERO_FAILURE_PASS}: {n_blocks >= MIN_BLOCKS_FOR_ZERO_FAILURE_PASS}")

    verdict = (
        "PASS"
        if n_blocks >= MIN_BLOCKS_FOR_ZERO_FAILURE_PASS and cp_lower >= 0.9
        else "INCOMPLETE"
    )
    print(f"Gate verdict per the corrected decision rule: {verdict}")
    assert verdict == "INCOMPLETE", (
        "with only 5 blocks (< 20), the gate must report INCOMPLETE even though the "
        "CP lower bound alone would read as a pass -- this is the exact case the "
        "block-count condition exists to catch"
    )
    print("\nPASS: too few blocks correctly forces INCOMPLETE even though the Clopper-Pearson "
          "bound alone would have looked like a pass -- confirms the two-condition rule "
          "is load-bearing, not redundant with the CP check alone.")


def main() -> None:
    section_1_denominator_demo()
    section_2_ratio_of_sums_vs_mean_of_rates()
    section_3_zero_failure_pass_case()
    section_4_zero_failure_incomplete_case()
    print("\n" + "=" * 78)
    print("ALL SECTIONS PASS")
    print("=" * 78)


if __name__ == "__main__":
    main()
