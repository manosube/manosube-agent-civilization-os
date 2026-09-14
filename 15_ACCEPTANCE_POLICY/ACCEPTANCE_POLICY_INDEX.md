# Acceptance Policy Lineage Index (Phase 19 incident, Issue #80)

```text
DOC_TYPE=ACCEPTANCE_POLICY_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=ACCEPTANCE-POLICY-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_ACCEPTANCE_POLICY_LINEAGE_ADAPTER
CANONICAL_KERNEL_COUNT=1
ACCEPTANCE_POLICY_OWNER_COUNT=1
PUBLIC_ACCEPTANCE_POLICY_ENTRY_POINT_COUNT=9
STRUCTURAL_REVIEW_ROUNDS_APPLIED=3
```

---

## 0. What this document is

This is the one entry point for the **Acceptance Policy Lineage and Undeclared Gate Rejection**
contract set -- the two documents under `15_ACCEPTANCE_POLICY/` that define how this repository's
own acceptance policy (what is required for implementation, structural review, merge, Issue
closure, and phase completion) is represented as a closed, hash-linked, SHUKOU-adopted lineage,
never as prose, never as a side effect of an unrelated record.

```text
1. ACCEPTANCE_POLICY_INDEX.md      (this document)
2. ACCEPTANCE_POLICY_CONTRACT.md   FD4-C1..C10, the disclosed judgment calls, the closed
                                    vocabularies, the required proof layers, and the explicit
                                    non-claims
```

This delivery has passed three rounds of Structural Review: `STRUCTURAL_REVIEW_ROUNDS_APPLIED=3`
(P82-R1-F1..F5, `ACCEPTANCE_POLICY_CONTRACT.md` §10; P82-R2-F1..F4, `ACCEPTANCE_POLICY_CONTRACT.md`
§11; P82-R3-F1..F3, `ACCEPTANCE_POLICY_CONTRACT.md` §12). Issue #80's own adopted FD-0004 contract,
restated structurally:

```text
one immutable genesis Baseline (every original clause, ORIGINAL_ISSUE-sourced)
  -> proposed Transitions (ADD/REMOVE/REPLACE/NARROW/BROADEN/RECLASSIFY, hash-linked to the
     exact predecessor each one extends -- Agent-proposable, never Agent-effective)
    -> identity-bound SHUKOU Adoptions (the only act that ever makes a Baseline or Transition
       effective)
      -> derived Effective View (a pure fold of baseline + ordered valid adoptions -- never
         itself committed, never a caller-authored summary)
        -> pre-adoption Impact Preview (before/after/new-blocker projection, before SHUKOU decides)
          -> fail-closed admission boundary (any payload mentioning a known clause_id without
             policy_change=True is refused before it reaches any other record)
```

This work exists because it happened once: Issue #77's original "GitHub Actions is not acceptance
Authority" clause, Round 5's later `GITHUB_PREMERGE_GATE_GREEN` supplement (a distinct, additional
Required Evidence gate), and that supplement's later removal, were never represented as first-class
lineage -- this delivery's own permanent regression fixture (`ACCEPTANCE_POLICY_CONTRACT.md` §6,
FD4-C8) reconstructs exactly that sequence as three distinct, non-contradictory facts.

---

## 1. This is not a ninth Kernel element

The Kernel is fixed at eight (`KERNEL_ELEMENT_COUNT=8`, `ONE_KERNEL_ELEMENT_PER_PACKAGE=true`),
and this package declares `KERNEL_ELEMENT=NONE_ACCEPTANCE_POLICY_LINEAGE_ADAPTER` -- the same
`none`-style convention Boot, the CLI, Agent Runtime, Independent Verification, Projection,
Runtime, Model Runtime, URL Boot, Change Executor and Multi-Agent already use for their own adapter
layers.

What that means concretely: this layer mints no Authority, updates no canonical State's semantic
content beyond its own new record kinds, proves no causality, establishes no sufficient Evidence,
authorizes no Change, and declares no completion. It represents one thing only: what the acceptance
policy itself *is*, and how it *changed*, as an attributable, ordered, hash-linked fact set.

---

## 2. This is not a second State, Authority, Change, Evidence, or Reflow owner

| Existing owner | How this layer reaches it | What this layer never does |
|---|---|---|
| State / Store | `store.commit.commit_state_transition`, one import site (`route.py`) | never writes a file directly, never builds a second persistence path |
| Authority | recognises exactly one closed literal Human Authority constant (`SHUKOU`), matched by value against `development_binding.adoption_record.HUMAN_AUTHORITY`, never imported | never imports either Authority evaluator by name, never mints a Decision |
| Change / Change Executor | not at all | imports neither; no execution, no Boundary, no side effect |
| Evidence / Reflow / Difference / Observation | not at all | imports none of `evidence`, `reflow`, `difference`; this package's own records are read only by itself, `development_binding.adoption_record`'s existing grammar, and (in a future caller) an implementation handoff/return-Evidence/closure-sweep scan that resolves this package's public surface, never the reverse |
| Completion | not at all | declares no completion, marks nothing accepted in the Phase Acceptance Ledger, closes no Issue/PR |

```text
ACCEPTANCE_POLICY_IS_A_SECOND_STATE_OWNER=false
ACCEPTANCE_POLICY_IS_A_SECOND_AUTHORITY_OWNER=false
ACCEPTANCE_POLICY_IS_A_SECOND_EVIDENCE_OWNER=false
ACCEPTANCE_POLICY_IS_A_SECOND_REFLOW_OWNER=false
ACCEPTANCE_POLICY_IS_A_SECOND_CHANGE_OWNER=false
ACCEPTANCE_POLICY_DECLARES_COMPLETION=false
```

---

## 3. This is not a majority-vote, prose-inferred, or silently-collapsed policy mechanism

No module in this package infers a policy change from `statement`/`rationale` prose -- the
semantic diff (`ACCEPTANCE_POLICY_CONTRACT.md` §6, FD4-C5) is computed only from the three
structured fields `policy_class`/`blocking_effect`/`scope`. No module resolves a lineage conflict
(a missing predecessor, a fork, a reorder, a stale binding, a cross-project substitution) by
picking a branch, taking the latest, or any other silent heuristic -- every one of these raises a
typed `PolicyLineageConflictError` or `PolicyProvenanceError` and blocks a clean effective-policy
view entirely (FD4-C6). No module admits a policy-shaped term smuggled into an unrelated record
(a code finding, a `REQUIRED_PROOFS` block, an implementation handoff, return Evidence, a closure
sweep) without an explicit `policy_change: true` declaration (FD4-C4) -- this is the direct,
mechanical answer to how the real Phase 19 incident happened.

```text
UNDECLARED_POLICY_CHANGE_ADMITTED_IMPLEMENTED=false
POLICY_CONFLICT_AUTO_RESOLUTION_IMPLEMENTED=false
PROSE_INFERRED_POLICY_CHANGE_IMPLEMENTED=false
AGENT_SELF_ADOPTION_IMPLEMENTED=false
NON_OWNER_COMMENT_ADOPTION_IMPLEMENTED=false
AUTOMATIC_LEDGER_ACCEPTANCE_IMPLEMENTED=false
AUTOMATIC_ISSUE_CLOSE_IMPLEMENTED=false
AUTOMATIC_MERGE_IMPLEMENTED=false
PHASE_20_ALLOWED=false
```

---

## 4. Canonical owner

### 4.1 The nine public entry points

```text
open_acceptance_policy_baseline           commit the one immutable genesis Baseline for a work
                                           unit (FD4-C2). Every clause must declare
                                           existed_in_original_contract=true.
resolve_and_verify_baseline               resolve a committed Baseline, independently
                                           reproducing its own id/fingerprint before trusting it.
resolve_and_verify_transition             the same, for a committed Transition.
resolve_and_verify_adoption               the same, for a committed Adoption -- additionally
                                           re-verifies decision_owner and source_reference every
                                           read, never only at commit time (FD4-C3).
resolve_and_verify_effective_policy       fold a Store-resolved baseline + the complete,
                                           canonically-ordered adoption set this lineage's own
                                           Store state defines (never a caller-supplied list,
                                           Structural Review Round 1 P82-R1-F1) into the current
                                           effective policy (FD4-C6). Refuses on any lineage
                                           conflict, and exposes no baseline clause until the
                                           baseline's own adoption is folded (P82-R1-F2).
propose_acceptance_policy_transition      commit one Transition against the real, freshly
                                           resolved effective policy -- refuses fail-closed if the
                                           declared operation disagrees with the independently
                                           computed diff (FD4-C1/C5). Never itself effective.
adopt_acceptance_policy_transition        commit the identity-bound SHUKOU decision that
                                           activates one baseline or transition (FD4-C3). Refuses
                                           any non-SHUKOU decision_owner or non-OWNER source.
preview_acceptance_policy_transition      pure before/after/new-blocker projection against the
                                           real current effective policy, before adoption (FD4-C7).
assert_no_undeclared_policy_change_in_
payload                                   fail-closed scan of an arbitrary payload for any
                                           mention of a known clause_id without a declared
                                           policy_change=true (FD4-C4).
```

### 4.2 The seven new record kinds

```text
acceptance_policy_baseline         the immutable, full-content-addressed genesis record (FD4-C2)
acceptance_policy_clause           embedded only -- inside a baseline's clauses array or a
                                    transition's proposed_clause; never independently committed
acceptance_policy_transition       one hash-linked ADD/REMOVE/REPLACE/NARROW/BROADEN/RECLASSIFY
                                    proposal on one clause (FD4-C1/C5)
acceptance_policy_adoption         the identity-bound SHUKOU decision activating one baseline or
                                    transition (FD4-C3)
acceptance_policy_effective_view   derived only -- a pure fold of baseline + ordered adoptions;
                                    never committed (FD4-C6)
acceptance_policy_impact_preview   derived only -- pure before/after projection; never committed
                                    (FD4-C7)
acceptance_policy_refusal_outcome  schema-declared for wire-shape completeness; every refusal in
                                    this delivery is a raised typed exception, never a persisted
                                    record (ACCEPTANCE_POLICY_CONTRACT.md §3 item 7)
```

### 4.3 The closed vocabularies

```text
POLICY_CLASSES             AUTHORITY, REQUIRED_EVIDENCE
POLICY_OPERATIONS          ADD, REMOVE, REPLACE, NARROW, BROADEN, RECLASSIFY
PROPOSER_ROLES             HUMAN_AUTHORITY, STRUCTURAL_ADVISOR, EXECUTOR, OTHER_AGENT
BLOCKING_EFFECT_FIELDS     implementation, structural_review, merge, issue_closure,
                            phase_completion
HUMAN_AUTHORITY            "SHUKOU" -- the sole recognised Human Authority
REQUIRED_COMMENT_AUTHOR_
ASSOCIATION                "OWNER"
```

Nothing here asserts its own sufficiency, majority, or completion -- see
`ACCEPTANCE_POLICY_CONTRACT.md` §6 (FD4-C1..C10) for the full discipline and §8 for the required
proof layers.

---

## 5. Explicit non-claims

Restated here so the index and the contract cannot drift; `ACCEPTANCE_POLICY_CONTRACT.md` §9 is
the full list.

- This delivery marks nothing complete: no Phase Acceptance Ledger entry, no Issue #80 closure, no
  Phase 20 entry. Only Structural Review, SHUKOU's own final acceptance, a manual merge, and
  after-state re-observation can do that.
- This delivery never touches PR #78, PR #78's branch, or PR #78's own Actions policy selection.
- This delivery does not retroactively validate or reinterpret Round 5 or Round 12 history -- it
  demonstrates the representational mechanism the Phase 19 incident showed was missing, nothing
  about whether that history's own decisions were themselves correct.
- No parallel Authority/State/Evidence/Reflow/Store owner is introduced.
- No production Baseline for this repository's actual current acceptance policy is committed by
  this delivery -- every clause_id in this delivery's own tests and fixtures exists only there.

```text
MERGE_ALLOWED=false
ISSUE_80_CLOSE_ALLOWED=false
PHASE_20_ALLOWED=false
PHASE_ACCEPTANCE_LEDGER_ENTRY_ADDED=false
```
