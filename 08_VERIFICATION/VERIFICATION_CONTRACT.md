# Independent Verification Contract (Phase 13, Issue #51)

```text
DOC_TYPE=VERIFICATION_CONTRACT
DOCUMENT_ID=VERIFICATION-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=INDEPENDENT_EVIDENCE_ADAPTER
PREDECESSOR_ISSUE=#49
PREDECESSOR_PR=#50
PREDECESSOR_MERGE_COMMIT=36b06d88cf779d9f04b79e41022b42d1f3d47510
```

See `VERIFICATION_INDEX.md` for this contract set's own position and reading order.

## 1. Position

This layer adds exactly one provider-neutral, explicit Independent Verification adapter:
an explicit verification requirement, a SHUKOU-authorized verifier selection, an immutable
verification boundary, and an independently produced verification result -- routed to the
existing Evidence owner, the existing evidence-sufficiency/completion owner, and the
existing Difference/Reflow owner, none of which this layer duplicates.

```text
INDEPENDENT_VERIFICATION_OWNER_COUNT=1
PUBLIC_VERIFICATION_ENTRY_POINT_COUNT=1
```

## 2. Public signature

```python
run_independent_verification(
    store,
    *,
    project_id: str,
    project_binding_id: str,
    verification_requirement: VerificationRequirement,
    verifier_selection: VerifierSelection,
    verifier_selection_grant_refs: Sequence[Mapping[str, Any]],
    verifier: IndependentVerifier,
) -> VerificationResult

route_verification_result_to_evidence(
    verification_result: VerificationResult,
    evidence_request: Mapping[str, Any],
) -> dict[str, Any]
```

`project_binding_id` (Structural Review Round 1, P13-R1-F2) is passed to the existing Boot
owner's own public `boot_project` to independently re-verify the real Human Authority
reference this project is bound to, rather than trusting a caller-supplied equality check
alone.

`verifier_selection_grant_refs` (Structural Review Round 3, P13-R3-F1; resolved from the
Store since Structural Review Round 4, P13-R4) is the caller's own explicit collection of
`{"kind": "verifier_selection_grant", "id": ...}` references -- never grant *content*. Round
3 originally accepted the grant bodies themselves as a caller-supplied argument; Round 4
(Authority Provenance Bypass, P13-R3-F2) closes the gap that left open: a `human_authority_ref`
is not a secret, so a caller able to supply arbitrary in-memory content could self-hash a
grant whose `granted_by` merely repeats the real, Boot-verified reference. Each supplied ref
is now resolved through the existing Store's own read-only `resolve_record` -- the identical
call site `observation_evidence` targets already resolve through -- before its body is ever
considered; an unresolvable ref refuses before the verifier is ever called. Only the
resulting, genuinely Store-committed, real, Human-Authority-declared, content-addressed
bodies are passed, together with `verifier_selection`'s own fields and the real,
Boot-verified Human Authority reference, to the existing Authority owner's own dedicated,
read-only `evaluate_verifier_selection` exactly once, and this route requires it to answer
`VERIFIER_SELECTION_SELECTED` before the verifier is ever called.

`route_verification_result_to_evidence` (Structural Review Round 2, P13-R2-F2) hands an
admissible `VerificationResult` to the existing Evidence owner's own public `derive_evidence`
via a caller-supplied, already-real, Change-free `evidence_request` grounded in the
`verification_observation_request` position (`evidence/engine.py`'s Change-Free Verification
Evidence). It calls `derive_evidence` exactly once, cross-validates the resulting record
against `verification_result`, and returns the resulting canonical Evidence record. It raises
`EvidenceHandoffError` for its own two boundaries (Change-freedom, and that the derived record
is actually about `verification_result`); every `EvidenceError` the existing Evidence owner
itself raises propagates unchanged.

```text
VerificationRequirement
  requirement_id, project_id
  target_refs                  explicit {"kind", "id"} references -- difference / change /
                                 observation_evidence only
  verification_boundary        immutable, explicit
  required_conditions          immutable, explicit; read and passed through, never
                                 interpreted by this route
  selection_authority_ref      the Human Authority this requirement is bound to

VerifierSelection
  selection_id, project_id, requirement_id
  status                        ACTIVE | REVOKED | EXPIRED -- SHUKOU-declared, never
                                 clock-derived (no evaluation_instant parameter exists on
                                 this route for a clock comparison to use)
  selection_authority_ref      must canonical-reference-equal the requirement's own
  verifier_identity             provider-neutral identity/capability, passed through
                                 unmodified into the result
  permitted_boundary           must canonical-reference-equal the requirement's own
                                 verification_boundary

VerificationResult
  status                        VERIFIED | FAILED | INSUFFICIENT | UNAVAILABLE
  requirement_id, selection_id, project_id
  target_refs, verifier_identity, selection_authority_ref, verification_boundary
                                 (all carried through from the requirement/selection)
  input_refs                    what the verifier actually examined; explicit
  observations                  the verifier's own attestation candidate payload; explicit,
                                 never interpreted by this route

IndependentVerifier
  a callable: (*, requirement, selection) -> Mapping[str, Any]
  returns {"status", "input_refs", "observations"}; called exactly once
```

## 3. Frozen semantic decisions

1. **Verification only when required.** `run_independent_verification` is never invoked as
   a blanket rule -- it is called only when a caller holds an explicit
   `VerificationRequirement`, itself derived from an existing Difference risk/Authority
   condition or specified directly by SHUKOU.
2. **Implementer is not Closure Authority.** This layer produces no closure decision of any
   kind; a `VerificationResult` never substitutes for, weakens, or bypasses existing
   Evidence-sufficiency or Closure Policy semantics. Implementation success, self-review, CI
   success, bot output, and AI review are not treated as verification by this layer -- they
   are not a `VerifierSelection` this route ever constructs or infers.
3. **No fixed verifier.** `IndependentVerifier` is a provider-neutral protocol: a
   deterministic test runner, a schema validator, a runtime observer, a distinct AI, or a
   Human review may all implement it identically. No product, model, provider, or bot is
   selected by this package.
4. **SHUKOU selects explicitly, and the existing Authority owner re-verifies the selection
   itself.** `VerifierSelection` is always caller-supplied. Its `selection_authority_ref`
   must canonical-reference-equal the requirement's own, and its `permitted_boundary` must
   canonical-reference-equal the requirement's own `verification_boundary` -- a selection
   bound to a different authority or boundary is rejected before the verifier is ever called.
   No automatic selection, fallback, cwd/environment/cache inference, or "only available
   reviewer" rule exists. Structural Review Round 3 (P13-R3-F1) resolves the further gap
   Round 2 disclosed: the real, Boot-verified Human Authority reference alone does not prove
   SHUKOU selected *this* `VerifierSelection` for *this* `VerificationRequirement` -- only the
   existing Authority owner's own `evaluate_verifier_selection`, re-verifying a real,
   Human-Authority-declared `verifier_selection_grant` that binds every one of project_id,
   requirement_id, verifier_identity, permitted_boundary, selection status, and the real
   selection authority identity together, can. Structural Review Round 4 (P13-R4) resolves
   the gap Round 3 itself left open: a grant's own content -- `granted_by` included -- is not
   a secret a caller lacks, so accepting grant *content* directly as an argument let a caller
   self-hash one that merely repeats known-real values. This route now accepts only
   `{"kind": "verifier_selection_grant", "id": ...}` references, resolves each through the
   existing Store's own `resolve_record` before its body is ever considered, and offers only
   the resulting, genuinely Store-committed bodies to `evaluate_verifier_selection` -- a ref
   naming a record the Store does not durably resolve refuses before the verifier is ever
   called, exactly as an unresolvable `observation_evidence` target already does. See §10.
5. **Independence is provenance plus boundary, for every status alike.** A
   `VerificationResult` carries target refs, frozen boundary, verifier identity, selection
   authority ref, input refs, and result. A verifier whose own `input_refs` cite nothing
   beyond the requirement's own `target_refs` has produced no independent input at all --
   implementation-indistinguishable provenance does not satisfy an independent verification
   requirement, and this route refuses it (`VerifierOutputError`). Structural Review Round 2
   (P13-R2-F3) supersedes Round 0's disclosed `UNAVAILABLE` exemption: `UNAVAILABLE` is not
   exempt from this obligation either -- a verifier asserting it could not evaluate must still
   cite the explicit boundary/capability/observation/Evidence input that actually grounds why
   it could not, so an unconstructible `UNAVAILABLE` with no such grounding is rejected the
   same as any other status with implementation-indistinguishable provenance.
6. **Verifier never persists canonical Evidence directly, but a real handoff connects an
   admissible result to the existing Evidence owner.** `IndependentVerifier` returns an
   immutable result/attestation-candidate payload; this package never writes canonical
   Evidence itself, never operates the Store's transaction manifest, recovery, or
   current-view reconstruction, and invents no second Evidence owner
   (`NEW_EVIDENCE_OWNER=false`). Structural Review Round 2 (P13-R2-F2) supersedes Round 0's
   "the caller's own, separate concern" stance: `route_verification_result_to_evidence` is
   the real connection -- it calls the existing Evidence owner's own public `derive_evidence`
   exactly once over a caller-supplied, already-real, Change-free `evidence_request`, and
   cross-validates the resulting record against the `VerificationResult` it is about. Existing
   Evidence ownership remains the only canonical persistence path, and the existing
   evidence-sufficiency/completion owner and the existing Difference/Reflow owner remain the
   only surfaces that decide sufficiency or closure from the resulting record
   (`EXISTING_EVIDENCE_OWNER_HANDOFF_REQUIRED=true`,
   `VERIFIER_DIRECT_STORE_WRITE=false`,
   `INDEPENDENT_VERIFICATION_DIRECT_STORE_COMMIT=false`).
7. **Verification result is not Closure.** `VERIFIED` is only a result for the stated
   requirement. It is not an Authority Decision, Evidence record, Closure receipt, State
   transition, Merge approval, or execution permission -- `VerificationResult` has no method
   or field that could make it any of those.
8. **Failure is fail-closed.** `FAILED`, `INSUFFICIENT`, `UNAVAILABLE`, a wrong project, a
   selection that does not apply to the supplied requirement, a selection whose own
   authority or boundary diverges, an inactive selection, a malformed or out-of-vocabulary
   target reference, an unresolvable Store-owned target, or implementation-indistinguishable
   verifier provenance -- none of these ever produces a `VerificationResult` with `status`
   substituted, narrowed, or silently accepted; every one of them raises before a
   `VerificationResult` is constructed, except the four real outcome statuses themselves
   (`VERIFIED`/`FAILED`/`INSUFFICIENT`/`UNAVAILABLE`), which the caller's own verifier
   determines and this route never overrides.
9. **All inputs are explicit and frozen.** No Project discovery, filesystem scan,
   network/GitHub read, automatic Agent creation, or hidden environment input is permitted.
   This route reads no clock: `VerifierSelection.status` (`ACTIVE`/`REVOKED`/`EXPIRED`) is a
   SHUKOU-declared field, never derived from comparing a timestamp to the current instant.
10. **External bot output remains unverified.** This layer does not activate or justify
    Codex automated review. Bot findings and CI annotations remain unverified external
    observation until SHUKOU explicitly adopts a `VerificationRequirement` and
    `VerifierSelection`, and existing Evidence ownership records an admissible result
    derived from a real `VerificationResult`.
11. **No hidden execution capability.** No model call, prompt execution, shell, subprocess,
    network, URL read, GitHub operation, runtime observation, scheduler, background loop, or
    Agent-to-Agent messaging is implemented here. `IndependentVerifier` is a plain Python
    callable this route invokes synchronously and exactly once; an explicitly supplied
    verifier capability or Human-provided attestation is merely normalized into a
    `VerificationResult`, never executed by this package itself.
12. **Strict phase boundary.** GitHub is Phase 14; Runtime Observation 15; Multi-model 16;
    URL Read-only 17; Autonomous Change 18; Multi-Agent 19 remain out of scope.

## 4. Canonical owner

```text
src/manosube_agent_civilization/independent_verification/
├── __init__.py         public exports
├── errors.py            IndependentVerificationError / VerificationRequirementError /
│                         VerifierOutputError / VerificationValueError /
│                         EvidenceHandoffError
├── types.py              VerificationRequirement / VerifierSelection / VerificationResult /
│                         IndependentVerifier
├── route.py              run_independent_verification
└── evidence_handoff.py   route_verification_result_to_evidence
```

`VerificationRequirementError`, `VerifierOutputError`, and `VerificationValueError` exist
only for the admission boundaries this layer itself owns (requirement/selection/boundary/
target admission; the shape of what an explicit verifier returns; deep-freeze admission of a
supplied value). `VerificationRequirementError` is also what this route raises when the
existing Authority owner's own `evaluate_verifier_selection` does not answer
`VERIFIER_SELECTION_SELECTED` (Structural Review Round 3, P13-R3-F1) -- a readable-but-refused
decision, not an exception the Authority owner itself raises. `EvidenceHandoffError`
(Structural Review Round 2, P13-R2-F2) exists only for `evidence_handoff.py`'s own two
boundaries (Change-freedom of the supplied `evidence_request`; that the derived Evidence
record is actually about the supplied `VerificationResult`). Every other failure mode -- a
caller-supplied `store` that itself raises a typed Store error from `resolve_record`, the
existing Boot owner's own `boot_project` failure, the existing Authority owner's own
`evaluate_verifier_selection` failure for an unreadable request (an `AuthorityError`), or the
existing Evidence owner's own `derive_evidence` failure -- propagates unchanged; this layer
never catches or reclassifies any of them.

## 5. Canonical route

```text
1. Validate project_id and project_binding_id are each an explicit canonical identity
   (never a path/URL/locator).
2. Validate verification_requirement.project_id and verifier_selection.project_id both
   equal project_id.
3. Validate verifier_selection.requirement_id equals verification_requirement.requirement_id.
4. Validate verifier_selection.status is ACTIVE (REVOKED/EXPIRED/unrecognized all refuse).
5. Call the existing Boot owner's own public boot_project(store, project_id=project_id,
   project_binding_id=project_binding_id) exactly once (Structural Review Round 1,
   P13-R1-F2) and require both verification_requirement.selection_authority_ref and
   verifier_selection.selection_authority_ref to canonical-reference-equal the real,
   independently re-verified BootContext.human_authority_ref that call returns -- never
   merely each other. Every Boot/Binding/Store failure boot_project itself raises
   propagates unchanged.
6. Validate verifier_selection.permitted_boundary canonical-reference-equals
   verification_requirement.verification_boundary.
7. Validate each entry of verifier_selection_grant_refs is an explicit {"kind": "verifier_
   selection_grant", "id": ...} reference and resolve it through store.resolve_record
   (project_id, "verifier_selection_grant", id) (Structural Review Round 4, P13-R4) -- an
   unresolvable ref refuses before the Authority owner or the verifier is ever called; grant
   content is never accepted as a caller-supplied argument.
8. Call the existing Authority owner's own public evaluate_verifier_selection(...) exactly
   once (Structural Review Round 3, P13-R3-F1), over project_id, verification_requirement.
   requirement_id, verifier_selection.selection_id/verifier_identity/permitted_boundary/
   status, the real Boot-verified Human Authority reference from step 5, and the bodies
   resolved in step 7. Require the returned decision to be VERIFIER_SELECTION_SELECTED; any
   other decision refuses before the verifier is ever called. Every AuthorityError this call
   itself raises for an unreadable request propagates unchanged.
9. Validate verification_requirement.target_refs is non-empty, and each entry is an
   explicit {"kind", "id"} reference whose kind is difference/change/observation_evidence.
   Every observation_evidence target is resolved through the identical store.resolve_record
   call site step 7 already uses -- an unresolvable one refuses before the verifier is called.
10. Validate the supplied verifier itself declares, on its own verifier_identity attribute,
   the identical identity canonical-reference-equal to verifier_selection.verifier_identity
   (Structural Review Round 1, P13-R1-F1) -- checked before the verifier is ever called.
10. Call verifier(requirement=verification_requirement, selection=verifier_selection)
    exactly once. Zero Store writes occur, in this route or in the verifier call itself
    (the verifier is a plain Python callable this route never grants Store access to).
11. Validate the verifier's own return value: status in {VERIFIED, FAILED, INSUFFICIENT,
    UNAVAILABLE}; input_refs a non-empty list of explicit {"kind", "id"} references that is
    not a subset of target_refs, for every status alike including UNAVAILABLE (Structural
    Review Round 2, P13-R2-F3 -- no exemption); observations an explicit mapping.
12. Return one immutable VerificationResult carrying every field above, deep-frozen.
```

## 6. Required rejection proofs

At minimum, this layer fails closed, with zero Store mutation
(`STATE_TRANSITION_COUNT_DELTA=0`, `RECORD_COUNT_DELTA=0`, `EXTERNAL_OPERATION_COUNT_DELTA=0`)
and no `VerificationResult` produced, and the supplied `verifier` never called, for:

```text
- a project_id or project_binding_id that is a path/URL/locator rather than a plain identity
- verification_requirement.project_id or verifier_selection.project_id not matching the
  requested project_id
- a verifier_selection whose requirement_id does not name the supplied requirement
- a verifier_selection whose status is REVOKED, EXPIRED, or any unrecognized value
- any Boot/Binding/Store failure the existing Boot owner's own boot_project raises for
  project_id/project_binding_id (propagates unchanged -- Structural Review Round 1,
  P13-R1-F2)
- a verification_requirement.selection_authority_ref or verifier_selection.
  selection_authority_ref that diverges from the real, Boot-verified Human Authority
  reference (not merely from each other -- Structural Review Round 1, P13-R1-F2)
- a verifier_selection whose permitted_boundary diverges from the requirement's own
  verification_boundary
- a verifier_selection_grant_refs entry that is not an explicit {"kind": "verifier_selection_
  grant", "id": ...} reference, or whose kind is anything else -- grant content itself is
  never an accepted argument shape (Structural Review Round 4, P13-R4)
- a verifier_selection_grant_refs entry naming a record the Store does not durably resolve
  for this project (Structural Review Round 4, P13-R4 -- the identical failure shape an
  unresolvable observation_evidence target already produces)
- verifier_selection_grant_refs that resolve to no genuine, Human-Authority-declared grant
  binding every one of project_id, requirement_id, verifier_identity, permitted_boundary,
  selection status, and the real, Boot-verified selection authority identity together --
  including no refs at all, a resolved grant naming a different selection, and a resolved
  grant declared by a fabricated or different Human Authority (Structural Review Round 3,
  P13-R3-F1, refs resolved per Round 4; the existing Authority owner's own
  evaluate_verifier_selection answers anything but VERIFIER_SELECTION_SELECTED)
- any AuthorityError the existing Authority owner's own evaluate_verifier_selection itself
  raises for an unreadable resolved-grant body (propagates unchanged -- Structural Review
  Round 3, P13-R3-F1)
- an empty target_refs, a target reference missing kind/id, or a target reference whose
  kind is outside {difference, change, observation_evidence}
- an observation_evidence target reference the Store does not resolve for this project
- a verifier whose own verifier_identity attribute is missing, unreadable, or diverges from
  verifier_selection.verifier_identity (Structural Review Round 1, P13-R1-F1)
```

And, once the verifier has been called (the one point past which this route's own
admission gate has already passed and Store mutation remains zero throughout):

```text
- a non-mapping verifier return value
- an unrecognized status
- a non-list input_refs, or an input_refs entry missing kind/id
- a non-mapping observations payload
- an empty input_refs, or an input_refs set that is a subset of target_refs --
  implementation-indistinguishable provenance, for every status alike including
  `UNAVAILABLE` (Structural Review Round 2, P13-R2-F3 -- superseding Round 0's disclosed
  `UNAVAILABLE` exemption)
```

And, for `route_verification_result_to_evidence` (Structural Review Round 2, P13-R2-F2), with
zero calls to `derive_evidence` and no Evidence record produced or returned:

```text
- a verification_result argument that is not a VerificationResult instance
- an evidence_request argument that is not an explicit mapping
- an evidence_request carrying a change_request (Independent Verification never executes or
  grounds a Change)
- an evidence_request carrying a post_change_observation_request
- an evidence_request with no verification_observation_request -- the one Evidence position
  this handoff produces
```

And, once `derive_evidence` has been called and returned a genuine canonical Evidence record
(the one point past which the existing Evidence owner's own admission gate has already
passed):

```text
- a derived Evidence record whose target.project_id does not match verification_result's own
- a derived Evidence record bound to a Difference verification_result never named in its own
  target_refs
```

Static conformance additionally proves: exactly two public callables
(`run_independent_verification`, `route_verification_result_to_evidence`) and exactly one
lifecycle-free result type (`VerificationResult`); that no module in this package ever
imports `difference`, `reflow`, or `binding`; that `evidence` is importable only from
`evidence_handoff.py` (Structural Review Round 2, P13-R2-F2) and only to call
`derive_evidence` exactly once; that `authority` is importable only from `route.py`
(Structural Review Round 3, P13-R3-F1) and only to call `evaluate_verifier_selection` exactly
once; that `store.resolve_record` is the only Store method this package ever calls, called
from exactly one call site (Structural Review Round 4, P13-R4: shared by both
`observation_evidence` target resolution and `verifier_selection_grant` resolution) and once
per resolved reference; and that no module in this package imports a model, subprocess,
shell, network, GitHub, Observer, Change-execution, scheduler, or multi-Agent surface.

## 7. Explicit non-claims

```text
MODEL_PROVIDER_IMPLEMENTED=false
PROMPT_EXECUTION_IMPLEMENTED=false
SUBPROCESS_VERIFIER_IMPLEMENTED=false
CI_ADAPTER_IMPLEMENTED=false
GITHUB_ADAPTER_IMPLEMENTED=false
NETWORK_ACCESS_IMPLEMENTED=false
URL_READ_IMPLEMENTED=false
RUNTIME_OBSERVER_IMPLEMENTED=false
SCHEDULER_IMPLEMENTED=false
BACKGROUND_VERIFIER_IMPLEMENTED=false
AUTOMATIC_VERIFIER_SELECTION=false
AUTOMATIC_CLOSURE_IMPLEMENTED=false
AUTONOMOUS_CHANGE_IMPLEMENTED=false
MULTI_AGENT_IMPLEMENTED=false
NEW_STATE_OWNER=false
NEW_EVIDENCE_OWNER=false
NEW_AUTHORITY_OWNER=false
NEW_STORE_OWNER=false
VERIFIER_DIRECT_STORE_WRITE=false
INDEPENDENT_VERIFICATION_DIRECT_STORE_COMMIT=false
EXISTING_EVIDENCE_OWNER_HANDOFF_REQUIRED=true
NEW_SELECTION_REGISTRY=false
NEW_SELECTION_TOKEN=false
NEW_SELECTION_CACHE=false
FAKE_DIFFERENCE_OR_STATE_FOR_AUTHORITY=false
CALLER_MAPPING_EQUALITY_AS_AUTHORITY=false
BOOT_HUMAN_AUTHORITY_REF_ALONE_IS_SELECTION_DECISION=false
CALLER_ASSERTED_GRANT_CONTENT_AS_PROVENANCE=false
PARALLEL_OR_HIDDEN_AUTHORITY_OWNER=false
```

## 8. Failed verification is now actually connected to existing ownership, not merely representable

A `FAILED`/`INSUFFICIENT`/`UNAVAILABLE`/`VERIFIED` `VerificationResult` is no longer only
"theoretically representable" in existing Difference/Reflow semantics -- Structural Review
Round 2 (P13-R2-F2) implements the real connection. Reflow's own terminal-cause binding
(`evidence/engine.py`'s `resolve_terminal_reason_evidence`, consumed by `reflow/closure.py`
and `reflow/route.py`) already accepts real Evidence records naming any truthful
`BLOCKED`/`RETAINED`/`STALE`/`NOT_SATISFIED`/`CONTRADICTED` outcome, and Evidence's own
existing Change-Free Verification Evidence position (the `verification_observation_request`
field CLOSURE_POLICY.md's own `CHANGE_FREE` row already assigns) is the exact existing
vocabulary an independent verification result belongs in.
`route_verification_result_to_evidence` is the caller's one call from an admissible
`VerificationResult` into that existing position: it calls `derive_evidence` exactly once
over a caller-built, already-real, Change-free `evidence_request`, and returns the resulting
canonical Evidence record already in the shape the existing evidence-sufficiency owner
(`evidence/sufficiency.py`'s `evaluate_sufficiency`) and the existing Difference/Reflow
owner's own reference-closure gate already accept. This layer adds no new terminal-cause
vocabulary and no new Difference/Reflow/Evidence surface -- it connects to the existing ones
by one real call, not by inventing a second owner.

## 9. Structural Review Round 2 corrections (P13-R2-F1/F2/F3)

Three corrections were adopted and implemented on the same branch/PR as Round 1
(`ADOPT_P13_R2_CANONICAL_SELECTION_EVIDENCE_HANDOFF_AND_UNAVAILABLE_PROVENANCE`):

- **P13-R2-F2 (implemented):** §6/§8 above -- `route_verification_result_to_evidence` is the
  real handoff from an admissible `VerificationResult` into the existing Evidence owner's own
  `derive_evidence`, superseding Round 0's "the caller's own, separate concern" stance.
- **P13-R2-F3 (implemented):** frozen semantic decision 5 above -- `UNAVAILABLE` is no longer
  exempt from the distinguishable-input-provenance obligation; every status requires at least
  one explicit, non-target-only input reference, and an unconstructible `UNAVAILABLE` (no
  canonical grounding beyond the target it was asked to verify) is rejected with
  `VerifierOutputError`, not silently accepted. This supersedes §9 as it read before this
  round (the disclosed `UNAVAILABLE` exemption is withdrawn, not merely narrowed).
- **P13-R2-F1 (was disclosed, unresolved; resolved by Round 3):** see §10.

## 10. Structural Review Round 3 resolution (P13-R3-F1)

Round 2 disclosed that no existing Authority owner public surface could bind a
`VerifierSelection` (verifier_identity, permitted_boundary, status, selection authority
identity) and the `VerificationRequirement` it is for (project_id, requirement_id) to a real
Authority Decision *for this specific selection* -- `authority.evaluate_authority`, the only
public surface `manosube_agent_civilization.authority` exported at the time, requires a full,
real, materialized Difference and a matching current State (a Change-against-
Difference-and-State evaluator), and constructing a synthetic Difference/State solely to
launder a `VerifierSelection` through it would have been misuse of an existing owner, not
reuse of one.

SHUKOU adopted `ADOPT_P13_R3_AUTHORITY_OWNED_VERIFIER_SELECTION_DECISION`
(`https://github.com/manosube/manosube-agent-civilization-os/issues/51#issuecomment-5563790496`),
authorizing exactly the escape valve P13-R2-F1 itself named: **extend** the existing
Authority owner with one further, narrowly-scoped, read-only, deterministic public surface --
never a second Authority owner, registry, token, or cache. `authority.
evaluate_verifier_selection` is that extension (`00_KERNEL/05_AUTHORITY/AUTHORITY_CONTRACT.md`
§7.3): it binds `project_id`, `requirement_id`, `verifier_identity`, `permitted_boundary`,
`selection_status`, and the real, Boot-verified `human_authority_ref` to a genuine, canonical,
content-addressed `verifier_selection_grant` record -- admitted through the identical
`admit`/`admit_all` gate every other Authority-owned record (`authority_rule`, `approval`,
`prohibition`) already crosses -- and answers `VERIFIER_SELECTION_SELECTED` only when exactly
one such grant, declared by that real Human Authority, binds every one of those fields
together. A caller-created selection that merely repeats known-real values (including the
real `human_authority_ref` itself) without a genuine backing grant is refused, with the
verifier called zero times, exactly as P13-R2-F1's own required proof demanded.

`run_independent_verification` took an explicit `verifier_selection_grants` collection (grant
*content*, as a caller-supplied argument) and calls `evaluate_verifier_selection` exactly
once, before the verifier is ever called (§5 step 8 since Round 4's renumbering; step 7 at
the time of Round 3); every `AuthorityError` that call itself
raises for an unreadable request propagates unchanged (§6). Round 1's own Boot-verified
`human_authority_ref` check remains in place, unchanged, as the necessary (but, alone, no
longer treated as sufficient) precondition this new Authority-owned decision itself now
consumes as one of its own bound fields (`selection_authority_ref` in the resulting Verifier
Selection Decision record) -- P13-R2-F1 is resolved, not narrowed: the gap this section
previously disclosed no longer exists. Round 3 itself, however, left one further gap open,
resolved by Round 4: see §11.

## 11. Structural Review Round 4 resolution (P13-R4, Authority Provenance Bypass, P13-R3-F2)

Round 3 required a genuine, canonical, Human-Authority-declared `verifier_selection_grant`
before `evaluate_verifier_selection` could answer `VERIFIER_SELECTION_SELECTED` -- but that
evaluator's own admission gate (`authority.conformance.admit`/`admit_all`, shared with every
other Authority-owned record kind) proves only that a supplied grant's content is internally
self-consistent: its own declared identity matches its own recomputed content address, and
its `granted_by` field is shaped like, and equal to, a `human_authority_ref`. Neither check
proves the grant was actually authored by the real Human Authority it names. A
`human_authority_ref` is not a secret -- `boot_project`'s own return value, itself required
input to this exact route -- so a caller able to supply `verifier_selection_grants` as
arbitrary in-memory content could self-hash a grant whose every field, `granted_by` included,
merely repeats known-real values, and reach `VERIFIER_SELECTION_SELECTED` with the verifier
called on the strength of a grant that exists nowhere but that one function call's own
arguments. This is the identical class of gap Round 1 (P13-R1-F2) already closed for the
Human Authority reference itself -- caller-supplied equality is not provenance -- recurring
one layer deeper, at the grant this exact route added in Round 3 to close it.

SHUKOU adopted `ADOPT_P13_R4_CANONICAL_GRANT_PROVENANCE_BINDING`
(`https://github.com/manosube/manosube-agent-civilization-os/issues/51#issuecomment-5570217097`),
requiring grants used to reach `SELECTED` to be resolved/verified against an existing
canonical Human Authority source rather than accepted as caller-supplied, self-hashed
objects, and explicitly prohibiting a second, parallel, or hidden Authority owner and
caller-asserted grant content as provenance. `evaluate_verifier_selection` itself is
untouched by this round -- it remains the one Authority-owned evaluator this decision belongs
to, and still performs the identical shape/binding checks over whatever content it is given
(`00_KERNEL/05_AUTHORITY/AUTHORITY_CONTRACT.md` §7.3, likewise unchanged in its own
evaluation semantics). What changed is what content `run_independent_verification` is willing
to give it: the route now takes `verifier_selection_grant_refs` -- `{"kind":
"verifier_selection_grant", "id": ...}` references, never content -- and resolves each
through the existing Store's own read-only `resolve_record` (the identical single call site
`observation_evidence` targets already resolve through) before any resulting body is ever
considered a grant candidate. A ref naming a record the Store does not durably resolve
refuses (`VerificationRequirementError`) before the Authority owner or the verifier is ever
reached, with zero Store mutation and the verifier called zero times -- exactly the same
failure shape an unresolvable `observation_evidence` target already produces. Only a grant
that actually reached the same durable, `COMMITTED`-boundary persistence
(`store/file_store.py`'s `resolve_record`/`_record_committed_by_any_transaction`) every other
canonical record in this system already relies on can ever bind a selection; a grant that
exists only as one caller's in-process argument cannot.

This closes `CALLER_ASSERTED_GRANT_AS_PROVENANCE` without adding a second Authority owner,
registry, token, or cache, and without expanding this route's own Store surface: `store.
resolve_record` remains the only Store method this package ever calls, from the identical one
call site, now shared by both `observation_evidence` target resolution and
`verifier_selection_grant` resolution (§4, static conformance). Requiring durable Store
commission for a grant does not, by itself, prove *who* wrote that record -- authenticating
write access to the Store is a stated Binding obligation, out of scope for both the Authority
and Independent Verification owners today (`AUTHORITY_CONTRACT.md` §4.1's own
`TRUSTED_STATE_PROVENANCE=BINDING_OBLIGATION` non-claim, unchanged and not newly introduced
by this round); what Round 4 closes is narrower and concrete: a grant asserted only in one
function call's own arguments, never durably committed anywhere, can no longer reach
`SELECTED`.
