# Schema Index v0.1

```text
DOC_TYPE=SCHEMA_INDEX
JSON_SCHEMA_DIALECT=2020-12
STATUS=CANONICAL_DESIGN
```

Schema dependency is one-way: `common → objective → state`. Kernel contracts remain semantically superior. Every schema has one absolute `$id`; unknown fields and versions fail closed. The canonical inventory is 5 common, 4 objective, and 5 state schemas. Schema existence does not prove serialization, reload, runtime, or completion.

```text
SCHEMA_COUNT=14
STATE_ENGINE_IMPLEMENTED=false
KERNEL_V0_1_COMPLETE=false
```
