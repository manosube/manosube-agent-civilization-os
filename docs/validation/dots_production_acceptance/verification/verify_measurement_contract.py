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
# Renamed from MIN_BLOCKS_FOR_ZERO_FAILURE_PASS (SR3): this threshold no longer gates a
# PASS verdict -- it only flags whether the reference-only CP figure is additionally
# unreliable. See MEASUREMENT_CONTRACT.md Sec.B, zero-failure edge case (third pass).
MIN_BLOCKS_FOR_ZERO_FAILURE_CP_REFERENCE = 20
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

    # headline = DENOMINATOR_ELIGIBLE in full (every ENVIRONMENT_FAULT attempt included,
    # regardless of independently_confirmed_excluded_environment_fault). This is the
    # exact SR3 fix: a prior revision of this script (matching the prior, buggy formula
    # in MEASUREMENT_CONTRACT.md) removed independently-excluded attempts from the
    # headline itself -- backwards from the contract's own prose, which has always said
    # the un-excluded count is the headline and the excluded one is only a reference.
    headline = []  # list of (id, outcome, is_success)
    infra_excluded_ids = []

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

        headline.append((a["id"], outcome, is_success))
        if cls == "ENVIRONMENT_FAULT" and a.get("environment_fault_independently_excluded"):
            infra_excluded_ids.append(a["id"])

    headline_successes = sum(x[2] for x in headline)
    # DENOMINATOR_INFRASTRUCTURE_EXCLUDED = DENOMINATOR_ELIGIBLE minus the
    # independently-confirmed-excluded attempts -- a reference number, reported
    # alongside the headline, never substituted for it.
    reference = [x for x in headline if x[0] not in infra_excluded_ids]
    reference_successes = sum(x[2] for x in reference)

    print(f"Headline denominator DENOMINATOR (ENVIRONMENT_FAULT included in full, "
          f"independently-excluded attempts NOT removed): {[x[0] for x in headline]}")
    print(f"Headline outcomes: {[(x[0], x[1]) for x in headline]}")
    print(f"Headline success rate: {headline_successes}/{len(headline)} "
          f"= {headline_successes/len(headline):.4f}")
    print(f"Reference DENOMINATOR_INFRASTRUCTURE_EXCLUDED (headline minus "
          f"{infra_excluded_ids}): {[x[0] for x in reference]}")
    print(f"Reference success rate: {reference_successes}/{len(reference)} "
          f"= {reference_successes/len(reference):.4f}  "
          f"(reported alongside, never substituted for, the headline number)")

    # Assertions proving the corrected rules actually hold:
    ids = [x[0] for x in headline]
    assert "A5" not in ids, "INTENTIONAL_REFUSAL_TEST (A5) must never enter the denominator"
    assert "A8" not in ids, "oracle-infeasible attempt (A8) must never enter the denominator"
    assert ("A3", "UNRESOLVED_AT_WINDOW_CLOSE", False) in headline, \
        "A3 (still PENDING_HUMAN_APPROVAL at window close) must be scored as a non-success, not left out"
    assert ("A6", "FAILED", False) in headline, \
        "A6 (ENVIRONMENT_FAULT, not independently excluded) must be in the headline denominator by default"
    assert "A7" in ids, \
        "A7 (ENVIRONMENT_FAULT, independently confirmed excluded) MUST still be in the HEADLINE " \
        "denominator -- this is the exact formula bug SR3 fixes: a prior revision removed it here"
    assert "A7" in infra_excluded_ids, \
        "A7 must be tracked as independently-excluded for the reference line"
    assert "A7" not in [x[0] for x in reference], \
        "A7 must be absent from the reference (infrastructure-excluded) denominator"
    assert "A6" in [x[0] for x in reference], \
        "A6 (not independently excluded) must remain in the reference denominator too"
    print("\nPASS: all 8 assertions hold -- the headline denominator includes every "
          "ENVIRONMENT_FAULT attempt regardless of independent exclusion, the reference "
          "denominator alone removes the independently-excluded ones, and "
          "UNRESOLVED_AT_WINDOW_CLOSE scoring behaves exactly as MEASUREMENT_CONTRACT.md now specifies.")


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


def zero_failure_gate_report(blocks: list[dict]) -> dict:
    """The CORRECTED (third-pass) zero-failure gate: the verdict is ALWAYS INCOMPLETE,
    because a CP lower bound computed under an undisclosed-as-unconfirmed independence
    assumption is a reference figure, never a PASS condition. The only thing the block
    count still controls is whether that reference figure is additionally flagged
    unreliable -- it no longer controls PASS vs. INCOMPLETE, because PASS is no longer
    reachable through this gate at all under this contract."""

    n_blocks = len(blocks)
    total_n = sum(b["total"] for b in blocks)
    total_succ = sum(b["successes"] for b in blocks)
    assert total_succ == total_n, "this fixture must be all-success by construction"

    boot = ratio_of_sums_bootstrap(blocks, seed=BOOTSTRAP_RANDOM_SEED, iterations=BOOTSTRAP_ITERATIONS)
    cp_lower = clopper_pearson_lower_bound_all_success(total_n)
    reference_reliable = n_blocks >= MIN_BLOCKS_FOR_ZERO_FAILURE_CP_REFERENCE

    return {
        "n_blocks": n_blocks,
        "total_n": total_n,
        "bootstrap_ci": (boot["ci_lower"], boot["ci_upper"]),
        "cp_lower": cp_lower,
        "reference_reliable": reference_reliable,
        "verdict": "INCOMPLETE",  # never anything else, regardless of n_blocks/cp_lower
    }


def section_3_zero_failure_many_blocks() -> None:
    print("\n" + "=" * 78)
    print("SECTION 3: zero-failure edge case -- many blocks (reference figure reliable, "
          "verdict still INCOMPLETE)")
    print("=" * 78)
    blocks = load_blocks("blocks_zero_failure_pass.json")
    r = zero_failure_gate_report(blocks)

    print(f"Input: {r['n_blocks']} all-success blocks, pooled n={r['total_n']}")
    print(f"Degenerate bootstrap CI: [{r['bootstrap_ci'][0]:.6f}, {r['bootstrap_ci'][1]:.6f}] "
          f"(point mass at 1.0 -- never used alone to declare anything)")
    print(f"CP_LOWER_BOUND_REFERENCE_ONLY_IID_NOT_ESTABLISHED (x=n={r['total_n']}): "
          f"{r['cp_lower']:.4f}")
    print(f"Block-count check: {r['n_blocks']} >= min_blocks_for_zero_failure_cp_reference="
          f"{MIN_BLOCKS_FOR_ZERO_FAILURE_CP_REFERENCE}: {r['reference_reliable']} "
          f"(reference figure NOT flagged TOO_FEW_BLOCKS_FOR_REFERENCE)")
    print(f"Gate verdict: {r['verdict']}  (NOT PASS -- a high CP lower bound over enough "
          f"blocks is still only a disclosed-assumption reference figure, never a "
          f"statistically confirmed judgment, since i.i.d. is not established for this data)")

    assert r["verdict"] == "INCOMPLETE", \
        "the gate must report INCOMPLETE even with many blocks and a high CP lower bound"
    assert r["reference_reliable"] is True, \
        "with >= 20 blocks the reference CP figure should NOT be flagged unreliable"
    print("\nPASS: even with enough blocks for a reliable CP reference figure and a CP "
          "lower bound >= 0.9, the verdict is INCOMPLETE, never PASS -- confirms CP is no "
          "longer usable as a PASS condition under this contract, full stop.")


def section_4_zero_failure_few_blocks() -> None:
    print("\n" + "=" * 78)
    print("SECTION 4: zero-failure edge case -- few blocks (reference figure additionally "
          "flagged unreliable, verdict still INCOMPLETE)")
    print("=" * 78)
    blocks = load_blocks("blocks_zero_failure_incomplete.json")
    r = zero_failure_gate_report(blocks)

    print(f"Input: {r['n_blocks']} all-success blocks, pooled n={r['total_n']}")
    print(f"CP_LOWER_BOUND_REFERENCE_ONLY_IID_NOT_ESTABLISHED: {r['cp_lower']:.4f}  "
          f"(numerically high, but that was never the point)")
    print(f"Block-count check: {r['n_blocks']} >= min_blocks_for_zero_failure_cp_reference="
          f"{MIN_BLOCKS_FOR_ZERO_FAILURE_CP_REFERENCE}: {r['reference_reliable']} "
          f"-> reference figure flagged TOO_FEW_BLOCKS_FOR_REFERENCE: {not r['reference_reliable']}")
    print(f"Gate verdict: {r['verdict']}  (same INCOMPLETE verdict as Section 3 -- the "
          f"block count here only adds an extra unreliability flag on the reference "
          f"number, it does not change PASS/INCOMPLETE, because PASS was never reachable)")

    assert r["verdict"] == "INCOMPLETE", "the gate must report INCOMPLETE with few blocks too"
    assert r["reference_reliable"] is False, \
        "with < 20 blocks the reference CP figure SHOULD be flagged TOO_FEW_BLOCKS_FOR_REFERENCE"
    print("\nPASS: with too few blocks, the gate still reports INCOMPLETE (same as Section "
          "3) and additionally flags the CP reference figure itself as unreliable -- "
          "confirms the block-count threshold now gates reference-figure reliability "
          "only, not PASS, which this gate no longer grants under any input.")


def main() -> None:
    section_1_denominator_demo()
    section_2_ratio_of_sums_vs_mean_of_rates()
    section_3_zero_failure_many_blocks()
    section_4_zero_failure_few_blocks()
    print("\n" + "=" * 78)
    print("ALL SECTIONS PASS")
    print("=" * 78)


if __name__ == "__main__":
    main()
