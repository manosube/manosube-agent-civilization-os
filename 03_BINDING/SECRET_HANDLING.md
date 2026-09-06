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

**Corrected in Phase 9 Structural Review Round 1 (P9-R1-F3).** A prior version of this scan
excluded `secret_exclusion_policy` wholesale (both its field *names* and its own *values*)
to avoid a false positive on its own field name `allowed_secret_reference_kinds` (which
legitimately names the concept it forbids). That exclusion was too broad: it also silently
exempted that subtree's own *values* (e.g. `forbidden_field_names` list entries) from the
secret-*value*-pattern check, letting a real secret-shaped string smuggled in as a "field
name" escape scanning entirely.

`manosube_agent_civilization.binding.engine.assemble_project_binding` now runs the
repo-wide secret scan (`difference.canonical.reject_secret_material`) over the **whole**
accepted declaration, `secret_exclusion_policy`'s own subtree included. The two field
*names* that legitimately name the concept they forbid (`secret_exclusion_policy` itself
and its own `allowed_secret_reference_kinds`) are allowlisted at the scan's one shared
source (`difference.canonical._SECRET_KEY_ALLOWLIST`, alongside the pre-existing
`credential_paths` entry) -- no second, competing secret-key-name taxonomy is created. Every
field's own *value* is scanned uniformly, `secret_exclusion_policy`'s own values included:
a real secret-shaped string (a GitHub-token-shaped value, a private-key block, ...) is
rejected wherever it appears in the accepted graph, this subtree included.

```text
SECRET_POLICY_FIELD_NAMES_ALLOWED=true
SECRET_VALUE_IN_SECRET_POLICY_REJECTED=true
```

## 4. Scan scope corrected to the whole accepted/persisted graph (Round 2 P9-R2-F1)

**Corrected in Phase 9 Structural Review Round 2.** §3's own "whole accepted declaration"
claim was itself incomplete: it described only `assemble_project_binding`'s own scan of the
Project Binding record. 構造参謀's Round 2 re-observation found that `bind_project` also
accepts and persists Objective Revision, Authority Rule, genesis State, and every
`additional_genesis_records` member -- none of which were ever scanned. A secret-shaped
value in, for example, an Objective Revision's own free-text `semantic_change_summary`
field passed silently through to persistence.

`manosube_agent_civilization.binding.admission.admit_genesis_transaction` (see
`PROJECT_BINDING.md` §9b) now scans every one of those bodies too, before
`store.initialize` is ever called. `session_id` (`01_SCHEMA/state/state_metadata.
schema.json`'s own `execution_context.session_id` field) is added to the shared
`difference.canonical._SECRET_KEY_ALLOWLIST` alongside the existing entries -- a real,
pre-existing Kernel schema field name that only became reachable by the scan once genesis
State itself was included in scope, never a secret carrier.

```text
SECRET_SCAN_COVERS_WHOLE_ACCEPTED_GRAPH=true
SECRET_SCAN_ERROR_NEVER_ECHOES_THE_SECRET_VALUE=true
```

## 5. Scan ordering relative to additional-record identity reverification (Round 3 P9-R3-F3)

**Added in Phase 9 Structural Review Round 3.** `admit_genesis_transaction` now reverifies
each `additional_genesis_records` member's own content-addressed identity (P9-R3-F3) before
the secret scan runs (SHUKOU's own required admission order, §2 of the Round 3 adoption:
schema validation and identity reverification precede the secret scan). For a
content-addressed kind such as `source_snapshot`, every substantive field participates in
that content address, so a secret-shaped value injected into any of them necessarily changes
the record's own recomputed identity too -- identity reverification fails closed first,
before the secret scan is ever reached. This is not a gap: a body that fails identity
reverification is refused regardless of what the secret scan would have found, and a body
that is genuinely self-consistent (its own declared id legitimately recomputes, including
when a legitimately-content-addressed field happens to contain a secret-shaped string) still
reaches, and is caught by, the secret scan.

```text
SECRET_SCAN_MAY_BE_PREEMPTED_BY_IDENTITY_REVERIFICATION_FOR_CONTENT_ADDRESSED_KINDS=true
SELF_CONSISTENT_SECRET_SHAPED_ADDITIONAL_RECORD_BODY_STILL_REJECTED=true
```
