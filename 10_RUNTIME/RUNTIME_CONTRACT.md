# Bounded Runtime Observation and Trusted Runtime Provisioning Contract (Phase 15, Issue #64)

```text
DOC_TYPE=RUNTIME_CONTRACT
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=RUNTIME-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_RUNTIME_ADAPTER
RUNTIME_OWNER_COUNT=1
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
```

## 1. Position

This layer adds exactly one provider-neutral, explicit Runtime Adapter boundary: a
deterministic Runtime Observation Envelope binding an explicit, declared runtime target
identity to a bounded, time-windowed observation of what that target currently reports,
through a replaceable `RuntimeAdapter`, plus a trusted runtime bootstrap that provisions
Phase 14's own `ProjectionExecutionCapability` from canonical Store/Boot state. A running
deployment is observed as bounded, identity-preserving Runtime Evidence through the existing
Store, Boot, and Evidence owners, none of which this layer duplicates; a runtime target is
never a canonical source of Difference, Change, Evidence, Authority, or State -- it is an
external world this layer observes under an explicit closed boundary and hands off,
unchanged, to the existing Evidence owner.

```text
RUNTIME_OWNER_COUNT=1
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
```

## 2. Public signature

```python
observe_runtime_target(
    store,
    *,
    project_id: str,
    project_binding_id: str,
    target_identity: Mapping[str, Any],
    boundary: Mapping[str, Any],
    adapter: RuntimeAdapter,
    observed_at: str,
) -> dict[str, Any]
    # {"envelope": ..., "receipt": RuntimeObservationReceipt}

route_runtime_observation_to_evidence(
    store,
    receipt: RuntimeObservationReceipt,
    project_id: str,
    evidence_request: Mapping[str, Any],
) -> dict[str, Any]

bootstrap_projection_execution_capability(
    store,
    *,
    project_id: str,
    project_binding_id: str,
    github_projection_grant_refs: list[Mapping[str, str]],
    github_projection_grant_declaration_refs: list[Mapping[str, str]],
) -> ProjectionExecutionCapability
```

`target_identity` is `{provider, deployment_id, instance_identity, project_binding_ref,
deployment_fingerprint}` -- `project_binding_ref` must name exactly `project_binding_id`;
a target declaring a different Project Binding refuses before any adapter call. `boundary` is
the closed Observation Boundary: `{observation_method, endpoint, permitted_fields,
time_window, network_scope, timeout_seconds, redaction_fields, expected_field?,
expected_value?}` -- the complete, explicit closure of what may ever be asked, read, and kept.
`observed_at` is a required, caller-supplied instant (this route reads no clock, the identical
discipline every other route in this repository already requires) that must fall within
`boundary["time_window"]` -- an observation whose own instant already falls outside that
window refuses before the adapter is ever called. `adapter` is the caller's own
`RuntimeAdapter` implementation -- never selected, defaulted, or constructed by this route
itself.

`route_runtime_observation_to_evidence` hands an already-real `RuntimeObservationReceipt` to
the existing Evidence owner's own public `derive_evidence`, via a caller-supplied,
already-real, Change-free `evidence_request` grounded in the `verification_observation_request`
position (`evidence/engine.py`'s Change-Free Verification Evidence -- the identical position
Projection's own `route_observation_receipt_to_evidence` and Independent Verification's own
`route_verification_result_to_evidence` already use for a structurally identical fact: an
independent, Change-free confirmation of an external observation). Unlike Projection's own
handoff, this one never re-observes the live target at handoff time (see §6, item 3);
corroboration is Store resolution of the real, committed Envelope plus an exact-match check
against every one of the receipt's own fields.

`bootstrap_projection_execution_capability` (V5) is the Phase-14-deferred trusted runtime
bootstrap: a production-general adaptation of the Phase 14 V3 test harness's own
`resolve_v3_live_write_authority`, resolving caller-supplied grant/declaration **references**
(never bodies) exclusively within the caller-injected trusted `store`, and returning one
`ProjectionExecutionCapability` (Phase 14's own shipped, bound-once execution interface --
`manosube_agent_civilization.projection`) bound to a freshly constructed
`ProjectionExecutionContext`. See §7, V5.

```text
RuntimeAdapter (Protocol)
  adapter_identity              caller-inspectable identity, checked before observe() is ever
                                  called
  observe(*, target_identity, boundary) -> Mapping[str, Any]
                                  returns {transport_outcome, observed_fields,
                                  observed_deployment_identity} -- transport_outcome is one of
                                  the six RUNTIME_ADAPTER_TRANSPORT_OUTCOMES (OBSERVED |
                                  NOT_FOUND | PERMISSION_DENIED | TIMEOUT | UNAVAILABLE |
                                  MALFORMED); an adapter may never itself report NEGATIVE or
                                  IDENTITY_MISMATCH -- both are route-level-only
                                  classifications (§3, item 4)

RuntimeObservationReceipt (frozen dataclass)
  status                        one of VERIFIED | FAILED | INSUFFICIENT | UNAVAILABLE (this
                                  route's own classification never produces INSUFFICIENT; the
                                  value remains in the schema's closed set for a future caller)
  runtime_observation_envelope_id, project_id, target_identity, boundary, adapter_identity,
  human_authority_ref, input_refs, observations

Runtime Observation Envelope (persisted record)
  schema_version, runtime_observation_envelope_id, runtime_observation_semantic_fingerprint,
  project_id, target_identity, target_fingerprint, boundary, boundary_fingerprint,
  observation_request_identity, observed_at, observation_outcome, observed_fields,
  observed_content_fingerprint, adapter_identity, human_authority_ref
```

## 3. Frozen semantic decisions

1. **Observation only of an explicit, already-declared runtime target.** `observe_runtime_target`
   never discovers, infers, or enumerates targets of its own -- `target_identity` is always an
   explicit caller input, bound to a real, already-verified Project Binding.
2. **Runtime target state is never canonical.** No field a `RuntimeAdapter` reports is ever
   trusted as Difference, Change, Evidence, Authority, or State content directly -- it is
   independently reclassified (§3, item 4) and persisted only as a bounded Runtime Observation
   Envelope, then handed off to the existing Evidence owner exactly like any other independent
   observation.
3. **One replaceable Runtime Adapter, never a fixed transport.** No product, protocol, or
   deployment platform is selected by this Phase beyond the one method
   (`HTTP_GET_BOUNDED`) this delivery implements end to end. A `RuntimeAdapter` is always
   supplied by the caller.
4. **NEGATIVE/IDENTITY_MISMATCH are route-level-only classifications.** A `RuntimeAdapter` may
   only ever honestly report a transport-level fact (one of
   `RUNTIME_ADAPTER_TRANSPORT_OUTCOMES`). `observe_runtime_target` independently recomputes the
   observed content's own fingerprint and the observed target's own reported identity, and
   only it may ever classify the result as `NEGATIVE` (a genuine, semantic content mismatch
   against `boundary["expected_field"]`/`boundary["expected_value"]`) or `IDENTITY_MISMATCH` (a
   genuinely reached target whose own reported `deployment_fingerprint` does not match the
   declared one) -- never accepted from the adapter's own self-report, which the Protocol does
   not even offer a field for.
5. **Transport failure never becomes absence.** `NOT_FOUND` means only an authoritative,
   confirmed absence (this delivery's `LocalHttpRuntimeAdapter`: a genuine HTTP 404).
   `PERMISSION_DENIED`/`TIMEOUT`/`UNAVAILABLE`/`MALFORMED` each mean the adapter could not
   determine existence or content at all -- never folded into `NOT_FOUND`, never promoted to
   `OBSERVED`.
6. **Redaction happens before any fingerprint or persistence.** A field named in
   `boundary["redaction_fields"]` is replaced with a fixed marker before this route computes
   `observed_content_fingerprint` or commits the Envelope -- the real value never reaches
   canonical Store content, the receipt, or any fingerprint derived from either.
7. **Time-window enforcement precedes any adapter call.** An `observed_at` outside
   `boundary["time_window"]` refuses before `RuntimeAdapter.observe` is ever called -- the
   closed Boundary bounds *when* an observation may happen, not merely what it may read.
8. **No Authority Decision gates Runtime Observation.** Unlike Projection's own
   `github_projection_grant`-gated `MATERIALIZE_PROJECTION`, Runtime Observation mutates
   nothing external and is bounded entirely by its own explicit, closed Observation Boundary
   -- disclosed judgment call, §6, item 1.
9. **Read-only: no intent/materialize-attempt claim pair.** Unlike Projection's own atomic
   recoverable claim state machine (needed to prevent a duplicate *external write*), Runtime
   Observation creates no external artifact -- observing the identical target under the
   identical Boundary twice is two independent, equally legitimate facts, never a duplicate to
   guard against. Disclosed judgment call, §6, item 2.
10. **No re-observation at Evidence hand-off.** Unlike Projection's own `receipt_handoff.py`,
    which re-observes the live external artifact at hand-off time (a GitHub artifact is
    expected to remain stable), this hand-off never calls the adapter again -- a live runtime
    target may legitimately change between observation and hand-off. Corroboration is Store
    resolution plus exact-match field comparison. Disclosed judgment call, §6, item 3.

```text
RUNTIME_IS_A_SECOND_STATE_OWNER=false
RUNTIME_IS_A_SECOND_DIFFERENCE_OWNER=false
RUNTIME_IS_A_SECOND_AUTHORITY_OWNER=false
RUNTIME_IS_A_SECOND_EVIDENCE_OWNER=false
RUNTIME_IS_A_SECOND_STORE_OWNER=false
RUNTIME_IS_A_SECOND_CLOSURE_OWNER=false
RUNTIME_TARGET_STATE_IS_CANONICAL=false
RUNTIME_TARGET_IS_OBSERVATION_SURFACE_ONLY=true
RUNTIME_ADAPTER_IS_KERNEL_ELEMENT=false
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
├── adapter.py              FakeRuntimeAdapter (controlled, in-memory) and
│                           LocalHttpRuntimeAdapter (stdlib urllib only) -- the two
│                           RuntimeAdapter implementations
├── route.py                observe_runtime_target -- the one public Runtime Observation
│                           route
├── evidence_handoff.py     route_runtime_observation_to_evidence -- the one public
│                           Runtime-Observation-to-Evidence hand-off
└── bootstrap.py            bootstrap_projection_execution_capability -- the V5 trusted
                             runtime bootstrap provisioning Phase 14's
                             ProjectionExecutionCapability
```

No second Boot, Store, Binding, Evidence, Difference, Authority, or Reflow owner is created
anywhere in this package. `reflow` and `independent_verification` are never imported by any
module in this package. `authority` is importable only from `bootstrap.py`, and only to call
`evaluate_projection_authorization` exactly once, to provision Phase 14's own capability --
`route.py` never imports `authority` at all (§3, item 8). `evidence` is importable only from
`evidence_handoff.py` (the one `derive_evidence` call) and, narrowly, `bootstrap.py`
(read-only `evidence.identity.evidence_semantic_fingerprint`, to reverify an
`EVIDENCE_ARTIFACT`-kind subject's own real fingerprint -- the identical narrow reuse
Projection's own `route.py` already makes of the same function). `boot` is importable from
`route.py` and `bootstrap.py`, each calling `boot_project` exactly once. `binding.identity`
and `difference`/`change` identity utilities are importable only from `bootstrap.py`, for the
identical read-only grant/declaration/subject reverification Phase 14's own V3 test harness
already performs. `manosube_agent_civilization.projection` (the shipped Phase 14 execution
interface) is importable only from `bootstrap.py`. A network/transport surface (`urllib`) is
importable only from `adapter.py` -- static conformance proves all of this by AST walk, the
identical technique `tests/contract/projection/test_projection_static_conformance.py` already
uses.

## 5. Canonical route

```text
real Project/Human Authority (Boot re-verification)
→ explicit runtime target identity, fingerprinted (never trusted from a caller)
→ closed Observation Boundary, fingerprinted (never trusted from a caller)
→ time-window check -- refuses before any adapter call once expired
→ deterministic observation_request_identity (target + Boundary + issued_at)
→ replaceable Runtime Adapter -- one bounded transport call
→ independent content/identity reclassification (NEGATIVE/IDENTITY_MISMATCH computed here,
  never accepted from the adapter's own report; redaction applied before any fingerprint or
  persistence)
→ canonical Runtime Observation Envelope
→ existing canonical persistence boundary (store.commit.commit_state_transition)
→ bounded Runtime Observation Receipt
→ caller's own subsequent hand-off to the existing Evidence owner (Store resolution +
  exact-match corroboration, never a second live observation)
```

For V5's own separate route:

```text
caller-injected trusted Store
→ boot_project (Project/Human Authority re-verification)
→ caller-supplied github_projection_grant/github_projection_grant_declaration references,
  resolved and identity-recomputed exclusively within the trusted Store
→ each grant's own subject_ref resolved and identity-recomputed the identical way
  project_to_github itself resolves a Store-resolvable subject
→ evaluate_projection_authorization, once per distinct projection_kind the resolved grants
  themselves name (dynamic kind set, never a fixed three-kind requirement)
→ ProjectionExecutionContext
→ ProjectionExecutionCapability(context) -- Phase 14's own shipped, bound-once interface
```

## 6. Disclosed judgment calls

1. **No Authority Decision gates Runtime Observation.** Projection's own
   `github_projection_grant`-gated `MATERIALIZE_PROJECTION` exists because materializing an
   external artifact is a write a Human must have explicitly authorized. Runtime Observation
   performs no write of any kind against the observed target -- it is bounded entirely by its
   own explicit, closed Observation Boundary (target, method, permitted fields, time window,
   network scope, timeout, redaction). Requiring a separate Authority Decision on top of an
   already-closed Boundary would duplicate, not strengthen, the actual control this Phase
   needs.
2. **No intent/materialize-attempt claim pair.** Projection's own atomic recoverable claim
   state machine exists to prevent two concurrent callers from both materializing a duplicate
   *external* artifact. Runtime Observation creates no external artifact of any kind --
   observing the identical target under the identical Boundary twice, even concurrently, is
   two independent, equally legitimate facts (a target's own state may genuinely differ
   between the two), never a duplicate to guard against. This package therefore commits
   exactly one new Envelope per `observe_runtime_target` call, with no reuse-lookup semantics.
3. **No re-observation at Evidence hand-off.** Projection's own `receipt_handoff.py`
   independently re-observes the live external artifact at hand-off time, because a genuine
   GitHub artifact is expected to remain stable between materialization and hand-off, and a
   fresh re-observation is exactly what corroborates a receipt cannot be forged. A live
   runtime target may legitimately change between the original observation and a later
   hand-off -- re-observing here would either produce a spurious mismatch against a target
   that has since, legitimately, changed, or silently redefine "this receipt is genuine" to
   mean "the target still looks like this right now". Corroboration here instead means:
   resolve the real, committed Envelope from Store, independently re-verify its own semantic
   fingerprint (tamper detection), and require every one of the receipt's own fields to
   exactly equal what that real, resolved Envelope actually recorded.
4. **Identity follows Evidence's single-projection convention, not Projection's split key.**
   Projection deliberately splits `projection_envelope_id` (a pure function of subject/kind/
   target, independent of the eventual external artifact) from
   `projection_envelope_semantic_fingerprint` (the full committed fact), because a Projection
   Envelope has create-once-reuse-after semantics a stable, outcome-independent mapping key
   must serve. Runtime Observation has no such semantics: this package's own
   `runtime_observation_envelope_id` is a full-content digest exactly like Evidence's own
   `evidence_id`, and `runtime_observation_semantic_fingerprint` is the identical projection
   under a different, `sha256:`-prefixed encoding -- both digests cover every field, including
   the observed outcome itself.
5. **Runtime target references its owning Project Binding, not a Difference/Change/Evidence
   subject.** A Projection subject is always a real Difference/Change/Evidence record already
   in canonical State. A Runtime target is external infrastructure with no such canonical
   record of its own -- `target_identity["project_binding_ref"]` is the one existing-owner
   reference this Phase can genuinely bind an observation to, and is what
   `route_runtime_observation_to_evidence` uses for `verification_result_provenance`'s own
   `target_refs`/`input_refs`.

## 7. Required proof layers

**V1 -- deterministic identity/Boundary proof.** `tests/unit/runtime/test_runtime_identity.py`:
`runtime_target_fingerprint`/`runtime_observation_boundary_fingerprint`/
`runtime_observation_request_identity` are deterministic, field-sensitive, and each of the
three distinct identities (target, request, committed fact) remains genuinely distinct from
the other two for the identical observation.

**V2 -- controlled Adapter contract proof.** `tests/contract/runtime/
test_runtime_adapter_contract.py`: all eight `RUNTIME_OBSERVATION_OUTCOMES` are reachable
end to end through `FakeRuntimeAdapter` and the real route; a transport failure never becomes,
or is confused with, an authoritative absence; `NEGATIVE`/`IDENTITY_MISMATCH` are proved
route-level-only (the Fake adapter can only ever report a transport-level `OBSERVED`, and the
route alone reclassifies); the route fails closed on a malformed/out-of-vocabulary adapter
report and on an adapter with no readable `adapter_identity`.

**V3 -- real bounded runtime vertical proof.** `tests/integration/runtime/
test_runtime_local_http_vertical_proof.py`: one real, disposable, local HTTP target (started
and stopped by the test itself, `127.0.0.1`, an ephemeral port -- no VPS or cloud provider) is
observed through `LocalHttpRuntimeAdapter` end to end, including at least one genuine positive
(`OBSERVED`, real content) and one genuine bounded negative (`NOT_FOUND`, a real 404)
observation, with the positive receipt handed off to a real `VERIFIED` Evidence record.

**V4 -- failure/tamper/provenance proof matrix.** `tests/integration/runtime/
test_runtime_failure_tamper_matrix.py`: time-window refusal before any adapter call;
substituted-Binding refusal; sequential calls each surviving their own prior commit; an
unrelated Store mutation between calls never blocking a fresh, correctly re-verified
observation; redacted fields never appearing unredacted anywhere persisted, and never
affecting content-fingerprint collision-freedom for the field that carries them; a directly
edited committed Envelope caught by the Store's own manifest layer; a directly committed,
self-inconsistent Envelope caught by this package's own domain-level integrity check; every
individual receipt field (target identity, Boundary, status, observations, adapter identity,
Human Authority reference, input refs, envelope id) tampered one at a time and refused at
hand-off; cross-project receipt relabeling refused; a receipt genuinely produced under one
Store refused when handed off through an entirely different Store.

**V5 -- Phase 14 runtime-provisioning continuity proof.** `tests/integration/runtime/
test_runtime_bootstrap_continuity.py`: `bootstrap_projection_execution_capability` constructs
a real `ProjectionExecutionCapability` from canonical Store/Boot state and a genuine, signed
`github_projection_grant`/`github_projection_grant_declaration` pair, which then reaches a
controlled `FakeGitHubAdapter` (zero live network calls) through `.execute(...)`; refuses with
no grant references, an unresolvable grant reference, a grant with no anchoring declaration,
and two grants for the identical `projection_kind`; a static proof that `bootstrap.py` imports
no `tests.*` module and no network/transport surface of its own.

## 8. Explicit non-claims

```text
RUNTIME_OBSERVATION_ENVELOPE_IMPLEMENTED=true
RUNTIME_ADAPTER_BOUNDARY_IMPLEMENTED=true
LOCAL_HTTP_RUNTIME_ADAPTER_IMPLEMENTED=true
LOCAL_HTTP_RUNTIME_ADAPTER_EXECUTED_AGAINST_A_REAL_LOCAL_TARGET=true
VPS_OR_CLOUD_PROVIDER_REQUIRED=false
GENERAL_COMMAND_EXECUTOR_IMPLEMENTED=false
ORCHESTRATOR_OR_SCHEDULER_IMPLEMENTED=false
DEPLOYMENT_MANAGER_IMPLEMENTED=false
SECRET_STORE_IMPLEMENTED=false
PROCESS_SUPERVISOR_IMPLEMENTED=false
CLOUD_PROVIDER_OWNER_IMPLEMENTED=false
NEW_STATE_OWNER=false
NEW_EVIDENCE_OWNER=false
NEW_AUTHORITY_OWNER=false
NEW_STORE_OWNER=false
TRUSTED_RUNTIME_BOOTSTRAP_IMPLEMENTED=true
PROJECTION_EXECUTION_CAPABILITY_PROVISIONED_FROM_CANONICAL_STORE_BOOT_STATE=true
BOOTSTRAP_IMPORTS_NO_TEST_MODULE=true
BOOTSTRAP_CREATES_NO_STORE_FROM_AN_UNTRUSTED_PATH=true
BOOTSTRAP_MINTS_NO_AUTHORITY=true
BOOTSTRAP_ACCEPTS_NO_AUTHORITATIVE_RECORD_BODIES=true
TRANSPORT_LEVEL_OUTCOME_VOCABULARY_CLOSED=true
ROUTE_LEVEL_NEGATIVE_AND_IDENTITY_MISMATCH_NEVER_ADAPTER_REPORTED=true
REDACTION_APPLIED_BEFORE_ANY_FINGERPRINT_OR_PERSISTENCE=true
TIME_WINDOW_ENFORCED_BEFORE_ANY_ADAPTER_CALL=true
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
```

## 9. Gate 15

```text
GATE=15
GATE_NAME=BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_PROVISIONING
GOVERNING_ISSUE=#64
ADOPTION_ID=ADOPT_P15_D001_BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_PROVISIONING
V1_DETERMINISTIC_IDENTITY_PROOF=true
V2_CONTROLLED_ADAPTER_CONTRACT_PROOF=true
V3_REAL_BOUNDED_RUNTIME_VERTICAL_PROOF=true
V4_FAILURE_TAMPER_PROVENANCE_PROOF_MATRIX=true
V5_PHASE_14_RUNTIME_PROVISIONING_CONTINUITY_PROOF=true
STATIC_CONFORMANCE_PROOF=true
```

`PHASE_15_COMPLETE`/`PHASE_16_ALLOWED` remain `false`: this delivery closes Issue #64's own
structural findings, not Phase 15 itself, which awaits a separate SHUKOU decision -- the
identical discipline every prior Phase's own first-delivery contract already states.
