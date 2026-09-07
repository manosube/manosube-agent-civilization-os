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
PUBLIC_PRODUCT_BINDING_ENTRY_POINT_COUNT=2
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
├── __init__.py                    public exports
├── errors.py                      BindingError / BindingValidationError / BindingIdentityError
├── identity.py                    project_binding_id, verify_project_binding_identity,
│                                   human_grant_declaration_id,
│                                   human_grant_declaration_signing_payload (P13-R5-R1),
│                                   verify_human_grant_declaration_identity (P13-R5)
├── signature.py                   verify_ed25519_signature, verify_declaration_signature
│                                   (Phase 13, Issue #51, P13-R5-R1) -- read-only Ed25519
│                                   signature verification only; never generates a signature,
│                                   the Human's own private key never touches this module
├── validation.py                  schema-registry validation (the same registry every
                                    domain reads)
├── reference_classification.py    typed reference-edge classification over every accepted
                                    record kind (Round 1 P9-R1-F5, extended Round 2
                                    P9-R2-F2/F3)
├── admission.py                   admit_genesis_transaction -- the one shared pre-commit
                                    admission (closed additional-record kind allowlist,
                                    duplicate detection, whole-graph secret scan, reference
                                    closure scoped to the candidate manifest only; Round 2
                                    P9-R2-F1/F2/F3/F5, extended Round 3 P9-R3-F1/F3/F5)
├── engine.py                      assemble_project_binding, assemble_human_grant_declaration
│                                   (Phase 13, Issue #51, P13-R5; signature-verifying,
│                                   P13-R5-R1) -- the validation+identity engines
└── route.py                       bind_project -- the one public genesis entry point;
                                    declare_human_grant (P13-R5) -- a second, post-genesis
                                    public entry point, never a second genesis route --
                                    delegates its own actual persistence call to the one
                                    shared, package-wide atomic State-transition commit
                                    primitive (P13-R5-R1, see below), never a direct
                                    store.commit of its own
```

No second State, Store, Lineage, Recovery, Objective, Boundary, or Authority owner is
created anywhere in this package. Genesis State is produced by the existing State owner
(`manosube_agent_civilization.state.fingerprint.fingerprint_project_state`); atomic
adoption reuses the existing, generic `FileStateStore.initialize`. Replay comparison reads
the Store's own manifest membership through its public
`resolve_transaction_manifest(project_id, transaction_id)` method (Round 2 P9-R2-F4) --

`declare_human_grant`'s own post-genesis commit (Phase 13, Issue #51, P13-R5) does not call
`FileStateStore.commit` directly -- Structural Review Round 5-R1 (P13-R5-R1) extracted the one
shared, domain-agnostic atomic State-transition commit primitive,
`manosube_agent_civilization.store.commit.commit_state_transition`, the single place in this
repository's whole installed package that ever calls `.commit(...)`. `reflow.commit.
commit_reflow` and `binding.route.declare_human_grant` each build their own domain-specific
`next_state`/`transition`/`records` and delegate only the actual persistence call to this one
function -- `topology.py`'s `_SANCTIONED_COMMIT_CALL_MODULES` (K-003/R-001) names this one
module as the sole sanctioned caller.
Binding never reads the Store's private on-disk layout.

## 5. Canonical successful route

```text
1. Human declares a Project Binding (Objective Revision body, Authority Rule body,
   Boundary, Source Registrations, Command Policy, secret-exclusion policy)
2. bind_project validates every embedded structure and cross-field constraint, including
   Authority Rule identity reverification and the four-way Human Authority cross-match
   (Round 1 P9-R1-F1/F2, extended to four-way Round 3 P9-R3-F4)
3. bind_project mints and reverifies the content-addressed project_binding_id
4. bind_project computes genesis State's own semantic_fingerprint via the real State owner
5. admit_genesis_transaction refuses any additional_genesis_records member whose kind is
   outside a closed allowlist, rejects any duplicate (kind, id) member (identical or
   conflicting), scans the WHOLE candidate genesis manifest for secret material, and closes
   every typed reference edge it declares -- Objective Revision, Authority Rule, Project
   Binding, genesis State, and every additional_genesis_records member -- strictly against
   this genesis transaction's own candidate manifest, never a pre-existing Store record
   (Round 2 P9-R2-F1/F2/F3/F5, extended Round 3 P9-R3-F1/F3/F5)
6. FileStateStore.initialize atomically adopts the Objective Revision, the Authority
   Rule, the Project Binding, and genesis State in one transaction
7. A fresh Store instance / a fresh Python process resolves the identical Binding,
   Authority Rule, and genesis State (Round 1 P9-R1-F1/F5)
8. An identical replay -- the full atomic manifest, order-independent, no duplicate member
   of any kind -- is a no-op; a conflicting replay (missing, extra, wrong-kind, differing, or
   duplicated member) is rejected before any mutation (Round 1 P9-R1-F4, corrected Round 2
   P9-R2-F4, corrected again Round 3 P9-R3-F1/F2)
```

No fake Observation, Evidence, Difference, Change, Closure, or Reflow record is ever
created to simulate this route.

## 5a. Accepted graph inventory (Phase 9 Structural Review Round 1 §9.1)

Every body the successful route accepts, persists, or references:

```text
body                    producer/authority owner     schema owner        identity owner
Project Binding         binding.engine                binding schema      binding.identity
                                                                            (content-addressed)
Objective Revision      Human Authority (declared)     objective schema    Human-declared
                                                                            (accepted verbatim)
Authority Rule          Human Authority (declared)      authority schema    authority.identity.
                                                                            rule_id
genesis State           state.fingerprint               state schema        state.fingerprint
additional genesis      their own real producers         their own schemas   their own real
records (a closed                                                           identity owners
allowlist, Round 3
P9-R3-F3 -- currently
source_snapshot only)
TX-GENESIS manifest     store.file_store (generic,      n/a (not itself     n/a -- membership
                        Binding-agnostic)                schema-validated)   only, per-member
                                                                             identity is each
                                                                             member's own
external Human          none (external constitutional  n/a                  n/a -- cross-
Authority reference     identity, never Store-owned)                        checked for
                                                                             equality only
```

```text
persistence owner: manosube_agent_civilization.store.file_store.FileStateStore (the one
                    Store this repository has; the one generic, Binding-agnostic method
                    added this round -- resolve_transaction_manifest -- carries no
                    domain-specific persistence or comparison logic)
secret scan / additional-record kind allowlist / duplicate detection / reference
                    classification / closure owner (Round 2 P9-R2-F1/F2/F3/F5, extended
                    Round 3 P9-R3-F1/F3/F5): manosube_agent_civilization.binding.admission
                    (admit_genesis_transaction) and .reference_classification -- covering
                    every accepted body above, never just Project Binding, never the Store;
                    reference closure scoped strictly to this genesis transaction's own
                    candidate manifest, never a pre-existing Store record
replay comparison owner: manosube_agent_civilization.binding.route (bind_project), reading
                    Store membership through the public resolve_transaction_manifest API
                    (Round 3 P9-R3-F2: this method, and resolve_transaction, now agree that a
                    never-initialized project is unresolvable, never indistinguishable from
                    a genuinely committed bare genesis)
                    (Round 2 P9-R2-F4)
```

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
