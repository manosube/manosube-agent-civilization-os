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
RUNTIME_DEPLOYMENT_DECLARATION_COMMIT_ENTRY_POINT_COUNT=1
RUNTIME_ROOT_ADMISSION_COMMIT_ENTRY_POINT_COUNT=1
TRUSTED_DEPLOYMENT_COMPOSITION_ENTRY_POINT_COUNT=1
STRUCTURAL_REVIEW_ROUNDS_APPLIED=5
```

`TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT` was `1` after Round 1 and is `0` from
Round 2 (P15-R2-F1) onward: shipped code mints no `TrustedRuntimeRoot`, and no later round
reintroduces a minting function. Round 3 (P15-R3-F1) made the *type* inert — possessing one
granted nothing — and gated provisioning on a canonical `runtime_root_admission` record verified
against an externally supplied trust anchor. **Round 4 (P15-R4-F1) removes that type entirely**
and replaces the whole framing with an ownership boundary: a single
`TRUSTED_DEPLOYMENT_COMPOSITION_ENTRY_POINT_COUNT=1` composition step owns the Store, project,
Binding, admission selection and anchor, and the request-facing bootstrap has **no parameter** for
any of them. **Round 5 (P15-R5-F1)** removes the opaque `RuntimeDeploymentAuthority` value type
Round 4 carried that boundary on — it was a public dataclass with a public constructor, so any
importer could build one over an alternate world — and makes composition *return the
request-facing operation itself*, a closure with no public constructor. **Round 6 (P15-R6-F1)**
leaves that boundary untouched and closes the per-call half instead: the admission recheck Round 5
introduced ran once, at the start of the request, and only ever read fields the resolved record
declared about itself — so it now runs **twice**, the second time immediately before issuance from
its own fresh Boot, and both times it recomputes the resolved body's identity and semantic
fingerprint from that body and compares them against a commitment captured at composition.
**Round 7 (P15-R7-F1)** leaves both barriers and their placement untouched and widens only what
each one proves: those recomputations are hashes of a *projection* that deliberately excludes the
record's own declared id, its own declared semantic fingerprint and its whole `signature` block, so
composition additionally commits to the **exact full record** — through this repository's one
canonical serialization owner — and each barrier additionally requires declared == recomputed ==
bound for the id and the fingerprint, and the full-record commitment to match. See sections 4.2,
4.3, 4.4, 4.5, 4.6 and 4.7 here, and `RUNTIME_CONTRACT.md` sections 11.1, 12.1, 13.1, 14.1, 15.1
and 16.1.

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
                          P15-R1-F1 .. P15-R1-F6, (section 11) the Structural Review
                          Round 2 corrections, P15-R2-F1/F2, which reopened and supersede
                          Round 1's own F4 and F6, (section 12) the Structural Review
                          Round 3 corrections, P15-R3-F1/F2, which reopened and supersede
                          both of Round 2's, and (section 13) the Structural Review Round 4
                          corrections, P15-R4-F1/F2, which reopened and supersede both of
                          Round 3's
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
├── root_admission.py       verify_runtime_root_admission_signature -- the identical
│                           composition against a DEPLOYMENT-supplied trust anchor public key
│                           rather than any Store-resolved signing key (Round 3, P15-R3-F1)
├── deployment_registry.py  commit_runtime_deployment_declaration /
│                           current_deployment_declaration_id -- the canonical
│                           current-declaration pointer and the one atomic
│                           commit-and-supersede transition (Round 3, P15-R3-F2)
├── route.py                observe_runtime_target -- the one public Runtime Observation
│                           route
├── evidence_handoff.py     route_runtime_observation_to_evidence -- the one public
│                           Runtime-Observation-to-Evidence hand-off
└── bootstrap.py            TrustedRuntimeRoot (an ordinary public value that grants nothing
                             by itself -- Round 3, P15-R3-F1; shipped code still constructs
                             none) and bootstrap_projection_execution_capability -- the V5
                             trusted runtime bootstrap, gated on an externally anchored
                             runtime_root_admission on every call

01_SCHEMA/runtime/
├── runtime_observation_envelope.schema.json     the committed observation fact
├── runtime_deployment_declaration.schema.json   the canonical, Human-Authority-declared
│                                                 deployment identity (Round 1, P15-R1-F6);
│                                                 required status and required Ed25519
│                                                 signature added by Round 2, P15-R2-F2;
│                                                 required valid_from/valid_until added by
│                                                 Round 3, P15-R3-F2
└── runtime_root_admission.schema.json           the canonical, trust-anchor-signed record
                                                  admitting exactly one project and one
                                                  Project Binding (Round 3, P15-R3-F1)
```

No second Boot, Store, Binding, Evidence, Difference, Authority, or Reflow owner is created
anywhere in this package. `reflow` and `independent_verification` are never imported by any
module in this package. `authority` is importable only from `bootstrap.py` (V5's own
provisioning concern) -- `route.py` never imports it at all. `evidence` is importable only
from `evidence_handoff.py` (the one `derive_evidence` call) and, narrowly, `bootstrap.py`
(read-only `evidence.identity.evidence_semantic_fingerprint`). `binding.identity` is importable
only from `bootstrap.py`, and `binding.signature` only from `deployment_declaration.py` (Round 2,
P15-R2-F2) and `root_admission.py` (Round 3, P15-R3-F1) -- and `binding/` itself imports nothing
from this package, in either direction. `commit_state_transition` is called from exactly two
modules, each exactly once: `route.py` and -- since Round 4 (P15-R4-F1/F2) -- `transition_chain.py`,
the one shared monotonic-chain mechanism both the declaration and root-admission chains
parameterize. Round 3 had admitted `deployment_registry.py` for that second site; Round 4 moved it
into the shared mechanism, so adding a *second* chain kind added no third call site.
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

> **Item 1 below is superseded by section 4.3 (P15-R3-F1)**: the conclusion that provisioning had
> to wait for a later Phase is rejected, and `TrustedRuntimeRoot` is publicly constructible again
> — because the type now grants nothing, not because the deleted factory returned. Item 2's
> record kind is extended by section 4.3 (P15-R3-F2), and its "the canonical schema total stays at
> `58`" statement is true of Round 2 only; Round 3 adds one file, making `59`.

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
   schema total stayed at `58` through *this* round — Round 3 adds one new file, making `59`, and
   takes this Phase's own new record-kind count to `2`), and this layer remains the owner of no Authority, State,
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

## 4.3 Structural Review Round 3 (P15-R3-F1, P15-R3-F2)

Round 3 of PR #65 confirmed Round 1's F1/F2/F3/F5 closed and Round 2's F2 signature-and-Boot-
binding half closed, and reopened both of Round 2's corrections.
`10_RUNTIME/RUNTIME_CONTRACT.md` section 12 records both in full. This document records only what
the round changed about *this layer's position*, which is four things:

1. **A trust root stopped being a capability, so shipped provisioning became legitimate.**
   Round 2 concluded that, since no shipped code could mint a `TrustedRuntimeRoot`, real issuance
   had to wait for a later Phase. Round 3 rejected that: Issue #64 assigns this production
   provisioning boundary to *this* Phase, and Round 2's module-private sentinel was in any case a
   naming convention rather than a control (any in-process caller able to import the shipped
   module could read it and construct a root over an arbitrary Store — which is exactly what the
   test-only issuer did). The fix moves the boundary off the type: a new canonical record kind,
   `runtime_root_admission`, is resolved inside the root's own Store, must be ACTIVE and name
   exactly that project and Project Binding, and must carry a genuine signature verified against
   a `trust_anchor_public_key_hex` **the deployment/composition boundary supplies** — never a key
   resolvable from inside the Store being admitted. The check is folded into
   `bootstrap_projection_execution_capability` itself and runs on every call, before any grant
   resolution and before any authorization evaluation.

   **This is not a reversal of Round 2, and the diff should not be read as one.** Public
   construction of `TrustedRuntimeRoot` returns only because the type now grants nothing: all
   three of Round 2's own mechanical facts remain literally true and remain asserted unchanged
   (the deleted factory appears in no code position anywhere shipped; no shipped callable returns
   the type; no shipped module constructs one). `RUNTIME_CONTRACT.md` section 12.1.1 states the
   before/after precisely.

   **Scope, stated exactly:** what is now proved is that a *production-legitimate mechanism is
   shipped and is not reproducible by a request-path caller lacking the anchor's private key*.
   What is still **not** claimed is that any live deployment/CLI/agent-runtime entrypoint in this
   repository invokes it — none does, and Phase 16+ remains unauthorized. The difference from
   Round 2's caveat is that the remaining gap is a scheduling fact about later Phases rather than
   a defect in the mechanism.

2. **A third Store-committed record kind exists, and the canonical schema total moved.**
   `runtime_root_admission` (P15-R3-F1) is the second new schema file this Phase adds, taking the
   canonical total from `58` to `59`; `scripts/validate_schemas.py`'s asserted inventory is
   updated accordingly. Like every other record kind here it introduces no secret, no HMAC, and
   no signing key of its own — only a *public* verification key a deployment supplies at
   composition time — so `RUNTIME_CREDENTIAL_USE_AUTHORITY` remains `false` and this layer remains
   the owner of no Authority, State, Evidence, or Closure semantics. It is deliberately **not**
   added to `reflow/reference_registry.py`'s `STORE_OWNED_REFERENCE_KINDS`, for the identical
   reason section 4.1 item 2 already gives for `runtime_deployment_declaration`.

3. **This layer now writes one field of `semantic_state`, and exactly one.** `runtime_deployment_
   declaration` gains required `valid_from`/`valid_until` (both covered by the record's own
   content address *and* the Human Authority's own signature), and — because an immutable,
   content-addressed record cannot be revoked by minting a second one — "current" becomes what
   Project State's own pointer names: `semantic_state.runtime.claims[<target_key>]`, moved
   atomically with the record by the new shipped `commit_runtime_deployment_declaration`
   (P15-R3-F2). That property is already part of the adopted
   `01_SCHEMA/state/semantic_state.schema.json`, so **no State schema changes**; this layer
   merges one key into one domain's `claims` and carries every other field of that domain, and
   every other domain, through byte-identical. It is still not a second State owner: it builds a
   transition plan and hands it to the Store's own single sanctioned committer, exactly as Reflow
   and Binding already do.

4. **A fourth public callable exists, and it is not a fourth route.**
   `commit_runtime_deployment_declaration` is a canonical *committer*: it reaches no adapter,
   observes nothing, and mints no Authority. `PUBLIC_RUNTIME_ENTRY_POINT_COUNT` is still `3`,
   alongside a separately declared `RUNTIME_DEPLOYMENT_DECLARATION_COMMIT_ENTRY_POINT_COUNT=1` —
   the identical convention section 4.1 used for
   `TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT`.

```text
STRUCTURAL_REVIEW_ROUNDS_APPLIED=3
TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT=0
RUNTIME_DEPLOYMENT_DECLARATION_COMMIT_ENTRY_POINT_COUNT=1
SHIPPED_TRUSTED_RUNTIME_ROOT_MINTING_PATH_EXISTS=false
POSSESSING_A_TRUSTED_RUNTIME_ROOT_GRANTS_ADAPTER_ACCESS=false
RUNTIME_ROOT_ADMISSION_REQUIRED_FOR_PROVISIONING=true
RUNTIME_ROOT_ADMISSION_VERIFIED_AGAINST_AN_EXTERNALLY_SUPPLIED_ANCHOR=true
TRUST_ANCHOR_HARDCODED_IN_SHIPPED_SOURCE=false
PRODUCTION_LEGITIMATE_PROVISIONING_MECHANISM_SHIPPED=true
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false
DEPLOYMENT_DECLARATION_VALIDITY_WINDOW_REQUIRED=true
DEPLOYMENT_DECLARATION_REVOCATION_IS_EFFECTIVE=true
DEPLOYMENT_DECLARATION_CURRENT_POINTER_IS_STORE_RESOLVED=true
SEMANTIC_STATE_SCHEMA_CHANGED=false
RUNTIME_IS_A_SECOND_STATE_OWNER=false
NEW_RUNTIME_STORE_COMMITTED_RECORD_KINDS=2
CANONICAL_SCHEMA_COUNT_CHANGED=true
CANONICAL_SCHEMA_COUNT=59
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
NEW_KERNEL_ELEMENT=false
```

## 4.4 Structural Review Round 4 (P15-R4-F1, P15-R4-F2)

Round 4 of PR #65 confirmed every earlier round's remaining corrections closed and reopened both
of Round 3's, on the review's own explicit observation that **the same trust-boundary semantic
class has recurred across Rounds 1-4**. `10_RUNTIME/RUNTIME_CONTRACT.md` section 13 records both
findings in full. This document records only what the round changed about *this layer's position*,
which is five things:

1. **The trust decision stopped being a parameter and became an ownership boundary.** Rounds 1-3
   each moved the decision somewhere a caller could still reach: a parameter list, a public
   factory, a private sentinel, then a signed admission record verified against an anchor the
   *caller of the request-facing function supplied*. That last form still let a caller supply both
   sides of the question. Round 4 splits provisioning into a **trusted deployment composition**
   step — which owns the Store handle, `project_id`, `project_binding_id`, the root-admission
   selection and the configured anchor, and runs once before any request boundary exists — and a
   **request-facing bootstrap** that consumes only the opaque `RuntimeDeploymentAuthority` that
   step returns. Five parameters are *gone* from the request-facing signature rather than
   validated, so there is no call shape through which an alternate world can be substituted.
   `TrustedRuntimeRoot` is removed outright, and the static assertion that replaces Rounds 2 and
   3's own is strictly stronger: that name now appears in no code position anywhere shipped.

2. **A fourth Store-committed record-kind lifecycle exists, and it is the *same* lifecycle.** The
   root admission gains signed `generation`/`predecessor_ref` fields and a current-admission
   pointer, so a composition-level rotation or revocation genuinely takes effect instead of leaving
   the superseded admission usable forever. It is deliberately not a second scheme: both chains
   parameterize one shared mechanism (`runtime/transition_chain.py`), so the
   genesis/successor/rotation/revocation/terminality/Compare-And-Swap rules exist exactly once.

3. **This layer writes one more `claims` key, and still changes no State schema.** The admission
   pointer lives in the identical `semantic_state.runtime.claims` map Round 3 established, under a
   structurally distinct key namespace (`ROOT-ADMISSION:<project_binding_id>`) whose disjointness
   from declaration target keys is proved over the alphabets themselves, not by sampling. Still no
   `01_SCHEMA/state/` change of any kind, and still not a second State owner.

4. **No new schema file.** Both Runtime schemas gain required `generation`/`predecessor_ref`
   fields; the canonical total stays at `59`, verified against what is on disk rather than assumed.

5. **Two further public callables exist, and neither is a route.**
   `compose_trusted_runtime_deployment_authority` (a composition step) and
   `commit_runtime_root_admission` (a canonical committer) join
   `commit_runtime_deployment_declaration`. `PUBLIC_RUNTIME_ENTRY_POINT_COUNT` is still `3`,
   alongside separately declared counts — the identical convention sections 4.1 and 4.3 already
   used.

```text
STRUCTURAL_REVIEW_ROUNDS_APPLIED=4
TRUSTED_DEPLOYMENT_COMPOSITION_ENTRY_POINT_COUNT=1
RUNTIME_ROOT_ADMISSION_COMMIT_ENTRY_POINT_COUNT=1
REQUEST_FACING_BOOTSTRAP_PARAMETER_COUNT=3
TRUST_ANCHOR_PRESENT_ON_REQUEST_FACING_SIGNATURE=false
ROOT_ADMISSION_REF_PRESENT_ON_REQUEST_FACING_SIGNATURE=false
DEPLOYMENT_AUTHORITY_RETAINS_THE_RAW_TRUST_ANCHOR=false
TRUSTED_RUNTIME_ROOT_TYPE_EXISTS=false
ROOT_ADMISSION_IS_A_MONOTONIC_SIGNED_CHAIN=true
DEPLOYMENT_DECLARATION_IS_A_MONOTONIC_SIGNED_CHAIN=true
CHAIN_MECHANISM_MODULE_COUNT=1
CHAIN_RULE_DUPLICATED_PER_RECORD_KIND=false
CHAIN_KEY_SPACES_PROVABLY_DISJOINT=true
COMMIT_STATE_TRANSITION_CALL_SITES_IN_THIS_PACKAGE=2
CONCURRENCY_LOSER_FAILS_CLOSED=true
TARGET_EPOCH_REACTIVATION_MECHANISM_BUILT=false
AUTHORITY_COMPOSED_BEFORE_A_ROTATION_IS_RETROACTIVELY_REVOKED=false
SEMANTIC_STATE_SCHEMA_CHANGED=false
NEW_SCHEMA_FILES_ADDED=0
CANONICAL_SCHEMA_COUNT=59
RUNTIME_IS_A_SECOND_STATE_OWNER=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
NEW_KERNEL_ELEMENT=false
```

## 4.5 Structural Review Round 5 (P15-R5-F1, P15-R5-F2, P15-R5-F3)

Round 5 of PR #65 confirmed Round 4's F2 closed, **reopened Round 4's own F1**, and added one
further independent finding. `10_RUNTIME/RUNTIME_CONTRACT.md` section 14 records all three in
full. This document records only what the round changed about *this layer's position*, which is
four things:

1. **The ownership boundary stopped being carried by a value and became a closure.** Round 4 handed
   request-facing code an opaque `RuntimeDeploymentAuthority`. That type was an ordinary public
   frozen dataclass with an ordinary public constructor, and the request-facing half was a free
   module-level function guarded only by an `isinstance` check — so any caller able to import the
   module could construct their own authority over an alternate Store/Project/Binding and hand it
   straight in. The adopted correction rules out a sentinel, a private constructor, a
   leading-underscore field, an opaque `repr` and an `isinstance` check as trust controls, so the
   type is **deleted** and `compose_trusted_runtime_deployment_authority` now returns the
   request-facing operation itself, already closed over the canonical Store, Project, Binding and
   admitted admission id/generation. A closure has no public constructor, so the only way to
   obtain a working bootstrap is to pass composition's own admission gate. The request-facing
   signature is down to **two** keyword-only, operation-scoped parameters.

2. **New capability issuance now proves the bound admission is still current, on every call.**
   Round 4 disclosed that an already-composed authority behaved like a cached credential. Round 5
   narrows that without contradicting the contract's "closed over afterward" wording, by
   separating two questions: the *anchor* is still verified exactly once, at composition, and
   never appears on a request-facing signature; the *currency* of the already-admitted record is
   now proved freshly per call, from the canonical Store's own pointer plus the retained admission
   id and generation. A rotated or revoked composition authority mints no new capability, refusing
   before any grant resolution and at zero adapter, network and authorization cost. Capabilities
   already issued are deliberately **not** retroactively revoked — the adopted boundary is
   prevention of new issuance, and that limit is proved as its own control.

3. **The declaration committer's validity window is ordered as real UTC instants.** It compared
   raw timestamp strings, which is unsound over this repository's own canonical grammar (an
   optional fractional part, and `.` sorting below `Z`) — accepting an inverted window and
   refusing a genuine fractional-second one. `route.py`'s existing parser moved, unchanged, to
   `engine.parse_utc_instant`, and both sites read through it: no second timestamp grammar and no
   Runtime-specific time owner was created, and the committer still reads no clock.

4. **One public callable fewer, and still no change to the route count.**
   `bootstrap_projection_execution_capability` is no longer a module-level name at all — exactly
   one `def` anywhere shipped carries it, nested inside the composition entry point, which returns
   it. `PUBLIC_RUNTIME_ENTRY_POINT_COUNT` is still `3`: neither the removed name nor the surviving
   composition step was ever a route.

```text
STRUCTURAL_REVIEW_ROUNDS_APPLIED=5
COMPOSITION_RETURNS_A_BOUND_REQUEST_FACING_SERVICE=true
REQUEST_FACING_OPERATION_IS_A_CLOSURE=true
REQUEST_FACING_OPERATION_HAS_A_PUBLIC_CONSTRUCTOR=false
REQUEST_FACING_BOOTSTRAP_PARAMETER_COUNT=2
MODULE_LEVEL_REQUEST_FACING_BOOTSTRAP_EXISTS=false
RUNTIME_DEPLOYMENT_AUTHORITY_TYPE_EXISTS=false
RUNTIME_DEPLOYMENT_AUTHORITY_NAME_APPEARS_IN_SHIPPED_CODE=false
DEPLOYMENT_AUTHORITY_PARAMETER_PRESENT_ON_REQUEST_FACING_SIGNATURE=false
TRUST_ANCHOR_PRESENT_ON_REQUEST_FACING_SIGNATURE=false
CURRENT_ADMISSION_RECHECKED_ON_EVERY_NEW_CAPABILITY_ISSUANCE=true
CURRENCY_RECHECK_REQUIRES_A_RAW_TRUST_ANCHOR=false
ROTATION_OR_REVOCATION_BLOCKS_NEW_ISSUANCE_FROM_AN_OLD_SERVICE=true
ALREADY_ISSUED_CAPABILITIES_RETROACTIVELY_REVOKED=false
DECLARATION_VALIDITY_WINDOW_ORDERED_AS_REAL_INSTANTS=true
INSTANT_PARSING_OWNER_COUNT_IN_THIS_PACKAGE=1
SECOND_TIMESTAMP_GRAMMAR_CREATED=false
DECLARATION_COMMITTER_READS_A_CLOCK=false
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
TRUSTED_DEPLOYMENT_COMPOSITION_ENTRY_POINT_COUNT=1
CLOSED_ROUND_1_TO_4_WORK_REGRESSED=false
SEMANTIC_STATE_SCHEMA_CHANGED=false
NEW_SCHEMA_FILES_ADDED=0
CANONICAL_SCHEMA_COUNT=59
RUNTIME_IS_A_SECOND_STATE_OWNER=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
NEW_KERNEL_ELEMENT=false
```

## 4.6 Structural Review Round 6 (P15-R6-F1)

Round 6 of PR #65 confirmed Round 5's F1 and F3 closed and **reopened Round 5's own F2**.
`10_RUNTIME/RUNTIME_CONTRACT.md` section 15 records the finding in full. This document records
only what the round changed about *this layer's position*, which is three things:

1. **Composition now captures an immutable commitment to the exact admission, not just a name for
   it.** Round 5 retained the admitted record's id and generation. Round 6 additionally retains
   its **independently recomputed semantic fingerprint** — a value `_require_currently_admitted`
   had already derived from the record's own body and proved equal to its declared value, so
   nothing new is computed and no new trust is taken; it is simply kept. All three live in the
   returned closure's cells, chosen before any request boundary exists, and the raw anchor is
   still discarded and still absent from every request-facing signature.

2. **The per-call barrier runs twice, and re-establishes integrity rather than reading fields.**
   Round 5's single barrier ran at the start of the request and checked four fields the resolved
   record declares about itself — so a rotation or revocation committing *after* it, while grants
   and Authority decisions were still being evaluated, was still followed by a newly issued
   capability; and a Store-level substitution of the record body under the **current, unmoved id**
   passed the gate entirely, because the four fields it checked were exactly the ones such a
   substitution can leave untouched. The barrier now recomputes the resolved body's own identity
   and semantic fingerprint **from that body's actual content** and requires exact equality with
   the composition-captured commitment — six requirements, not four — and it runs a second time,
   from its own fresh Boot, immediately before the capability is constructed. Recomputing from the
   body, against the captured reference, is what closes the substitution gap: comparing a
   record's declared id against its own other declared fields is a self-comparison, and a
   self-consistent forgery satisfies it trivially.

3. **The issued context snapshots the final Boot's State, not the initial one.**
   `state_revision`/`semantic_fingerprint` now describe the State that was current at the moment
   of issuance. Disclosed judgment call: only the *State snapshot* moves. The Human Authority
   binding — and therefore the decisions, the pre-issued authorities and the context's own
   `github_authority_ref` — deliberately remains sourced from the first Boot, because that is
   what the Authority evaluation actually ran against; re-deriving it afterwards would let the
   context claim an authorization that never happened.

Nothing else moved. Round 5's closure boundary is unchanged, the request-facing signature is
unchanged at exactly two keyword-only operation-scoped parameters with no new public parameter of
any kind, the single instant-parsing owner is unchanged, and `admission_registry.py`,
`transition_chain.py`, `identity.py`, `engine.py`, `route.py` and `deployment_registry.py` are all
untouched: exactly one shipped file changed this round.

```text
STRUCTURAL_REVIEW_ROUNDS_APPLIED=6
ADMISSION_BARRIERS_PER_REQUEST_FACING_CALL=2
PRE_ISSUANCE_ADMISSION_BARRIER_EXISTS=true
FINAL_BARRIER_READS_ITS_OWN_FRESH_BOOT=true
ISSUED_CONTEXT_STATE_SNAPSHOT_SOURCED_FROM_FINAL_BOOT=true
ISSUED_CONTEXT_AUTHORITY_BINDING_SOURCED_FROM_INITIAL_BOOT=true
COMPOSITION_CAPTURES_AN_IMMUTABLE_ADMISSION_COMMITMENT=true
COMMITMENT_INCLUDES_SEMANTIC_FINGERPRINT=true
PER_CALL_RECHECK_REQUIREMENT_COUNT=6
PER_CALL_RECHECK_RECOMPUTES_IDENTITY_FROM_THE_RESOLVED_BODY=true
PER_CALL_RECHECK_TRUSTS_THE_RESOLVED_BODYS_OWN_DECLARED_IDENTITY=false
ROTATION_LANDING_BETWEEN_THE_TWO_BARRIERS_ISSUES_A_CAPABILITY=false
REVOCATION_LANDING_BETWEEN_THE_TWO_BARRIERS_ISSUES_A_CAPABILITY=false
CURRENT_ID_BODY_SUBSTITUTION_ISSUES_A_CAPABILITY=false
CURRENT_ID_BODY_SUBSTITUTION_REFUSED_BEFORE_AUTHORITY_EVALUATION=true
UNCHANGED_CURRENT_ADMISSION_STILL_ISSUES_A_WORKING_CAPABILITY=true
UNRELATED_STATE_CONTENTION_BLOCKS_ISSUANCE=false
REQUEST_FACING_BOOTSTRAP_PARAMETER_COUNT=2
NEW_PUBLIC_REQUEST_PARAMETER_ADDED=0
REQUEST_FACING_SIGNATURE_CHANGED_SINCE_ROUND_5=false
CURRENCY_RECHECK_REQUIRES_A_RAW_TRUST_ANCHOR=false
ALREADY_ISSUED_CAPABILITIES_RETROACTIVELY_REVOKED=false
ROUND_5_CLOSURE_BOUNDARY_CHANGED=false
ROUND_5_TIMESTAMP_OWNER_CHANGED=false
SHIPPED_FILES_CHANGED_THIS_ROUND=1
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
TRUSTED_DEPLOYMENT_COMPOSITION_ENTRY_POINT_COUNT=1
CLOSED_ROUND_1_TO_5_WORK_REGRESSED=false
SEMANTIC_STATE_SCHEMA_CHANGED=false
NEW_SCHEMA_FILES_ADDED=0
CANONICAL_SCHEMA_COUNT=59
RUNTIME_IS_A_SECOND_STATE_OWNER=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
NEW_KERNEL_ELEMENT=false
```

## 4.7 Structural Review Round 7 (P15-R7-F1)

Round 7 of PR #65 confirmed Round 6's two-barrier placement closed, confirmed Round 5's closure
boundary and the transition-chain mechanism closed, and found **one remaining gap in what each
barrier proves**. `10_RUNTIME/RUNTIME_CONTRACT.md` section 16 records the finding in full. This
document records only what the round changed about *this layer's position*, which is two things:

1. **The composition-time commitment now covers the exact full record, not only a projection of
   it.** Rounds 5 and 6 retained the admitted record's id, generation and independently recomputed
   semantic fingerprint. All three are kept unchanged, and a fourth is added beside them: a
   deterministic digest of the **exact, complete, schema-valid, anchor-verified record**. The
   reason is that the id and the semantic fingerprint are *both* hashes of
   `ROOT_ADMISSION_SEMANTIC_FIELDS`, and that projection deliberately excludes three of the
   record's own fields — its declared `runtime_root_admission_id`, its declared
   `runtime_root_admission_semantic_fingerprint` (an identity cannot be computed over itself), and
   its whole `signature` block (a signature cannot cover its own value). Those exclusions are
   load-bearing and are not changed; `identity.py` is untouched. What follows is only that
   *something else* must commit to the three excluded fields, since a hash of a projection can
   detect a change only inside that projection. That something else is one digest over the complete
   record, computed through **this repository's one canonical serialization owner**,
   `state.canonicalize.canonical_json_bytes` — the same function `identity.py` already reads for
   every one of its own derivations. A second way to turn a canonical record into bytes would be a
   second notion of *what this record is*, and the whole value of a full-record commitment is that
   there is exactly one such notion. It retains no trust anchor and reintroduces none: a record
   carries a signature, never a key.

2. **Each barrier now requires nine things, not six, and the id and fingerprint equalities are
   three-way.** Round 6 compared the *recomputed* id and fingerprint against the *bound* ones, and
   never against the resolved record's own **declared** id and fingerprint fields. So a Store-level
   substitution changing only the declared id, or only the declared fingerprint, or only
   `signature.value`/`signature.key_id` — leaving every semantic field byte-identical — passed both
   barriers: every existing check reads values such a substitution does not move, and the signature
   is not reverified per call at all, because the anchor is deliberately gone by then. Each barrier
   now additionally requires `declared == recomputed == bound` for the id, the same three-way
   equality for the semantic fingerprint, and the full-record commitment to equal the
   composition-time one. Adding the declared field to the chain does not reintroduce the
   self-comparison Round 6 rightly rejected: the *bound* value is still the anchor of the chain, so
   `declared == recomputed == bound` is strictly stronger than `recomputed == bound`, never a
   substitute for it. The three new requirements are checked **last**, on the same ordering
   rationale §15.1 already states, so each refuses for its own distinguishable reason and the
   broadest one is isolated by the only case nothing narrower can see: a body whose `signature`
   alone was replaced.

Nothing else moved. Round 6's two barriers, their placement and their fresh Boots are unchanged;
Round 5's closure boundary is unchanged; the transition-chain mechanism is unchanged; the
request-facing signature is unchanged at exactly two keyword-only operation-scoped parameters with
no new public parameter of any kind — the commitment lives in a closure cell and on the barrier's
own private signature, which is precisely where a value a caller must never be able to name
belongs. `admission_registry.py`, `transition_chain.py`, `identity.py`, `engine.py`, `route.py`,
`deployment_registry.py`, `__init__.py` and `01_SCHEMA/` are all untouched: exactly one shipped
file changed this round.

```text
STRUCTURAL_REVIEW_ROUNDS_APPLIED=7
ADMISSION_BARRIERS_PER_REQUEST_FACING_CALL=2
PRE_ISSUANCE_ADMISSION_BARRIER_EXISTS=true
FINAL_BARRIER_READS_ITS_OWN_FRESH_BOOT=true
ISSUED_CONTEXT_STATE_SNAPSHOT_SOURCED_FROM_FINAL_BOOT=true
ISSUED_CONTEXT_AUTHORITY_BINDING_SOURCED_FROM_INITIAL_BOOT=true
COMPOSITION_CAPTURES_AN_IMMUTABLE_ADMISSION_COMMITMENT=true
COMMITMENT_INCLUDES_SEMANTIC_FINGERPRINT=true
COMMITMENT_INCLUDES_THE_EXACT_FULL_RECORD=true
FULL_RECORD_COMMITMENT_COVERS_THE_DECLARED_ID=true
FULL_RECORD_COMMITMENT_COVERS_THE_DECLARED_SEMANTIC_FINGERPRINT=true
FULL_RECORD_COMMITMENT_COVERS_THE_SIGNATURE_BLOCK=true
FULL_RECORD_COMMITMENT_USES_THE_ONE_CANONICAL_SERIALIZATION_OWNER=true
SECOND_SERIALIZATION_MECHANISM_INTRODUCED=false
FULL_RECORD_COMMITMENT_RETAINS_A_RAW_TRUST_ANCHOR=false
PER_CALL_RECHECK_REQUIREMENT_COUNT=9
PER_CALL_RECHECK_REQUIRES_DECLARED_EQUALS_RECOMPUTED_EQUALS_BOUND_ID=true
PER_CALL_RECHECK_REQUIRES_DECLARED_EQUALS_RECOMPUTED_EQUALS_BOUND_FINGERPRINT=true
PER_CALL_RECHECK_TRUSTS_THE_RESOLVED_BODYS_OWN_DECLARED_IDENTITY=false
DECLARED_ID_SUBSTITUTION_ISSUES_A_CAPABILITY=false
DECLARED_SEMANTIC_FINGERPRINT_SUBSTITUTION_ISSUES_A_CAPABILITY=false
SIGNATURE_VALUE_SUBSTITUTION_ISSUES_A_CAPABILITY=false
SIGNATURE_KEY_ID_SUBSTITUTION_ISSUES_A_CAPABILITY=false
ISOLATED_SUBSTITUTIONS_REFUSED_BEFORE_AUTHORITY_EVALUATION=true
CURRENT_ID_BODY_SUBSTITUTION_ISSUES_A_CAPABILITY=false
UNCHANGED_CURRENT_ADMISSION_STILL_ISSUES_A_WORKING_CAPABILITY=true
REQUEST_FACING_BOOTSTRAP_PARAMETER_COUNT=2
NEW_PUBLIC_REQUEST_PARAMETER_ADDED=0
REQUEST_FACING_SIGNATURE_CHANGED_SINCE_ROUND_5=false
CURRENCY_RECHECK_REQUIRES_A_RAW_TRUST_ANCHOR=false
ALREADY_ISSUED_CAPABILITIES_RETROACTIVELY_REVOKED=false
ROUND_5_CLOSURE_BOUNDARY_CHANGED=false
ROUND_6_TWO_BARRIER_PLACEMENT_CHANGED=false
ROUND_5_TIMESTAMP_OWNER_CHANGED=false
SHIPPED_FILES_CHANGED_THIS_ROUND=1
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
TRUSTED_DEPLOYMENT_COMPOSITION_ENTRY_POINT_COUNT=1
CLOSED_ROUND_1_TO_6_WORK_REGRESSED=false
SEMANTIC_STATE_SCHEMA_CHANGED=false
NEW_SCHEMA_FILES_ADDED=0
CANONICAL_SCHEMA_COUNT=59
RUNTIME_IS_A_SECOND_STATE_OWNER=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
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
DEPLOYMENT_DECLARATION_VALIDITY_WINDOW_REQUIRED=true
DEPLOYMENT_DECLARATION_REVOCATION_IS_EFFECTIVE=true
RUNTIME_ROOT_ADMISSION_IMPLEMENTED=true
RUNTIME_ROOT_ADMISSION_REQUIRED_FOR_PROVISIONING=true
RUNTIME_ROOT_ADMISSION_IS_A_MONOTONIC_SIGNED_CHAIN=true
RUNTIME_ROOT_ADMISSION_ROTATION_AND_REVOCATION_ARE_EFFECTIVE=true
TRUSTED_RUNTIME_ROOT_TYPE_EXISTS=false
RUNTIME_DEPLOYMENT_AUTHORITY_TYPE_EXISTS=false
SHIPPED_TRUSTED_RUNTIME_ROOT_MINTING_PATH_EXISTS=false
TRUSTED_DEPLOYMENT_COMPOSITION_OWNS_THE_TRUST_ANCHOR=true
TRUSTED_DEPLOYMENT_COMPOSITION_RETURNS_THE_BOUND_REQUEST_FACING_SERVICE=true
REQUEST_FACING_OPERATION_IS_A_CLOSURE=true
TRUST_ANCHOR_PRESENT_ON_REQUEST_FACING_SIGNATURE=false
CURRENT_ADMISSION_RECHECKED_ON_EVERY_NEW_CAPABILITY_ISSUANCE=true
CURRENT_ADMISSION_RECHECKED_AGAIN_IMMEDIATELY_BEFORE_ISSUANCE=true
ADMISSION_RECHECK_RECOMPUTES_IDENTITY_AND_FINGERPRINT_FROM_THE_RESOLVED_BODY=true
ADMISSION_RECHECK_COMMITS_TO_THE_EXACT_FULL_ADMISSION_RECORD=true
ADMISSION_RECHECK_COVERS_THE_RECORDS_OWN_DECLARED_ID_AND_FINGERPRINT=true
ADMISSION_RECHECK_COVERS_THE_SIGNATURE_BLOCK=true
FULL_RECORD_COMMITMENT_USES_THE_ONE_CANONICAL_SERIALIZATION_OWNER=true
CURRENT_ID_RECORD_BODY_SUBSTITUTION_IS_DETECTED=true
DECLARED_ID_ONLY_SUBSTITUTION_IS_DETECTED=true
DECLARED_SEMANTIC_FINGERPRINT_ONLY_SUBSTITUTION_IS_DETECTED=true
SIGNATURE_ONLY_SUBSTITUTION_IS_DETECTED=true
ROTATION_OR_REVOCATION_BLOCKS_NEW_ISSUANCE_FROM_AN_OLD_SERVICE=true
ROTATION_OR_REVOCATION_LANDING_MID_REQUEST_BLOCKS_ISSUANCE=true
ISSUED_CONTEXT_STATE_SNAPSHOT_SOURCED_FROM_FINAL_BOOT=true
ALREADY_ISSUED_CAPABILITIES_RETROACTIVELY_REVOKED=false
DECLARATION_VALIDITY_WINDOW_ORDERED_AS_REAL_INSTANTS=true
INSTANT_PARSING_OWNER_COUNT_IN_THIS_PACKAGE=1
DEPLOYMENT_DECLARATION_IS_A_MONOTONIC_SIGNED_CHAIN=true
DECLARATION_ANCESTOR_REPLAY_IS_REFUSED=true
DECLARATION_REVOCATION_IS_TERMINAL=true
CONCURRENCY_LOSER_FAILS_CLOSED=true
TARGET_EPOCH_REACTIVATION_MECHANISM_BUILT=false
PRODUCTION_LEGITIMATE_PROVISIONING_MECHANISM_SHIPPED=true
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false
AUTHORITY_FRESHNESS_RECHECKED_AT_ADAPTER_AND_COMMIT_BOUNDARIES=true
CURRENT_DECLARATION_POINTER_RECHECKED_ON_EVERY_COMMIT_ATTEMPT=true
STRUCTURAL_REVIEW_ROUND_1_CORRECTIONS_APPLIED=true
STRUCTURAL_REVIEW_ROUND_2_CORRECTIONS_APPLIED=true
STRUCTURAL_REVIEW_ROUND_3_CORRECTIONS_APPLIED=true
STRUCTURAL_REVIEW_ROUND_4_CORRECTIONS_APPLIED=true
STRUCTURAL_REVIEW_ROUND_5_CORRECTIONS_APPLIED=true
STRUCTURAL_REVIEW_ROUND_6_CORRECTIONS_APPLIED=true
STRUCTURAL_REVIEW_ROUND_7_CORRECTIONS_APPLIED=true
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
