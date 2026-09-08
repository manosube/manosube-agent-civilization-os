# Identity-Preserving GitHub Projection Contract (Phase 14, Issue #62)

```text
DOC_TYPE=PROJECTION_CONTRACT
DOCUMENT_ID=PROJECTION-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PROJECTION_ADAPTER
ADOPTION_ID=ADOPT_P14_D001_PROJECTION_ENVELOPE_IMPLEMENTATION
CORRECTION_ADOPTION_ID=ADOPT_P14_R1_CANONICAL_AUTHORITY_SUBJECT_AND_RECOVERABLE_PROJECTION
GOVERNING_ISSUE=#62
REVIEWED_MAIN_SHA=7fc597356330a0d1da7a334ef20cd913b74154d
```

See `PROJECTION_INDEX.md` for this contract set's own position and reading order.

This document records the delivery as corrected by Structural Review Round 1
(`ADOPT_P14_R1_CANONICAL_AUTHORITY_SUBJECT_AND_RECOVERABLE_PROJECTION`, Issue #62), which
found and required correction of seven findings (P14-R1-F1 through F7): a genuine,
exact-binding Authority Decision for every projection operation (F1); real, schema-validated
Difference/Change subject admission in place of a bare caller-declared fingerprint (F2);
independently recomputed observable-content comparison and project-carrying receipts, refusing
cross-project relabeling (F3); recoverable idempotency across the external-write boundary via a
durable correlation key (F4); an executable V3 harness for all three projection kinds and a
complete `RealGitHubAdapter` (F5); distinct typed GitHub observation outcomes in place of a
collapsed `FAILED`/`exists=False` (F6); and a genuine SHA-256 content fingerprint in place of a
truncated raw-byte prefix (F7). Every section below reflects the corrected design; where a
frozen decision from the original delivery was superseded rather than merely extended, this is
stated explicitly at the point of change.

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
    github_projection_grant_refs: list[Mapping[str, Any]],
    subject_record: Mapping[str, Any] | None = None,
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

`github_projection_grant_refs` (Structural Review Round 1, P14-R1-F1) is the caller's own
explicit collection of `{"kind": "github_projection_grant", "id": ...}` references, each
resolved through the Store and offered to the existing Authority owner's own
`evaluate_projection_authorization`; grant *content* is never an accepted argument shape, the
identical discipline Independent Verification's own `verifier_selection_grant_refs` already
established. `subject_record` (Structural Review Round 1, P14-R1-F2) is required for a
`difference`/`change` subject -- the real, canonical record body, independently
schema-validated and fingerprint-recomputed by this route -- and ignored for an
`observation_evidence` subject, which remains Store-resolved instead.

`subject_fingerprint` is accepted but never trusted alone, for any subject kind: this route
always independently resolves or admits the real record (`store.resolve_record` for
`observation_evidence`; schema validation and identity recomputation of the caller-supplied
`subject_record` for `difference`/`change`) and recomputes its own fingerprint; a
caller-supplied value that disagrees with the recomputed one refuses
(`ProjectionRequirementError`). This supersedes the original delivery's frozen decision that a
`difference`/`change` subject's fingerprint was caller-supplied and trusted as given -- see §6.

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
  materialize(*, projection_kind, target_repository, payload, correlation_key) ->
                                  Mapping[str, Any]
                                  called at most once per genuinely new projection identity;
                                  returns external_artifact_ref; correlation_key (Structural
                                  Review Round 1, P14-R1-F4) is the caller's own durable,
                                  recomputable idempotency key
  find_by_correlation_key(*, correlation_key, target_repository, projection_kind, payload) ->
                                  Mapping[str, Any] | None
                                  Structural Review Round 1 (P14-R1-F4): called before
                                  materialize on every attempt, including the first --
                                  recovers an artifact a prior attempt genuinely materialized
                                  but never committed an Envelope for
  observe(*, external_artifact_ref) -> Mapping[str, Any]
                                  re-observes what is actually there now; returns
                                  {observation_outcome, observed_content_fingerprint,
                                  observed_at} -- observation_outcome (Structural Review
                                  Round 1, P14-R1-F6) is one of FOUND | NOT_FOUND |
                                  PERMISSION_DENIED | UNAVAILABLE; only NOT_FOUND
                                  establishes non-existence

GitHubObservationReceipt (frozen dataclass)
  status                        one of VERIFIED | FAILED | INSUFFICIENT | UNAVAILABLE (this
                                  route's own _observe never produces INSUFFICIENT; the value
                                  remains in the schema's closed set for a future caller)
  project_id                    Structural Review Round 1 (P14-R1-F3): the receipt's own
                                  originating project identity, checked by
                                  route_observation_receipt_to_evidence against the requested
                                  project_id -- a receipt genuinely produced for one project
                                  can never be relabeled as Evidence for another
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
4. **Reuse, never blind re-materialization -- and recoverable across the external-write
   boundary itself (Structural Review Round 1, P14-R1-F4).** A request whose (subject,
   subject fingerprint, projection kind, target repository) already resolves to a committed
   Envelope never calls `adapter.materialize` again -- it calls `adapter.observe` against the
   already-recorded `external_artifact_ref` instead, and returns the existing Envelope
   unmodified, provided the caller's own `projection_payload_fingerprint` (always recomputed
   here, never trusted from a caller) exactly matches what that Envelope already committed.
   Additionally, even when no Envelope is yet committed, this route calls
   `adapter.find_by_correlation_key` before ever calling `materialize` -- on every attempt,
   including the first. Because the deterministic mapping key is itself the correlation key
   (durable and recomputable with no I/O, since it is a pure function of already-real inputs),
   an attempt interrupted after a genuine external success but before (or during) the Store
   commit converges on retry to the identical external artifact rather than creating a
   duplicate, with no separate persisted intent record of this route's own required.
5. **A payload conflict at an identical identity refuses outright.** A mismatch between the
   recomputed payload fingerprint and the already-committed Envelope's own raises
   `ConflictingProjectionPayloadError` before any adapter call and with zero Store writes --
   the existing, committed Envelope is never overwritten and no second external artifact is
   ever materialized for the same identity.
6. **Explicit GitHub Authority check, reusing the existing Boot owner -- necessary but not by
   itself sufficient (Structural Review Round 1, P14-R1-F1).** `github_authority_ref` is
   trusted only once it canonical-reference-equals the real, independently re-verified
   `human_authority_ref` the existing Boot owner's own `boot_project` returns for this exact
   project/binding -- the identical pattern Independent Verification's own Structural Review
   Round 1 (P13-R1-F2) already established for its own selection-authority check. Every
   `boot_project` failure propagates unchanged; the adapter is called zero times on any such
   rejection. This equality alone proves only who owns Human Authority for the Project, never
   that this exact projection was authorized -- see item 13 below for the additional, required
   Authority Decision.
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
13. **A genuine, exact-binding Authority Decision gates every projection operation (Structural
    Review Round 1, P14-R1-F1).** `github_projection_grant_refs` -- the caller's own explicit
    `{"kind": "github_projection_grant", "id": ...}` references, resolved through the Store --
    are offered to the existing Authority owner's own new `evaluate_projection_authorization`
    (an extension of the existing Authority owner, `authority/projection_authorization.py`,
    mirroring Independent Verification's own `evaluate_verifier_selection`). Authorization
    requires a resolved grant whose own `project_id`, `subject_ref`, `subject_fingerprint`,
    `projection_kind`, `target_repository`, `payload_fingerprint`, and `permitted_action`
    (`MATERIALIZE_PROJECTION`) exactly bind to this precise request, whose `status` is
    `ACTIVE`, and whose `granted_by` exactly equals the real, Boot-verified Human Authority
    reference -- checked on every request, the reuse-observe path included, since it too is a
    real external call this Decision gates. A fabricated, stale, wrong-target, wrong-payload,
    or merely-owner-equal grant calls the adapter zero times. This new Authority extension is a
    disclosed, bounded scope decision: it does not add the full Human Grant Declaration +
    Ed25519 signature layer Independent Verification's own Structural Review Round 5/5-R1
    eventually added for `verifier_selection_grant`, matching instead the rigor level of
    Independent Verification's own Round 3/4 (a Store-resolved genuine grant, exact field
    binding, `ACTIVE` status, `granted_by` equal to the real Human Authority reference) -- a
    candidate future Difference, recorded in `authority/projection_authorization.py`'s own
    module docstring, not a silently narrowed one.
14. **A Difference/Change subject is admitted from its real, canonical record body, never a
    bare caller-declared fingerprint (Structural Review Round 1, P14-R1-F2).** `subject_record`
    is schema-validated against the existing Difference/Change owners' own schemas, required to
    name the requested `project_id` as its own, and its own content-addressed identity
    (`difference.identity.difference_id` / `change.identity.change_id`) is recomputed and
    required to equal `subject_ref`'s own declared `id`. The subject's own semantic fingerprint
    used throughout this route (the mapping key, the Authority Decision request, the persisted
    Envelope) is always this recomputed value, never a caller-supplied string accepted at face
    value.
15. **The adapter's own reported observation status is never trusted alone; independently
    recomputed content-fingerprint comparison, and project-carrying receipts, close the
    substitution/relabeling gap (Structural Review Round 1, P14-R1-F3).** `_observe` compares
    the adapter's own reported `observed_content_fingerprint` against
    `observable.expected_observable_fingerprint(projection_kind, committed_payload)` --
    independently recomputed from the real, already-committed payload this route itself holds,
    never from adapter-supplied content -- and forces a non-`VERIFIED` result on any mismatch,
    including a genuine external artifact that has been substituted or tampered with after
    materialization. Every `GitHubObservationReceipt` additionally carries its own `project_id`
    (the exact value this route independently verified), and
    `route_observation_receipt_to_evidence` refuses a receipt whose `project_id` does not equal
    the requested one before `derive_evidence` is ever called -- a receipt genuinely produced
    for one project can never be relabeled as Evidence for a different project.
16. **Distinct, typed GitHub observation outcomes; only an authoritative absence establishes
    non-existence (Structural Review Round 1, P14-R1-F6).** `adapter.observe`'s own
    `observation_outcome` is one of `FOUND`, `NOT_FOUND`, `PERMISSION_DENIED`, or `UNAVAILABLE`
    (`types.OBSERVATION_OUTCOME_KINDS`) -- never collapsed into a single `FAILED`/`exists=False`
    result. Only `NOT_FOUND` yields `exists=False`; `PERMISSION_DENIED` and `UNAVAILABLE` both
    leave existence undetermined (`exists=None`, receipt `status="UNAVAILABLE"`) rather than
    being folded into a false absence or a false confirmation. `RealGitHubAdapter`'s own
    `_classify_error` distinguishes an authoritative 404 (`NOT_FOUND`) from permission denial,
    rate limiting, and transport/5xx failure (`PERMISSION_DENIED` / `UNAVAILABLE`).
17. **A genuine content fingerprint, never a truncated byte prefix (Structural Review Round 1,
    P14-R1-F7).** `FakeGitHubAdapter.observe` computes `observed_content_fingerprint` via the
    identical `observable.expected_observable_fingerprint` this route itself uses to verify
    it -- a real SHA-256 digest over the canonical observable-payload projection for the
    relevant `projection_kind`, never the first 64 hex characters of raw JSON bytes mislabeled
    `sha256:`.

## 4. Canonical owner

```text
src/manosube_agent_civilization/projection/
├── __init__.py           public exports
├── errors.py              ProjectionError / ProjectionRequirementError /
│                           ConflictingProjectionPayloadError / ProjectionValueError /
│                           ProjectionAdapterError
├── types.py               GitHubAdapter (Protocol) / GitHubObservationReceipt /
│                           OBSERVATION_OUTCOME_KINDS (Structural Review Round 1, P14-R1-F6)
├── identity.py             projection_mapping_key / projection_envelope_id /
│                           projection_envelope_semantic_fingerprint /
│                           projection_payload_fingerprint
├── observable.py           expected_observable_projection / expected_observable_fingerprint
│                           (Structural Review Round 1, P14-R1-F3/F7)
├── engine.py               derive_projection_envelope
├── github_adapter.py       FakeGitHubAdapter / RealGitHubAdapter
├── receipt_handoff.py      route_observation_receipt_to_evidence
└── route.py                project_to_github

src/manosube_agent_civilization/authority/
└── projection_authorization.py   evaluate_projection_authorization (Structural Review
                                    Round 1, P14-R1-F1 -- an extension of the existing
                                    Authority owner, not a new one)
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
   refuses. Otherwise (difference/change, Structural Review Round 1, P14-R1-F2):
   schema-validate the caller-supplied subject_record against the existing Difference/Change
   owner's own schema, require its own project_id to equal the requested project_id,
   recompute its own content-addressed identity (difference_id / change_id) and require it to
   equal subject_ref.id, then recompute the subject's own semantic fingerprint from
   subject_record itself; a caller-supplied subject_fingerprint that disagrees refuses.
7. Compute the deterministic mapping key over (subject_ref, real subject_fingerprint,
   projection_kind, target_repository) and the deterministic payload fingerprint over
   projection_payload (both always recomputed here, never trusted from a caller).
8. Resolve github_projection_grant_refs through the Store and require a genuine, exact-binding
   github_projection_grant Authority Decision (evaluate_projection_authorization) for this
   precise (subject, subject fingerprint, projection kind, target repository, payload
   fingerprint) before any Store lookup or adapter call in steps 9-10 (Structural Review
   Round 1, P14-R1-F1). Every AuthorityError propagates unchanged; a non-AUTHORIZED decision
   refuses with zero Store writes and zero adapter calls.
9. Resolve the mapping key through store.resolve_record(project_id, "projection_envelope",
   mapping_key):
   9a. If a committed Envelope already exists: if its own projection_payload_fingerprint
       disagrees with the recomputed one, raise ConflictingProjectionPayloadError with zero
       Store writes and zero adapter calls beyond the observe in 9b. Otherwise call
       adapter.observe(external_artifact_ref=<the existing Envelope's own ref>) exactly
       once, build one GitHubObservationReceipt (step 11), and return {"envelope": existing,
       "receipt": receipt, "reused": True}.
   9b. If no committed Envelope exists: require adapter.adapter_identity to be a readable
       mapping, then call adapter.find_by_correlation_key(correlation_key=mapping_key, ...)
       (Structural Review Round 1, P14-R1-F4) before ever calling materialize. If it returns a
       real ref, validate and reuse it; otherwise call adapter.materialize(...,
       correlation_key=mapping_key) exactly once and validate its return shape. Derive a new
       Projection Envelope (engine.derive_projection_envelope) from the real, resolved inputs
       and re-verify its own derived identity equals the mapping key computed in step 7.
       Persist it through the existing Store's own single sanctioned committer
       (store.commit.commit_state_transition), then call adapter.observe(...) exactly once,
       build one GitHubObservationReceipt (step 11), and return {"envelope": envelope,
       "receipt": receipt, "reused": False}.
10. Both 9a and 9b resolve external_artifact_ref through _require_external_artifact_ref, which
    refuses an artifact bound to a different target_repository or naming an artifact_kind
    outside the closed set projection_kind permits (Structural Review Round 1, P14-R1-F3).
11. Build the GitHubObservationReceipt from adapter.observe's own typed observation_outcome
    (FOUND / NOT_FOUND / PERMISSION_DENIED / UNAVAILABLE -- Structural Review Round 1,
    P14-R1-F6): on FOUND, independently recompute the expected observable-payload fingerprint
    from the real, already-committed payload (observable.expected_observable_fingerprint) and
    compare it against the adapter's own reported observed_content_fingerprint, forcing status
    != VERIFIED on any mismatch (Structural Review Round 1, P14-R1-F3); on NOT_FOUND,
    exists=False, status=FAILED; on PERMISSION_DENIED/UNAVAILABLE, exists=None,
    status=UNAVAILABLE. The receipt carries its own project_id -- the exact value this route
    independently verified in step 5 -- as a required field (Structural Review Round 1,
    P14-R1-F3).
12. route_observation_receipt_to_evidence (caller-invoked separately): validate the receipt
    is a real GitHubObservationReceipt instance whose own project_id equals the requested
    project_id (Structural Review Round 1, P14-R1-F3 -- refusing before derive_evidence is
    ever called) and evidence_request is Change-free and carries a
    verification_observation_request; construct verification_result_provenance from the
    receipt itself (never accepted from a caller); call the existing Evidence owner's own
    derive_evidence exactly once; require the returned record's own provenance and project_id
    to exactly match what this handoff constructed/requested.
```

## 6. Corrected scope boundary (Structural Review Round 1, P14-R1-F2)

The original delivery's disclosed boundary -- that a `difference`/`change` subject's
`subject_fingerprint` is caller-supplied and trusted as given, since neither is a Store-owned
record kind in this vertical -- is superseded by Structural Review Round 1 (P14-R1-F2). Every
subject, regardless of kind, is now independently admitted and fingerprinted by this route
itself: an `observation_evidence` subject continues to be Store-resolved directly; a
`difference`/`change` subject is admitted from the caller-supplied `subject_record` (the real
canonical record body, which this route does not construct or invent), schema-validated
against the existing Difference/Change owner's own schema, checked to name the requested
`project_id`, and content-address-recomputed through the existing owner's own
`difference_id`/`change_id` -- never a bare, unverified caller-declared fingerprint string.

One narrower boundary remains, disclosed and unchanged from the original delivery: this route
does not itself resolve a `difference`/`change` record from the Store, since neither is a
Store-owned record kind in this vertical (`reflow/reference_registry.py`'s own documented
classification) -- the caller must already hold the real record body. This differs from the
original boundary only in degree (identity and fingerprint are now independently recomputed
from that body, never trusted from a bare caller-declared string) and mirrors the identical,
already-established precedent Independent Verification's own route carries for its own
`target_refs`.

A Difference has no separate broader semantic fingerprint in this Kernel encoded in the
`sha256:`-prefixed form the Projection Envelope schema's own `subject_fingerprint` requires
(`difference_id`'s own `D-`-prefixed uppercase-hex encoding does not match that pattern); this
route further hashes the real, recomputed `difference_id` into that required form
(`"sha256:" + sha256(difference_id).hexdigest()`), a documented, deliberate re-encoding of an
already-real, already-verified identity -- never itself trusted as an independent identity, and
`subject_ref.id` is still checked against the raw `difference_id` directly, not this derived
encoding of it.

```text
OBSERVATION_EVIDENCE_SUBJECT_INDEPENDENTLY_RESOLVED_AND_FINGERPRINTED=true
DIFFERENCE_SUBJECT_INDEPENDENTLY_SCHEMA_VALIDATED_AND_FINGERPRINTED=true
CHANGE_SUBJECT_INDEPENDENTLY_SCHEMA_VALIDATED_AND_FINGERPRINTED=true
DIFFERENCE_CHANGE_SUBJECT_RECORD_BODY_CALLER_SUPPLIED=true
DIFFERENCE_CHANGE_SUBJECT_RESOLVED_FROM_STORE_BY_THIS_ROUTE=false
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
- a missing subject_record for a difference/change subject (Structural Review Round 1,
  P14-R1-F2)
- a subject_record that fails the existing Difference/Change owner's own schema validation
- a subject_record naming a different project_id than requested
- a subject_record whose own recomputed difference_id/change_id does not equal subject_ref.id
- a caller-supplied subject_fingerprint for a difference/change subject that disagrees with
  the real, recomputed fingerprint of subject_record
- an adapter that does not declare a readable adapter_identity attribute (checked before
  materialize is ever called)
- a fabricated, unresolvable, stale, wrong-target, wrong-payload, or merely-owner-equal
  github_projection_grant_refs entry, or a PROJECTION_REFUSED decision from
  evaluate_projection_authorization (Structural Review Round 1, P14-R1-F1) -- checked before
  any Store lookup or adapter call, on every request including the reuse-observe path
```

And, once an existing Envelope has been resolved at the identical identity (zero
`materialize` calls on this path):

```text
- a recomputed projection_payload_fingerprint that disagrees with the existing Envelope's
  own -- raises ConflictingProjectionPayloadError before observe is called, the existing
  Envelope is never overwritten and no second artifact is materialized
```

And, once `adapter.find_by_correlation_key`/`adapter.materialize`/`adapter.observe` has been
called (Store mutation remains zero until the one `commit_state_transition` call in step 9b,
and never occurs at all on the reuse path in step 9a):

```text
- a non-mapping return value from find_by_correlation_key/materialize/observe
- a find_by_correlation_key/materialize return value missing
  host/owner/repo/artifact_kind/external_id/url, naming an artifact_kind outside
  {issue, pull_request, check_run, review, artifact}, naming a different target_repository
  than requested, naming an artifact_kind projection_kind could never produce, or whose url
  does not name the requested repository (Structural Review Round 1, P14-R1-F3)
- an observe return value whose own observation_outcome is not one of FOUND/NOT_FOUND/
  PERMISSION_DENIED/UNAVAILABLE (Structural Review Round 1, P14-R1-F6), or a FOUND outcome
  with no observed_content_fingerprint
- a FOUND observation whose own observed_content_fingerprint disagrees with the
  independently recomputed expected_observable_fingerprint of the real, committed payload --
  forces a non-VERIFIED receipt status rather than trusting the adapter's own report
  (Structural Review Round 1, P14-R1-F3)
- a newly derived Envelope whose own recomputed projection_envelope_id does not equal the
  mapping key computed before materialization (engine.py's own internal self-consistency
  check)
```

And, for `route_observation_receipt_to_evidence`, with zero calls to `derive_evidence` and no
Evidence record produced or returned:

```text
- a receipt argument that is not a GitHubObservationReceipt instance
- a receipt whose own project_id does not equal the requested project_id (Structural Review
  Round 1, P14-R1-F3 -- a receipt genuinely produced for one project can never be relabeled
  as Evidence for a different project)
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
`reflow`, `binding`, or `independent_verification`; that `evidence` is importable only from
`route.py` (read-only `evidence.identity.evidence_semantic_fingerprint`) and
`receipt_handoff.py` (the one `derive_evidence` call); that `boot` is importable only from
`route.py` and only to call `boot_project` exactly once; that `authority` is importable only
from `route.py` and only to call `evaluate_projection_authorization` exactly once (Structural
Review Round 1, P14-R1-F1); that `difference.identity`/`change.identity` are importable only
from `route.py`, for their own read-only fingerprint functions -- never
`difference.engine`/`difference.graph`/`change.engine`, and no module besides `route.py`
imports `difference`/`change` at all beyond the shared `difference.validation`
schema-validator utility `engine.py` already uses (Structural Review Round 1, P14-R1-F2);
that `store.commit` is never called directly anywhere in this package (the sanctioned single
committer is `store.commit.commit_state_transition`, called exactly once, only from
`route.py`); and that no module besides `github_adapter.py` imports a network, subprocess, or
GitHub transport surface.

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
NEW_DIFFERENCE_OR_CHANGE_OWNER=false
PROJECTION_DIRECT_STORE_WRITE_OUTSIDE_COMMIT_STATE_TRANSITION=false
EXISTING_EVIDENCE_OWNER_HANDOFF_REQUIRED=true
CALLER_MAPPING_EQUALITY_AS_AUTHORITY=false
BOOT_HUMAN_AUTHORITY_REF_ALONE_IS_SELECTION_DECISION=false
PARALLEL_OR_HIDDEN_CANONICAL_OWNER=false
GITHUB_PROJECTION_GRANT_IS_AN_AUTHORITY_EXTENSION_NOT_A_NEW_OWNER=true
HUMAN_GRANT_DECLARATION_SIGNATURE_LAYER_FOR_GITHUB_PROJECTION_GRANT=false
```

`GITHUB_PROJECTION_GRANT_IS_AN_AUTHORITY_EXTENSION_NOT_A_NEW_OWNER=true` records that
`github_projection_grant`/`github_projection_decision` (Structural Review Round 1, P14-R1-F1)
are new record kinds *owned by the existing Authority owner*, exactly as
`verifier_selection_grant` already is -- `NEW_AUTHORITY_OWNER` above remains `false`.
`HUMAN_GRANT_DECLARATION_SIGNATURE_LAYER_FOR_GITHUB_PROJECTION_GRANT=false` records the
disclosed scope boundary §3 item 13 states: this extension does not add the Human Grant
Declaration + Ed25519 signature layer Independent Verification's own `verifier_selection_grant`
eventually gained in its own Structural Review Round 5/5-R1 -- a candidate future Difference,
not a silent gap.

## 9. V3 real-GitHub vertical proof: prepared, not executed

`github_adapter.py`'s `RealGitHubAdapter` is a complete, real implementation over the GitHub
REST API (stdlib `urllib` only, no new runtime dependency) for all three projection kinds,
including `EVIDENCE_ARTIFACT` (Structural Review Round 1, P14-R1-F5 -- the original delivery's
`materialize` did not implement this artifact kind at all). The harness in
`tests/integration/projection/test_v3_real_github_vertical_proof.py` is now mechanically
complete and executable, not merely a stub: a shared `_run_vertical_proof` helper builds a
real, Store-committed subject (a Difference, a Change, or an `observation_evidence` record,
per projection kind) and a real `github_projection_grant`, then calls `project_to_github`
end-to-end. Four tests run unconditionally against `FakeGitHubAdapter` -- the pre-existing
authorization-gate check, plus three new tests, one per projection kind, each asserting a
`VERIFIED` receipt (Structural Review Round 1, P14-R1-F5; the original delivery's two
Difference/Change-kind V3 test bodies were bare `NotImplementedError`, and its Evidence-kind
body targeted an artifact kind the adapter could not yet materialize). The three
`RealGitHubAdapter`-based tests call the identical `_run_vertical_proof` helper with real
bodies -- no more `NotImplementedError` -- but every assertion that would perform a live write
remains `pytest.mark.skip`, citing this exact reason:

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
