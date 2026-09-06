# Secret Handling (Phase 9, Issue #43)

```text
DOC_TYPE=SECRET_HANDLING_CONTRACT
DOCUMENT_ID=BINDING-SECRET-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PRODUCT_BINDING_LAYER
```

## 1. Position

No token, password, private key, credential body, or other secret material may ever enter
a Binding request, a canonical record, an identity input, a fixture, a log, or a Store
record. Only a non-secret secret-*reference* policy may be declared.

```text
SECRET_VALUE_PERSISTED=false
```

## 2. `secret_exclusion_policy` shape

Schema: the `secret_exclusion_policy` `$defs` entry in `01_SCHEMA/binding/
project_binding.schema.json`.

```text
forbidden_field_names            array of field-name strings, unique
allowed_secret_reference_kinds   array from a closed enum: ENVIRONMENT_VARIABLE_REFERENCE,
                                  EXTERNAL_SECRET_MANAGER_REFERENCE
```

`additionalProperties: false`: this shape never accepts a field for an actual secret
value -- only field *names* and a closed reference-*kind* enum. A caller attempting to add
any other field (a real value, an inline credential) fails schema validation immediately.

## 3. Scan boundary

`manosube_agent_civilization.binding.engine.assemble_project_binding` runs the repo-wide
secret scan (`difference.canonical.reject_secret_material`) over the whole accepted
declaration *except* `secret_exclusion_policy` itself -- that subtree's own field names
(`allowed_secret_reference_kinds`, ...) legitimately name the concept they forbid, and
would otherwise trip the scan's own secret-*key*-name pattern by simply naming it. Every
other field (Boundary, Source Registrations, Command Policy, every typed reference) is
scanned, both by key name and by value pattern (recognizable token/private-key/credential
shapes), before any identity is minted.

```text
SECRET_SCAN_COVERS_WHOLE_DECLARATION_EXCEPT_ITS_OWN_POLICY_SUBTREE=true
```
