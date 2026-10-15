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
| Stop-request acceptance | Driver's own durable write of a `STOP_ACCEPTED` flag to its *own* run-state (test-harness-local, outside canonical Store) at the instant the stop control call returns a positive acknowledgment from the real control surface in use (per `DOTS_CONNECTIVITY_ASSESSMENT.md`: a human-relay log timestamp today, since no synchronous API-level stop exists) | None exists for dots today — pause confirms only the *main task*, never delegated/scheduled work by itself | A natural-language "okay, stopping" message with no control-surface confirmation |
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

## B. Success-rate denominator, exclusions, and confidence intervals

### Required attempt classification (every logged attempt carries exactly one)

```text
NORMAL_OPERATION
INTENTIONAL_REFUSAL_TEST      (a fault/negative-control case from case-catalog.json)
PENDING_HUMAN_APPROVAL         (held, not failed -- see Q5's required 48h unattended window)
ENVIRONMENT_FAULT              (infra/runner/network failure, not a Kernel or dots defect)
```

This classification is recorded **at dispatch time**, from the frozen manifest/case ID
that produced the attempt — never assigned retroactively from the outcome. An attempt
whose case ID names a fault case is `INTENTIONAL_REFUSAL_TEST` even if it happens to
succeed or fail in an unexpected way; a `NORMAL_OPERATION` attempt that times out is
still `NORMAL_OPERATION` with outcome `TIMEOUT`, never reclassified away afterward.

### Denominator (Q5 success rate; case-catalog.json's `oracle_feasible_success_rate_min=0.95`)

```text
DENOMINATOR = { attempts : classification == NORMAL_OPERATION
                           AND independent_oracle_judged_feasible == true }
```

- `independent_oracle_judged_feasible` is decided **before** the attempt runs (oracle
  pre-registration, per PROTOCOL.md §7) — never decided after seeing the outcome.
- `PENDING_HUMAN_APPROVAL` attempts are excluded from this denominator *while pending*
  and re-classified into it only once resolved; the pending duration itself is reported
  as a separate Q5 metric, never silently dropped or counted as latency against the
  Kernel.
- `ENVIRONMENT_FAULT` attempts are **not excluded** from the denominator by default —
  PROTOCOL.md §6's own rule ("timeout/環境失敗を後から除かない") means an environment
  fault counts as a failure unless independently confirmed (by the oracle, from
  infrastructure logs external to both dots and the Kernel) to be outside both
  systems' control — in which case it is reported on a **parallel, explicitly-labeled
  "infrastructure-excluded" line** alongside the un-excluded headline number. Both
  numbers are always published together; the excluded one is never presented alone.
- `INTENTIONAL_REFUSAL_TEST` attempts never enter this denominator; they have their own
  100%-required-refusal gate (PROTOCOL.md §6).

### Confidence interval method

- **Q4 (240-run paired comparison):** `case-catalog.json` fixes `analysis_unit=TASK`
  and cluster-bootstrap over the 40 tasks (3 repetitions per task are correlated, not
  120 independent samples). WU1 adopts this unchanged and specifies the
  implementation: resample **tasks with replacement** (never individual runs),
  recompute the paired primary-metric difference each resample, take the 2.5/97.5
  percentiles.
- **Q5 (168h soak, one continuous run):** repetitions here are **not** independent
  trials — they are consecutive cycles in one continuous process, so a naive per-cycle
  binomial CI would understate variance from serial correlation (a bad hour tends to
  produce several bad cycles in a row). WU1 fixes the method: partition the frozen soak
  window into non-overlapping fixed blocks (default 4 hours; the exact block length is
  a manifest field, set once at freeze time, never tuned after seeing data), compute
  the per-block success rate, and bootstrap over **blocks**, not individual cycles.
  `case-catalog.json`'s `success_rate_95_ci_lower_min=0.9` gate is evaluated against
  this block-bootstrap interval.
- Any run with fewer than 8 blocks (a soak barely past the 168h/4h minimum) reports the
  CI tagged `WIDE_CI_LOW_BLOCK_COUNT` alongside the number — never presented as equally
  precise as a well-powered run.

## C. What remains for WU2 (not WU1) to actually build

A concrete block-bootstrap/cluster-bootstrap implementation, the attempt-classification
recorder wired into the driver's own dispatch loop, and the dual (Store + external)
reconciliation check as an executable gate. WU1 fixes the contract these must satisfy;
WU2 is the harness that satisfies it.
