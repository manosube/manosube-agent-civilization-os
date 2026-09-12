# Multi-Agent Dynamic Execution Index (Phase 19, Issue #77)

```text
DOC_TYPE=MULTI_AGENT_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=MULTI-AGENT-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_MULTI_AGENT_ORCHESTRATION_ADAPTER
CANONICAL_KERNEL_COUNT=1
MULTI_AGENT_OWNER_COUNT=1
PUBLIC_MULTI_AGENT_ENTRY_POINT_COUNT=3
STRUCTURAL_REVIEW_ROUNDS_APPLIED=0
```

---

## 0. What this document is

This is the one entry point for the **Multi-Agent Dynamic Execution** contract set -- the two
documents under `14_MULTI_AGENT/` that define how one canonical Difference and its required
capabilities select 1, 2 or N temporary Agents, execute them independently, preserve every
disagreement, and release every one of them, without ever creating a permanent Agent
organization.

```text
1. MULTI_AGENT_INDEX.md      (this document)
2. MULTI_AGENT_CONTRACT.md   P19-C1..C10, the closed vocabularies, the disclosed judgment
                              calls, the required proof layers, Gate 19, and the explicit
                              non-claims
```

This is a **first delivery**: `STRUCTURAL_REVIEW_ROUNDS_APPLIED=0`. Issue #77's own adopted
proposal, restated structurally:

```text
canonical Difference + its required capabilities
  -> identity-bound dynamic execution plan (one shared, reused Model Runtime Work Unit)
    -> 1/2/N temporary Agents (Phase 12's own lifecycle, reused, never reimplemented)
      -> independent, provenance-bound outputs (Model Runtime's own execution contract, reused)
        -> explicit conflict representation (agreement/contradiction/absence, never collapsed)
          -> Evidence-aggregation input (never a verdict)
            -> existing Evidence / Independent Verification / Reflow owners
              -> release receipts for every temporary Agent
```

"Multi-Agent execution does not create Authority, canonical State, Observation, Evidence
sufficiency, truth by consensus, a permanent Agent hierarchy, or completion" (Issue #77's own
adopted objective) -- restated structurally in §2 below.

---

## 1. This is not a ninth Kernel element

The Kernel is fixed at eight (`KERNEL_ELEMENT_COUNT=8`, `ONE_KERNEL_ELEMENT_PER_PACKAGE=true`),
and this package declares `KERNEL_ELEMENT=NONE_MULTI_AGENT_ORCHESTRATION_ADAPTER` -- the same
`none`-style convention Boot, the CLI, Agent Runtime, Independent Verification, Projection,
Runtime, Model Runtime, URL Boot and Change Executor already use for their own adapter layers.

What that means concretely: this layer mints no Authority, updates no canonical State's semantic
content beyond its own six new record kinds, proves no causality, establishes no sufficient
Evidence, closes no Difference, and declares no completion. Each of those remains its existing
owner's own, one-owner concern, and this layer reaches every one of them only through that
owner's own public surface, resolving and recomputing an already-existing record rather than
minting one of its own.

---

## 2. This is not a second State, Authority, Change, Evidence, Reflow, Agent-lifecycle, or completion owner

| Existing owner | How this layer reaches it | What this layer never does |
|---|---|---|
| State / Store | `store.commit.commit_state_transition`, one import site (`route.py`); `evidence_handoff.py` reuses `route.py`'s own committer directly (a disclosed intra-package exception -- `MULTI_AGENT_CONTRACT.md` §3 item 9) | never writes a file directly, never builds a second persistence path |
| Temporary Agent lifecycle | `agent_runtime.start_temporary_agent`, exactly two disclosed literal call sites, one live role each (`MULTI_AGENT_CONTRACT.md` §3 item 5) | never boots a Project itself, never defines a second class implementing `boot_context`+`release`, never persists an Agent identity or memory |
| Model Runtime execution contract | `model_runtime.open_model_work_unit` (once per plan) and `model_runtime.execute_model_work_unit` (once per slot's own attempt), reused unchanged | never evaluates Authority itself, never derives a Model Execution Envelope of its own, never reads an adapter's raw report directly |
| Authority | reproduced only through Model Runtime's own already-evaluated decision, embedded on the plan | never imports either Authority evaluator by name |
| Evidence | `model_runtime.evidence_handoff.route_model_execution_to_evidence`, one call site, chained across every admitted output of one plan | never judges sufficiency, never derives an Evidence record of its own, never supplies its own accepting provenance |
| Reflow / Difference / Observation / Independent Verification / Change / Change Executor | not at all | imports none of `reflow`, `independent_verification`, `projection`, `runtime`, `change`, or `change_executor` anywhere (proved by AST-walked static conformance, not merely by docstring) |
| Completion | not at all | declares no completion, closes no Issue/PR/Difference; a coordinator or an Agent cannot approve its own plan, mark its own output sufficient, or accept its own receipt as completion |

```text
MULTI_AGENT_IS_A_SECOND_STATE_OWNER=false
MULTI_AGENT_IS_A_SECOND_AGENT_LIFECYCLE_OWNER=false
MULTI_AGENT_IS_A_SECOND_AUTHORITY_OWNER=false
MULTI_AGENT_IS_A_SECOND_EVIDENCE_OWNER=false
MULTI_AGENT_IS_A_SECOND_REFLOW_OWNER=false
MULTI_AGENT_IS_A_SECOND_CHANGE_OWNER=false
MULTI_AGENT_DECLARES_COMPLETION=false
```

---

## 3. This is not a permanent Agent organization, a majority-as-truth mechanism, or unrestricted tool dispatch

No module in this package persists an Agent identity, memory, registry, or hierarchy across
plans, and no module builds a thread pool, `asyncio` task group, or subprocess fan-out (confirmed
by direct inspection of every module's own import list -- `threading`/`asyncio`/`multiprocessing`
appear nowhere in this package). Every Agent this package constructs is released before this
package's own terminal receipt can exist, proved even under a genuinely unexpected
mid-orchestration exception. Conflict classification uses exact fingerprint equality or explicit
disagreement -- there is no majority-vote, confidence-average, last-writer-wins, or model-rank
vocabulary anywhere in this package's own source; a `CONTRADICTING` group admits neither
candidate, ever. This package dispatches nothing beyond the one, existing, already-bounded Model
Runtime execution contract -- no shell, subprocess, network, or credential surface is opened
anywhere in this package (this package does not even define its own Adapter Protocol; it reuses
Model Runtime's `ModelAdapter` type directly).

```text
PERMANENT_AGENT_HIERARCHY_IMPLEMENTED=false
PERSISTENT_AGENT_MEMORY_IMPLEMENTED=false
PERMANENT_AGENT_REGISTRY_IMPLEMENTED=false
UNBOUNDED_AGENT_COUNT_IMPLEMENTED=false
UNRESTRICTED_TOOL_DISPATCH_IMPLEMENTED=false
CONSENSUS_EQUALS_EVIDENCE_IMPLEMENTED=false
AGENT_MAJORITY_CREATES_AUTHORITY_IMPLEMENTED=false
COORDINATOR_CREATES_AUTHORITY_IMPLEMENTED=false
CONFLICT_AUTO_RESOLUTION_IMPLEMENTED=false
AUTOMATIC_DIFFERENCE_CLOSE_IMPLEMENTED=false
AUTOMATIC_ISSUE_CLOSE_IMPLEMENTED=false
AUTOMATIC_MERGE_IMPLEMENTED=false
```

---

## 4. Canonical owner

### 4.1 The three public entry points

```text
open_dynamic_execution_plan       select 1/2/N slots from one canonical Difference (P19-C1),
                                   open the one shared Model Work Unit they act under (Phase 16's
                                   own owner, unchanged), and commit one immutable,
                                   content-addressed plan (P19-C2). Requires a live Phase 12
                                   coordinator Agent as its own second positional argument.
execute_dynamic_execution_plan    fan out to 1/2/N fresh temporary Agents (Phase 12's own
                                   lifecycle, reused), record each slot's own independent,
                                   provenance-bound attempt (P19-C5), release every Agent
                                   (P19-C8), and produce the deterministic conflict set (P19-C6)
                                   and Evidence-aggregation input (P19-C7).
route_orchestration_to_evidence   hand every admitted output off to the existing Evidence owner
                                   (Model Runtime's own hand-off, reused, chained), and commit
                                   the terminal orchestration receipt (P19-C7/C8/C9).
```

### 4.2 The six new record kinds

```text
multi_agent_dynamic_execution_plan       the immutable, full-content-addressed plan (P19-C2)
multi_agent_slot_output                  one per slot's own attempt (P19-C5); narrow natural-key
                                          id (see MULTI_AGENT_CONTRACT.md §3 item 8 / §4.1)
multi_agent_agent_release_receipt        one per slot (P19-C8); narrow natural-key id
multi_agent_conflict_set                 one per plan (P19-C6); narrow natural-key id
multi_agent_evidence_aggregation_input   one per plan (P19-C7); narrow natural-key id; refused
                                          unless every release receipt is RELEASED
multi_agent_orchestration_receipt        one per plan, terminal (P19-C8/C9); narrow natural-key
                                          id; carries evidence_refs, appended after the hand-off
```

### 4.3 The closed vocabularies

```text
MULTI_AGENT_CAPABILITIES     reused verbatim from Model Runtime -- {"PROPOSE_EVIDENCE_CANDIDATE"}
MULTI_AGENT_SLOT_OUTCOMES    reused verbatim from Model Runtime's own MODEL_EXECUTION_OUTCOMES
RISK_CLASS_TO_SLOT_COUNT     LOW->1, MODERATE->1, HIGH->2, CRITICAL->3 -- fixed, total, immutable
CONFLICT_MEMBER_KINDS        AGREEING, CONTRADICTING, ABSENT
ORCHESTRATION_OUTCOMES       COMPLETED_ALL_RELEASED, COMPLETED_WITH_UNRESOLVED_CAPABILITY,
                              ABORTED_RELEASE_INCOMPLETE (disclosed-unreachable via the route)
```

Nothing here asserts its own sufficiency, majority, or completion -- see
`MULTI_AGENT_CONTRACT.md` §6 (P19-C6/P19-C7) for the full discipline and §8 for the idempotency/
replay scheme these records feed into.

---

## 5. Explicit non-claims

Restated here so the index and the contract cannot drift; `MULTI_AGENT_CONTRACT.md` §10 is the
full list.

- This package creates no Authority, updates no canonical State's semantic content beyond its
  own six new record kinds, proves no causality, establishes no sufficient Evidence, closes no
  Difference, and declares no completion (Issue #77's own adopted objective, restated verbatim).
- `MULTI_AGENT_CAPABILITIES` has exactly one member today. This delivery proves the *mechanism*
  for genuine N-capability fan-out with the one capability that exists, never a hypothetical
  multi-capability catalog it would have had to invent to exercise.
- "CONCURRENT" execution ordering is an honest, structurally-checked absence-of-dependency claim
  -- this package builds no real thread/async/process fan-out.
- The one declared cancellation policy is not runtime-enforced; no module in this package reads
  a clock or watches a deadline.
- `ORCHESTRATION_OUTCOMES.ABORTED_RELEASE_INCOMPLETE` is schema-representable but, in this
  delivery, unreachable through the public route -- `agent_runtime`'s own `release()` cannot
  currently fail. See `MULTI_AGENT_CONTRACT.md` §10 for the engine-level control that still
  proves the refusal exists.
- This package never implements Phase 20 (long-running Agent proof) or Phase 21 (comparative
  benchmark) -- neither exists as a vocabulary, module, or schema field anywhere here.
- This package never automatically closes a Difference or an Issue, and never merges anything --
  it imports none of `reflow`, `change_executor`, or any git/GitHub surface.
- A model output is never treated as executable authority-bearing instruction -- every candidate
  this package ever classifies or hands to Evidence is the identical, already-Boundary-projected
  fact the existing Model Runtime route itself produces.

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_19_COMPLETE=false
PHASE_20_ALLOWED=false
```
