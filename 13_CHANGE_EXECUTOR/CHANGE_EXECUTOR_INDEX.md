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
STRUCTURAL_REVIEW_ROUNDS_APPLIED=0
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

This is a **first delivery**: `STRUCTURAL_REVIEW_ROUNDS_APPLIED=0`. No structural review round
has yet reopened, corrected, or superseded anything stated here.

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
    → immutable authorized change_execution_receipt (KILL_SWITCH_STOPPED and
      BOUNDARY_VIOLATION are themselves terminal receipts, never bare exceptions, once an
      execution_attempt already exists)
      → embedded independent after-state re-observation request
        → existing Evidence / Independent Verification / Reflow owners, via the one existing
          derive_evidence call, in the Change-Free Verification Evidence position
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
                                      execution_instant, worktree_root,
                                      permit_semantic_reuse=False) -> {"receipt": ...,
                                      "replay": bool, "semantic_reuse": bool}
route_change_execution_to_evidence   hand a committed change_execution_receipt to the existing
                                      Evidence owner, in the Change-Free Verification Evidence
                                      position
```

### 4.2 The three new record kinds, and the one kill switch chain

```text
execution_intent           the first durable fact of an execution attempt -- which Change,
                            under which Boundary and adapter identity, claimed by whom, when.
                            Keyed by the deterministic mapping-slot key (see contract §9), not a
                            full content address, so two distinct claim_token values for the
                            identical (change, Boundary, adapter) triple always collide.
execution_attempt          restates execution_intent's own fields plus a reference back to it,
                            under the identical mapping-slot id -- committed once the concurrency
                            barrier has already passed.
change_execution_receipt   the sole durable, immutable fact this package ever commits about one
                            execution attempt's own terminal outcome (P18-C6). Its own id is
                            always exactly its own execution_request_id, the shared mapping-slot
                            key all three related records carry.
change_executor_kill_switch   a monotonic, Ed25519-signed ACTIVE/REVOKED chain (see contract
                               §10) -- not one of the three request-scoped record kinds above,
                               and never produced by an execution request itself; only an
                               externally authorized trust anchor can move it.
```

### 4.3 The closed vocabularies

```text
EXECUTION_OUTCOMES   SUCCEEDED, REFUSED, BOUNDARY_VIOLATION, STALE_AUTHORITY, TARGET_DRIFT,
                      KILL_SWITCH_STOPPED, TIMEOUT, ADAPTER_FAILURE, PARTIAL_MUTATION,
                      ROLLBACK_SUCCEEDED, ROLLBACK_FAILED, UNKNOWN
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
  file and test name.
- A model output, URL Boot content, or temporary Agent output is never treated as executable
  authority-bearing instruction here -- this package imports none of `model_runtime`, `url_boot`,
  or `agent_runtime`, and its one replaceable adapter receives only a closed, prevalidated
  `ExecutionOperation`, never raw prose, a URL, or model output (P18-C10).
- This package never implements Phase 19 multi-Agent orchestration.
- A committed `change_execution_receipt` is never treated, by this package, as sufficient
  Evidence -- it is handed to the existing Evidence owner as one Change-Free Verification input
  among whatever else that owner requires.

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_18_COMPLETE=false
PHASE_19_ALLOWED=false
```
