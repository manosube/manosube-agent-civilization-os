# Schema Index v0.1

```text
DOC_TYPE=SCHEMA_INDEX
JSON_SCHEMA_DIALECT=2020-12
STATUS=CANONICAL_DESIGN
```

Schema dependency is one-way: `common → objective → state → observation → difference`. Kernel contracts remain semantically superior. Every schema has one absolute `$id`; unknown fields and versions fail closed.

The canonical inventory is:

```text
common=5
objective=4
state=5
observation=7
difference=7
```

Observation schemas cover the immutable Observation／Fact／Negative Observation records, source-occurrence provenance Bindings, and append-only Fact／Negative evaluation records. Schema existence does not prove Observation Engine execution, Evidence persistence, Difference derivation, Reflow, or completion.

Difference schemas cover the immutable Difference Record, append-only Lifecycle Event, append-only Supersession Relation, Closure Policy, Closure Evaluation, Next Observation Request and Observation Method. Contract-derived inline projections such as normalized values, Effective Boundary, blocker scope／resolution condition, After-State Candidate and candidate evaluation Bindings remain owned through closed `$defs`.

```text
SCHEMA_COUNT=28
OBSERVATION_SCHEMA_COUNT=7
DIFFERENCE_SCHEMA_COUNT=7
OBSERVATION_SCHEMA_VALIDATION_DEFINED=true
DIFFERENCE_SCHEMA_VALIDATION_DEFINED=true
OBSERVATION_ENGINE_IMPLEMENTED=false
DIFFERENCE_ENGINE_IMPLEMENTED=false
STATE_ENGINE_IMPLEMENTED=false
KERNEL_V0_1_COMPLETE=false
```
