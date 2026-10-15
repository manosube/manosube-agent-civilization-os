# WU1 output: WU2 change targets, implementation order, verification steps

Tracks #116 / PR #117. This is a plan for WU2 — it authorizes no WU2 implementation
code itself.

## Change targets (new paths only; no existing Kernel owner is modified)

```text
docs/validation/dots_production_acceptance/   (this directory -- WU1 outputs, extended by WU2 with real run data)
tests/dots_production_acceptance/
  driver.py              -- dispatch loop, stop/reconcile gate (Measurement Contract SS A)
  dots_adapter.py        -- the human-relay adapter (Connectivity Assessment SS6); never a
                            second State/Authority/Evidence/Reflow owner
  independent_oracle.py  -- readback/probe judging per PROTOCOL.md SS7, never trusting
                            Kernel closure as its own ground truth
  case_generators.py     -- materializes case-catalog.json's 24 fault cases + Q4's 40
                            distinct task fixtures (8 strata x 5 tasks each = 40 tasks,
                            never 40 x 8) into concrete, runnable fixtures; the 240 Q4
                            *runs* come from those same 40 tasks x 3 repetitions x 2
                            conditions, not from a larger fixture count
  aggregator.py          -- block/cluster bootstrap per Measurement Contract SS B
  recorder.py            -- raw receipts to the source-tree-external evidence root
                            (PROTOCOL.md SS8); writes hash manifests only into source tree
  test_contract_*.py     -- contract tests proving the driver/adapter/oracle themselves
                            obey this WU1 contract (never a second copy of Kernel tests)
cli entry points (deferred to WU2, contract fixed by case-catalog.json SS4):
  preflight / freeze / run / reconcile / recompute / report
```

Adapter responsibility mapping, from `DOTS_CONNECTIVITY_ASSESSMENT.md` (revised: the
prior version of this plan committed to a human-relay-only adapter design before
`DOTS_CONNECTIVITY_ASSESSMENT.md`'s own correction reopened Readings A/C via the
confirmed GitHub connector/Activity view -- WU2 must not re-commit to one design
prematurely either):

```text
read_state             -> CANDIDATE CHANNELS, not yet selected: (a) GitHub
                           Issue/PR state dots' own connector can read once a human
                           sets the goal, relayed into the driver by whichever means
                           SHUKOU selects; (b) a human-operator relay as fallback if (a)
                           cannot be triggered without a human-authored prompt each time
submit_candidate       -> same two-channel candidacy as read_state; never a direct
                           Store/Difference write regardless of channel
dispatch_authorized_work -> existing Issue/handoff mechanism (Reading A/C) OR explicit
                           amended policy admitting a new executor path (Reading B) --
                           three readings open, see OPEN_ITEMS.md item 1
collect_receipt         -> Activity (confirmed real feature) and/or human-operator
                           transcription, cross-checked against the driver's own durable
                           work_time_coordination records -- never either alone, per
                           Measurement Contract SS A
stop_and_reconcile       -> driver-enforced dual gate (Measurement Contract SS A); pause,
                           Activity-stop, and Scheduled-disable are three distinct
                           controls, all three exercised and confirmed, never conflated
```

WU2's own first deliverable regarding this adapter is therefore not "build the
human-relay adapter" but "determine, with SHUKOU, which of Readings A/B/C is in scope,
and whether channel (a) above is reachable by an automated harness at all" --
`dots_adapter.py`'s actual shape depends on that answer.

## Implementation order

1. `recorder.py` + evidence-root layout first — every later component writes through it;
   getting the source-tree-external/hash-manifest boundary right first avoids rework.
2. `independent_oracle.py` — pre-registers feasibility/ground-truth judgments *before*
   any case runs, per PROTOCOL.md SS7; must exist before `driver.py` can classify any
   attempt.
3. `driver.py` — the dispatch loop + stop/reconcile gate (Measurement Contract SS A),
   against the real `work_time_transparency`/Store owners, with `dots_adapter.py` stubbed
   to a fixed fixture response first (no live dots yet) — proves the gate's shape before
   any real external dependency is introduced.
4. `case_generators.py` — the 24 fault cases first (Q2), since they exercise the gate
   built in step 3 most directly; the Q4 generator afterward (40 distinct task fixtures,
   8 strata x 5 tasks each; 240 runs = 40 tasks x 3 repetitions x 2 conditions, computed
   from those 40, never a separate 320-fixture set), reusing
   `examples/false_completion/PROTOCOL.md`'s own strata/task design rather than inventing
   a second one.
5. `aggregator.py` — block/cluster bootstrap, testable entirely offline against
   synthetic data generated by `case_generators.py`, before any real run exists.
6. `dots_adapter.py` last, once the rest of the harness already passes its own contract
   tests against the stub, and once SHUKOU's Reading A/B/C decision and the
   channel-(a)-vs-(b) question above are both resolved — minimizes how much of the
   harness depends on an unconfirmed external surface while it's being built, and
   avoids building an adapter shape that has to be thrown away once that decision lands.
7. `tests/dots_production_acceptance/test_contract_*.py` throughout steps 1–6, not
   appended afterward — each component above ships with its own contract test proving it
   obeys this WU1 document, mirroring how every existing Kernel owner in this repo is
   proven (e.g. `tests/integration/binding/test_bounded_technical_review_route.py`'s own
   pattern).

## Verification steps (WU2's own delivery gate, not WU1's)

1. `ruff check` / `ruff format` on every new file.
2. `source_impact_gate` against the then-current `main` for every changed/added path.
3. Full `tests/dots_production_acceptance/` suite green, offline (stubbed adapter) —
   zero live dots calls required to prove the harness itself is correct.
4. A **dry-run** of `case_generators.py` against `case-catalog.json` producing exactly
   24 fault-case fixtures + 40 Q4 task fixtures (8 strata × 5 tasks each) with no
   duplicate `case_id`s or task IDs — a pure data-shape check, no execution. The 240 Q4
   *runs* (40 tasks × 3 repetitions × 2 conditions) are generated from those same 40
   task fixtures at run time, never as a separately materialized 320-item set.
5. `git diff --check`.
6. Only after 1–5 pass, and only with a SHUKOU-ratified `RUN_MANIFEST_TEMPLATE.json`
   instance (every `null` field filled, `authorization.*` flags explicitly flipped),
   does WU3 (Q1–Q3 real-environment execution) become possible — WU2's own delivery
   itself authorizes no live launch.
