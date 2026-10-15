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
   formula actually includes `ENVIRONMENT_FAULT` in the headline `DENOMINATOR` by
   default, including attempts that are independently confirmed excluded (a prior
   revision's formula had an `AND NOT independently_confirmed_excluded_...` clause
   *inside* the headline itself — backwards from this document's own prose, which has
   always said the un-excluded count is the headline). It also proves that an attempt
   still `PENDING_HUMAN_APPROVAL` when the window closes is scored as a non-success
   rather than indefinitely excluded, and that the separate, secondary
   `DENOMINATOR_INFRASTRUCTURE_EXCLUDED` reference number — which does remove the
   independently-excluded attempts — is reported alongside the headline, never in place
   of it.
2. **Ratio-of-sums bootstrap vs. the prior mean-of-rates bug** — proves the corrected
   aggregation is closer to the true pooled rate than the prior method, **on this one
   fixed, synthetic input**. This is a demonstration that the method is implemented as
   specified and behaves as expected in a controlled case — it is not a measurement of
   real operational performance, and it does not establish a general improvement
   factor (an earlier verbal summary of this kind of check overstated this as "~100x
   improvement" in general; that characterization has been withdrawn — see the script's
   own Section 2 output, which deliberately states only the exact numbers for this one
   input and explicitly disclaims a general performance claim).
3. **Zero-failure gate, many blocks** — proves that even with enough blocks for the
   Clopper-Pearson (CP) reference figure to be considered reliable, and a CP lower
   bound ≥ 0.9, the gate's verdict is `INCOMPLETE`, never `PASS`. A prior revision let
   CP serve as a PASS condition once a block-count threshold was met; this revision
   removes that path entirely, because disclosing that CP's i.i.d. assumption is
   unconfirmed does not make a verdict conditioned on it statistically confirmed.
4. **Zero-failure gate, few blocks** — proves the same `INCOMPLETE` verdict holds with
   too few blocks, and that the block-count threshold
   (`min_blocks_for_zero_failure_cp_reference`) now controls only whether the CP
   reference figure is additionally flagged `TOO_FEW_BLOCKS_FOR_REFERENCE` — it no
   longer controls PASS vs. INCOMPLETE, since PASS is not reachable through this gate
   under this contract at all.

None of this validates dots itself, validates the Kernel's real operational success
rate, or constitutes a WU3/WU4 run. It validates that WU1's own corrected contract text
is internally executable and behaves the way that text claims.

**SR3 correction note (this revision):** two issues survived the previous round. (1)
The denominator formula and this script's own Section 1 logic had the headline/reference
roles reversed relative to this document's own prose — fixed by making the headline
`DENOMINATOR` include every `ENVIRONMENT_FAULT` attempt unconditionally, with the
exclusion applied only inside the separate `DENOMINATOR_INFRASTRUCTURE_EXCLUDED`
reference number. (2) The zero-failure gate treated a Clopper-Pearson lower bound as a
PASS condition even though this document itself says the i.i.d. assumption CP requires
is not established for this data — fixed by making the gate's verdict always
`INCOMPLETE` and demoting CP to a labeled, non-binding reference figure.
