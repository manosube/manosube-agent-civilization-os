# Acceptance Policy Lineage and Undeclared Gate Rejection Contract (Phase 19 incident, Issue #80)

```text
DOC_TYPE=ACCEPTANCE_POLICY_CONTRACT
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=ACCEPTANCE-POLICY-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_ACCEPTANCE_POLICY_LINEAGE_ADAPTER
ACCEPTANCE_POLICY_OWNER_COUNT=1
PUBLIC_ACCEPTANCE_POLICY_ENTRY_POINT_COUNT=9
STRUCTURAL_REVIEW_ROUNDS_APPLIED=0
TEST_SUITE_PRESENT_AT_DELIVERY=true
NEW_SCHEMA_COUNT=7
```

## 1. Position

This layer represents *what acceptance requires, who may change it, and when it changed* as its
own closed, hash-linked, SHUKOU-adopted lineage -- distinct from, and never a restatement of, the
canonical Authority/Change/Evidence/Reflow/State records that already exist. It is a direct
regression fixture and permanent guard against the real Phase 19 incident this repository lived
through: Issue #77's original "GitHub Actions is not acceptance Authority" clause, Round 5's later
`GITHUB_PREMERGE_GATE_GREEN` supplement (a distinct, additional Required Evidence gate, not a
contradiction of the original clause), and that supplement's later removal -- three genuine facts
about *how the applicable acceptance policy itself changed over time*, which nothing in this
repository previously represented as first-class, ordered, attributable records. It is **not** a
ninth Kernel element (`KERNEL_ELEMENT_COUNT=8`, `ONE_KERNEL_ELEMENT_PER_PACKAGE=true`) -- an
adapter/lineage layer, exactly as Boot, CLI, Agent Runtime, Independent Verification, Projection,
Runtime, Model Runtime, URL Boot, Change Executor and Multi-Agent already are. It mints no
Authority, no canonical State beyond its own seven new record kinds, no Evidence sufficiency, no
Change, and no completion.

```text
ACCEPTANCE_POLICY_OWNER_COUNT=1
PUBLIC_ACCEPTANCE_POLICY_ENTRY_POINT_COUNT=9
```

This is a first delivery against Issue #80's own adopted FD-0004 contract (`STRUCTURAL_REVIEW_
ROUNDS_APPLIED=0`). A real test suite (unit, contract, integration -- 62 tests) was written
alongside this document and is cited throughout §6 and §8 by real file and test name.

## 2. Public signature

```python
from manosube_agent_civilization.acceptance_policy import (
    open_acceptance_policy_baseline,
    resolve_and_verify_baseline,
    resolve_and_verify_transition,
    resolve_and_verify_adoption,
    resolve_and_verify_effective_policy,
    propose_acceptance_policy_transition,
    adopt_acceptance_policy_transition,
    preview_acceptance_policy_transition,
    assert_no_undeclared_policy_change_in_payload,
)

baseline = open_acceptance_policy_baseline(
    store, project_id,
    governing_issue=77,
    source_reference={                       # FD4-C3's own grammar -- the exact GitHub comment
        "comment_url": "https://github.com/manosube/manosube-agent-civilization-os/issues/77#issuecomment-...",
        "comment_id": "...", "comment_author": "manosube",
        "comment_author_association": "OWNER", "source_kind": "ORIGINAL_ISSUE",
    },
    clauses=[...],                            # every clause: existed_in_original_contract=True
    committed_at="2026-09-13T00:00:00Z",
)
baseline_ref = {"kind": "acceptance_policy_baseline", "id": baseline["acceptance_policy_baseline_id"]}

genesis_adoption = adopt_acceptance_policy_transition(
    store, project_id, governing_issue=77,
    adopted_ref=baseline_ref, decision_owner="SHUKOU",
    source_reference={...}, decided_at="...", committed_at="...",
)
adoption_refs = [{"kind": "acceptance_policy_adoption", "id": genesis_adoption["acceptance_policy_adoption_id"]}]

transition = propose_acceptance_policy_transition(
    store, project_id, governing_issue=77,
    baseline_ref=baseline_ref, adoption_refs=adoption_refs,
    clause_id="GITHUB_PREMERGE_GATE_GREEN", policy_operation="ADD",
    proposed_by="STRUCTURAL_ADVISOR", proposed_clause={...}, source_reference={...},
    rollback_condition="revert on demand", committed_at="...",
)

preview = preview_acceptance_policy_transition(store, project_id, baseline_ref, adoption_refs, transition)
preview["new_blockers"]                       # exactly what SHUKOU sees before adopting

adoption = adopt_acceptance_policy_transition(
    store, project_id, governing_issue=77,
    adopted_ref={"kind": "acceptance_policy_transition", "id": transition["acceptance_policy_transition_id"]},
    decision_owner="SHUKOU", source_reference={...}, decided_at="...", committed_at="...",
)
adoption_refs.append({"kind": "acceptance_policy_adoption", "id": adoption["acceptance_policy_adoption_id"]})

effective = resolve_and_verify_effective_policy(store, project_id, baseline_ref, adoption_refs)
effective["effective_clauses"]                # the derived, never-committed view

assert_no_undeclared_policy_change_in_payload(
    store, project_id, baseline_ref, adoption_refs,
    payload={"required_proofs": {"GITHUB_PREMERGE_GATE_GREEN_REQUIRED": True}},
)                                              # refuses unless payload["policy_change"] is True
```

## 3. Disclosed judgment calls

1. **Baseline / Transition / Adoption / derived Effective View is a four-shape design, not one
   the Issue dictates literally.** FD-0004's own text asks for closed schemas for "the original
   policy baseline", "a policy clause", "a proposed transition", "the SHUKOU adoption binding",
   "impact preview", "conflict/refusal outcome", and "a derived effective-policy view" -- seven
   nouns, not a wire format. This delivery reads those seven as: one immutable genesis Baseline
   (embeds every original clause), a Clause (embedded, never a standalone committed record --
   there is no independent lifecycle for a clause body outside a Baseline or a Transition's own
   `proposed_clause`), a Transition (one hash-linked ADD/REMOVE/REPLACE/NARROW/BROADEN/RECLASSIFY
   proposal on exactly one clause), an Adoption (the identity-bound SHUKOU act that activates one
   Baseline-or-Transition), a pure-function derived Effective View (never itself committed), an
   Impact Preview (pure, pre-adoption), and a Refusal Outcome (schema-declared for completeness;
   in this delivery every refusal is a raised typed exception, never a persisted record -- see
   item 7 below).
2. **Proposing is not adopting (FD4-C3's Agent/Human split), enforced structurally, not by
   convention.** `propose_acceptance_policy_transition` accepts any `proposed_by` role in
   `types.PROPOSER_ROLES` (`HUMAN_AUTHORITY`, `STRUCTURAL_ADVISOR`, `EXECUTOR`, `OTHER_AGENT`) and never
   changes the effective policy by itself -- a Transition sits inert, addressable, until a
   separate `adopt_acceptance_policy_transition` call names it. `engine.build_adoption` refuses
   (`AcceptancePolicyValidationError`) any `decision_owner != "SHUKOU"`, and
   `route._require_source_reference` independently refuses
   (`UnauthorizedPolicyAdoptionError`) any `source_reference.comment_author_association !=
   "OWNER"` -- two independent checks, at two independent points (build time and every resolve
   time), neither of which an Agent proposing a transition can satisfy on its own.
3. **Hash-linked lineage, not a flat append log.** Each Transition's own `prior_clause_binding`
   names the exact Baseline or Transition it extends (the same "walk backward through a hash
   link to verify" pattern this repository's own Reflow lifecycle-event chain already uses).
   `engine.derive_effective_policy` walks the *adoption* order (not the transition-creation
   order -- a transition can be proposed long before it is adopted) and refuses
   (`PolicyLineageConflictError`) the moment an adopted transition's own binding does not match
   the clause's currently-live predecessor reference -- this is what makes a fork, a reorder, or
   a stale base a structural refusal rather than a silently-resolved ambiguity.
4. **The semantic diff is computed over exactly three structured fields --
   `policy_class`/`blocking_effect`/`scope` -- and never over `statement`/`rationale` prose or
   the `existed_in_original_contract` lineage flag.** `engine.classify_operation` is the one
   function both `build_transition` (at propose time) and `derive_effective_policy` (at fold
   time, independently, a second time) call to check a transition's own declared
   `policy_operation` against the actual before/after clause bodies. `RECLASSIFY` takes priority
   over a simultaneous blocking-effect change (`test_reclassify_takes_priority_over_a_
   simultaneous_blocking_effect_change`) because a policy_class change is a categorically
   different kind of decision (who decides vs. what proof is required) than a widening or
   narrowing of the *same* Authority/Evidence class. A scope-only change (identical
   `policy_class`/`blocking_effect`) is `REPLACE`, not a no-op -- `scope` still participates in
   "is this a real change" (only an *entirely* identical comparison projection raises
   `UndeclaredPolicyChangeError`, per `test_classify_operation_refuses_a_semantically_identical_
   pair`).
5. **The undeclared-change scanner (FD4-C4) checks both dict keys and string values, recursively,
   for substring containment -- not only exact-value equality.** An early draft of
   `engine._mentions_in_text` matched only an exact string value; that version failed to catch
   the realistic Phase-19-incident shape (`{"required_proofs": {"GITHUB_PREMERGE_GATE_GREEN_
   REQUIRED": true}}` -- the clause_id `GITHUB_PREMERGE_GATE_GREEN` is a substring of the *key*,
   never a standalone value at all). `_find_known_clause_id_mentions` now walks every dict key
   and every string value (recursively through nested dicts/lists) and treats a clause_id
   appearing anywhere inside a longer string as a mention. This is a deliberately broad,
   fail-closed scan: it may over-flag a coincidental substring match, but this package's own
   position is that a false refusal on a genuinely unrelated payload is always cheaper than a
   silently smuggled policy change.
6. **`assert_no_undeclared_policy_change_in_payload` is a fresh, Store-resolved check every
   call, never a cached clause-id list.** `route.assert_no_undeclared_policy_change_in_payload`
   calls `resolve_and_verify_effective_policy` itself before scanning -- so the check is always
   against the actual current lineage, never a caller-supplied or stale set of clause ids a
   caller could under- or over-state.
7. **A conflict/refusal is always a raised typed exception, never a persisted "refusal record".**
   `acceptance_policy_refusal_outcome.schema.json` exists (FD-0004's own explicit "closed schema
   for conflict/refusal outcome" requirement, and `test_all_seven_required_schema_files_exist`/
   `test_every_schema_is_draft_2020_12_valid_and_resolvable` prove it is real, Draft-2020-12
   valid, and resolvable), but no production code path in this delivery ever constructs or
   commits one: every refusal in `engine.py`/`route.py` raises one of the six typed errors in
   `errors.py` before any Store mutation is attempted (`test_no_refusal_ever_advances_state_
   revision` proves this decisively across the full negative-control matrix). A refusal is a
   fact about *this call*, not a new fact for the lineage to carry forward -- persisting refusal
   attempts as first-class State would itself be a form of the exact mistake this Issue
   regresses against (an unreviewed side channel quietly becoming part of "what happened"). The
   schema is kept for wire-shape honesty (a future caller-facing API boundary could serialize a
   caught exception into this exact shape) without this delivery inventing a second, unused
   commit path to populate it.
8. **Content-addressed identity for every one of the five committed/derived record kinds, no
   narrow natural-key exception.** Unlike Multi-Agent's own deliberate five-of-six narrow-key
   design (`14_MULTI_AGENT/MULTI_AGENT_CONTRACT.md` §3 item 8), every Acceptance Policy record's
   `<kind>_id` is a full-content hash over its own `identity.py` semantic-fields tuple. This is
   the correct choice here specifically *because* FD4-C9 requires exact replay to be a pure
   content-equality question ("the identical record, resubmitted, is a no-op; a same-identity,
   different-body resubmission is a conflict") -- a narrow natural key would make two
   *semantically different* transitions on the same clause collide at the identity layer before
   ever reaching the semantic-diff gate, which is exactly the ambiguity this delivery's own
   lineage discipline exists to prevent.
9. **`route._commit_one_record`'s idempotency check is a pre-commit `resolve_record` read, not
   solely reliance on the Store's own transaction-id collision detection.** The Store's low-level
   `commit_state_transition` derives `from_revision`/fingerprints fresh from `load_current` on
   every call; a genuine replay (called *after* State has already advanced past the first commit)
   therefore never produces an identical transition envelope, so a bare "same transaction_id"
   check at the Store layer alone cannot detect it. `_commit_one_record` instead reads the target
   record directly by its own content-addressed identity *before* attempting any commit: an
   identical body already present is a no-op return; a different body at the same identity raises
   `ConflictingPolicyReplayError` immediately, with zero Store interaction. The retry loop's own
   `except (RecordConflictError, TransactionConflictError)` remains as defense-in-depth for a
   genuine concurrent race between the pre-check and the commit attempt (`test_route_py_
   translates_a_conflicting_replay_into_the_typed_package_error` proves the low-level Store
   exception is never allowed to leak past this package's own boundary).
10. **No second Authority evaluator; `HUMAN_AUTHORITY = "SHUKOU"` is a closed literal constant,
    matched by value (not import) to `development_binding.adoption_record.HUMAN_AUTHORITY`.**
    This package recognises exactly one Human Authority, the same one the existing adoption-record
    evaluator already enforces for instruction-to-authority binding -- it does not import that
    module (a genuinely independent, self-contained extension of the same real-world owner, not a
    second dependent one; `test_no_module_imports_the_authority_engine_or_mints_a_decision` proves
    no `authority` import exists anywhere in this package either).

## 4. Canonical owner

```text
acceptance_policy/route.py       the nine public entry points; the only module that ever
                                  resolves a record from the Store or commits one, through the
                                  one shared commit_state_transition (SINGLE_COMMITTER_REQUIRED)
acceptance_policy/engine.py      pure record builders, the semantic-diff classifier, the
                                  undeclared-change scanner, and the lineage fold; no Store I/O,
                                  no clock, no network
acceptance_policy/identity.py    deterministic full-content ids and semantic fingerprints for
                                  all five committed/derived record kinds
acceptance_policy/types.py       closed vocabularies (policy classes, operations, proposer
                                  roles, blocking-effect fields, lineage/source kinds, the one
                                  Human Authority constant)
acceptance_policy/errors.py      the typed refusal vocabulary, one base + six narrow subclasses
```

### 4.1 Canonical records

```text
acceptance_policy_baseline
    id/fingerprint: full-content hash over (project_id, governing_issue, source_reference,
    clauses) -- BASELINE_SEMANTIC_FIELDS. Genesis-immutable; embeds every original clause.

acceptance_policy_clause (embedded only -- never independently committed)
    comparison projection for the semantic diff: (clause_id, policy_class, blocking_effect,
    scope). statement/rationale are non-authoritative prose; existed_in_original_contract is a
    lineage fact about the clause version, not part of the diff.

acceptance_policy_transition
    id/fingerprint: full-content hash over (project_id, governing_issue, baseline_ref, clause_id,
    policy_operation, proposed_by, prior_clause_binding, proposed_clause,
    declared_existed_in_original_contract, policy_change_declared, source_reference,
    rollback_condition) -- TRANSITION_SEMANTIC_FIELDS.

acceptance_policy_adoption
    id/fingerprint: full-content hash over (project_id, governing_issue, adopted_ref,
    decision_owner, source_reference, decided_at) -- ADOPTION_SEMANTIC_FIELDS. decided_at
    participates in identity: two textually-identical SHUKOU decisions at genuinely different
    times are two different Human acts, never the same one replayed.

acceptance_policy_effective_view (derived only -- never committed)
    fingerprint: full-content hash over (project_id, governing_issue, baseline_ref,
    effective_clauses, folded_adoption_refs) -- EFFECTIVE_VIEW_SEMANTIC_FIELDS. A pure fold of
    baseline + ordered valid adoptions; never a caller-authored summary (FD4-C6).

acceptance_policy_impact_preview (derived only -- never committed)
    fingerprint: full-content hash over (project_id, governing_issue, before_policy,
    proposed_change, after_policy, new_blockers, removed_blockers, affected_work_units,
    rollback_condition) -- IMPACT_PREVIEW_SEMANTIC_FIELDS.

acceptance_policy_refusal_outcome (schema-declared only -- see §3 item 7; never committed by
    this delivery's own production code)
```

## 5. Canonical route

```text
open_acceptance_policy_baseline:
  validate source_reference (OWNER association) and every clause (existed_in_original_contract
  must be true for every genesis clause; no duplicate clause_id; at least one clause)
  -> engine.build_baseline stamps id/fingerprint
  -> commit via route._commit_one_record (content-addressed transaction_id == baseline id)

propose_acceptance_policy_transition:
  resolve-and-verify the baseline
  -> resolve_and_verify_effective_policy (fresh, Store-resolved -- never a caller-supplied view)
  -> resolve the real prior clause body for clause_id from the effective view's own
     provenance_chain (baseline clause, or the winning prior transition's proposed_clause)
  -> engine.build_transition: independently recomputes classify_operation(prior, proposed) and
     refuses (UndeclaredPolicyChangeError) if it disagrees with the declared policy_operation
  -> commit (never changes the effective policy by itself -- see §3 item 2)

adopt_acceptance_policy_transition:
  validate source_reference (OWNER association) and decision_owner == "SHUKOU"
  -> resolve-and-verify the adopted_ref target (baseline or transition) FIRST -- an adoption can
     never be minted for a target that does not genuinely exist under the identity it names
  -> engine.build_adoption
  -> commit

resolve_and_verify_effective_policy:
  resolve-and-verify the baseline
  -> resolve-and-verify every named adoption, in the given (= Store append) order
  -> resolve-and-verify every transition an adoption references
  -> engine.derive_effective_policy: fold baseline clauses, then each adopted transition in
     order, refusing (PolicyLineageConflictError) on missing predecessor / fork / reorder /
     stale binding / cross-project substitution / a REMOVE with no live clause / an ADD onto an
     already-live clause; re-verifies classify_operation a second time at fold time

preview_acceptance_policy_transition:
  resolve_and_verify_effective_policy (fresh)
  -> engine.build_impact_preview: pure before/after/new-blocker/removed-blocker projection;
     candidate_transition need not even be committed yet

assert_no_undeclared_policy_change_in_payload:
  resolve_and_verify_effective_policy (fresh)
  -> engine.assert_no_undeclared_policy_change: recursive key+value substring scan of payload
     against every known clause_id; refuses unless payload["policy_change"] is True
```

## 6. FD4-C1 through FD4-C10

### FD4-C1 -- Original policy baseline and proposed transitions as closed, hash-linked records

*Requirement:* the original acceptance-policy contract and every later proposed change are
represented as closed schemas / immutable value objects, hash-linked so lineage can be walked and
verified, never inferred from prose.

*Code:* `acceptance_policy_baseline.schema.json` (genesis, immutable, embeds every original
clause) and `acceptance_policy_transition.schema.json` (`prior_clause_binding` is the hash link --
`{source: BASELINE|TRANSITION, source_ref: {kind, id}}`, always resolving to the exact predecessor
record it extends). `engine.build_baseline`/`build_transition` stamp deterministic ids/fingerprints
via `identity.py`; `route.propose_acceptance_policy_transition` independently recomputes the
semantic diff against the *actual* resolved predecessor before ever committing (§3 item 4).

*Proof layer:* V1, `tests/unit/acceptance_policy/test_acceptance_policy_identity.py` (baseline/
transition id-and-fingerprint reproduction, hash-link binding); V6,
`test_missing_predecessor_transition_refuses`,
`test_a_fork_two_transitions_claiming_the_same_predecessor_refuses`,
`test_reordered_adoption_sequence_refuses`.

### FD4-C2 -- Immutable genesis baseline; no clause retroactively claims original status

*Requirement:* the original contract, once recorded, never changes shape; a later-added or
later-modified clause can never claim it always existed.

*Code:* `engine.build_baseline` refuses any clause not declaring `existed_in_original_contract=
True` (`test_baseline_refuses_a_clause_not_declaring_existed_in_original_contract`).
`engine.build_transition` refuses (`AcceptancePolicyValidationError`) if
`declared_existed_in_original_contract` is `True`, or if a `proposed_clause` itself declares
`existed_in_original_contract=True` -- a transition's own proposed clause always carries `False`,
structurally, never merely by convention.

*Proof layer:* V1, `test_baseline_refuses_a_clause_not_declaring_existed_in_original_contract`.

### FD4-C3 -- Identity-bound SHUKOU adoption; proposing is not adopting

*Requirement:* only an identity-bound SHUKOU adoption record activates a baseline or transition.
An Agent may propose; only the Human Authority may adopt.

*Code:* §3 items 2 and 6 above. `engine.build_adoption` refuses any `decision_owner != "SHUKOU"`
(`test_build_adoption_refuses_a_non_shukou_decision_owner`); `route._require_source_reference`
refuses any `comment_author_association != "OWNER"`
(`test_wrong_comment_author_association_refuses`); `route.resolve_and_verify_adoption` re-checks
both facts every time an adoption is *read*, not only at commit time (the same discipline
`change_executor`'s kill-switch resolver holds itself to). `test_wrong_human_authority_decision_
owner_refuses` proves a forged `decision_owner="CLAUDE_CODE"` adoption is refused before any
commit and never reaches the effective policy.

*Proof layer:* V1 (`test_adoption_id_and_fingerprint_reproduce_and_require_shukou`,
`test_build_adoption_refuses_a_non_shukou_decision_owner`); V6
(`test_wrong_human_authority_decision_owner_refuses`,
`test_wrong_comment_author_association_refuses`).

### FD4-C4 -- Fail-closed admission boundary against undeclared/smuggled policy changes

*Requirement:* an undeclared policy change smuggled into an unrelated record (a code finding,
`REQUIRED_PROOFS`, an implementation handoff, return Evidence, a closure sweep) must be refused
fail-closed, not silently admitted.

*Code:* `engine.assert_no_undeclared_policy_change` (§3 item 5), exposed through
`route.assert_no_undeclared_policy_change_in_payload` against the real, Store-resolved effective
policy (§3 item 6). Three decisive smuggling shapes are proven refused:
`test_undeclared_add_smuggled_inside_a_code_finding_refuses` (a bare value mention),
`test_undeclared_add_smuggled_only_inside_required_proofs_refuses` (the exact real-incident shape
-- a clause_id as a substring of a `REQUIRED_PROOFS` key), and
`test_a_handoff_cannot_activate_a_gate_not_present_in_effective_policy` (an implementation
handoff naming a gate the effective policy has never adopted). A payload that legitimately
declares `policy_change: True` is admitted
(`test_assert_no_undeclared_policy_change_admits_a_declared_change`).

*Proof layer:* V3 (unit), `tests/unit/acceptance_policy/test_acceptance_policy_diff.py`; V6
(integration, the real-shape smuggling controls above).

### FD4-C5 -- Structured semantic diff, never inferred from prose

*Requirement:* ADD/REMOVE/REPLACE/NARROW/BROADEN/RECLASSIFY is classified from structured fields
alone, never from `statement`/`rationale` prose, and a caller's declared operation is checked
against the independently computed one.

*Code:* `engine.classify_operation` (§3 item 4); called independently at both propose time
(`build_transition`) and fold time (`derive_effective_policy`) -- never trusted once and then
carried forward. `test_classify_operation_refuses_a_semantically_identical_pair` proves a
prose-only change (`statement` differs, structured fields identical) is refused as *not* a real
change, never silently classified as one.

*Proof layer:* V3, `test_acceptance_policy_diff.py` (10 classification tests covering all six
operations plus the priority/no-op edge cases).

### FD4-C6 -- Derived effective policy, never a caller-authored summary; explicit conflict representation

*Requirement:* the effective policy is derived only from baseline + valid identity-bound
SHUKOU-adopted transitions, in order; conflicting, missing, cyclic, stale, cross-project, or
unauthorized transitions must remain explicit and block a clean view, never silently resolved.

*Code:* `engine.derive_effective_policy` (§5 above); `identity.effective_view_semantic_
fingerprint` proves the view is itself a pure, reproducible function of its own inputs -- never a
field a caller could set independently. Every conflict class the requirement names raises
`PolicyLineageConflictError` or `PolicyProvenanceError`, never a partial or best-effort fold:
missing predecessor (`test_missing_predecessor_transition_refuses`), fork
(`test_a_fork_two_transitions_claiming_the_same_predecessor_refuses`), reordering
(`test_reordered_adoption_sequence_refuses`), cross-project substitution
(`test_wrong_project_substitution_refuses`), a REMOVE with no live clause / ADD onto an
already-live clause (`derive_effective_policy`'s own `is_currently_live` checks).

*Proof layer:* V1 (`test_impact_preview_fingerprint_reproduces` and the identity suite); V6, the
full conflict matrix above.

### FD4-C7 -- Pre-adoption impact preview

*Requirement:* SHUKOU can see, before adopting, exactly what a candidate transition would add,
remove, or reclassify against the real current effective policy.

*Code:* `engine.build_impact_preview` / `route.preview_acceptance_policy_transition` (§5 above) --
pure, requires no prior commit of the candidate. `new_blockers`/`removed_blockers` are computed as
set differences over `blocking_effect` true-fields between the real before/after clause bodies.

*Proof layer:* V1 (`test_impact_preview_fingerprint_reproduces`); integration
`test_impact_preview_shows_the_exact_before_after_and_new_blocker`.

### FD4-C8 -- The Phase 19 incident as a permanent regression fixture

*Requirement:* Issue #77's original "Actions is not acceptance Authority" clause, Round 5's later
`GITHUB_PREMERGE_GATE_GREEN` supplement, and that supplement's later removal must reconstruct as
three distinct, never-contradictory facts.

*Code:* `test_phase19_incident_reconstructs_as_three_distinct_facts_never_contradictory` builds
exactly this sequence against real route calls: a genesis baseline carrying the original
`ACTIONS_NOT_AUTHORITY` clause (`policy_class=AUTHORITY`), an ADD transition for
`GITHUB_PREMERGE_GATE_GREEN` (`policy_class=REQUIRED_EVIDENCE`) adopted second, then a REMOVE
transition for that same clause adopted third -- and asserts the effective policy after all three
adoptions still carries `ACTIONS_NOT_AUTHORITY` unchanged (never touched, never reclassified) while
`GITHUB_PREMERGE_GATE_GREEN` is genuinely absent again, with its own full add-then-remove history
still resolvable via the lineage (never erased). Two further tests close the two ways this
incident could otherwise be mis-modeled:
`test_removing_the_round5_supplement_as_original_restoration_without_the_real_transition_is_
impossible` proves a REMOVE cannot be proposed for a clause_id with no live predecessor to
classify against; `test_actions_is_not_authority_never_implies_actions_cannot_be_required_evidence`
proves the two clauses are independent `policy_class` members that never collapse into one
implication. `test_infrastructure_failure_never_changes_effective_policy` proves an infrastructure
failure (a CI run failing) is not itself a policy-lineage event at all -- nothing about the
effective policy moves without a genuine, adopted Transition.

*Proof layer:* V6, the four Phase-19-incident tests above.

### FD4-C9 -- Idempotent exact replay; conflicting replay refuses

*Requirement:* resubmitting the identical record is a no-op; resubmitting a different body under
the same identity refuses.

*Code:* `route._commit_one_record` (§3 item 9). `test_exact_replay_of_a_baseline_commit_is_
idempotent` proves a second, byte-identical `open_acceptance_policy_baseline` call advances
`state_revision` by zero. `test_conflicting_replay_of_the_same_transaction_id_refuses` proves a
forged low-level commit at the identical transaction id with a different record body raises the
Store's own `TransactionConflictError`; `test_route_py_translates_a_conflicting_replay_into_the_
typed_package_error` proves `route.py`'s own commit path translates this (and the `RecordConflict
Error` case) into `ConflictingPolicyReplayError`, never an opaque Store exception leaking past this
package's own boundary. `test_no_refusal_ever_advances_state_revision` sweeps the entire negative
matrix and proves every refusal in this delivery leaves `state_revision` untouched.

*Proof layer:* V6, the replay/conflict tests above.

### FD4-C10 -- Integration through existing owners; no second canonical owner

*Requirement:* this package integrates through the existing Authority/State/Evidence/Reflow/Store
owners; it never becomes a second one of any of them.

*Code:* static conformance (`tests/contract/acceptance_policy/test_acceptance_policy_static_
conformance.py`, 10 tests): exactly one module (`route.py`) ever imports `store.commit`
(`test_only_route_py_imports_the_store_commit_module`); no module constructs a `FileStateStore`
directly outside `route.py`; no module imports the Authority evaluator or Difference/Evidence/
Reflow engines at all (`test_no_module_imports_the_authority_engine_or_mints_a_decision`,
`test_no_module_imports_difference_evidence_or_reflow_engines`); `engine.py` never imports the
Store package (`test_engine_module_never_imports_the_store_package`); the public surface is
exactly the 9 documented entry points, verified by AST-level `__module__` filtering to exclude
imported names (`test_route_module_exposes_exactly_the_documented_public_functions`).

*Proof layer:* V7, static conformance.

## 7. Closed vocabularies

```text
POLICY_CLASSES              AUTHORITY, REQUIRED_EVIDENCE (FD4-C3/C4's own Authority-vs-Evidence
                             split -- a clause is exactly one, never both)
POLICY_OPERATIONS           ADD, REMOVE, REPLACE, NARROW, BROADEN, RECLASSIFY (FD4-C1/C5)
PROPOSER_ROLES              HUMAN_AUTHORITY, STRUCTURAL_ADVISOR, EXECUTOR, OTHER_AGENT
BLOCKING_EFFECT_FIELDS      implementation, structural_review, merge, issue_closure,
                             phase_completion -- one boolean per gate this Issue's own required
                             canonical model names explicitly
LINEAGE_SOURCE_KINDS        BASELINE, TRANSITION -- what a hash link may point at
SOURCE_KINDS                ORIGINAL_ISSUE (baseline only), STRUCTURAL_REVIEW, AUTHORITY_ADOPTION,
                             OTHER
HUMAN_AUTHORITY             "SHUKOU" -- the sole recognised Human Authority (§3 item 10)
REQUIRED_COMMENT_AUTHOR_
ASSOCIATION                 "OWNER" -- the sole comment-author association this package treats
                             as a genuine SHUKOU record
```

## 8. Required proof layers

```text
V1  Deterministic schema/identity totality       tests/unit/acceptance_policy/
    test_acceptance_policy_identity.py (15 tests): clause shape/enum validation, every one of
    baseline/transition/adoption/impact-preview reproduces its own id/fingerprint from its own
    content, changes when a semantic field changes, is stable under identical reconstruction,
    and every refusal path (empty clause list, duplicate clause_id, non-original-contract
    genesis clause, non-SHUKOU adoption) is exercised.

V3  Semantic diff and undeclared-change scanner  tests/unit/acceptance_policy/
    test_acceptance_policy_diff.py (17 tests): all six classify_operation outcomes plus the
    RECLASSIFY-priority and identical-clause-is-not-a-change edge cases, and the full
    undeclared-policy-change smuggling matrix (bare value, REQUIRED_PROOFS key substring,
    handoff, closure sweep, declared-change admission, non-object payload).

V6  Lineage integration, incident fixture, and   tests/integration/acceptance_policy/
    tamper/replay/substitution matrix            test_acceptance_policy_lineage_and_incident_
    fixture.py (19 tests): the canonical successful route (genesis, propose+adopt, impact
    preview), the four-test Phase 19 incident fixture (FD4-C8), the undeclared-change
    integration controls (FD4-C4), the Human-Authority/comment-association/cross-project tamper
    matrix (FD4-C3/C6), the missing-predecessor/fork/reorder lineage-conflict matrix (FD4-C6),
    exact-replay idempotency and conflicting-replay refusal (FD4-C9), and the decisive
    "no refusal ever advances state_revision" sweep.

V7  Static conformance                           tests/contract/acceptance_policy/
    test_acceptance_policy_static_conformance.py (10 tests): single Store committer, no second
    Store/Authority/Difference/Evidence/Reflow owner, engine.py touches no Store, the public
    surface is exactly the 9 documented entry points, no undocumented leading-underscore escape,
    and all 7 schemas exist, are Draft 2020-12 valid, and are internally resolvable.
```

Total: 62 tests, `pytest tests/unit/acceptance_policy tests/contract/acceptance_policy
tests/integration/acceptance_policy -q` -> `62 passed`.

## 9. Explicit non-claims

- **This delivery marks nothing complete.** No code in this package writes to the Phase Acceptance
  Ledger, closes Issue #80, or declares Phase 20. Only Structural Review, SHUKOU's own final
  acceptance, a manual merge, and after-state re-observation can do that (Issue #80's own explicit
  prohibition, restated here).
- **`acceptance_policy_refusal_outcome` is schema-representable but never committed by this
  delivery's own production code** -- see §3 item 7. Every refusal is a raised typed exception,
  proven never to mutate State.
- **This package proposes no changes to PR #78's own Actions policy, and never touches PR #78's
  branch.** It has no fixture, test, or code path that opens, resolves, or references PR #78 at
  all -- the Phase 19 incident fixture (FD4-C8) reconstructs the *policy lineage facts*, entirely
  independent of that PR's own live CI configuration.
- **This delivery does not retroactively validate or reinterpret Round 5 or Round 12 history.**
  The Phase 19 incident fixture demonstrates the *representational mechanism* this Issue asked
  for; it makes no claim about whether Round 5's own original supplement or its later removal was
  itself correct policy -- only that both are now representable as distinct, attributable,
  non-contradictory facts.
- **No parallel Authority/State/Evidence/Reflow/Store owner is introduced** (FD4-C10, V7). Issue
  #60's own existing discipline is left untouched -- this package imports none of its owners and
  is never itself imported by them.
- **`GITHUB_PREMERGE_GATE_GREEN` and `ACTIONS_NOT_AUTHORITY` (and every other clause_id used in
  this delivery's own tests and fixtures) exist only inside `tests/fixtures/acceptance_policy_
  world.py` and the test suite itself.** This delivery does not commit a real, production
  Baseline for this repository's actual current acceptance policy -- that is a Structural
  Review / SHUKOU decision, out of scope for this code delivery.
