# WU1: Measurement & Statistics Contract

Tracks #116 / PR #117. Fixes where/how WU2's driver must observe stop, recovery, and
reconciliation events, and how Q4/Q5's success rates, exclusions, and confidence
intervals are computed — before any implementation, per PROTOCOL.md §5/§6/§7.

## A. Observation points — never from executor/dot self-report alone

Every timed event below is defined by **two independent clocks**, and the contract's
recorded value is the one that is durable and externally checkable, never a party's own
self-report of having done something.

| Event | Primary observation (durable, canonical) | Secondary cross-check | Forbidden substitute |
|---|---|---|---|
| Dispatch start | New `work_time_coordination_open` record (`opened_at`, `work_unit_ref`, `adapter_kind`) committed via the existing `work_time_transparency` owner (`01_SCHEMA/work_time_transparency/work_time_coordination_open.schema.json`) | Driver's own local send-timestamp for the dispatch call | dot's own "I started" message |
| Stop-request acceptance | Driver's own durable write of a `STOP_ACCEPTED` flag to its *own* run-state (test-harness-local, outside canonical Store) at the instant the stop control call returns a positive acknowledgment from whichever control surface SHUKOU's Reading A/B/C decision selects (per `DOTS_CONNECTIVITY_ASSESSMENT.md`: Activity-stop and Scheduled-disable are confirmed real, named controls; a synchronous, API-level stop is unconfirmed either way) | Pause confirms only the *main task* — Activity-stop (delegated work) and Scheduled-disable (recurring work) are separate, both required | A natural-language "okay, stopping" message with no control-surface confirmation |
| New-dispatch-stop | Zero new `work_time_coordination_open` records created for the frozen `run_id` after the stop-accepted timestamp, confirmed by re-querying the Store | Driver's own dispatch-loop internal halt flag | Absence of *visible* new work alone (a queued-but-not-yet-opened dispatch is not "stopped") |
| Worker termination | OS-level process-group exit observed by the driver's own process supervisor (same pattern as `development_binding/review_adapter.py`'s process-result collection: PID + start-time pair, not PID alone, to guard against PID reuse) | `work_time_coordination_terminal.terminal_outcome` | A worker's own exit-code report sent *before* actually exiting |
| Fault detection | `work_time_coordination_terminal.heartbeat_deadline_breached=true`, or the driver's own heartbeat-poll missing `next_progress_update_due_minutes` | External-service health probe (for a transport outage, case `TRANSPORT_OUTAGE`) | Silence alone without crossing the declared deadline |
| Recovery start | A new `work_time_coordination_open` opened for the same `work_unit_ref` lineage (or an explicit recovery work unit referencing the prior `open_ref`) | Driver's own recovery-attempt log entry | Any resend of the original change before reconciliation (see §B below) |
| Reconciliation completion | **Both** of: (1) Store state re-read (`load_current`/`read_current_consistent`) matching the expected post-condition fingerprint, **and** (2) independent re-read of the external side effect (GitHub API state of the actual PR/Issue/commit, or dots' own task/relay state) | — | Declaring reconciliation complete from (1) alone when the action had an external side effect, or from (2) alone ever |

**Invariant, binding on the WU2 driver, not merely advisory:** no dispatch may be
resent while the prior attempt's outcome is unknown. "Unknown" is resolved only by
completing the two-part reconciliation above, never by a timeout alone. This is the
same gate cases `COMMIT_ACK_UNKNOWN` / `TRANSPORT_OUTAGE` in `case-catalog.json` already
require; this contract makes the gate's two-part shape explicit so WU2 cannot implement
a resend path that checks only the Store side or only the external side.

### A.1 Clock-reference discipline (corrected in this revision)

A `work_time_coordination_open`/`_terminal` record's own timestamp proves only that
*the Kernel's own commit* happened at that instant — it does not by itself prove when a
dispatch actually reached dots, or when a stop actually reached dots' own control
surface, because those events happen on clocks this record never touches. Every
duration this contract reports must name which clock(s) produced its two endpoints:

```text
DRIVER_CLOCK       -- the WU2 harness host's own clock (used for send-time of any
                      control-surface call, and for its own receive-time of any
                      acknowledgment, whether human-relayed or connector-mediated)
STORE_CLOCK        -- whatever clock the composing route passes to
                      with_work_time_coordination (typically DRIVER_CLOCK already,
                      since the driver supplies it -- confirm this at WU2 build time
                      per OPEN_ITEMS.md item 8, never assume it)
GITHUB_API_CLOCK   -- the timestamp GitHub's own API returns on a resource
                      (created_at/updated_at), a clock this harness does not control
EXTERNAL_RELAY_CLOCK -- a human operator's or connector's own reported time, where
                      used, lowest-trust of the four
```

A duration whose two endpoints come from the **same** clock (e.g. `DRIVER_CLOCK` send
time vs. `DRIVER_CLOCK` receive time of the stop-acceptance acknowledgment) is reported
as-is. A duration that must mix clocks (e.g. `DRIVER_CLOCK` dispatch time vs.
`GITHUB_API_CLOCK` time of the resulting PR/comment) is reported with an explicit
`assumed_max_clock_skew_seconds` (a `RUN_MANIFEST_TEMPLATE.json` field, set once at
freeze, never tuned after seeing data) added as an error bar — never as a bare point
value implying precision the measurement does not have. `dispatch_stop_seconds_max=30`
and `controlled_worker_stop_seconds_max=60` (`case-catalog.json`) are evaluated against
same-clock durations only; a mixed-clock measurement that would otherwise violate the
ceiling is reported separately, tagged `MIXED_CLOCK_UNVERIFIED`, rather than silently
passed or failed by the single-clock gate.

## B. Success-rate denominator, exclusions, and confidence intervals

### Required attempt classification vs. run state (two separate fields — corrected in this revision)

A prior revision of this contract both said classification is "never assigned
retroactively from the outcome" and said `PENDING_HUMAN_APPROVAL` attempts are
"re-classified... once resolved" — a direct contradiction. This revision separates two
fields that were conflated into one:

```text
case_classification (fixed forever, assigned once at dispatch, from the frozen
manifest/case ID that produced the attempt -- never revised regardless of what
happens next):
  NORMAL_OPERATION
  INTENTIONAL_REFUSAL_TEST      (a fault/negative-control case from case-catalog.json)
  ENVIRONMENT_FAULT              (infra/runner/network failure, not a Kernel or dots defect)

run_state (mutable, tracks the attempt's own lifecycle, independent of its fixed
case_classification above):
  DISPATCHED
  PENDING_HUMAN_APPROVAL         (held, not failed -- see Q5's required 48h unattended window)
  RESOLVED                       (terminal; carries its own outcome field)
```

`run_state` itself is never force-set to a value other than the three above — an
attempt genuinely still `DISPATCHED`/`PENDING_HUMAN_APPROVAL` when the window closes
keeps that true value in its own record. What changes at window close is purely how
that attempt is *scored* for the denominator (see `UNRESOLVED_AT_WINDOW_CLOSE` below) —
a reporting-time computation over the frozen data, never a rewrite of the attempt's own
recorded history.

An attempt whose case ID names a fault case carries `case_classification=
INTENTIONAL_REFUSAL_TEST` for its entire life, even if its `run_state` passes through
`PENDING_HUMAN_APPROVAL` on the way to `RESOLVED`, and even if it happens to succeed or
fail in an unexpected way. A `NORMAL_OPERATION` attempt that times out is still
`case_classification=NORMAL_OPERATION`, `run_state=RESOLVED`, outcome `TIMEOUT` — never
reclassified away. Nothing about `case_classification` is ever revised after dispatch;
only `run_state` moves, and only forward.

### Denominator (Q5 success rate; case-catalog.json's `oracle_feasible_success_rate_min=0.95`)

**Corrected in this revision: the formula below previously named only
`NORMAL_OPERATION`, contradicting the very next bullet's own rule that
`ENVIRONMENT_FAULT` also counts by default.** The formula now matches the prose:

```text
AT WINDOW CLOSE (the frozen end of the Q5 soak window -- never an arbitrary earlier
instant chosen after seeing partial results):

DENOMINATOR = { attempts : case_classification IN {NORMAL_OPERATION, ENVIRONMENT_FAULT}
                           AND independent_oracle_judged_feasible == true
                           AND NOT independently_confirmed_excluded_environment_fault }

For every attempt in DENOMINATOR:
  outcome = attempt.recorded_outcome          if run_state == RESOLVED
          = UNRESOLVED_AT_WINDOW_CLOSE        if run_state != RESOLVED
                                                (still DISPATCHED or
                                                 PENDING_HUMAN_APPROVAL when the
                                                 window closed)

UNRESOLVED_AT_WINDOW_CLOSE counts as a NON-SUCCESS in the numerator. It is never
excluded, and never silently omitted by the attempt simply never reaching RESOLVED.
```

- `independent_oracle_judged_feasible` is decided **before** the attempt runs (oracle
  pre-registration, per PROTOCOL.md §7) — never decided after seeing the outcome. It is
  a property of the task, fixed alongside `case_classification`, not of `run_state`.
- **While the window is still open**, an attempt with `run_state == PENDING_HUMAN_APPROVAL`
  is correctly not yet scored — its pending duration is reported as a separate Q5
  metric, never silently dropped or counted as latency against the Kernel. This remains
  true during the campaign. **The correction is specifically about window close:** a
  prior revision of this contract left open exactly how an attempt that *never resolves
  before the window ends* gets scored, which is a loophole — an attempt that would score
  as a failure could be left `PENDING_HUMAN_APPROVAL` indefinitely and never counted
  against the success rate. The `UNRESOLVED_AT_WINDOW_CLOSE` rule above closes it: at
  the moment the frozen window ends, every denominator-eligible attempt is scored one
  way or the other, with no third option of remaining permanently unscored.
- `ENVIRONMENT_FAULT` attempts are **in the denominator by default** —
  PROTOCOL.md §6's own rule ("timeout/環境失敗を後から除かない") means an environment
  fault counts as a failure unless independently confirmed (by the oracle, from
  infrastructure logs external to both dots and the Kernel) to be outside both
  systems' control — in which case that specific attempt is additionally reported on a
  **parallel, explicitly-labeled "infrastructure-excluded" line** alongside the
  un-excluded headline number. Both numbers are always published together; the excluded
  one is never presented alone, and exclusion is decided per-attempt against disclosed
  infrastructure evidence, never by a blanket "all ENVIRONMENT_FAULT attempts" rule.
- `case_classification == INTENTIONAL_REFUSAL_TEST` attempts never enter this
  denominator regardless of `run_state`; they have their own 100%-required-refusal gate
  (PROTOCOL.md §6).

### Confidence interval method

- **Q4 (240-run paired comparison):** `case-catalog.json` fixes `analysis_unit=TASK`
  and cluster-bootstrap over the 40 tasks (3 repetitions per task are correlated, not
  120 independent samples). WU1 adopts this unchanged and specifies the
  implementation: resample **tasks with replacement** (never individual runs),
  recompute the paired primary-metric difference each resample, take the 2.5/97.5
  percentiles.
- **Q5 (168h soak, one continuous run) — corrected method.** Repetitions here are
  **not** independent trials — they are consecutive cycles in one continuous process,
  so a naive per-cycle binomial CI would understate variance from serial correlation (a
  bad hour tends to produce several bad cycles in a row). Partition the frozen soak
  window into non-overlapping fixed blocks (default 4 hours; the exact block length is
  a manifest field, set once at freeze time, never tuned after seeing data). **A prior
  revision of this contract then averaged each block's own success rate and bootstrapped
  over those per-block rates — this is a mean-of-ratios, not the pooled success rate,
  and is biased whenever blocks don't all carry the same denominator** (which they
  usually won't, since real work arrives unevenly). The corrected method: for each of
  `B` (manifest-fixed, default 10,000) bootstrap iterations, resample blocks **with
  replacement**, then compute `sum(successes across resampled blocks) /
  sum(denominator-eligible attempts across resampled blocks)` — a ratio of sums, never
  an average of per-block rates — and take the 2.5/97.5 percentiles of that statistic
  across iterations. `case-catalog.json`'s `success_rate_95_ci_lower_min=0.9` gate is
  evaluated against this corrected interval.
  - `random_seed` for the resampling is a manifest field, fixed once at freeze, never
    re-rolled after seeing data.
  - A block with zero denominator-eligible attempts contributes `(0, 0)` to that
    resample's sums (never a `NaN`/undefined rate propagated into the percentile
    calculation, and never silently dropped from the resample as if it hadn't been
    selected).
  - **Zero-failure edge case — corrected decision rule.** If the entire frozen window
    has zero failures among denominator-eligible attempts (after `UNRESOLVED_AT_
    WINDOW_CLOSE` scoring above), the block-bootstrap percentile interval degenerates
    at the boundary (point mass at 1.0). **A degenerate interval must never, by itself,
    satisfy `success_rate_95_ci_lower_min=0.9`** — reporting a lower bound of exactly
    1.0 claims more certainty than zero observed failures over a small, correlated
    sample can support.

    The report additionally computes the exact Clopper-Pearson (CP) lower bound over
    the pooled count, labeled explicitly: **CP assumes independent, identically
    distributed Bernoulli trials — an assumption this soak data's own block/serial
    structure does not establish and this cross-check does not resolve.** CP is used
    here only as a floor/sanity bound under that disclosed, unverified assumption, never
    presented as a correctly-specified analysis of the correlated data, and never as a
    substitute for addressing the correlation the block-bootstrap exists to handle.

    The zero-failure case is reported `PASS` on this gate **only if both**:
    1. the number of distinct blocks carrying at least one denominator-eligible attempt
       meets a manifest-fixed minimum (`min_blocks_for_zero_failure_pass`, default 20,
       set once at freeze, never lowered after seeing data) — a handful of all-success
       blocks is exactly the case where CP's independence assumption is least
       trustworthy, since most of the "sample" could share a single time-of-day or
       environmental cause; and
    2. the CP lower bound itself is `>= 0.9`.

    If either condition fails, the gate is reported `INCOMPLETE` (insufficient
    evidence to support a zero-failure PASS claim), **never `PASS`**, regardless of how
    high the raw pooled rate is. Both the degenerate bootstrap interval and the CP
    bound, with its assumption caveat, are always reported together — neither number is
    ever presented alone.
- Any run with fewer than 8 blocks (a soak barely past the 168h/4h minimum) reports the
  CI tagged `WIDE_CI_LOW_BLOCK_COUNT` alongside the number — never presented as equally
  precise as a well-powered run.

## C. What remains for WU2 (not WU1) to actually build

A concrete block-bootstrap/cluster-bootstrap implementation, the attempt-classification
recorder wired into the driver's own dispatch loop, and the dual (Store + external)
reconciliation check as an executable gate. WU1 fixes the contract these must satisfy;
WU2 is the harness that satisfies it.
