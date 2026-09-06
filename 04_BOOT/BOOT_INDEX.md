# Boot Index (Phase 10, Issue #45)

```text
DOC_TYPE=BOOT_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=BOOT-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_ADAPTER_ENTRY
CANONICAL_KERNEL_COUNT=1
BOOT_OWNER_COUNT=1
PUBLIC_BOOT_ENTRY_POINT_COUNT=1
```

---

## 0. What this document is

This is the one entry point for the **Boot** contract set -- the two documents under
`04_BOOT/` that define how an already-bound Project is restored from an existing canonical
Store into one immutable, non-authoritative Boot Context.

```text
1. BOOT_INDEX.md      (this document)
2. BOOT_CONTRACT.md   the one public route, its frozen semantics, and its negative controls
```

Read `BOOT_CONTRACT.md` for the load-bearing design; this document only fixes Boot's own
position relative to the rest of the Kernel and to Product Binding.

## 1. This is not a ninth Kernel element

`00_KERNEL/KERNEL_INDEX.md` §4 fixes exactly eight Kernel elements (Objective through
Reflow). Boot is not a ninth -- the same `KERNEL_ELEMENT=none` convention Development
Binding and Product Binding already use. It does not appear in `00_KERNEL/`'s own numbered
reading order, and it redefines no Kernel Contract's own semantics.

```text
KERNEL_ELEMENT=NONE_ADAPTER_ENTRY
CANONICAL_KERNEL_COUNT=1
```

## 2. This is not Product Binding, and not a second Binding owner

Boot never validates, assembles, mints, or adopts a Project Binding -- that remains
`03_BINDING/`'s own, one-owner concern (`manosube_agent_civilization.binding`). Boot only
*resolves and reverifies* an already-adopted Project Binding through that same package's own
public identity and reference-resolution functions
(`verify_project_binding_identity`, `resolve_binding_references`,
`reject_wrong_kind_reference`), reused rather than restated.

```text
BOOT_IS_A_SECOND_BINDING_OWNER=false
BOOT_CALLS_BIND_PROJECT=false
```

## 3. This is not initialization, discovery, or repair

Boot never calls `FileStateStore.initialize`, never calls `FileStateStore.recover`, never
enumerates Store projects, and never infers an identity from a path, URL, repository name,
or the current working directory. A caller must already know the exact `project_id` and
`project_binding_id` of an already-bound Project; Boot restores it, or fails closed.

```text
BOOT_IS_RESTORATION=true
BOOT_IS_INITIALIZATION=false
BOOT_MAY_MUTATE_STORE=false
BOOT_MAY_CREATE_BINDING=false
BOOT_MAY_REPAIR_STORE=false
BOOT_MAY_DISCOVER_PROJECT=false
```

## 4. Canonical owner

```text
src/manosube_agent_civilization/boot/
├── __init__.py     public exports
├── errors.py       BootError / BootNotFoundError / BootConsistencyError
├── context.py      BootContext -- the one immutable, non-authoritative return type
└── route.py        boot_project -- the one public entry point
```

No second State, Store, Lineage, Recovery, Objective, Boundary, Authority, or Binding owner
is created anywhere in this package. Current State is reconstructed exclusively through the
existing append-only lineage owner's pure, read-only replay (`FileStateStore.reconstruct` --
never `FileStateStore.load_current`, which performs a real write to materialize a missing
`current.json` view, Structural Review Round 1 P10-R1-F2); the Project Binding, Objective
Revision, and Authority Rule are resolved exclusively through the existing Product Binding
owners; no new schema and no new persisted record kind is introduced.

## 5. Explicit non-claims

```text
CLI_IMPLEMENTED=false
PROJECT_DISCOVERY_IMPLEMENTED=false
FILESYSTEM_SCAN_IMPLEMENTED=false
SYMLINK_RUNTIME_CONTAINMENT_PROVEN=false
STORE_PATH_INFERRED_FROM_CWD=false
STORE_RECOVERY_AUTO_EXECUTED=false
COMMAND_EXECUTION_IMPLEMENTED=false
GITHUB_ADAPTER_IMPLEMENTED=false
EXTERNAL_OPERATION_EXECUTED=false
RUNTIME_OBSERVATION_IMPLEMENTED=false
TEMPORARY_AGENT_IMPLEMENTED=false
INDEPENDENT_VERIFICATION_IMPLEMENTED=false
AUTONOMOUS_CHANGE_IMPLEMENTED=false
MULTI_AGENT_IMPLEMENTED=false
PHASE_10_COMPLETE=false
PHASE_11_ALLOWED=false
```
