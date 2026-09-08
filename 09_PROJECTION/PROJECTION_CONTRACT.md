# Identity-Preserving GitHub Projection Contract (Phase 14, Issue #62)

```text
DOC_TYPE=PROJECTION_CONTRACT
DOCUMENT_ID=PROJECTION-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PROJECTION_ADAPTER
ADOPTION_ID=ADOPT_P14_D001_PROJECTION_ENVELOPE_IMPLEMENTATION
CORRECTION_ADOPTION_ID=ADOPT_P14_R1_CANONICAL_AUTHORITY_SUBJECT_AND_RECOVERABLE_PROJECTION
CORRECTION_ADOPTION_ID_ROUND_2=ADOPT_P14_R2_SIGNED_AUTHORITY_ATOMIC_PROJECTION_AND_REAL_V3
CORRECTION_ADOPTION_ID_ROUND_3=ADOPT_P14_R3_UNIQUE_CLAIM_ATTESTED_RECEIPT_AND_CONFIGURABLE_V3
CORRECTION_ADOPTION_ID_ROUND_4=ADOPT_P14_R4_TERMINAL_CLAIM_ATTESTED_RECEIPT_AND_SOURCE_EDIT_FREE_V3
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
truncated raw-byte prefix (F7).

It is further corrected by Structural Review Round 2
(`ADOPT_P14_R2_SIGNED_AUTHORITY_ATOMIC_PROJECTION_AND_REAL_V3`, Issue #62), which found and
required correction of four further findings (P14-R2-F1 through F4, §10): a genuine, signed
Human declaration anchoring every `github_projection_grant`, never a Store-resolved grant's own
self-consistency alone (F1); an atomic, recoverable claim/attempt state machine closing the
remaining search-then-create race between two genuinely concurrent callers (F2); an
independently-resolved, Store-corroborated Projection Envelope binding for every
`GitHubObservationReceipt` at hand-off, replacing an unchecked, publicly-settable `project_id`
field, together with an exact per-artifact-kind GitHub locator grammar (never a bare URL prefix)
(F3); and a corrected write/read observable transformation removing the correlation marker
self-defeat (F4), plus transport-level `RealGitHubAdapter` contract fixtures (F4b) -- F4b's own
exact target-bound V3 configuration (replacing the harness's remaining hardcoded `head_ref`/
`head_sha` placeholders) is disclosed as not yet closed this round; see §10's own F4 note.

It is further corrected by Structural Review Round 3
(`ADOPT_P14_R3_UNIQUE_CLAIM_ATTESTED_RECEIPT_AND_CONFIGURABLE_V3`, Issue #62), which found and
required correction of three further findings (P14-R3-F1 through F3, §11): an explicit,
canonical attempt/claim token binding claim ownership independently of any caller-controlled
timestamp, closing a same-timestamp/distinct-attempt race Round 2's own F2 did not yet guard
(F1); an independently, freshly re-observed receipt at Evidence hand-off -- never any of
`receipt.status`/`observations`/`adapter_identity`/`input_refs` -- closing a
forged-attestation gap Round 2's own F3 did not yet catch (F2); and a validated, offline,
zero-network V3 target configuration contract closing Round 2's own disclosed F4b gap for
real, replacing every hardcoded placeholder ref/SHA with values sourced from one
configuration object (F3). This round's own structural review found that Round 2's own
self-reported closure of F2 and F3 was premature -- both are corrected for real here, not
merely re-asserted.

It is further corrected by Structural Review Round 4
(`ADOPT_P14_R4_TERMINAL_CLAIM_ATTESTED_RECEIPT_AND_SOURCE_EDIT_FREE_V3`, Issue #62), which
found and required correction of three further findings (P14-R4-F1 through F3, §12): the
winning attempt's own `claim_token` is now carried on the terminal Projection Envelope itself
and checked on every subsequent reuse, so a distinct claim token reaching an already-terminal
mapping can no longer silently masquerade as the winning attempt merely because a matching
Envelope exists -- later, genuinely intended semantic reuse remains possible only as an
explicitly separate, disclosed operation (F1); Evidence hand-off now requires every one of a
receipt's own Evidence-relevant fields (`status`, `observations`, `adapter_identity`,
`input_refs`) to exactly equal the freshly, independently recomputed candidate, closing a gap
where Round 3's own fresh re-observation was correct but the receipt's own claimed fields were
never actually checked against it (F2); and the V3 harness's own real-adapter tests are now
gated by a fail-closed runtime check (`_v3_live_authorized`) requiring both a fully validated,
fully bound `V3TargetConfiguration` -- now itself binding `authorized_artifact_kinds`/
`authorized_artifact_count`/`cleanup_confirmed`/`no_merge_confirmed` as real fields, never
checked once and discarded -- and a wholly separate, independently-gated live-write-authority
input, replacing the unconditional `pytest.mark.skip` markers Round 3 left in place (F3). This
round's own structural review found that Round 3's own self-reported closure of F1 through F3
was again premature -- all three are corrected for real here.

Every section below reflects the corrected design; where a frozen decision from the original
delivery or from Round 1 was superseded rather than merely extended, this is stated explicitly
at the point of change.

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
    github_projection_grant_declaration_refs: list[Mapping[str, Any]],
    attempt_claim_token: str,
    subject_record: Mapping[str, Any] | None = None,
    subject_fingerprint: str | None = None,
    permit_semantic_reuse: bool = False,
) -> dict[str, Any]
    # {"envelope": ..., "receipt": GitHubObservationReceipt, "reused": bool, "same_attempt": bool}

route_observation_receipt_to_evidence(
    store,
    receipt: GitHubObservationReceipt,
    project_id: str,
    evidence_request: Mapping[str, Any],
    *,
    adapter: GitHubAdapter,
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
established. `github_projection_grant_declaration_refs` (Structural Review Round 2, P14-R2-F1)
is the caller's own explicit collection of `{"kind": "github_projection_grant_declaration",
"id": ...}` references, resolved the identical way -- a Store-resolved, self-consistent grant
alone no longer authorizes anything; it must additionally be anchored by a genuine,
Ed25519-signed declaration, independently re-verified against the real Project Binding's own
`human_authority_signing_key` (§10, F1). `subject_record` (Structural Review Round 1, P14-R1-F2)
is required for a
`difference`/`change` subject -- the real, canonical record body, independently
schema-validated and fingerprint-recomputed by this route -- and ignored for an
`observation_evidence` subject, which remains Store-resolved instead.
`attempt_claim_token` (Structural Review Round 3, P14-R3-F1) is a required, caller-supplied,
canonical-identity-shaped attempt token -- never `materialized_at`, which two genuinely
distinct callers may legitimately share -- included in both the `projection_intent` and
`projection_materialize_attempt` record content the Store's own same-key/different-content
rejection keys its concurrency barrier on (§10, F1), and now also carried on the terminal
Projection Envelope itself as `claim_token` (Structural Review Round 4, P14-R4-F1, §12).
`permit_semantic_reuse` (Structural Review Round 4, P14-R4-F1) governs only the case where the
mapping key already resolves to a terminally committed Envelope whose own `claim_token`
differs from this call's `attempt_claim_token`: left `False` (the default), such a call
refuses with `ProjectionTerminalClaimMismatchError` rather than silently masquerading as the
winning attempt; passing `True` explicitly requests the separate, disclosed "later semantic
reuse" operation instead, and the returned `"same_attempt"` key records whether this call was
the attempt that won the mapping slot.

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
  github_authority_ref, materialized_at, claim_token
                                  claim_token (Structural Review Round 4, P14-R4-F1) is the
                                  winning attempt's own attempt_claim_token -- deliberately
                                  excluded from projection_envelope_id/projection_envelope_
                                  semantic_fingerprint, since which attempt won is metadata
                                  about the Envelope, never part of what was projected
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

## 10. Structural Review Round 2 corrections (`ADOPT_P14_R2_SIGNED_AUTHORITY_ATOMIC_PROJECTION_AND_REAL_V3`)

**F1: a signed Human declaration now anchors every `github_projection_grant`.** §3 item 13's
own disclosed scope boundary -- `HUMAN_GRANT_DECLARATION_SIGNATURE_LAYER_FOR_GITHUB_PROJECTION_
GRANT=false` -- is now closed. A new Binding-owned record kind,
`github_projection_grant_declaration` (mirroring `human_grant_declaration`'s own shape, never
literally reusing it -- that schema's `grant_ref.kind` is hard-pinned to
`"verifier_selection_grant"`), carries an Ed25519 signature over its own restated fields
(`subject_ref`, `subject_fingerprint`, `projection_kind`, `target_repository`,
`payload_fingerprint`, `permitted_action`) plus `grant_ref`/`declared_by`/`status`/
`declared_at`. `evaluate_projection_authorization` now requires two new request keys,
`human_authority_signing_key` and `grant_declarations`, and stages five checks per candidate
grant before it can bind: the declaration must anchor this exact grant (`project_id` +
`grant_ref` match), be declared by the request's own `human_authority_ref`, be `ACTIVE`,
restate the grant's own semantic fields exactly, and carry a signature that independently
re-verifies against the real Project Binding's own `human_authority_signing_key` -- resolved
by the caller from `boot_context.project_binding["human_authority_signing_key"]`, never a
caller-supplied copy. A grant inserted directly into Store, self-consistent and correctly
`granted_by`-shaped, now authorizes zero adapter calls without a matching declaration. The
`github_projection_decision` record gains a `declaration_ref` field (mirroring `grant_ref`'s
null/non-null pattern), and `project_to_github` gains the required
`github_projection_grant_declaration_refs` parameter (§2).

**F2: an atomic, recoverable claim/attempt state machine closes the remaining
search-then-create race.** P14-R1-F4's own `find_by_correlation_key`-before-`materialize`
discipline still let two genuinely concurrent callers both observe "nothing found" and both
fall through to `materialize`. Two new Store record kinds, both keyed by the mapping key
itself and both committed through the identical `commit_state_transition` primitive the
Envelope itself uses -- `projection_intent` (committed before `find_by_correlation_key`) and
`projection_materialize_attempt` (committed before `materialize`) -- turn the Store's own
per-project commit serialization and same-key/different-content rejection
(`RecordConflictError`) into the entire concurrency barrier; this route adds no lock, queue,
or timeout of its own beyond a bounded Compare-And-Swap retry loop for genuinely unrelated
contention. A caller whose own claim collides with a different, already-durable claim refuses
immediately, before any adapter call, with `ProjectionConcurrentClaimError`. A caller that
already owns the claim but finds neither a discoverable external artifact nor an Envelope,
with an already-durable `projection_materialize_attempt` marker present, is in a genuinely
ambiguous state (materialize may have failed cleanly, or succeeded with its response lost) and
refuses with `ProjectionReconciliationRequiredError` rather than call `materialize` a second
time under the same claim. Separately, `RealGitHubAdapter.find_by_correlation_key` no longer
collapses every lookup failure (permission, rate limit, transport, outage) into `None`; it now
raises `ProjectionAdapterError`, so a failed lookup blocks new creation instead of being
silently treated as "not found."

**F3: `GitHubObservationReceipt` hand-off is now independently resolved against the real,
committed Envelope, and the external-artifact locator is now grammar-checked, not
prefix-checked.** P14-R1-F3's own `receipt.project_id == project_id` check compared a publicly
constructible dataclass's own field against itself -- a caller could copy a genuine receipt,
overwrite `project_id`, and pass the same value both places. `route_observation_receipt_to_
evidence` now takes a required `store` parameter (§2) and resolves `receipt.projection_envelope_
id` under the *requested* `project_id`'s own Store partition before trusting anything else on
the receipt; a receipt naming an envelope that was never actually committed under that project
resolves to nothing and refuses. `subject_ref`, `external_artifact_ref`, and
`github_authority_ref` are then cross-checked against the resolved Envelope's own real values,
never trusted as the receipt's own self-reported copies. Separately, `_require_external_
artifact_ref`'s own URL check previously verified only a literal string prefix
(`url.startswith("https://github.com/{owner}/{repo}/")`), which a URL naming a different
artifact id, a different artifact kind, or hiding its real target behind a query string,
fragment, or embedded userinfo could still satisfy. A new `_require_consistent_locator` (hand-
parsed with plain string operations -- never `urllib`, which this package's own static
conformance test reserves to `github_adapter.py` alone) now requires the URL's own host, path
owner/repo, kind segment (checked against a closed, per-`artifact_kind` set of real-GitHub and
this package's own fixture-adapter conventions), and id segment to all name the identical
artifact `artifact_kind`/`external_id` already claim, with zero query string, fragment, or
userinfo left unaccounted for.

**F4: the correlation-marker round-trip self-defeat is fixed; F4b's transport-level contract
fixtures are in place, but its V3 target-bound configuration is disclosed as not yet closed.**
`RealGitHubAdapter.materialize` embeds a hidden correlation marker in an Issue/PR's own `body`;
`observe` previously fingerprinted the *marker-carrying* body it read back, while `route.py`'s
own `_observe` always computes the *expected* fingerprint from the caller's committed payload,
which never carries the marker -- a successful, untampered real materialization was guaranteed
to observe as a mismatch. `RealGitHubAdapter._strip_correlation_marker` now removes the
adapter's own trailing marker block (matched by template shape, not by a specific key, since
`observe` is never told which key a given artifact carries) from the observed `body` before
computing `observed_content_fingerprint`, restoring the one canonical write/read observable
transformation both sides must agree on -- genuine content tampering in `title`/`body` prose
remains fully detectable, since only the marker block itself is ever stripped. Separately, a new
`tests/unit/projection/test_real_github_adapter_transport.py` proves this same round-trip, the
`_classify_error` mapping across the full real GitHub HTTP status space, and
`find_by_correlation_key`'s fail-closed behavior, entirely against offline transport fixtures
that reproduce real GitHub API response shapes (F4b's own transport-fixture half). F4b's other
half -- replacing `test_v3_real_github_vertical_proof.py`'s own placeholder `head_ref=
"agent/v3-harness"` / `head_sha="a"*40` with real target-bound inputs -- is **not** addressed by
this round: `V3_LIVE_EXTERNAL_WRITE_AUTHORITY=false` still holds, no exact target repository has
been separately frozen and re-confirmed for this harness, and no such ref can be genuine without
one. This is disclosed as an open item rather than silently narrowed; closing it is contingent on
that boundary being frozen in a future adoption, not on any remaining code change here.

```text
P14_R2_F1_CLOSED=true
P14_R2_F2_CLOSED=true
P14_R2_F3_CLOSED=true
P14_R2_F3b_CLOSED=true
P14_R2_F4_CLOSED=true
P14_R2_F4b_TRANSPORT_FIXTURES_CLOSED=true
P14_R2_F4b_V3_TARGET_CONFIG_CLOSED=false
```

```text
P14_R1_F1_CLOSED=false
P14_R1_F2_MATERIALLY_IMPROVED=true
P14_R1_F3_CLOSED=false
P14_R1_F4_CLOSED=false
P14_R1_F5_CLOSED=false
P14_R1_F6_MATERIALLY_IMPROVED=true
P14_R1_F7_CLOSED=true
```

(`P14_R1_F1`, re-addressed as this section's own F1; `P14_R1_F3`, re-addressed as F3 plus its
own locator-grammar sub-requirement; `P14_R1_F4`, re-addressed as F2; `P14_R1_F5`, re-addressed
as F4 -- all now closed at the head this correction lands at. `P14_R1_F2`/`P14_R1_F6` remain
materially improved, not regressed. `P14_R1_F7` remains closed.)

## 11. Structural Review Round 3 corrections (`ADOPT_P14_R3_UNIQUE_CLAIM_ATTESTED_RECEIPT_AND_CONFIGURABLE_V3`)

**F1: claim ownership is now an explicit token, never inferred from a caller-controlled
timestamp.** §10's own F2 closed the search-then-create race using `materialized_at` as (part
of) the durable claim record's own content -- but `materialized_at` is a caller-supplied
instant, never a uniqueness primitive, and two genuinely distinct concurrent callers could
legitimately supply the identical value, making both look like the same caller's own
idempotent retry and letting both reach `materialize`. `project_to_github` now requires a
second, explicit `attempt_claim_token` (§2) on every call, included in both the
`projection_intent` and `projection_materialize_attempt` record content the same
same-key/different-content rejection already keys its concurrency barrier on: two attempts
sharing a timestamp but carrying distinct tokens now produce genuinely different record
content, so only whichever commit the Store's single per-project lock admits first ever
proceeds, and the other refuses via `ProjectionConcurrentClaimError` before any adapter call.
A genuine retry of the identical attempt must present the identical token again. Both new
schemas (`projection_intent.schema.json`, `projection_materialize_attempt.schema.json`) gain
a required `claim_token` field.

**F2: the observation receipt handed to Evidence is now independently, freshly
re-observed -- never trusted from the receipt object itself.** §10's own F3 resolved the
receipt's claimed Envelope and cross-checked `subject_ref`/`external_artifact_ref`/
`github_authority_ref` against it, closing cross-project relabeling -- but
`GitHubObservationReceipt` remains a publicly constructible dataclass, so a caller could copy
every one of those Envelope-bound fields from a genuine receipt while forging its own
`status`, `observations`, `adapter_identity`, or `input_refs`, and `route_observation_
receipt_to_evidence` would still copy the forged `status` straight into Evidence's own
`verification_result_provenance`. `route_observation_receipt_to_evidence` now takes a
required `adapter` parameter (§2) and, once the real Envelope resolves, independently
re-observes through it -- via the identical `observe_and_classify` body
(`projection/observable.py`) `route.py`'s own materialization-time `_observe` now also calls,
so both call sites share one classification owner rather than two that could drift. Every
field of `verification_result_provenance` this handoff constructs comes from the real,
resolved Envelope and this fresh re-observation alone; none of `receipt.status`,
`receipt.observations`, `receipt.adapter_identity`, or `receipt.input_refs` is ever read.
A forged claim in any of those four fields therefore has no path to affect the outcome at
all, closing every variant of the finding at once rather than patching each field
individually.

**F3: the V3 harness now sources every real-adapter value from one validated, offline
configuration contract -- never a hardcoded, impossible placeholder.** §10's own F4b left
`test_v3_real_github_vertical_proof.py`'s `head_ref="agent/v3-harness"`, `base_ref="main"`,
and `head_sha="a" * 40` hardcoded, disclosed as not yet closed. A new module,
`tests/fixtures/v3_target_configuration.py`, defines `V3TargetConfiguration` and
`load_v3_target_configuration` -- reading eight environment variables (exact target
repository, GitHub token, the Change projection's own existing head/base refs, the Evidence
projection's own real commit SHA, an artifact naming prefix, and explicit `"true"`-literal
cleanup/no-merge confirmations), validating every one of them with plain string/regex
grammar checks and zero network access, and returning `None` only when every variable is
unset (the genuinely safe default every CI/local environment in this delivery has) -- any
*partial* configuration, or any single malformed value, raises `V3ConfigurationError` before
any network call could ever occur. The three real-adapter tests now build every payload field
from this one validated configuration object instead of a literal; `V3_LIVE_EXTERNAL_WRITE_
AUTHORITY=false` still gates all three behind an unconditional `pytest.mark.skip`, unchanged
by this correction -- only the *configuration*, never the live-write authorization, is what
this finding required closed. Three additional tests
(`test_v3_configured_real_adapter_projects_*`) prove the identical `_run_vertical_proof`
harness body executes to completion, for all three projection kinds, over a real
`RealGitHubAdapter` and a synthetic-but-validated `V3TargetConfiguration`, with
`urllib.request.urlopen` monkeypatched to canned GitHub-shaped responses -- mechanically
executable, with zero live network access, never merely asserted.

```text
P14_R3_F1_CLOSED=true
P14_R3_F2_CLOSED=true
P14_R3_F3_CLOSED=true
```

```text
P14_R2_F2_CLOSED=true
P14_R2_F3_CLOSED=true
P14_R2_F4b_V3_TARGET_CONFIG_CLOSED=true
```

(§10's own status block above records `P14_R2_F2_CLOSED=true`/`P14_R2_F3_CLOSED=true` -- that
self-assessment was mistaken: Structural Review Round 3 found genuine, reproduced
counterexamples in both (the identical-timestamp/distinct-token race F2's own implementation
did not yet guard, and the forged-status/forged-observations receipt F3's own Envelope-only
corroboration did not yet catch), corrected here as this section's own F1/F2, and the record
above is left unedited as an honest account of what Round 2 believed at the time rather than
silently rewritten to agree with this correction. `P14_R2_F4b_V3_TARGET_CONFIG_CLOSED=false`,
disclosed open at the end of §10, is closed for real by this section's own F3.)

## 12. Structural Review Round 4 corrections (`ADOPT_P14_R4_TERMINAL_CLAIM_ATTESTED_RECEIPT_AND_SOURCE_EDIT_FREE_V3`)

**F1: the winning attempt's own claim token is now carried on the terminal Envelope and
checked on every reuse -- a distinct token can no longer masquerade as the winning attempt.**
§11's own F1 bound `claim_token` into the `projection_intent`/`projection_materialize_attempt`
records, but not into the terminal Envelope itself: a request whose mapping key already
resolved to a committed Envelope returned it unconditionally, regardless of which
`attempt_claim_token` the caller presented, so a distinct caller reaching an already-terminal
projection was treated identically to the attempt that actually won it -- the terminal record
could not attest which attempt owned it. `projection_envelope.schema.json` gains a required
`claim_token` field; `derive_projection_envelope` (`engine.py`) takes and includes it,
deliberately excluded from `MAPPING_KEY_FIELDS`/`SEMANTIC_FIELDS` (`identity.py`) since which
attempt won is metadata about the Envelope, never part of what was projected. `project_to_
github`'s own existing-Envelope reuse path now compares the committed Envelope's own
`claim_token` against the caller's `attempt_claim_token`: an exact match is a genuine
same-attempt retry, proceeding exactly as before with `"same_attempt": True`; a mismatch
refuses with the new `ProjectionTerminalClaimMismatchError` unless the caller explicitly
passes the new `permit_semantic_reuse=True` keyword (§2), in which case the existing Envelope
is still returned and freshly re-observed, but `"same_attempt": False` discloses that this
call was not the winning attempt. Later, genuinely intended semantic reuse of an
already-completed projection remains possible -- but only as this explicitly separate,
disclosed operation, never silently conflated with same-attempt retry.

**F2: Evidence hand-off now requires every one of a receipt's own claimed fields to exactly
equal the freshly, independently recomputed candidate -- a fresh re-observation alone is not
itself an attestation of the receipt.** §11's own F2 made `route_observation_receipt_to_
evidence` independently re-observe through the exact authorized adapter, but it then
constructed `verification_result_provenance` entirely from that fresh result, never reading
`receipt.status`/`observations`/`adapter_identity`/`input_refs` at all -- so a publicly
constructed receipt with any one of those fields forged could still yield `VERIFIED` Evidence
whenever the artifact currently happened to match, using the receipt only as an unverified
locator. `route_observation_receipt_to_evidence` now additionally requires, before deriving
any Evidence: `receipt.status == classified["status"]`; `dict(receipt.observations) ==` the
freshly recomputed `{observation_outcome, exists, observed_content_fingerprint, observed_at}`
(covering outcome, fingerprint, and timestamp together); `dict(receipt.adapter_identity) ==
dict(adapter.adapter_identity)`; and `receipt.input_refs ==` the expected `(subject_ref,)`
tuple derived from the real Envelope. A single forged field, even with every other field
(including the fresh re-observation itself) genuine, refuses with `ProjectionRequirementError`
before `derive_evidence` is ever called.

**F3: the V3 harness's own real-adapter tests are now gated by a fail-closed runtime check
requiring both a fully bound configuration and a wholly separate live-write-authority input --
no source edit activates them.** §11's own F3 built `V3TargetConfiguration`/`load_v3_target_
configuration`, but the three real-adapter tests remained decorated with an unconditional
`pytest.mark.skip`, and the configuration itself validated `cleanup`/`no-merge` confirmations
and discarded them rather than binding them as real fields, with no `artifact_kinds`/
`artifact_count` boundary at all. `tests/fixtures/v3_target_configuration.py` now: (a) binds
`cleanup_confirmed`, `no_merge_confirmed`, `authorized_artifact_kinds` (a non-empty subset of
the real `ARTIFACT_KINDS` vocabulary, from a new comma-separated `MANOSUBE_P14_V3_AUTHORIZED_
ARTIFACT_KINDS` variable), and `authorized_artifact_count` (a positive integer, from `MANOSUBE_
P14_V3_AUTHORIZED_ARTIFACT_COUNT`) as real `V3TargetConfiguration` fields, never checked-then-
discarded; (b) adds `v3_live_write_authorized`, reading one dedicated, deliberately separate
environment variable (`MANOSUBE_P14_V3_LIVE_WRITE_AUTHORIZED`) not among `ALL_V3_ENV_VARS`, so
configuration validity and live-write authority remain two independently-gated inputs -- a
fully valid, fully bound configuration alone still never authorizes a live call. The three
real-adapter tests in `test_v3_real_github_vertical_proof.py` now carry `@pytest.mark.skipif
(not _v3_live_authorized(), ...)` in place of the unconditional skip, where `_v3_live_
authorized()` requires both `load_v3_target_configuration() is not None` and `v3_live_write_
authorized()`; each also calls a new `_require_authorized_artifact_kind` binding its own
`projection_kind`'s real `artifact_kind` against the frozen configuration's own `authorized_
artifact_kinds` before ever constructing a `RealGitHubAdapter` call. Once a later round
supplies both inputs via the environment, these tests activate with no edit to this file or
the configuration module. All of this remains entirely offline (no `urllib` import, no
network access in either module) and, in this delivery's own environment, both gates evaluate
`False` -- `test_v3_authorization_is_not_yet_configured_in_this_environment` asserts all four
combinations (`_v3_authorized()`, `load_v3_target_configuration()`, `v3_live_write_
authorized()`, `_v3_live_authorized()`) explicitly.

```text
P14_R4_F1_CLOSED=true
P14_R4_F2_CLOSED=true
P14_R4_F3_CLOSED=true
```

```text
P14_R3_F1_CLOSED=true
P14_R3_F2_CLOSED=true
P14_R3_F3_CLOSED=true
```

(§11's own status block above records all three as `true` -- that self-assessment was again
mistaken: Structural Review Round 4 found genuine, reproduced counterexamples in all three
(the terminal Envelope's own missing claim-token binding for F1; the never-read receipt fields
for F2; the unconditional skip and the discarded cleanup/no-merge/artifact-kind/count fields
for F3), corrected here as this section's own F1/F2/F3, and the record above is left unedited
as an honest account of what Round 3 believed at the time rather than silently rewritten to
agree with this correction.)
