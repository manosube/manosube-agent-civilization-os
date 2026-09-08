# Identity-Preserving GitHub Projection Contract (Phase 14, Issue #62)

```text
DOC_TYPE=PROJECTION_CONTRACT
DOCUMENT_ID=PROJECTION-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PROJECTION_ADAPTER
ADOPTION_ID=ADOPT_P14_D001_PROJECTION_ENVELOPE_IMPLEMENTATION
GOVERNING_ISSUE=#62
REVIEWED_MAIN_SHA=7fc597356330a0d1da7a334ef20cd913b74154d
```

See `PROJECTION_INDEX.md` for this contract set's own position and reading order.

## 1. Position

This layer adds exactly one provider-neutral, explicit GitHub Projection adapter: a
deterministic Projection Envelope binding an already-real canonical subject to an external
GitHub artifact, an explicit GitHub Authority check, an explicit `GitHubAdapter` boundary, and
an immutable, non-persisted GitHub Observation Receipt -- routed to the existing Store, the
existing Boot owner, and the existing Evidence owner, none of which this layer duplicates.
GitHub itself is a projection/audit surface only; it is never the canonical source of any
Difference, Change, Evidence, Authority Decision, or State.

```text
PROJECTION_OWNER_COUNT=1
PUBLIC_PROJECTION_ENTRY_POINT_COUNT=1
```

## 2. Public signature

```python
project_to_github(
    store,
    *,
    project_id: str,
    project_binding_id: str,
    subject_ref: Mapping[str, Any],
    projection_kind: str,
    target_repository: Mapping[str, Any],
    projection_payload: Mapping[str, Any],
    github_authority_ref: Mapping[str, Any],
    materialized_at: str,
    adapter: GitHubAdapter,
    subject_fingerprint: str | None = None,
) -> dict[str, Any]   # {"envelope": ..., "receipt": GitHubObservationReceipt, "reused": bool}

route_observation_receipt_to_evidence(
    receipt: GitHubObservationReceipt,
    project_id: str,
    evidence_request: Mapping[str, Any],
) -> dict[str, Any]
```

`subject_ref` is one of `{"kind": "difference" | "change" | "observation_evidence", "id": ...}`.
`projection_kind` is one of `DIFFERENCE_ISSUE` (requires a `difference` subject),
`CHANGE_PULL_REQUEST` (requires a `change` subject), or `EVIDENCE_ARTIFACT` (requires an
`observation_evidence` subject) -- a subject/kind mismatch refuses before any Store or adapter
call. `target_repository` must declare `{"host": "github", "owner": ..., "repo": ...}`.
`materialized_at` is a required, caller-supplied instant; this route reads no clock, the
identical discipline Evidence's own `derive_evidence` already requires of its own "recording
instant". `adapter` is the caller's own `GitHubAdapter` implementation -- never selected,
defaulted, or constructed by this route itself.

`subject_fingerprint` is accepted but never trusted for an `observation_evidence` subject:
this route always independently resolves the real record through `store.resolve_record` and
recomputes its own fingerprint via `evidence.identity.evidence_semantic_fingerprint`; a
caller-supplied value that disagrees with the recomputed one refuses
(`ProjectionRequirementError`). For a `difference`/`change` subject it is required (see §6,
disclosed scope boundary) and is trusted as supplied, since this route does not itself
reconstruct a Difference/Change record.

`route_observation_receipt_to_evidence` hands an already-real `GitHubObservationReceipt` to
the existing Evidence owner's own public `derive_evidence`, via a caller-supplied,
already-real, Change-free `evidence_request` grounded in the `verification_observation_request`
position (`evidence/engine.py`'s Change-Free Verification Evidence -- the identical position
Independent Verification's own `route_verification_result_to_evidence` already uses for a
structurally identical fact: an independent, Change-free confirmation that some external
observation still corresponds to a canonical subject). It calls `derive_evidence` exactly
once, constructs and injects `verification_result_provenance` from the receipt itself (never
accepted from a caller), and cross-validates the resulting record against both that provenance
and the requested `project_id`.

```text
GitHubAdapter (Protocol)
  adapter_identity              caller-inspectable identity, checked before either method
  materialize(*, projection_kind, target_repository, payload) -> Mapping[str, Any]
                                  called at most once per genuinely new projection identity;
                                  returns external_artifact_ref
  observe(*, external_artifact_ref) -> Mapping[str, Any]
                                  re-observes what is actually there now; returns
                                  {status, exists, observed_content_fingerprint, observed_at}

GitHubObservationReceipt (frozen dataclass)
  status                        one of VERIFIED | FAILED | INSUFFICIENT | UNAVAILABLE
  projection_envelope_id, subject_ref, external_artifact_ref, adapter_identity,
  github_authority_ref, input_refs, observations

Projection Envelope (persisted record)
  schema_version, projection_envelope_id, projection_envelope_semantic_fingerprint,
  subject_ref, subject_fingerprint, projection_kind, target_repository,
  projection_payload, projection_payload_fingerprint, external_artifact_ref,
  github_authority_ref, materialized_at
```

## 3. Frozen semantic decisions

1. **Projection only of an already-real canonical subject.** `project_to_github` is never
   invoked to *create* a Difference, Change, or Evidence record -- it projects one that
   already exists (Boot/Store-verified for `observation_evidence`, caller-attested-real for
   `difference`/`change` per §6's disclosed boundary). GitHub is a downstream surface, never
   an upstream source of canonical meaning.
2. **GitHub is projection and audit surface only, never canonical.** No field this package
   persists or returns is ever treated by any other owner as canonical Difference, Change,
   Evidence, Authority Decision, or State content. A Projection Envelope records that a
   projection happened and what it currently is understood to be, not a second copy of the
   canonical fact itself.
3. **Deliberate identity-scheme deviation: mapping key and semantic fingerprint are different
   projections of the record, not two encodings of the identical one.** Every other Kernel/
   adapter record in this repository content-addresses its own `_id` and `_semantic_fingerprint`
   over the identical field set (`evidence/identity.py`'s own convention). A Projection
   Envelope cannot use that convention and still satisfy items 5-6 below: re-projecting the
   *same* canonical subject, at the *same* fingerprint, kind, and target must reuse the *same*
   projection identity regardless of payload, while a *different* payload at that identical
   identity must fail closed rather than silently minting a second identity. `projection_
   envelope_id` (and its lookup form, `projection_mapping_key`) is therefore a function of
   exactly four fields -- `subject_ref`, `subject_fingerprint`, `projection_kind`,
   `target_repository` -- deliberately excluding `projection_payload`/
   `projection_payload_fingerprint`; `projection_envelope_semantic_fingerprint` additionally
   covers `projection_payload_fingerprint`, for tamper/mutation detection after persistence.
   This is a documented, deliberate deviation from the single-projection convention, not an
   oversight (`identity.py`'s own module docstring states the identical reasoning).
4. **Reuse, never blind re-materialization.** A request whose (subject, subject fingerprint,
   projection kind, target repository) already resolves to a committed Envelope never calls
   `adapter.materialize` again -- it calls `adapter.observe` against the already-recorded
   `external_artifact_ref` instead, and returns the existing Envelope unmodified, provided the
   caller's own `projection_payload_fingerprint` (always recomputed here, never trusted from a
   caller) exactly matches what that Envelope already committed.
5. **A payload conflict at an identical identity refuses outright.** A mismatch between the
   recomputed payload fingerprint and the already-committed Envelope's own raises
   `ConflictingProjectionPayloadError` before any adapter call and with zero Store writes --
   the existing, committed Envelope is never overwritten and no second external artifact is
   ever materialized for the same identity.
6. **Explicit GitHub Authority check, reusing the existing Boot owner.** `github_authority_ref`
   is trusted only once it canonical-reference-equals the real, independently re-verified
   `human_authority_ref` the existing Boot owner's own `boot_project` returns for this exact
   project/binding -- the identical pattern Independent Verification's own Structural Review
   Round 1 (P13-R1-F2) already established for its own selection-authority check. Every
   `boot_project` failure propagates unchanged; the adapter is called zero times on any such
   rejection.
7. **No fixed adapter.** `GitHubAdapter` is a provider-neutral protocol: a real GitHub REST
   client, a controlled fake for local tests, or a Human review interface may all implement it
   identically. No product, library, or transport is selected by this package; an
   implementation must not derive Difference meaning, select Change authority, determine
   Evidence sufficiency, close a Difference, transition Canonical State directly, or merge a
   Pull Request -- the Protocol's own two methods admit no such call.
8. **A bounded receipt, connected to existing Observation/Evidence/Reflow ownership, not a
   canonical fact on its own.** `GitHubObservationReceipt` is never itself a canonical
   Evidence record, an Authority Decision, a Closure receipt, or a State transition (the
   identical frozen semantic decision `VerificationResult` already states for Phase 13). It is
   the caller's own explicit input to `route_observation_receipt_to_evidence`, which routes it
   into the existing Evidence owner's own Change-Free Verification Evidence position -- the
   existing evidence-sufficiency/completion owner and the existing Difference/Reflow owner
   remain the only surfaces that ever decide sufficiency or closure from the resulting record.
9. **Failure is fail-closed.** An unresolvable subject, a subject/kind mismatch, a malformed
   `target_repository`/`projection_payload`, a `github_authority_ref` that does not
   canonical-reference-equal the real Boot-verified reference, a conflicting payload at an
   existing identity, an adapter that does not declare a readable `adapter_identity`, or a
   malformed adapter return value -- none of these ever produces an Envelope or a Receipt with
   a field substituted, narrowed, or silently accepted; every one of them raises before either
   is constructed.
10. **All inputs are explicit and frozen.** No repository discovery, filesystem scan,
    automatic Agent creation, or hidden environment input is permitted. This route reads no
    clock: `materialized_at` is a required, caller-supplied argument.
11. **No hidden execution capability beyond the one declared adapter boundary.** No model
    call, prompt execution, shell, subprocess, scheduler, background loop, or Agent-to-Agent
    messaging is implemented here. `GitHubAdapter.materialize`/`observe` are the only points at
    which this package ever crosses a process/network boundary, and only through the caller's
    own supplied implementation.
12. **Strict phase boundary.** Runtime Observation is Phase 15; Multi-model 16; URL Read-only
    17; Autonomous Change 18; Multi-Agent 19 remain out of scope. GitHub Issue close, Pull
    Request merge, and Difference closure driven by GitHub state are explicitly not
    implemented by this Phase.

## 4. Canonical owner

```text
src/manosube_agent_civilization/projection/
├── __init__.py           public exports
├── errors.py              ProjectionError / ProjectionRequirementError /
│                           ConflictingProjectionPayloadError / ProjectionValueError /
│                           ProjectionAdapterError
├── types.py               GitHubAdapter (Protocol) / GitHubObservationReceipt
├── identity.py             projection_mapping_key / projection_envelope_id /
│                           projection_envelope_semantic_fingerprint /
│                           projection_payload_fingerprint
├── engine.py               derive_projection_envelope
├── github_adapter.py       FakeGitHubAdapter / RealGitHubAdapter
├── receipt_handoff.py      route_observation_receipt_to_evidence
└── route.py                project_to_github
```

`ProjectionRequirementError` (and its subclass `ConflictingProjectionPayloadError`) exist only
for the admission boundaries this layer itself owns (subject/target/payload/authority
admission, and the identity/conflict semantics §3 items 3-5 fix). `ProjectionAdapterError`
exists only for a supplied `GitHubAdapter`'s own return-value shape and for adapter-reported
failure (outage, permission denial, rate limit, ambiguous outcome, transport failure) -- never
retried or silently substituted with a manufactured success. `ProjectionValueError` exists only
for `GitHubObservationReceipt`'s own deep-freeze admission (the identical fail-closed
discipline Independent Verification's own Structural Review Round 1, P13-R1-F3, already
established). Every Boot/Store/Evidence failure remains that owning domain's own typed error;
this layer never catches or reclassifies one.

## 5. Canonical route

```text
1. Validate project_id and project_binding_id are each an explicit canonical identity
   (never a path/URL/locator).
2. Validate subject_ref is an explicit {"kind", "id"} reference whose kind is one of
   difference/change/observation_evidence, and that its kind matches what projection_kind
   requires (DIFFERENCE_ISSUE -> difference, CHANGE_PULL_REQUEST -> change,
   EVIDENCE_ARTIFACT -> observation_evidence).
3. Validate target_repository declares host="github" and non-empty owner/repo.
4. Validate projection_payload is an explicit mapping.
5. Call the existing Boot owner's own public boot_project(store, project_id=project_id,
   project_binding_id=project_binding_id) exactly once and require github_authority_ref to
   canonical-reference-equal the real, independently re-verified
   BootContext.human_authority_ref that call returns. Every Boot/Binding/Store failure
   boot_project itself raises propagates unchanged.
6. If subject_ref.kind == "observation_evidence": resolve the real record through
   store.resolve_record(project_id, "observation_evidence", subject_ref.id) -- an
   unresolvable subject refuses. Recompute its own fingerprint via evidence.identity.
   evidence_semantic_fingerprint; a caller-supplied subject_fingerprint that disagrees
   refuses. Otherwise (difference/change): require subject_fingerprint to be supplied by
   the caller (§6, disclosed scope boundary) and trust it as given.
7. Compute the deterministic mapping key over (subject_ref, real subject_fingerprint,
   projection_kind, target_repository) and the deterministic payload fingerprint over
   projection_payload (both always recomputed here, never trusted from a caller).
8. Resolve the mapping key through store.resolve_record(project_id, "projection_envelope",
   mapping_key):
   8a. If a committed Envelope already exists: if its own projection_payload_fingerprint
       disagrees with the recomputed one, raise ConflictingProjectionPayloadError with zero
       Store writes and zero adapter calls beyond the observe in 8b. Otherwise call
       adapter.observe(external_artifact_ref=<the existing Envelope's own ref>) exactly
       once, build one GitHubObservationReceipt, and return {"envelope": existing,
       "receipt": receipt, "reused": True}.
   8b. If no committed Envelope exists: require adapter.adapter_identity to be a readable
       mapping, then call adapter.materialize(...) exactly once and validate its return
       shape. Derive a new Projection Envelope (engine.derive_projection_envelope) from the
       real, resolved inputs and re-verify its own derived identity equals the mapping key
       computed in step 7. Persist it through the existing Store's own single sanctioned
       committer (store.commit.commit_state_transition), then call adapter.observe(...)
       exactly once, build one GitHubObservationReceipt, and return {"envelope": envelope,
       "receipt": receipt, "reused": False}.
9. route_observation_receipt_to_evidence (caller-invoked separately): validate the receipt
   is a real GitHubObservationReceipt instance and evidence_request is Change-free and
   carries a verification_observation_request; construct verification_result_provenance
   from the receipt itself (never accepted from a caller); call the existing Evidence
   owner's own derive_evidence exactly once; require the returned record's own provenance
   and project_id to exactly match what this handoff constructed/requested.
```

## 6. Disclosed scope boundary

Only an `observation_evidence` subject is resolved and independently fingerprinted by this
route itself. `difference` and `change` are never Store-owned record kinds in this vertical
(`reflow/reference_registry.py`'s own documented classification), so a `difference`/`change`
subject's `subject_fingerprint` must be supplied by the caller, who already holds the real
record it was derived from. Deriving a Difference/Change subject fingerprint independently
within this route would require a second State/Difference reconstruction this route does not
perform and Issue #62's own prohibitions forbid inventing (`PARALLEL_CANONICAL_OWNER=false`).
This mirrors the identical, already-established precedent Independent Verification's own route
carries for its own `target_refs`. This is a disclosed boundary, not a silently narrowed one.

```text
OBSERVATION_EVIDENCE_SUBJECT_INDEPENDENTLY_RESOLVED_AND_FINGERPRINTED=true
DIFFERENCE_SUBJECT_FINGERPRINT_CALLER_SUPPLIED=true
CHANGE_SUBJECT_FINGERPRINT_CALLER_SUPPLIED=true
SECOND_STATE_OR_DIFFERENCE_RECONSTRUCTION_FOR_FINGERPRINTING=false
```

## 7. Required rejection proofs

At minimum, this layer fails closed, with zero Store mutation and zero adapter calls, for:

```text
- a project_id or project_binding_id that is a path/URL/locator rather than a plain identity
- a subject_ref missing kind/id, or whose kind is outside {difference, change,
  observation_evidence}
- a subject_ref whose kind does not match what projection_kind requires
- an unrecognized projection_kind
- a target_repository that does not declare host="github", or with a missing/empty
  owner/repo
- a non-mapping projection_payload
- any Boot/Binding/Store failure the existing Boot owner's own boot_project raises for
  project_id/project_binding_id (propagates unchanged)
- a github_authority_ref that diverges from the real, Boot-verified Human Authority
  reference
- an observation_evidence subject_ref the Store does not resolve for this project
- a caller-supplied subject_fingerprint for an observation_evidence subject that disagrees
  with the real, recomputed fingerprint
- a missing or empty subject_fingerprint for a difference/change subject
- an adapter that does not declare a readable adapter_identity attribute (checked before
  materialize is ever called)
```

And, once an existing Envelope has been resolved at the identical identity (zero
`materialize` calls on this path):

```text
- a recomputed projection_payload_fingerprint that disagrees with the existing Envelope's
  own -- raises ConflictingProjectionPayloadError before observe is called, the existing
  Envelope is never overwritten and no second artifact is materialized
```

And, once `adapter.materialize`/`adapter.observe` has been called (Store mutation remains
zero until the one `commit_state_transition` call in step 8b, and never occurs at all on the
reuse path in step 8a):

```text
- a non-mapping return value from materialize/observe
- a materialize return value missing host/owner/repo/artifact_kind/external_id/url, or
  naming an artifact_kind outside {issue, pull_request, check_run, review, artifact}
- an observe return value whose own 'exists' is not a bool, or whose own 'status' is not a
  string when 'exists' is not False
- a newly derived Envelope whose own recomputed projection_envelope_id does not equal the
  mapping key computed before materialization (engine.py's own internal self-consistency
  check)
```

And, for `route_observation_receipt_to_evidence`, with zero calls to `derive_evidence` and no
Evidence record produced or returned:

```text
- a receipt argument that is not a GitHubObservationReceipt instance
- an evidence_request argument that is not an explicit mapping
- an evidence_request carrying a change_request (Projection never executes or grounds a
  Change)
- an evidence_request carrying a post_change_observation_request
- an evidence_request with no verification_observation_request -- the one Evidence position
  this handoff produces
- an evidence_request that already carries a verification_result_provenance (this handoff
  constructs it from receipt itself, never accepts one from a caller)
```

And, once `derive_evidence` has been called and returned a genuine canonical Evidence record
(the one point past which the existing Evidence owner's own admission gate has already
passed):

```text
- a derived Evidence record whose own verification_result_provenance does not exactly equal
  what this handoff constructed from receipt
- a derived Evidence record whose own target.project_id does not match the requested
  project_id
```

Static conformance additionally proves: exactly two public callables (`project_to_github`,
`route_observation_receipt_to_evidence`); that no module in this package ever imports
`difference` (except the shared `difference.validation` schema-validator utility),
`reflow`, `binding`, or `independent_verification`; that `evidence` is importable only from
`route.py` (read-only `evidence.identity.evidence_semantic_fingerprint`) and
`receipt_handoff.py` (the one `derive_evidence` call); that `boot` is importable only from
`route.py` and only to call `boot_project` exactly once; that `store.commit` is never called
directly anywhere in this package (the sanctioned single committer is
`store.commit.commit_state_transition`, called exactly once, only from `route.py`); and that
no module besides `github_adapter.py` imports a network, subprocess, or GitHub transport
surface.

## 8. Explicit non-claims

```text
GITHUB_ISSUE_CLOSE_IMPLEMENTED=false
GITHUB_PULL_REQUEST_MERGE_IMPLEMENTED=false
DIFFERENCE_CLOSURE_FROM_GITHUB_STATE_IMPLEMENTED=false
AUTOMATIC_ADAPTER_SELECTION=false
NEW_STATE_OWNER=false
NEW_EVIDENCE_OWNER=false
NEW_AUTHORITY_OWNER=false
NEW_STORE_OWNER=false
PROJECTION_DIRECT_STORE_WRITE_OUTSIDE_COMMIT_STATE_TRANSITION=false
EXISTING_EVIDENCE_OWNER_HANDOFF_REQUIRED=true
CALLER_MAPPING_EQUALITY_AS_AUTHORITY=false
BOOT_HUMAN_AUTHORITY_REF_ALONE_IS_SELECTION_DECISION=false
PARALLEL_OR_HIDDEN_CANONICAL_OWNER=false
```

## 9. V3 real-GitHub vertical proof: prepared, not executed

`github_adapter.py`'s `RealGitHubAdapter` is a complete, real implementation over the GitHub
REST API (stdlib `urllib` only, no new runtime dependency), and
`tests/integration/projection/test_v3_real_github_vertical_proof.py` is a real harness proving
the boundary itself is real (one test runs, asserting the harness correctly detects the
absence of live-write authorization). Every assertion that would perform a live write is
`pytest.mark.skip`, citing this exact reason:

```text
V3_EXTERNAL_WRITE_ALLOWED_BY_THIS_COMMENT=false
```

`ADOPT_P14_D001_PROJECTION_ENVELOPE_IMPLEMENTATION` (Issue #62) explicitly authorizes
*preparing* this harness and explicitly withholds authority to *execute* it against any live
target until a separate, later SHUKOU decision freezes the exact target repository, artifact
count, naming, cleanup, and no-merge boundary
(`PRE_V3_EXACT_TARGET_AND_ARTIFACT_BOUNDARY_RECONFIRMATION_REQUIRED=true`). This section
records that boundary as still in force as of this delivery.

```text
V3_HARNESS_PREPARED=true
V3_EXECUTED_AGAINST_LIVE_TARGET=false
V3_TARGET_REPOSITORY_FROZEN=false
V3_ARTIFACT_COUNT_FROZEN=false
V3_NAMING_FROZEN=false
V3_CLEANUP_BOUNDARY_FROZEN=false
V3_NO_MERGE_BOUNDARY_FROZEN=true
PHASE_14_COMPLETE=false
PHASE_15_ALLOWED=false
```
