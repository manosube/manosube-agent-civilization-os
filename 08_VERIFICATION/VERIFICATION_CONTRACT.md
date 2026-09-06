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
    verification_requirement: VerificationRequirement,
    verifier_selection: VerifierSelection,
    verifier: IndependentVerifier,
) -> VerificationResult
```

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
4. **SHUKOU selects explicitly.** `VerifierSelection` is always caller-supplied. Its
   `selection_authority_ref` must canonical-reference-equal the requirement's own, and its
   `permitted_boundary` must canonical-reference-equal the requirement's own
   `verification_boundary` -- a selection bound to a different authority or boundary is
   rejected before the verifier is ever called. No automatic selection, fallback,
   cwd/environment/cache inference, or "only available reviewer" rule exists.
5. **Independence is provenance plus boundary.** A `VerificationResult` carries target refs,
   frozen boundary, verifier identity, selection authority ref, input refs, and result.
   A verifier whose own `input_refs` cite nothing beyond the requirement's own `target_refs`
   has produced no independent input at all -- implementation-indistinguishable provenance
   does not satisfy an independent verification requirement, and this route refuses it
   (`VerifierOutputError`), except when `status` is `UNAVAILABLE` (disclosed interpretation:
   an `UNAVAILABLE` result asserts the verifier could not evaluate at all, so it is not
   expected to have examined anything; see §9).
6. **Verifier never persists canonical Evidence directly.** `IndependentVerifier` returns an
   immutable result/attestation-candidate payload. This package never calls into
   `manosube_agent_civilization.evidence`, and therefore never writes canonical Evidence,
   never operates the Store's transaction manifest, recovery, or current-view
   reconstruction. Existing Evidence ownership remains the only canonical persistence path;
   carrying an admissible verification result into it is the caller's own, separate concern.
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
├── __init__.py     public exports
├── errors.py        IndependentVerificationError / VerificationRequirementError /
│                     VerifierOutputError
├── types.py          VerificationRequirement / VerifierSelection / VerificationResult /
│                     IndependentVerifier
└── route.py          run_independent_verification
```

`VerificationRequirementError` and `VerifierOutputError` exist only for the two admission
boundaries this layer itself owns (requirement/selection/boundary/target admission; the
shape of what an explicit verifier returns). Every other failure mode -- a caller-supplied
`store` that itself raises a typed Store error from `resolve_record` -- propagates unchanged;
this layer never catches or reclassifies it.

## 5. Canonical route

```text
1. Validate project_id is an explicit canonical identity (never a path/URL/locator).
2. Validate verification_requirement.project_id and verifier_selection.project_id both
   equal project_id.
3. Validate verifier_selection.requirement_id equals verification_requirement.requirement_id.
4. Validate verifier_selection.status is ACTIVE (REVOKED/EXPIRED/unrecognized all refuse).
5. Validate verifier_selection.selection_authority_ref canonical-reference-equals
   verification_requirement.selection_authority_ref.
6. Validate verifier_selection.permitted_boundary canonical-reference-equals
   verification_requirement.verification_boundary.
7. Validate verification_requirement.target_refs is non-empty, and each entry is an
   explicit {"kind", "id"} reference whose kind is difference/change/observation_evidence.
   Every observation_evidence target is resolved through store.resolve_record(project_id,
   "observation_evidence", id) -- an unresolvable one refuses before the verifier is called.
8. Call verifier(requirement=verification_requirement, selection=verifier_selection)
   exactly once. Zero Store writes occur, in this route or in the verifier call itself
   (the verifier is a plain Python callable this route never grants Store access to).
9. Validate the verifier's own return value: status in {VERIFIED, FAILED, INSUFFICIENT,
   UNAVAILABLE}; input_refs a list of explicit {"kind", "id"} references, non-empty and not
   a subset of target_refs unless status is UNAVAILABLE; observations an explicit mapping.
10. Return one immutable VerificationResult carrying every field above, deep-frozen.
```

## 6. Required rejection proofs

At minimum, this layer fails closed, with zero Store mutation
(`STATE_TRANSITION_COUNT_DELTA=0`, `RECORD_COUNT_DELTA=0`, `EXTERNAL_OPERATION_COUNT_DELTA=0`)
and no `VerificationResult` produced, and the supplied `verifier` never called, for:

```text
- a project_id that is a path/URL/locator rather than a plain identity
- verification_requirement.project_id or verifier_selection.project_id not matching the
  requested project_id
- a verifier_selection whose requirement_id does not name the supplied requirement
- a verifier_selection whose status is REVOKED, EXPIRED, or any unrecognized value
- a verifier_selection whose selection_authority_ref diverges from the requirement's own
- a verifier_selection whose permitted_boundary diverges from the requirement's own
  verification_boundary
- an empty target_refs, a target reference missing kind/id, or a target reference whose
  kind is outside {difference, change, observation_evidence}
- an observation_evidence target reference the Store does not resolve for this project
```

And, once the verifier has been called (the one point past which this route's own
admission gate has already passed and Store mutation remains zero throughout):

```text
- a non-mapping verifier return value
- an unrecognized status
- a non-list input_refs, or an input_refs entry missing kind/id
- a non-mapping observations payload
- (status != UNAVAILABLE) an empty input_refs, or an input_refs set that is a subset of
  target_refs -- implementation-indistinguishable provenance
```

Static conformance additionally proves: exactly one public route
(`run_independent_verification`) and exactly one lifecycle-free result type
(`VerificationResult`); that this package never imports `evidence`, `difference`,
`authority`, `reflow`, `boot`, or `binding`; that `store.resolve_record` is the only Store
method this package ever calls, and is called at most once per Store-owned target
reference; and that no module in this package imports a model, subprocess, shell, network,
GitHub, Observer, Change-execution, scheduler, or multi-Agent surface.

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
```

## 8. Failed verification remains representable through existing ownership

No new capability is required for a `FAILED`/`INSUFFICIENT`/`UNAVAILABLE`
`VerificationResult` to be representable in existing Difference/Reflow semantics: Reflow's
own terminal-cause binding (`evidence/engine.py`'s `resolve_terminal_reason_evidence`,
consumed by `reflow/closure.py` and `reflow/route.py`) already accepts real Evidence
records naming any truthful `BLOCKED`/`RETAINED`/`STALE`/`NOT_SATISFIED`/`CONTRADICTED`
outcome. A caller holding a non-`VERIFIED` `VerificationResult` records the underlying
observation as ordinary Evidence through the existing Evidence owner, exactly as it would
for any other observed failure -- this layer adds no new terminal-cause vocabulary and no
new Difference/Reflow surface, because none is needed.

## 9. Disclosed interpretation: the UNAVAILABLE exemption from the independence check

Frozen semantic decision 5 requires a `VerificationResult`'s own provenance to be
distinguishable from the implementation lineage it names, and this route enforces that by
refusing a verifier's `input_refs` when they cite nothing beyond `target_refs`. This
adopted implementation exempts `status=UNAVAILABLE` from that specific check (only), on the
reading that `UNAVAILABLE` asserts the verifier could not evaluate at all -- it has nothing
to have examined, so requiring it to cite distinguishable input would make a truthful
`UNAVAILABLE` report unconstructible. This is a disclosed interpretation, not a silent
narrowing: Issue #51 does not itself resolve whether `UNAVAILABLE` should be exempt, and a
future round may adopt a narrower or wider rule.
