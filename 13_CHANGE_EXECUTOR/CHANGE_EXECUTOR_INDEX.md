# Controlled Autonomous Change Executor Index (Phase 18, Issue #73)

```text
DOC_TYPE=CHANGE_EXECUTOR_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=CHANGE-EXECUTOR-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_EXECUTION_ADAPTER
CANONICAL_KERNEL_COUNT=1
CHANGE_EXECUTOR_OWNER_COUNT=1
PUBLIC_CHANGE_EXECUTOR_ENTRY_POINT_COUNT=2
SIGNED_DEPLOYMENT_DECLARATION_CHAIN=false
STRUCTURAL_REVIEW_ROUNDS_APPLIED=2
```

---

## 0. What this document is

This is the one entry point for the **Controlled Autonomous Change Executor** contract set --
the two documents under `13_CHANGE_EXECUTOR/` that define how an already-authorized canonical
Change may be *executed*, autonomously, only inside an explicit, closed, low-risk Execution
Boundary, producing exactly one immutable execution receipt, and then handing off to the
existing Evidence/Observation/Reflow owners rather than declaring anything itself.

```text
1. CHANGE_EXECUTOR_INDEX.md      (this document)
2. CHANGE_EXECUTOR_CONTRACT.md   P18-C1..C10, the closed Execution Boundary schema, the closed
                                  outcome vocabularies, the idempotency/mapping-slot state
                                  machine, the kill switch chain, the disclosed judgment calls,
                                  the required proof layers, the explicit non-claims, and Gate 18
```

This was a **first delivery**: `STRUCTURAL_REVIEW_ROUNDS_APPLIED` started at `0`. It became `1`
when SHUKOU adopted six structural-review corrections
(`ADOPT_P18_R1_STRUCTURAL_CORRECTIONS`, comment
`https://github.com/manosube/manosube-agent-civilization-os/pull/74#issuecomment-5626622213`)
against this package's exact prior head (commit `2010f05`), each implemented on the identical
branch, no new PR. It is now `2`: SHUKOU subsequently adopted four further corrections
(`ADOPT_P18_R2_STRUCTURAL_CORRECTIONS`, comment
`https://github.com/manosube/manosube-agent-civilization-os/pull/74#issuecomment-5628140572`)
against this package's exact prior head (commit `85bd43fbf4619d6ae9f765c76441dd5ea94bbdff`),
again each implemented on the identical existing branch, no new branch, no new PR.
`CHANGE_EXECUTOR_CONTRACT.md` §1/§3 items 9-14/§11 items 12-16/§12 record Round 1's six
corrections and their proof in full; §1/§3 items 15-18/§11 items 18-22/§12 record Round 2's four;
this document's own restatements below are updated to match both.

The human objective this Phase serves, in the adopting authority's own terms (SHUKOU's
`ADOPT_P18_CONTROLLED_AUTONOMOUS_CHANGE` comment on Issue #73):

```text
trusted Boot + exact Project Binding
+ current State revision/fingerprint
+ canonical Difference
+ reproduced AUTONOMOUS Authority decision
+ canonical AUTHORIZED Change
+ explicit low-risk execution Boundary
  → controlled Change Executor adapter, called at most once for the primary operation
    → this package's own independent, read-only re-read of the actual resulting filesystem
      state (Structural Review Round 1, P18-R1-F1) -- never trusting the adapter's own
      self-reported facts alone
      → immutable authorized change_execution_receipt, embedding that independent observation
        (KILL_SWITCH_STOPPED, BOUNDARY_VIOLATION, and UNKNOWN -- an adapter raise or a
        structurally invalid report, P18-R1-F4 -- are themselves terminal receipts, never bare
        exceptions, once an execution_attempt already exists)
        → embedded independent after-state re-observation request
          → existing Evidence / Independent Verification / Reflow owners, via the one existing
            derive_evidence call, in the Change-Free Verification Evidence position -- which now
            also requires the embedded independent observation to agree before deriving VERIFIED
```

"Execution does not create Authority, update canonical State, prove causality, establish
sufficient Evidence, close a Difference, or declare the Objective complete" (Issue #73's own
adopted Objective) -- restated structurally in §2 below.

---

## 1. This is not a ninth Kernel element

The Kernel is fixed at eight (`KERNEL_ELEMENT_COUNT=8`,
`ONE_KERNEL_ELEMENT_PER_PACKAGE=true`), and this package declares
`KERNEL_ELEMENT=NONE_EXECUTION_ADAPTER` -- the same `none`-style convention Boot, the CLI, Agent
Runtime, Independent Verification, Projection, Runtime, and URL Boot already use for their own
adapter layers.

What that means concretely: this layer mints no Authority, updates no canonical State's semantic
content beyond its own three new record kinds (`execution_intent`, `execution_attempt`,
`change_execution_receipt`) and its own kill switch chain (`change_executor_kill_switch`),
proves no causality, establishes no sufficient Evidence, closes no Difference, and declares no
completion. Each of those remains its existing owner's own, one-owner concern, and this layer
reaches every one of them only through that owner's own public surface, resolving and
recomputing an already-existing record rather than minting one of its own.

---

## 2. This is not a second State, Authority, Change, Evidence, Reflow, Binding, Boot, or completion owner

| Existing owner | How this layer reaches it | What this layer never does |
|---|---|---|
| State / Store | `store.commit.commit_state_transition`, two call sites (`route.py`'s own `_commit_records` template, shared by the `execution_intent`/`execution_attempt`/`change_execution_receipt` commits; `kill_switch.py`'s own `commit_change_executor_kill_switch`) | never writes a file directly, never builds a second persistence path, never mutates `semantic_state` content outside the single `deployment.claims` pointer key `kill_switch.py` owns (see `CHANGE_EXECUTOR_CONTRACT.md` §10) |
| Boot | `boot_project`, one call site, inside the returned closure's own `execute(...)` | never imports `boot_project` anywhere else in this package; every request Boots fresh, never caches a Boot across calls |
| Authority | resolve-and-recompute of an already-existing `authority_decision` (`route._resolve_authority_decision`), requiring the reproduced `decision` to equal `AUTONOMOUS` | never imports `authority.evaluate_authority` or any other evaluator -- this package never evaluates permission, only verifies a Change already carries a genuine, already-minted Decision |
| Change | resolve-and-recompute of an already-existing, `AUTHORIZED` canonical `change` (`route._resolve_change`) | never imports `change.engine.derive_change` -- this package never derives, proposes, or authors a Change, only executes one that already exists |
| Evidence | `derive_evidence`, one call site, in `evidence_handoff.py`, in the Change-Free Verification Evidence position | never judges sufficiency, never closes a Difference, never supplies its own accepting provenance beyond the one `verification_result_provenance` projection it constructs from the real, resolved receipt |
| Reflow / Difference / Observation | not at all | imports none of `reflow`; `difference.validation`/`difference.errors` are imported only for the repository's own shared canonical-schema-validation utility (`validate_record`), never for Difference domain semantics |
| Binding | not at all beyond `project_binding_ref`, a caller-supplied identity echoed onto the receipt | never imports `binding.identity`; `binding.signature.verify_ed25519_signature` is imported only for kill-switch signature *verification* (§10 of the contract), never for Binding's own grant semantics |
| Completion | not at all | declares no completion, closes no Issue/PR/Difference; the executing Agent and adapter cannot approve their own Change or accept their own receipt as sufficient Evidence (P18-C8) |

```text
CHANGE_EXECUTOR_IS_A_SECOND_STATE_OWNER=false
CHANGE_EXECUTOR_IS_A_SECOND_AUTHORITY_OWNER=false
CHANGE_EXECUTOR_IS_A_SECOND_CHANGE_OWNER=false
CHANGE_EXECUTOR_IS_A_SECOND_EVIDENCE_OWNER=false
CHANGE_EXECUTOR_IS_A_SECOND_REFLOW_OWNER=false
CHANGE_EXECUTOR_IS_A_SECOND_BINDING_OWNER=false
CHANGE_EXECUTOR_IS_A_SECOND_BOOT_OWNER=false
CHANGE_EXECUTOR_DECLARES_COMPLETION=false
```

---

## 3. This is not a general command executor, a production/deployment mechanism, or a GitHub pusher

No shell, subprocess, network, or credential surface is opened anywhere in this package.
`ControlledFilesystemAdapter` (`adapter.py`) is the only shipped production adapter, and it
imports none of `socket`, `subprocess`, `urllib`, or `requests`, and never mutates `os.environ`
-- confirmed by direct inspection of every module's own import list, not merely asserted by a
docstring. The closed Execution Boundary schema-fixes `permit_network`, `permit_subprocess`,
`permit_environment_mutation`, and `permit_credential_access` to exactly `False` (§7 of the
contract); a Boundary supplying `True` for any of them is refused outright, never silently
downgraded. This package never pushes or merges to GitHub, never deploys, and never selects a
target beyond a caller-supplied, disposable `worktree_root` path this package never chooses on
its own.

```text
ARBITRARY_SHELL_EXECUTION_IMPLEMENTED=false
REMOTE_COMMAND_EXECUTION_IMPLEMENTED=false
GENERAL_PURPOSE_TOOL_DISPATCH_IMPLEMENTED=false
GITHUB_PUSH_OR_MERGE_IMPLEMENTED=false
DEPLOYMENT_IMPLEMENTED=false
PRODUCTION_MUTATION_IMPLEMENTED=false
CREDENTIAL_USE_AUTHORITY=false
VPS_OR_CLOUD_PROVIDER_REQUIRED=false
```

---

## 4. Canonical owner

### 4.1 The two public entry points

```text
compose_change_executor              a trusted composition step binding Store/Project/Binding/
                                      Execution Boundary/adapter identity/adapter/kill-switch
                                      trust anchor once, and returning the request-facing
                                      operation itself: execute(change_id, *, claim_token,
                                      execution_instant, permit_semantic_reuse=False) ->
                                      {"receipt": ..., "replay": bool, "semantic_reuse": bool}.
                                      worktree_root is a required field *inside* the closed
                                      Execution Boundary itself (Structural Review Round 1,
                                      P18-R1-F3, CHANGE_EXECUTOR_CONTRACT.md §3 item 11,
                                      superseding the prior round's own separate
                                      composition-time parameter, §3 item 6) -- compose_change_
                                      executor no longer accepts a worktree_root= keyword at all.
route_change_execution_to_evidence   hand a committed change_execution_receipt to the existing
                                      Evidence owner, in the Change-Free Verification Evidence
                                      position -- now also requiring the receipt's own embedded
                                      independent_after_state_observation to agree before
                                      deriving VERIFIED (Structural Review Round 1, P18-R1-F1),
                                      AND now itself performing a SECOND, genuinely independent,
                                      handoff-time-only re-read that must also agree before
                                      VERIFIED may ever be derived -- never trusting the receipt's
                                      own embedded field alone (Structural Review Round 2,
                                      P18-R2-F1, CHANGE_EXECUTOR_CONTRACT.md §3 item 18)
```

### 4.2 The three new record kinds, and the one kill switch chain

```text
execution_intent           the first durable fact of an execution attempt -- which Change,
                            under which Boundary and adapter identity, claimed by whom, when.
                            Keyed by the deterministic mapping-slot key (see contract §9), not a
                            full content address, so two distinct claim_token values for the
                            identical (change, Boundary, adapter) triple always collide.
execution_attempt          restates execution_intent's own fields plus a reference back to it,
                            plus a fresh, per-call attempt_nonce -- under the identical
                            mapping-slot id -- committed once the concurrency barrier has already
                            passed. attempt_nonce (never part of the id itself) makes two
                            independently-built attempts for the identical slot genuinely
                            different byte-for-byte, closing a genuine race an automated PR
                            review identified (CHANGE_EXECUTOR_CONTRACT.md §3 item 8). Now also
                            embeds reobservation_request durably, at commit time (Structural
                            Review Round 2, P18-R2-F3 part 1, §3 item 16) -- so a caller resuming
                            its own orphaned attempt (identical claim_token) can resolve to a
                            grounded terminal UNKNOWN receipt directly from it, never a perpetual
                            ExecutionReconciliationRequiredError (P18-R2-F3 part 2, §3 item 17).
change_execution_receipt   the sole durable, immutable fact this package ever commits about one
                            execution attempt's own terminal outcome (P18-C6). Its own id is
                            always exactly its own execution_request_id, the shared mapping-slot
                            key all three related records carry. Now also embeds
                            independent_after_state_observation (Structural Review Round 1,
                            P18-R1-F1) -- this package's own genuine, read-only re-read of the
                            actual resulting filesystem state, never the adapter's own
                            self-reported facts alone; produced by the new reobservation.py.
change_executor_kill_switch   a monotonic, Ed25519-signed ACTIVE/REVOKED chain (see contract
                               §10) -- not one of the three request-scoped record kinds above,
                               and never produced by an execution request itself; only an
                               externally authorized trust anchor can move it.
```

### 4.3 The closed vocabularies

```text
EXECUTION_OUTCOMES   SUCCEEDED, REFUSED, BOUNDARY_VIOLATION, STALE_AUTHORITY, TARGET_DRIFT,
                      KILL_SWITCH_STOPPED, TIMEOUT, ADAPTER_FAILURE, PARTIAL_MUTATION,
                      ROLLBACK_SUCCEEDED, ROLLBACK_FAILED, UNKNOWN, REOBSERVATION_MISMATCH
                      (REOBSERVATION_MISMATCH added Structural Review Round 1, P18-R1-F1)
ROLLBACK_OUTCOMES    NOT_ATTEMPTED, ROLLBACK_SUCCEEDED, ROLLBACK_FAILED
```

The adapter itself asserts no `EXECUTION_OUTCOMES` member -- it reports only raw, structurally
bounded facts (`AdapterReport`: `files_written`, `bytes_written`, `files_deleted`, `error`), and
`route.py` alone classifies those facts into one outcome. See `CHANGE_EXECUTOR_CONTRACT.md` §8
for the full vocabulary discipline and §9 for the idempotency state machine these outcomes feed
into.

---

## 5. Explicit non-claims

Restated here so the index and the contract cannot drift; `CHANGE_EXECUTOR_CONTRACT.md` §13 is
the full list.

- This package creates no Authority, updates no canonical State's semantic content beyond its
  own three new record kinds and its own kill switch chain, proves no causality, establishes no
  sufficient Evidence, closes no Difference, and declares no completion (Issue #73's own adopted
  Objective, restated verbatim).
- No test suite existed in this repository at the moment this document pair's first draft was
  written -- confirmed absent by direct search immediately before writing. A full suite (9 test
  files, 2 fixture modules, 161 tests, 0 skipped, 0 failed) was written and verified immediately
  afterward and now exists under `tests/unit/change_executor/`, `tests/contract/change_executor/`,
  and `tests/integration/change_executor/`; `CHANGE_EXECUTOR_CONTRACT.md` §12 cites it by real
  file and test name. An automated review of PR #74 subsequently identified three real defects
  against `route.py` (a request-facing `worktree_root` not bound to the Boundary; a crash between
  the `execution_intent` and `execution_attempt` commits permanently stranding the slot; two
  concurrent callers able to both call `adapter.execute`), each fixed and each proven by a new
  regression test -- the same 9 files and 2 fixture modules, then 167 tests, 0 skipped, 0 failed.
  SHUKOU's own Structural Review Round 1 subsequently adopted six further corrections
  (`ADOPT_P18_R1_STRUCTURAL_CORRECTIONS`) against that exact 167-test head (commit `2010f05`):
  independent after-state re-observation now gates `VERIFIED` (P18-R1-F1); an exact
  post-intent-successor staleness check and a final pre-effect State barrier replace a blanket
  staleness skip (P18-R1-F2); `worktree_root` moved from a separate composition-time parameter
  into the closed Boundary itself (P18-R1-F3); every post-attempt path, including an adapter raise
  and a structurally invalid adapter report, now commits exactly one terminal receipt (P18-R1-F4);
  idempotency-slot resolution now runs before time-window/kill-switch checkpoint #1 too, not
  merely before Boot/staleness (P18-R1-F5). Each was fixed and each proven by new tests -- the
  same 9 files and 2 fixture modules plus one new file
  (`test_change_executor_independent_reobservation.py`), now 10 files, 182 tests, 0 skipped, 0
  failed (`CHANGE_EXECUTOR_CONTRACT.md` §1/§3 items 6-8, 9-14/§11 items 9-16/§12). SHUKOU's own
  Structural Review Round 2 subsequently adopted four further corrections
  (`ADOPT_P18_R2_STRUCTURAL_CORRECTIONS`) against that exact 182-test head (commit `85bd43f`): a
  second, genuinely independent, handoff-time-only re-read now gates `VERIFIED`, never the
  receipt's own embedded field alone (P18-R2-F1); composition-time `worktree_root` identity
  verification against the Boundary's own `repository`/`branch`, via pure local `.git` metadata
  reads (P18-R2-F2); `execution_attempt` now durably embeds its own `reobservation_request` at
  commit time, and a caller resuming its own orphaned attempt (identical `claim_token`) resolves
  to a grounded terminal `UNKNOWN` receipt rather than a perpetual
  `ExecutionReconciliationRequiredError` (P18-R2-F3); and this document pair's own
  record-keeping corrected its prior round's self-referential `FINAL_HEAD_SHA` field (P18-R2-F4).
  Each was fixed and each proven by new tests -- the same 10 files and 2 fixture modules plus
  one new file (`test_change_executor_worktree_git_identity.py`), now 11 files, 197 tests, 0
  skipped, 0 failed (`CHANGE_EXECUTOR_CONTRACT.md` §1/§3 items 15-18/§11 items 18-22/§12).
- A model output, URL Boot content, or temporary Agent output is never treated as executable
  authority-bearing instruction here -- this package imports none of `model_runtime`, `url_boot`,
  or `agent_runtime`, and its one replaceable adapter receives only a closed, prevalidated
  `ExecutionOperation`, never raw prose, a URL, or model output (P18-C10).
- This package never implements Phase 19 multi-Agent orchestration.
- A committed `change_execution_receipt` is never treated, by this package, as sufficient
  Evidence -- it is handed to the existing Evidence owner as one Change-Free Verification input
  among whatever else that owner requires. Since Structural Review Round 1 (P18-R1-F1), the
  hand-off additionally requires the receipt's own embedded
  `independent_after_state_observation` to agree before deriving `VERIFIED` -- but this still
  never makes this package the decider of sufficiency; that remains `derive_evidence`'s own.
- A Boundary's own `worktree_root` (now bound inside the Boundary itself, P18-R1-F3) is, since
  Structural Review Round 2 (P18-R2-F2), verified -- via pure local `.git` metadata file reads,
  still no subprocess/network call of any kind -- to be a genuine checkout of that same
  Boundary's own `repository`/`branch`. What remains a non-claim: this package trusts that local
  `.git` metadata itself to be an honest report of the worktree's own real state; it performs no
  cryptographic verification of `.git/HEAD`/`.git/config`, and a `.git` directory whose own
  metadata has been hand-edited to lie is not detected (`CHANGE_EXECUTOR_CONTRACT.md` §13's
  corresponding non-claims).

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_18_COMPLETE=false
PHASE_19_ALLOWED=false
```
