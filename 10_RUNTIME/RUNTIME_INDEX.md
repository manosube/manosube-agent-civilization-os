# Bounded Runtime Observation Index (Phase 15, Issue #64)

```text
DOC_TYPE=RUNTIME_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=RUNTIME-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_RUNTIME_ADAPTER
CANONICAL_KERNEL_COUNT=1
RUNTIME_OWNER_COUNT=1
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT=0
STRUCTURAL_REVIEW_ROUNDS_APPLIED=2
```

`TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT` was `1` after Round 1 and is `0` after
Round 2 (P15-R2-F1): shipped code mints no `TrustedRuntimeRoot` at all. See section 4.2 here and
`RUNTIME_CONTRACT.md` section 11.1, including that correction's own explicit scope caveat.

---

## 0. What this document is

This is the one entry point for the **Bounded Runtime Observation and Trusted Runtime
Provisioning** contract set -- the two documents under `10_RUNTIME/` that define how an
explicit, already-declared runtime target is observed as bounded, identity-preserving Runtime
Evidence through the existing Store, Boot, and Evidence owners, and how Phase 14's own
deferred trusted runtime bootstrap is provisioned from canonical Store/Boot state.

```text
1. RUNTIME_INDEX.md      (this document)
2. RUNTIME_CONTRACT.md   the three public routes, their frozen semantics, their negative
                          controls, (section 10) the Structural Review Round 1 corrections,
                          P15-R1-F1 .. P15-R1-F6, and (section 11) the Structural Review
                          Round 2 corrections, P15-R2-F1/F2, which reopened and supersede
                          Round 1's own F4 and F6
```

Read `RUNTIME_CONTRACT.md` for the load-bearing design; this document only fixes this layer's
own position relative to the rest of the Kernel and to Boot, Store, Evidence, and Projection.

## 1. This is not a ninth Kernel element

`00_KERNEL/KERNEL_INDEX.md` §4 fixes exactly eight Kernel elements (Objective through Reflow).
Bounded Runtime Observation is not a ninth -- the identical `KERNEL_ELEMENT=none`-style
convention Boot, the CLI, the Temporary Agent lifecycle, Independent Verification, and
Projection already use (here spelled `NONE_RUNTIME_ADAPTER`, since it is specifically a
bounded, replaceable transport/probe boundary over an explicit external target, never a
persisted or authoritative owner of any canonical fact). It does not appear in `00_KERNEL/`'s
own numbered reading order, and it redefines no Kernel Contract's own semantics.

```text
KERNEL_ELEMENT=NONE_RUNTIME_ADAPTER
CANONICAL_KERNEL_COUNT=1
RUNTIME_ADAPTER_IS_KERNEL_ELEMENT=false
```

## 2. This is not a second State, Difference, Authority, Evidence, Store, or Closure owner

`observe_runtime_target` never mints canonical Difference/Change/Evidence content, never
evaluates a Closure Policy, never emits a Difference Lifecycle Event or a Closure Evaluation,
and mutates the Store exactly once per call, through the existing Store's own single sanctioned
committer (`store.commit.commit_state_transition` -- the identical primitive Reflow, Binding,
and Projection already share), and only to persist a genuinely new Runtime Observation
Envelope. It calls the existing Boot owner's own `boot_project` exactly once to independently
re-verify the real Project/Human Authority (the identical pattern Independent Verification's
own Structural Review Round 1, P13-R1-F2, and Projection's own Structural Review Round 1,
P14-R1-F1, already established) -- but, unlike Projection, evaluates no Authority Decision of
its own: Runtime Observation is bounded entirely by its own explicit, closed Observation
Boundary, never by a write-permission grant (`10_RUNTIME/RUNTIME_CONTRACT.md` §6, item 1 --
this Phase's own disclosed judgment call). It calls its one explicit `RuntimeAdapter` exactly
once per observation. `route_runtime_observation_to_evidence` calls the existing Evidence
owner's own public `derive_evidence` exactly once, over a caller-supplied, already-real,
Change-free request grounded in the existing Change-Free Verification Evidence position --
never a second Evidence owner. `bootstrap_projection_execution_capability` mints no Authority
of its own either -- it only resolves and independently reverifies grants/declarations a Human
Authority already issued and a Store already committed, then constructs Phase 14's own shipped
`ProjectionExecutionCapability`, never a second execution interface.

```text
RUNTIME_IS_A_SECOND_STATE_OWNER=false
RUNTIME_IS_A_SECOND_DIFFERENCE_OWNER=false
RUNTIME_IS_A_SECOND_AUTHORITY_OWNER=false
RUNTIME_IS_A_SECOND_EVIDENCE_OWNER=false
RUNTIME_IS_A_SECOND_STORE_OWNER=false
RUNTIME_IS_A_SECOND_CLOSURE_OWNER=false
RUNTIME_TARGET_STATE_IS_CANONICAL=false
RUNTIME_TARGET_IS_OBSERVATION_SURFACE_ONLY=true
RUNTIME_OBSERVATION_RESULT_IS_EVIDENCE=false
RUNTIME_OBSERVATION_RESULT_IS_AUTHORITY_DECISION=false
RUNTIME_OBSERVATION_RESULT_IS_CLOSURE_RECEIPT=false
BOOTSTRAP_MINTS_A_SECOND_EXECUTION_INTERFACE=false
```

## 3. This is not a general command executor, orchestrator, or cloud owner

No product, transport, or cloud provider identity is selected by this Phase. A
`RuntimeAdapter` is always supplied by the caller; `observe_runtime_target` never executes a
remote command, never supervises a process, never deploys or schedules anything, never stores
a credential of its own, and never selects, defaults, infers, or falls back to an adapter
implementation of its own. This Phase requires no VPS or cloud provider -- its own real,
disposable vertical proof (V3) uses one local HTTP target the test itself starts and stops.

```text
GENERAL_COMMAND_EXECUTOR_IMPLEMENTED=false
ORCHESTRATOR_OR_SCHEDULER_IMPLEMENTED=false
DEPLOYMENT_MANAGER_IMPLEMENTED=false
SECRET_STORE_IMPLEMENTED=false
PROCESS_SUPERVISOR_IMPLEMENTED=false
CLOUD_PROVIDER_OWNER_IMPLEMENTED=false
VPS_OR_CLOUD_PROVIDER_REQUIRED=false
FIXED_RUNTIME_ADAPTER_IMPLEMENTED=false
```

## 4. Canonical owner

```text
src/manosube_agent_civilization/runtime/
├── __init__.py           public exports
├── errors.py              RuntimeObservationError / RuntimeRequirementError /
│                           RuntimeEnvelopeIntegrityError / RuntimeAdapterError
├── types.py               vocab frozensets, RuntimeAdapter Protocol,
│                           RuntimeObservationReceipt -- immutable, non-persisted value types
├── identity.py             runtime_target_fingerprint / runtime_observation_boundary_
│                           fingerprint / runtime_observation_request_identity /
│                           runtime_observed_content_fingerprint /
│                           runtime_observation_envelope_id /
│                           runtime_observation_envelope_semantic_fingerprint
├── engine.py               derive_runtime_observation_envelope -- pure, no Store/Boot/
│                           Adapter I/O
├── network.py              require_endpoint_within_network_scope -- pure, I/O-free
│                           network-scope enforcement (Round 1, P15-R1-F1)
├── adapter.py              FakeRuntimeAdapter (controlled, in-memory) and
│                           LocalHttpRuntimeAdapter (stdlib urllib only, no redirect ever
│                           followed) -- the two RuntimeAdapter implementations
├── deployment_declaration.py
│                           verify_runtime_deployment_declaration_signature -- verification
│                           only, composing binding.signature's own shared Ed25519 primitive
│                           (Round 2, P15-R2-F2)
├── route.py                observe_runtime_target -- the one public Runtime Observation
│                           route
├── evidence_handoff.py     route_runtime_observation_to_evidence -- the one public
│                           Runtime-Observation-to-Evidence hand-off
└── bootstrap.py            TrustedRuntimeRoot (a type shipped code never mints -- Round 2,
                             P15-R2-F1) and bootstrap_projection_execution_capability -- the
                             V5 trusted runtime bootstrap provisioning Phase 14's
                             ProjectionExecutionCapability

01_SCHEMA/runtime/
├── runtime_observation_envelope.schema.json     the committed observation fact
└── runtime_deployment_declaration.schema.json   the canonical, Human-Authority-declared
                                                  deployment identity (Round 1, P15-R1-F6);
                                                  required status and required Ed25519
                                                  signature added by Round 2, P15-R2-F2
```

No second Boot, Store, Binding, Evidence, Difference, Authority, or Reflow owner is created
anywhere in this package. `reflow` and `independent_verification` are never imported by any
module in this package. `authority` is importable only from `bootstrap.py` (V5's own
provisioning concern) -- `route.py` never imports it at all. `evidence` is importable only
from `evidence_handoff.py` (the one `derive_evidence` call) and, narrowly, `bootstrap.py`
(read-only `evidence.identity.evidence_semantic_fingerprint`). `binding.identity` is importable
only from `bootstrap.py`, and `binding.signature` only from `deployment_declaration.py` (Round 2,
P15-R2-F2) -- and `binding/` itself imports nothing from this package, in either direction.
`boot` is importable from `route.py` and `bootstrap.py`, each calling `boot_project` exactly
once.
`manosube_agent_civilization.projection` is importable only from `bootstrap.py`. A network/
transport surface that actually opens anything (`urllib.request`/`urllib.error`) is importable
only from `adapter.py`; `network.py` may additionally import exactly `urllib.parse`, a
parse-only surface, and is statically proved to open, resolve, and read nothing (Round 1,
P15-R1-F1). `route.py` itself imports no `urllib` of any kind. Static conformance proves all
of this by AST walk, `tests/contract/runtime/test_runtime_static_conformance.py`.

## 4.1 Structural Review Round 1 (P15-R1-F1 .. P15-R1-F6)

> **Item 1 below is superseded by section 4.2 (P15-R2-F1)**: the fourth public callable it
> describes, `provision_trusted_runtime_root`, no longer exists. Item 2's record kind is extended
> by section 4.2 (P15-R2-F2).

Round 1 of PR #65 found six ways this layer's own first delivery claimed more than its code
kept. `10_RUNTIME/RUNTIME_CONTRACT.md` section 10 records each in full -- what was claimed,
what was true, and what the code now does. This document records only what the round changed
about *this layer's position*, which is two things:

1. **A fourth public callable exists, and it is not a fourth route.**
   `provision_trusted_runtime_root` (P15-R1-F4) is the single, explicit boundary at which a
   deployment fixes which Store/Project/Binding its trusted provisioning operates within. It
   resolves nothing, Boots nothing, and commits nothing; it exists so that
   `bootstrap_projection_execution_capability` no longer carries a `store`/`project_id`/
   `project_binding_id` parameter surface through which a caller could name an alternate,
   internally self-consistent Authority world. `PUBLIC_RUNTIME_ENTRY_POINT_COUNT` is therefore
   still `3` -- the three *routes* are unchanged -- alongside a new, separately declared
   `TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT=1`. This two-step provisioning
   discipline is a new disclosed judgment call (`RUNTIME_CONTRACT.md` section 6, item 6).

2. **A second Store-committed record kind exists.** `runtime_deployment_declaration`
   (P15-R1-F6) is the canonical, content-addressed, Human-Authority-declared record a target's
   own claimed `deployment_fingerprint` must now match. Before it, both sides of the
   deployed-identity comparison were caller/endpoint-controlled, so the check proved only that
   the endpoint echoed the expected string. It introduces no secret, no HMAC, and no signing
   key of its own (`RUNTIME_CREDENTIAL_USE_AUTHORITY=false` is unchanged) -- it is a canonical
   record resolved through the existing Store, exactly like every other canonical fact here,
   and this layer remains the owner of no Authority, State, Evidence, or Closure semantics.

   It is deliberately **not** added to `reflow/reference_registry.py`'s
   `STORE_OWNED_REFERENCE_KINDS`, for the identical reason `runtime_observation_envelope`,
   `projection_envelope`, and `github_projection_grant` are not: that registry enumerates the
   reference edges the *Reflow* vertical's own admission path persists and resolves, and this
   kind has no Reflow-Store-owned producer (`RUNTIME_CONTRACT.md` section 10.7).

```text
STRUCTURAL_REVIEW_ROUNDS_APPLIED=1
RUNTIME_IS_A_SECOND_AUTHORITY_OWNER=false
RUNTIME_IS_A_SECOND_STATE_OWNER=false
NEW_RUNTIME_STORE_COMMITTED_RECORD_KINDS=1
NEW_KERNEL_ELEMENT=false
```

## 4.2 Structural Review Round 2 (P15-R2-F1, P15-R2-F2)

Round 2 of PR #65 confirmed four of Round 1's own six corrections closed cleanly (P15-R1-F1/F2/
F3/F5) and reopened two. `10_RUNTIME/RUNTIME_CONTRACT.md` section 11 records both in full. This
document records only what the round changed about *this layer's position*, which is three
things:

1. **The fourth public callable section 4.1 introduced no longer exists.**
   `provision_trusted_runtime_root` (P15-R1-F4) accepted exactly the caller-controlled
   Store/Project/Binding tuple that correction existed to stop an untrusted surface from
   selecting; its module-private sentinel protected only the `TrustedRuntimeRoot` constructor,
   while the factory itself supplied that sentinel for whatever Store a caller passed. Moving the
   same three arguments one call earlier changed API shape, not control of the trust decision, so
   Round 2 deletes it (P15-R2-F1). `PUBLIC_RUNTIME_ENTRY_POINT_COUNT` is still `3` — the three
   *routes* are unchanged — and `TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT` is now
   `0`. The `TrustedRuntimeRoot` *type* is retained: it is unforgeable by shape, holds no verdict
   that could go stale, and is the shape a future, separately authorized Phase's real deployment
   composition boundary will mint. Until then the only issuer anywhere is a test-confined one.

   **Scope, stated exactly:** this establishes that *no shipped minting path exists at all in
   this Phase*, not that a live path resists an attacker at runtime — there is no live
   deployment/CLI/agent-runtime composition boundary wired to Runtime yet for an attacker to
   attack (`RUNTIME_CONTRACT.md` section 11.1).

2. **The second Store-committed record kind became a signed Human Authority statement.**
   `runtime_deployment_declaration` (P15-R1-F6) gains a required `status`
   (`ACTIVE`/`REVOKED`) and a required Ed25519 `signature` over its own adopted semantic fields,
   in the identical `$def` shape `binding/github_projection_grant_declaration.schema.json`
   already uses; and `observe_runtime_target` now additionally requires the resolved declaration
   to be `ACTIVE`, to name the exact Human Authority that call's own Boot restored, and to carry
   that Authority's genuine signature verified against the exact `human_authority_signing_key`
   the same Boot restored from the current Project Binding (P15-R2-F2). This adopts, explicitly,
   the operational decision section 10.6 had declined to assume: **a legitimate Human Authority
   re-binding invalidates previously issued deployment declarations for new observations.**

   The record count is unchanged (`NEW_RUNTIME_STORE_COMMITTED_RECORD_KINDS=1` for this Phase as
   a whole; Round 2 adds fields to an existing schema, never a new schema file, so the canonical
   schema total stays at `58`), and this layer remains the owner of no Authority, State,
   Evidence, or Closure semantics. `RUNTIME_CREDENTIAL_USE_AUTHORITY` remains `false`: this
   package holds no private key, mints no signature, and reaches no key server — it only
   *verifies* against the public key a real, Boot-restored Project Binding already carries.

3. **One new module, and one new admitted import edge.** `runtime/deployment_declaration.py`
   owns that verification and is the only module in this package permitted to import
   `binding.signature`, whose shared Ed25519 primitive it *composes* rather than reimplements.
   The dependency direction is unchanged and load-bearing: **`binding/` imports nothing from
   `runtime/`** — Runtime is an adapter layer that depends on the Kernel's Binding element, never
   the reverse.

```text
STRUCTURAL_REVIEW_ROUNDS_APPLIED=2
TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT=0
SHIPPED_TRUSTED_RUNTIME_ROOT_MINTING_PATH_EXISTS=false
LIVE_PATH_ADVERSARIAL_RESISTANCE_PROVEN=false
DEPLOYMENT_DECLARATION_HUMAN_AUTHORITY_SIGNED=true
DEPLOYMENT_DECLARATION_SURVIVES_A_HUMAN_AUTHORITY_REBINDING=false
BINDING_IMPORTS_RUNTIME=false
RUNTIME_HOLDS_A_PRIVATE_SIGNING_KEY=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
NEW_RUNTIME_STORE_COMMITTED_RECORD_KINDS=1
CANONICAL_SCHEMA_COUNT_CHANGED=false
NEW_KERNEL_ELEMENT=false
```

## 5. Explicit non-claims

```text
RUNTIME_OBSERVATION_ENVELOPE_IMPLEMENTED=true
RUNTIME_DEPLOYMENT_DECLARATION_IMPLEMENTED=true
RUNTIME_ADAPTER_BOUNDARY_IMPLEMENTED=true
LOCAL_HTTP_RUNTIME_ADAPTER_IMPLEMENTED=true
LOCAL_HTTP_RUNTIME_ADAPTER_EXECUTED_AGAINST_A_REAL_LOCAL_TARGET=true
VPS_OR_CLOUD_PROVIDER_REQUIRED=false
TRUSTED_RUNTIME_BOOTSTRAP_IMPLEMENTED=true
PROJECTION_EXECUTION_CAPABILITY_PROVISIONED_FROM_CANONICAL_STORE_BOOT_STATE=true
NEW_STATE_OWNER=false
NEW_EVIDENCE_OWNER=false
NEW_AUTHORITY_OWNER=false
NEW_STORE_OWNER=false
TRANSPORT_LEVEL_OUTCOME_VOCABULARY_CLOSED=true
ROUTE_LEVEL_NEGATIVE_AND_IDENTITY_MISMATCH_NEVER_ADAPTER_REPORTED=true
REDACTION_APPLIED_BEFORE_ANY_FINGERPRINT_OR_PERSISTENCE=true
TIME_WINDOW_ENFORCED_BEFORE_ANY_ADAPTER_CALL=true
OBSERVATION_BOUNDARY_CLOSED=true
NETWORK_SCOPE_ENFORCED_BEFORE_ANY_CONNECTION=true
REDIRECT_EVER_FOLLOWED=false
DEPLOYMENT_IDENTITY_STORE_ANCHORED=true
DEPLOYMENT_DECLARATION_HUMAN_AUTHORITY_SIGNED=true
DEPLOYMENT_DECLARATION_STATUS_ENFORCED=true
DEPLOYMENT_DECLARATION_BOUND_TO_BOOT_RESTORED_AUTHORITY=true
TRUSTED_RUNTIME_ROOT_REQUIRED_FOR_PROVISIONING=true
SHIPPED_TRUSTED_RUNTIME_ROOT_MINTING_PATH_EXISTS=false
AUTHORITY_FRESHNESS_RECHECKED_AT_ADAPTER_AND_COMMIT_BOUNDARIES=true
STRUCTURAL_REVIEW_ROUND_1_CORRECTIONS_APPLIED=true
STRUCTURAL_REVIEW_ROUND_2_CORRECTIONS_APPLIED=true
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
```

`PHASE_15_COMPLETE` and `PHASE_16_ALLOWED` remain `false`: this delivery closes Issue #64's own
structural findings (Structural Difference `P15-D001-BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_
PROVISIONING`), not Phase 15 itself, which still awaits a separate SHUKOU decision -- the
identical discipline every prior Phase's own first-delivery contract already states.
