# Product Binding Index (Phase 9, Issue #43)

```text
DOC_TYPE=BINDING_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=BINDING-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PRODUCT_BINDING_LAYER
CANONICAL_KERNEL_COUNT=1
PRODUCT_BINDING_OWNER_COUNT=1
PUBLIC_PRODUCT_BINDING_ENTRY_POINT_COUNT=1
```

---

## 0. What this document is

This is the one entry point for the **Product Binding** contract set -- the seven documents
under `03_BINDING/` that define how a real Human-declared project is bound to its Objective
Revision, Boundary, Authority policy reference, Source Registrations, Command Policy, and
secret-exclusion policy, and atomically adopted alongside genesis State.

```text
1. BINDING_INDEX.md              (this document)
2. PROJECT_BINDING.md            the one persisted record and its identity
3. BOUNDARY_CONTRACT.md          the declared operating boundary
4. TRUST_MODEL.md                Source Registration and Authority-reference semantics
5. SECRET_HANDLING.md            what may never be declared, and what may
6. COMMAND_EXECUTION_POLICY.md   the command-class ceiling, never an execution grant
7. SOURCE_REGISTRATION.md        the trust-declaration record
```

Read in that order for design and implementation work. `PROJECT_BINDING.md` is the load-
bearing document; the other five each own exactly one embedded structure it composes.

## 1. This is not Development Binding

`03_BINDING/CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md` and `03_BINDING/
DEVELOPMENT_BINDING_POLICY.json` govern **this repository's own** human/agent development
process (SHUKOU/構造参謀/Claude Code/GitHub role separation). Product Binding governs a
**real bound project's** own operating boundary. Neither substitutes for the other, and
neither document set may be edited to describe the other's concern.

```text
PRODUCT_BINDING_NE_DEVELOPMENT_BINDING=true
DEVELOPMENT_BINDING_SUBSTITUTION_ALLOWED=false
```

Their schemas are kept apart the same way: Development Binding's own policy artifact is
`03_BINDING/DEVELOPMENT_BINDING_POLICY.json` (hand-pinned code, never registered in
`01_SCHEMA/`); Product Binding's four schemas live under `01_SCHEMA/binding/`, the exact
location `tests/contract/binding/test_development_binding_conformance.py` had already
reserved for it.

## 2. This is not a ninth Kernel element

`00_KERNEL/KERNEL_INDEX.md` §4 fixes exactly eight Kernel elements (Objective through
Reflow). Product Binding is not a ninth -- the same `KERNEL_ELEMENT=none` convention
Development Binding already uses, and the same precedent Lineage's own non-element status
(`00_KERNEL/KERNEL_INDEX.md` §4.8) already set. It does not appear in `00_KERNEL/`'s own
numbered reading order, and it redefines no Kernel Contract's own semantics.

```text
KERNEL_ELEMENT=NONE_PRODUCT_BINDING_LAYER
CANONICAL_KERNEL_COUNT=1
```

## 3. This is not the Phase 8 fixture

`tests/fixtures/vertical_proof.py` binds a minimal, deterministic *test* world to the
Phase 8 natural-cycle proof; it creates no canonical Binding domain, schema, or production
identity of its own (`00_KERNEL/VERTICAL_PROOF_CONTRACT.md` §3). Product Binding is the
production owner Phase 8's own fixture explicitly deferred (`PHASE_8_FIXTURE_BINDING_NE_
PHASE_9_BINDING=true`). Neither fixture world imports the other.

## 4. Canonical owner

```text
src/manosube_agent_civilization/binding/
├── __init__.py    public exports
├── errors.py      BindingError / BindingValidationError / BindingIdentityError
├── identity.py    project_binding_id, verify_project_binding_identity
├── validation.py  schema-registry validation (the same registry every domain reads)
├── engine.py      assemble_project_binding -- the one validation+identity engine
└── route.py       bind_project -- the one public entry point
```

No second State, Store, Lineage, Recovery, Objective, Boundary, or Authority owner is
created anywhere in this package. Genesis State is produced by the existing State owner
(`manosube_agent_civilization.state.fingerprint.fingerprint_project_state`); atomic
adoption reuses the existing, generic `FileStateStore.initialize`.

## 5. Canonical successful route

```text
1. Human declares a Project Binding (Objective Revision body, Boundary, Authority policy
   reference, Source Registrations, Command Policy, secret-exclusion policy)
2. bind_project validates every embedded structure and cross-field constraint
3. bind_project mints and reverifies the content-addressed project_binding_id
4. bind_project computes genesis State's own semantic_fingerprint via the real State owner
5. FileStateStore.initialize atomically adopts the Objective Revision, the Project
   Binding, and genesis State in one transaction
6. A fresh Store instance / a fresh Python process resolves the identical Binding and
   reconstructs the identical State
7. An identical replay is a no-op; a conflicting replay is rejected before any mutation
```

No fake Observation, Evidence, Difference, Change, Closure, or Reflow record is ever
created to simulate this route.

## 6. Explicit non-claims

```text
BOOT_IMPLEMENTED=false
CLI_IMPLEMENTED=false
FILESYSTEM_SCAN_IMPLEMENTED=false
SYMLINK_RUNTIME_CONTAINMENT_PROVEN=false
COMMAND_EXECUTION_IMPLEMENTED=false
GITHUB_ADAPTER_IMPLEMENTED=false
EXTERNAL_OPERATION_EXECUTED=false
RUNTIME_PROVEN=false
TEMPORARY_AGENT_IMPLEMENTED=false
INDEPENDENT_VERIFICATION_IMPLEMENTED=false
AUTONOMOUS_CHANGE_IMPLEMENTED=false
MULTI_AGENT_IMPLEMENTED=false
PHASE_9_COMPLETE=false
PHASE_10_ALLOWED=false
```
