# ADR-0012: Selection by exact binding, and reference paths declared by schema

```text
DOC_TYPE=STRUCTURAL_CORRECTION_AND_ENGINE_CONFORMANCE
DOCUMENT_ID=ADR-0012-DIFFERENCE-DECLARED-SELECTION-AND-REFERENCE-PATHS
STATUS=ACCEPTED
DECIDED_AT=2026-09-01
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0011
SOURCE=INDEPENDENT_REVIEW_OF_3a30039_AND_e0e7484
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
DERIVATION_INPUT_INTERFACE_EXTENDED=true
```

## 0. Position

Six findings, in two families.

**Three are the same mistake: a container was read as the binding.** The Engine treated
every Fact an Observation references as contributing, every Objective predicate list entry
as indexable by identity, and every Negative Evidence reference as belonging to whoever
cited it. In each case the record that *actually* binds was never selected.

**Three are the cost of the round-11/12 gates being one layer too coarse.** Reference
detection was decided by shape, so a canonical value that legitimately *is* a typed
reference was rejected as an unresolvable edge. The own-Scope resolver had no input route
for a lineage without a Difference predecessor. The relational pass reached Closure
Evaluations only through the events that cite them.

All six were reproduced before anything was changed:

```text
1  multi-subject Scope: Observation carries the Target's Fact and another subject's
     Engine   REJECTED  "the bound Observation carries a Fact outside the Target subject"
   same subject, Fact minted for another project (identity recomputes)
     Engine   ACCEPTED  observed candidates ['FOREIGN', 'NOT-READY']   <- worse than reported
     auditor  Difference projection mismatch
2  ABSENT evaluation citing Evidence its Negative Observation never declared
     Engine   ACCEPTED  auditor: Difference projection mismatch
3  two Target Predicates under one predicate_id
     Engine   ACCEPTED  projected the *last* one ('DEGRADED')
     auditor  Difference projection mismatch
4  Fact value {"kind": "widget", "id": "abc"} with value_type STRUCTURED
     Engine   REJECTED  "unknown reference kind: ... .value -> widget"
5  Scope-change re-observation with no Difference predecessor
     Engine   REJECTED  "carried Observation names a Scope absent from the bundle"
6  extra carried Closure Evaluation with a different target_predicate_ref
     Engine   ACCEPTED  auditor: evaluation Difference input mismatch
```

No Kernel contract text and no schema changed. No identity algorithm changed.

## 1. Selection is stated once

`difference/selection.py` decides *which* records a derivation is built from. Selection is
not validation: every selected record still crosses the schema, identity, boundary and
cross-record gates it always did.

**`contributing_facts`** returns the Facts of an Observation that bind this exact project
and Target subject, in the Observation's own reference order. A canonical Observation is
scoped to a *Scope*, not to a subject, so Facts for other included subjects are legitimate
provenance — they travel with the returned bundle and simply do not contribute here.
Rejecting the Observation for carrying them made a valid multi-subject Scope underivable.

The project half is the dangerous half. A Fact minted for another project recomputes its
own identity perfectly, so no downstream gate questioned it, and finding 1 turned out to be
worse than reported: the foreign project's value entered a `PRJ-0001` Difference's observed
candidates. The independent validator imports the same selector, so producer and auditor
cannot disagree about the source set.

**`unique_target_predicates`** rejects two payloads under one `predicate_id`.
`objective_revision.schema.json` declares `uniqueItems`, which compares whole payloads, so
two predicates sharing an identity satisfy it; the Engine's dict comprehension kept the
last, and the auditor resolved the first. A Target Predicate identity names one predicate;
two payloads under it is input the Difference route cannot interpret, and it fails closed
before any index is built.

## 2. Bounded Negative Evidence is a channel

`observation/verification.negative_evaluation_evidence_errors` — owned by the Observation
element, imported by both Engines and both independent validators — requires every Negative
Evaluation's Evidence to be declared by its own Negative Observation, and requires an
`ABSENT` or `EMPTY` conclusion to carry Evidence at all.

`CONFLICTED` is the one status that cites the *Observation* channel, and this is not a
relaxation. That status concludes the negative claim was contradicted by an observed Fact;
what proves that is the Observation Evidence which produced the Fact, since the bounded
Negative Evidence proves absence — precisely what is being contradicted. It stays bound, to
that Observation's declared Evidence, rather than free. **This repository's own Observation
Engine emits exactly that shape**, which is how the first, over-strict draft of the rule was
caught: `test_new_fact_conflicts_with_prior_negative_on_both_sides` rejected it.

## 3. Reference paths are declared by schema, not inferred from shape

The round-12 gate decided references structurally: any nested object with string `kind` and
`id`. That is unsound and cannot be tuned into soundness, because `IDENTITY_REFERENCE` is a
**declared canonical value type** — a schema-valid Fact value *is* `{"kind": ..., "id": ...}`.
Legitimate domain payload was rejected as an unresolvable edge.

Traversal now follows declared locations only, and completeness comes from a comparison
rather than a heuristic. `tests/schema_reference_paths.py` derives every identity-bearing
reference location from `01_SCHEMA` — **152 locations** — and a contract test compares it
against `REFERENCE_EDGES` in both directions, modulo two reviewed lists:

```text
EXCLUDED_REFERENCE_SUBTREES  4   value-bearing and foreign-owned subtrees, each with a
                                 stated reason: the three canonical value locations, and
                                 the Project State projection inside an after-state
                                 candidate, whose internal references the State element owns
NON_IDENTITY_POINTERS        6   typed pointers carrying no identity (a State revision and
                                 fingerprint, a git tree). They can never resolve, and a
                                 contract test proves every kind they name is external
```

Running that comparison for the first time found **six wrong paths in the round-12
registry** — `evidence_refs[]` where the schema declares `evidence_refs.members[]`,
`candidate_claim_bindings[]` where the property is `candidate_claim_evaluation_bindings[]`,
and two edges pinned to `{"type": "null"}` fields. Those edges had been matching nothing.
Eight schema-declared locations were missing entirely, including the Difference's own
`authority_required` and the normalized observed-state projection's copies of its Scope and
snapshot bindings. `supersession_relation` was removed from `RESOLVABLE_KINDS`: no canonical
schema declares a reference to one, so listing it claimed an obligation nothing bears.

## 4. A fresh derivation across a Scope change

ADR-0011 made every Observation resolve against its own Scope. With a Difference
predecessor the historical Scope arrives as carried context; with none it could not arrive
at all, because the canonical Observation bundle has no Scope section — a contract test now
asserts that emptiness rather than assuming it.

`binding["historical_observation_scopes"]` is the explicit route. **This extends the
derivation-request interface, which is this Issue's own input contract; no Kernel schema
changed.** It supplies records only and relaxes nothing:

* each Scope crosses the same canonical input gate as the resolved Scope, and must belong
  to this project;
* a supplied Scope restating the resolved Scope's identity with a different payload fails
  closed;
* the resolved Scope remains the sole boundary of the Difference derived here;
* a Scope no carried Observation names is rejected, not emitted — otherwise the route would
  be a way to inject unrelated records into the output;
* the binding key set is now closed, so an unknown binding key is rejected rather than
  ignored.

## 5. Every carried Closure Evaluation

`lifecycle.closure_evaluation_input_errors` is extracted from the independent validator and
imported back by it, and the Engine applies it to **every** record in `evaluations` — not
only those a transition cites. It decides what the bundle alone can decide: subject
Difference, Closure Policy binding, event head, Target Predicate, evaluated Objective
semantics and evaluated-State self-consistency.

The **orphan rule is stated, not assumed**: an unreferenced Evaluation is permitted as
provenance — the contract does not require a citing transition — and is held to exactly the
same input binding as one that is cited. The independent validator additionally requires an
unpromoted Evaluation to be evaluated at the bundle's current State head, and the test that
carries a valid unreferenced Evaluation builds it that way.

Two limits stay with the auditor, for the same reason as ADR-0011's Reflow window: the
multi-revision editorial Objective chain and the bundle-wide current-State head need
analysis this phase does not carry.

## 6. Proofs added

```text
tests/contract/difference/test_reference_paths.py             47 cases
  - schema-derived inventory (152 locations) == REFERENCE_EDGES, both directions, per type
  - every excluded subtree names a real schema location; every non-identity pointer's
    kinds are enumerated non-claims; every resolvable kind is reachable from an edge
  - a reference-shaped canonical value, a registered-kind lookalike and a nested
    collection of them are all payload, and are never traversed
  - shape-based detection is gone and cannot return

tests/unit/difference/test_reference_closure.py              151 cases
  - one dangling-edge mutation per declared resolving edge per kind (68)
  - one wrong-kind mutation per declared resolving edge (68)
  - one dangling-key mutation per declared foreign key (11)
  - the edge matrix covers every resolvable kind

tests/unit/difference/test_source_selection.py                14 cases
  - multi-subject Observation derives, stays cross-record valid, and keeps the unrelated
    subject as provenance; input order does not change the selection
  - a same-subject Fact minted for another project never contributes
  - four duplicate-predicate payload mutations, order reversal, identical duplicate,
    single-predicate control, predicate without an identity

tests/unit/difference/test_negative_evidence_channel.py       12 cases
  - foreign negative Evidence, Observation-channel Evidence, both
  - ABSENT and EMPTY with no Evidence; NO_RESULT and UNOBSERVED unaffected
  - CONFLICTED may cite its own Observation's Evidence and nothing else
  - unresolvable owner; the Observation element applies the same rule to its own output

tests/unit/difference/test_historical_scopes.py               13 cases
  - the lineage really spans two Scopes with one recurring Fact, and the Observation
    bundle really has no Scope section
  - absent, forged, contradicting, foreign-project, schema-invalid and unused Scopes
  - the resolved Scope remains the boundary; every Observation verified against its own
  - the binding key set is closed; the request is never mutated

tests/unit/difference/test_closure_evaluation_binding.py      35 cases (11 added)
  - an unreferenced Evaluation is carried, and held to the same input binding
  - six input mutations on an unreferenced Evaluation
  - the input authority is shared with the auditor; the section is visited once
```

## 7. Acceptance

```text
SOURCE_SELECTION_AUTHORITY_COUNT=1
FACT_SELECTED_BY_PROJECT_AND_SUBJECT=true
MULTI_SUBJECT_SCOPE_DERIVABLE=true
FOREIGN_PROJECT_FACT_EXCLUDED=true
FULL_OBSERVATION_PROVENANCE_PRESERVED=true
TARGET_PREDICATE_IDENTITY_UNIQUE=true
NEGATIVE_EVIDENCE_CHANNEL_AUTHORITY_COUNT=1
NEGATIVE_EVALUATION_EVIDENCE_BOUND=true
REFERENCE_PATHS_DECLARED_BY_SCHEMA=true
SCHEMA_DECLARED_REFERENCE_LOCATIONS=152
DECLARED_REFERENCE_EDGES=128
DECLARED_FOREIGN_KEYS=11
RESOLVABLE_REFERENCE_KIND_COUNT=19
EXCLUDED_REFERENCE_SUBTREE_COUNT=4
NON_IDENTITY_POINTER_COUNT=6
SHAPE_BASED_REFERENCE_DETECTION=removed
CANONICAL_VALUE_NEVER_TRAVERSED=true
HISTORICAL_SCOPE_INPUT_ROUTE=explicit
NO_PREDECESSOR_SCOPE_CHANGE_DERIVABLE=true
BINDING_KEY_SET_CLOSED=true
EVERY_CARRIED_EVALUATION_VALIDATED=true
ORPHAN_EVALUATION_RULE=permitted_and_fully_gated

KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
CANONICAL_OWNER_COUNT=1
```

```text
DERIVATION_INPUT_INTERFACE_EXTENDED=true   # historical_observation_scopes; no Kernel schema
ENGINE_EMBEDS_INDEPENDENT_AUDITOR=false
CLOSURE_EVALUATION_EXECUTION_IMPLEMENTED=false
REFLOW_COMMITMENT_CLAIMED=false
OBJECTIVE_EDITORIAL_CHAIN_CLAIMED=false    # the auditor owns the multi-revision analysis
OBSERVATION_METHOD_CLOSURE=partial
TARGET_PREDICATE_RESOLVED_STRUCTURALLY=false
SUPERSESSION_RELATION_IS_NEVER_REFERENCED=true
REOPENED_CROSS_RECORD_PROVEN=false
LATER_PHASE_SEMANTICS_CLAIMED=false
CHANGE_AND_REFLOW_SCHEMA_AVAILABLE=false
IMPACT_PROJECTION_UNCONSTRAINED=true
DIFFERENCE_RUNTIME_PROVEN=false
KERNEL_V0_1_COMPLETE=false
```

`DERIVATION_INPUT_INTERFACE_EXTENDED` is recorded rather than buried. The derivation
request is this Issue's own input interface — no file under `00_KERNEL/` or `01_SCHEMA/`
changed — and the new key is explicit, optional, immutable, deterministic, schema-validated
per record and adapter-free. Where the Kernel later defines a canonical context source for
historical Scopes, this route should be replaced by it rather than kept alongside.
