# Project Binding Contract (Phase 9, Issue #43)

```text
DOC_TYPE=PROJECT_BINDING_CONTRACT
DOCUMENT_ID=BINDING-PROJECT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PRODUCT_BINDING_LAYER
```

See `BINDING_INDEX.md` for this contract set's own position and reading order.

## 1. Position

A Project Binding is the one immutable, content-addressed record that binds a real
Human-declared project to its Objective Revision, Boundary, Authority policy reference,
Source Registrations, Command Policy, and secret-exclusion policy. It is produced,
validated, and identified by exactly one owner
(`manosube_agent_civilization.binding.engine.assemble_project_binding`) and adopted by
exactly one public entry point (`manosube_agent_civilization.binding.route.bind_project`).

```text
PRODUCT_BINDING_OWNER_COUNT=1
PUBLIC_PRODUCT_BINDING_ENTRY_POINT_COUNT=1
```

## 2. Shape

Schema: `01_SCHEMA/binding/project_binding.schema.json`.

```text
schema_version              const "0.1"
project_binding_id          PROJBIND-<sha256 hex, uppercase> -- content-addressed, see §3
project_id                  common/identity.schema.json -- Human-declared, semantic, never
                             a filesystem path, URL, GitHub id, directory name, or mutable
                             locator (§4)
objective_revision_ref      {kind: "objective_revision", id} -- names the real Objective
                             Revision body bind_project also persists (§5)
boundary                    boundary.schema.json (BOUNDARY_CONTRACT.md)
authority_policy_ref        {kind: "authority_rule", id} -- resolves to a real, persisted
                             Authority Rule body (§5b), never a second Authority owner
                             (TRUST_MODEL.md §2)
source_registrations        array of source_registration.schema.json (SOURCE_REGISTRATION.md)
command_policy               command_policy.schema.json (COMMAND_EXECUTION_POLICY.md)
secret_exclusion_policy      forbidden_field_names + allowed_secret_reference_kinds
                              (SECRET_HANDLING.md) -- never an actual secret value
human_authority_ref           common/reference.schema.json
bound_at                      common/timestamp.schema.json -- excluded from identity, §3
```

`additionalProperties: false` throughout every embedded schema: an unrecognized field
anywhere in the accepted graph fails closed at schema validation, before any cross-field
reasoning runs.

## 3. Identity

`project_binding_id` is the sha256 content address (`PROJBIND-` prefix, uppercase hex) of
the closed field set `schema_version, project_id, objective_revision_ref, boundary,
authority_policy_ref, source_registrations, command_policy, secret_exclusion_policy,
human_authority_ref` -- the repo-wide canonical-serialization convention
(`state.canonicalize.canonical_json_bytes`, via `difference.canonical.canonical_bytes`),
the same one every other domain's own identity function reads rather than restates.

`bound_at` is excluded: it is the instant a declaration was adopted, never part of what was
adopted, exactly as Reflow's own `closure_evaluation_id` excludes its later-stamped
`reflow_transition_ref`.

`manosube_agent_civilization.binding.identity.verify_project_binding_identity` recomputes
the id from a record's own declared fields and requires it to equal the claimed id --
called once inside `assemble_project_binding` itself, so a forged or drifted id is refused
before any record is ever returned for persistence, not merely detected after the fact.

```text
PROJECT_BINDING_CONTENT_ADDRESSED=true
PROJECT_BINDING_IDENTITY_REVERIFIED=true
PROJECT_ID_IS_LOCATOR=false
```

## 4. `project_id` is not a locator

`project_id` uses the same generic `common/identity.schema.json` pattern
(`^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$`) every other cross-cutting canonical id in this Kernel
uses. That pattern structurally forecloses a filesystem path (no `/`), a URL (no scheme,
no `.`), a bare numeric GitHub repository id (must start with an uppercase letter), and a
lowercase directory name (must be uppercase) -- fail-closed by schema, never by inferring
meaning from the string's own content.

## 5. Objective Revision is accepted and persisted, not re-produced

`bind_project` accepts the real, Human-declared Objective Revision body and validates it
against Objective's own schema (`01_SCHEMA/objective/objective_revision.schema.json`,
never restated here). It mints no `objective_revision_id` of its own -- Objective Revision
identity remains Human-Authority-declared input, exactly as every other Kernel consumer of
it already treats it (`reflow/reference_registry.py`'s own inventory).

Unlike that existing precedent, Product Binding *does* persist the accepted Objective
Revision body as a Store-owned record (`kind="objective_revision"`), atomically alongside
the Project Binding and genesis State, through the existing, generic `FileStateStore.
initialize`. This is required to make Issue #43's own "same-id/different-body
substitution" negative control real and provable -- the Store's own generic manifest-
claimant mechanism (`FileStateStore._record_committed_by_any_transaction`) then protects it
identically to every other persisted record, with no domain-specific content-address logic
added to the Store itself.

```text
OBJECTIVE_REVISION_SECOND_PRODUCER=false
OBJECTIVE_REVISION_PERSISTED_AS_A_STORE_RECORD=true
```

## 5b. Authority Rule is accepted and persisted, not re-produced

**Added in Phase 9 Structural Review Round 1 (P9-R1-F1).** `bind_project` accepts the real
Authority Rule body `authority_policy_ref` names (a new required `authority_rule` keyword),
validates it against Authority's own existing schema (`01_SCHEMA/authority/
authority_rule.schema.json`, never restated here), and reverifies its identity via
Authority's own existing `authority.identity.rule_id` (never a second identity algorithm) --
requiring `rule_id(authority_rule) == authority_policy_ref["id"] ==
authority_rule["authority_rule_id"]`.

Two further checks, before any write:

```text
authority_rule.project_id == project_id                          (else BindingIdentityError)
authority_rule.declared_by == human_authority_ref                 (else BindingIdentityError,
                                                                    canonical-reference exact
                                                                    equality; see TRUST_MODEL
                                                                    .md §2b)
```

`authority_rule` is persisted as a Store-owned record (`kind="authority_rule"`) in the same
atomic `TX-GENESIS` manifest as the Objective Revision and Project Binding, through the
existing, generic `FileStateStore.initialize` -- protected by the Store's own generic
manifest-claimant mechanism identically to every other persisted record, with no
domain-specific content-address logic added to the Store itself.

```text
AUTHORITY_RULE_SECOND_PRODUCER=false
AUTHORITY_RULE_SECOND_IDENTITY_ALGORITHM=false
AUTHORITY_RULE_PERSISTED_AS_A_STORE_RECORD=true
AUTHORITY_POLICY_REF_RESOLVABLE_FROM_FRESH_STORE=true
```

## 6. Atomic adoption

`bind_project` builds a fully assembled genesis `project_state` dict (caller-supplied
`semantic_state`/`state_metadata`, `state_revision=0`), computes its real
`semantic_fingerprint` via `state.fingerprint.fingerprint_project_state` (the existing
State owner's own real producer), and calls `FileStateStore.initialize` once, with
`records=[objective_revision, authority_rule, project_binding,
*additional_genesis_records]` -- the identical `(kind, id, body)` shape, and the identical
atomic staged/journaled transaction mechanism (`TX-GENESIS`), R10-F1 already established for
genesis records this vertical's own State references. `additional_genesis_records` carries
whatever further records genesis State's own declared content references (its own Kernel
Source Snapshot, in particular) -- never a second genesis-record surface.

```text
BINDING_AND_GENESIS_ATOMICALLY_VISIBLE=true
SECOND_STATE_OR_STORE_OWNER_CREATED=false
```

## 7. Cross-consistency, checked before any write

```text
objective_revision.project_id == project_id                     (else BindingIdentityError,
                                                                   Round 1 P9-R1-F2)
objective_revision.human_authority_ref == human_authority_ref     (else BindingIdentityError,
                                                                    Round 1 P9-R1-F2)
genesis_state.project_id == project_id                         (else BindingIdentityError)
genesis_state.objective_revision_id == objective_revision_id    (else BindingIdentityError)
genesis_state.state_revision == 0                               (else BindingValidationError)
genesis_state.previous_state_fingerprint is None                (else BindingValidationError)
genesis_state.lineage_head_ref is None                          (else BindingValidationError)
```

See §5b for the Authority Rule's own cross-consistency checks.

## 8. Replay semantics

**Corrected in Phase 9 Structural Review Round 1 (P9-R1-F4).** `FileStateStore.initialize`
treats genesis as strictly one-shot: any second call for an already-initialized
`project_id` raises `AlreadyInitializedError`, with no body comparison of its own.
`bind_project` draws the identical-replay/conflicting-replay distinction over the Store's
own existing, generic read surfaces (`load_current`/`resolve_record`), plus a direct,
read-only reproduction of the genesis transaction's own recovery journal manifest
(`state/recovery/TX-GENESIS/manifest.json`, the identical file the Store's own
`_transaction_manifest_keys` reads for the same purpose) -- never a second persistence
mechanism, and never any Binding-specific comparison logic added to the Store itself.

The comparison now covers the **full** atomic manifest -- every member the genesis
transaction actually adopted (Objective Revision, Authority Rule, Project Binding, and
every `additional_genesis_records` member), not merely three named records. It is
order-independent (a replay supplying `additional_genesis_records` in a different order is
still a no-op) but duplicate-aware (two different bodies claimed under one `(kind, id)` in
one replay attempt is rejected as a conflict, never silently resolved to the last one seen).

```text
IDENTICAL_REPLAY_IS_NO_OP=true       (byte-identical Objective Revision, Authority Rule,
                                       Project Binding, genesis State, and every
                                       additional_genesis_records member, any order ->
                                       the already-committed result, no new write)
CONFLICTING_REPLAY_REJECTED_BEFORE_WRITE=true   (a missing, extra, wrong-kind, or
                                                  same-kind/id-different-body member ->
                                                  AlreadyInitializedError re-raised,
                                                  nothing new persisted)
FULL_MANIFEST_REPLAY_COMPARED=true
```

## 10. Typed reference classification

**Added in Phase 9 Structural Review Round 1 (P9-R1-F5).** Product Binding's own top-level
reference fields are classified, once, in `manosube_agent_civilization.binding.
reference_classification` -- pattern-compatible with, but organizationally separate from,
`reflow/reference_registry.py` (a different domain's own vocabulary, never repurposed as
this one's owner):

```text
field                    expected kind          classification
objective_revision_ref   objective_revision     Store-owned
authority_policy_ref     authority_rule         Store-owned
human_authority_ref      human_authority        external constitutional identity
```

`reject_wrong_kind_reference` runs before any Store lookup: a reference whose own `kind` is
not the one closed kind its field permits is refused, never silently accepted or narrowed
to whatever kind happened to be there (`CROSS_KIND_SUBSTITUTION_ALLOWED=false`).
`resolve_binding_references` recursively resolves every Store-owned field against a real
Store, proving `UNRESOLVED_STORE_OWNED_REFERENCE_COUNT=0` from both a fresh Store instance
and a fresh process.

```text
PRODUCT_BINDING_REFERENCE_CLASSIFICATION_COMPLETE=true
WRONG_KIND_REFERENCE_ACCEPTED=false
UNRESOLVED_STORE_OWNED_REFERENCE_ACCEPTED=false
```

## 9. Explicit non-claims

```text
FILESYSTEM_READ_PERFORMED=false
SOURCE_REGISTRATION_GRANTS_AUTHORITY=false
COMMAND_POLICY_GRANTS_AUTHORITY=false
COMMAND_EXECUTION_PERFORMED=false
SECRET_VALUE_PERSISTED=false
```
