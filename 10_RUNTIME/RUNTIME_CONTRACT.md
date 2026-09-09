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
TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT=1
STRUCTURAL_REVIEW_ROUNDS_APPLIED=1
```

Section 10 records Structural Review Round 1 (P15-R1-F1..F6) in full. Where that section
and an earlier section differ, section 10 governs.

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

provision_trusted_runtime_root(
    store,
    *,
    project_id: str,
    project_binding_id: str,
) -> TrustedRuntimeRoot

bootstrap_projection_execution_capability(
    trusted_runtime_root: TrustedRuntimeRoot,
    *,
    github_projection_grant_refs: list[Mapping[str, str]],
    github_projection_grant_declaration_refs: list[Mapping[str, str]],
) -> ProjectionExecutionCapability
```

`target_identity` is `{provider, deployment_id, instance_identity, project_binding_ref,
deployment_declaration_ref, deployment_fingerprint}` (`deployment_declaration_ref` added by
Round 1, P15-R1-F6 -- see §10) -- `project_binding_ref` must name exactly `project_binding_id`;
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
opaque `TrustedRuntimeRoot` obtained from `provision_trusted_runtime_root`; it carries no
`store`/`project_id`/`project_binding_id` parameter of its own at all. See §7, V5 and §10.

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
├── route.py                observe_runtime_target -- the one public Runtime Observation
│                           route
├── evidence_handoff.py     route_runtime_observation_to_evidence -- the one public
│                           Runtime-Observation-to-Evidence hand-off
└── bootstrap.py            provision_trusted_runtime_root / TrustedRuntimeRoot and
                             bootstrap_projection_execution_capability -- the V5 trusted
                             runtime bootstrap provisioning Phase 14's
                             ProjectionExecutionCapability

01_SCHEMA/runtime/
├── runtime_observation_envelope.schema.json     the committed observation fact
└── runtime_deployment_declaration.schema.json   the canonical, Human-Authority-declared
                                                  deployment identity a target's own claimed
                                                  deployment_fingerprint must match
                                                  (Round 1, P15-R1-F6)
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
6. **Trusted runtime provisioning is two steps, and the trust root is a type (Round 1,
   P15-R1-F4).** `provision_trusted_runtime_root` is the single, explicit boundary at which a
   deployment fixes which Store/Project/Binding its trusted provisioning operates within;
   `bootstrap_projection_execution_capability` then reads that opaque root and carries no
   `store`/`project_id`/`project_binding_id` parameter of its own at all. This is a
   deliberate ergonomic cost (two calls where there was one, and one more type to hold) paid
   for a structural gain: the parameter through which a caller could name an alternate,
   internally self-consistent Authority world no longer exists. `TrustedRuntimeRoot` performs
   no verification of its own -- it holds no Boot verdict that could go stale, only *which*
   world is in play; every check runs fresh inside the bootstrap call. Full rationale in §10.4.

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
here provisions a `TrustedRuntimeRoot` first -- P15-R1-F4, §10.4.)

**Round 1 proof layers.** Six further suites, one per adopted finding, are listed in §10.9.

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
TRUSTED_RUNTIME_ROOT_REQUIRED_FOR_PROVISIONING=true
AUTHORITY_FRESHNESS_RECHECKED_AT_ADAPTER_AND_COMMIT_BOUNDARIES=true
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
STRUCTURAL_REVIEW_ROUND_1_CORRECTIONS_APPLIED=true
STRUCTURAL_REVIEW_ROUND_1_FINDINGS_CLOSED=6
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
