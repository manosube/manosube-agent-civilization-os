# Schema Index v0.1

```text
DOC_TYPE=SCHEMA_INDEX
JSON_SCHEMA_DIALECT=2020-12
STATUS=CANONICAL_DESIGN
```

Schema dependency is one-way: `common → objective → state → observation → difference → authority`. Kernel contracts remain semantically superior. Every schema has one absolute `$id`; unknown fields and versions fail closed.

The canonical inventory is:

```text
common=5
objective=4
state=5
observation=7
difference=12
authority=4
```

Observation schemas cover the immutable Observation／Fact／Negative Observation records, source-occurrence provenance Bindings, and append-only Fact／Negative evaluation records. Schema existence does not prove Observation Engine execution, Evidence persistence, Difference derivation, Reflow, or completion.

Difference schemas cover the immutable Difference Record, append-only Lifecycle Event, append-only Supersession Relation, Closure Policy, Closure Evaluation, Next Observation Request, Observation Method, Candidate Completion Record, Candidate Claim Evaluation Event, resolved Invariant Evaluation, Evidence Sufficiency Result and Reopen Condition Evaluation. Contract-derived inline projections such as normalized values, Effective Boundary, blocker scope／resolution condition, After-State Candidate and candidate evaluation Bindings remain owned through closed `$defs`.

Authority schemas cover the Authority Decision, the Authority Rule that permits, the Human Approval that binds one exact operation, and the Prohibition that refuses. A rule may declare only `AUTONOMOUS` or `HUMAN_APPROVAL_REQUIRED`; refusal is a Prohibition record, so permission and refusal never share one vocabulary. Schema existence does not prove Change execution, Evidence sufficiency or completion.

```text
SCHEMA_COUNT=37
OBSERVATION_SCHEMA_COUNT=7
DIFFERENCE_SCHEMA_COUNT=12
AUTHORITY_SCHEMA_COUNT=4
OBSERVATION_SCHEMA_VALIDATION_DEFINED=true
DIFFERENCE_SCHEMA_VALIDATION_DEFINED=true
AUTHORITY_SCHEMA_VALIDATION_DEFINED=true
OBSERVATION_ENGINE_IMPLEMENTED=true
DIFFERENCE_ENGINE_IMPLEMENTED=true
AUTHORITY_ENGINE_IMPLEMENTED=true
STATE_ENGINE_IMPLEMENTED=false
CHANGE_ENGINE_IMPLEMENTED=false
KERNEL_V0_1_COMPLETE=false
```
