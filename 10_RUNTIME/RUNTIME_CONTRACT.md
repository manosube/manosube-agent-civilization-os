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
reopened and supersedes both of Round 2's. Where two sections differ, the **highest-numbered**
section governs.

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
