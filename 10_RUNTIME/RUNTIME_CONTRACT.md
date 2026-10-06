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
TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT=0
RUNTIME_DEPLOYMENT_DECLARATION_COMMIT_ENTRY_POINT_COUNT=1
STRUCTURAL_REVIEW_ROUNDS_APPLIED=3
```

`TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT` was `1` after Round 1 and is `0` from
Round 2 onward: shipped code mints no `TrustedRuntimeRoot`, and Round 3 (§12.1) does **not**
reintroduce a minting function. It instead makes the type inert — possessing one grants nothing —
and gates provisioning on a canonical `runtime_root_admission` record verified against an
externally supplied trust anchor, so the type's own constructor is public again without being a
trust decision. Read §12.1.1 before reading Round 3's diff.

Section 10 records Structural Review Round 1 (P15-R1-F1..F6) in full; section 11 records
Structural Review Round 2 (P15-R2-F1/F2), which reopened and supersedes Round 1's own
corrections for F4 and F6; section 12 records Structural Review Round 3 (P15-R3-F1/F2), which
reopened and supersedes both of Round 2's; section 13 records Structural Review Round 4
(P15-R4-F1/F2), which reopened and supersedes both of Round 3's; section 14 records Structural
Review Round 5 (P15-R5-F1/F2/F3), which reopened and supersedes Round 4's F1 and added a third,
independent finding about timestamp ordering at declaration commit; section 15 records Structural
Review Round 6 (P15-R6-F1), which reopens and supersedes Round 5's F2 — the per-call admission
recheck ran once, at the start of the request, and never re-established the resolved record's own
integrity; section 16 records Structural Review Round 7 (P15-R7-F1), which confirms Round 6's two
barriers and their placement closed and widens only what each one *proves* — both of Round 6's
recomputations read a projection that deliberately excludes the record's own declared id, its own
declared semantic fingerprint and its whole `signature` block, so a substitution changing only one
of those three still passed. Where two sections differ, the **highest-numbered** section governs.

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
    trusted_runtime_root: TrustedRuntimeRoot,
    *,
    runtime_root_admission_ref: Mapping[str, str],
    trust_anchor_public_key_hex: str,
    github_projection_grant_refs: list[Mapping[str, str]],
    github_projection_grant_declaration_refs: list[Mapping[str, str]],
) -> ProjectionExecutionCapability

commit_runtime_deployment_declaration(
    store,
    project_id: str,
    declaration: Mapping[str, Any],
    *,
    committed_at: str,
) -> dict[str, Any]
    # {"runtime_deployment_declaration_ref", "runtime_deployment_target_key",
    #  "committed_state"}
```

`commit_runtime_deployment_declaration` (Round 3, P15-R3-F2 — see §12.2) is a canonical
*committer*, not a fourth route: in one atomic `commit_state_transition` it commits the immutable
declaration record **and** moves that target's own current-declaration pointer
(`semantic_state.runtime.claims[<target_key>]`). Issuing any new declaration for a target —
`ACTIVE` (a rotation) or `REVOKED` (a revocation) — supersedes whatever the pointer named before,
which is what makes revocation genuinely effective rather than merely declared.

`target_identity` is `{provider, deployment_id, instance_identity, project_binding_ref,
deployment_declaration_ref, deployment_fingerprint}` (`deployment_declaration_ref` added by
Round 1, P15-R1-F6 -- see §10; the record it names became signed, status-bound, and
Boot-Authority-cross-checked in Round 2, P15-R2-F2 -- see §11.2; and validity-windowed and
supersession-bound in Round 3, P15-R3-F2 -- see §12.2) --
`project_binding_ref` must name exactly `project_binding_id`;
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
(never bodies) exclusively within the trusted `store`, and returning one
`ProjectionExecutionCapability` (Phase 14's own shipped, bound-once execution interface --
`manosube_agent_civilization.projection`) bound to a freshly constructed
`ProjectionExecutionContext`. Since Round 1 (P15-R1-F4) it names that Store only through an
opaque `TrustedRuntimeRoot`; it carries no `store`/`project_id`/`project_binding_id` parameter
of its own at all. **Since Round 2 (P15-R2-F1) there is no shipped way to obtain that root**:
the public minting factory is deleted, nothing in the shipped package constructs a
`TrustedRuntimeRoot`, and this route is exercised only by tests through an explicitly
test-confined issuer, pending a future Phase's real deployment composition boundary. See §7, V5,
§10.4, and §11.1 (including that correction's own scope caveat).

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
├── network.py              require_endpoint_within_network_scope / canonical_endpoint_url /
│                           canonical_endpoint_host -- pure, I/O-free network-scope
│                           enforcement (Round 1, P15-R1-F1); the only module besides
│                           adapter.py naming urllib, and only ever urllib.parse
├── adapter.py              FakeRuntimeAdapter (controlled, in-memory) and
│                           LocalHttpRuntimeAdapter (stdlib urllib only, no redirect ever
│                           followed) -- the two RuntimeAdapter implementations
├── deployment_declaration.py
│                           verify_runtime_deployment_declaration_signature -- the local
│                           composition of binding.signature's own shared Ed25519 primitive
│                           over a deployment declaration's signing payload (Round 2,
│                           P15-R2-F2); verification only, never signing, never a key of its
│                           own, and never imported by binding/
├── root_admission.py       verify_runtime_root_admission_signature -- the identical local
│                           composition over a root admission's signing payload, against a
│                           trust anchor public key the DEPLOYMENT supplies rather than any
│                           Store-resolved signing key (Round 3, P15-R3-F1); verification
│                           only, again never signing and never a key of its own
├── deployment_registry.py  commit_runtime_deployment_declaration /
│                           current_deployment_declaration_id -- the canonical
│                           current-declaration pointer in semantic_state.runtime.claims, and
│                           the one atomic commit-the-record-and-move-the-pointer transition
│                           that makes revocation genuinely effective (Round 3, P15-R3-F2)
├── route.py                observe_runtime_target -- the one public Runtime Observation
│                           route
├── evidence_handoff.py     route_runtime_observation_to_evidence -- the one public
│                           Runtime-Observation-to-Evidence hand-off
└── bootstrap.py            TrustedRuntimeRoot (an ordinary public frozen value that grants
                             nothing by itself -- Round 3, P15-R3-F1; shipped code still
                             constructs none, and the Round 1 minting factory Round 2 deleted
                             is not reintroduced) and
                             bootstrap_projection_execution_capability -- the V5 trusted
                             runtime bootstrap provisioning Phase 14's
                             ProjectionExecutionCapability, gated on a canonical, externally
                             anchored runtime_root_admission on every call

01_SCHEMA/runtime/
├── runtime_observation_envelope.schema.json     the committed observation fact
├── runtime_deployment_declaration.schema.json   the canonical, Human-Authority-declared
│                                                 deployment identity a target's own claimed
│                                                 deployment_fingerprint must match
│                                                 (Round 1, P15-R1-F6); required `status` and
│                                                 required Ed25519 `signature` added by
│                                                 Round 2, P15-R2-F2; required
│                                                 `valid_from`/`valid_until` added by Round 3,
│                                                 P15-R3-F2
└── runtime_root_admission.schema.json           the canonical, content-addressed,
                                                  trust-anchor-signed record admitting exactly
                                                  one project and one Project Binding, without
                                                  which a TrustedRuntimeRoot provisions
                                                  nothing (Round 3, P15-R3-F1)
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
already performs; `binding.signature` is importable only from `deployment_declaration.py`
(Round 2, P15-R2-F2) and `root_admission.py` (Round 3, P15-R3-F1), each for the one shared
Ed25519 verification primitive it composes rather than reimplements. `commit_state_transition`
is called from exactly two modules, each exactly once: `route.py` (one Envelope per observation)
and `deployment_registry.py` (one atomic record-and-pointer transition per issued declaration,
Round 3, P15-R3-F2); no module in this package ever calls a `store` object's own `.commit`
directly. `binding/` imports nothing from this package, in either direction: Runtime is an
adapter layer that depends on the Kernel's Binding element, never the reverse. `manosube_agent_civilization.projection` (the shipped Phase 14 execution
interface) is importable only from `bootstrap.py`. A network/transport surface that actually
*opens* anything (`urllib.request`/`urllib.error`) is importable only from `adapter.py`;
`network.py` may additionally import exactly `urllib.parse`, a parse-only surface, and is
statically proved to call nothing that could open, resolve, or read anything (Round 1,
P15-R1-F1 -- `route.py` itself still imports no `urllib` of any kind). `engine.py`
additionally imports `difference.errors`, solely to translate the canonical schema
validator's own failure into this package's own refusal vocabulary (Round 1, P15-R1-F2).
Static conformance proves all of this by AST walk, the identical technique
`tests/contract/projection/test_projection_static_conformance.py` already uses.

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
→ canonical, ACTIVE, content-addressed runtime_root_admission naming exactly this project and
  this Project Binding, resolved inside the trusted Store and verified against the
  deployment-supplied trust_anchor_public_key_hex -- before any grant is resolved and before any
  authorization is evaluated (Round 3, P15-R3-F1)
→ caller-supplied github_projection_grant/github_projection_grant_declaration references,
  resolved and identity-recomputed exclusively within the trusted Store
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
6. **The trust root is a type, and in this Phase shipped code mints none (Round 1, P15-R1-F4;
   superseded by Round 2, P15-R2-F1).** Round 1 made `bootstrap_projection_execution_capability`
   read an opaque `TrustedRuntimeRoot` instead of `store`/`project_id`/`project_binding_id`, and
   introduced `provision_trusted_runtime_root` in front of it. Round 2 found that factory *was*
   the caller-selected trust anchor, merely relocated, and deleted it. `TrustedRuntimeRoot`
   itself is kept: it is unforgeable by shape (a module-private sentinel is a required
   constructor argument), it holds no Boot verdict that could go stale (only *which* world is in
   play; every check runs fresh inside the bootstrap call), and it is the shape a future,
   separately authorized Phase's real deployment composition boundary will mint. Until then the
   only issuer is a test-confined one, and the capability route has no production-legitimate way
   to obtain its own first argument. Full rationale and the exact scope caveat in §11.1.

7. **A deployment declaration is a signed, revocable, Boot-Authority-bound Human Authority
   statement, not merely a content-addressed body (Round 2, P15-R2-F2).** Round 1's own §10.6
   explicitly declined to compare a declaration's `human_authority_ref` against the currently
   Boot-verified Human Authority, on the grounds that no adopted decision established what
   should happen at a re-binding. Round 2 adopts that decision: a re-binding **does** invalidate
   previously issued deployment declarations for new observations, and there is no silent
   carry-forward. `RUNTIME_CREDENTIAL_USE_AUTHORITY` remains `false` -- this package still holds
   no private key, mints no signature, and reaches no key server; it only *verifies* a signature
   against the public key a real, Boot-restored Project Binding already carries, exactly as
   Binding itself already does for its own two declaration kinds. Full rationale in §11.2.

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
no `tests.*` module and no network/transport surface of its own. (Since Round 1, every call
here names its world through a `TrustedRuntimeRoot` -- P15-R1-F4, §10.4; since Round 3, every
call additionally presents a genuine, externally anchored `runtime_root_admission`, which is what
actually admits it -- P15-R3-F1, §12.1.)

**Round 1 proof layers.** Six further suites, one per adopted finding, are listed in §10.9.
**Round 2 proof layers** are listed in §11.5. **Round 3 proof layers** are listed in §12.5.

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
OBSERVATION_BOUNDARY_CLOSED=true
NETWORK_SCOPE_ENFORCED_BEFORE_ANY_CONNECTION=true
REDIRECT_EVER_FOLLOWED=false
DEPLOYMENT_IDENTITY_STORE_ANCHORED=true
DEPLOYMENT_DECLARATION_HUMAN_AUTHORITY_SIGNED=true
DEPLOYMENT_DECLARATION_STATUS_ENFORCED=true
DEPLOYMENT_DECLARATION_BOUND_TO_BOOT_RESTORED_AUTHORITY=true
DEPLOYMENT_DECLARATION_VALIDITY_WINDOW_REQUIRED=true
DEPLOYMENT_DECLARATION_REVOCATION_IS_EFFECTIVE=true
DEPLOYMENT_DECLARATION_CURRENT_POINTER_IS_STORE_RESOLVED=true
TRUSTED_RUNTIME_ROOT_REQUIRED_FOR_PROVISIONING=true
SHIPPED_TRUSTED_RUNTIME_ROOT_MINTING_PATH_EXISTS=false
POSSESSING_A_TRUSTED_RUNTIME_ROOT_GRANTS_ADAPTER_ACCESS=false
RUNTIME_ROOT_ADMISSION_REQUIRED_FOR_PROVISIONING=true
RUNTIME_ROOT_ADMISSION_VERIFIED_AGAINST_AN_EXTERNALLY_SUPPLIED_ANCHOR=true
PRODUCTION_LEGITIMATE_PROVISIONING_MECHANISM_SHIPPED=true
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false
AUTHORITY_FRESHNESS_RECHECKED_AT_ADAPTER_AND_COMMIT_BOUNDARIES=true
CURRENT_DECLARATION_POINTER_RECHECKED_ON_EVERY_COMMIT_ATTEMPT=true
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
RUNTIME_HOLDS_A_PRIVATE_SIGNING_KEY=false
RUNTIME_MINTS_A_SIGNATURE=false
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
STRUCTURAL_REVIEW_ROUND_1_CORRECTIONS_APPLIED=true
STRUCTURAL_REVIEW_ROUND_1_FINDINGS_CLOSED=6
STRUCTURAL_REVIEW_ROUND_2_CORRECTIONS_APPLIED=true
STRUCTURAL_REVIEW_ROUND_2_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_3_CORRECTIONS_APPLIED=true
STRUCTURAL_REVIEW_ROUND_3_FINDINGS_CLOSED=2
```

`PHASE_15_COMPLETE`/`PHASE_16_ALLOWED` remain `false`: this delivery closes Issue #64's own
structural findings, not Phase 15 itself, which awaits a separate SHUKOU decision -- the
identical discipline every prior Phase's own first-delivery contract already states.

## 10. Structural Review Round 1 corrections (P15-R1-F1 .. P15-R1-F6)

```text
ROUND=1
GOVERNING_REVIEW=PR #65 Structural Review Round 1
FINDINGS_ADOPTED=6
FINDINGS_CLOSED=6
```

Round 1 found six ways the first delivery's own claims were weaker than the code actually
kept. Each is recorded below as *what was claimed*, *what was true*, and *what the code now
does* -- the identical per-round accumulation `09_PROJECTION/PROJECTION_CONTRACT.md` already
keeps.

### 10.1 P15-R1-F1 -- network scope is now genuinely enforced, and no redirect is followed

*Claimed:* `OBSERVATION_BOUNDARY_CLOSED=true` -- the Boundary closes what may be reached.
*True:* `LocalHttpRuntimeAdapter.observe` constructed and opened `boundary["endpoint"]` and
never read `boundary["network_scope"]["allowed_hosts"]` at all, so a Boundary could name one
allowed host and the GET could go to another; and stdlib `urllib`'s automatic redirect
following could leave the declared host entirely, with no post-redirect check anywhere.

*Now:*

- A new pure module, `runtime/network.py`, owns the decision. It parses the endpoint with
  `urllib.parse.urlsplit` (parse-only -- it opens, resolves, and reads nothing, proved by an
  AST walk in static conformance) and refuses, before any connection could exist: an
  unsupported scheme (only `http`/`https`), userinfo (`user@host`), an absent or ambiguously
  encoded host, a port that is present but non-numeric or outside `1..65535`, a malformed
  network scope, and any host that is not an exact case-insensitive member of `allowed_hosts`.
- **The check runs in `route.py`'s own Boundary validation**, so a wrong-host Boundary refuses
  with the adapter **never invoked at all** -- structurally, for every adapter implementation
  that exists or will exist, rather than depending on each adapter to police itself.
- `LocalHttpRuntimeAdapter` re-runs the identical check itself immediately before opening a
  socket (defense in depth; neither site assumes it is the only one).
- **No redirect is ever followed.** The adapter builds its own opener with a redirect handler
  that returns `None` for every 3xx, so `urllib` raises it as an ordinary `HTTPError` and it
  is classified `UNAVAILABLE` at the one place transport failures are already classified.
  Chosen over per-hop host validation deliberately: this is a bounded observation probe
  against one explicit declared endpoint, not a general HTTP client, so a target answering
  3xx has not answered the bounded question that was asked.

Deliberately *not* attempted (`OVER_ENGINEERING_REFUSED=true`): no DNS resolution, and
therefore no claim that an allowed hostname resolves to an allowed address; no IDN/punycode
normalization; no per-port scoping. `allowed_hosts` is a closed allowlist of *names*, exactly
as the Boundary schema declares it.

### 10.2 P15-R1-F2 -- the complete declared shape is proved before Boot or any adapter

*Claimed:* the closed Boundary bounds the observation.
*True:* `route._require_boundary` checked an observation method, two non-empty timestamp
strings, and a non-empty `permitted_fields`. Endpoint, network scope, timeout, redaction
fields, exact key set, and timestamp grammar were validated only inside
`derive_runtime_observation_envelope` -- *after* `adapter.observe` had already run. And
`_require_within_time_window` compared timestamps as strings.

*Now:* `target_identity` and `boundary` are validated completely against
`runtime_observation_envelope.schema.json`'s own `$defs/target_identity`/`$defs/boundary`
before Boot or any adapter is reached, reusing the canonical registry
(`difference.validation.subschema_validator`/`validate_subrecord`, factored out of the
existing loader so no second schema loader exists). `observed_at` is validated against the
canonical timestamp grammar the same way. The window is then compared as **real UTC instants**
(`datetime.fromisoformat` after normalizing the `Z` suffix), and `issued_at < expires_at` is
required rather than assumed.

The string comparison was genuinely unsound, not merely inelegant.
`common/timestamp.schema.json` admits an optional fractional part, and `.` (0x2E) sorts below
`Z` (0x5A):

```text
"2026-01-01T00:10:00.5Z" < "2026-01-01T00:10:00Z"    lexicographically TRUE
 00:10:00.5              > 00:10:00                   chronologically LATER
```

So the old check *accepted* an observation half a second after expiry, and *refused* one half
a second after a whole-second `issued_at`. Both directions are proved, in both directions, in
`tests/contract/runtime/test_runtime_boundary_enforcement.py`.

### 10.3 P15-R1-F3 -- an adapter can neither escape the field boundary nor mutate validated inputs

*Claimed:* observed content is bounded to `permitted_fields`, and redaction precedes any
fingerprint or persistence.
*True:* for an `OBSERVED` response the route passed the adapter's **entire** `observed_fields`
mapping into redaction, fingerprinting, and persistence -- it never independently restricted
it -- so a buggy or hostile adapter could persist a field the Boundary never admitted, a
credential included. Separately, the route handed the adapter the very same mutable
`checked_target_identity`/`checked_boundary` dict objects it then reused, so an adapter could
mutate them in place after validation.

*Now:*

- The adapter receives **deep-frozen, alias-free** copies (`types.deep_freeze`, already this
  package's own helper), so mutation is impossible rather than merely detectable.
- After the call, the route **independently projects** `observed_fields` down to exactly
  `boundary["permitted_fields"]`, and **raises `RuntimeAdapterError`** on any extra key rather
  than silently dropping it -- a compliant adapter never reports an unpermitted field, so one
  that does is a defect worth surfacing loudly. Nothing is committed on that path.
- Everything after the call (fingerprints, Envelope, receipt, `input_refs`) is recomputed from
  the route's own validated copies alone, never from anything the adapter echoes back.

### 10.4 P15-R1-F4 -- the trusted bootstrap no longer accepts a caller-selected Authority world

> **Superseded in part by §11.1 (P15-R2-F1).** Round 2 reopened this finding: the
> `provision_trusted_runtime_root` factory this subsection introduces *was itself* the
> caller-selected trust anchor, relocated one call earlier. It no longer exists. Everything
> below about the *type* remains accurate; every statement about the *factory* is historical.

*Claimed:* `bootstrap_projection_execution_capability` provisions from *canonical* Store/Boot
state.
*True:* it accepted `store`/`project_id`/`project_binding_id` as its own free parameters and
proved only internal self-consistency inside whatever Store it was handed. A fully
self-consistent alternate Store -- its own Human Authority signing key, its own Binding,
grants, declarations and subjects, all internally valid -- produced a real
`ProjectionExecutionCapability`, because nothing in the signature distinguished "the canonical
adopted Store" from "any internally consistent Store a caller passes".

*Now (new disclosed judgment call -- see §6, item 6):* provisioning is **two steps**, and the
capability call has no Store-selecting parameter at all.

```text
provision_trusted_runtime_root(store, project_id=..., project_binding_id=...)
    -> TrustedRuntimeRoot      frozen, opaque, constructible ONLY through this function (a
                               module-private sentinel is a required constructor argument;
                               a directly constructed root raises). Performs no Boot, resolves
                               no record, commits nothing -- it holds no verdict that could
                               ever go stale, only WHICH world is in play.

bootstrap_projection_execution_capability(trusted_runtime_root, *, grant refs, declaration refs)
    -> ProjectionExecutionCapability
                               reads store/project/binding from the root alone, checks
                               isinstance up front (before Boot), and resolves every reference
                               exclusively within that root's own Store.
```

This is closed **structurally, not evidentially**: no environment digest, no hardcoded
repository key, no other caller-selectable anchor is introduced -- the parameter through which
an alternate world could be named simply does not exist any more. Deciding *which* root is
canonical remains the deployment's own responsibility, exactly as choosing which Store to open
always was; what changed is that the decision now happens once, visibly, at a dedicated
boundary instead of being re-offered on every capability request.

### 10.5 P15-R1-F5 -- authority freshness is re-proved at the adapter and commit boundaries

*Claimed:* each call independently re-verifies Project/Human Authority through Boot.
*True:* it Boot-verified **once**, at the start, then called the adapter and committed under
bounded Compare-And-Swap retries without re-proving anything -- so a mutation landing before
adapter entry reached a live target under stale context, and a later retry could commit an
Envelope carrying a now-stale `human_authority_ref` into newer State.

*Now:* the authority-defining context is re-proved immediately before `adapter.observe`
(refusing with **zero adapter calls**) and again on **every** commit attempt inside the retry
loop (refusing to commit). All three Boots go through one private helper, so `route.py` still
contains exactly one literal `boot_project` call site.

The comparison is over a closed projection -- `{project_binding_id, human_authority_ref,
human_authority_signing_key}` -- and deliberately **not** over `state_revision`/
`semantic_fingerprint` (which is what Phase 14's own `execution_context_still_current`
correctly compares for a *bound, reused* capability). A Runtime Observation re-verifies Boot
fresh on every call, so an ordinary unrelated commit is not a reason to refuse anything; it is
exactly the contention the bounded retry exists to absorb. The existing proof that an
unrelated Store mutation between calls never blocks a fresh observation therefore still holds,
and a new proof adds the harder case: an unrelated commit landing *inside* the retry loop.

A new error class, `RuntimeAuthorityFreshnessError`, names this refusal. It is deliberately a
sibling of `RuntimeRequirementError` and `RuntimeEnvelopeIntegrityError` rather than a subclass
of either: no caller input was malformed, and the derived Envelope is entirely self-consistent
-- what changed is the *world underneath an already-valid request*, which a caller may
legitimately retry against the new authority, and which neither existing class names honestly.

*Disclosed structural note.* Within this Kernel a Project Binding is content-addressed over
its own `human_authority_ref`/`human_authority_signing_key`, and Boot re-verifies that address
on every restore -- so a substituted Binding cannot also satisfy Boot for the same
`project_binding_id`; Boot itself catches it. These re-checks are therefore genuinely
load-bearing for the case this route must still defend against rather than assume away:
`observe_runtime_target`'s `store` parameter is `Any`, so a caller may inject any object at
all, and this route never assumes the one it was given is a content-addressed `FileStateStore`.

### 10.6 P15-R1-F6 -- deployed identity is Store-anchored, not echoed

> **Superseded in part by §11.2 (P15-R2-F2).** Round 2 reopened this finding: a content address
> over a *self-asserted* body proves only internal self-consistency, so any Store-writing caller
> could still construct a declaration naming any Human Authority and any deployment fingerprint.
> The record is now signed and status-bound, and the route now cross-checks it against the
> Human Authority its own Boot restored. In particular, the "Deliberately not added, disclosed"
> paragraph below is **reversed** by Round 2, which adopts exactly the decision it declined to
> assume.

*Claimed:* the observed target's own reported identity is checked against the declared one.
*True:* `target_identity["deployment_fingerprint"]` was an arbitrary caller string and
`observed_deployment_identity` was read straight out of the target's own response, so the
comparison proved only that *the endpoint echoed the expected string* -- which anyone
controlling both the declaration and the endpoint can arrange trivially.

*Now:* a new canonical record kind anchors the declared side.

```text
01_SCHEMA/runtime/runtime_deployment_declaration.schema.json
  schema_version, runtime_deployment_declaration_id (content-addressed),
  runtime_deployment_declaration_semantic_fingerprint, project_id, project_binding_ref,
  provider, deployment_id, instance_identity, deployment_fingerprint, human_authority_ref,
  declared_at
```

`target_identity` gains a required `deployment_declaration_ref`. Before comparing declared
against observed, `route.py` resolves that reference from Store, requires the resolved record
to be schema-valid, independently recomputes its own id and semantic fingerprint and requires
both to equal their declared values (the identical `_resolve_*`-with-identity-reverification
pattern `bootstrap.py` already applies to grants and declarations), requires its `project_id`
to match, requires it to independently restate this target's own `project_binding_ref`/
`provider`/`deployment_id`/`instance_identity` (the anti-replay control -- a valid declaration
for one target can never anchor another), and requires
`target_identity["deployment_fingerprint"]` to equal the declaration's own. Only then does the
existing observed-vs-declared comparison run, unchanged.

**Classification, disclosed.** Every refusal on this path is a `RuntimeRequirementError` with
**zero commits**, never an `IDENTITY_MISMATCH` observation outcome. `IDENTITY_MISMATCH` is a
statement about what a genuinely reached target reported; on this path nothing has been
reached, because the *request itself* is not anchored -- so there is no observation to
classify, and none is committed.

**Deliberately not added, disclosed.** The resolved declaration's own `human_authority_ref` is
schema-checked as a reference and covered by the record's content address, but is **not**
required to equal the currently Boot-verified Human Authority. Adopted finding F6 does not
name that constraint, and adding it would silently invalidate every previously declared
deployment whenever a project is legitimately re-bound to a new Human Authority -- an
operational semantics no adopted decision establishes. Named here so the omission is a
disclosed choice rather than an oversight.

`RUNTIME_CREDENTIAL_USE_AUTHORITY` remains `false`: this anchor introduces no secret, no HMAC,
and no signing-key material of its own. It is a canonical, content-addressed, Human-Authority-
declared *record*, resolved through the Store like every other canonical fact in this
repository.

### 10.7 Reference registry scope (checked, deliberately unchanged)

`reflow/reference_registry.py`'s `STORE_OWNED_REFERENCE_KINDS` gains **no** entry for
`runtime_deployment_declaration`. That registry enumerates the reference edges the *Reflow*
vertical's own Store admission path persists and resolves; its own docstring is explicit that
a kind this Kernel names but gives no Reflow-Store-owned producer of its own is out of scope,
never silently treated as resolved. `runtime_deployment_declaration` is committed by this
package through `commit_state_transition`, exactly as `runtime_observation_envelope`,
`projection_envelope`, and `github_projection_grant` already are -- none of which has an entry
there either, for the identical reason. Adding one would claim a Reflow producer that does not
exist.

### 10.8 Round 1 declarations

```text
NETWORK_SCOPE_ENFORCED_BEFORE_ANY_CONNECTION=true
NETWORK_SCOPE_ENFORCED_IN_ROUTE_NOT_ONLY_IN_ADAPTER=true
WRONG_HOST_BOUNDARY_PRODUCES_ZERO_ADAPTER_CALLS=true
REDIRECT_EVER_FOLLOWED=false
DNS_RESOLUTION_PERFORMED=false
COMPLETE_TARGET_AND_BOUNDARY_SCHEMA_VALIDATION_PRECEDES_BOOT_AND_ADAPTER=true
TIME_WINDOW_COMPARED_AS_REAL_INSTANTS=true
TIME_WINDOW_ORDERING_REQUIRED=true
ADAPTER_RECEIVES_DEEP_FROZEN_INPUTS=true
OBSERVED_FIELDS_INDEPENDENTLY_PROJECTED_TO_PERMITTED_FIELDS=true
UNPERMITTED_ADAPTER_FIELD_SILENTLY_DROPPED=false
TRUSTED_RUNTIME_ROOT_REQUIRED_FOR_PROVISIONING=true
BOOTSTRAP_ACCEPTS_A_CALLER_SELECTED_STORE=false
TRUSTED_RUNTIME_ROOT_DIRECTLY_CONSTRUCTIBLE=false
AUTHORITY_FRESHNESS_RECHECKED_BEFORE_ADAPTER=true
AUTHORITY_FRESHNESS_RECHECKED_ON_EVERY_COMMIT_ATTEMPT=true
UNRELATED_STORE_MUTATION_BLOCKS_OBSERVATION=false
DEPLOYMENT_IDENTITY_STORE_ANCHORED=true
DEPLOYMENT_DECLARATION_REPLAY_ACROSS_TARGETS_ALLOWED=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
```

### 10.9 Round 1 proof layers

```text
tests/unit/runtime/test_runtime_network_scope.py               F1 (pure decision)
tests/unit/runtime/test_runtime_identity.py                    F6 (declaration identity)
tests/contract/runtime/test_runtime_boundary_enforcement.py    F1/F2 (zero-call refusals)
tests/contract/runtime/test_runtime_static_conformance.py      F1/F2/F4/F5 (static facts)
tests/integration/runtime/test_runtime_local_http_redirect_control.py
                                                               F1 (real 3xx, two live servers)
tests/integration/runtime/test_runtime_adapter_boundary_escape.py
                                                               F3 (field escape, mutation,
                                                                   substitution, leakage)
tests/integration/runtime/test_runtime_trusted_root.py         F4 (decisive control, both
                                                                   worlds built for real)
tests/integration/runtime/test_runtime_authority_freshness.py  F5 (both barriers + the
                                                                   harmless-contention control)
tests/integration/runtime/test_runtime_deployment_identity_anchor.py
                                                               F6 (spoofing, replay, tamper)
```

## 11. Structural Review Round 2 corrections (P15-R2-F1, P15-R2-F2)

```text
ROUND=2
GOVERNING_REVIEW=PR #65 Structural Review Round 2
FINDINGS_ADOPTED=2
FINDINGS_CLOSED=2
REOPENED_FROM_ROUND_1=P15-R1-F4 (now P15-R2-F1), P15-R1-F6 (now P15-R2-F2)
ROUND_1_FINDINGS_CONFIRMED_CLOSED=P15-R1-F1, P15-R1-F2, P15-R1-F3, P15-R1-F5
```

Round 2 confirmed four of Round 1's own six corrections closed cleanly and reopened two: the
trusted-provisioning correction (§10.4) and the deployment-identity anchor (§10.6). Both are
recorded below in the same *what was claimed / what was true / what the code now does* form,
with the same rule as Round 1: where this section and an earlier one differ, this section
governs.

### 11.1 P15-R2-F1 -- shipped code mints no trust root at all

*Claimed (Round 1):* provisioning is two steps, and the capability call "no longer has *any*
parameter through which an alternate Store, Project, or Binding could be named at all".

*True:* the *capability call* did not — but `provision_trusted_runtime_root(store,
project_id=..., project_binding_id=...)` was publicly exported and accepted exactly that tuple.
Its module-private sentinel protected only the `TrustedRuntimeRoot` dataclass's own constructor;
the public factory supplied that sentinel for whatever Store the caller passed. Any caller could
simply call the factory. Moving the same three arguments one call earlier changed API shape, not
control of the trust decision. Round 1's own regression suite *demonstrated* the bypass rather
than closing it: `test_the_alternate_world_is_genuinely_self_consistent_under_its_own_authority`
provisioned a root over an independently built alternate Store and obtained a real
`ProjectionExecutionCapability`; the later "decisive" test proved only that alternate
*references* do not resolve inside a *canonical* root, never that a caller could not provision
and use the *alternate* root directly.

*Now:*

- **`provision_trusted_runtime_root` is deleted**, from `bootstrap.py` and from
  `runtime/__init__.py`'s exports and `__all__`. It is not replaced by a same-shaped function
  under a new name anywhere in `src/` — that would reproduce the exact defect the review named.
- **`TrustedRuntimeRoot` is kept**, unchanged in role: a frozen, slotted dataclass whose
  `__post_init__` still requires the module-private `_PROVISIONING_SENTINEL`, still drops it
  once checked (so holding a root grants no ability to mint another), and now also carries the
  canonical-identity check the deleted factory used to perform before construction. The *type*
  was never the problem; the public *minting function* was.
- **`bootstrap_projection_execution_capability`'s signature is unchanged** — Round 1 already
  removed `store`/`project_id`/`project_binding_id` from it, and that was never this finding.
- **The only issuer that exists anywhere is test-confined.**
  `tests/fixtures/runtime_world.py::test_only_trusted_runtime_root` imports
  `_PROVISIONING_SENTINEL` directly from `runtime.bootstrap`. Python does not enforce
  leading-underscore privacy across an import boundary, and that is used here deliberately and
  by an honestly named function: it is exactly the "explicitly injected test issuer that is
  structurally unavailable to the live path" the Structural Review's own text permits. The
  shipped package cannot reach it, because production code importing any `tests.*` module is
  itself statically forbidden and proved so.
- **Static conformance proves it mechanically.** An AST walk over every `.py` file in the
  *installed* `manosube_agent_civilization` package asserts (a) no `ast.Call` resolving to
  `TrustedRuntimeRoot` exists outside that dataclass's own class body, (b) the name
  `provision_trusted_runtime_root` appears in no code position (definition, name, attribute,
  import alias, or `__all__` string) in any shipped file, and (c) no public callable this
  package exports declares `TrustedRuntimeRoot` as its return type — so a same-shaped function
  under a different name is caught too.

**Scope, stated exactly and not implied away.** This repository has genuinely no live
deployment, CLI, or agent-runtime composition boundary wired to Runtime (Phase 16+ is not
authorized; `RUNTIME_CREDENTIAL_USE_AUTHORITY=false`, `LIVE_EXTERNAL_WRITE_AUTHORITY=false`).
What is proved here is therefore:

```text
NO SHIPPED MINTING PATH EXISTS AT ALL, IN THIS PHASE
```

and **not**:

```text
THE LIVE PATH RESISTS AN ATTACKER AT RUNTIME
```

There is no live path yet to resist one. When a future, separately authorized Phase wires a real
deployment composition boundary, *that* boundary will mint roots, and "can it be tricked into
naming an alternate world?" becomes a real question requiring its own real control. This round
establishes only that the decision cannot be made *here*, by a shipped library function, on
behalf of whatever Store a caller happened to pass. Deciding which root is canonical remains the
future deployment's own responsibility, exactly as choosing which Store to open always was.

**The reversed counterexample, proved dynamically rather than asserted.**
`tests/integration/runtime/test_runtime_no_shipped_minting_path.py` builds both worlds for real
— the canonical one, and the fully self-consistent alternate one Round 1 already built (its own
external Human Authority, its own Ed25519 key, its own committed grants, declarations, and
subjects) — and first confirms the alternate world genuinely *is* internally legitimate, by
bootstrapping a real capability inside it through the test-only issuer. So the control is not
vacuous: that world is exactly the kind Round 1's factory would have accepted. It then proves
that nothing in the shipped surface (`runtime/__init__.py`, `bootstrap.py`,
`bootstrap_projection_execution_capability`, `route.py`) offers any way to reach or mint a root
over it — not because that particular world is specially blocked, but because shipped minting
does not exist — and that `observe_runtime_target`, the one public route a real deployment
reaches today, names neither `TrustedRuntimeRoot` nor the capability bootstrap at all, so there
is no ambient live path that could be steered into minting one.

### 11.2 P15-R2-F2 -- the deployment declaration is signed, revocable, and bound to the Boot-restored Human Authority

*Claimed (Round 1):* the declared deployment identity is anchored to "a genuinely pre-committed,
content-addressed, Human-Authority-declared record".

*True:* it was content-addressed, but the "Human-Authority-declared" half was a *self-assertion*.
The record carried a caller-supplied `human_authority_ref` and no signature, no signed payload,
no Authority Decision, and no `status`/validity of any kind; its identity functions merely
content-addressed that self-asserted body. Any Store-writing caller could construct a
declaration naming any Human Authority and any deployment fingerprint.
`route._resolve_deployment_declaration` schema-validated and recomputed the content address but
— as §10.6's own "Deliberately not added, disclosed" paragraph stated — did not compare the
declaration's `human_authority_ref` against the Human Authority freshly restored by Boot, and
performed no cryptographic verification at all. So an old-authority declaration remained
accepted after a legitimate Human Authority re-binding, and a fabricated-but-internally-
consistent record could anchor whatever fingerprint an attacker's own endpoint echoed.

*Now:*

```text
01_SCHEMA/runtime/runtime_deployment_declaration.schema.json
  ... + status     {"enum": ["ACTIVE", "REVOKED"]}                      required
      + signature  {"algorithm": const "ed25519",                       required
                    "key_id": <common/identity.schema.json>,
                    "value": "^[0-9a-f]{128}$"}
```

The `signature` `$def` is byte-for-byte the shape
`01_SCHEMA/binding/github_projection_grant_declaration.schema.json` already uses — a sibling
record kind's identical convention, reused rather than reinvented. The canonical schema count was
unchanged at `58` by *this* round: it adds fields to an existing schema file, never a new one, so
`scripts/validate_schemas.py`'s asserted inventory was deliberately left alone. (Round 3 adds one
new file and the asserted count becomes `59` — see §12.1.)

**Identity and signature are one derivation.** `runtime/identity.py` gains
`runtime_deployment_declaration_signing_payload(record) -> bytes` over a closed tuple of adopted
semantic fields, and `runtime_deployment_declaration_id` /
`runtime_deployment_declaration_semantic_fingerprint` are now computed over *that payload's own
bytes* — exactly how `binding/identity.py`'s `human_grant_declaration_id` is computed over
`human_grant_declaration_signing_payload`. The content address and the signed message therefore
cannot drift apart into two different notions of "what this record declared". The payload covers
every field except three: the record's own two digests (an identity cannot be computed over
itself) and `signature` (a signature cannot cover its own value) — the identical three
exclusions, for the identical reasons, that `binding/identity.py`'s own payload tuples make.
`status` participates, so a revocation cannot validate under a signature issued for an ACTIVE
declaration; `declared_at` participates, so a signature always bound *when*.

**Verification composes the shared primitive; it does not reimplement it.** A new module,
`runtime/deployment_declaration.py`, owns
`verify_runtime_deployment_declaration_signature(record, *, signing_key)`. It imports
`binding.signature.verify_ed25519_signature` (this repository's one public, fail-closed-as-a-
value Ed25519 primitive) and `binding.signature.SUPPORTED_SIGNATURE_ALGORITHM`, and restates only
the three-check composition around them — algorithm match, `key_id` match, then the primitive —
because `binding/signature.py`'s own equivalent composition is module-private. It holds no
private key, mints no signature, imports no `cryptography` surface of its own, and reaches no key
server, environment variable, or network; static conformance proves each of those. It lives in
`runtime/` rather than `binding/` deliberately: **Binding must never import anything from
`runtime/`** — Runtime is an adapter layer that depends on the Kernel's Binding element, never the
reverse, and adding a Phase 15 record kind's verifier to `binding/` would invert that dependency.

**Three new refusals in `route._resolve_deployment_declaration`,** after its existing
resolve/schema-validate/tamper-check/field-restatement checks and in this order:

```text
1. status must be "ACTIVE"                          a REVOKED declaration anchors nothing
2. human_authority_ref must equal the exact          a legitimate Human Authority re-binding
   reference THIS call's own Boot just restored      invalidates old declarations; there is no
                                                     silent carry-forward
3. signature must verify against the exact           never a caller-supplied copy of the key,
   human_authority_signing_key THAT SAME Boot        never a key read from the declaration
   restored from the current Project Binding         itself, never a cached one
```

Each is a `RuntimeRequirementError` raised **before any adapter call, with zero commits** — the
identical "nothing was reached, so there is nothing to classify as `IDENTITY_MISMATCH`"
discipline §10.6 already established for this function's earlier checks.

**Round 1's disclosed omission is deliberately reversed.** §10.6 declined to require the
declaration's `human_authority_ref` to equal the Boot-verified Human Authority, on the stated
grounds that F6 did not name that constraint and that adding it would "silently invalidate every
previously declared deployment whenever a project is legitimately re-bound to a new Human
Authority — an operational semantics no adopted decision establishes". Round 2 adopts exactly
that operational semantics, explicitly: **a re-binding invalidates previously issued deployment
declarations for new observations, and a newly issued, newly signed declaration under the new
Binding is required.** That is now a stated, tested rule rather than an assumed one — the
invalidation is loud (a refusal with zero adapter calls) rather than silent, and the positive
control proving re-issuance works is part of the same suite.

**`RUNTIME_CREDENTIAL_USE_AUTHORITY` remains `false`.** This package still holds no secret and
signs nothing. A real Human's private key never touches this system at all — the only key ever
consulted is the *public* verification key a real, Store-resolved, Boot-restored Project Binding
record already carries, which is precisely what `binding/signature.py`'s own module docstring has
always said about the two declaration kinds Binding owns.

### 11.3 Judgment calls made in this round that the adopted findings did not fully pin down

1. **Placement of the verification wrapper.** A new `runtime/deployment_declaration.py`, rather
   than folding it into `bootstrap.py` or `route.py`. `route.py` was rejected because static
   conformance pins "`binding` is imported only by `bootstrap.py`", and widening that to
   `route.py` would blur the route's own no-Authority-import discipline; `bootstrap.py` was
   rejected because it is the *provisioning* module and has nothing to do with observation. One
   small module with one public function keeps both existing facts intact and makes the new
   import admissible by name.

2. **Which canonical serializer the signing payload uses.** `state.canonicalize.
   canonical_json_bytes` — the serializer `runtime/identity.py` already uses for every other
   Runtime digest — rather than `difference.canonical.canonical_bytes`, which
   `binding/identity.py` uses for its own payloads. Both are canonical serializers this
   repository already owns; changing Runtime's would have silently changed every existing Runtime
   identity. The *convention* being reused from Binding is the closed-adopted-field-tuple and the
   one-derivation-for-address-and-signature discipline, not the specific byte encoder.

3. **The fixture signer has a canonical default.** `deployment_declaration_for` /
   `commit_target_identity` gained `status` (default `"ACTIVE"`) and `signer`/`signing_key_id`
   (default: the canonical fixture Human Authority's own key pair), rather than making every
   existing call site pass them explicitly. This mirrors the `signer: Any = None` default
   `commit_declaration` already carries in the same fixture module: a test that wants a
   legitimate declaration gets one, and every negative control passes an attacker's, an
   alternate world's, or a pre-re-binding key *explicitly*, so the intent is visible exactly
   where it matters.

4. **What "a re-binding" means here.** This repository has no separate re-bind route:
   `bind_project` owns genesis and genesis is strictly one-shot. A re-binding is therefore
   modelled as what it actually is in this Kernel — a genuinely new `project_binding` record,
   assembled through the *real* Binding producer (`assemble_project_binding`, the identical
   function `bind_project` itself calls), carrying a rotated `human_authority_signing_key` under
   the identical Human Authority, committed into the identical project. Because a Project Binding
   is content-addressed over its own `human_authority_ref`/`human_authority_signing_key`, that
   rotation necessarily mints a new `project_binding_id`, and Boot restores it exactly as it
   restores the original.

5. **The cross-Binding control's refusal point, disclosed.** Because Binding identity and signing
   key are inseparable (item 4), a declaration "genuinely valid under Binding A, presented while
   Binding B is Boot-restored" is refused at the `project_binding_ref` restatement check, *before*
   the signature check. The signature check is therefore isolated by a separate test — a
   declaration restating the new Binding correctly, naming the correct current Human Authority,
   ACTIVE, and content-address-reproducing, whose signature alone is by the pre-re-binding key.
   Both cases are proved; neither stands in for the other.

6. **The test-only issuer's name.** `test_only_trusted_runtime_root`, so no call site can read as
   a production entry point. It carries `__test__ = False` so pytest does not collect it as a test
   case in the modules that import it.

### 11.4 Round 2 declarations

```text
TRUSTED_RUNTIME_ROOT_TYPE_RETAINED=true
TRUSTED_RUNTIME_ROOT_DIRECTLY_CONSTRUCTIBLE=false
SHIPPED_TRUSTED_RUNTIME_ROOT_MINTING_PATH_EXISTS=false
SHIPPED_FUNCTION_RETURNING_A_TRUSTED_RUNTIME_ROOT_EXISTS=false
TRUSTED_RUNTIME_ROOT_ISSUER_IS_TEST_ONLY=true
TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT=0
NO_SHIPPED_MINTING_PATH_PROVEN_BY_AST_WALK_OVER_INSTALLED_PACKAGE=true
LIVE_PATH_ADVERSARIAL_RESISTANCE_PROVEN=false
LIVE_DEPLOYMENT_COMPOSITION_BOUNDARY_EXISTS=false
DEPLOYMENT_DECLARATION_HUMAN_AUTHORITY_SIGNED=true
DEPLOYMENT_DECLARATION_STATUS_ENFORCED=true
DEPLOYMENT_DECLARATION_BOUND_TO_BOOT_RESTORED_AUTHORITY=true
DEPLOYMENT_DECLARATION_SIGNING_PAYLOAD_EQUALS_CONTENT_ADDRESS_PAYLOAD=true
DEPLOYMENT_DECLARATION_SURVIVES_A_HUMAN_AUTHORITY_REBINDING=false
ED25519_VERIFICATION_REIMPLEMENTED_IN_RUNTIME=false
BINDING_IMPORTS_RUNTIME=false
RUNTIME_HOLDS_A_PRIVATE_SIGNING_KEY=false
RUNTIME_MINTS_A_SIGNATURE=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
CANONICAL_SCHEMA_COUNT_CHANGED=false
NEW_RUNTIME_STORE_COMMITTED_RECORD_KINDS=0
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
```

### 11.5 Round 2 proof layers

```text
tests/contract/runtime/test_runtime_static_conformance.py       F1 (no shipped minting call
                                                                   site; deleted name absent
                                                                   from every code position; no
                                                                   public callable returns the
                                                                   type) and F2 (binding.
                                                                   signature admitted for
                                                                   exactly one module; that
                                                                   module reimplements no
                                                                   cryptography and signs
                                                                   nothing)
tests/integration/runtime/test_runtime_no_shipped_minting_path.py
                                                                F1 (the reversed counterexample,
                                                                   both worlds built for real,
                                                                   with the explicit scope
                                                                   caveat in its own docstring)
tests/integration/runtime/test_runtime_trusted_root.py          F1 (Round 1's own controls, now
                                                                   minted through the test-only
                                                                   issuer)
tests/integration/runtime/test_runtime_bootstrap_continuity.py  F1 (V5 continuity, unchanged in
                                                                   substance, re-rooted on the
                                                                   test-only issuer)
tests/unit/runtime/test_runtime_identity.py                     F2 (one derivation for address,
                                                                   fingerprint, and signed
                                                                   message; the three exclusions;
                                                                   status/declared_at sensitivity)
tests/integration/runtime/test_runtime_deployment_identity_anchor.py
                                                                F2 (unsigned, self-authored,
                                                                   wrong-signer, wrong-Authority,
                                                                   REVOKED, tampered-after-
                                                                   signing in both directions,
                                                                   cross-Binding, the full
                                                                   re-binding scenario, and the
                                                                   non-vacuity controls for the
                                                                   preserved replay/cross-project
                                                                   cases)
```

## 12. Structural Review Round 3 corrections (P15-R3-F1, P15-R3-F2)

```text
ROUND=3
GOVERNING_REVIEW=PR #65 Structural Review Round 3
FINDINGS_ADOPTED=2
FINDINGS_CLOSED=2
REOPENED_FROM_ROUND_2=P15-R2-F1 (now P15-R3-F1), P15-R2-F2 (now P15-R3-F2)
ROUND_1_FINDINGS_CONFIRMED_CLOSED=P15-R1-F1, P15-R1-F2, P15-R1-F3, P15-R1-F5
ROUND_2_FINDINGS_CONFIRMED_CLOSED=P15-R2-F2's own signature/Boot-binding half
```

Round 3 confirmed Round 1's F1/F2/F3/F5 closed and confirmed the signature-and-Boot-binding half
of Round 2's own F2 closed, then reopened both of Round 2's corrections for what each still left
open. Both are recorded below in the same *what was claimed / what was true / what the code now
does* form, with the same rule as every earlier round: **where this section and an earlier one
differ, this section governs.**

### 12.1 P15-R3-F1 -- the trusted root now has a legitimate shipped issuer, because holding a root no longer grants anything

*Claimed (Round 2):* deleting the public minting factory closed the finding, and real issuance
could be deferred to "a future Phase" because shipped code minting no root at all is the
strongest correction available at the library level.

*True:* the correction failed in **both** directions at once.

- **No production-legitimate path existed.** Issue #64 assigns this production
  runtime-provisioning boundary to *this* Phase. A bootstrap with no supported way for a real
  deployment to obtain its own required first argument does not satisfy this Phase's own V5
  requirement, and the deferral is rejected outright.
- **The "private" sentinel was not actually unreachable.** The test-only issuer's structural
  unavailability was illusory: it worked by importing `bootstrap._PROVISIONING_SENTINEL` and
  calling `TrustedRuntimeRoot(..., sentinel)` directly. Python's leading-underscore convention is
  not access control, so *any* in-process caller able to import the shipped module could do the
  identical thing over an arbitrary Store.

*Now:* a new canonical record kind, and a mandatory check folded into the capability call itself.

```text
01_SCHEMA/runtime/runtime_root_admission.schema.json
  schema_version, runtime_root_admission_id (content-addressed,
  ^RUNTIME-ROOT-ADMISSION-[0-9A-F]{64}$), runtime_root_admission_semantic_fingerprint,
  project_id, project_binding_ref (kind project_binding), status {ACTIVE|REVOKED},
  declared_at, signature {algorithm ed25519, key_id, value}
```

The `signature` `$def` is byte-for-byte the shape `runtime_deployment_declaration.schema.json`
already uses, which is itself the shape
`01_SCHEMA/binding/github_projection_grant_declaration.schema.json` established -- a sibling
record kind's identical convention, reused rather than reinvented for the third time.

**Identity and signature are one derivation**, exactly as for a deployment declaration.
`runtime/identity.py` gains `runtime_root_admission_signing_payload(record) -> bytes` over
`ROOT_ADMISSION_SEMANTIC_FIELDS`, and `runtime_root_admission_id` /
`runtime_root_admission_semantic_fingerprint` are both computed over that payload's own bytes.
The payload excludes exactly three fields, the identical three and for the identical reasons:
the record's own two digests, and `signature`.

**What the record deliberately does *not* carry, and why that absence is the whole design.**
There is no `human_authority_ref` field on this record, and no field naming any key. Its
signature is **never** verified against the target project's own Boot-restored
`human_authority_signing_key`, or against anything else resolvable from inside the Store being
admitted. That would be self-referential again: an attacker's fully self-consistent alternate
world -- its own Human Authority, its own Ed25519 signing key, its own Project Binding, every
record internally valid on its own terms -- would simply self-sign a matching admission record
with its *own* internally-legitimate key and pass. The entire point of this record kind is that
the key that decides is one the admitted Store cannot produce.

**The verification wrapper** is a new module, `runtime/root_admission.py`, owning
`verify_runtime_root_admission_signature(record, *, trust_anchor_public_key_hex)`. It imports
`binding.signature.verify_ed25519_signature` and `SUPPORTED_SIGNATURE_ALGORITHM` and restates
only the same short composition around them -- never reimplementing Ed25519 -- exactly as
`runtime/deployment_declaration.py` already does, and for the identical dependency-direction
reason (`binding/` must never import anything from `runtime/`). Note the deliberate parameter
difference from its sibling: this one takes a **caller-supplied public key hex string**, not a
`signing_key` mapping resolved from a Store.

**The check is folded into `bootstrap_projection_execution_capability` itself**, not offered as a
separate pre-step whose result a caller could discard or bypass:

```python
bootstrap_projection_execution_capability(
    trusted_runtime_root: TrustedRuntimeRoot,
    *,
    runtime_root_admission_ref: Mapping[str, str],
    trust_anchor_public_key_hex: str,
    github_projection_grant_refs,
    github_projection_grant_declaration_refs,
) -> ProjectionExecutionCapability
```

Immediately after Boot and before any grant or declaration is resolved, it resolves
`runtime_root_admission_ref` **from the root's own Store**; independently recomputes the resolved
record's id and semantic fingerprint and refuses on mismatch; requires `status == "ACTIVE"`;
requires the admission's own `project_id` / `project_binding_ref` to **exactly** equal the root's
own `project_id` / `project_binding_id` (so one admission artifact anchors exactly one project
and one Binding, never an unbounded trust grant reusable across arbitrary Stores); and requires
`verify_runtime_root_admission_signature(..., trust_anchor_public_key_hex=...)` to be true. Every
refusal is a `RuntimeRequirementError` reached with **zero adapter calls and zero authorization
evaluations**, regardless of how `trusted_runtime_root` itself was constructed.

**`trust_anchor_public_key_hex`, stated exactly.** It is a required keyword argument sourced
**exclusively from deployment/composition-time configuration** -- never from the Store being
admitted, never derived from anything on the request path, and never hardcoded as a specific
real-world key inside shipped source (proved by an AST walk for any 64-hex string constant
anywhere in the shipped `runtime` package). Who supplies it and how is a genuine deployment's own
responsibility. This repository still wires no live CLI/agent-runtime entrypoint that *calls*
this function for real -- that remains true -- but that is now a statement about invocation,
not about whether the mechanism itself is production-legitimate and shipped, which is what the
review requires. The mechanism is complete and correct; its live invocation by some future
deployment entrypoint is a separate, later concern.

#### 12.1.1 This is not a walk-back of Round 2 -- read this before reading the diff

A superficial read of this round's diff could mistake it for reverting Round 2's own correction.
It is the opposite, and the distinction is precise:

```text
BEFORE (Round 1 and Round 2)   POSSESSING A TrustedRuntimeRoot WAS SUFFICIENT to reach an
                               adapter. Every question therefore became "who may mint one?" --
                               which no shipped library function could answer, and which the
                               sentinel only appeared to answer.

AFTER  (Round 3)               POSSESSING A TrustedRuntimeRoot GRANTS NOTHING. The mandatory
                               admission-record-plus-external-anchor check inside
                               bootstrap_projection_execution_capability is what gates adapter
                               access now, and it reruns on EVERY call regardless of the root's
                               provenance. A directly constructed root -- via the old sentinel
                               import, via the public constructor, over any Store at all --
                               gets no benefit unless the caller can ALSO produce a
                               runtime_root_admission genuinely signed by the private key
                               matching whatever trust_anchor_public_key_hex the caller of
                               bootstrap_projection_execution_capability supplies.
```

Because the type is no longer a capability, restricting its construction protects nothing, and a
fake-private gate around a value that grants nothing would preserve exactly the illusion this
round named. The sentinel is therefore **dropped**, and `TrustedRuntimeRoot` becomes an ordinary
public frozen dataclass -- `TrustedRuntimeRoot(store, project_id, project_binding_id)` -- keeping
only its canonical-identity shape check on `project_id`/`project_binding_id` (a check on a
*name*, never a trust decision).

**Round 2's own mechanical facts are all still literally true, and all still asserted unchanged**
in `tests/contract/runtime/test_runtime_static_conformance.py`:

```text
provision_trusted_runtime_root appears in NO code position in any shipped file      still true
no shipped public callable declares TrustedRuntimeRoot as its return type           still true
no shipped module constructs a TrustedRuntimeRoot                                   still true
```

That none of those had to be weakened is itself the evidence that this is a different correction
rather than a reversal: the deleted factory is gone, no same-shaped function replaces it under
any name, and shipped code still mints nothing. What changed is that the caller constructing the
value directly is now harmless, because the value is inert.

#### 12.1.2 What is proved, and what is not

```text
A PRODUCTION-LEGITIMATE, SHIPPED PROVISIONING MECHANISM EXISTS                      proved
THE MECHANISM IS NOT REPRODUCIBLE BY A REQUEST-PATH CALLER WITHOUT THE ANCHOR KEY   proved
AN INTERNALLY SELF-CONSISTENT ALTERNATE WORLD CANNOT SELF-ADMIT                     proved
A LIVE DEPLOYMENT ENTRYPOINT CALLS THIS FUNCTION IN THIS REPOSITORY                 false, and
                                                                                    not claimed
```

The last line is unchanged from Round 2 and is stated here rather than implied away. What Round 3
changes is that it is no longer the *load-bearing* caveat: the earlier rounds' honest limitation
was "there is no legitimate way to obtain a root at all", which is a defect in the mechanism.
This round's remaining limitation is "no entrypoint in this repository invokes the mechanism
yet", which is a scheduling fact about later Phases.

### 12.2 P15-R3-F2 -- a deployment declaration now has a validity window, and revocation is genuinely effective

*Claimed (Round 2):* adding `status` (`ACTIVE`/`REVOKED`), a Human Authority signature, and a
Boot-restored-Authority cross-check made the deployment anchor sound.

*True:* two things were still missing.

- **No validity window, and no evaluation-instant binding.** The schema had no
  `valid_from`/`valid_until` at all, so a declaration signed once was signed forever.
- **Revocation was not actually effective.** Because the record is immutable and
  content-addressed, minting a *new* record with `status="REVOKED"` does **not** invalidate the
  original `ACTIVE` record: that record keeps its own unchanged id and remains individually
  resolvable, individually signature-valid, and individually accepted, forever. A target already
  referencing the old `ACTIVE` record's id can keep presenting that exact reference
  indefinitely. Round 2's own "revoked" regression test only proved that a *separately
  constructed* `REVOKED` record is refused -- it never proved an *already-issued* `ACTIVE`
  declaration could be revoked at all.

*Now:*

```text
01_SCHEMA/runtime/runtime_deployment_declaration.schema.json
  ... + valid_from   <common/timestamp.schema.json>     required
      + valid_until  <common/timestamp.schema.json>     required
```

Both participate in `DEPLOYMENT_DECLARATION_SEMANTIC_FIELDS`, and therefore in the record's own
content address, its own semantic fingerprint, **and** the Human Authority's own signature -- the
identical single-derivation discipline `declared_at` and `status` already follow. A declaration
cannot be re-dated after signing without breaking its own identity and its own signature both.
`route._resolve_deployment_declaration` parses both bounds as real UTC instants through this
module's own existing `_instant` helper and requires `valid_from <= observed_at <= valid_until`,
inclusive at both ends -- exactly the convention `_require_within_time_window` already applies to
the Observation Boundary's own window.

**Effective revocation: a canonical, Store-resolved current-declaration pointer.** "Current"
stops meaning *whatever the caller happens to reference* and starts meaning *whatever Project
State's own pointer names*:

```text
semantic_state.runtime.claims[<target_key>]  ->  runtime_deployment_declaration_id
```

`<target_key>` is `runtime_deployment_target_key(...)`: a stable `RUNTIME-DEPLOYMENT-TARGET-<64
hex>` digest over the canonical projection of exactly four fields --
`project_binding_ref`, `provider`, `deployment_id`, `instance_identity`.

A new shipped module, `runtime/deployment_registry.py`, owns the pointer and the one sanctioned
way to move it: `commit_runtime_deployment_declaration(store, project_id, declaration, *,
committed_at)`. In **one** atomic `commit_state_transition` call -- mirroring `route.py`'s own
`_commit_envelope` pattern exactly, including its bounded Compare-And-Swap retry -- it commits
the new immutable record *and* sets `semantic_state.runtime.claims[<target_key>]` to that
record's own id. There is no call shape through which one half happens without the other.

Issuing **any** new declaration for a given target therefore atomically supersedes whatever the
pointer named before -- whether the new record's own `status` is `ACTIVE` (a rotation) or
`REVOKED` (a revocation), and regardless of whether the old record is still individually
resolvable and still inside its own validity window.

**`_resolve_deployment_declaration` gains two further requirements**, after every check Rounds 1
and 2 established (all still required, unchanged) and in this order:

```text
4. valid_from <= observed_at <= valid_until          real UTC instants, inclusive both ends
5. semantic_state.runtime.claims[<target_key>]       read fresh from Store State; a MISSING
   must exactly equal this declaration's own id      pointer refuses for the same reason a
                                                     pointer naming a DIFFERENT id does
```

Both are `RuntimeRequirementError` before any adapter call, with zero commits -- the identical
"nothing was reached, so there is nothing to classify as `IDENTITY_MISMATCH`" discipline §10.6
established for this function's earlier checks.

**The post-check-substitution barrier.** The pointer is re-proved on **every** commit attempt
inside `_commit_envelope`'s existing retry loop, against State loaded fresh at that attempt --
deliberately reusing the per-attempt-rather-than-once-before-the-loop discipline P15-R1-F5
already established for the authority-defining context, rather than adding a second, parallel
freshness mechanism. So a legitimate supersession landing *after* this route's own resolution but
*before* the Envelope is actually committed refuses, rather than persisting an Envelope anchored
to a declaration that was current when checked and is no longer current at commit time.

**Why `semantic_state.runtime.claims`, and what it does not disturb.** That property is already
part of the canonical, adopted `01_SCHEMA/state/semantic_state.schema.json` -- a `$defs/domain`
whose `claims` is an open `{string: scalar}` map -- and Phase 15 had, until this round, never
written to the `runtime` domain at all (`route._commit_envelope` bumps
`state_revision`/`lineage_head_ref`/`semantic_fingerprint` and touches `semantic_state`
nowhere). Recording a `{target_key: declaration_id}` mapping there requires **no schema change of
any kind**. `deployment_registry` deep-copies the existing `semantic_state`, sets exactly one
key inside exactly one domain's `claims`, and carries everything else through byte-identical --
the `runtime` domain's own `status` (`BLOCKED` at genesis), `identity_refs`, `evidence_refs`, and
`blind_spots` included, and every other domain untouched. The scope is deliberately as narrow as
`reflow/bookkeeping.py`'s own single sanctioned `semantic_state` mutation.

### 12.3 Judgment calls made in this round that the adopted findings did not fully pin down

1. **Public root construction: the sentinel is dropped rather than replaced by a constructor
   function.** The adopted finding permitted either. Dropping it was chosen because reintroducing
   a named factory -- even under a new name -- is exactly the shape Round 2 deleted, and would
   read as a restoration whatever its docstring said; whereas making the dataclass ordinary keeps
   **all three** of Round 2's static assertions literally true and unweakened (§12.1.1), which is
   itself the clearest available evidence that this is not a reversal. It also states the
   architectural fact directly: there is nothing to mint, because there is nothing to confer.

2. **Placement of the two new modules.** `root_admission.py` mirrors
   `deployment_declaration.py`'s own placement decision exactly (§11.3, item 1) and for the same
   reasons; folding it into that module was rejected because that module is named for, and
   documents itself as being about, a different record kind. `deployment_registry.py` is separate
   from both `route.py` (which would then hold two `commit_state_transition` call sites and blur
   its own "one commit per observation" fact) and `deployment_declaration.py` (whose own
   docstring states it verifies only and holds no commit path). The static conformance proof was
   updated to admit exactly one further `commit_state_transition` call site, by name, with that
   rationale recorded at the test.

3. **`commit_runtime_deployment_declaration` is exported from `runtime/__init__.py`.** The
   finding requires it to be "genuinely new production code, not test-only", and a canonical
   committer a real deployment must call to issue, rotate, or revoke a declaration is not
   production code if it is reachable only through a private submodule. It is a **committer, not
   a route**: `PUBLIC_RUNTIME_ENTRY_POINT_COUNT` stays `3`, exactly as Round 1 declared
   `TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT` separately rather than inflating the
   route count, and a separate `RUNTIME_DEPLOYMENT_DECLARATION_COMMIT_ENTRY_POINT_COUNT=1` is
   declared in §12.4.

4. **`committed_at` is a required keyword argument on the committer.** The brief's own sketch
   signature omitted it. It is required here because every route and committer in this repository
   reads no clock, and silently defaulting a commit instant would be this package's first
   exception to that discipline.

5. **The target key excludes `deployment_fingerprint`.** The finding's own enumeration named four
   fields while `_DECLARATION_ANCHORED_TARGET_FIELDS` restates five. The four-field reading is
   adopted, and the exclusion is load-bearing rather than incidental: a `deployment_fingerprint`
   says *what this target currently is*, not *which target this is*. A legitimate rotation
   re-declares the identical provider/deployment/instance under a new fingerprint and must
   **supersede** its predecessor; if the fingerprint were part of the key, every rotation would
   fork the pointer space and leave the superseded declaration permanently current for its own
   old key -- reintroducing exactly the ineffective-revocation defect this round closes.

6. **A missing pointer refuses, and is not treated as a lesser case than a moved one.** A
   declaration that was never made current through the canonical path was never admitted as this
   target's own current deployment identity at all -- which is precisely the "anyone who can
   write a Store record can anchor anything" gap the pointer exists to close. Both refusals carry
   distinct messages, and both are proved.

7. **The post-check-substitution barrier extends the existing retry loop rather than adding a new
   mechanism.** No new error class was introduced: the refusal is a `RuntimeRequirementError`,
   like every other declaration-anchoring refusal on this route, rather than a sibling of
   `RuntimeAuthorityFreshnessError`. The distinction Round 1 drew when it *did* add a class still
   holds -- that one names a change in *whose authority* is in force, which is a different kind of
   fact from *which declaration is current for this target*, and folding the two into one
   vocabulary would make both less honest.

8. **The Round 2 "unsigned declaration" control now plants its record raw.** The canonical
   committer schema-validates before it commits, so an unsigned record cannot pass through it --
   correctly. That control therefore inserts the record directly, and the route's own schema
   refusal (which precedes the currency check) is still exactly the refusal it asserts. The same
   applies to the two tamper controls, unchanged since Round 1.

9. **The `wrong-current-record` control's refusal point, disclosed.** Because a declaration
   restates the very fields the target key is derived from, a record belonging to *another
   target's* history necessarily fails the P15-R1-F6 field-restatement check *before* the
   currency check is reached -- the identical kind of disclosure §11.3 item 5 made for the
   cross-Binding control. The currency check is isolated instead by the superseded, replayed, and
   revoked-after-issuance controls, whose declarations restate this target perfectly and are
   refused for no other reason. Both are proved; neither stands in for the other.

10. **The hardcoded-anchor-key scan is scoped to the `runtime` package.** A repository-wide AST
    walk for 64-hex string constants would be noise rather than a control: such constants are
    legitimate and numerous elsewhere (canonical record digests in Reflow's own invariant
    registry, for one). This package is where an anchor key would plausibly be pasted, and this
    package contains none.

### 12.4 Round 3 declarations

```text
TRUSTED_RUNTIME_ROOT_TYPE_RETAINED=true
TRUSTED_RUNTIME_ROOT_DIRECTLY_CONSTRUCTIBLE=true
TRUSTED_RUNTIME_ROOT_IS_A_CAPABILITY=false
POSSESSING_A_TRUSTED_RUNTIME_ROOT_GRANTS_ADAPTER_ACCESS=false
PROVISIONING_SENTINEL_EXISTS=false
SHIPPED_TRUSTED_RUNTIME_ROOT_MINTING_PATH_EXISTS=false
SHIPPED_FUNCTION_RETURNING_A_TRUSTED_RUNTIME_ROOT_EXISTS=false
DELETED_ROUND_1_MINTING_FACTORY_REINTRODUCED=false
RUNTIME_ROOT_ADMISSION_REQUIRED_FOR_PROVISIONING=true
RUNTIME_ROOT_ADMISSION_VERIFIED_AGAINST_AN_EXTERNALLY_SUPPLIED_ANCHOR=true
RUNTIME_ROOT_ADMISSION_VERIFIED_AGAINST_STORE_RESOLVABLE_KEY_MATERIAL=false
RUNTIME_ROOT_ADMISSION_CARRIES_A_HUMAN_AUTHORITY_REF=false
RUNTIME_ROOT_ADMISSION_ANCHORS_EXACTLY_ONE_PROJECT_AND_BINDING=true
TRUST_ANCHOR_HARDCODED_IN_SHIPPED_SOURCE=false
TRUST_ANCHOR_SOURCED_FROM_DEPLOYMENT_CONFIGURATION=true
ADMISSION_CHECK_PRECEDES_EVERY_GRANT_RESOLUTION_AND_AUTHORIZATION=true
PRODUCTION_LEGITIMATE_PROVISIONING_MECHANISM_SHIPPED=true
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false
LIVE_PATH_ADVERSARIAL_RESISTANCE_PROVEN=false
DEPLOYMENT_DECLARATION_VALIDITY_WINDOW_REQUIRED=true
DEPLOYMENT_DECLARATION_VALIDITY_WINDOW_SIGNED_AND_CONTENT_ADDRESSED=true
DEPLOYMENT_DECLARATION_WINDOW_BOUNDS_INCLUSIVE=true
DEPLOYMENT_DECLARATION_CURRENT_POINTER_IS_STORE_RESOLVED=true
DEPLOYMENT_DECLARATION_REVOCATION_IS_EFFECTIVE=true
ALREADY_ISSUED_ACTIVE_DECLARATION_CAN_BE_REVOKED=true
SUPERSEDED_DECLARATION_STILL_INDIVIDUALLY_RESOLVABLE=true
SUPERSEDED_DECLARATION_STILL_ANCHORS_AN_OBSERVATION=false
CURRENT_POINTER_RECHECKED_ON_EVERY_COMMIT_ATTEMPT=true
SEMANTIC_STATE_SCHEMA_CHANGED=false
NEW_RUNTIME_STORE_COMMITTED_RECORD_KINDS=2
CANONICAL_SCHEMA_COUNT_CHANGED=true
CANONICAL_SCHEMA_COUNT=59
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
RUNTIME_DEPLOYMENT_DECLARATION_COMMIT_ENTRY_POINT_COUNT=1
ED25519_VERIFICATION_REIMPLEMENTED_IN_RUNTIME=false
BINDING_IMPORTS_RUNTIME=false
RUNTIME_HOLDS_A_PRIVATE_SIGNING_KEY=false
RUNTIME_MINTS_A_SIGNATURE=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
```

### 12.5 Round 3 proof layers

```text
tests/unit/runtime/test_runtime_identity.py                     F1 (the admission record's own
                                                                   one derivation for address,
                                                                   fingerprint and signed
                                                                   message; the three exclusions;
                                                                   collision sensitivity in every
                                                                   field; the load-bearing
                                                                   absence of any Human Authority
                                                                   or key field) and F2 (the
                                                                   target key derived identically
                                                                   from both sides, sensitive to
                                                                   every field that names a
                                                                   different target, and
                                                                   deliberately insensitive to
                                                                   deployment_fingerprint; the
                                                                   validity window's own payload
                                                                   sensitivity)
tests/contract/runtime/test_runtime_static_conformance.py       F1 (the three Round 2 facts, all
                                                                   still asserted unweakened; the
                                                                   two new bootstrap keyword
                                                                   arguments and the still-absent
                                                                   store/project/binding ones; no
                                                                   64-hex constant anywhere in
                                                                   the shipped runtime package;
                                                                   the admission call site
                                                                   precedes every grant
                                                                   resolution and authorization
                                                                   call inside the function's own
                                                                   AST) and F2 (exactly two
                                                                   commit_state_transition call
                                                                   sites in this package, both
                                                                   named; still no direct
                                                                   store.commit anywhere)
tests/integration/runtime/test_runtime_root_admission.py        F1 (the genuine positive path end
                                                                   to end under an independent
                                                                   anchor; a directly constructed
                                                                   root with no admission and
                                                                   with a self-signed one, both
                                                                   zero-authorization; the
                                                                   alternate world self-signing
                                                                   with its OWN internally
                                                                   legitimate Human Authority
                                                                   key, refused; wrong project;
                                                                   wrong Binding; revoked;
                                                                   tampered in both directions;
                                                                   cross-Store; malformed and
                                                                   wrong anchors)
tests/integration/runtime/test_runtime_deployment_identity_anchor.py
                                                                F2 (stale; expired; both
                                                                   inclusive-bound positives;
                                                                   re-dating after signing;
                                                                   revoked-after-issuance;
                                                                   the revoking record's own
                                                                   status refusal; superseded by
                                                                   rotation; replayed-old-ACTIVE;
                                                                   wrong-current-record; never
                                                                   registered at all; and the
                                                                   post-check-substitution
                                                                   barrier)
tests/integration/runtime/test_runtime_trusted_root.py          F1 (Round 2's own (a)-group
                                                                   inverted deliberately and
                                                                   visibly: public construction
                                                                   succeeds, and holding a root
                                                                   confers nothing)
tests/integration/runtime/test_runtime_no_shipped_minting_path.py
                                                                F1 (every Round 2 fact that
                                                                   survives, still asserted, plus
                                                                   the Round 3 successor to its
                                                                   one obsolete test)
tests/integration/runtime/test_runtime_bootstrap_continuity.py  F1 (V5 continuity, unchanged in
                                                                   substance, re-rooted on a
                                                                   genuinely admitted root)
tests/fixtures/runtime_world.py                                 F2 (every fixture-side
                                                                   declaration commit migrated to
                                                                   the shipped canonical
                                                                   commit-and-supersede path, so
                                                                   every positive-path test in
                                                                   this repository genuinely
                                                                   populates the pointer)
```

## 13. Structural Review Round 4 corrections (P15-R4-F1, P15-R4-F2)

```text
ROUND=4
GOVERNING_REVIEW=PR #65 Structural Review Round 4
FINDINGS_ADOPTED=2
FINDINGS_CLOSED=2
REOPENED_FROM_ROUND_3=P15-R3-F1 (now P15-R4-F1), P15-R3-F2 (now P15-R4-F2)
ROUND_1_FINDINGS_CONFIRMED_CLOSED=P15-R1-F1, P15-R1-F2, P15-R1-F3, P15-R1-F5, P15-R1-F6
ROUND_2_FINDINGS_CONFIRMED_CLOSED=P15-R2-F2's own signature/Boot-binding half
ROUND_3_FINDINGS_CONFIRMED_CLOSED=the validity-window half of P15-R3-F2
```

Round 4 confirmed every earlier round's remaining corrections closed and reopened both of
Round 3's, on the review's own explicit observation that **the same trust-boundary semantic class
has now recurred across Rounds 1-4**. Where this section and an earlier one differ, this section
governs -- the same rule every earlier round states.

The recurrence is worth naming precisely, because it is what shapes both corrections below:

```text
ROUND 1   the trust decision was a PARAMETER LIST      -> replaced by a TYPE
ROUND 2   the trust decision was a PUBLIC FACTORY      -> replaced by a PRIVATE SENTINEL
ROUND 3   the trust decision was POSSESSION OF A TYPE  -> replaced by a SIGNED ADMISSION RECORD
                                                          verified against a CALLER-SUPPLIED
                                                          anchor
ROUND 4   the trust decision was STILL A PARAMETER --   -> replaced by an OWNERSHIP BOUNDARY: the
          the caller supplied both the admission and       values that decide are owned by a
          the anchor it was signed under, so a caller       composition step, and the
          who brought a matching attacker anchor           request-facing signature has no
          along with a self-consistent alternate world     parameter for any of them
          passed every check
```

Each earlier round moved the decision somewhere a caller could still reach. Round 4's correction
is the first that is not a check at all: it is about *who owns which value*, and it is enforced
by the absence of parameters rather than by their validation.

### 13.1 P15-R4-F1 -- the trust anchor is composition-owned, and absent from every request-facing signature

*Claimed (Round 3):* requiring a canonical, Store-committed, ACTIVE `runtime_root_admission`
verified against an externally supplied `trust_anchor_public_key_hex` made possession of a trust
root worthless, and therefore closed the finding.

*True:* every one of those checks was real and every one still runs -- but they were performed
against material **the caller of the request-facing function supplied**:

```python
bootstrap_projection_execution_capability(
    TrustedRuntimeRoot(attacker_store, attacker_project, attacker_binding),
    runtime_root_admission_ref=<the attacker's own ACTIVE, correctly signed admission>,
    trust_anchor_public_key_hex=<the attacker's own matching public key>,
    github_projection_grant_refs=[...],
    github_projection_grant_declaration_refs=[...],
)   # every check passes -- the attacker supplied both sides of the question
```

A caller who can name the anchor *is* the trust decision, whatever the record in between proves.

*Now:* provisioning is two owned halves, and the ownership is the correction.

```text
TRUSTED_DEPLOYMENT_COMPOSITION
  owns:  canonical Store handle, project_id, project_binding_id, root-admission selection,
         configured trust-anchor identity/public key
  runs:  ONCE, at deployment composition, before any request boundary exists

REQUEST_FACING_BOOTSTRAP
  may supply:      operation/grant/declaration references allowed by the frozen API
  must not supply: Store, project_id, project_binding_id, trust anchor or its fingerprint,
                   root-admission reference or body, Human Authority signing key
```

```python
# bootstrap.py -- the one shipped trusted-composition entry point
compose_trusted_runtime_deployment_authority(
    store, *, project_id, project_binding_id,
    runtime_root_admission_ref, trust_anchor_public_key_hex,
) -> RuntimeDeploymentAuthority

# bootstrap.py -- request-facing; five parameters are GONE, not validated
bootstrap_projection_execution_capability(
    deployment_authority: RuntimeDeploymentAuthority,
    *, github_projection_grant_refs, github_projection_grant_declaration_refs,
) -> ProjectionExecutionCapability
```

`RuntimeDeploymentAuthority` is an opaque, frozen, slotted capability. It binds the Store, the
project, the Project Binding, the exact admitted `runtime_root_admission_id`, and that
admission's own `generation`; it exposes **no** public accessor of any kind (`dir()` over the
type yields nothing public), its `__repr__` deliberately reveals nothing, and the raw anchor is
**discarded** at composition rather than retained -- proved by walking everything reachable from a
composed instance and asserting the anchor hex appears nowhere in it.

Composition performs every Round 3 admission check, in this order, and adds Round 4's own
currency requirement last:

```text
1. runtime_root_admission_ref is a well-formed reference of the right kind
2. it resolves in the bound Store; the record is schema-valid; its own recomputed content
   address and semantic fingerprint equal its own declared values
3. status == "ACTIVE"
4. its project_id / project_binding_ref exactly equal the ones being composed
5. its signature verifies against the deployment-configured trust anchor
6. this Project Binding's own admission chain has a CURRENT admission at all
7. the presented reference names EXACTLY that current admission
```

**Why currency is last, deliberately.** It is the identical ordering
`route._resolve_deployment_declaration` already uses for its own sibling pointer, and for the
identical reason: a forged, foreign-signed, tampered, wrong-project or wrong-Binding admission can
never *become* current -- the committer that moves the pointer verifies the anchor signature
first -- so ordering currency ahead of the record-level checks would collapse every one of those
refusals into an indistinguishable "not current" and stop each control proving what it claims.
Ordering it last keeps each refusal at its own check, and leaves currency isolated by the rotation
and revocation controls, where the presented record is perfectly genuine in every other respect.

**`TrustedRuntimeRoot` is removed, not kept beside the new type.** It existed only to *name* a
world, and naming a world is now composition's own job; an inert value beside the authority would
leave a future reader two handles with one purpose. Rounds 2 and 3 could assert only that no
shipped callable returned that type and no shipped module constructed one; the Round 4 assertion
is strictly stronger -- the name occurs in **no code position anywhere in the shipped tree** --
and the deleted Round 1 minting factory is still absent by name, unchanged. What replaces those
assertions on the positive side is the honest fact Round 3 itself established (a mechanism with no
production-legitimate producer is a defect): **exactly one** shipped callable returns a
`RuntimeDeploymentAuthority`, exactly one shipped call site constructs one, and it is the trusted
composition step.

#### 13.1.1 The root-admission lifecycle is the *same* mechanism, one level up

The review required that the root admission "must not repeat the declaration-currency defect
below". Round 3 asked only *does a matching ACTIVE admission exist and resolve?* -- which is
literally the ineffective-revocation question Round 3 itself had already rejected one level down:

```text
admission A committed, ACTIVE, anchor-signed         composition succeeds -- correct
the deployment revokes the boundary: mints B         A keeps its own unchanged content address,
                                                     stays resolvable, ACTIVE and signed forever
composition presented with A again                   ACCEPTED under Round 3 -- and wrong
```

So a root admission is now a chained record in exactly the sense §13.2 defines for declarations:
required `generation`/`predecessor_ref` in `runtime_root_admission.schema.json`, both covered by
`ROOT_ADMISSION_SEMANTIC_FIELDS` and therefore by the record's own content address, its own
semantic fingerprint, and the **trust anchor's** own signature over it; a current-admission
pointer in Project State; and one sanctioned committer,
`commit_runtime_root_admission(store, project_id, admission, *, trust_anchor_public_key_hex,
committed_at)`, that moves it.

```text
semantic_state.runtime.claims["ROOT-ADMISSION:<project_binding_id>"] -> runtime_root_admission_id
```

**The two chains' key spaces are provably disjoint, not observed not to collide.** A declaration
target key is exactly `RUNTIME-DEPLOYMENT-TARGET-` plus 64 characters from `[0-9A-F]` (a
`hexdigest().upper()` can emit nothing else), and neither that prefix nor that alphabet contains
`":"`; every admission chain key contains one, at the fixed offset the literal prefix
`ROOT-ADMISSION:` puts it at. No string can be a member of both sets, whatever the inputs. The
proof is over the alphabets themselves, in `tests/unit/runtime/test_runtime_transition_chain.py`,
with an empirical companion asserting the real derivations really do produce those shapes. Still
**no State schema change**: `claims` remains the open `{string: scalar}` map Round 3 already used.

#### 13.1.2 What is proved, and what is not

```text
THE REQUEST-FACING SIGNATURE CAN NAME NO STORE/PROJECT/BINDING/ADMISSION/ANCHOR      proved
A SELF-CONSISTENT ALTERNATE WORLD PLUS ITS MATCHING ANCHOR CANNOT BE SUBSTITUTED     proved
   INTO THE REQUEST-FACING BOOTSTRAP, AT ZERO ADAPTER AND ZERO NETWORK CALLS
EACH OF STORE / PROJECT / BINDING / ADMISSION / ANCHOR IS INDEPENDENTLY REFUSED      proved
   WHEN SUBSTITUTED ALONE AT THE COMPOSITION BOUNDARY
A ROTATED OR REVOKED ADMISSION CANNOT BE REPLAYED THROUGH ITS OLD REFERENCE          proved
THE RAW ANCHOR IS ABSENT FROM THE COMPOSED AUTHORITY'S ENTIRE REACHABLE STATE        proved
AN ALREADY-COMPOSED AUTHORITY IS REVOKED RETROACTIVELY                               false, and
                                                                                    not claimed
A LIVE DEPLOYMENT ENTRYPOINT CALLS THIS COMPOSITION IN THIS REPOSITORY               false, and
                                                                                    not claimed
```

The second-to-last line is §13.5 item 1, stated here rather than implied away. The last is
unchanged from Rounds 2 and 3 and remains a scheduling fact about later Phases.

### 13.2 P15-R4-F2 -- a declaration's lifecycle is a monotonic, signed transition chain

*Claimed (Round 3):* making "current" mean what
`semantic_state.runtime.claims[<target_key>]` names, and moving that pointer atomically whenever
any new declaration is issued for a target, made revocation genuinely effective.

*True:* it made revocation effective in one direction only. Nothing required a declaration to say
*what it replaced*, so the pointer was freely re-pointable in both:

```text
A(ACTIVE)  -> B(REVOKED)   a genuine revocation                                     intended
B(REVOKED) -> A(ACTIVE)    replaying the already-issued, still-signed, still-in-     ACCEPTED
                           window ancestor A moved the pointer straight back and     and wrong
                           silently un-revoked a revoked deployment target
```

and two rotations racing each other interleaved into whichever order the Store happened to see
last, with no way to tell which head either was issued against.

*Now:* every `runtime_deployment_declaration` binds, inside both its content identity and its
Human Authority signature:

```text
project_id, project_binding_ref, human_authority_ref, target identity fields,
deployment_fingerprint, status, declared_at, valid_from, valid_until,
generation, predecessor_ref
```

```text
GENESIS      generation == 0, predecessor_ref == null, and only when the target has no current
             declaration. A genesis record must be ACTIVE (§13.5, item 6).
SUCCESSOR    generation == current.generation + 1, and predecessor_ref naming the EXACT id the
             pointer currently holds.
ROTATION     an ACTIVE successor replacing an ACTIVE current -- the successor rule, nothing more.
REVOCATION   a REVOKED successor naming the exact current declaration. TERMINAL for that target.
TERMINAL     after a REVOKED head, no same-chain successor and no ancestor replay is ever
             admitted again. Reactivation requires a separately adopted new target epoch/chain,
             never silent pointer movement -- and that epoch is deliberately not built in this
             round (§13.5, item 8).
REPLAY       proposing the record the pointer already names is an idempotent no-op success: it
             moves nothing, commits nothing, and is not a transition.
```

Because `generation` and `predecessor_ref` participate in the signed payload, a successor is a
*signed statement about which record it replaces*. That single fact is what makes §13.3's
concurrency rule sound rather than merely convenient.

**The mechanism is shared, not duplicated.** Both chains parameterize one module,
`runtime/transition_chain.py`, through a `MonotonicChainSpec` naming only what genuinely differs
(record kind, its two digest field names, its validator, its two derivations, its chain key). The
rules -- genesis, succession, terminality, status legality, pointer movement, and the
Compare-And-Swap discipline -- live there and are identical for both. Two consequences are worth
recording:

- `deployment_registry.py` no longer calls `commit_state_transition` at all; `transition_chain.py`
  owns that single call site for both chains, so adding a second chain kind in this round added
  **no** second commit site. This package still admits exactly two, by name (`route.py` and
  `transition_chain.py`), and still calls no `store.commit` directly.
- static conformance additionally proves neither committer restates a chain rule of its own: each
  calls `commit_chain_transition` exactly once, evaluates no transition legality itself, and names
  no `ACTIVE`/`REVOKED` literal in any code position.

**`observe_runtime_target` is unchanged.** Every Round 1-3 check it performs -- pre-adapter
refusals, per-commit currency and authority-freshness re-checks, the ACTIVE requirement, the
signature/Boot binding, the validity window -- remains exactly as it was, and every one of those
controls is still green. The declaration registry likewise remains a Runtime domain route using
the existing Store's single sanctioned committer; it is not a second Store, State, Authority, or
Reflow owner.

### 13.3 The committer: dual verification, and why the concurrency loser fails closed

**Boot and signature verification now happen at commit time too, in addition to
`observe_runtime_target`'s own independent re-check.** Round 3's committer deliberately skipped
signature verification, arguing that the route re-checks it fresh and that a second copy could
drift into a different notion of "an acceptable declaration". That argument rested on a premise
Round 4 removes: Round 3's committer had **no transition legality to gate at all** -- every
declaration simply overwrote the pointer -- so verifying there would genuinely have bought
nothing. The committer now decides whether a proposal may *move a chain*, and it cannot decide
that honestly while unable to tell a genuine Human Authority statement from an unsigned or
wrongly-signed one.

```text
AT COMMIT TIME (deployment_registry)   may this proposal move this target's own pointer at all?
                                       -> fresh Boot; human_authority_ref must equal the restored
                                          one; signature verified against the Boot-restored key;
                                          validity window well-ordered -- all BEFORE any
                                          generation/predecessor legality is considered.

AT OBSERVATION TIME (route.py)         may this declaration be trusted to anchor an observation
                                       NOW -- possibly much later, possibly after a legitimate
                                       Human Authority re-binding? -> that call's OWN fresh Boot,
                                       its own signature check, ACTIVE requirement, validity
                                       window, and currency check. All unchanged, all required.
```

Neither subsumes the other: a declaration committed under authority X stays committed, while an
observation made after a re-binding to authority Y must refuse it. Round 3's drift concern is
answered by both sites calling the identical
`verify_runtime_deployment_declaration_signature` over the identical
`runtime_deployment_declaration_signing_payload` bytes -- one verifier, one payload, two moments
-- rather than by one of them not looking. The admission committer's own verification is the
same shape against the deployment anchor instead of a Boot-restored key.

**The commit loop, exactly.**

```text
loop (bounded retries, the identical bound route.py's own _commit_envelope uses):
    load State fresh
    read this chain's own pointer
    if the pointer already names this exact record -> IDEMPOTENT_REPLAY; return, commit nothing
    resolve the current record from the bound Store
    verify(proposed, state)                  fresh Boot + signature, EVERY iteration
    re-evaluate the ENTIRE transition        genesis / successor / terminality / status legality
        -> any illegality FAILS CLOSED, immediately, never retried
    commit_state_transition(...)
        StaleStateError -> reload and re-evaluate everything from scratch
```

The distinction Round 3's loop could not draw:

```text
UNRELATED CONTENTION        this chain's own pointer still names the record the proposal's own
                            predecessor_ref names   ->  reload and retry (Round 1 F5's own
                            established tolerance, deliberately preserved and still proved)
THIS CHAIN'S POINTER MOVED  the pointer already names something else  ->  FAIL CLOSED, no retry
```

The second is not pessimism about retries; it is the only sound answer. The losing proposal's
`predecessor_ref` and `generation` were signed against a *specific* prior head. Re-aiming it at
the new head would mean committing a body whose own signed content no longer describes its true
predecessor, and producing an honestly re-aimed one requires a **new signature over a new
payload** -- which only the Human Authority (or, for admissions, the deployment trust anchor) can
create, never this committer. So "the loser re-evaluates against the new head and fails closed"
is literally what happens, and the loser's operator must re-issue rather than the committer
adjusting anything on their behalf.

The concurrency control that proves this uses this package's own established barrier-store
technique (`test_runtime_authority_freshness.py`'s `_UnrelatedContentionStore`,
`test_runtime_deployment_identity_anchor.py`'s `_PointerBarrierStore`) rather than a new
simulation mechanism: a test-only Store wrapper lands a *legitimate competing successor from the
same predecessor* between the call's own load and its own commit attempt, so the loser's retry
genuinely re-observes a moved head. The harness never asserts an outcome it did not cause the real
retry path to produce.

### 13.4 Finding-to-code-to-test matrix

```text
P15-R4-F1  composition owns the trust anchor
  src/manosube_agent_civilization/runtime/bootstrap.py
      RuntimeDeploymentAuthority (opaque, no public accessor, no retained anchor)
      compose_trusted_runtime_deployment_authority  (the one shipped composition entry point)
      _require_currently_admitted                   (7 checks, currency last)
      bootstrap_projection_execution_capability     (3 parameters; 5 removed)
      _boot                                         (one literal boot_project call site, two uses)
  src/manosube_agent_civilization/runtime/admission_registry.py   the admission chain + committer
  src/manosube_agent_civilization/runtime/identity.py             chain fields + chain key
  01_SCHEMA/runtime/runtime_root_admission.schema.json            generation + predecessor_ref

  tests/contract/runtime/test_runtime_static_conformance.py
      test_the_request_facing_bootstrap_accepts_no_trust_deciding_parameter
      test_the_composition_entry_point_owns_every_trust_deciding_parameter
      test_the_raw_trust_anchor_is_named_only_by_composition_side_functions
      test_the_removed_trust_root_type_appears_in_no_shipped_code_position
      test_exactly_one_shipped_module_defines_the_composition_owned_authority
      test_exactly_one_shipped_public_callable_returns_a_deployment_authority
      test_the_composed_authority_exposes_no_public_accessor_for_what_it_binds
      test_the_admission_gate_precedes_every_grant_and_authority_call_by_construction
      test_no_shipped_runtime_module_reads_configuration_at_all
      test_the_two_chain_key_spaces_are_structurally_disjoint
  tests/integration/runtime/test_runtime_deployment_authority_composition.py
      test_a_canonical_composition_bound_world_reaches_the_controlled_adapter
      test_the_composed_authority_retains_the_raw_trust_anchor_nowhere
      test_the_composed_authority_exposes_no_public_accessor_at_all
      test_the_attacker_world_is_genuinely_self_consistent_and_self_admitted
      test_the_attacker_world_cannot_be_substituted_into_the_request_facing_bootstrap
      test_substituting_only_the_anchor_is_independently_refused
      test_substituting_only_the_admission_is_independently_refused
      test_substituting_only_the_store_is_independently_refused
      test_substituting_only_the_project_is_independently_refused
      test_substituting_only_the_binding_is_independently_refused
      test_an_admission_rotated_at_the_composition_level_can_no_longer_be_replayed
      test_a_revoked_admission_chain_admits_no_further_composition_at_all
      test_a_revoked_admission_chain_is_permanently_terminal
      test_an_authority_composed_before_a_rotation_remains_usable_by_its_holder
      test_an_admission_planted_without_the_committer_is_never_current
  tests/integration/runtime/test_runtime_root_admission.py       every Round 3 record-level
                                                                 control, re-rooted at composition
  tests/integration/runtime/test_runtime_trusted_root.py         the two-world (a)/(b)/(c) groups
  tests/integration/runtime/test_runtime_no_shipped_minting_path.py
                                                                 no shipped minting path survives

P15-R4-F2  monotonic, signed declaration transition chain
  src/manosube_agent_civilization/runtime/transition_chain.py    the ONE shared mechanism
  src/manosube_agent_civilization/runtime/deployment_registry.py the declaration binding + Boot
                                                                 and signature verification
  src/manosube_agent_civilization/runtime/identity.py            generation/predecessor_ref in
                                                                 DEPLOYMENT_DECLARATION_SEMANTIC_
                                                                 FIELDS
  01_SCHEMA/runtime/runtime_deployment_declaration.schema.json   generation + predecessor_ref

  tests/unit/runtime/test_runtime_transition_chain.py            every rule, over a synthetic kind
  tests/integration/runtime/test_runtime_declaration_transition_chain.py
      test_the_chain_admits_genesis_then_rotation_then_revocation_in_order
      test_replaying_the_ancestor_after_a_revocation_leaves_the_pointer_at_the_revocation
      test_replaying_the_ancestor_after_a_rotation_leaves_the_pointer_at_the_rotation
      test_a_deep_chain_cannot_be_rewound_to_any_earlier_generation
      test_a_successor_naming_the_wrong_predecessor_refuses_without_state_change
      test_a_successor_skipping_a_generation_refuses_without_state_change
      test_a_duplicate_generation_with_a_different_body_refuses_without_state_change
      test_a_successor_after_a_revocation_refuses_without_state_change
      test_a_first_declaration_that_is_not_a_genesis_record_refuses_without_state_change
      test_replaying_the_exact_current_declaration_is_idempotent_and_moves_nothing
      test_replaying_a_revoked_current_declaration_is_also_idempotent
      test_the_committer_refuses_an_unsigned_or_wrongly_signed_transition
      test_the_committer_refuses_a_declaration_naming_an_authority_boot_did_not_restore
      test_the_committers_boot_is_fresh_so_a_rebinding_invalidates_a_stale_signer
      test_two_concurrent_successors_from_the_same_head_resolve_to_at_most_one_winner
      test_an_unrelated_state_bump_during_the_retry_loop_never_blocks_a_legal_transition
  tests/integration/runtime/test_runtime_deployment_identity_anchor.py
                                                                 every Round 1-3 observation-side
                                                                 control, migrated to the chain and
                                                                 still green (validity boundaries,
                                                                 stale/not-yet-valid, superseded,
                                                                 replayed-old-ACTIVE, unregistered,
                                                                 post-check substitution)
  tests/unit/runtime/test_runtime_identity.py                    both chain fields participate in
                                                                 identity, fingerprint and payload
```

### 13.5 Judgment calls made in this round that the adopted findings did not fully pin down

1. **An already-composed authority is a cached capability, and rotation binds the *next*
   composition.** Composition Boots and verifies the anchor exactly once and then discards it;
   there is no per-request re-verification. This is not an oversight -- it is forced by the
   adopted contract's own wording ("closed over afterward", "absent from every request-facing
   execution signature"), which rules out re-verifying per call, and it is exactly how a cached
   credential or capability token behaves in any real system. A holder keeps working until they
   stop or recompose; a revocation takes effect at the next composition. Stated here, and proved
   as its own control (`test_an_authority_composed_before_a_rotation_remains_usable_by_its_holder`)
   rather than left for a reader to infer a retroactive property this design does not have.

2. **The root admission keeps a caller-supplied reference, cross-checked against the pointer,
   rather than composition resolving "whatever is current".** Both were permitted. The presented-
   reference form is chosen because it mirrors `_resolve_deployment_declaration` exactly (a
   presented reference checked against its own pointer), and because it makes the decisive control
   literally expressible: *compose against A, rotate or revoke to B, then present A's own
   still-valid, still-resolvable reference and be refused*. With "resolve whatever is current",
   referencing A would not be expressible at all, and the strongest available control would be a
   weaker one.

3. **The shared mechanism is a spec object plus free functions, not a base class.**
   `MonotonicChainSpec` carries only what genuinely differs between record kinds; every rule is a
   module-level function over it. Inheritance was rejected because a subclass can override a rule,
   which is precisely the drift the review's "same class has recurred four times" framing warns
   about. Signature verification is deliberately a per-call `verify` callback rather than a spec
   field: the two chains ask genuinely different questions of genuinely different keys (a
   Boot-restored Human Authority key; a deployment-configured anchor not resolvable from inside
   the Store at all), and one spec field would have to pretend they are the same question.

4. **The admission chain lives in its own module, `admission_registry.py`.** Folding it into
   `deployment_registry.py` would have made a module named and documented for one record kind own
   two; folding it into `root_admission.py` would contradict that module's own stated
   verification-only discipline. The separation costs nothing in duplication, because both
   registries are thin bindings over one shared mechanism.

5. **`commit_runtime_root_admission` takes the raw trust anchor, and that is not a violation of
   "the anchor appears only at composition".** Issuing, rotating, or revoking an admission *is*
   the deployment/composition boundary acting -- it is the act of deciding which world is canonical
   at all. Static conformance pins the exact set of shipped functions that may name the parameter
   (the composition entry point, its own private helper, this committer, and the pure verification
   wrapper) and proves the request-facing operation is not among them.

6. **A genesis record must be ACTIVE.** The adopted rules fix `generation`/`predecessor_ref` for
   genesis but not its status. A genesis `REVOKED` record would revoke nothing and would open a
   permanently terminal chain that never admitted anything -- a shape with no meaning rather than a
   stricter one -- so it is refused, with its own message.

7. **Idempotent replay short-circuits before verification, deliberately.** Proposing the record
   the pointer already names returns immediately, without a fresh Boot or signature check. It is
   not a transition, nothing moves, and the record's signature was already verified when it was
   made current; running the checks anyway would imply a decision is being made when none is.
   `committed_state` is `None` for that outcome, and the returned `transition` says
   `IDEMPOTENT_REPLAY` rather than naming a transition that did not happen.

8. **Target-epoch reactivation after a terminal REVOKED is deliberately NOT built.** The adopted
   contract requires only that terminal REVOKED be permanently terminal for that exact chain key,
   and says a later reactivation "requires a separately adopted new target epoch/chain, not silent
   pointer movement" -- it does not require that epoch to exist now. Building a target-identity
   `epoch` field and a reactivation path would be unrequested scope. The permanent-terminal
   property is implemented and proved for both chains; no reactivation mechanism exists, and none
   is claimed.

9. **`TrustedRuntimeRoot` is deleted rather than kept as an inert alias.** See §13.1. The
   strictly-stronger static assertion that replaces Rounds 2 and 3's own is what makes this a
   supersession rather than a quiet loss of a proved fact.

10. **Several Round 1-3 negative controls now plant their record with a raw `commit_records`.**
    The committers verify signature, authority binding, project and Binding before they will move a
    chain, so a forged, foreign-signed, wrong-project, wrong-Binding, tampered, or genesis-REVOKED
    record cannot reach the Store through them at all -- correctly. Those controls therefore plant
    the record directly, and each still refuses at exactly the check its own name claims, because
    both the route and composition check the record itself before checking currency. Every such
    site says so at the test.

11. **The configuration-reading prohibition is proved package-wide, not only on the request
    path.** Contract 1 item 7 forbids request-path code from reading an environment variable, file,
    or parameter to choose a different trust root. Proving it for the whole shipped `runtime`
    package -- no `os`/`pathlib` import, no `environ`/`getenv`/`expanduser` in any code position,
    no bare `open`/`read_text`/`read_bytes` call -- is both stronger and simpler to keep true than
    trying to delimit "the request path" statically. `adapter.py`'s own `self._opener.open(...)` is
    the HTTP opener this package's network boundary already owns and bounds, and is excluded by
    name and by shape rather than by accident.

### 13.6 Round 4 declarations

```text
TRUST_ANCHOR_OWNED_BY_COMPOSITION=true
TRUST_ANCHOR_PRESENT_ON_REQUEST_FACING_SIGNATURE=false
ROOT_ADMISSION_REF_PRESENT_ON_REQUEST_FACING_SIGNATURE=false
STORE_PROJECT_OR_BINDING_PRESENT_ON_REQUEST_FACING_SIGNATURE=false
REQUEST_FACING_BOOTSTRAP_PARAMETER_COUNT=3
COMPOSITION_ENTRY_POINT_COUNT=1
SHIPPED_CALLABLES_RETURNING_A_DEPLOYMENT_AUTHORITY=1
SHIPPED_CONSTRUCTION_SITES_OF_A_DEPLOYMENT_AUTHORITY=1
DEPLOYMENT_AUTHORITY_RETAINS_THE_RAW_TRUST_ANCHOR=false
DEPLOYMENT_AUTHORITY_EXPOSES_A_PUBLIC_ACCESSOR=false
DEPLOYMENT_AUTHORITY_BINDS_THE_EXACT_ADMITTED_GENERATION=true
TRUSTED_RUNTIME_ROOT_TYPE_EXISTS=false
TRUSTED_RUNTIME_ROOT_NAME_APPEARS_IN_SHIPPED_CODE=false
DELETED_ROUND_1_MINTING_FACTORY_REINTRODUCED=false
REQUEST_PATH_READS_ENVIRONMENT_FILE_OR_REGISTRY=false
ROOT_ADMISSION_IS_A_MONOTONIC_SIGNED_CHAIN=true
ROOT_ADMISSION_CURRENT_POINTER_IS_STORE_RESOLVED=true
ROOT_ADMISSION_ROTATION_AND_REVOCATION_ARE_EFFECTIVE=true
ROOT_ADMISSION_REVOCATION_IS_TERMINAL=true
DEPLOYMENT_DECLARATION_IS_A_MONOTONIC_SIGNED_CHAIN=true
DECLARATION_GENERATION_AND_PREDECESSOR_ARE_SIGNED=true
DECLARATION_ANCESTOR_REPLAY_IS_REFUSED=true
DECLARATION_REVOCATION_IS_TERMINAL=true
TARGET_EPOCH_REACTIVATION_MECHANISM_BUILT=false
IDENTICAL_CURRENT_RECORD_REPLAY_IS_IDEMPOTENT=true
CONCURRENCY_LOSER_FAILS_CLOSED=true
UNRELATED_CONTENTION_STILL_RETRIES=true
COMMITTER_VERIFIES_BOOT_AND_SIGNATURE=true
OBSERVE_RUNTIME_TARGET_CHECKS_WEAKENED=false
CHAIN_MECHANISM_MODULE_COUNT=1
CHAIN_RULE_DUPLICATED_PER_RECORD_KIND=false
CHAIN_KEY_SPACES_PROVABLY_DISJOINT=true
COMMIT_STATE_TRANSITION_CALL_SITES_IN_THIS_PACKAGE=2
SEMANTIC_STATE_SCHEMA_CHANGED=false
NEW_SCHEMA_FILES_ADDED=0
CANONICAL_SCHEMA_COUNT=59
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
RUNTIME_DEPLOYMENT_DECLARATION_COMMIT_ENTRY_POINT_COUNT=1
RUNTIME_ROOT_ADMISSION_COMMIT_ENTRY_POINT_COUNT=1
AUTHORITY_COMPOSED_BEFORE_A_ROTATION_IS_RETROACTIVELY_REVOKED=false
ED25519_VERIFICATION_REIMPLEMENTED_IN_RUNTIME=false
BINDING_IMPORTS_RUNTIME=false
RUNTIME_HOLDS_A_PRIVATE_SIGNING_KEY=false
RUNTIME_MINTS_A_SIGNATURE=false
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
```

### 13.7 Round 4 proof layers

```text
tests/unit/runtime/test_runtime_transition_chain.py             F1/F2 (every chain rule, over a
                                                                   synthetic record kind: genesis,
                                                                   succession, rotation,
                                                                   revocation, terminality,
                                                                   malformed chain fields, pointer
                                                                   reads, and the structural
                                                                   key-space disjointness proof)
tests/unit/runtime/test_runtime_identity.py                     F1/F2 (both chain fields
                                                                   participate in each record
                                                                   kind's own single derivation,
                                                                   and a record missing either
                                                                   cannot be addressed at all)
tests/contract/runtime/test_runtime_static_conformance.py       F1 (the request-facing signature's
                                                                   three parameters and five
                                                                   absences; composition's own
                                                                   five; the exact set of shipped
                                                                   functions that may name a raw
                                                                   anchor; the removed type absent
                                                                   from every code position; one
                                                                   authority definition, one
                                                                   construction site, one producer;
                                                                   no public accessor; no
                                                                   configuration read anywhere) and
                                                                   F2 (still exactly two
                                                                   commit_state_transition call
                                                                   sites, now route.py and
                                                                   transition_chain.py; neither
                                                                   committer restates a chain rule)
tests/integration/runtime/test_runtime_deployment_authority_composition.py
                                                                F1 (the canonical composition-bound
                                                                   world reaching a controlled
                                                                   adapter; the anchor absent from
                                                                   the authority's entire reachable
                                                                   state; the alternate world with
                                                                   its own matching attacker anchor,
                                                                   unsubstitutable at zero adapter
                                                                   and zero authorization calls;
                                                                   each of Store/Project/Binding/
                                                                   admission/anchor refused alone;
                                                                   admission rotation, revocation,
                                                                   permanent terminality, and the
                                                                   disclosed cached-capability
                                                                   boundary)
tests/integration/runtime/test_runtime_declaration_transition_chain.py
                                                                F2 (genesis/rotation/revocation in
                                                                   order; both ancestor-replay
                                                                   rollback controls; deep-chain
                                                                   rewind; wrong predecessor,
                                                                   skipped and duplicate
                                                                   generation, successor after
                                                                   REVOKED, non-genesis first
                                                                   record -- each without any State
                                                                   change; idempotent replay; the
                                                                   committer's Boot and signature
                                                                   gate; the concurrent-successor
                                                                   control; and the preserved
                                                                   unrelated-contention tolerance)
tests/integration/runtime/test_runtime_root_admission.py        F1 (every Round 3 record-level
                                                                   admission control, re-rooted at
                                                                   the composition boundary that now
                                                                   owns the question)
tests/integration/runtime/test_runtime_trusted_root.py          F1 (the two-world groups: composition
                                                                   as the only path to an authority;
                                                                   no request-facing argument can
                                                                   redirect a call; bare stores and
                                                                   look-alikes refused before Boot)
tests/integration/runtime/test_runtime_no_shipped_minting_path.py
                                                                F1 (the deleted factory still gone;
                                                                   the removed type gone everywhere;
                                                                   exactly one producer, and it
                                                                   cannot produce without the
                                                                   deployment's own anchor)
tests/integration/runtime/test_runtime_deployment_identity_anchor.py
                                                                F2 (every Round 1-3 observation-side
                                                                   control, migrated to the chain and
                                                                   still green)
tests/fixtures/runtime_world.py                                 F1/F2 (every fixture migrated to the
                                                                   composed-authority shape and to
                                                                   signed chain fields; both
                                                                   admission and declaration commits
                                                                   now go through the shipped
                                                                   canonical committers)
```

---

## 14. Structural Review Round 5 (P15-R5-F1, P15-R5-F2, P15-R5-F3)

Round 5 of PR #65 confirmed Round 4's F2 (the monotonic, signed transition chain) closed and
**reopened Round 4's own F1**, on the observation that the ownership boundary Round 4 built was
still carried by an ordinary public value type. It added one further, independent finding about
timestamp ordering at declaration commit. Where this section and an earlier one differ, this
section governs — the same rule every earlier round states.

The recurrence series Round 4 named continues, and Round 5's entry names the specific step that
was still missing:

```text
ROUND 1   the trust decision was a PARAMETER LIST      -> replaced by a TYPE
ROUND 2   the trust decision was a PUBLIC FACTORY      -> replaced by a PRIVATE SENTINEL
ROUND 3   the trust decision was POSSESSION OF A TYPE  -> replaced by a SIGNED ADMISSION RECORD
                                                          verified against a CALLER-SUPPLIED
                                                          anchor
ROUND 4   the trust decision was STILL A PARAMETER     -> replaced by an OWNERSHIP BOUNDARY
                                                          carried by an opaque VALUE TYPE
ROUND 5   the OWNERSHIP BOUNDARY was carried by a      -> replaced by a CLOSURE: composition
          PUBLIC DATACLASS with a PUBLIC CONSTRUCTOR,     RETURNS the request-facing operation,
          guarded only by an `isinstance` check, so      already bound to its world, and there is
          any importer could construct their own over    no public constructor for an equivalent
          an alternate world and hand it in              one at all
```

### 14.1 P15-R5-F1 — the composition step returns a bound request-facing service

*Claimed (Round 4):* moving every trust-deciding value onto
`compose_trusted_runtime_deployment_authority` and handing request-facing code an opaque
`RuntimeDeploymentAuthority` closed the finding, because the request-facing signature had no
parameter for a Store, Project, Binding, admission or anchor.

*True:* those five parameters were genuinely gone, and remain gone. But Round 4 introduced a
**sixth** world-bearing parameter in their place — the authority object itself — and the type
behind it was a plain public frozen dataclass with a plain public constructor. The request-facing
half was a free module-level function whose only defence was an `isinstance` check:

```python
bootstrap_projection_execution_capability(
    RuntimeDeploymentAuthority(attacker_store, attacker_project, attacker_binding, adm_id, gen),
    github_projection_grant_refs=[...],
    github_projection_grant_declaration_refs=[...],
)  # a genuine instance of exactly the right type, over an entirely alternate world
```

Making that function a *method* on the same public dataclass would not have closed it either: a
caller can still construct their own instance and call the method on it. The review explicitly
rules out a sentinel, a leading-underscore field, a private constructor, an opaque `repr`, and an
`isinstance` check as the trust control, and states the control positively: *deployment
composition chooses and closes over the authority before the request boundary exists.*

*Now:* the type is **deleted**, and composition returns the request-facing operation itself.

```python
# bootstrap.py — the one shipped trusted-composition entry point (parameters unchanged)
compose_trusted_runtime_deployment_authority(
    store, *, project_id, project_binding_id,
    runtime_root_admission_ref, trust_anchor_public_key_hex,
) -> Callable[..., ProjectionExecutionCapability]

# ...that returned callable IS the request-facing operation. Two parameters, both keyword-only,
# both operation-scoped. It is a closure defined inside the call frame above, holding the
# canonical Store, Project, Binding and admitted admission id/generation in closure cells.
<returned callable>(
    *, github_projection_grant_refs, github_projection_grant_declaration_refs,
) -> ProjectionExecutionCapability
```

A closure is not a class: it has **no public constructor**, so there is nothing a caller can call
to fabricate an equivalent operation over an alternate world. The only way to obtain a working one
is to call composition, which runs the full anchor-signature/currency admission gate
(`_require_currently_admitted`, unchanged from Round 4) before the closure exists at all.

```text
canonical composed service + canonical refs        -> controlled adapter boundary reached
attacker authority + attacker refs                 -> cannot be supplied to the canonical
                                                      request operation (TypeError; no such
                                                      parameter, positional or keyword)
attacker Store/Project/Binding/admission/anchor    -> absent from the operation's signature
   kwargs
adapter/network calls on every substitution        -> 0
authorization evaluations on every substitution    -> 0
```

The attacker world used for that control is fully self-consistent and composes a genuinely
working service **inside itself** — proved, so that every refusal is a statement about ownership
rather than about a broken world.

**`RuntimeDeploymentAuthority` is deleted, not kept beside the closure.** This is the precedent
Round 2 set for the minting factory and Round 4 set for `TrustedRuntimeRoot`, applied to Round 4's
own type: leaving an inert value behind would give a future reader two handles with one purpose.
The static assertion is the absolute one — the name occurs in **no code position anywhere in the
shipped tree** — and `bootstrap_projection_execution_capability` is no longer a module-level name
either: exactly one `def` anywhere shipped carries it, nested inside the composition entry point,
which genuinely returns it.

**Scope, disclosed.** This is a control over *call shapes and obtainability*, not over in-process
memory. Nothing in Python stops code that already holds the returned function object from
rewriting its own closure cells (`__closure__[i].cell_contents`), exactly as nothing stopped
Round 4's frozen dataclass from being rewritten through `object.__setattr__`. What changed, and
what the decisive controls measure, is that no *call* can name an alternate world and no *public
constructor* can fabricate an equivalent service.

### 14.2 P15-R5-F2 — current-admission recheck before every new capability issuance

*Claimed (Round 4, §13.5 item 1):* an already-composed authority is a cached capability, and
rotation or revocation binds only the *next* composition — forced, it argued, by the adopted
contract's own "closed over afterward" wording.

*True, but narrower than Round 4 treated it.* That wording constrains the **anchor**, not the
admission's currency. Those are two different questions, exactly as `deployment_registry.py`'s own
docstring already distinguishes signature-verification-at-commit from currency-at-observation:

```text
IS THE ANCHOR STILL THE RIGHT ANCHOR?    asked exactly ONCE, at composition. The raw anchor stays
                                         absent from every request-facing signature and is never
                                         re-verified per call. UNCHANGED from Round 4.

IS THE ADMISSION THIS SERVICE WAS        asked FRESHLY ON EVERY CALL, from the canonical Store's
COMPOSED AGAINST STILL THE CURRENT ONE?  own current-admission pointer plus the retained admission
                                         id and generation. Needs no anchor: the record is
                                         immutable and content-addressed, and the pointer is moved
                                         only by the anchor-signature-gated
                                         commit_runtime_root_admission.
```

*Now:* every request-facing call runs `_require_bound_admission_still_current` before resolving a
single grant. Four requirements, each stated and checked separately because the adopted contract
lists four — deliberately not collapsed into one another even where an implication is visible, so
that a future edit changing what "current" resolves through cannot silently take three checks with
it:

```text
1. the Store's current-admission pointer still names the exact admission id captured at
   composition
2. the resolved current admission carries the exact captured generation
3. the current admission is still ACTIVE
4. it still restates this bound service's own Project and Project Binding
```

```text
compose at A -> rotate to ACTIVE B -> bootstrap through the A service  -> refuse
compose at A -> move to REVOKED B  -> bootstrap through the A service  -> refuse
old A remains resolvable and signature-valid                           -> still refuse, on
                                                                          currency alone
grant/authorization/adapter call counts before refusal                 -> 0
fresh service composed at the current ACTIVE B                         -> succeeds, reaches a
                                                                          real capability and the
                                                                          controlled adapter
```

**Already-issued downstream projection capabilities are not retroactively revoked.** The adopted
boundary is prevention of *new* issuance from a no-longer-current composition authority, and that
limit is proved as its own control rather than quietly widened: a capability obtained while A was
still current is issued, exercised against the controlled adapter, and then — after the rotation —
shown to be the identical object with the identical bound context, while the same service refuses
to mint another.

*Disclosed precisely:* whether that already-issued capability would still **execute** after a
rotation is not this correction's question. Phase 14's own independent context-currency check
(`projection.execution.execution_context_still_current`) refuses execution after **any** State
transition, related or not — a pre-existing mechanism with its own separate reasons, which a
rotation commit trips exactly as an unrelated commit would. This round is responsible for the
object not being touched, and for new issuance being what stops.

Round 4's §13.5 item 1 is therefore **narrowed, not contradicted**: the anchor is still closed
over and never re-verified per call; currency of the already-admitted record now is.

### 14.3 P15-R5-F3 — real UTC instant ordering at declaration commit

*Claimed (Rounds 3 and 4):* `_require_declaration_shape_and_signature` required a declaration's
own validity window to be "genuinely ordered".

*True:* it compared the two raw timestamp **strings** (`if valid_from > valid_until`). Round 1
(P15-R1-F2) had already established that lexicographic comparison is unsound over this
repository's own canonical timestamp grammar, which admits an optional fractional part — and the
committer never got the correction the route did. The failure runs in both directions:

```text
valid_from="2026-01-01T00:00:00Z"    valid_until="2026-01-01T00:00:00.5Z"
    a real 0.5s window                                     REFUSED lexicographically, and wrong
valid_from="2026-01-01T00:00:00.5Z"  valid_until="2026-01-01T00:00:00Z"
    an inverted window                                     ACCEPTED lexicographically, and wrong
```

*Now:* both bounds are parsed and compared as real UTC instants, and the parser is **the one this
package already had** — the adopted contract forbids a second timestamp grammar or a
Runtime-specific time owner, so `route.py`'s own private `_instant` moved, unchanged, to
`engine.parse_utc_instant`, and `route.py` and `deployment_registry.py` both read through it. The
committer still reads **no clock**: it orders the two declared bounds against each other and
against nothing else; whether an already-committed declaration is in-window at some later instant
remains `observe_runtime_target`'s own question, unchanged.

Uniqueness is proved statically rather than asserted: exactly one module in this package imports
`datetime` at all, exactly one function anywhere in it calls `fromisoformat`, and that function is
`engine.parse_utc_instant`.

### 14.4 Finding-to-code-to-test matrix

```text
P15-R5-F1  composition returns a bound request-facing service
  src/manosube_agent_civilization/runtime/bootstrap.py
      RuntimeDeploymentAuthority                    DELETED (no code position anywhere shipped)
      compose_trusted_runtime_deployment_authority  -> Callable[..., ProjectionExecutionCapability]
      bootstrap_projection_execution_capability     the returned CLOSURE; 2 keyword-only
                                                    parameters; 6 removed
      _require_currently_admitted                   unchanged (7 checks, currency last)
  src/manosube_agent_civilization/runtime/__init__.py   one public callable fewer for this
                                                        mechanism; usage example rewritten

  tests/contract/runtime/test_runtime_static_conformance.py
      test_runtime_package_exports_exactly_three_routes_and_one_capability_bootstrap
      test_the_removed_deployment_authority_type_appears_in_no_shipped_code_position
      test_the_request_facing_operation_is_a_closure_owned_by_the_composition_entry_point
      test_exactly_one_shipped_public_callable_returns_a_bound_request_facing_bootstrap
      test_the_request_facing_bootstrap_accepts_no_trust_deciding_parameter
      test_the_composition_entry_point_owns_every_trust_deciding_parameter
      test_the_raw_trust_anchor_is_named_only_by_composition_side_functions
  tests/integration/runtime/test_runtime_deployment_authority_composition.py
      test_a_canonical_composition_bound_world_reaches_the_controlled_adapter
      test_the_composed_bootstrap_retains_the_raw_trust_anchor_nowhere
      test_the_composed_bootstrap_is_a_closure_with_no_public_constructor
      test_the_attacker_world_is_genuinely_self_consistent_and_self_admitted
      test_the_attacker_world_cannot_be_substituted_into_the_request_facing_bootstrap
  tests/integration/runtime/test_runtime_trusted_root.py
      test_composition_is_the_only_shipped_path_to_a_request_facing_bootstrap
      test_a_composed_bootstrap_names_its_world_in_no_public_surface
      test_no_request_facing_argument_can_redirect_a_capability_call_into_another_world
      test_no_world_bearing_object_can_be_handed_to_the_request_facing_bootstrap
  tests/integration/runtime/test_runtime_no_shipped_minting_path.py
      test_the_removed_trust_root_type_appears_in_no_shipped_code_position (extended to the
          removed authority type and the removed module-level bootstrap name)
      test_exactly_one_shipped_callable_hands_back_a_bound_request_facing_bootstrap
      test_the_capability_call_accepts_no_world_bearing_argument_at_all

P15-R5-F2  current-admission recheck before every new capability issuance
  src/manosube_agent_civilization/runtime/bootstrap.py
      _require_bound_admission_still_current        the four separate requirements
      the returned closure                          calls it before any grant resolution

  tests/contract/runtime/test_runtime_static_conformance.py
      test_the_admission_gate_precedes_every_grant_and_authority_call_by_construction
  tests/integration/runtime/test_runtime_deployment_authority_composition.py
      test_a_service_composed_at_a_rotated_away_admission_issues_no_new_capability
      test_a_service_composed_before_a_revocation_issues_no_new_capability
      test_the_refusal_is_on_currency_alone_not_because_the_old_admission_became_invalid
      test_a_service_freshly_composed_at_the_new_current_admission_succeeds
      test_a_capability_issued_before_a_rotation_is_not_retroactively_revoked

P15-R5-F3  real UTC instant ordering at declaration commit
  src/manosube_agent_civilization/runtime/engine.py              parse_utc_instant (the one owner)
  src/manosube_agent_civilization/runtime/route.py               _instant deleted; reads engine's
  src/manosube_agent_civilization/runtime/deployment_registry.py parsed instants, not strings

  tests/contract/runtime/test_runtime_static_conformance.py
      test_this_package_has_exactly_one_instant_parsing_owner
      test_the_declaration_committer_orders_its_validity_window_as_instants_not_strings
  tests/integration/runtime/test_runtime_declaration_transition_chain.py
      test_the_two_orderings_genuinely_disagree_over_this_grammar
      test_a_chronologically_valid_fractional_second_window_commits
      test_a_chronologically_inverted_fractional_second_window_refuses_without_state_change
```

### 14.5 Judgment calls made in this round that the adopted findings did not fully pin down

1. **The closure's bound world is reachable through `__closure__` by in-process code, and that is
   disclosed rather than claimed away.** No Python-level control prevents code that already holds
   a function object from rewriting its cells, just as none prevented `object.__setattr__` on
   Round 4's frozen dataclass. The adopted control is about *obtainability and call shape*, and
   that is exactly what is proved. Stated in `bootstrap.py`'s own module docstring, in §14.1, and
   at the test that would otherwise be read as claiming more
   (`test_a_composed_bootstrap_names_its_world_in_no_public_surface`).

2. **The four currency requirements are implemented separately even where one implies another.**
   For an untampered Store, requirement 1 (the pointer still names the exact content-addressed
   admission id) arguably implies 2–4, since generation, status and Binding all participate in
   that id. They are still checked one by one, with their own messages, because the adopted text
   lists four and this protocol implements what was adopted rather than a logically-equivalent
   subset.

3. **`admitted_root`'s fixture key is renamed `bootstrap`, not kept as `deployment_authority`.**
   The value it holds is no longer an authority object but the request-facing operation, and a
   fixture key that named the old thing would make every call site read as though an authority
   were still being passed.

4. **The Phase 14 execution-context currency interaction is disclosed, not worked around.** A
   capability already issued before a rotation cannot be *executed* afterwards — but that is
   Phase 14's own `execution_context_still_current`, which refuses after any State transition
   whatsoever, and not a retroactive revocation this round introduces. The control therefore
   exercises the capability *before* the rotation to prove it genuinely worked, and asserts
   afterwards only what this round is responsible for: the object and its bound context are
   untouched, and new issuance is what stops (§14.2).

5. **`parse_utc_instant` is public on `engine.py` rather than private and re-exported.** Two
   modules in this package now depend on it, so a leading underscore would be a name that lies
   about its own reach. It is not added to the `runtime` package's own `__all__`: it is an
   intra-package owner, not a public entry point, so `PUBLIC_RUNTIME_ENTRY_POINT_COUNT` is
   untouched.

6. **The removed `bootstrap_projection_execution_capability` name is not re-exported from the
   package.** Exporting a module-level alias for the closure would hand callers a name they could
   import without composing, which is precisely the shape F1 removes.

### 14.6 Round 5 declarations

```text
COMPOSITION_RETURNS_A_BOUND_REQUEST_FACING_SERVICE=true
REQUEST_FACING_OPERATION_IS_A_CLOSURE=true
REQUEST_FACING_OPERATION_HAS_A_PUBLIC_CONSTRUCTOR=false
REQUEST_FACING_BOOTSTRAP_PARAMETER_COUNT=2
DEPLOYMENT_AUTHORITY_PARAMETER_PRESENT_ON_REQUEST_FACING_SIGNATURE=false
TRUST_ANCHOR_PRESENT_ON_REQUEST_FACING_SIGNATURE=false
ROOT_ADMISSION_REF_PRESENT_ON_REQUEST_FACING_SIGNATURE=false
STORE_PROJECT_OR_BINDING_PRESENT_ON_REQUEST_FACING_SIGNATURE=false
RUNTIME_DEPLOYMENT_AUTHORITY_TYPE_EXISTS=false
RUNTIME_DEPLOYMENT_AUTHORITY_NAME_APPEARS_IN_SHIPPED_CODE=false
TRUSTED_RUNTIME_ROOT_TYPE_EXISTS=false
TRUSTED_RUNTIME_ROOT_NAME_APPEARS_IN_SHIPPED_CODE=false
DELETED_ROUND_1_MINTING_FACTORY_REINTRODUCED=false
MODULE_LEVEL_REQUEST_FACING_BOOTSTRAP_EXISTS=false
SENTINEL_PRIVATE_CONSTRUCTOR_OR_ISINSTANCE_USED_AS_THE_TRUST_CONTROL=false
CURRENT_ADMISSION_RECHECKED_ON_EVERY_NEW_CAPABILITY_ISSUANCE=true
CURRENCY_RECHECK_REQUIRES_A_RAW_TRUST_ANCHOR=false
CURRENCY_RECHECK_PRECEDES_GRANT_RESOLUTION=true
CURRENCY_RECHECK_PRECEDES_ANY_ADAPTER_OR_NETWORK_CALL=true
ROTATION_OR_REVOCATION_BLOCKS_NEW_ISSUANCE_FROM_AN_OLD_SERVICE=true
ALREADY_ISSUED_CAPABILITIES_RETROACTIVELY_REVOKED=false
FRESH_COMPOSITION_AT_THE_CURRENT_ADMISSION_SUCCEEDS=true
DECLARATION_VALIDITY_WINDOW_ORDERED_AS_REAL_INSTANTS=true
DECLARATION_VALIDITY_WINDOW_ORDERED_LEXICOGRAPHICALLY=false
INSTANT_PARSING_OWNER_COUNT_IN_THIS_PACKAGE=1
SECOND_TIMESTAMP_GRAMMAR_CREATED=false
RUNTIME_SPECIFIC_TIME_OWNER_CREATED=false
DECLARATION_COMMITTER_READS_A_CLOCK=false
MONOTONIC_TRANSITION_CHAIN_MECHANISM_CHANGED=false
ADMISSION_REGISTRY_CHANGED=false
TRANSITION_CHAIN_CHANGED=false
RUNTIME_IDENTITY_CHANGED=false
SEMANTIC_STATE_SCHEMA_CHANGED=false
NEW_SCHEMA_FILES_ADDED=0
CANONICAL_SCHEMA_COUNT=59
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
TRUSTED_DEPLOYMENT_COMPOSITION_ENTRY_POINT_COUNT=1
RUNTIME_DEPLOYMENT_DECLARATION_COMMIT_ENTRY_POINT_COUNT=1
RUNTIME_ROOT_ADMISSION_COMMIT_ENTRY_POINT_COUNT=1
COMMIT_STATE_TRANSITION_CALL_SITES_IN_THIS_PACKAGE=2
CLOSED_ROUND_1_TO_4_WORK_REGRESSED=false
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
```

## 15. Structural Review Round 6 (P15-R6-F1)

Round 6 of PR #65 confirmed Round 5's F1 (the closure-carried ownership boundary) and F3 (real
UTC instant ordering) closed, and **reopened Round 5's own F2**: the per-call admission recheck
existed and ran, but it ran *once*, at the start of the request, and it never re-established that
the record then resolving was still the record composition had proved. Where this section and an
earlier one differ, this section governs — the same rule every earlier round states.

The recurrence series continues, and Round 6's entry names the step that was still missing:

```text
ROUND 4   the trust decision was STILL A PARAMETER     -> replaced by an OWNERSHIP BOUNDARY
                                                          carried by an opaque VALUE TYPE
ROUND 5   the OWNERSHIP BOUNDARY was carried by a      -> replaced by a CLOSURE, plus a per-call
          PUBLIC DATACLASS, and an already-composed       recheck that the bound admission is
          service minted capabilities from a              still the current one
          superseded admission forever
ROUND 6   the per-call recheck ran ONCE, at the start  -> replaced by TWO BARRIERS over an
          of the request, and only ever read fields       IMMUTABLE COMPOSITION-TIME COMMITMENT:
          the resolved record declared about itself      the second barrier runs immediately
                                                          before issuance, from its own fresh
                                                          Boot, and both recompute identity and
                                                          fingerprint FROM THE RESOLVED BODY
```

### 15.1 P15-R6-F1 — the two open halves of the Round 5 barrier

*Claimed (Round 5, §14.2):* every new capability issuance rechecks the bound admission's
currency, so a rotated or revoked composition authority mints no new capability.

*True, and insufficient in two independently reproducible ways.*

**1. Post-check rotation/revocation race.** The recheck ran at the top of the request-facing
closure. Grants, declarations and subjects were then resolved and every Authority decision
evaluated — real work, taking real time — and the capability was finally constructed and returned
from that **same original Boot snapshot**, with no second barrier anywhere. A canonical rotation
or revocation committing in that window was therefore still followed by a newly issued capability,
which directly violates the adopted condition that rotation and revocation prevent *new capability
issuance*.

```text
t0  Boot #1, recheck passes                 admission A is current
t1  resolve grants/declarations/subjects
t2  evaluate_projection_authorization
t3  canonical rotation A -> B COMMITS       admission A is no longer current
t4  construct ProjectionExecutionContext    <- ROUND 5 ISSUED A CAPABILITY HERE
```

**2. Resolved-record integrity was never re-established.** The recheck schema-validated the
resolved record and then checked four things — generation, status, project_id,
project_binding_ref — and every one of them reads a field *the resolved body itself declares*. It
never recomputed `runtime_root_admission_id` or the semantic fingerprint from that body, and never
compared the body against the admission admitted at composition. A Store-level substitution under
the **current, unmoved id** therefore passed the entire gate:

```text
substituted body        declared_at (or predecessor_ref, or signature) ALTERED
                        generation / status / project_id / project_binding_ref UNCHANGED
                        its own declared id and semantic fingerprint UNCHANGED

Round 5 requirement 1   pointer still names the captured id            PASSES (never moved)
Round 5 requirement 2   generation equals the captured one             PASSES (unchanged)
Round 5 requirement 3   status is ACTIVE                               PASSES (unchanged)
Round 5 requirement 4   restates this Project and Binding              PASSES (unchanged)
signature reverification                                               NOT PERFORMED — the anchor
                                                                       is gone by then, by design
```

Composition proved the ORIGINAL record. The per-call recheck only ever re-proved that certain of
that record's fields still read a particular way.

*Now:* one bounded forward correction, entirely inside `bootstrap.py`. Round 5's closure boundary
and the Round 5 timestamp owner are unchanged.

```text
AT COMPOSITION   bound_admission_id          )  an immutable canonical commitment to the EXACT
                 bound_generation            )  anchor-verified admission, captured in closure
                 bound_semantic_fingerprint  )  cells before any request boundary exists.
                                                The fingerprint is the new one: it was already
                                                independently recomputed and proved equal to its
                                                own declared value by _require_currently_admitted,
                                                and is now also retained.

ON EVERY REQUEST _require_bound_admission_still_current recomputes the CURRENTLY RESOLVED body's
                 own identity and semantic fingerprint FROM THAT BODY, and requires exact equality
                 with the captured commitment. SIX requirements now, not four.

BEFORE ISSUANCE  after ALL grant/declaration/subject resolution and Authority evaluation, and
                 immediately before the capability is constructed, the operation Boots AGAIN and
                 repeats the FULL check — identity, fingerprint, generation, status,
                 Project/Binding, all of it, not a subset. The returned context's
                 state_revision/semantic_fingerprint come from that FINAL Boot.
```

The six requirements, in the order they are checked:

```text
1. the Store's current-admission pointer still names the exact admission id captured at
   composition
2. the resolved current admission carries the exact captured generation
3. the current admission is still ACTIVE
4. it still restates this bound service's own Project and Project Binding
5. its identity, INDEPENDENTLY RECOMPUTED FROM THE BODY NOW RESOLVING, equals the captured
   identity                                                                          [NEW]
6. its semantic fingerprint, likewise recomputed from that body, equals the captured
   fingerprint                                                                       [NEW]
```

**Why recomputing from the body — rather than reading the body's own declared id and fingerprint —
is what actually closes the substitution gap.** A substituted body can declare *anything* about
itself, including an `runtime_root_admission_id` and a
`runtime_root_admission_semantic_fingerprint` forged to match its own tampered content. Comparing
a record's declared fields against that same record's other declared fields is a self-comparison,
and a self-consistent forgery satisfies it trivially. What cannot be forged from the reading side
is the **reference**: the identity and fingerprint this service captured at composition, from the
record whose signature it verified against the deployment's own anchor, before any request
boundary existed. Recomputing the current body's identity from its actual content and comparing
that against the captured reference is the only form of the check that asks the question the
finding names — *is this still the same record?* — rather than *does this record agree with
itself?*

**Why 5 and 6 are checked last.** It is the identical ordering `_require_currently_admitted`
already keeps for its own currency check, and for the identical reason: requirements 2–4 each name
a specific, independently meaningful way the current admission can have stopped being what this
service was composed against, and any body failing one of them necessarily also fails 5.
Recomputing first would collapse every one of those refusals into a single indistinguishable
"identity mismatch" message and stop each control proving what it claims. Recomputing last leaves
5 and 6 isolated by exactly the case nothing else can see — a substituted body whose declared
generation, status, Project and Binding are untouched.

```text
compose at A -> rotation to ACTIVE B lands between barrier 1 and barrier 2  -> no capability
compose at A -> revocation to REVOKED B lands at the same point             -> no capability
compose at A -> body substituted under A's own unmoved id                   -> no capability,
                                                                               refused at
                                                                               barrier 1, with
                                                                               0 authorization
                                                                               evaluations and
                                                                               0 adapter calls
compose at A -> nothing changes                                             -> working capability,
                                                                               controlled adapter
                                                                               reached
unrelated State bump between the two barriers                               -> capability issued;
                                                                               its context
                                                                               snapshots the FINAL
                                                                               Boot
```

**Scope, unchanged and still disclosed.** Already-issued downstream capabilities are still not
retroactively revoked (§14.2); this round moves the boundary from "current at the start of the
request" to "current at the instant of issuance", and claims nothing beyond that. The closure's
bound cells remain rewritable by in-process code that already holds the function object (§14.5,
item 1) — a commitment captured in a cell is a commitment against a *Store*, never against the
process's own memory.

### 15.2 Finding-to-code-to-test matrix

```text
P15-R6-F1  manifestation 1 — post-check rotation/revocation race
  src/manosube_agent_civilization/runtime/bootstrap.py
      compose_trusted_runtime_deployment_authority  captures bound_semantic_fingerprint beside
                                                    bound_admission_id/bound_generation
      bootstrap_projection_execution_capability     second _boot + second
                                                    _require_bound_admission_still_current,
                                                    immediately before the
                                                    ProjectionExecutionContext construction;
                                                    state_revision/semantic_fingerprint sourced
                                                    from that final Boot
      _boot                                         three call points now, one literal call site

  tests/contract/runtime/test_runtime_static_conformance.py
      test_the_admission_barrier_runs_again_immediately_before_the_capability_is_constructed
      test_the_admission_gate_precedes_every_grant_and_authority_call_by_construction (unweakened)
      test_bootstrap_calls_boot_project_exactly_once (unweakened)
  tests/integration/runtime/test_runtime_deployment_authority_composition.py
      test_a_rotation_landing_between_the_two_barriers_returns_no_capability
      test_a_revocation_landing_between_the_two_barriers_returns_no_capability
      test_the_issued_context_snapshots_the_final_boot_not_the_initial_one
      test_an_unchanged_current_admission_still_issues_a_working_capability

P15-R6-F1  manifestation 2 — resolved-record integrity never re-established
  src/manosube_agent_civilization/runtime/bootstrap.py
      _require_bound_admission_still_current        six requirements; 5 and 6 recompute
                                                    runtime_root_admission_id and
                                                    runtime_root_admission_semantic_fingerprint
                                                    from the resolved body and compare against the
                                                    composition-time commitment
                                                    (bound_semantic_fingerprint is its new
                                                    keyword parameter)

  tests/integration/runtime/test_runtime_deployment_authority_composition.py
      test_a_record_body_substituted_under_the_current_id_issues_no_capability
      test_an_unchanged_current_admission_still_issues_a_working_capability

P15-R6-F1  item 6 — the closed request signature is unchanged
  tests/contract/runtime/test_runtime_static_conformance.py
      test_the_admission_barrier_runs_again_immediately_before_the_capability_is_constructed
      test_the_request_facing_bootstrap_accepts_no_trust_deciding_parameter (unweakened)
      test_the_composition_entry_point_owns_every_trust_deciding_parameter (unweakened)
```

### 15.3 Judgment calls made in this round that the adopted findings did not fully pin down

1. **Only the State snapshot moves to the final Boot; the Human Authority binding does not.**
   `human_authority_ref` and `human_authority_signing_key` — and therefore the `decisions`,
   the `authorities`, and the context's own `github_authority_ref` — remain sourced from the
   **first** Boot, exactly as before. They are what the Authority evaluation actually ran against
   and what the returned capability legitimately represents. Re-deriving them from the final Boot
   would let the context claim it was authorized under a Human Authority binding no evaluation
   ever used, if a re-binding landed between the two Boots — a strictly worse defect than the one
   being closed. The adopted text's item 4 names `state_revision`/`semantic_fingerprint`, and only
   those move.

2. **Requirements 5 and 6 are ordered last, after 2–4.** The adopted text requires all six at both
   barriers and does not pin their order. Ordering the recomputation last keeps each of the four
   Round 5 controls refusing for its own distinguishable reason (see §15.1); ordering it first
   would have made 2–4 unreachable in practice, since any body failing them also fails 5.

3. **The substitution control is arranged as a Store proxy, not by overwriting the
   `FileStateStore`'s own record files.** That store independently detects a permanent record file
   diverging from its promoting transaction's staged copy and refuses with its own corruption
   error (`SAME_ID_DIFFERENT_BODY_MUST_FAIL_CLOSED`). A file-level tamper would therefore be
   caught by a pre-existing, unrelated mechanism and would prove nothing about this recheck. The
   proxy returns a substituted body under the unchanged current id, which is precisely the reading
   side of the threat the finding names.

4. **The barrier for the race controls hooks the first grant resolution.** The request-facing
   operation Boots and runs barrier 1 before resolving any grant, and Boots and runs barrier 2
   only after every grant, declaration and subject has resolved and every Authority decision has
   been evaluated — so a grant resolution fires strictly between the two, exactly once for a
   single-grant request. The controls assert the injection genuinely fired, that a real successor
   genuinely committed and now owns the chain pointer, and that the Authority evaluation genuinely
   ran (which is what places the refusal at the *second* barrier rather than the first).

5. **The unrelated-contention control asserts `semantic_fingerprint` equality, not inequality.**
   `semantic_fingerprint` is a pure function of *semantic* State, so committing a record that
   participates in no semantic claim moves `state_revision` and leaves the fingerprint alone. That
   is disclosed in the control's own docstring rather than papered over by manufacturing a
   semantic change: both fields are asserted to equal what is current at the moment of return,
   which is the property item 4 names, and `state_revision` is what makes the two snapshots
   distinguishable at all.

### 15.4 Round 6 declarations

```text
ADMISSION_BARRIERS_PER_REQUEST_FACING_CALL=2
PRE_ISSUANCE_ADMISSION_BARRIER_EXISTS=true
FINAL_BARRIER_READS_ITS_OWN_FRESH_BOOT=true
ISSUED_CONTEXT_STATE_SNAPSHOT_SOURCED_FROM_FINAL_BOOT=true
ISSUED_CONTEXT_AUTHORITY_BINDING_SOURCED_FROM_INITIAL_BOOT=true
COMPOSITION_CAPTURES_AN_IMMUTABLE_ADMISSION_COMMITMENT=true
COMMITMENT_INCLUDES_SEMANTIC_FINGERPRINT=true
PER_CALL_RECHECK_REQUIREMENT_COUNT=6
PER_CALL_RECHECK_RECOMPUTES_IDENTITY_FROM_THE_RESOLVED_BODY=true
PER_CALL_RECHECK_RECOMPUTES_FINGERPRINT_FROM_THE_RESOLVED_BODY=true
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
CLOSURE_CELLS_ARE_UNWRITABLE_BY_IN_PROCESS_CODE=false
ROUND_5_CLOSURE_BOUNDARY_CHANGED=false
ROUND_5_TIMESTAMP_OWNER_CHANGED=false
INSTANT_PARSING_OWNER_COUNT_IN_THIS_PACKAGE=1
ADMISSION_REGISTRY_CHANGED=false
TRANSITION_CHAIN_CHANGED=false
RUNTIME_IDENTITY_CHANGED=false
ENGINE_CHANGED=false
ROUTE_CHANGED=false
DEPLOYMENT_REGISTRY_CHANGED=false
SHIPPED_FILES_CHANGED_THIS_ROUND=1
SEMANTIC_STATE_SCHEMA_CHANGED=false
NEW_SCHEMA_FILES_ADDED=0
CANONICAL_SCHEMA_COUNT=59
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
TRUSTED_DEPLOYMENT_COMPOSITION_ENTRY_POINT_COUNT=1
COMMIT_STATE_TRANSITION_CALL_SITES_IN_THIS_PACKAGE=2
CLOSED_ROUND_1_TO_5_WORK_REGRESSED=false
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
```

## 16. Structural Review Round 7 (P15-R7-F1)

Round 7 of PR #65 confirmed Round 6's two-barrier placement, its closure boundary and the
transition-chain mechanism all closed, and found **one remaining gap in what each barrier
proves**: both of Round 6's recomputations are hashes of `ROOT_ADMISSION_SEMANTIC_FIELDS`, and
that projection deliberately excludes exactly the three fields a Store-level substitution could
still change without moving it. Where this section and an earlier one differ, this section
governs — the same rule every earlier round states.

The recurrence series continues, and Round 7's entry names the last surface left:

```text
ROUND 5   an already-composed service minted           -> per-call currency recheck
          capabilities from a superseded admission
ROUND 6   the recheck ran ONCE and only ever read      -> TWO BARRIERS over an IMMUTABLE
          fields the resolved record declared             COMPOSITION-TIME COMMITMENT, both
          about itself                                    recomputing FROM THE RESOLVED BODY
ROUND 7   what those recomputations read is a          -> the commitment now covers the EXACT
          PROJECTION, and the projection excludes         FULL RECORD, and the declared id and
          exactly the fields a substitution could         fingerprint must equal the recomputed
          still move                                      ones as well as the bound ones
```

### 16.1 P15-R7-F1 — the semantic projection's three deliberate exclusions

*Claimed (Round 6, §15.1):* each barrier re-establishes the resolved record's integrity, by
recomputing its identity and semantic fingerprint from the body now resolving and requiring exact
equality with a commitment captured at composition.

*True, and insufficient in one respect that has three separate manifestations.*

`bound_admission_id` and `bound_semantic_fingerprint` are **both** hashes of
`ROOT_ADMISSION_SEMANTIC_FIELDS` — one canonical projection, hashed twice under two prefixes. That
projection excludes three of the record's own fields, and each exclusion is *correct where it is
made*, for reasons `identity.py` itself states:

```text
runtime_root_admission_id                       excluded: an identity cannot be computed over
                                                itself
runtime_root_admission_semantic_fingerprint     excluded: likewise
signature (algorithm / key_id / value)          excluded: a signature cannot cover its own value
```

Each barrier recomputed `recomputed_id`/`recomputed_fingerprint` **from the body's semantic
fields** and compared them only against the composition-time `bound_admission_id`/
`bound_semantic_fingerprint`. It never checked that the resolved body's own **declared**
`runtime_root_admission_id`/`runtime_root_admission_semantic_fingerprint` equalled those recomputed
values, and it never compared the resolved body's `signature` — or any full-record commitment —
against anything captured at composition. So a substitution changing **only** one of those three
things, leaving every semantic field exactly as it was, passed both barriers undetected:

```text
substitution                                    what each existing check saw

change only the declared                        require_valid_root_admission  PASSES (shape only)
runtime_root_admission_id                       generation/status/project/binding  PASSES
                                                recomputed id == bound id  PASSES (reads other
                                                                                   fields)
                                                recomputed fingerprint == bound  PASSES

change only the declared                        identical: every check above PASSES
runtime_root_admission_semantic_fingerprint

change only signature.value                     identical: every check above PASSES — and the
(or signature.key_id)                           signature is not reverified per call at all, by
                                                design, because the anchor is gone by then
```

In all three cases a capability was issued from a record that is no longer, in every observable
respect, the exact anchor-verified record admitted at composition.

*Now:* one narrow addition, entirely inside `bootstrap.py`. Round 5's closure boundary, Round 6's
two-barrier placement and the transition-chain mechanism are all unchanged, and nothing existing
is replaced — the three semantic cells stay exactly as they are and a fourth is added beside them.

```text
AT COMPOSITION   bound_admission_id            )
                 bound_generation              )  UNCHANGED — all three kept
                 bound_semantic_fingerprint    )
                 bound_full_record_commitment  <- NEW: a deterministic digest of the EXACT full,
                                                  schema-valid, anchor-verified record, computed
                                                  over the very object _require_currently_admitted
                                                  returned rather than a re-resolved copy

AT EACH BARRIER  three further requirements, after the existing six and in the established
                 "recompute-and-compare last" order. NINE requirements now, not six.
```

The nine requirements, in the order they are checked:

```text
1. the Store's current-admission pointer still names the exact admission id captured at
   composition
2. the resolved current admission carries the exact captured generation
3. the current admission is still ACTIVE
4. it still restates this bound service's own Project and Project Binding
5. its identity, INDEPENDENTLY RECOMPUTED FROM THE BODY NOW RESOLVING, equals the captured
   identity
6. its semantic fingerprint, likewise recomputed from that body, equals the captured fingerprint
7. its own DECLARED runtime_root_admission_id equals that recomputed identity — so declared,
   recomputed and bound are one value, not two out of three                          [NEW]
8. its own DECLARED runtime_root_admission_semantic_fingerprint equals that recomputed
   fingerprint — the same three-way equality                                         [NEW]
9. the EXACT FULL-RECORD COMMITMENT over the body now resolving — every field it carries,
   signature.algorithm, signature.key_id and signature.value included — equals the commitment
   captured at composition over the exact anchor-verified record                     [NEW]
```

**Why the projection excludes those three fields, and why that means they need their own
commitment.** The exclusions are not an oversight to be repaired inside `identity.py` — they are
load-bearing. A content address computed over a record that contains that content address is not
computable at all, and a signature that covered its own value could never be produced. So
`ROOT_ADMISSION_SEMANTIC_FIELDS` is right to exclude them, `identity.py` is right to keep
excluding them, and this round changes nothing there. What follows is simply that *something else*
has to commit to them, because a hash of a projection can only ever detect a change inside that
projection. That something else is one deterministic digest over the complete record — deliberately
broader than the semantic fingerprint, and deliberately computed somewhere else, in the one place
that needs a "hash the entire record including its own declared id, fingerprint and signature"
primitive: this per-call integrity recheck, and nothing else in the package.

**Why it reuses `state.canonicalize.canonical_json_bytes` rather than inventing a second
serializer.** This repository has exactly one canonical serialization owner, and `identity.py`
already reads it for every one of its own id/fingerprint derivations. A second way to turn a
canonical record into bytes would be a second notion of *what this record is* — and the entire
value of a full-record commitment is that there is exactly one such notion, so that the bytes
composition hashed and the bytes a barrier hashes can never drift apart. `_full_admission_record_
commitment` therefore imports and calls that same function, under the same `sha256:` encoding every
other digest in this repository uses. It retains no trust anchor and reintroduces none: a record
carries a *signature*, never a key, so committing to the full record adds no anchor-derived value
to anything downstream of composition, and the anchor is still consumed exactly once and discarded.

**Why the three-way declared/recomputed/bound equality is not the self-comparison Round 6
rejected.** Round 6 was right that comparing a record's declared id against its own other declared
fields is a self-comparison a self-consistent forgery satisfies trivially — which is why
requirements 5 and 6 anchor to the *bound* value and must keep doing so. Requirements 7 and 8 do
not weaken that: the bound value remains the anchor of the chain of equalities, and adding the
declared field to it can only ever *narrow* what passes. `declared == recomputed == bound` is
strictly stronger than `recomputed == bound`, never a substitute for it.

**Why 7, 8 and 9 are checked last.** The same ordering rationale §15.1 already states, extended one
step. Requirement 9 is the broadest check in the function — every body failing any of 5–8 also
fails 9 — so putting it first would collapse all of them into one indistinguishable "full-record
commitment mismatch" and 7 and 8 would never refuse for their own reason. Checked last, 9 is
isolated by exactly the case nothing narrower can see: a body whose every semantic field, whose own
declared id and whose own declared fingerprint are all untouched, and whose `signature` alone was
replaced.

```text
compose at A -> only the declared id substituted under A's own unmoved id   -> no capability,
                                                                               refused at barrier
                                                                               1 by requirement 7
compose at A -> only the declared fingerprint substituted                   -> refused by 8
compose at A -> only signature.value substituted                            -> refused by 9
compose at A -> only signature.key_id substituted                           -> refused by 9
        each of the four: 0 authorization evaluations, 0 adapter calls, 0 network calls, and the
        chain pointer never touched — these are substitutions, not rotations
```

**Scope, unchanged and still disclosed.** Everything §15.1's own scope paragraph states still
holds without amendment: already-issued downstream capabilities are still not retroactively
revoked, and the closure's bound cells remain rewritable by in-process code that already holds the
function object. A commitment captured in a cell is a commitment against a *Store*, never against
the process's own memory.

### 16.2 Finding-to-code-to-test matrix

```text
P15-R7-F1  the semantic projection's three deliberate exclusions
  src/manosube_agent_civilization/runtime/bootstrap.py
      _full_admission_record_commitment             NEW private helper: the exact full record,
                                                    including its own declared id, its own declared
                                                    semantic fingerprint and its whole signature
                                                    block, reduced to one deterministic digest
                                                    through state.canonicalize.canonical_json_bytes
      compose_trusted_runtime_deployment_authority  captures bound_full_record_commitment beside
                                                    bound_admission_id / bound_generation /
                                                    bound_semantic_fingerprint (all three kept)
      _require_bound_admission_still_current        nine requirements; 7 and 8 require declared ==
                                                    recomputed == bound for id and fingerprint,
                                                    9 requires the full-record commitment to equal
                                                    the composition-time one
                                                    (bound_full_record_commitment is its new
                                                    keyword parameter; both barrier call sites pass
                                                    it)

  tests/integration/runtime/test_runtime_deployment_authority_composition.py
      test_a_substituted_declared_admission_id_issues_no_capability
      test_a_substituted_declared_semantic_fingerprint_issues_no_capability
      test_a_substituted_signature_value_issues_no_capability
      test_a_substituted_signature_key_id_issues_no_capability
      test_the_composed_service_binds_the_exact_full_record_commitment
      test_a_record_body_substituted_under_the_current_id_issues_no_capability  (Round 6, kept)
      test_an_unchanged_current_admission_still_issues_a_working_capability     (Round 6, kept)

P15-R7-F1  item 6 — the closed request signature is unchanged, again
  tests/contract/runtime/test_runtime_static_conformance.py
      test_the_full_record_commitment_is_barrier_side_only_and_reuses_the_one_serializer
      test_the_admission_barrier_runs_again_immediately_before_the_capability_is_constructed
                                                                               (Round 6, unweakened)
      test_the_request_facing_bootstrap_accepts_no_trust_deciding_parameter    (unweakened)
      test_the_composition_entry_point_owns_every_trust_deciding_parameter     (unweakened)
```

### 16.3 Judgment calls made in this round that the adopted findings did not fully pin down

1. **The helper lives in `bootstrap.py`, not in `identity.py`.** The adopted text left the choice
   open. Nothing else in the package needs a "hash the entire record including its own declared
   id/fingerprint/signature" primitive — it exists solely for this per-call integrity recheck — and
   putting it beside `identity.py`'s three deliberately-projected derivations would invite a future
   reader to treat it as a fourth identity of the record, which it is not. It is kept local, and it
   still reads the one canonical serializer rather than restating one.

2. **The substitute values chosen for the four isolated controls.** The adopted text says only
   "some other schema-valid string", so each is stated here explicitly: the declared id becomes
   `RUNTIME-ROOT-ADMISSION-` + `A`×64 (the schema's own prefix and 64 uppercase hex characters);
   the declared semantic fingerprint becomes `sha256:` + `b`×64 (its own `^sha256:[0-9a-f]{64}$`
   pattern); `signature.value` becomes `c`×128 (its own `^[0-9a-f]{128}$` pattern); and
   `signature.key_id` becomes `TRUST-ANCHOR-0002` against the genuine `TRUST-ANCHOR-0001` (the
   canonical identity grammar `common/identity.schema.json` owns). Each is genuinely schema-valid,
   so `require_valid_root_admission` genuinely passes and no refusal is a schema refusal in
   disguise; and each is genuinely different from the real value, which the controls assert rather
   than assume. Every one of them is deliberately *not* a plausible digest or signature: the point
   is that nothing here verifies the signature, only that the record is still the exact record
   composition proved.

3. **`signature.key_id` is its own control rather than folded into the `signature.value` one.**
   The adopted text says "preferably also". They are kept separate because they say different
   things: replacing the value rewrites *the signature*, while replacing the key id rewrites *whose
   signature this claims to be* — a record still carrying the anchor's own genuine signature bytes
   while naming a different signing key. Both are refused by requirement 9, and the two controls
   assert that separately.

4. **Requirements 7 and 8 are ordered before 9, and all three after 5 and 6.** The adopted text
   requires all three at both barriers and does not pin their order. The ordering follows §15.1's
   own stated rationale exactly: narrower checks first, so each refuses for its own distinguishable
   reason, with the broadest one last where it is isolated by the only case nothing narrower can
   see.

5. **The four controls reuse Round 6's own `_SubstitutedAdmissionBodyStore` unchanged.** Its
   constructor already takes the substituted body whole, so an *isolated* single-field substitution
   is expressed by what is handed to it rather than by a new parameter on it. Extending the class
   would have made four controls that differ in one field look like four different mechanisms. The
   isolation itself is asserted in each test body — every semantic field, and the other three
   excluded positions, proved byte-identical to the genuine original — exactly as Round 6's own
   `declared_at` control already asserts it.

### 16.4 Round 7 declarations

```text
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
PER_CALL_RECHECK_RECOMPUTES_IDENTITY_FROM_THE_RESOLVED_BODY=true
PER_CALL_RECHECK_RECOMPUTES_FINGERPRINT_FROM_THE_RESOLVED_BODY=true
PER_CALL_RECHECK_REQUIRES_DECLARED_EQUALS_RECOMPUTED_EQUALS_BOUND_ID=true
PER_CALL_RECHECK_REQUIRES_DECLARED_EQUALS_RECOMPUTED_EQUALS_BOUND_FINGERPRINT=true
PER_CALL_RECHECK_TRUSTS_THE_RESOLVED_BODYS_OWN_DECLARED_IDENTITY=false
DECLARED_ID_SUBSTITUTION_ISSUES_A_CAPABILITY=false
DECLARED_SEMANTIC_FINGERPRINT_SUBSTITUTION_ISSUES_A_CAPABILITY=false
SIGNATURE_VALUE_SUBSTITUTION_ISSUES_A_CAPABILITY=false
SIGNATURE_KEY_ID_SUBSTITUTION_ISSUES_A_CAPABILITY=false
ISOLATED_SUBSTITUTIONS_REFUSED_BEFORE_AUTHORITY_EVALUATION=true
ROTATION_LANDING_BETWEEN_THE_TWO_BARRIERS_ISSUES_A_CAPABILITY=false
REVOCATION_LANDING_BETWEEN_THE_TWO_BARRIERS_ISSUES_A_CAPABILITY=false
CURRENT_ID_BODY_SUBSTITUTION_ISSUES_A_CAPABILITY=false
UNCHANGED_CURRENT_ADMISSION_STILL_ISSUES_A_WORKING_CAPABILITY=true
UNRELATED_STATE_CONTENTION_BLOCKS_ISSUANCE=false
REQUEST_FACING_BOOTSTRAP_PARAMETER_COUNT=2
NEW_PUBLIC_REQUEST_PARAMETER_ADDED=0
REQUEST_FACING_SIGNATURE_CHANGED_SINCE_ROUND_5=false
CURRENCY_RECHECK_REQUIRES_A_RAW_TRUST_ANCHOR=false
ALREADY_ISSUED_CAPABILITIES_RETROACTIVELY_REVOKED=false
CLOSURE_CELLS_ARE_UNWRITABLE_BY_IN_PROCESS_CODE=false
ROUND_5_CLOSURE_BOUNDARY_CHANGED=false
ROUND_6_TWO_BARRIER_PLACEMENT_CHANGED=false
ROUND_5_TIMESTAMP_OWNER_CHANGED=false
INSTANT_PARSING_OWNER_COUNT_IN_THIS_PACKAGE=1
ADMISSION_REGISTRY_CHANGED=false
TRANSITION_CHAIN_CHANGED=false
RUNTIME_IDENTITY_CHANGED=false
ENGINE_CHANGED=false
ROUTE_CHANGED=false
DEPLOYMENT_REGISTRY_CHANGED=false
SHIPPED_FILES_CHANGED_THIS_ROUND=1
SEMANTIC_STATE_SCHEMA_CHANGED=false
NEW_SCHEMA_FILES_ADDED=0
CANONICAL_SCHEMA_COUNT=59
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
TRUSTED_DEPLOYMENT_COMPOSITION_ENTRY_POINT_COUNT=1
COMMIT_STATE_TRANSITION_CALL_SITES_IN_THIS_PACKAGE=2
CLOSED_ROUND_1_TO_6_WORK_REGRESSED=false
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
```

## 17. Issue #105 — transport-independent SSH observation and grant-gated unattended execution

```text
GOVERNING_ISSUE=#105
ADOPTION=issue #105 comment 5975681963 (SHUKOU, formal adoption)
HANDOFF=issue #105 comment 5975690640 (SHUKOU, implementation handoff to Claude Code)
DELIVERY_BRANCH=agent/issue-105-runtime-observation-transports
DELIVERY_BASE=main @ 6e32bc7b3fddada77f8bcc75656e0453768a9a42
```

This is not a Structural Review round — nothing above claims something the code did not actually
keep. It is a new delivery against a separate, formally adopted Issue, in this document's own
established append-only form: nothing in sections 1–16 is edited, and where this section and an
earlier one differ about anything in `runtime/`'s shared surface, this section governs, the
identical rule every Structural Review round above already states.

### 17.1 Position

Issue #64 shipped exactly one observation method, `HTTP_GET_BOUNDED`, against a VPS or cloud
target reachable over HTTP. Issue #105's own structural difference is transport
**independence**, not a new capability: `observe_runtime_target` already did not care who or
what called it, and nothing about its own semantics names a transport at all. What this delivery
adds is a second, equally bounded `RuntimeAdapter` implementation (`SSH_EXEC_BOUNDED`, for a
target reachable only over SSH), a render-only Capability A (a copy/paste-able manual SSH command
for a Human operator), and a narrow, Human-ratified-grant-gated Capability B (automatic SSH
execution with no Human present at the moment of execution) — plus the Actions-independent
classification that keeps a GitHub Actions quota/runner-allocation failure from ever being
misread as a code, test, or runtime failure.

```text
RUNTIME_OWNER_COUNT=1                       unchanged
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3           unchanged — no fourth canonical route
KERNEL_ELEMENT=NONE_RUNTIME_ADAPTER          unchanged
```

### 17.2 Public signature delta

`observe_runtime_target`, `route_runtime_observation_to_evidence`,
`bootstrap_projection_execution_capability`, and `commit_runtime_deployment_declaration` are
**unchanged** — the same four entries §2 already lists, called with a `boundary` whose
`observation_method` may now be `SSH_EXEC_BOUNDED` as well as `HTTP_GET_BOUNDED`. No fifth
route is added.

```python
# runtime/transport_control.py -- an authorization/rendering layer IN FRONT OF the one
# canonical route above, never a second route, and never re-exported from runtime/__init__.py
# this delivery (the identical "adapters are package-internal" precedent FakeRuntimeAdapter/
# LocalHttpRuntimeAdapter already set -- neither is re-exported either).

require_valid_grant(grant: Any) -> dict[str, Any]
require_grant_permits_transport(grant: Mapping[str, Any], transport: str) -> dict[str, Any]
require_grant_not_expired(grant: Mapping[str, Any], *, now: str) -> dict[str, Any]
render_manual_ssh_command(grant: Mapping[str, Any], *, now: str) -> str
classify_actions_dispatch(*, dispatched: bool, runner_allocated: bool,
                           start_deadline_exceeded: bool) -> str
select_transport(*, actions_status: str, requested_transport: str | None,
                  grant: Mapping[str, Any], now: str) -> str
```

`SshRuntimeAdapter` (in `adapter.py`, alongside `FakeRuntimeAdapter`/`LocalHttpRuntimeAdapter`)
is a third `RuntimeAdapter` implementation, constructed and supplied by the caller exactly as
the other two already are — `observe_runtime_target`'s own `adapter` parameter is unchanged.

### 17.3 Frozen semantic decisions added

11. **A bounded-SSH-observation grant is a narrower authorization gate in front of the existing
    Boundary validation, never a second Runtime/Authority/Evidence/State/Reflow owner, and
    never a substitute for it.** `transport_control.require_valid_grant` and its siblings check
    only "may this exact transport be used for this exact target, right now" — they commit
    nothing, decide no observation outcome, and never replace the identical
    `host`/`port`/`user`/`probe_identity` validation `route.py`'s own Boundary enforcement
    already performs on every call, attended or not.
12. **Tool availability must not create Authority.** `classify_actions_dispatch` reports
    GitHub Actions `AVAILABLE`/`UNAVAILABLE`/`UNKNOWN` from caller-observed dispatch facts
    alone, never inferred or guessed; Actions being `UNAVAILABLE` never, by itself,
    auto-selects `MANUAL_SSH` or `PREAUTHORIZED_UNATTENDED_SSH` — `select_transport` raises
    unless an operator (or a caller with its own policy) explicitly names one, and even an
    explicit `PREAUTHORIZED_UNATTENDED_SSH` request is refused unless a Human-ratified grant
    already named that exact mode for that exact target.
13. **Manual and unattended execution share one command, byte for byte.**
    `render_manual_ssh_command` (Capability A, shown to a Human) and `SshRuntimeAdapter.observe`
    (Capability B's automatic half) both build their SSH invocation through the identical
    `network.render_ssh_command_argv` — the exact command a Human is shown is the exact command
    this package would otherwise run unattended, so the two paths can never silently diverge.
14. **The remote probe command is never caller-supplied text.** `boundary["endpoint"]
    ["probe_identity"]` (and a grant's own `probe_identity`) selects one of exactly two pinned
    identities (`SSH_PROBE_IDENTITIES`), each mapped by the closed `SSH_PROBE_REMOTE_COMMANDS`
    table to one fixed remote command string. No path, argument, or shell fragment reaches the
    remote command from any caller-controlled field — disclosed judgment call, §17.6, item 3.
15. **SSH argument-injection is refused by character set and leading-character, independently
    of shell quoting.** `canonical_ssh_endpoint_host`/`require_safe_ssh_user` refuse a
    `host`/`user` beginning with `-`, because `ssh`'s own argument parser (not a shell) would
    otherwise read a crafted `host`/`user` as a further option rather than as part of the
    `user@host` destination, even though `subprocess.run` is always called with `shell=False`
    and a fixed-length argv. Enforced in both `route.py`'s own zero-call Boundary validation
    and `render_ssh_command_argv` (defense in depth, the identical discipline item 1's own
    `P15-R1-F1` network-scope check already keeps for HTTP).
16. **An SSH transport failure is classified by the identical rule item 5 already states for
    HTTP, extended to `ssh`'s own exit-code vocabulary.** Exit `255` with no parseable probe
    report is `UNAVAILABLE` (or `PERMISSION_DENIED` when stderr names it) — an `ssh`-level
    connection/authentication failure, never folded into the authoritative `NOT_FOUND` the
    remote probe's own `{"ok": false, "reason": "NOT_FOUND"}` report means.

### 17.4 Canonical owner delta

```text
src/manosube_agent_civilization/runtime/
├── types.py                 RUNTIME_OBSERVATION_METHODS now {HTTP_GET_BOUNDED,
│                             SSH_EXEC_BOUNDED}; added SSH_PROBE_IDENTITIES (2 pinned values)
│                             and the closed SSH_PROBE_IDENTITIES -> remote-command-string
│                             mapping SSH_PROBE_REMOTE_COMMANDS
├── engine.py                 require_valid_boundary additionally refuses an SSH boundary
│                             naming an unpinned probe_identity
├── network.py                 added canonical_ssh_endpoint_host / require_safe_ssh_user /
│                             require_ssh_endpoint_within_network_scope / SSH_CONNECT_TIMEOUT_
│                             SECONDS / render_ssh_command_argv (the one argv builder both the
│                             real adapter and the manual-command renderer call) -- still pure,
│                             I/O-free, still importing nothing beyond urllib.parse
├── route.py                   _require_boundary now dispatches on observation_method: an SSH
│                             boundary additionally passes through require_ssh_endpoint_within_
│                             network_scope and require_safe_ssh_user before any adapter call
│                             (see §17.7 -- a gap this delivery's own test-writing caught and
│                             closed before any external review)
├── adapter.py                  added SshRuntimeAdapter -- the third RuntimeAdapter
│                             implementation, stdlib subprocess (invoking the system ssh
│                             binary) only, shell=False, a fixed-length argv built exclusively
│                             through network.render_ssh_command_argv
└── transport_control.py      NEW -- grant verification (require_valid_grant and siblings),
                              manual-command rendering, Actions-independent dispatch
                              classification, and select_transport; imports only engine.py/
                              errors.py/network.py/types.py from this package, and no
                              Authority/Evidence/State/Reflow module at all

01_SCHEMA/runtime/
└── runtime_observation_envelope.schema.json
                              $defs/boundary is now a oneOf discriminated union over
                              boundary_http_get_bounded (the original shape, observation_method
                              const HTTP_GET_BOUNDED) and boundary_ssh_exec_bounded
                              (observation_method const SSH_EXEC_BOUNDED, endpoint {host, port,
                              user, probe_identity}) -- each branch fully self-contained
                              (additionalProperties:false on each, no allOf composition), so an
                              object naming fields from both branches, or an unauthorized field
                              such as a path on the SSH endpoint, matches neither and is refused

scripts/
├── runtime_observation_probe.py   NEW -- the one pinned, stdlib-only, Python 3.8+-compatible
│                                 script SshRuntimeAdapter's own SSH_EXEC_BOUNDED method runs
│                                 remotely; accepts no path/argument from its caller beyond a
│                                 closed probe_identity positional argument; prints exactly one
│                                 closed-shape JSON report to stdout, always exit 0
└── runtime_observation_transport.py
                                  NEW -- the CLI front end for Capability A (render-command) and
                                  the Actions dispatch classification (classify-dispatch),
                                  callable from a Human's own terminal or from a GitHub Actions
                                  step; imports transport_control/network, no new dependency

.github/workflows/
└── runtime_observation.yml        NEW -- workflow_dispatch-only (no push/PR/schedule trigger),
                                  renders a manual SSH command into the job's own step summary;
                                  the GitHub-Actions half of Capability A, never an unattended
                                  trigger of Capability B
```

No second Runtime, Authority, Evidence, State, or Reflow owner is created. `transport_control.py`
imports nothing from `authority`/`evidence`/`state`/`reflow`/`store`, and no `tests.*` module —
proved the identical way `test_runtime_static_conformance.py` already proves it for every other
module in this package, by adding `transport_control` to that suite's own AST-walked module
tuple (it required zero further rule changes: its conventional shape already satisfied every
existing conformance rule). `subprocess` is importable only from `adapter.py`, exactly as
`urllib.request`/`urllib.error` already are, by name, in the identical static check.

### 17.5 Canonical route delta

```text
Capability A -- manual (Human-present, any transport-availability state)
  render_manual_ssh_command(grant, now=...) -> one copy/paste-able command string
  -> a Human runs it themselves, over a connection this package never opens
  -> the Human (or a script they control) feeds whatever the probe printed back into
     observe_runtime_target through the identical canonical route every other observation uses

Capability B -- grant-gated unattended execution (no Human present at invocation time)
  select_transport(actions_status, requested_transport, grant, now)
    -> refuses (zero adapter calls) unless a Human-ratified grant explicitly names
       PREAUTHORIZED_UNATTENDED_SSH for this exact scope, current at `now`
    -> "PREAUTHORIZED_UNATTENDED_SSH"
  observe_runtime_target(..., boundary=<SSH_EXEC_BOUNDED boundary>, adapter=SshRuntimeAdapter())
    -- the identical canonical route Capability A's own Human-run command, HTTP observation,
       and every other call in this package already go through; nothing about how the call
       was authorized changes what the route or the adapter does
  -> canonical Runtime Observation Envelope / Receipt, exactly as any other observation
```

### 17.6 Disclosed judgment calls

1. **The Boundary schema's `oneOf` discriminated union is new in this repository's own
   `01_SCHEMA/` style.** No prior schema in `01_SCHEMA/` names two alternative shapes for one
   field by a `const` discriminator. Each branch is written fully self-contained — no `allOf`
   composition of a shared base — specifically so `additionalProperties: false` on each branch
   stays simple to reason about; the alternative (a shared base plus an `allOf`-composed
   extension per method) raises the well-known `additionalProperties` interaction footgun
   `allOf` composition is known for in Draft 2020-12, and this delivery did not need the field
   reuse that pattern would have bought.
2. **`SshRuntimeAdapter` goes directly into the existing `adapter.py`.**
   `test_runtime_static_conformance.py` names `adapter.py` the one module permitted a
   non-empty forbidden-substring import hit-set without a special-cased exact-set assertion —
   adding a second I/O-performing module would have required extending that static-conformance
   mechanism itself for no structural reason, since the identical "the one module that may
   actually open/spawn something" precedent `LocalHttpRuntimeAdapter` already set covers SSH
   just as well.
3. **SSH probe identities are completely parameterless by design (a deliberately minimal V1
   scope).** No caller-supplied path, filter, or argument ever reaches the remote command —
   `SOURCE_LOG_EXCERPT_BOUNDED` reads one fixed, pre-configured log path baked into
   `scripts/runtime_observation_probe.py` itself at deployment time, never passed by a caller.
   A path-parameterized probe is a distinct, separately-reviewed future extension, not this
   one; the schema's own `additionalProperties: false` on `boundary_ssh_exec_bounded.endpoint`
   refuses an attempted `target_path` (or any other unauthorized) field outright, proved in
   `tests/contract/runtime/test_runtime_boundary_enforcement.py`.
4. **A grant's own `project_id` scopes the authorization a Human ratified, and is not a second
   target-identity check Boundary enforcement already owns.** `transport_control.py` makes no
   claim of enforcing that a grant's `project_id`/`host`/`port`/`user`/`probe_identity` match
   the Boundary a caller separately supplies to `observe_runtime_target` for the identical
   call — matching the right grant to the right target is the calling code's own
   responsibility (the Actions workflow, or an operator's own script), exactly as its own
   module docstring states ("a grant answers only 'may this exact transport be used for this
   exact target, right now'"). Recorded here as a disclosed boundary rather than an assumed
   one, mirroring this repository's own §6, item 5 precedent.
5. **The real local-SSH-fixture vertical proof is reported pending, not claimed.** No
   `ssh`/`sshd`/`ssh-keygen` binary exists in this delivery's own build/test environment
   (confirmed by direct lookup), and installing one would itself be a machine/service
   modification outside this delivery's own authorized scope (the adoption and handoff both
   explicitly prohibit production SSH, credential provisioning, and machine/service
   modification). Every SSH-transport test in this delivery's own suite runs the real
   `observe_runtime_target`/`SshRuntimeAdapter` pipeline with `subprocess.run` mocked to return
   exactly the stdout `scripts/runtime_observation_probe.py` itself emits — proving this
   package's own handling of that exact contract, never a real network/SSH transport. The real
   fixture proof, and the real unattended-dispatch-against-a-real-target proof, are reported
   pending in this delivery's own evidence; this package's own unattended SSH path is never
   actually launched against anything from any test in this delivery.
6. **A structural gap this delivery's own test-writing caught and closed before any external
   review.** Writing the counterexample for an unsafe `user` (`"-oProxyCommand=evil"`) against
   `route.py`'s own zero-call Boundary validation failed with "did not raise" — `require_safe_
   ssh_user` was being called only from inside `render_ssh_command_argv` (reached by
   `SshRuntimeAdapter.observe` and the manual-command renderer), never from `route.py`'s own
   `_require_boundary`. This meant the `user` safety check was not structurally guaranteed "for
   every adapter implementation that exists or will exist" the way §10.1's own `P15-R1-F1`
   network-scope check already is for `host` — exactly the principle that whole correction
   established. Fixed by adding the identical call `route.py`'s `_require_boundary` already
   makes for `require_ssh_endpoint_within_network_scope` alongside a new one for `require_safe_
   ssh_user`. Disclosed here rather than silently folded in, because it is a genuine finding
   about this delivery's own first draft, caught by its own authorship discipline rather than
   by a reviewer.

### 17.7 Required proof layers

**V6 -- transport independence.** `tests/integration/runtime/
test_runtime_transport_independence.py`: the identical canonical route, run once through
`LocalHttpRuntimeAdapter` against a real, disposable local HTTP target, and once through
`SshRuntimeAdapter` with `subprocess.run` mocked to the probe script's own exact contract,
reaches structurally identical `OBSERVED`/`VERIFIED`/Evidence-hand-off semantics on a positive
observation, and structurally identical `UNAVAILABLE` semantics on each transport's own genuine
connection-failure case — proving the route/adapter pipeline's own classification never reads
`observation_method`. The HTTP-transport evidence is a real local network round trip; the
SSH-transport evidence is explicitly disclosed as mocked (§17.6, item 5).

**V7 -- grant-gated unattended dispatch, end to end.** `tests/integration/runtime/
test_runtime_unattended_ssh.py`: the zero-call, real-route proof that a Human-ratified grant's
gate sits genuinely in front of the real `observe_runtime_target` — no grant, an expired grant,
and a grant that does not name `PREAUTHORIZED_UNATTENDED_SSH` are each refused with zero
`subprocess.run` calls, proved by a mock call-count assertion; Actions being `UNAVAILABLE` never
by itself escalates to the unattended transport even when the grant would otherwise permit it
(§17.3, item 12); and the one positive path (a complete, ratified, permitting grant) reaches a
real `OBSERVED`/`VERIFIED` outcome through the identical canonical route, with `subprocess.run`
mocked for the identical disclosed reason V6 states.

Further unit/contract proofs, each extending an existing V1-pattern suite rather than adding a
new one: `tests/unit/runtime/test_runtime_network_scope.py` (the SSH host/user canonicalization
and the one shared `render_ssh_command_argv`, including every unsafe/unpinned-field refusal);
`tests/unit/runtime/test_runtime_transport_control.py` (every pure function in
`transport_control.py` — an unreadable-or-insufficient grant is always refused, never
default-admitted, over a 16-case mutation matrix; the manual-command renderer matches the
shared argv builder exactly; `classify_actions_dispatch`/`select_transport`'s own closed
decision table); `tests/contract/runtime/test_runtime_boundary_enforcement.py` (an SSH endpoint
outside its declared scope, an ambiguous/unsafe SSH host or user, and a malformed SSH endpoint —
including an unpinned `probe_identity` and an unauthorized `target_path` field — each refused
with zero adapter calls); `tests/contract/runtime/test_runtime_adapter_contract.py` (the
`OBSERVED` outcome is reachable through either boundary factory, proving the route's own
outcome classification reads nothing method-specific); `tests/contract/runtime/
test_runtime_static_conformance.py` (`transport_control` added to the AST-walked module set,
satisfying every existing rule with no rule change needed). `tests/unit/runtime/
test_runtime_identity.py` needed no change at all: every identity/fingerprint function there
already treats `boundary`/`target_identity` as an opaque mapping, independent of
`observation_method`.

### 17.8 Explicit non-claims delta

```text
SSH_EXEC_BOUNDED_OBSERVATION_METHOD_IMPLEMENTED=true
MANUAL_SSH_COMMAND_RENDERING_IMPLEMENTED=true
PREAUTHORIZED_UNATTENDED_SSH_GRANT_MODEL_IMPLEMENTED=true
GRANT_GATE_SITS_IN_FRONT_OF_THE_EXISTING_BOUNDARY_VALIDATION=true
GRANT_IS_A_SECOND_RUNTIME_OR_AUTHORITY_OWNER=false
TOOL_AVAILABILITY_CAN_CREATE_AUTHORITY=false
UNATTENDED_SSH_EVER_LAUNCHED_AGAINST_A_REAL_TARGET_IN_THIS_DELIVERY=false
REAL_LOCAL_SSH_FIXTURE_AVAILABLE_IN_THIS_DELIVERYS_BUILD_ENVIRONMENT=false
REAL_SSH_TRANSPORT_VERTICAL_PROOF_STATUS=PENDING
PRODUCTION_SSH_CONNECTION_MADE_IN_THIS_DELIVERY=false
NEW_CREDENTIAL_OR_KEY_PROVISIONED_IN_THIS_DELIVERY=false
MACHINE_OR_SERVICE_MODIFIED_IN_THIS_DELIVERY=false
REMOTE_PROBE_COMMAND_EVER_CALLER_SUPPLIED_TEXT=false
PATH_PARAMETERIZED_PROBE_AUTHORIZED=false
FOURTH_PUBLIC_RUNTIME_ROUTE_ADDED=false
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
RUNTIME_INIT_PY_RE_EXPORTS_SSH_RUNTIME_ADAPTER=false
RUNTIME_INIT_PY_RE_EXPORTS_TRANSPORT_CONTROL=false
STATIC_CONFORMANCE_PROOF_EXTENDED=true
PR_MARKED_READY_FOR_REVIEW_BY_THIS_DELIVERY=false
ISSUE_105_CLOSED_BY_THIS_DELIVERY=false
```

## 18. PR #108 Structural Review Round 1 corrections (F1–F6, E1)

```text
ROUND=1
GOVERNING_REVIEW=PR #108 comment 5978408215
ADOPTION_ID=ADOPT_I105_PR108_SR1_F1_F6_E1
ADOPTION_COMMENT=5978467672
FINDINGS_ADOPTED=7
FINDINGS_CLOSED=7
```

Independent structural review of PR #108's own initial HEAD (`6af171f1f325dbd41e5b1423bda56901ad8bbb7e`)
found the §17 delivery's own claims weaker than the code actually kept, in seven ways. Each is
recorded below as *what was claimed*, *what was true*, and *what the code now does* -- the
identical per-round accumulation this document already keeps for Issue #64's own Rounds 1–7.
Where this section and §17 differ, this section governs.

### 18.1 F1 — grant authenticity is reused from an existing trusted path, not self-asserted

*Claimed:* "a Human-ratified grant" gates every executable SSH path.
*True:* a grant's `decision_authority`/`decision_status` were plain, self-asserted JSON
strings -- a caller could fabricate `{"decision_authority": "SHUKOU", "decision_status":
"RATIFIED", ...}` and every check in `transport_control.py` passed it. Nothing bound a
grant's own declared project/target/scope to the real attempt using it (a grant for one
project was accepted while observing another's target), and nothing stopped a caller from
constructing `SshRuntimeAdapter` directly, bypassing `transport_control.py` entirely.

*Now:* a grant carries a genuine Ed25519 `signature`, verified (`transport_control.
_verify_grant_signature`, composing `binding.signature.verify_ed25519_signature` exactly as
`deployment_declaration.py` already does for its own record kind) against the *exact*
`human_authority_signing_key` a fresh `boot_project` call restores for the attempt's own
`project_id`/`project_binding_id` -- never a caller-supplied or cached key. The grant's own
declared scope (`project_id`, `project_binding_id`, `provider`/`deployment_id`/
`instance_identity`, `host`/`port`/`user`/`probe_identity`, `permitted_fields`) is signed, so
none of it can be forged or altered independently of the signature, and
`require_grant_matches_attempt` independently re-compares every one of those fields against
the real `target_identity`/`boundary` immediately before any subprocess is spawned.
`SshRuntimeAdapter.__init__` itself now requires and fully verifies a grant (signature,
window, `PREAUTHORIZED_UNATTENDED_SSH` permission) -- the gate moved into the one place that
actually spawns a process, so constructing the adapter directly is no longer a bypass.

### 18.2 F2 — a transport label is never, by itself, permission to execute

*Claimed:* Capability A (manual) only renders; Capability B's unattended half executes only
under grant.
*True:* `scripts/runtime_observation_transport.py`'s `observe` subcommand constructed
`SshRuntimeAdapter` unconditionally after `select_transport` returned *any* label, so a
`MANUAL_SSH`-selected attempt still reached the real executable adapter through this CLI.

*Now:* `_cmd_observe` refuses outright (exit 1, zero adapter construction) unless
`select_transport` actually resolved `PREAUTHORIZED_UNATTENDED_SSH` -- the one mode this
package ever executes without a Human present. A `MANUAL_SSH` selection is directed to
`render-command`; a `GITHUB_ACTIONS` selection is directed to the real dispatched workflow
(which itself only renders, never executes, per its own docstring).

### 18.3 F3 — probe artifact identity is a content digest, not a name, and Capability B
covers source *and* log

*Claimed:* a pinned `probe_identity` plus a result-return contract satisfies Capability B.
*True:* `probe_identity` is a string selecting a remote *command*, not a verified artifact --
nothing proved the file actually executed on a target was the reviewed script. `
SOURCE_LOG_EXCERPT_BOUNDED` read only a log path, never source code, contradicting its own
name. `import-output` echoed whatever JSON it was given, with no schema check at all.

*Now:* every probe report self-reports `probe_script_sha256` -- this file's own SHA-256,
computed fresh at run time over its own bytes -- and `SshRuntimeAdapter` refuses
(`MALFORMED`) any report whose digest does not equal
`types.SSH_PROBE_SCRIPT_SHA256`, the one pinned, reviewed value
(`tests/contract/runtime/test_runtime_static_conformance.py`'s own
`test_the_probe_script_digest_pin_matches_the_real_shipped_script` keeps that constant honest
against the real file). `SOURCE_LOG_EXCERPT_BOUNDED` now reads two independently-bounded
fixed paths (`SOURCE_EXCERPT_PATH`, `LOG_EXCERPT_PATH`), each optional, reporting `NOT_FOUND`
only when both are absent. `import-output` now parses the captured text through the identical
closed-shape check (`SshRuntimeAdapter._parse_probe_report`) the real adapter applies, plus
the digest check -- a Human-captured transcript is validated exactly as strictly as an
automatically-captured one.

### 18.4 F4 — I/O bounds, report schema, and exit-code semantics are enforced, not assumed

*Claimed:* bounded reads, a closed report schema, and honest transport-failure classification.
*True:* `subprocess.run(capture_output=True)` buffered however much a target chose to print,
with no ceiling ever checked; `_parse_probe_report` accepted any dict containing an `"ok"`
key, so `{"ok": "false", ...}` (a truthy *string*, not the boolean `false`) was accepted as
genuine, and a nonzero process exit code did not prevent a well-formed-looking report from
being parsed and trusted.

*Now:* `adapter._run_bounded_subprocess` streams a spawned process's stdout/stderr through two
background threads into a hard byte ceiling (the grant's own `max_output_bytes`) and the
calling loop through a hard wall-clock ceiling (the Boundary's own `timeout_seconds`), killing
the process the instant either is exceeded (proved against a real subprocess, not a mock, in
`tests/contract/runtime/test_runtime_adapter_contract.py`). `_parse_probe_report` requires the
*exact* closed key set, `ok` to be a real `bool` (never a truthy string), and every other
field's own declared type. Exit-code handling now precedes report parsing entirely: a nonzero,
non-255 exit is `MALFORMED` regardless of what stdout contains, since the probe script's own
convention is to always exit `0` on its own terms. The grant's own `max_lines` additionally
bounds a `SOURCE_LOG_EXCERPT_BOUNDED` report's self-reported excerpt line counts.

### 18.5 F5 — no workflow input is ever interpolated into executable shell text

*Claimed:* `runtime_observation.yml` only renders a command; it opens nothing.
*True:* `--now "${{ github.event.inputs.now }}"` interpolated the dispatch input directly
into the step's own `run:` script source. GitHub Actions expands that expression *before* the
shell ever sees the script, so a value containing `$(...)` or backticks would be evaluated as
a real command on the runner, before this package's own timestamp validation ever ran.

*Now:* every dispatch input (`now`, `store_root`, `project_id`, `project_binding_id`, and the
pre-existing `grant_json`) reaches its step exclusively through that step's own `env:`
mapping; the shell only ever reads an ordinary `"$NAME"` variable reference, whose value is
never re-parsed as further shell syntax.
`tests/contract/governance/test_merge_source_reflow_workflows.py`'s new
`test_runtime_observation_workflow_interpolates_no_event_input_into_run_script_text` proves
this by AST-adjacent regex over every `run:` block in the file, confirmed to actually detect
the original vulnerable pattern before being proved against the corrected file.

### 18.6 F6 — the governance workflow-enumeration regression, and the `RUNTIME_INDEX.md` scope gap

*Claimed (implicitly, by omission):* every file this delivery touched was within its own
permitted inventory.
*True, in two respects.* First, adding `.github/workflows/runtime_observation.yml` --
required by the original handoff -- broke `tests/contract/governance/
test_merge_source_reflow_workflows.py`'s own exact-three-filename assertion, a real regression
the first delivery disclosed but left unfixed because that test file was outside its own
permitted inventory. Second, `10_RUNTIME/RUNTIME_INDEX.md` was edited (a one-paragraph
pointer to this document's own §17) without that path appearing in the original handoff's
exact permitted-file list at all -- a genuine, if narrow, scope overrun.

*Now:* SHUKOU's PR #108 adoption explicitly supplements both. The governance test's own
closed filename set now admits `runtime_observation.yml` by name, with five new assertions
(dispatch-only trigger, `contents: read` only, no merge/push/comment action, never invokes the
`observe` subcommand, no event-input interpolation into script text) proving its own adopted
properties rather than merely counting it. `10_RUNTIME/RUNTIME_INDEX.md`'s pointer is
retained under this explicit scope supplement -- its earlier edit is disclosed here as having
been outside the original handoff's own inventory, not retroactively recharacterized as
having been authorized at the time it was made.

### 18.7 E1 — verification chronology and the governance failure's own framing, corrected

*Claimed:* "none of the pre-existing suites were weakened to make the focused 462-test result
above pass" and the one governance failure was reported as a "scope boundary artifact."
*True:* the delivery's own commit and push, and the Draft PR's own creation, happened while
the broader (non-focused) full-suite verification was still running in the background --
sequenced that way under the local Stop-hook's own pressure to commit, not because applicable
pre-commit verification had actually finished first, as the handoff's own verification-before-
commit instruction requires. The one real governance-test failure was correctly identified as
caused by this delivery's own new file, but described as a "scope boundary artifact" rather
than named plainly as an unresolved required check this delivery had not yet fixed.

*Now:* this correction round's own commit happens only after every requirement above is
re-verified against the actual corrected tree (§18.8), in the order the handoff requires;
the governance-test regression is fixed outright (§18.6), not merely disclosed as acceptable;
and this section states the original sequencing plainly rather than relabeling it.

### 18.8 Round 1 declarations

```text
GRANT_AUTHENTICITY_IS_A_GENUINE_ED25519_SIGNATURE=true
GRANT_SIGNATURE_VERIFIED_AGAINST_A_FRESH_BOOT_RESTORED_KEY=true
GRANT_SELF_ASSERTED_DECISION_AUTHORITY_STRING_REMOVED=true
GRANT_BINDS_REAL_PROJECT_AND_BINDING=true
GRANT_BINDS_REAL_TARGET_AND_REAL_BOUNDARY_SCOPE=true
SSH_RUNTIME_ADAPTER_REQUIRES_A_VERIFIED_GRANT_AT_CONSTRUCTION=true
DIRECT_ADAPTER_CONSTRUCTION_BYPASSES_THE_GRANT_GATE=false
CLI_OBSERVE_SUBCOMMAND_EXECUTES_NON_UNATTENDED_TRANSPORTS=false
PROBE_REPORT_CARRIES_A_SELF_REPORTED_CONTENT_DIGEST=true
PROBE_SCRIPT_DIGEST_PINNED_AND_KEPT_HONEST_BY_A_TEST=true
SOURCE_LOG_EXCERPT_BOUNDED_COVERS_SOURCE_AND_LOG=true
SUBPROCESS_STDOUT_STDERR_BOUNDED_BY_A_REAL_STREAMING_CAP=true
SUBPROCESS_BOUND_PROVEN_AGAINST_A_REAL_PROCESS_NOT_ONLY_A_MOCK=true
PROBE_REPORT_OK_FIELD_MUST_BE_A_REAL_BOOLEAN=true
NONZERO_NON_255_EXIT_CODE_CAN_EVER_BE_PARSED_AS_A_REPORT=false
WORKFLOW_INPUT_EVER_INTERPOLATED_INTO_RUN_SCRIPT_TEXT=false
GOVERNANCE_WORKFLOW_ENUMERATION_TEST_REGRESSION_FIXED=true
RUNTIME_INDEX_SCOPE_GAP_DISCLOSED_AND_SUPPLEMENTED=true
VERIFICATION_CHRONOLOGY_CORRECTED_IN_THIS_SECTION=true
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
FOURTH_PUBLIC_RUNTIME_ROUTE_ADDED=false
REAL_SSH_TRANSPORT_VERTICAL_PROOF_STATUS=PENDING
PRODUCTION_SSH_CONNECTION_MADE_IN_THIS_CORRECTION=false
NEW_CREDENTIAL_OR_KEY_PROVISIONED_IN_THIS_CORRECTION=false
MERGE_PERFORMED=false
READY_TRANSITION_PERFORMED=false
ISSUE_105_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

## 19. PR #108 Structural Review Round 2 corrections (SR2-F1–F4)

```text
ROUND=2
GOVERNING_REVIEW=PR #108 comment 5979222584
ADOPTION_ID=ADOPT_I105_PR108_SR2_F1_F4
ADOPTION_COMMENT=5979845810
CORRECTION_HANDOFF_COMMENT=5979856829
REVIEWED_HEAD=ecbf956eb0dcef51daf710e8c49ea70104ff4c0d
FINDINGS_ADOPTED=4
FINDINGS_CLOSED=4
```

Independent structural review of Round 1's own corrected HEAD found four further ways the §18
delivery's own claims were weaker than the code actually kept. Each is recorded below as *what
was claimed*, *what was true*, and *what the code now does* -- the identical per-round
accumulation this document already keeps. Where this section and §18 differ, this section
governs.

### 19.1 SR2-F1 — GitHub Actions now actually executes, and automatic unattended fallback is
an explicit, narrowly scoped opt-in

*Claimed:* "transport-independent runtime observation" -- GitHub Actions, manual SSH, and
grant-gated unattended SSH are interchangeable transports for the identical canonical route.
*True:* `.github/workflows/runtime_observation.yml` only ever rendered a command (never
invoked `observe_runtime_target`), and `scripts/runtime_observation_transport.py`'s own
`observe` subcommand refused every transport except `PREAUTHORIZED_UNATTENDED_SSH` outright --
so a `GITHUB_ACTIONS`-resolved attempt could never actually execute the bounded observation at
all, directly contradicting the delivery's own "transport-independent" claim for the one
transport real operational continuity depends on most. `transport_control.select_transport`
also had no automatic-fallback path whatsoever: Actions being unavailable always required an
explicit Human selection, even when a grant had already, explicitly pre-authorized unattended
execution for exactly this case.

*Now:* `SshRuntimeAdapter.__init__` takes a new `transport` keyword (one of
`{"GITHUB_ACTIONS", "PREAUTHORIZED_UNATTENDED_SSH"}`; `MANUAL_SSH` is refused outright at
construction, since a Human running the rendered command themselves is that mode's own entire
authorization act and this package must never construct a live adapter for it) and requires
the grant to explicitly permit *that exact* transport, re-verified live inside `observe()`
exactly as the cached, construction-time permission already was (§19.2). `scripts/
runtime_observation_transport.py`'s `observe` subcommand now constructs this adapter, and
genuinely executes, for either `GITHUB_ACTIONS` or `PREAUTHORIZED_UNATTENDED_SSH`; only
`MANUAL_SSH` is still refused and directed to `render-command`.
`.github/workflows/runtime_observation.yml` gains a second job, `observe`, that genuinely
invokes the `observe` subcommand with `--actions-status AVAILABLE` (the job's own dispatch is
itself the fact that Actions is available for this attempt) and no `--requested-transport` --
resolving to `GITHUB_ACTIONS` automatically through `select_transport`'s own existing,
unchanged preference order. This repository ships no bound Project Store, so a real dispatch
of that job correctly fails closed at grant verification, demonstrating genuine invocation of
the canonical route from inside a real Actions runner without fabricating a target to reach.

A new, separate function, `select_transport_with_automatic_fallback`, is added alongside
`select_transport` (which is itself left entirely unchanged, including every one of its own
existing tests): it resolves to `PREAUTHORIZED_UNATTENDED_SSH` with no per-attempt Human
selection only when `actions_status` is the *confirmed* `"UNAVAILABLE"` (never the ambiguous
`"UNKNOWN"`), no explicit `requested_transport` was given, the grant genuinely verifies and
explicitly permits that transport, and a caller-supplied `attempt_already_satisfied` flag is
`False`. This creates no new authority (`FALLBACK_CREATES_AUTHORITY=false` continues to hold):
the authority already fully pre-exists in the signed grant itself; only the mechanical trigger
is automated. `compute_runtime_observation_attempt_id` is a new, pure, local function (no
persistence, no second Store/Evidence/State owner) a caller may use to correlate its own
bounded record of attempts already satisfied -- this module still owns no attempt ledger of its
own. `scripts/runtime_observation_transport.py`'s `observe` subcommand threads both through new
`--allow-automatic-fallback`/`--attempt-already-satisfied` flags, surfacing `attempt_id` in
every output.

### 19.2 SR2-F2 — grant verification is re-run live at the actual attempt, never merely
trusted from construction

*Claimed:* a verified grant gates every executable SSH path.
*True:* `SshRuntimeAdapter.__init__` verified the grant's signature, Boot-restored authority,
and transport permission exactly once, at construction, and cached the result; `observe()`
only re-matched the *static* fields (`require_grant_matches_attempt`) against the real
target/Boundary, never re-running the signature/Boot/expiry/permission chain itself. An adapter
retained across a longer-lived process (an Actions job's own runtime, an unattended
controller) could expire, have its signing authority rotate, or be superseded between
construction and the actual attempt, with the cached, by-then-stale verification never
re-checked.

*Now:* `observe()` re-runs the complete chain -- `require_grant_permits_transport` then
`require_grant_not_expired` -- fresh, immediately before anything is spawned, using this exact
attempt's own `boundary["time_window"]["issued_at"]` as the live instant (the one instant
`route.py` has already proved the whole attempt genuinely occurs at, before this adapter is
ever reached; the fixed `RuntimeAdapter.observe()` Protocol signature carries no separate `now`
parameter this adapter could otherwise demand). `require_grant_matches_attempt` is further
extended to bind the attempt's own claimed `target_identity.deployment_fingerprint` against the
grant's own newly-signed `deployment_fingerprint` field (a grant issued against one declared
identity is refused once the target has rotated to a new one, even though every stable
provider/deployment/instance coordinate still matches), and to require the attempt's own
`boundary.timeout_seconds` never exceed the grant's own newly-signed `max_timeout_seconds`
ceiling. `transport_control.py` still contains exactly one literal `boot_project` call site
(unchanged; `observe()`'s own live re-check reaches it only by calling the existing,
unmodified `require_valid_grant` again through these same functions, never a second, drifting
restoration path).

### 19.3 SR2-F3 — the output-cap race, self-reported excerpt counters, ancestor-directory
symlinks, and the bounded result-return contract

*Claimed:* bounded subprocess I/O, a closed report schema, and a designated bounded-contents
return contract for Capability B.
*True, in four respects.* (A) `_run_bounded_subprocess`'s own polling loop checked
`overflow.is_set()` only *before* calling `proc.wait()` on each iteration; a short-lived child
writing past the ceiling and exiting immediately could make `proc.wait()` return normally
before either drain thread had a scheduling slot to notice, so the function returned the full,
oversized output with no error at all. (B) a `SOURCE_LOG_EXCERPT_BOUNDED` report's own
self-reported `source_line_count`/`log_line_count` was compared only against the grant's own
`max_lines` -- never against the real line count of the `source_excerpt`/`log_excerpt` string
content it claimed to describe -- so a report lying about its own counter (a negative value, a
non-int, or simply a false one) while shipping more real content than the grant ever authorized
was accepted. (C) the probe script's own `_open_bounded` used `O_NOFOLLOW`, which refuses only
a symlinked *final* path component; a symlink placed in an *ancestor* directory of a configured
excerpt path was never refused. (D) neither the `observe` nor `import-output` CLI subcommand
ever returned the actually-acquired, bounded observed content -- only identifiers a caller
would have to separately resolve against the Store to ever see it -- and `import-output`'s own
file read carried no byte cap at all.

*Now, in the identical order.* (A) `_run_bounded_subprocess` performs one final,
authoritative `overflow.is_set()` recheck immediately after both drain threads are joined, on
every exit path -- proved by a real subprocess that writes past the ceiling and exits with no
delay whatsoever (`tests/contract/runtime/test_runtime_adapter_contract.py::
test_run_bounded_subprocess_catches_an_overflow_from_a_process_that_exits_immediately`). (B)
`SshRuntimeAdapter.observe()` independently recomputes the real line count and real UTF-8 byte
length of `source_excerpt`/`log_excerpt` and requires each to *exactly* equal its own
self-reported counterpart (the one shape a genuinely honest probe always produces) before the
real, recomputed line count is checked against the grant's own `max_lines` bound -- a mismatch
of any kind, in either direction, refuses (`MALFORMED`). (C) the probe script gains
`_open_bounded_strict`, which refuses outright unless a configured path already equals its own
`os.path.realpath` before `_open_bounded` is ever reached -- used for every path an operator
configures (the excerpt paths, the script's own sibling configuration file; never for the
script's own `__file__` self-digest read, which Python may hand this script as a relative path
depending on invocation and is not an attacker-reachable value). (D) `scripts/
runtime_observation_transport.py`'s `observe` subcommand now includes `observed_fields` (the
already-bounded, already-redacted content the route itself derived) in its own output;
`import-output` now reads at most `_IMPORT_OUTPUT_MAX_BYTES` (refusing outright, never silently
truncating, a larger file) and validates the captured report against an explicit, independently
verified grant (§19.4) rather than shape alone.

### 19.4 SR2-F4 — the executed probe artifact is a signed claim, not a public-constant
comparison, and per-deployment paths no longer require editing the reviewed script

*Claimed:* a self-reported `probe_script_sha256` proves the executed file is the reviewed
artifact.
*True, in two respects.* First, that digest was compared only against
`types.SSH_PROBE_SCRIPT_SHA256` -- a *public* constant, visible in this repository's own
shipped source -- so a substitute script could simply print the public expected value back; the
comparison proved only that *some* value matching a public constant was echoed, nothing about
what a specific Human Authority had actually approved running. Second,
`docs/runtime_observation_transports.md` and the probe script's own docstring both instructed
an operator to *edit* `SOURCE_EXCERPT_PATH`/`LOG_EXCERPT_PATH` directly in the reviewed script
before deploying it -- which changes that file's own SHA-256 content digest, directly
contradicting the very digest pin this delivery's own F3 correction relies on.

*Now, in the identical order.* First, a grant's own `RUNTIME_OBSERVATION_GRANT_SEMANTIC_FIELDS`
gains a required, *signed* `probe_script_sha256` field (`identity.py`), required by
`transport_control.require_valid_grant` to equal exactly `types.SSH_PROBE_SCRIPT_SHA256` (the
real, current, test-kept-honest digest of the shipped script); `SshRuntimeAdapter.observe()`
compares a live probe report's own self-reported digest against *this exact, live-reverified
grant's own signed field* (§19.2), never against the bare public constant directly -- a forged
or substituted digest can never be made to agree with a genuine Human Authority signature, even
though it could always trivially be made to agree with a public constant. This is a disclosed,
honestly bounded guarantee, stated here rather than overclaimed: no stronger remote attestation
primitive exists over plain SSH, so what is actually proved is "the Human Authority signed off
on exactly this digest being run," never an independent cryptographic attestation of what code
genuinely executed on the remote target. Second, the probe script gains a sibling, non-digested
configuration file (`runtime_observation_probe.config.json`, resolved only relative to the
script's own real, already-resolved directory) naming `source_excerpt_path`/`log_excerpt_path`;
an absent, unreadable, or malformed configuration file falls back to the script's own shipped
defaults rather than breaking its fixed "always prints one JSON object and exits 0" contract.
The "edit the script constants before deployment" instruction is withdrawn from both the probe
script's own docstring and `docs/runtime_observation_transports.md` §5, replaced with guidance
to configure through the sibling file and to recompute/reissue a new signed grant if this
script's own reviewed source is ever genuinely revised.

### 19.5 Round 2 declarations

```text
GITHUB_ACTIONS_TRANSPORT_EXECUTES_THE_REAL_CANONICAL_ROUTE=true
MANUAL_SSH_EVER_CONSTRUCTS_A_LIVE_ADAPTER=false
AUTOMATIC_UNATTENDED_FALLBACK_IS_AN_EXPLICIT_OPT_IN=true
AUTOMATIC_FALLBACK_REQUIRES_CONFIRMED_UNAVAILABLE_NEVER_UNKNOWN=true
FALLBACK_CREATES_AUTHORITY=false
SELECT_TRANSPORT_ITSELF_LEFT_UNCHANGED=true
ATTEMPT_CORRELATION_IS_LOCAL_PURE_AND_CALLER_OWNED=true
NEW_PERSISTENT_ATTEMPT_LEDGER_CREATED=false
OBSERVE_RERUNS_THE_COMPLETE_GRANT_CHAIN_LIVE_AT_THE_ATTEMPT=true
GRANT_VERIFICATION_EVER_MERELY_CACHED_FROM_CONSTRUCTION=false
GRANT_BINDS_THE_ATTEMPTS_OWN_DEPLOYMENT_FINGERPRINT=true
GRANT_BINDS_A_SIGNED_MAX_TIMEOUT_SECONDS_CEILING=true
TRANSPORT_CONTROL_BOOT_PROJECT_CALL_SITE_COUNT=1
OUTPUT_CAP_RACE_CLOSED_BY_A_POST_JOIN_RECHECK=true
RACE_PROVEN_AGAINST_A_REAL_IMMEDIATE_EXIT_SUBPROCESS=true
EXCERPT_SELF_REPORTED_COUNTERS_CROSS_CHECKED_AGAINST_REAL_CONTENT=true
ACTUAL_EXCERPT_CONTENT_EXCEEDING_MAX_LINES_EVER_ACCEPTED=false
ANCESTOR_DIRECTORY_SYMLINKS_REFUSED_FOR_EVERY_CONFIGURED_PATH=true
CLI_OBSERVE_SURFACES_OBSERVED_FIELDS=true
IMPORT_OUTPUT_READ_IS_BYTE_BOUNDED=true
IMPORT_OUTPUT_VALIDATES_AGAINST_AN_EXPLICIT_VERIFIED_GRANT=true
PROBE_SCRIPT_DIGEST_IS_A_SIGNED_GRANT_FIELD=true
PROBE_DIGEST_COMPARED_AGAINST_THE_SIGNED_GRANT_NEVER_THE_BARE_CONSTANT_ALONE=true
REMOTE_ATTESTATION_LIMITATION_HONESTLY_DISCLOSED=true
PER_DEPLOYMENT_PATHS_CONFIGURED_VIA_A_SIBLING_FILE_NEVER_A_SCRIPT_EDIT=true
EDIT_SCRIPT_BEFORE_DEPLOY_INSTRUCTION_WITHDRAWN=true
PROBE_SCRIPT_SHA256_RECOMPUTED_FOR_THE_REVISED_SCRIPT=true
NEW_TEST_FILE_PATH_ADDED_FOR_SCRIPTS_DIRECTORY=false
SCRIPTS_LEVEL_CORRECTIONS_VERIFIED_BY_MANUAL_INVOCATION_NOT_A_NEW_AUTOMATED_TEST=true
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
FOURTH_PUBLIC_RUNTIME_ROUTE_ADDED=false
REAL_SSH_TRANSPORT_VERTICAL_PROOF_STATUS=PENDING
PRODUCTION_SSH_CONNECTION_MADE_IN_THIS_CORRECTION=false
NEW_CREDENTIAL_OR_KEY_PROVISIONED_IN_THIS_CORRECTION=false
MERGE_PERFORMED=false
READY_TRANSITION_PERFORMED=false
ISSUE_105_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

## 20. PR #108 Structural Review Round 3 corrections (SR3-F1–F4)

```text
ROUND=3
GOVERNING_REVIEW=PR #108 comment 5980755904
ADOPTION_ID=ADOPT_I105_PR108_SR3_F1_F4
ADOPTION_COMMENT=5980804642
CORRECTION_HANDOFF_COMMENT=5980817862
REVIEWED_HEAD=c5e89774fceab66edbeed84f0321e5fbe70dbbf7
FINDINGS_ADOPTED=4
FINDINGS_CLOSED=4
```

Independent structural review of Round 2's own corrected HEAD found four further ways the §19
delivery's own claims were weaker than the code actually kept. Each is recorded below as *what
was claimed*, *what was true*, and *what the code now does* -- the identical per-round
accumulation this document already keeps. Where this section and §19 differ, this section
governs.

### 20.1 SR3-F1 — a genuinely independent fallback controller, not a caller-driven selector

*Claimed:* "automatic unattended fallback" closes design requirement 6 once Actions is
confirmed unavailable.
*True:* ``select_transport_with_automatic_fallback`` only ever *accepted* a caller's own,
already-decided ``actions_status`` string and a caller-supplied ``attempt_already_satisfied``
boolean -- it performed no waiting or observation of its own, so no bounded start-deadline
mechanism existed anywhere in this package, and ``compute_runtime_observation_attempt_id``
varied with ``actions_status``/``now``, so it could never correlate an Actions attempt and a
later SSH fallback as the identical logical operation. An Actions job that never started could
never trigger its own fallback through anything this package shipped.

*Now:* ``transport_control.resolve_bounded_actions_fallback`` is a genuinely independent
controller: it owns a bounded polling loop (bounded by iteration count, never unbounded
wall-clock time) over its own injected ``dispatch_status_provider``, decides for itself once
that bound is exhausted without ever reaching a decisive Actions ``AVAILABLE``, and only then
asks whether the grant already, explicitly preauthorizes ``PREAUTHORIZED_UNATTENDED_SSH`` --
``FALLBACK_AUTHORIZED``/``FALLBACK_REFUSED_NO_GRANT``/``ACTIONS_AVAILABLE_DEFER``/
``ALREADY_SATISFIED``, never a transport this controller invents for itself, and never a new
Human prompt for either the confirmed-unavailable or the deadline-exceeded case.
``compute_runtime_observation_operation_id`` is a new, pure function naming the one stable
operation a controller correlates across an Actions attempt and any SSH fallback (deliberately
never varying with ``actions_status``/``now``); ``RuntimeObservationClaimState`` is a bounded,
in-process, caller-owned record a controller consults before repeating work for the identical
operation -- never a new persistent Store, and disclosed, honestly, as never itself a claim of
distributed exactly-once from a local boolean. ``select_transport_with_automatic_fallback``
itself is unchanged, kept for the narrower case a caller already knows the decisive answer.
``scripts/runtime_observation_transport.py`` gains a new ``run-controller`` subcommand wiring
this to the real ``observe_runtime_target`` route on ``FALLBACK_AUTHORIZED`` alone, with zero
target calls on every other decision.

### 20.2 SR3-F2 — grant expiry is checked against a trusted clock, never a backdatable
Boundary timestamp, and the Boundary's own window is bound inside the grant's own

*Claimed:* ``SshRuntimeAdapter.observe()``'s own live re-verification (SR2-F2) checks the grant
against the actual instant of the attempt.
*True:* that live instant was ``boundary["time_window"]["issued_at"]`` -- a value a CLI/workflow
caller supplies (the shipped CLI built it directly from ``grant["issued_at"]``), and which can
trivially be backdated to make an already-expired grant look current again. Nothing bound the
Boundary's own declared window inside the grant's own authorized window either, so a Boundary
could independently declare an arbitrarily wide window of its own; ``route.py``'s own window
check only ever compared the caller-supplied ``observed_at`` against *that* Boundary's own
bounds, never against the grant's.

*Now:* ``engine.py`` gains ``current_utc_instant()`` -- this package's own one, deliberately
narrow exception to "every function here reads no clock of its own" -- and
``SshRuntimeAdapter.__init__`` takes an injectable ``now_fn`` (defaulting to that function in
production, overridden only by deterministic test fixtures) that ``_reverify_live_grant`` now
calls instead of reading ``boundary["time_window"]["issued_at"]``. ``require_grant_matches_attempt``
additionally requires ``grant["issued_at"] <= boundary.time_window.issued_at`` and
``boundary.time_window.expires_at <= grant["expires_at"]``, as real instants -- a Boundary may
never declare a window wider than what the grant's own Human Authority signature actually
authorized.

### 20.3 SR3-F3 — captured results reach the real canonical route, and path safety is
descriptor-relative, not check-then-open

*Claimed:* ``import-output`` validates a captured transcript as strictly as the real adapter
does, and every configured path is ancestor-symlink-safe (SR2-F3).
*True, in two respects.* (A) ``_cmd_import_output`` parsed the closed report shape and compared
its digest against the grant's own signed value, then stopped -- the grant's own
``max_output_bytes``/``max_lines``/``permitted_fields`` bounds were never applied, the report
was never bound to a real ``target_identity``/request, nothing was redacted, and no canonical
envelope/receipt/Evidence hand-off was ever produced; a captured report naming the wrong
target, an unpermitted field, or a lying self-reported counter was still echoed back as
``{"ok": true, ...}``. (B) the probe script's own ``_open_bounded_strict`` called
``os.path.realpath(path)`` and then, as a separate system call, ``os.open(path, ...)`` -- a
genuine TOCTOU race: a concurrent process can swap an ancestor directory for a symlink between
those two calls, so the ``realpath`` check approves the real ancestry and the following
``open`` call re-resolves the same string path through the now-swapped symlink instead,
independently reproduced by the Structural Advisor.

*Now, in the identical order.* (A) ``SshRuntimeAdapter._classify_probe_result`` is a new
shared method factored out of ``observe()``'s own post-subprocess logic (exit-code handling,
digest and excerpt validation, field projection -- unchanged); a new
``CapturedProbeReportRuntimeAdapter`` subclass (restricted, via ``_ALLOWED_TRANSPORTS``, to
exactly ``MANUAL_SSH``) replays a captured ``(stdout, stderr, returncode)`` triple through that
identical method, and ``_cmd_import_output`` now constructs this adapter and calls the real
``observe_runtime_target`` with it -- a real ``target_identity``/Boundary are now required CLI
arguments, and the real bounded envelope, receipt, and Evidence hand-off are what a captured
transcript reaches; wrong-target, unpermitted-field, and lying-counter input now all surface as
the genuine, bounded ``observation_outcome`` a live subprocess result would also produce, never
a forged ``ok: true``. ``_classify_probe_result`` additionally enforces the grant's own
``max_output_bytes`` directly (defense in depth: a captured transcript never passes through
``_run_bounded_subprocess`` at all, so without this it would have had no enforcement of that
bound whatsoever). (B) the probe script's ``_open_bounded_strict`` is rewritten as a
descriptor-relative, component-by-component ``O_NOFOLLOW`` walk from the filesystem root
(``dir_fd=``, never re-resolving a string path at any step) -- no step ever re-parses an
absolute path from scratch, so there is no window between "check" and "open" for a concurrent
rename or symlink-swap to exploit; the race is kept as a permanent regression, reproduced and
proved closed via direct manual invocation (§20.5).

### 20.4 SR3-F4 — the executed configuration is now a signed claim too, not merely the script

*Claimed:* a probe artifact's own self-reported digest, checked against the grant's own signed
``probe_script_sha256``, proves the file executed is the one the Human Authority approved
(SR2-F4).
*True:* that proves which *script* ran; it says nothing about which *configuration* that
script was run with. Two byte-identical copies of the probe script, deployed beside two
different sibling ``runtime_observation_probe.config.json`` files, report the identical
``probe_script_sha256`` while ``SOURCE_EXCERPT_PATH``/``LOG_EXCERPT_PATH`` -- and therefore
every real file actually read -- can differ completely; independently reproduced by the
Structural Advisor against two such deployments.

*Now:* a grant's ``RUNTIME_OBSERVATION_GRANT_SEMANTIC_FIELDS`` gains a required, signed
``deployment_config_fingerprint`` field; the probe script gains
``_deployment_config_fingerprint()``, a content digest over exactly ``{source_excerpt_path,
log_excerpt_path}`` as currently configured (sibling file or shipped default), included in
every report. ``_classify_probe_result`` compares a live/captured report's own self-reported
value against this exact grant's signed field, the identical "a forged value can never agree
with a genuine signature" discipline ``probe_script_sha256`` already keeps. Disclosed
honestly, unchanged from §19.4: no stronger remote attestation primitive exists over plain
SSH, so what is proved is "the Human Authority signed off on exactly this configuration,"
never an independent cryptographic attestation of what genuinely executed.

### 20.5 Round 3 declarations

```text
RESOLVE_BOUNDED_ACTIONS_FALLBACK_OWNS_ITS_OWN_BOUNDED_POLLING=true
SELECT_TRANSPORT_WITH_AUTOMATIC_FALLBACK_LEFT_UNCHANGED=true
OPERATION_ID_STABLE_ACROSS_ACTIONS_ATTEMPT_AND_SSH_FALLBACK=true
ATTEMPT_ID_AND_OPERATION_ID_ARE_TWO_DISTINCT_IDENTITIES=true
CLAIM_STATE_IS_BOUNDED_IN_PROCESS_NEVER_A_NEW_PERSISTENT_STORE=true
DISTRIBUTED_EXACTLY_ONCE_CLAIMED_FROM_A_LOCAL_BOOLEAN=false
CLI_RUN_CONTROLLER_SUBCOMMAND_EXECUTES_ONLY_ON_FALLBACK_AUTHORIZED=true
SSH_RUNTIME_ADAPTER_LIVE_CLOCK_IS_INJECTABLE_DEFAULTS_TO_REAL_UTC=true
BOUNDARY_TIME_WINDOW_USED_AS_THE_LIVE_INSTANT=false
BOUNDARY_WINDOW_BOUND_INSIDE_THE_GRANTS_OWN_WINDOW=true
IMPORT_OUTPUT_REACHES_THE_REAL_CANONICAL_ROUTE=true
CAPTURED_REPORT_ADAPTER_RESTRICTED_TO_MANUAL_SSH=true
CLASSIFY_PROBE_RESULT_SHARED_BY_LIVE_AND_CAPTURED_PATHS=true
MAX_OUTPUT_BYTES_ENFORCED_FOR_CAPTURED_REPORTS_TOO=true
PROBE_PATH_SAFETY_IS_DESCRIPTOR_RELATIVE_NEVER_CHECK_THEN_OPEN=true
ANCESTOR_SYMLINK_TOCTOU_RACE_KEPT_AS_A_PERMANENT_REGRESSION=true
DEPLOYMENT_CONFIG_FINGERPRINT_IS_A_SIGNED_GRANT_FIELD=true
CONFIG_FINGERPRINT_DISTINGUISHES_IDENTICAL_SCRIPTS_DIFFERENT_CONFIG=true
REMOTE_ATTESTATION_LIMITATION_HONESTLY_DISCLOSED=true
NEW_TEST_FILE_PATH_ADDED_FOR_SCRIPTS_DIRECTORY=false
SCRIPTS_LEVEL_CORRECTIONS_VERIFIED_BY_MANUAL_INVOCATION_NOT_A_NEW_AUTOMATED_TEST=true
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
FOURTH_PUBLIC_RUNTIME_ROUTE_ADDED=false
REAL_SSH_TRANSPORT_VERTICAL_PROOF_STATUS=PENDING
PRODUCTION_SSH_CONNECTION_MADE_IN_THIS_CORRECTION=false
PRODUCTION_ACTIONS_DISPATCH_MADE_IN_THIS_CORRECTION=false
BACKGROUND_SCHEDULE_ACTIVATED_IN_THIS_CORRECTION=false
NEW_CREDENTIAL_OR_KEY_PROVISIONED_IN_THIS_CORRECTION=false
MERGE_PERFORMED=false
READY_TRANSITION_PERFORMED=false
ISSUE_105_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

## 21. PR #108 Structural Review Round 4 corrections (SR4-F1–F4)

```text
ROUND=4
GOVERNING_REVIEW=PR #108 comment 5981307932
ADOPTION_ID=ADOPT_I105_PR108_SR4_F1_F4
ADOPTION_COMMENT=5981338154
CORRECTION_HANDOFF_COMMENT=5981351416
REVIEWED_HEAD=7fc082368749b8d35072aaa8129c4227a399f459
FINDINGS_ADOPTED=4
FINDINGS_CLOSED=4
```

Independent structural review of Round 3's own corrected HEAD found four further ways §20's
own claims were weaker than the code actually kept, and one further way §19/§20's own claims
about what a digest comparison proves were simply incorrect. Each is recorded below as *what
was claimed*, *what was true*, and *what the code now does*. Where this section and §19/§20
differ, this section governs.

### 21.1 SR4-F1 — a genuine elapsed-time deadline, and an actually-integrated claim

*Claimed:* ``resolve_bounded_actions_fallback`` is a genuinely independent controller with its
own bounded start deadline (§20.1).
*True:* that "bounded start deadline" was ``max_polls`` alone -- a bounded iteration count,
never bounded wall-clock time. An instantly-answering provider (the zero-sleep fixture
sequence this delivery's own CLI and tests both still used) could exhaust every poll, and
therefore reach "deadline exceeded", in microseconds -- reproduced by the Structural Advisor
as exactly three ``UNKNOWN`` polls resolving to ``FALLBACK_AUTHORIZED`` in roughly 10
microseconds. Conversely, nothing bounded an individual poll call itself, so a provider whose
own call blocked could prevent the iteration bound from ever being reached either.
``scripts/runtime_observation_transport.py``'s own ``run-controller`` subcommand never
constructed or updated ``RuntimeObservationClaimState`` at all -- ``--claim-already-satisfied``
was still only ever a caller-supplied boolean, the identical shape SR3's own correction
disclosed as needing a caller's "own persistence" but never itself demonstrated. The operation
id also varied only with the grant and the target's own stable coordinates, so *every*
observation request made under one grant against one target collided on the identical
operation id -- a controller could never distinguish a retry of a request it already satisfied
from a completely separate, legitimate, later request.

*Now:* ``resolve_bounded_actions_fallback`` takes a real *start_deadline_seconds*, checked via
an injectable *monotonic_fn* (``time.monotonic`` in production) before every poll -- once
elapsed time already meets or exceeds that bound, no further poll is made, regardless of how
many ``max_polls`` still remain. Each poll receives its own remaining time budget as an
explicit argument (``dispatch_status_provider(remaining_seconds)``), the identical
"bounded-at-the-call-site" discipline every other I/O primitive in this package already keeps;
a provider call already in flight when the deadline is reached cannot be preempted from inside
this module (it imports no scheduler/thread/async primitive -- the one package-wide exception
remains ``adapter.py``'s own bounded subprocess drain), and this limitation is now disclosed
rather than silently assumed away. ``compute_runtime_observation_operation_id`` takes a new,
required *request_id*, distinguishing separate requests under the identical grant/target.
``RuntimeObservationClaimState`` gains ``to_dict``/``from_dict``, and ``run-controller`` gains
``--claim-state-file``: the controller now genuinely loads, consults, and -- only after a real
``FALLBACK_AUTHORIZED`` execution -- updates and persists that claim across separate process
invocations. The function's own return value is now a ``FallbackResolution`` dataclass
(``decision``, ``final_dispatch_status``, ``poll_count``, ``elapsed_seconds``), so a caller can
honestly distinguish a confirmed ``UNAVAILABLE`` fallback from a deadline-exceeded-while-still-
``UNKNOWN`` one, even though both reach the identical decision.

### 21.2 SR4-F2 — the trusted actual instant is checked against the Boundary's own window too

*Claimed:* live grant re-verification checks the trusted actual instant against the grant's own
window, and the Boundary's own window is bound inside the grant's own (§20.2).
*True:* both of those checks are real, but neither one -- nor their combination -- checks the
trusted actual instant against the *Boundary's* own window directly. A grant valid for a wide
window (January through December) that structurally contains a much narrower Boundary window
(one day in January) still passed both checks at a trusted instant (October) that fell inside
the grant's own window but far outside the Boundary's -- reproduced by the Structural Advisor
with ``_reverify_live_grant``/``require_grant_not_expired``/``require_grant_matches_attempt``
unchanged, returning the grant rather than refusing.

*Now:* ``transport_control.require_boundary_within_live_window(boundary, now=live_now)`` is a
new, third check -- called from ``SshRuntimeAdapter._reverify_live_grant`` immediately after
the existing two -- requiring the trusted actual instant to fall inside the Boundary's own
declared ``time_window`` directly, not merely inside whatever broader window the grant happens
to authorize.

### 21.3 SR4-F3 — real capture provenance, real redaction, and the real Evidence handoff

*Claimed:* ``import-output`` reaches the real canonical envelope/receipt/Evidence route, never
a second, unbound return path (§20.3).
*True, in three respects.* (A) ``CapturedProbeReportRuntimeAdapter``'s own
``captured_stderr``/``captured_returncode`` defaulted to ``b""``/``0``, and
``_cmd_import_output`` never required the operator to supply the command's own real exit
status -- a report left behind by a command that genuinely *failed* was classified
identically to one a successful command produced. (B) every CLI subcommand that built a
Boundary hardcoded ``"redaction_fields": []`` regardless of what the grant itself required
redacted -- "hardcoding redaction_fields=[] is not a policy." (C) "reaches the real
envelope/receipt/Evidence" overstated what the code did: the real envelope and receipt were
genuinely produced, but no subcommand ever called
``evidence_handoff.route_runtime_observation_to_evidence`` at all -- the claim was ahead of the
code.

*Now, in the identical order.* (A) ``captured_stderr``/``captured_returncode`` are required
constructor parameters with no default; ``import-output`` gains required ``--captured-exit-
code`` and optional ``--captured-stderr-file``, and a required ``--captured-at`` distinct from
``--now`` -- the trusted instant a Human operator attests the capture actually happened becomes
this call's own ``observed_at``, never invented from import time. (B) a grant gains a required,
signed ``redaction_fields`` field (``RUNTIME_OBSERVATION_GRANT_SEMANTIC_FIELDS``); every CLI
subcommand that builds a Boundary now reads it from the grant (``_redaction_fields_for``); and
``require_grant_matches_attempt`` now requires an attempt's own
``boundary.redaction_fields`` to cover at least the grant's own signed minimum -- a boundary
may redact more than the grant requires, never less. (C) every subcommand that reaches a real
receipt now accepts an optional ``--evidence-request-file``: when given, the real
``route_runtime_observation_to_evidence`` is invoked and the subcommand reports the real
Evidence id/position it returns, or the precise reason it refused (a malformed request, a
missing prerequisite); when omitted, the subcommand honestly reports
``{"status": "NOT_REQUESTED"}`` -- never fabricating a hand-off that never happened, and never
inventing the separate Observation/Difference authority chain a genuine
``verification_observation_request`` requires, which this delivery has no route of its own to
construct from nothing.

### 21.4 SR4-F4 — authorization is checked before any read, and the digest claim is corrected

*Claimed:* a probe artifact's own self-reported digest, checked against the grant's own signed
``probe_script_sha256``/``deployment_config_fingerprint``, means "a forged digest can never be
made to agree with a genuine signature" (§19.4, §20.4).
*True, in two respects.* (A) that claim is simply incorrect: both fields are *public* values
(the grant's own signed value, and the shipped script's own pinned constant), so copying a
known public value into a self-report is not forgery and defeats no signature -- reproduced by
the Structural Advisor with a fabricated report that simply copies the expected public
``probe_script_sha256``/``deployment_config_fingerprint`` and a fabricated ``hostname``,
reaching ``transport_outcome=OBSERVED``. What the comparison actually proves is only that the
probe's self-report *agrees with* the grant's signed expectation -- a consistency check, never
an independent cryptographic attestation of what genuinely executed. (B) the probe script
computed and compared ``deployment_config_fingerprint`` *after* already reading
``SOURCE_EXCERPT_PATH``/``LOG_EXCERPT_PATH`` -- an honest after-the-fact mismatch report, not a
refusal to read an unauthorized configuration in the first place; ``_load_probe_config`` also
silently substituted shipped defaults for an absent/unreadable/malformed sibling configuration
file, with no boundary at all before any read.

*Now, in the identical order.* (A) every claim of this shape in ``adapter.py``,
``transport_control.py``, ``runtime_observation_probe.py``, and
``docs/runtime_observation_transports.md`` is corrected to state plainly that this is a
consistency check, never proof of what genuinely executed, and that no stronger remote
attestation primitive exists over plain SSH -- the comparison itself is unchanged and remains
genuinely useful (a grant's signed expectation still cannot be satisfied by *any* value other
than the one the Human Authority actually approved), only the claim about what satisfying it
proves is corrected. (B) the probe script gains a second sibling file,
``runtime_observation_probe.approved_config.json``, naming the exact
``deployment_config_fingerprint`` a specific deployment is authorized to run under; for
``SOURCE_LOG_EXCERPT_BOUNDED``, this is loaded and compared against the configuration actually
in effect **before** ``_source_log_excerpt`` (the one function that opens either excerpt path)
is ever called. Absence, unreadable content, malformed JSON, and a genuine mismatch are all
refused identically (``reason: "CONFIG_NOT_AUTHORIZED"``), with zero reads of either excerpt
path -- proved, not merely asserted, by a permanent subprocess test that configures the source
path as a named pipe nothing ever writes to: a script that attempted the read first would hang
forever on it, and the bounded test timeout would fire. ``_load_probe_config``'s own existing
tolerance for an absent/malformed *path*-configuration file is deliberately unchanged -- that
tolerance is about which paths a legitimately *authorized* configuration may name, a different
question from whether this configuration is authorized at all.

### 21.5 Round 4 declarations

```text
RESOLVE_BOUNDED_ACTIONS_FALLBACK_HAS_A_REAL_ELAPSED_TIME_DEADLINE=true
EACH_POLL_RECEIVES_ITS_OWN_REMAINING_TIME_BUDGET=true
A_BLOCKING_PROVIDER_CALL_CANNOT_BE_PREEMPTED_FROM_THIS_MODULE_DISCLOSED=true
OPERATION_ID_NOW_TAKES_A_REQUIRED_REQUEST_ID=true
RUNTIME_OBSERVATION_CLAIM_STATE_GAINS_TO_DICT_FROM_DICT=true
RUN_CONTROLLER_CLI_GENUINELY_PERSISTS_CLAIM_STATE_ACROSS_INVOCATIONS=true
FALLBACK_RESOLUTION_PRESERVES_FINAL_DISPATCH_STATUS_HONESTLY=true
BOUNDARY_WINDOW_NOW_CHECKED_AGAINST_THE_LIVE_INSTANT_DIRECTLY=true
CAPTURED_STDERR_AND_RETURNCODE_ARE_NOW_REQUIRED_NO_DEFAULT=true
CAPTURED_AT_IS_DISTINCT_FROM_NOW_AND_BECOMES_OBSERVED_AT=true
GRANT_GAINS_A_REQUIRED_SIGNED_REDACTION_FIELDS_FIELD=true
BOUNDARY_REDACTION_FIELDS_MUST_COVER_THE_GRANTS_OWN_MINIMUM=true
CLI_NO_LONGER_HARDCODES_AN_EMPTY_REDACTION_SET=true
EVIDENCE_HANDOFF_ROUTE_NOW_GENUINELY_INVOKED_WHEN_REQUESTED=true
EVIDENCE_HANDOFF_REPORTS_NOT_REQUESTED_WHEN_NOT_INVOKED_NEVER_FABRICATED=true
NO_NEW_OBSERVATION_DIFFERENCE_AUTHORITY_CHAIN_INVENTED=true
PROBE_SCRIPT_SHA256_FORGERY_CLAIM_CORRECTED_TO_CONSISTENCY_CHECK_ONLY=true
DEPLOYMENT_CONFIG_FINGERPRINT_FORGERY_CLAIM_CORRECTED_TO_CONSISTENCY_CHECK_ONLY=true
PROBE_SCRIPT_GAINS_A_SECOND_APPROVED_CONFIG_SIBLING_FILE=true
SOURCE_LOG_EXCERPT_BOUNDED_AUTHORIZATION_CHECKED_BEFORE_ANY_READ=true
NO_READ_BEFORE_AUTHORIZATION_PROVED_BY_A_PERMANENT_FIFO_BLOCKING_TEST=true
PATH_CONFIG_ABSENT_DEFAULT_TOLERANCE_LEFT_UNCHANGED_DELIBERATELY=true
SCRIPTS_NOW_EXERCISED_BY_PERMANENT_SUBPROCESS_TESTS_IN_EXISTING_AUTHORIZED_FILES=true
NEW_TEST_FILE_PATH_ADDED_FOR_SCRIPTS_DIRECTORY=false
ALL_FOUR_SR3_FINDINGS_RESOLVED_CLAIM_WITHDRAWN_AS_PREMATURE=true
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
FOURTH_PUBLIC_RUNTIME_ROUTE_ADDED=false
REAL_SSH_TRANSPORT_VERTICAL_PROOF_STATUS=PENDING
PRODUCTION_SSH_CONNECTION_MADE_IN_THIS_CORRECTION=false
PRODUCTION_ACTIONS_DISPATCH_MADE_IN_THIS_CORRECTION=false
BACKGROUND_SCHEDULE_ACTIVATED_IN_THIS_CORRECTION=false
NEW_CREDENTIAL_OR_KEY_PROVISIONED_IN_THIS_CORRECTION=false
MERGE_PERFORMED=false
READY_TRANSITION_PERFORMED=false
ISSUE_105_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

## 22. PR #108 Structural Review Round 5 corrections (SR5-F1–F2)

```text
ROUND=5
GOVERNING_REVIEW=PR #108 comment 5986641480
ADOPTION_ID=ADOPT_I105_PR108_SR5_F1_F2
ADOPTION_COMMENT=5986676207
CORRECTION_HANDOFF_COMMENT=5986685146
REVIEWED_HEAD=43629af98604d10f693b71900bad0630701acd11
FINDINGS_ADOPTED=2
FINDINGS_CLOSED=2
```

Independent structural review of Round 4's own corrected HEAD found the remaining two findings
the adoption limited this round to: §21.1's own "real elapsed-time deadline" still conflated a
caller's poll *budget* running out with its wall-clock *deadline* genuinely elapsing, and
§21.4's own pre-read authorization gate was never actually bound to a caller's live, verified
Grant. Each is recorded below as *what was claimed*, *what was true*, and *what the code now
does*. Where this section and §21 differ, this section governs.

### 22.1 SR5-F1 — a poll budget running out is not a deadline elapsing

*Claimed:* ``resolve_bounded_actions_fallback`` checks a real elapsed-time deadline via
*monotonic_fn* before every poll, so an instantly-answering provider can no longer reach
"deadline exceeded" in microseconds (§21.1).

*True, in two respects.* (A) that check ran only *before* each poll, never *after* the loop
stopped for the other reason it can stop: ``max_polls`` simply being exhausted while the
provider had reported nothing but ``UNKNOWN``. The Structural Advisor reproduced
``start_deadline_seconds=60, max_polls=3`` against a provider that answers ``UNKNOWN``
instantly, reaching ``FALLBACK_AUTHORIZED`` (and therefore real unattended SSH authorization)
at an elapsed time of roughly five microseconds -- nowhere near the 60-second deadline a caller
actually declared. Nothing distinguished "the poll budget ran out" from "the deadline
genuinely elapsed"; both silently reached the identical decision. (B) ``dispatch_status_
provider(remaining_seconds)`` passing a number as an argument does not itself bound anything:
the Structural Advisor reproduced ``start_deadline_seconds=0.01, max_polls=1`` against a
provider that sleeps ``0.1`` seconds before answering, and the call still took the full
``~0.1`` seconds -- ten times the declared budget -- because nothing in that call chain could
preempt a callee that simply ignores the number it was handed. §21.1's own disclosed
limitation ("a provider call already in flight cannot be preempted from inside this module")
correctly described the *mechanism* but understated the consequence: a stalled acquisition held
the *entire controller*, not merely one poll, for however long the callee actually took.

*Now:* ``resolve_bounded_actions_fallback`` checks, honestly, which of the two actually
happened once the loop stops with ``status`` still ``"UNKNOWN"``: only when real elapsed time
(``elapsed_seconds``, computed the identical way as before) has genuinely reached
*start_deadline_seconds* is the attempt treated as deadline-exceeded and allowed to reach the
existing grant check; an ``UNKNOWN`` reached purely because ``max_polls`` ran out with real
time still remaining now returns a new, distinct decision,
``DEADLINE_NOT_YET_REACHED`` (added to ``FALLBACK_CONTROLLER_DECISIONS``) -- zero grant checks,
zero SSH, on that decision alone. A confirmed ``UNAVAILABLE`` still reaches the grant check
immediately, exactly as before, regardless of elapsed time; this correction touches only the
``UNKNOWN``-at-loop-exit case. Separately, ``adapter.py`` (the one module the static-
conformance test already permits to import ``threading``, alongside its own bounded subprocess
drain) gains ``bounded_dispatch_status_acquisition``: it runs a raw provider call in a
background daemon thread and joins with a timeout bounded by both the caller's own
``remaining_seconds`` and a second, fixed ``hard_cap_seconds`` ceiling, returning ``"UNKNOWN"``
immediately once that join times out rather than waiting any further for a stalled call to
finish -- never accumulating more than one leaked daemon thread per poll already budgeted for,
so this can never grow an unbounded pool of workers.
``scripts/runtime_observation_transport.py``'s ``run-controller`` subcommand now also gains a
declared NORMAL (non-fixture) dispatch-status source, ``--dispatch-status-file``: an external,
already-authorized process writes ``{"dispatch_status": ..., "observed_at": ...}`` to a local
file, which this subcommand reads fresh on every poll (wrapped in
``bounded_dispatch_status_acquisition``), with a freshness check against ``--now`` bounded by
``--dispatch-status-max-staleness-seconds``; the prior ``--dispatch-status-sequence`` is
renamed to ``--fixture-dispatch-status-sequence`` to make its synthetic nature explicit, and
the two are now mutually exclusive, exactly one required.

### 22.2 SR5-F2 — a local approval file is not a live Grant binding

*Claimed:* the probe script's own sibling ``runtime_observation_probe.approved_config.json``
file closes the pre-read authorization gap by refusing an unauthorized configuration before
any read (§21.4).

*True, in part.* The refusal genuinely runs before any read, exactly as claimed. But the value
it refuses against was an unsigned local JSON file, compared only against *this script's own*
locally-resolved configuration -- it had no connection whatsoever to what the real, currently-
verified bounded-SSH-observation Grant actually authorizes. The Structural Advisor reproduced
exactly that: a swapped sibling path-configuration file, paired with a locally self-consistent
``approved_config.json`` naming *that same swapped configuration's* own digest, was read and
returned successfully by the real probe script run as a real subprocess, with no caller Grant
involved at all. A party with only local filesystem access to the target -- never any access
to a live, freshly Boot-verified Grant -- could keep the two files mutually consistent and
redirect what the probe reads.

*Now:* the sibling ``approved_config.json`` mechanism is removed entirely, along with
``APPROVED_CONFIG_FILENAME``/``APPROVED_CONFIG_MAX_READ_BYTES``/``_load_approved_config_
fingerprint``. ``network.render_ssh_command_argv`` -- the one argv builder both
``SshRuntimeAdapter.observe()`` and ``render_manual_ssh_command`` call through -- now takes a
required keyword-only ``expected_deployment_config_fingerprint`` (validated as a lowercase
64-character hex digest) and appends it to the remote command string it renders; both callers
now pass the exact, freshly live-reverified grant's own signed ``deployment_config_fingerprint``
field. The probe script's own ``main()`` now requires this value as a second, required
positional CLI argument: missing or malformed shape is refused as ``MALFORMED`` before ``run()``
is ever reached (the identical general-invocation-error discipline this script already keeps
for an unrecognized ``probe_identity``); a correctly-shaped value that simply does not equal
this deployment's own locally-computed ``_deployment_config_fingerprint()`` is refused by
``run()`` as ``CONFIG_NOT_AUTHORIZED`` -- in both cases, before ``_source_log_excerpt`` (the one
function that opens either excerpt path) is ever called, proved by the identical permanent FIFO-
blocking test §21.4 already established, now exercising the live-argument gate instead. This
closes the gap because the decisive value now arrives fresh, from outside the target, riding
along on the one specific SSH command the caller's own already-Grant-verified attempt renders
-- never a static file sitting on the target in advance, and never something a party with mere
filesystem access to the target alone can control. Ed25519 signature verification on the target
was considered and rejected: the probe script is deliberately stdlib-only (Python 3.8+, no
``cryptography`` dependency), and a hand-rolled verification would require deploying a trust-
anchor public key as a third static sibling artifact, which closes the "swap files together"
gap no better than binding the value into the live command itself.

A genuine same-name-artifact-replacement test (not a config swap, which this round's own
handoff notes §21.4's own test suite mislabeled as one) is added: a byte-different substitute
probe script, deployed under the identical filename, is run as a real subprocess and leaves its
own execution marker before returning an honest, successful-looking report with its own,
necessarily different, ``probe_script_sha256`` -- proving the substitute genuinely executed,
not merely that it was theorized to run. A companion test feeds that same report shape through
the real classification pipeline (``observe_runtime_target``, through the real
``SshRuntimeAdapter.observe()``) and proves it is refused end to end (``MALFORMED``) on the
digest mismatch alone -- proving the existing ``probe_script_sha256`` check (SR1/SR2/SR3)
genuinely refuses a substitute *script*, never merely a substitute *configuration*.

### 22.3 Round 5 declarations

```text
RESOLVE_BOUNDED_ACTIONS_FALLBACK_DISTINGUISHES_BUDGET_FROM_DEADLINE=true
DEADLINE_NOT_YET_REACHED_DECISION_ADDED_TO_FALLBACK_CONTROLLER_DECISIONS=true
NEW_DECISION_MAKES_ZERO_GRANT_CHECKS_AND_ZERO_SSH=true
BOUNDED_DISPATCH_STATUS_ACQUISITION_ADDED_TO_ADAPTER_PY=true
BOUNDED_ACQUISITION_USES_THREADING_THE_ONE_PERMITTED_MODULE=true
BOUNDED_ACQUISITION_NEVER_ACCUMULATES_AN_UNBOUNDED_WORKER_POOL=true
RUN_CONTROLLER_GAINS_A_DECLARED_NORMAL_NON_FIXTURE_DISPATCH_STATUS_FILE_SOURCE=true
DISPATCH_STATUS_FILE_READ_FRESH_ON_EVERY_POLL_WITH_A_FRESHNESS_CHECK=true
FIXTURE_SEQUENCE_FLAG_RENAMED_TO_MAKE_ITS_SYNTHETIC_NATURE_EXPLICIT=true
FIXTURE_AND_FILE_SOURCES_ARE_MUTUALLY_EXCLUSIVE_EXACTLY_ONE_REQUIRED=true
APPROVED_CONFIG_SIBLING_FILE_MECHANISM_REMOVED_ENTIRELY=true
RENDER_SSH_COMMAND_ARGV_NOW_CARRIES_THE_LIVE_GRANTS_OWN_FINGERPRINT=true
PROBE_SCRIPT_REQUIRES_THE_FINGERPRINT_AS_A_SECOND_POSITIONAL_CLI_ARGUMENT=true
MISSING_OR_MALSHAPED_ARGUMENT_REFUSED_AS_MALFORMED_BEFORE_RUN=true
MISMATCHED_BUT_WELL_SHAPED_ARGUMENT_REFUSED_AS_CONFIG_NOT_AUTHORIZED_BY_RUN=true
NO_READ_BEFORE_AUTHORIZATION_STILL_PROVED_BY_THE_PERMANENT_FIFO_BLOCKING_TEST=true
ED25519_ON_TARGET_CONSIDERED_AND_REJECTED_NO_NEW_CRYPTO_CAPABILITY_ADDED=true
GENUINE_SUBSTITUTE_SCRIPT_EXECUTION_TEST_ADDED_WITH_A_REAL_EXECUTION_MARKER=true
SUBSTITUTE_SCRIPT_REPORT_REFUSED_END_TO_END_THROUGH_THE_REAL_ROUTE=true
NEW_TEST_FILE_PATH_ADDED_FOR_SCRIPTS_OR_ADAPTER_DIRECTORY=false
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
FOURTH_PUBLIC_RUNTIME_ROUTE_ADDED=false
REAL_SSH_TRANSPORT_VERTICAL_PROOF_STATUS=PENDING
PRODUCTION_SSH_CONNECTION_MADE_IN_THIS_CORRECTION=false
PRODUCTION_ACTIONS_DISPATCH_MADE_IN_THIS_CORRECTION=false
BACKGROUND_SCHEDULE_ACTIVATED_IN_THIS_CORRECTION=false
NEW_CREDENTIAL_OR_KEY_PROVISIONED_IN_THIS_CORRECTION=false
MERGE_PERFORMED=false
READY_TRANSITION_PERFORMED=false
ISSUE_105_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

## 23. PR #108 Structural Review Round 6 corrections (SR6-F1–F2)

```text
ROUND=6
GOVERNING_REVIEW=PR #108 comment 5987908311
ADOPTION_ID=ADOPT_I105_PR108_SR6_F1_F2
ADOPTION_COMMENT=5987938197
CORRECTION_HANDOFF_COMMENT=5987947878
REVIEWED_HEAD=72643dfce7cc6e61da81156c745c5b00d61c9429
FINDINGS_ADOPTED=2
FINDINGS_CLOSED=2
```

Independent structural review of Round 5's own corrected HEAD found the two findings this
round's adoption limited correction to: §22.1's own `bounded_dispatch_status_acquisition`
genuinely bounded the *caller's* wait but never the *worker* it spawned, and §22.2's own live
Grant-bound fingerprint closed the configuration gap while leaving the artifact itself
unverified before execution. Each is recorded below as *what was claimed*, *what was true*,
and *what the code now does*. Where this section and §22 differ, this section governs.

### 23.1 SR6-F1 — a thread cannot bound a worker it cannot stop, and an unbound fact is not a request's own fact

*Claimed:* `bounded_dispatch_status_acquisition` ensures a `dispatch_status_provider` call
that ignores its own `remaining_seconds` budget can no longer hold the controller hostage
(§22.1).

*True, in a narrow and ultimately self-defeating sense.* The *caller* genuinely never waited
past its own join timeout. But `join(timeout=...)` only ever stops the thread calling it from
*waiting* -- it neither stops nor contains the *spawned* thread, which keeps running for as
long as the real process lives. The Structural Advisor reproduced this directly against the
exact fetched function: twenty calls with a 1-millisecond acquisition cap, against a harmless
event-blocked provider, all returned `"UNKNOWN"` in roughly 25ms each -- but all twenty
spawned provider threads remained alive throughout, and only finished, one by one, well after
each of their own timeouts, once the blocking fixture event was released. Python has no safe
way to preempt a running thread, so no tuning of this wrapper could ever have actually bounded
the thing it claimed to bound -- only the caller's own patience, never the worker's own
lifetime, and across repeated polls in a persistent process this is an unbounded,
ever-growing population of abandoned workers, exactly the shape the adopted handoff's own
completion condition forbade. Separately, the file this wrapper bounded carried no connection
to *which* logical observation request it was actually a fact about: the Structural Advisor
reproduced a fresh, honestly `UNAVAILABLE` record naming a different request's own
`operation_id` still being accepted and allowed to confirm *this* request's own fallback
decision, and its own freshness check compared against the one static `--now` the whole
invocation started with, not a clock read fresh at each individual poll.

*Now:* `bounded_dispatch_status_acquisition` is removed from `adapter.py` entirely --
Python's inability to safely preempt a thread means no version of this approach could ever
have closed the gap the Structural Advisor demonstrated, so the fix is structural, not
tunable. `scripts/runtime_observation_transport.py`'s `_dispatch_status_file_provider`
performs a direct, synchronous, non-threaded read instead, through a new
`_read_bounded_regular_file` helper: it opens with `O_NONBLOCK | O_NOFOLLOW` (the
`O_NONBLOCK` closing a second, independently reproduced hazard -- a plain blocking `open()` on
a FIFO with no writer present already hangs *before* any type check or read is even reached),
refuses outright, before any read, anything that is not a genuine regular file (clearing
`O_NONBLOCK` again via `fcntl` once that check passes, as a belt-and-suspenders precaution for
the regular-file read itself), and never spawns a thread at all -- zero workers, by
construction, regardless of how many polls or how many separate operations run. The file's
own required shape gains `operation_id`/`source_id` fields: every read now requires
`operation_id` to equal this exact invocation's own computed operation id and `source_id` to
equal the caller's own new, required `--dispatch-status-source-id`, refusing (as the honest
`UNKNOWN` this controller already knows how to handle) on either missing or mismatched value.
Freshness is now checked against `now_fn()` -- a clock read taken fresh at the moment of each
individual poll (`engine.current_utc_instant` in production; injectable only for deterministic
test fixtures) -- never the one static `--now` the whole invocation started with.

### 23.2 SR6-F2 — a live-bound configuration is not a live-verified artifact

*Claimed:* the probe script's own required second CLI argument, bound to the live, Grant-
verified `deployment_config_fingerprint` via the one shared SSH command both callers render,
closes the pre-read authorization gap (§22.2).

*True, for the configuration alone; the artifact itself remained unverified before execution.*
The remote command this package sent still ran a fixed pathname unconditionally --
`probe_script_sha256` was, and had always been, compared only against the probe's own
self-report, computed *after* it had already run. Because both `probe_script_sha256` and
`deployment_config_fingerprint` are public values, a substitute script at the identical
pathname could simply echo the expected digest in its own self-report and have its own,
different code already executed by the time anything noticed a mismatch. The Structural
Advisor independently ran the exact fetched `test_probe_script_substitute_genuinely_executes_
and_reports_a_different_digest` test and its real subprocess helper: it passed specifically
*because* the substitute executed -- an explicit demonstration of the gap, not a completion
proof, exactly as its own name states. Its companion test refused the resulting report only
*after* that execution, through a mocked `_run_bounded_subprocess` return value, which is the
"after the fact" shape the original SR5 handoff's own required control ("refusal BEFORE
substitute execution") explicitly rejected.

*Now:* `network.render_ssh_command_argv` takes a new required
`expected_probe_script_sha256` (validated identically to `expected_deployment_config_
fingerprint`, and passed by both callers -- `SshRuntimeAdapter.observe()` and
`render_manual_ssh_command` -- from the exact, freshly live-reverified grant's own signed
`probe_script_sha256` field, already a required grant field since SR1-F3/SR2-F4). The remote
command it builds is no longer `python3 runtime_observation_probe.py <IDENTITY>
<FINGERPRINT>` directly; it is `python3 -c "<launcher>" <EXPECTED_SHA256> <IDENTITY>
<FINGERPRINT>`, where `<launcher>` is a new fixed, reviewed constant,
`types.SSH_PROBE_LAUNCHER_CODE` -- never built by interpolating any of this call's own
arguments into its own source. That launcher reads the probe script's own bytes into memory
exactly once, independently recomputes their SHA-256, and compares that fresh computation --
never anything the file claims about itself -- against the caller-supplied, live-verified
`<EXPECTED_SHA256>`. Only on an exact match does it `exec()` those *same in-memory bytes*
(rewriting `sys.argv` to `[path, <IDENTITY>, <FINGERPRINT>]` first, so the identical,
unmodified probe script receives the identical two arguments it already required); it never
reopens or rereads the file for execution, so there is no window between verification and use
for the file to be swapped -- a substitute's own code genuinely never runs, not merely "runs
and is reported as untrusted afterward." On any mismatch, or any failure to even read the
file, it prints a closed `{"ok": false, "reason": "ARTIFACT_NOT_AUTHORIZED", ...}` report
without ever reaching `exec()`. Every dynamic value this remote command carries is restricted
to a safe character set (64-lowercase-hex digests, or one of exactly two closed `probe_
identity` enum members) before being appended unquoted, so nothing caller- or grant-controlled
is ever interpolated into the launcher's own source or able to break out of its surrounding
shell quoting. Ed25519 or any other new on-target cryptographic capability remains
unnecessary and unauthorized: the launcher requires nothing beyond the `python3` interpreter
this package's design already requires everywhere.

The demonstration-only test pair this round's own handoff named is replaced with permanent
completion proofs, all run through the real `render_ssh_command_argv` and a real `sh -c`
subprocess (never a real `ssh`/`sshd` binary, unchanged disclosure): a genuine, unmodified
probe script and matching configuration reaches a real, successful bounded observation; a
byte-different same-name substitute is refused with its own execution marker left absent
(never reached); a substitute that fabricates a self-report naming the exact expected public
digests is refused identically, for the identical reason (the launcher never reads anything
the substitute claims); and a structural assertion against `SSH_PROBE_LAUNCHER_CODE`'s own
source confirms exactly one file read, one `compile()`, and one `exec()`, standing in for a
dynamic TOCTOU-race reproduction that the launcher's own single-read design makes impossible
to construct in the first place (there is no second read for a race to target).

### 23.3 Round 6 declarations

```text
BOUNDED_DISPATCH_STATUS_ACQUISITION_REMOVED_FROM_ADAPTER_PY=true
THREAD_BASED_BOUNDING_OF_AN_ARBITRARY_CALLABLE_PROVED_UNSOUND_AND_ABANDONED=true
DISPATCH_STATUS_FILE_READ_IS_NOW_DIRECT_NON_THREADED_AND_TYPE_CHECKED=true
NONBLOCKING_OPEN_CLOSES_THE_FIFO_OPEN_HANG_DISTINCT_FROM_THE_READ_HANG=true
ZERO_WORKER_THREADS_SPAWNED_BY_CONSTRUCTION_FOR_THE_NORMAL_SOURCE=true
DISPATCH_STATUS_FILE_NOW_REQUIRES_OPERATION_ID_AND_SOURCE_ID_CORRELATION=true
DISPATCH_STATUS_SOURCE_ID_FLAG_ADDED_REQUIRED_WITH_DISPATCH_STATUS_FILE=true
FRESHNESS_NOW_CHECKED_AGAINST_A_CLOCK_READ_FRESH_AT_EACH_POLL=true
RENDER_SSH_COMMAND_ARGV_GAINS_REQUIRED_EXPECTED_PROBE_SCRIPT_SHA256=true
REMOTE_COMMAND_IS_NOW_A_FIXED_LAUNCHER_NEVER_BUILT_BY_INTERPOLATION=true
LAUNCHER_READS_SCRIPT_BYTES_EXACTLY_ONCE_VERIFIES_THEN_EXECS_SAME_BYTES=true
NO_SECOND_READ_FOR_EXECUTION_TOCTOU_WINDOW_CLOSED_BY_CONSTRUCTION=true
SUBSTITUTE_SCRIPT_NEVER_REACHES_EXEC_ON_ANY_DIGEST_MISMATCH=true
SUBSTITUTE_ECHOING_EXPECTED_PUBLIC_DIGESTS_STILL_REFUSED_BEFORE_EXECUTION=true
DEMONSTRATION_ONLY_TEST_PAIR_REPLACED_WITH_PERMANENT_COMPLETION_PROOFS=true
NO_NEW_CREDENTIAL_SERVICE_OR_DEPLOYMENT_REQUIRED_BY_EITHER_FIX=true
NO_ED25519_OR_OTHER_NEW_ON_TARGET_CRYPTO_CAPABILITY_ADDED=true
NEW_TEST_FILE_PATH_ADDED_FOR_SCRIPTS_OR_ADAPTER_DIRECTORY=false
PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3
FOURTH_PUBLIC_RUNTIME_ROUTE_ADDED=false
REAL_SSH_TRANSPORT_VERTICAL_PROOF_STATUS=PENDING
PRODUCTION_SSH_CONNECTION_MADE_IN_THIS_CORRECTION=false
PRODUCTION_ACTIONS_DISPATCH_MADE_IN_THIS_CORRECTION=false
BACKGROUND_SCHEDULE_ACTIVATED_IN_THIS_CORRECTION=false
NEW_CREDENTIAL_OR_KEY_PROVISIONED_IN_THIS_CORRECTION=false
MERGE_PERFORMED=false
READY_TRANSITION_PERFORMED=false
ISSUE_105_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

## 24. Issue #105 isolated-deployment-identity correction

```text
GOVERNING_RECORD=Issue #105 comment 6006404738
ADOPTION_ID=ADOPT_I105_ISOLATED_DEPLOYMENT_IDENTITY_PATH_20261006
ADOPTION_COMMENT=6006432653
CORRECTION_HANDOFF_COMMENT=6006445961
AUTHORIZED_BASE_MAIN=8030acdef43cdb7c31ac7cb71d7b4c27a282d6b3
AUTHORIZED_BRANCH=agent/issue-105-isolated-deployment-identity
FINDING_ID=D-I105-ISOLATED-PROBE-DEPLOYMENT-IDENTITY-PATH
```

PR #108 merged as `8030acdef43cdb7c31ac7cb71d7b4c27a282d6b3`; this correction is a fresh branch
from that merged main, never a reopening of that PR. §22/§23 above continue to describe the
artifact PR #108 actually shipped and are kept unweakened as evidence of that artifact; this
section records a subsequent, independently adopted correction layered on top of it.

### 24.1 The real-target proof blocker

*Reported (comment 6006404738).* `scripts/runtime_observation_probe.py`'s own
`DEPLOYMENT_IDENTITY_PATH` was a single fixed constant
(`/etc/manosube/deployment_fingerprint`), with no sibling-config override of any kind --
unlike `SOURCE_EXCERPT_PATH`/`LOG_EXCERPT_PATH`, which §19 (SR2-F4) already made configurable
through `runtime_observation_probe.config.json`. On SHUKOU's own real target, under the test
account actually available, nothing readable existed at that fixed path, and the sibling
config exposed no key that could redirect it. `_read_deployment_identity` therefore always
returned `None`, and the canonical route's own identity-mismatch check
(`route.py`'s comparison of `observed_deployment_identity` against a target's declared
`deployment_fingerprint`) can never positively attest a null identity against a non-null
declared target -- so no real-VPS proof of a genuine, positive identity match was reachable at
all, through no fault of the route's own logic, which was already doing exactly what it
should with the only input the probe could ever give it.

### 24.2 The fix

`deployment_identity_path` is added as a third, optional key to the existing sibling
`runtime_observation_probe.config.json` file, read with the identical
"configured-with-fallback-to-shipped-default" discipline `source_excerpt_path`/
`log_excerpt_path` already use (`EFFECTIVE_DEPLOYMENT_IDENTITY_PATH`, in
`scripts/runtime_observation_probe.py`). No second grant field, Authority, observation
outcome, or Evidence owner is introduced: the existing signed `deployment_config_fingerprint`
field a bounded-SSH-observation grant already carries (§20, SR3-F4) is extended to cover all
three paths (`deployment_identity_path`, `source_excerpt_path`, `log_excerpt_path`) in its one
JSON digest, rather than minting a parallel mechanism for the third path alone.

The pre-read authorization gate §22.2 (SR5-F2) already keeps for `SOURCE_LOG_EXCERPT_BOUNDED`
is moved to run before `_read_deployment_identity` is ever called, for **both** pinned probe
identities. Before this correction, `OS_HEALTH_SNAPSHOT_BOUNDED` never read any configurable
path, so gating it was not yet a live concern; now that the identity path may itself be
configured, leaving `OS_HEALTH_SNAPSHOT_BOUNDED` ungated would have reopened, through the
"lighter" probe identity, precisely the unsigned configured-path-read-before-authorization
defect SR4-F4/SR5-F2 already closed for the other one. `run()` now checks
`expected_deployment_config_fingerprint == deployment_config_fingerprint` immediately after
the `probe_identity` membership check and before any branch reads anything, refusing
`CONFIG_NOT_AUTHORIZED` identically for either identity on any mismatch.

An absent, unreadable, or empty configured identity path continues to report
`deployment_identity: null`, exactly as the prior, fixed path already did on failure --
`_read_deployment_identity` fabricates nothing and raises nothing; `route.py`'s own
identity-mismatch comparison is unmodified and continues to refuse any positive `VERIFIED`
attestation whenever the observed identity is `null` against a non-null declared target. The
existing descriptor-relative, no-follow, ancestor-symlink-safe bounded-read mechanism
(`_open_bounded_strict`, SR3-F3(B)) is reused unchanged for the identity path; no new read
primitive was introduced.

### 24.3 Breaking change, disclosed

Folding a third path into `_deployment_config_fingerprint`'s own JSON payload changes every
deployment's own computed fingerprint, so every grant signed against the prior, two-path
digest no longer matches and is refused as `CONFIG_NOT_AUTHORIZED` -- for both pinned probe
identities -- the moment this corrected script is deployed. This is the deliberate, disclosed
consequence of binding the grant to the exact configuration genuinely in effect (SR3-F4's own
purpose); no retroactive rebinding of an old grant to the new digest is performed or possible.
Every target this correction's probe script is deployed to requires a freshly ratified grant
naming the new three-path `deployment_config_fingerprint`; see
`docs/runtime_observation_transports.md` §5 for the exact migration note.

### 24.4 Declarations

```text
DEPLOYMENT_IDENTITY_PATH_MADE_CONFIGURABLE_VIA_EXISTING_SIBLING_CONFIG=true
NO_SECOND_GRANT_AUTHORITY_OBSERVATION_OR_EVIDENCE_OWNER_INTRODUCED=true
DEPLOYMENT_CONFIG_FINGERPRINT_NOW_COVERS_THREE_PATHS=true
PRE_READ_AUTHORIZATION_GATE_NOW_COVERS_BOTH_PINNED_PROBE_IDENTITIES=true
OS_HEALTH_SNAPSHOT_BOUNDED_NO_LONGER_AN_UNSIGNED_CONFIGURED_PATH_ESCAPE=true
HONEST_NULL_IDENTITY_ON_FAILURE_PRESERVED_NEVER_FABRICATED=true
ROUTE_PY_IDENTITY_MISMATCH_LOGIC_UNCHANGED=true
DESCRIPTOR_RELATIVE_NO_FOLLOW_ANCESTOR_SYMLINK_DEFENSE_REUSED_UNCHANGED=true
LAUNCHER_VERIFY_BEFORE_EXECUTE_MECHANISM_UNCHANGED=true
SSH_PROBE_SCRIPT_SHA256_RECOMPUTED_AND_UPDATED_IN_TYPES_PY=true
EXISTING_TWO_PATH_GRANTS_REFUSED_AS_CONFIG_NOT_AUTHORIZED_NO_RETROACTIVE_REBINDING=true
PR_108_EVIDENCE_PRESERVED_UNCHANGED_AS_EVIDENCE_OF_THE_OLD_ARTIFACT=true
PR_108_MERGED_HEAD_8030ACD_NEVER_REOPENED_OR_ALTERED=true
VPS_EXECUTION_PERFORMED=false
CREDENTIAL_PROVISIONED_OR_CHANGED=false
SYSTEM_CONFIGURATION_CHANGED=false
DOWNSTREAM_APPLICATION_CHANGED=false
MERGE_PERFORMED=false
READY_TRANSITION_PERFORMED=false
ISSUE_105_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

## 25. PR #110 Structural Review Round 1 correction (F1/F2/E1)

```text
GOVERNING_ISSUE=#105
AUTHORIZED_PR=#110
REVIEW_COMMENT=6007573071
ADOPTION_ID=ADOPT_I105_PR110_SR1_F1_F2_E1_20261006
ADOPTION_COMMENT=6007973882
HANDOFF_COMMENT=6007979640
AUTHORIZED_START_HEAD=c9798bda79ed718b56c2bc3719921dcc627ee545
AUTHORIZED_BASE_MAIN=8030acdef43cdb7c31ac7cb71d7b4c27a282d6b3
FINDINGS_ADOPTED=F1,F2,E1
```

Independent Structural Advisor review of this correction's own prior HEAD (`c9798bd`, §24
above) found the review hashed the actual fetched probe script bytes
(`d613231acaee104ba227b769bc1083c16fbd4f46e62dd66ca9a84f55742b2c85`, confirmed to match
`types.py`) and confirmed the core gate-ordering fix itself correct, while finding three gaps
in the delivered completion evidence, each recorded below as *what was found* and *what the
code/docs/tests now do*.

### 25.1 F1 — the required real-probe → canonical receipt → Store-resolved Evidence proof was missing

*Found:* the prior round's own isolated-identity tests ran the real probe subprocess but
stopped at its bare JSON report -- they never called `observe_runtime_target` or
`route_runtime_observation_to_evidence`, used a plain configuration digest rather than a
signed grant, and used `"isolated-proof-identity-001"` rather than this codebase's own
canonical `sha256:<64 hex>` identity shape. Absent/empty/unreadable/wrong identity were not
carried through the canonical route; the changed-identity-path digest test never invoked the
real probe; the old-two-path refusal test did not instrument configured-file reads for either
profile; the default-fallback test silently assumed the real shipped default path
(`/etc/manosube/deployment_fingerprint`) is absent on whatever host runs the suite.

*Now:* `tests/integration/runtime/test_runtime_unattended_ssh.py` adds
`test_real_probe_report_over_an_isolated_identity_reaches_observed_verified_and_evidence` and
its `SOURCE_LOG_EXCERPT_BOUNDED` sibling -- each writes a canonical-format isolated identity
file, deploys the real shipped probe beside a genuinely matching three-path sibling config,
runs it as a real subprocess (`_run_probe_script_bytes`, returning the genuine, unmodified
stdout bytes, never a hand-written stand-in), and carries that exact report through
`CapturedProbeReportRuntimeAdapter` (the existing, unchanged PR #108 SR3-F3(A) route for a
real captured transcript) into the real `observe_runtime_target`, against a target whose own
Store-committed `deployment_fingerprint` and a genuinely Ed25519-signed grant's
`deployment_fingerprint`/`deployment_config_fingerprint` both genuinely equal that same
identity value. The resulting real receipt is handed to the real, unchanged
`route_runtime_observation_to_evidence`; every reference/fingerprint/provenance value
asserted is read back from what those functions actually returned. This is a *derived*
Evidence record `route_runtime_observation_to_evidence` already returns on every call site in
this file; this correction asserts that return value exactly as every other such call site
does and introduces no new Store-commitment claim and no new persistence owner.

`test_real_probe_identity_failure_modes_never_reach_verified_through_the_canonical_route`
carries all four cases -- absent, empty, unreadable (a directory in the identity path's own
place: opening a directory for reading always raises `IsADirectoryError`, an `OSError`
subclass, deterministically and regardless of the test runner's own privilege level, which
root-run suites cannot force through ordinary permission bits) -- and a genuinely wrong
canonical-format value, through the identical real-probe-to-real-route pipeline, and asserts
`IDENTITY_MISMATCH`/`FAILED`, never `OBSERVED`/`VERIFIED`, for every one.

`test_probe_script_a_changed_identity_path_changes_the_deployment_config_fingerprint` now
deploys and runs the real shipped probe twice, each beside a config differing only in
`deployment_identity_path`, and compares the two *self-reported* fingerprints the real
subprocess actually computed, rather than two calls to this test file's own replica function
alone.

`test_probe_script_zero_configured_file_reads_on_mismatch_for_both_profiles` places all three
configured paths (identity, source, log) as named pipes nothing ever writes to -- which block
forever on any process that actually opens them for reading -- supplies a mismatched
commitment, and asserts a prompt `CONFIG_NOT_AUTHORIZED` refusal for *both* pinned probe
identities within a bounded timeout; a probe that read any one of the three before its own
authorization gate would hang and the test's own timeout would fire.

`test_probe_script_omitted_identity_path_config_falls_back_to_the_shipped_default` no longer
asserts `report["deployment_identity"] is None` -- the genuine proof this test establishes
(the real probe's own live-computed fingerprint, with the key omitted, matching this file's
own `_config_fingerprint` helper's default-path computation) holds regardless of what, if
anything, exists at the real shipped default path on the host running the suite.

### 25.2 F2 — the operator guide instructed a now-refused health invocation

*Found:* `docs/runtime_observation_transports.md` §5 still told an operator to sanity-check
deployment with `OS_HEALTH_SNAPSHOT_BOUNDED` and sixty-four zeros, on the premise that health
mode "never compares it to anything" -- false since §24 above moved the pre-read
`deployment_config_fingerprint` gate in front of both pinned probe identities. The review
independently executed that exact invocation against the corrected script and confirmed
`{"ok": false, "reason": "CONFIG_NOT_AUTHORIZED", ...}`.

*Now:* §5 is corrected to state the premise is false, preserve the historical PR #108
evidence that the old invocation once worked (as evidence of the old artifact only, not of
the script this repository ships today), and show the genuine computation of this
deployment's own effective three-path fingerprint -- the same computation independently
re-verified against the real script's own `_deployment_config_fingerprint()` function during
this correction's own work (both produced
`5dff2d96636ec356ad26f8c1b0047b920a8b235e62b02574d1e13a4f5c1f8486` for the shipped defaults) --
and clarifies that a real attempt never has an operator type that value in: it rides along on
the live, Grant-verified SSH command exactly as §2/§3 already describe.

### 25.3 E1 — the specified governance verification gate was unreported

*Found:* the prior round's delivery evidence reported only `tests/unit/runtime
tests/contract/runtime tests/integration/runtime` (619 passed); `tests/contract/governance`
was never run or reported, though the adopted handoff required it.

*Now, run on this correction's own final tree, before this round's own commit:*

```text
RUFF_CHECK=PASS (tests/integration/runtime/test_runtime_unattended_ssh.py)
GIT_DIFF_CHECK=PASS
SOURCE_IMPACT_GATE_DECISION=PASS
FOCUSED_SUITE=tests/unit/runtime tests/contract/runtime tests/integration/runtime tests/contract/governance
FOCUSED_SUITE_RESULT=830 passed, 0 failed, 0 skipped, exit code 0, 660.18s
```

### 25.4 Declarations

```text
REAL_PROBE_SUBPROCESS_CARRIED_THROUGH_OBSERVE_RUNTIME_TARGET=true
REAL_RECEIPT_CARRIED_THROUGH_ROUTE_RUNTIME_OBSERVATION_TO_EVIDENCE=true
CANONICAL_FORMAT_IDENTITY_VALUE_USED_NOT_ARBITRARY_STRING=true
GENUINE_ED25519_SIGNED_GRANT_AND_STORE_COMMITTED_TARGET_USED=true
NO_NEW_PERSISTENCE_AUTHORITY_OR_EVIDENCE_OWNER_INTRODUCED=true
ABSENT_EMPTY_UNREADABLE_WRONG_IDENTITY_NEGATIVE_CONTROLS_ADDED=true
UNREADABLE_SIMULATED_DETERMINISTICALLY_VIA_DIRECTORY_NEVER_ASSUMED_PERMISSION_BITS=true
REAL_PROBE_DIGEST_CHANGE_PROVEN_OVER_ACTUAL_SUBPROCESS_NOT_ONLY_TEST_HELPER=true
ZERO_CONFIGURED_FILE_READS_ON_MISMATCH_PROVEN_FOR_BOTH_PROFILES_VIA_FIFO=true
OMITTED_DEFAULT_TEST_NO_LONGER_ASSUMES_REAL_SYSTEM_FILE_ABSENCE=true
OPERATOR_GUIDE_STALE_HEALTH_INVOCATION_CORRECTED=true
DOC_FINGERPRINT_EXAMPLE_INDEPENDENTLY_VERIFIED_AGAINST_REAL_SCRIPT_FUNCTION=true
HISTORICAL_PR_108_EVIDENCE_PRESERVED_UNCHANGED_AS_EVIDENCE_OF_THE_OLD_ARTIFACT=true
GOVERNANCE_VERIFICATION_GATE_RUN_AND_REPORTED_BEFORE_COMMIT=true
NO_RUNTIME_SEMANTICS_CHANGED_BEYOND_TEST_AND_DOC_CORRECTIONS_THIS_ROUND=true
VPS_EXECUTION_PERFORMED=false
CREDENTIAL_PROVISIONED_OR_CHANGED=false
SYSTEM_CONFIGURATION_CHANGED=false
DOWNSTREAM_APPLICATION_CHANGED=false
MERGE_PERFORMED=false
READY_TRANSITION_PERFORMED=false
ISSUE_105_CLOSE_PERFORMED=false
AUTOMATED_EXTERNAL_REVIEW_REQUEST_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```


## 26. Issue #105 isolated Actions real-VPS proof trial (ADOPT_I105_ISOLATED_ACTIONS_PROOF_SETTINGS_20261006)

```text
GOVERNING_ISSUE=#105
ADOPTION_ID=ADOPT_I105_ISOLATED_ACTIONS_PROOF_SETTINGS_20261006
ADOPTION_COMMENT=Issue #105 comment 6009525871
HANDOFF_COMMENT=Issue #105 comment 6009534957
AUTHORIZED_BASE_MAIN=066d85aa319b0de35f39d6dbf4aa48681466a404
AUTHORIZED_BRANCH=agent/issue-105-isolated-actions-proof
WORK_UNIT_ID=WORK-UNIT-I105-ISOLATED-ACTIONS-PROOF-1
```

`066d85a` is the merge commit of PR #110 (itself the merged isolated-deployment-identity
correction, §24/§25 above); this work unit is a fresh branch from that merged main, never a
reopening of #108 or #110. §24/§25 continue to describe those artifacts unchanged and are kept
as evidence of them.

### 26.1 The gap this closes

SHUKOU's own real signed Runtime observation checkpoint (Issue #105 comment 6009496416,
"isolated VPS trial V2") reached a genuine `OBSERVED`/`VERIFIED` outcome against a real target,
by hand, using a fresh in-memory Ed25519 Authority key, a genuinely bound local
`FileStateStore`, a signed declaration and a ten-minute signed grant, the shipped
`SshRuntimeAdapter`/`observe_runtime_target`, and a derived (never Store-committed) Evidence
record via the existing `route_runtime_observation_to_evidence`. That checkpoint also found
`.github/workflows/runtime_observation.yml` ships no bound Store restoration and no SSH
credential/known-host/working-directory setup of its own, so dispatching it could never
by itself reach a real target -- the shipped CLI could invoke the `GITHUB_ACTIONS` adapter, but
the unprepared workflow was not itself a real-VPS positive proof.

### 26.2 What this work unit adds

Exactly the six permitted paths the handoff (comment 6009534957) names; no others touched.

**`scripts/runtime_observation_proof.py` (new).** A standalone trial-orchestration tool --
never part of the installed package, never a second Runtime/Authority/Evidence owner. Its
`bootstrap` subcommand mints a disposable, isolated Project Binding and Store under a
genuinely random, in-process-memory `Ed25519PrivateKey.generate()` key -- never a publicly
known, deterministic fixture signing key standing in for deployed Authority -- commits a real
`runtime_deployment_declaration` under it (through the existing, unmodified
`commit_runtime_deployment_declaration`), and signs one bounded, short-lived
`runtime_observation_grant` naming the real target's own host/port/user/probe identity and its
own currently-configured identity/three-path config fingerprint. Project Binding genesis
scaffolding is deliberately reused from `tests.fixtures.product_binding` (Kernel-wide,
already-pinned infrastructure; re-deriving a second copy would itself duplicate it) with only
the signing key substituted -- the identical, already-established "same shapes, swapped
Authority key" pattern `tests.fixtures.runtime_world.alternate_bound` already uses. Its
`run-local-proof` subcommand runs the real, shipped `scripts/runtime_observation_probe.py` as a
real **local** subprocess -- explicitly disclosed as never a live network call
(`"transport": "LOCAL_SUBPROCESS_STAND_IN"`, `"live_network_call_made": false`) -- through
`CapturedProbeReportRuntimeAdapter` and the real `observe_runtime_target`, reopens the Store
before an optional Evidence hand-off, and reports that hand-off as `DERIVED` with
`store_committed_by_this_script: false`, never conflating a derived record with one this
script itself committed to Store. Both subcommands produce exactly the inputs
`scripts/runtime_observation_transport.py`'s own existing, unmodified `observe`/`run-controller`
subcommands already know how to consume -- a grant file, a target-identity file, a Store root --
introducing no parallel implementation of either.

**`tests/integration/runtime/test_runtime_observation_proof.py` (new).** Eight permanent tests:
a fresh-random-key proof (two bootstrap runs with identical signed semantic fields still
produce different signatures); the positive real-probe-to-`OBSERVED`/`VERIFIED`-to-derived-
Evidence path, both directly and through the real CLI entry point; and five refusal paths --
the target's own real configuration changing since the grant was signed (`CONFIG_NOT_
AUTHORIZED`), a wrong reported identity against the declared target (`IDENTITY_MISMATCH`), an
expired grant (refused at adapter construction), the operator's own sibling-config setup
missing entirely (falls back to unauthorized shipped defaults, refused), and a structural proof
that the one new local subprocess call site carries an explicit bound. The probe script's own
bounded-read/pre-read-authorization/symlink-refusal guarantees are not re-proven here; they
remain exhaustively covered by `tests/integration/runtime/test_runtime_unattended_ssh.py`.

**`.github/workflows/runtime_observation.yml`.** A new `isolated-actions-proof` job, gated by
an explicit opt-in `proof_mode` dispatch input (default `"false"`) -- every dispatch that omits
it, or any dispatch before this change existed, runs neither this job nor reads any of its new
inputs or secret. When opted in, it writes a separately named, operator-provisioned trial-only
SSH secret (`RUNTIME_OBSERVATION_TRIAL_SSH_PRIVATE_KEY`, never the production key, never
generated or provisioned by this workflow itself) and a pinned `known_hosts` entry to the
runner's own disk, calls the new script's `bootstrap` subcommand, then runs the existing,
unmodified `observe` (`GITHUB_ACTIONS` transport) and `run-controller` (the independent
Actions-to-SSH fallback controller, exercised against an explicitly FIXTURE-labelled
dispatch-status sequence, falling back to a real `PREAUTHORIZED_UNATTENDED_SSH` attempt only
once its own bounded deadline is reached and the grant already, explicitly authorizes it)
subcommands against the real target, removes the trial key before the job ends, and publishes
both results to the job summary with host/user deliberately not repeated there. Every new
`${{ github.event.inputs.* }}` reference reaches a step exclusively through that step's own
`env:` mapping, the identical discipline PR #108 SR1-F5 already established for this file; no
`push`/`pull_request`/`schedule` trigger, no `issues:`/`pull-requests:`/`contents: write`
permission, and no merge/approve/comment/push/commit text was added anywhere in this file --
independently confirmed by running this repository's own existing, unmodified governance test
(`tests/contract/governance/test_merge_source_reflow_workflows.py`), which required no edit of
its own to keep passing.

**`docs/runtime_observation_transports.md`.** New §7: the one-time operator setup sequence for
the trial-only SSH key (never performed by this repository's own tooling), how to dispatch the
trial, what the job does and does not do (Evidence hand-off stays a deliberately separate,
local, operator-run step against a receipt someone has actually reviewed, never something the
workflow performs unattended), and the cleanup obligation (remove the exact trial secret/
`authorized_keys` entry afterward, confirmed by a further dispatch that is expected to fail).

### 26.3 Verification (run before commit)

```text
RUFF_CHECK=PASS (scripts/runtime_observation_proof.py, tests/integration/runtime/test_runtime_observation_proof.py)
GIT_DIFF_CHECK=PASS
SOURCE_IMPACT_GATE_DECISION=PASS
FOCUSED_SUITE=tests/unit/runtime tests/contract/runtime tests/integration/runtime tests/contract/governance
FOCUSED_SUITE_RESULT=838 passed, 0 failed, 0 skipped, exit code 0, 720.45s
EXISTING_GOVERNANCE_WORKFLOW_TEST_PASSED_WITHOUT_EDIT=true
```

### 26.4 Declarations

```text
RANDOM_IN_MEMORY_ED25519_AUTHORITY_KEY_NEVER_A_FIXTURE_KEY_USED_AS_DEPLOYED_AUTHORITY=true
NO_SECOND_RUNTIME_AUTHORITY_OR_EVIDENCE_OWNER_INTRODUCED=true
EXISTING_OBSERVE_AND_RUN_CONTROLLER_SUBCOMMANDS_REUSED_UNCHANGED=true
LOCAL_SUBPROCESS_STAND_IN_EXPLICITLY_DISCLOSED_NEVER_A_LIVE_NETWORK_CALL_CLAIM=true
DERIVED_EVIDENCE_NEVER_CONFLATED_WITH_STORE_COMMITTED_EVIDENCE=true
PROOF_MODE_DEFAULT_IS_FALSE_EXISTING_DISPATCHES_UNCHANGED=true
TRIAL_ONLY_SSH_SECRET_NEVER_GENERATED_OR_PROVISIONED_BY_THIS_DELIVERY=true
PRODUCTION_SSH_KEY_NEVER_READ_USED_OR_ROTATED=true
PINNED_HOST_VERIFICATION_REQUIRED_NEVER_TRUST_ON_FIRST_USE=true
EVENT_INPUT_INTERPOLATION_SAFETY_DISCIPLINE_PRESERVED_PR108_SR1_F5=true
EXISTING_GOVERNANCE_WORKFLOW_TEST_FILE_UNCHANGED=true
FIXTURE_DISPATCH_STATUS_SEQUENCE_NEVER_CLAIMED_AS_REAL_OUTAGE_EVIDENCE=true
LIVE_VPS_EXECUTION_PERFORMED_BY_THIS_WORK_UNITS_OWN_AUTHOR=false
CREDENTIAL_OR_SECRET_PROVISIONED_BY_THIS_WORK_UNITS_OWN_AUTHOR=false
SYSTEM_SERVICE_OR_PACKAGE_CHANGED=false
DOWNSTREAM_APPLICATION_OR_PRODUCTION_DATA_ACCESSED=false
MERGE_PERFORMED=false
READY_TRANSITION_PERFORMED=false
ISSUE_105_CLOSE_PERFORMED=false
AUTOMATED_EXTERNAL_REVIEW_REQUEST_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

## 27. PR #111 Structural Review Round 1 correction (F1–F4)

```text
GOVERNING_ISSUE=#105
AUTHORIZED_PR=#111
REVIEW_COMMENT=6010116935
ADOPTION_ID=ADOPT_I105_PR111_SR1_F1_F4_20261006
ADOPTION_COMMENT=6010217837
HANDOFF_COMMENT=6010228905
AUTHORIZED_START_HEAD=7a5df808b5ecd508b217f6b4490995c002f58e69
AUTHORIZED_BASE_MAIN=066d85aa319b0de35f39d6dbf4aa48681466a404
FINDINGS_ADOPTED=F1,F2,F3,F4
```

Independent Structural Advisor review of §26's own prior HEAD (`7a5df80`) found four P1 gaps
in the isolated Actions real-VPS proof trial this correction closes, each recorded below as
*what was found* and *what the workflow/docs/script/tests now do*. Exactly the six paths the
original handoff (Issue #105 comment 6009534957, §26 above) named were touched again; no
installed Runtime/Kernel/Authority/State/Evidence owner, and no other workflow or test, was
modified.

### 27.1 F1 — the trial-only SSH key was never actually selected by any real `ssh` invocation

*Found:* `render_ssh_command_argv` (installed Runtime code, out of scope for this correction)
builds a plain `ssh -o BatchMode=yes ... user@host '<command>'` invocation carrying no
`-i`/`IdentityFile` flag and no `-F` override of its own, so it reads whatever `~/.ssh/config`
the runner happens to have. The prior round's own job wrote the trial key's bytes to disk but
never wrote any config naming it -- `ssh` would have silently selected whatever ambient
identity (an agent key, a default `id_*` file) the runner carried instead, never genuinely
proving the trial-only key itself authenticated. "A file-exists assertion is insufficient"
(the adopted handoff's own words) was not previously true even of the file-level check: there
was none.

*Now:* the job's own "Set up the trial-only SSH key, pinned host verification, and identity
selection" step independently validates the written key with `ssh-keygen -y` (failing closed,
before anything else, on a missing or malformed key -- never logging its own bytes either
way) and then writes a `~/.ssh/config` `Host` block scoped to the exact trial host, naming the
trial key as its only `IdentityFile` (`IdentitiesOnly yes`), before independently re-verifying
selection with a real `ssh -G -F ~/.ssh/config "$TRIAL_SSH_HOST"` resolution (failing the job
closed on any mismatch) -- never a mere file-existence assertion. The generated `~/.ssh/config`
is removed, alongside the key and `known_hosts`, before the job ends.
`docs/runtime_observation_transports.md` §7.2 step 1 and §7.4 record this. Three new permanent
tests in `tests/integration/runtime/test_runtime_observation_proof.py` extract this exact
step's own live script text (never a hand-copied stand-in) and run it against a real,
freshly generated Ed25519 key pair under a real `ssh`/`ssh-keygen` toolchain (skipped,
honestly, when neither binary is present in whatever environment runs the suite -- the real
target environment, GitHub Actions `ubuntu-latest`, ships both by default): the positive case
proves a real `ssh -G` resolution selects exactly the trial key for the exact host; one
refusal case proves a missing/invalid key fails closed before `~/.ssh/config` is ever written;
one proves an ambient default identity already present at `~/.ssh/id_ed25519` is never
selected or even considered once the trial's own `Host` block exists.

### 27.2 F2 — the documented forced-command example discarded the real launcher and its arguments

*Found:* `docs/runtime_observation_transports.md` §7.1 step 2 documented
`command="python3 /path/to/runtime_observation_probe.py"` as the `authorized_keys` forced
command. OpenSSH's own `command=` restriction *replaces* whatever command the connecting
client actually requested -- here, the real launcher-wrapped invocation
`render_ssh_command_argv` sends (`python3 -c "<SSH_PROBE_LAUNCHER_CODE>" <sha256> <identity>
<fingerprint>`, PR #108 SR6-F2) -- so the documented forced command discarded that launcher
and its three required positional arguments entirely, reaching the bare probe script with
zero of them. Independently reproduced against the real, accepted probe
(`d613231acaee104ba227b769bc1083c16fbd4f46e62dd66ca9a84f55742b2c85`): a closed `{"ok": false,
"fields": null, "deployment_identity": null, "reason": "MALFORMED", ...}`, never a genuine
exercise of the launcher's own verify-before-execute discipline at all.

*Now:* §7.1 steps 2–4 (renumbered) document creating a neutral directory holding the reviewed
probe script and its sibling config, generating the exact expected command text from this
repository's own real, unmodified `render_ssh_command_argv` (`scripts/
runtime_observation_proof.py render-expected-ssh-command`, a new subcommand -- never a
hand-transcribed copy that could drift from the real code), and a forced-command wrapper
script that `cd`s into that neutral directory, exact-string-compares `$SSH_ORIGINAL_COMMAND`
against that generated value, and only on a match `exec`s the client's own real command
(`exec /bin/sh -c "$SSH_ORIGINAL_COMMAND"`) -- preserving and re-executing the real launcher
intact, never substituting a bare, argument-less invocation of its own. Step 6 (renumbered)
additionally requires the captured `trial_ssh_known_hosts` host key to be corroborated through
the operator's own already-authenticated connection, never trusted from `ssh-keyscan` alone.
Two new permanent tests run the exact, extracted (never hand-copied) documented wrapper
script for real: the positive case, given the one real expected command (built from the real
`render_ssh_command_argv`), genuinely reaches the real, unmodified probe script and a genuine
positive report; the negative case proves any other command -- a different code string, an
unrelated command, no command at all -- is refused by the wrapper itself, with the launcher
and the real probe script never reached.

### 27.3 F3 — the documented Evidence hand-off derived from a fresh local probe, never the trial's own live receipt

*Found:* §7.2's "What this does not do" described `run-local-proof --with-evidence-handoff`
as the reviewed follow-up for the live trial's own Evidence hand-off. That subcommand actually
runs a brand-new **local** probe subprocess and derives Evidence from *that* new observation's
own receipt -- never from the real receipt the Actions job's own `observe`/`run-controller`
steps actually produced. The documented claim of deriving Evidence "for" the live trial from
its own real receipt was not accurate as implemented.

*Now:* a new `evidence-from-receipt` subcommand in `scripts/runtime_observation_proof.py`
reopens an already-populated Store and a new
`resolve_live_receipt_from_store(store, project_id=..., envelope_id=...)` function
reconstitutes a `RuntimeObservationReceipt` *directly from the already-committed Envelope
record's own fields* (independently re-verifying that record's own recomputed semantic
fingerprint first, refusing on any mismatch) -- zero probe invocation, zero second call to
`observe_runtime_target`, of any kind. That receipt is handed to the real, unchanged
`route_runtime_observation_to_evidence` and reported `DERIVED`, `store_committed_by_this_
script: false`, exactly as `run-local-proof` itself already reports (which remains a distinct,
honestly offline composition proof against a fresh local probe, now explicitly documented as
never a substitute for this). The `isolated-actions-proof` job now exports the isolated
Store/grant/target-identity files it produced as a GitHub Actions artifact (carrying no SSH or
signing private key -- the in-RAM isolated Authority key is never written to disk by this
script in the first place) for exactly this local, reviewed follow-up; `docs/
runtime_observation_transports.md` §7.2 documents the complete sequence. Three new permanent
tests: the positive path builds a real committed envelope through the real canonical route,
then monkeypatches the probe-invocation function to raise `AssertionError` if ever called
again before calling `evidence-from-receipt` -- proving zero new probe calls structurally,
not merely by inspection; one refusal proves an `--envelope-id` that never resolved is refused;
one proves a record whose own declared semantic fingerprint no longer matches its own
recomputed one (a genuine tamper) is refused before a receipt is ever reconstituted from it; a
fourth structurally scans every file the trial's own bootstrap/export writes for the literal
`PRIVATE KEY` marker, confirming none is ever present.

### 27.4 F4 — a proof-mode dispatch could spuriously run the generic jobs, and `ok: true`/exit 0 alone was treated as a positive proof

*Found:* `render-command` and `observe` carried no `if:` of their own, so a `proof_mode:
"true"` dispatch -- which names only the `isolated-actions-proof` job's own `trial_*` inputs --
would still attempt both generic jobs against their own unset/irrelevant generic inputs. The
`isolated-actions-proof` job's own `continue-on-error: true` live steps were never followed by
anything that actually inspected their JSON results: an honestly refused/`UNAVAILABLE`/timed-
out observation reports `"ok": true` exactly as genuinely as a real positive one, and the job's
own summary step merely echoed both results without judging them -- `ok: true`/exit 0 from
either step, alone, was never actually a positive proof of anything.

*Now:* `render-command` and `observe` each carry `if: github.event.inputs.proof_mode !=
'true'`; `isolated-actions-proof` keeps its own existing `if: ... == 'true'`, the exact
inverse. A new `check-proof-verdict` subcommand (and `check_proof_verdict`/
`_evaluate_transport_trial_result` functions) in `scripts/runtime_observation_proof.py` reads
the real `actions_trial_result.json`/`fallback_trial_result.json` and requires the Actions
trial to have genuinely reached `OBSERVED`/`VERIFIED` with a non-empty `observed_fields`, and
the fallback trial to have genuinely reached `decision: FALLBACK_AUTHORIZED`, `executed:
true`, the identical `OBSERVED`/`VERIFIED`/non-empty-`observed_fields` outcome, *and* an
`observed_fields` value equal to the Actions trial's own -- failing closed (non-zero exit) on
any gap, including a fallback that never left `ACTIONS_AVAILABLE_DEFER`/`FALLBACK_REFUSED_NO_
GRANT`/`ALREADY_SATISFIED` (a legitimate, honest controller decision that nonetheless never
proves this trial's own point). The job now runs this check (no `continue-on-error`) before
exporting the Store artifact and publishing the job summary, which now includes this verdict.
Six new permanent tests cover the pure function directly (positive; `ok: true`-alone rejected;
a never-authorized fallback rejected; mismatched stable fields rejected; the CLI's own
non-zero exit on a negative verdict) and a seventh statically confirms, by plain text
inspection of the live workflow file (never a YAML-parsing dependency this repository does not
otherwise carry), that both generic jobs' `if:` excludes `proof_mode: "true"` and the proof
job's own carries the exact inverse.

### 27.5 Verification (run on this correction's own final tree, before commit)

```text
RUFF_CHECK=PASS (scripts/runtime_observation_proof.py, tests/integration/runtime/test_runtime_observation_proof.py)
GIT_DIFF_CHECK=PASS
SOURCE_IMPACT_GATE_DECISION=PASS
FOCUSED_SUITE=tests/unit/runtime tests/contract/runtime tests/integration/runtime tests/contract/governance
FOCUSED_SUITE_RESULT=854 passed, 0 failed, 0 skipped, exit code 0, 747.79s
EXISTING_GOVERNANCE_WORKFLOW_TEST_PASSED_WITHOUT_EDIT=true
```

### 27.6 Declarations

```text
TRIAL_SSH_IDENTITY_SELECTION_VERIFIED_VIA_REAL_SSH_-G_RESOLUTION_NEVER_FILE_EXISTENCE_ALONE=true
MISSING_OR_INVALID_TRIAL_KEY_FAILS_CLOSED_BEFORE_ANY_CONFIG_IS_WRITTEN=true
AMBIENT_IDENTITY_NEVER_SELECTED_ONCE_THE_TRIAL_HOST_BLOCK_EXISTS=true
FORCED_COMMAND_PRESERVES_AND_VALIDATES_THE_REAL_LAUNCHER_INVOCATION_NEVER_A_BARE_ARGUMENTLESS_SUBSTITUTE=true
EXPECTED_COMMAND_TEXT_GENERATED_FROM_THE_REAL_RENDER_SSH_COMMAND_ARGV_NEVER_HAND_TRANSCRIBED=true
HOST_KEY_CORROBORATED_THROUGH_AN_ALREADY_AUTHENTICATED_CONNECTION_NEVER_SSH_KEYSCAN_ALONE=true
LIVE_RECEIPT_EVIDENCE_HANDOFF_RECONSTITUTED_DIRECTLY_FROM_THE_COMMITTED_ENVELOPE_ZERO_NEW_PROBE_CALLS=true
ZERO_NEW_PROBE_CALLS_PROVEN_STRUCTURALLY_VIA_A_RAISING_MONKEYPATCH_NOT_ONLY_BY_INSPECTION=true
TAMPERED_OR_UNRESOLVED_ENVELOPE_RECORDS_REFUSE_BEFORE_A_RECEIPT_IS_RECONSTITUTED=true
NO_SIGNING_OR_SSH_PRIVATE_KEY_MATERIAL_IN_THE_EXPORTED_STORE_BUNDLE=true
GENERIC_RENDER_COMMAND_AND_OBSERVE_JOBS_NEVER_RUN_ON_A_PROOF_MODE_DISPATCH=true
DEFAULT_GENERIC_DISPATCH_BEHAVIOR_UNCHANGED=true
PROOF_VERDICT_REQUIRES_GENUINE_OBSERVED_VERIFIED_ON_BOTH_TRIALS_NEVER_MERELY_OK_TRUE_OR_EXIT_ZERO=true
FALLBACK_VERDICT_REQUIRES_GENUINE_FALLBACK_AUTHORIZED_AND_EXECUTED_NEVER_A_DEFERRED_DECISION_ALONE=true
STABLE_FIELD_EQUALITY_BETWEEN_BOTH_TRIALS_REQUIRED_FOR_A_POSITIVE_VERDICT=true
NO_INSTALLED_RUNTIME_KERNEL_AUTHORITY_STATE_OR_EVIDENCE_OWNER_MODIFIED=true
NO_OTHER_WORKFLOW_OR_TEST_FILE_MODIFIED=true
EXISTING_GOVERNANCE_WORKFLOW_TEST_FILE_UNCHANGED=true
GOVERNANCE_VERIFICATION_GATE_RUN_AND_REPORTED_BEFORE_COMMIT=true
LIVE_VPS_EXECUTION_PERFORMED_BY_THIS_CORRECTIONS_OWN_AUTHOR=false
CREDENTIAL_OR_SECRET_PROVISIONED_BY_THIS_CORRECTIONS_OWN_AUTHOR=false
NEW_DRAFT_PR_OPENED=false
MERGE_PERFORMED=false
READY_TRANSITION_PERFORMED=false
ISSUE_105_CLOSE_PERFORMED=false
AUTOMATED_EXTERNAL_REVIEW_REQUEST_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

## 28. PR #111 Structural Review Round 2 correction (SR2-F1–F3)

```text
GOVERNING_ISSUE=#105
AUTHORIZED_PR=#111
REVIEW_COMMENT=6011295936
ADOPTION_ID=ADOPT_I105_PR111_SR2_F1_F3_20261006
ADOPTION_COMMENT=6012034272
HANDOFF_COMMENT=6012045397
AUTHORIZED_START_HEAD=272460c5eccd8cbda3dbc4ac928388dd3213ce50
AUTHORIZED_BASE_MAIN=066d85aa319b0de35f39d6dbf4aa48681466a404
FINDINGS_ADOPTED=SR2-F1,SR2-F2,SR2-F3
```

Independent Structural Advisor re-review of §27's own prior HEAD (`272460c`) acknowledged the
Round 1 corrections as genuinely resolved (trial-identity selection, forced-command
preservation, zero-probe live-receipt resolution, generic-job proof-mode exclusion) while
finding three residual P1 gaps, corrected below within the identical six permitted paths; no
installed Runtime/Kernel/Authority/State/Evidence owner, and no other workflow or test, was
touched.

### 28.1 SR2-F1 — a proof-mode dispatch still required meaningless generic inputs

*Found:* `workflow_dispatch.inputs` still declared `grant_json`/`store_root`/`project_id`/
`project_binding_id` as `required: true` at the dispatch-schema level. Job-level `if:`
conditions (Round 1, F4) never change what GitHub itself requires an operator to fill in
before a dispatch can even be submitted -- the documented `proof_mode: "true"` + `trial_*`
dispatch could not actually be submitted through the normal UI/API without also supplying
dummy values for four fields the isolated-actions-proof job never reads.

*Now:* those four inputs are `required: false`/`default: ""` at the dispatch-schema level;
`now` stays `required: true` (needed by every mode alike). Each of `render-command`/`observe`
gained its own "Validate required generic-mode dispatch inputs are present" step (fails closed
before anything else if any is empty), and `isolated-actions-proof` gained a parallel
"Validate required proof-mode dispatch inputs are present" step covering its own `trial_*`
inputs, including the new `trial_expected_observed_fields` (SR2-F3). Ten new permanent tests
in `tests/integration/runtime/test_runtime_observation_proof.py` cover both the dispatch-schema
declarations themselves (each of the four generic inputs and the new trial input must declare
`required: false`; `now` must stay `required: true`) and both validation steps' own live text
(extracted, never hand-copied): missing-generic-input refusal, complete-generic-input success,
missing-trial-input refusal, and a genuinely complete trial-only dispatch (no generic inputs
at all) passing.

### 28.2 SR2-F2 — LIVE Evidence was derived then discarded, and the export bundle was incomplete

*Found:* `_cmd_evidence_from_receipt` received the complete Evidence record
`route_runtime_observation_to_evidence` returned, then reported only its `evidence_id`/
`evidence_position` -- the CLI had no output path to ever actually keep the full body
anywhere, so "preserve LIVE receipt provenance through the receiver and Evidence" stopped
short of persistence. The exported artifact bundle (§27's own F3 delivery) carried only the
Store/grant/target-identity directories, omitting the trial's own `actions_trial_result.json`/
`fallback_trial_result.json`/`proof_verdict_result.json` -- the receiver's own exit/result/
`envelope_id` correlation facts. The adopted "runnable outside-Actions setup/controller
orchestration" obligation also remained undelivered as a concrete, documented sequence.

*Now:* `evidence-from-receipt` gained `--evidence-output-file`: when given, the complete
derived Evidence body is written to that path, then independently reloaded from the file
itself (never trusted from the in-memory value alone) and checked to still name the identical
original envelope before the command reports success -- refusing (`SAVED_EVIDENCE_RELOAD_DID_
NOT_MATCH_THE_ORIGINAL_RECORD`) if the reload ever disagrees. Omitting the flag keeps the
Round 1 behavior unchanged (`complete_body_saved_and_reloaded: {"performed": false}`). The
workflow's export step now also uploads `bootstrap_result.json`/`actions_trial_result.json`/
`fallback_trial_result.json`/`proof_verdict_result.json` alongside the Store/grant/
target-identity directories. `docs/runtime_observation_transports.md` gained new §7.2.1: a
concrete, runnable, outside-Actions sequence (local `bootstrap`, local `~/.ssh/config` set up
exactly as §7.1 step 4 describes, then the existing, unmodified `scripts/
runtime_observation_transport.py run-controller --claim-state-file <local path>`) that an
operator runs entirely on their own machine -- no Actions runner, uploaded artifact, or
repository secret of any kind, reusing only the existing, unmodified controller and
`RuntimeObservationClaimState` owners. Five new permanent tests: complete-body save/reload
(positive, with an independent on-disk re-check of the file itself); the no-output-file case
keeping prior behavior; a text check that the export step's own `path:` block carries all four
result files; and two tests exercising `resolve_bounded_actions_fallback`/
`RuntimeObservationClaimState`/`compute_runtime_observation_operation_id` directly (the real,
unmodified functions, never a second implementation) to prove claim persistence survives a
genuine local-file round trip between two separate calls, and that two deliberately distinct
proof requests never collapse onto one operation identity -- neither test performs a real SSH
attempt, which remains exhaustively covered by `tests/integration/runtime/
test_runtime_unattended_ssh.py`.

### 28.3 SR2-F3 — the proof verdict tested mutual agreement, not a reviewed expectation

*Found:* `check_proof_verdict` required both trials' own `observed_fields` to equal each
other, never an independent, reviewed expectation. The Structural Advisor's own direct
reproduction (extracting the real verdict function via Python AST from the fetched HEAD, no
replacement implementation) showed two `SOURCE_LOG_EXCERPT_BOUNDED` reports that merely agreed
`{"source_available": false, "log_available": false}`, with a genuinely `FALLBACK_AUTHORIZED`+
executed fallback, passing this check -- a false positive: the canonical Runtime can honestly
classify a bounded report `OBSERVED` even when the individual excerpt files are themselves
unavailable, so "both trials agree" was never the same fact as "the trial's own completion
expectations were met."

*Now:* `check_proof_verdict`/`_evaluate_transport_trial_result` take `probe_identity` and
`expected_fields` (plus an optional `normalize_fields` set for genuinely time-varying keys
such as `uptime_seconds`). A new closed `_PROFILE_REQUIRED_EXPECTED_FIELD_KEYS` table requires
`expected_fields` to actually cover each pinned probe identity's own stable key(s)
(`hostname` for `OS_HEALTH_SNAPSHOT_BOUNDED`; `source_available`/`log_available` for
`SOURCE_LOG_EXCERPT_BOUNDED`) -- refusing an expectation that says nothing about the one fact
a profile exists to report. Both trials' own `observed_fields` (after normalization) must now
equal `expected_fields` directly; this alone closes the reviewer's exact reproduction, since
two results that agree on an unexpected value no longer satisfy anything. A new
`trial_expected_observed_fields` dispatch input (required in proof mode via SR2-F1's own
validation step) carries the reviewed expectation through to the live job. Each live trial
step now also records its own *real* process exit code (`set +e; ...; rc=$?; set -e`,
written into the result JSON itself) and the verdict independently requires it to equal `0`,
never inferring that fact from the JSON body's own `"ok"` field alone. Six new
permanent tests: a direct reproduction of the reviewer's exact false-positive scenario (now
refused); the identical scenario with a genuinely matching expectation (still positive); a
rejection when `expected_fields` omits a profile's own required key(s); a rejection of an
unpinned `probe_identity`; a rejection when a result's own real process exit code is nonzero
despite an otherwise-positive body; and a positive case using `normalize_fields` to exclude
`uptime_seconds` while still requiring `hostname` to match exactly. The five pre-existing F4
tests (four fixture-based, one CLI-based) were updated to the new signature (adding
`process_exit_code`/`probe_identity`/`expected_fields`, and one renamed to match its own new
"match the reviewed expectation" semantics) rather than removed, preserving their own
original intent.

### 28.4 Verification (run on this correction's own final tree, before commit)

```text
RUFF_CHECK=PASS (scripts/runtime_observation_proof.py, tests/integration/runtime/test_runtime_observation_proof.py)
GIT_DIFF_CHECK=PASS
SOURCE_IMPACT_GATE_DECISION=PASS
FOCUSED_SUITE=tests/unit/runtime tests/contract/runtime tests/integration/runtime tests/contract/governance
FOCUSED_SUITE_RESULT=875 passed, 0 failed, 0 skipped, exit code 0, 772.31s
EXISTING_GOVERNANCE_WORKFLOW_TEST_PASSED_WITHOUT_EDIT=true
NEW_OR_UPDATED_TESTS_THIS_ROUND=21
```

### 28.5 Declarations

```text
GENERIC_MODE_DISPATCH_INPUTS_OPTIONAL_AT_SCHEMA_LEVEL_VALIDATED_PER_MODE_BY_THE_JOB_ITSELF=true
TRIAL_ONLY_DISPATCH_SUBMITTABLE_WITHOUT_ANY_GENERIC_FIELD=true
DEFAULT_GENERIC_DISPATCH_BEHAVIOR_UNCHANGED=true
COMPLETE_DERIVED_EVIDENCE_BODY_SAVED_AND_INDEPENDENTLY_RELOADED_WHEN_REQUESTED=true
EVIDENCE_OMITTING_THE_OUTPUT_FLAG_KEEPS_THE_PRIOR_ROUNDS_BEHAVIOR_UNCHANGED=true
EXPORTED_ARTIFACT_CARRIES_RESULT_FACTS_ALONGSIDE_THE_STORE=true
OUTSIDE_ACTIONS_CONTROLLER_SEQUENCE_DOCUMENTED_NEEDS_NO_RUNNER_ARTIFACT_OR_SECRET=true
OUTSIDE_ACTIONS_SEQUENCE_REUSES_ONLY_EXISTING_UNMODIFIED_CONTROLLER_CLAIM_STATE_OWNERS=true
CLAIM_PERSISTENCE_PROVEN_VIA_REAL_LOCAL_FILE_ROUND_TRIP_NEVER_A_REAL_SSH_ATTEMPT=true
DISTINCT_PROOF_REQUESTS_NEVER_COLLAPSE_ONTO_ONE_OPERATION_IDENTITY=true
PROOF_VERDICT_BOUND_TO_A_REVIEWED_EXPECTED_FIELDS_VALUE_NEVER_MUTUAL_AGREEMENT_ALONE=true
REVIEWERS_EXACT_FALSE_POSITIVE_REPRODUCTION_NOW_INDEPENDENTLY_CONFIRMED_REFUSED=true
PROFILE_APPROPRIATE_REQUIRED_EXPECTED_KEYS_ENFORCED_PER_PINNED_PROBE_IDENTITY=true
REAL_PROCESS_EXIT_CODE_CHECKED_INDEPENDENTLY_OF_THE_RESULTS_OWN_OK_FIELD=true
NO_INSTALLED_RUNTIME_KERNEL_AUTHORITY_STATE_OR_EVIDENCE_OWNER_MODIFIED=true
NO_OTHER_WORKFLOW_OR_TEST_FILE_MODIFIED=true
EXISTING_GOVERNANCE_WORKFLOW_TEST_FILE_UNCHANGED=true
GOVERNANCE_VERIFICATION_GATE_RUN_AND_REPORTED_BEFORE_COMMIT=true
LIVE_VPS_EXECUTION_PERFORMED_BY_THIS_CORRECTIONS_OWN_AUTHOR=false
CREDENTIAL_OR_SECRET_PROVISIONED_BY_THIS_CORRECTIONS_OWN_AUTHOR=false
NEW_DRAFT_PR_OPENED=false
MERGE_PERFORMED=false
READY_TRANSITION_PERFORMED=false
ISSUE_105_CLOSE_PERFORMED=false
AUTOMATED_EXTERNAL_REVIEW_REQUEST_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```
