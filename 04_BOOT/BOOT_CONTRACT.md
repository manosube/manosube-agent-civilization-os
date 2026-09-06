# Boot Contract (Phase 10, Issue #45)

```text
DOC_TYPE=BOOT_CONTRACT
DOCUMENT_ID=BOOT-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_ADAPTER_ENTRY
BASE_SHA=af2624ca5a73b1ae0811c320a5102552cdf6175e
```

See `BOOT_INDEX.md` for this contract set's own position and reading order.

## 1. Position

Boot restores one already-bound Project -- its Project Binding, Objective Revision,
Authority Rule, and current State -- from an existing, already-initialized canonical Store
into one immutable, non-authoritative Boot Context, so a caller can begin a Phase 8 Reflow
cycle. It is produced by exactly one owner
(`manosube_agent_civilization.boot.route.boot_project`) and returns exactly one
non-authoritative projection type (`manosube_agent_civilization.boot.context.BootContext`).

```text
BOOT_OWNER_COUNT=1
PUBLIC_BOOT_ENTRY_POINT_COUNT=1
```

## 2. Public signature

```python
boot_project(store, *, project_id: str, project_binding_id: str) -> BootContext
```

*store* is an already-constructed `FileStateStore` (or any object exposing its public read
surfaces) over a Store root that already has a real, committed genesis for *project_id*.
*project_id* and *project_binding_id* are explicit canonical identities the caller already
knows -- never a locator Boot must resolve, search, or infer.

## 3. Frozen semantic decisions

1. **Boot is restoration, not initialization.** Boot never calls `bind_project`,
   `FileStateStore.initialize`, or synthesizes a missing Binding/State record.
2. **Boot is not discovery.** The caller supplies `project_id`/`project_binding_id`
   explicitly. Boot never enumerates Store projects, scans a filesystem, inspects the
   current working directory, or infers identity from a path/URL/directory name.
3. **The existing Store and owners remain authoritative.** Boot uses only `FileStateStore`'s
   public read surfaces (`resolve_record`, `load_current`) and Product Binding's own public
   identity/reference-resolution functions. It creates no second Store/State/Binding/
   Objective/Authority/reference-resolution owner and duplicates no identity algorithm.
4. **Lineage is the State restoration authority.** Current State is reconstructed through
   `FileStateStore.load_current`, which itself reconstructs exclusively from the committed
   append-only lineage log. A materialized `current.json` body, a caller-supplied State, a
   cache, or a fixture is never a substitute.
5. **Binding identity and reference closure are reverified.** Boot resolves the exact
   `project_binding` record, recomputes its content-addressed identity through
   `manosube_agent_civilization.binding.verify_project_binding_identity`, and resolves its
   Store-owned references through `manosube_agent_civilization.binding.
   resolve_binding_references`. Missing, wrong-kind, same-id/different-body, or unresolved
   references fail closed.
6. **Cross-record equality is mandatory** (§5, step 8, below).
7. **Boot Context is an ephemeral projection, not Canonical State.** `BootContext` grants no
   Authority, closes no Difference, changes no State, and is never persisted as a second
   canonical record. Its mapping fields are `types.MappingProxyType`-wrapped and the
   dataclass itself is frozen.
8. **Boot is fail-closed and transactionally read-only.** A successful Boot performs no
   State transition, manifest adoption, lineage append, record promotion, command
   execution, or external write. A Store indicating corruption, partial visibility, an
   interrupted transaction, a missing genesis institution, or an inconsistent public read
   surface propagates its own typed Store error unchanged -- Boot never calls
   `FileStateStore.recover` and never "repairs" canonical history.

## 4. Canonical owner

```text
src/manosube_agent_civilization/boot/
├── __init__.py     public exports
├── errors.py       BootError / BootNotFoundError / BootConsistencyError
├── context.py      BootContext
└── route.py        boot_project
```

`BootNotFoundError` and `BootConsistencyError` exist only for the checks this route itself
owns (a required reference does not resolve; a cross-record invariant §5 step 8 requires
does not hold). Every other failure mode propagates the existing owner's own typed error
unchanged: `manosube_agent_civilization.binding.errors.BindingIdentityError`/
`BindingValidationError` for Product Binding identity/shape,
`manosube_agent_civilization.authority.identity.rule_id`'s own recompute for Authority Rule
identity, and `manosube_agent_civilization.store.errors.CorruptStoreError`/
`StateNotFoundError`/`BoundaryError` for Store-owned corruption, uninitialized-project, and
boundary violations.

## 5. Canonical successful route

```text
1. Receive an existing Store plus explicit project_id and project_binding_id.
2. Reject either identity if it is not a plain, non-empty string, or looks like a path/URL
   (contains "/", "\", "://", or a ".." prefix) -- never a locator.
3. Resolve project_binding/<project_binding_id> through store.resolve_record.
4. Require the resolved record's own declared project_binding_id to equal the requested
   project_binding_id.
5. Reverify Product Binding identity via
   manosube_agent_civilization.binding.verify_project_binding_identity.
6. Require the resolved record's own project_id to equal the requested project_id.
7. Reject a wrong-kind objective_revision_ref/authority_policy_ref/human_authority_ref via
   manosube_agent_civilization.binding.reject_wrong_kind_reference.
8. Resolve Objective Revision and Authority Rule via
   manosube_agent_civilization.binding.resolve_binding_references; require both to resolve.
   Recompute the Authority Rule's own authority_rule_id via
   manosube_agent_civilization.authority.identity.rule_id and require it to equal both the
   rule's own declared id and project_binding.authority_policy_ref.id. Require:
   requested project_id
     = project_binding.project_id = authority_rule.project_id = objective_revision.project_id
   project_binding.human_authority_ref
     = objective_revision.owner_authority_ref
     = objective_revision.human_authority_ref
     = authority_rule.declared_by
   (canonical reference exact equality throughout -- kind correctness never substitutes for
   identity equality).
9. Reconstruct current State via store.load_current (never store.recover). Require:
   reconstructed_state.project_id = requested project_id
   reconstructed_state.objective_revision_id = project_binding.objective_revision_ref.id
10. Return one immutable BootContext carrying the verified Project Binding, Objective
    Revision, Authority Rule, reconstructed current State, and Human Authority reference.
```

A fresh `FileStateStore` instance and a fresh Python process reach the identical route and
the identical result (§7 below). No fake Observation, Evidence, Difference, Change, Closure,
or Reflow record is ever created to simulate this route.

## 6. Required negative and interruption proofs

At minimum, `boot_project` fails closed, with zero Store mutation
(`STATE_TRANSITION_COUNT_DELTA=0`, `LINEAGE_APPEND_COUNT_DELTA=0`, `RECORD_COUNT_DELTA=0`,
`TRANSACTION_MANIFEST_COUNT_DELTA=0`, `EXTERNAL_OPERATION_COUNT_DELTA=0`), for:

```text
- missing project (unresolvable project_binding/project_binding_id under project_id)
- missing Product Binding
- wrong-kind Binding reference (objective_revision_ref/authority_policy_ref/
  human_authority_ref)
- project-id/path/URL/directory-name substitution
- a valid Binding belonging to another project
- caller-supplied project_binding_id differing from the resolved record's own declared id
- Binding body whose content no longer reproduces its declared identity
- unresolved Objective Revision
- unresolved Authority Rule
- wrong-kind Objective/Authority reference
- same-kind/id-different-body Objective or Authority substitution (closed by the Store's
  own manifest-claimant tamper detection on every resolve_record call)
- reconstructed State project mismatch
- reconstructed State Objective Revision mismatch
- four-way Human Authority mismatch
- Authority Rule identity or project mismatch
- missing, malformed, or substituted genesis receipt/reference (closed by
  FileStateStore.load_current's own genesis-institution verification)
- transaction-manifest or lineage tamper (closed by FileStateStore's own reconstruction)
- materialized-current divergence the Store classifies as corruption
- an interrupted/uncommitted transaction (a project with only an interrupted genesis has no
  committed events at all; load_current/reconstruct raise CorruptStoreError, never silently
  boot from nothing, and Boot never calls recover() to complete it)
- an uninitialized Store
- a caller-supplied State/Binding body attempting to bypass Store resolution (structurally
  impossible: boot_project's own signature accepts no such parameter)
- Development Binding substituted for Product Binding (resolve_record is called with the
  fixed record kind "project_binding"; a Development Binding record under a different kind
  never resolves under that pair)
- Phase 8 fixture object substituted for a production Binding (fails identity
  reverification unless it is independently self-consistent, in which case it is a real
  Binding, not a substitution)
- any Boot path attempting Store initialization, recovery completion, State commit, command
  execution, filesystem discovery, GitHub access, or Agent startup (proven by a static
  AST/import scan over `boot/route.py`)
```

## 7. Explicit non-claims

```text
PROJECT_DISCOVERY_IMPLEMENTED=false
FILESYSTEM_SCAN_IMPLEMENTED=false
SYMLINK_RUNTIME_CONTAINMENT_PROVEN=false
STORE_PATH_INFERRED_FROM_CWD=false
STORE_RECOVERY_AUTO_EXECUTED=false
CLI_IMPLEMENTED=false
COMMAND_EXECUTION_IMPLEMENTED=false
GITHUB_ADAPTER_IMPLEMENTED=false
EXTERNAL_OPERATION_EXECUTED=false
RUNTIME_OBSERVATION_IMPLEMENTED=false
TEMPORARY_AGENT_IMPLEMENTED=false
INDEPENDENT_VERIFICATION_IMPLEMENTED=false
AUTONOMOUS_CHANGE_IMPLEMENTED=false
MULTI_AGENT_IMPLEMENTED=false
```
