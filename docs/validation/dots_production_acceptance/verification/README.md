# WU1-SR2 design-validation artifacts

Tracks #116 / PR #117. **Scope disclaimer, read first:** everything in this directory
is a design-validation check of the *statistical and classification rules* described in
`../MEASUREMENT_CONTRACT.md` — it is not WU2 implementation code. It makes no Kernel
call, no Store call, no dots/GitHub connection, has no live effect, and is not part of
`tests/dots_production_acceptance/` (WU2's own future test-suite target per
`../WU2_PLAN.md`). It exists only so the corrected rules can be checked against
executable code and fixed, committed input data, rather than taken on faith from prose.

## What is here

| File | What it is |
|---|---|
| `verify_measurement_contract.py` | The verification script (Python 3 stdlib only, zero third-party dependencies, deterministic — fixed seed `20261015`). |
| `blocks_q5_realistic.json` | 42 fixed, literal `(successes, total)` blocks with unequal sizes, modeling a realistic 168h/4h-block Q5 soak. Generated once (seed 42, discarded after generation) and committed as literal data — not regenerated at verification time — so the input itself is inspectable and never depends on any RNG behaving identically across Python builds. |
| `blocks_zero_failure_pass.json` | 21 fixed, all-success blocks (pooled n=495) — exercises the zero-failure gate's PASS branch. |
| `blocks_zero_failure_incomplete.json` | 5 fixed, all-success blocks (pooled n=125) — exercises the zero-failure gate's INCOMPLETE branch (too few blocks, even though the Clopper-Pearson bound alone would read as a pass). |
| `attempts_denominator_demo.json` | 8 fixed synthetic attempts covering every classification/run_state/outcome combination the corrected denominator rule must handle (ordinary success/failure, still-pending-at-window-close, timeout, intentional-refusal-test, oracle-infeasible, environment-fault both included-by-default and independently-excluded). |
| `output.txt` | The exact, saved stdout of the command below, from this exact script and these exact input files. |

## Exact reproduction command

```sh
python3 docs/validation/dots_production_acceptance/verification/verify_measurement_contract.py
```

Run from the repository root at this PR's HEAD. Re-running it produces output
byte-identical to `output.txt` (verified with `diff` before committing — no
non-determinism, no system-clock or environment dependence anywhere in the script).

## What each section proves, and what it does not

1. **Denominator formula + `UNRESOLVED_AT_WINDOW_CLOSE`** — proves the corrected
   formula actually includes `ENVIRONMENT_FAULT` by default (the prior revision's
   formula omitted it, contradicting its own prose), that an attempt still
   `PENDING_HUMAN_APPROVAL` when the window closes is scored as a non-success rather
   than indefinitely excluded, and that an independently-excluded `ENVIRONMENT_FAULT`
   attempt moves to the parallel line rather than vanishing from both.
2. **Ratio-of-sums bootstrap vs. the prior mean-of-rates bug** — proves the corrected
   aggregation is closer to the true pooled rate than the prior method, **on this one
   fixed, synthetic input**. This is a demonstration that the method is implemented as
   specified and behaves as expected in a controlled case — it is not a measurement of
   real operational performance, and it does not establish a general improvement
   factor (an earlier verbal summary of this kind of check overstated this as "~100x
   improvement" in general; that characterization has been withdrawn — see the script's
   own Section 2 output, which deliberately states only the exact numbers for this one
   input and explicitly disclaims a general performance claim).
3. **Zero-failure PASS branch** — proves that with enough blocks (≥
   `min_blocks_for_zero_failure_pass`) and a Clopper-Pearson lower bound ≥ 0.9, the gate
   reports PASS, and that it reports the degenerate bootstrap interval and the CP bound
   together, never the bootstrap alone.
4. **Zero-failure INCOMPLETE branch** — proves that too few blocks forces INCOMPLETE
   even when the Clopper-Pearson bound alone would read as a pass, confirming the
   block-count condition is load-bearing and not redundant with the CP check.

None of this validates dots itself, validates the Kernel's real operational success
rate, or constitutes a WU3/WU4 run. It validates that WU1's own corrected contract text
is internally executable and behaves the way that text claims.
