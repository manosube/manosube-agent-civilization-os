# Independent Verification Index (Phase 13, Issue #51)

```text
DOC_TYPE=VERIFICATION_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=VERIFICATION-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=INDEPENDENT_EVIDENCE_ADAPTER
CANONICAL_KERNEL_COUNT=1
INDEPENDENT_VERIFICATION_OWNER_COUNT=1
PUBLIC_VERIFICATION_ENTRY_POINT_COUNT=1
```

---

## 0. What this document is

This is the one entry point for the **Independent Verification** contract set -- the two
documents under `08_VERIFICATION/` that define how an explicit, SHUKOU-authorized
verification lineage, distinct from the implementation lineage, is required, run, and
returned as one immutable, non-persisted result.

```text
1. VERIFICATION_INDEX.md      (this document)
2. VERIFICATION_CONTRACT.md   the one public route, its frozen semantics, and its negative
                               controls
```

Read `VERIFICATION_CONTRACT.md` for the load-bearing design; this document only fixes this
layer's own position relative to the rest of the Kernel and to Boot, the Temporary Agent
lifecycle, Evidence, Difference, and Reflow.

## 1. This is not a ninth Kernel element

`00_KERNEL/KERNEL_INDEX.md` §4 fixes exactly eight Kernel elements (Objective through
Reflow). Independent Verification is not a ninth -- the same `KERNEL_ELEMENT=none`-style
convention Boot, the CLI, and the Temporary Agent lifecycle already use (here spelled
`INDEPENDENT_EVIDENCE_ADAPTER`, since it is specifically a per-call verification handshake,
never a persisted or authoritative owner). It does not appear in `00_KERNEL/`'s own numbered
reading order, and it redefines no Kernel Contract's own semantics.

```text
KERNEL_ELEMENT=INDEPENDENT_EVIDENCE_ADAPTER
CANONICAL_KERNEL_COUNT=1
```

## 2. This is not a second Evidence, Difference, Authority, Reflow, or Store owner

`run_independent_verification` never mints canonical Evidence itself, never evaluates
Evidence Sufficiency, never evaluates a Closure Policy, never emits a Difference Lifecycle
Event or a Closure Evaluation, never evaluates a Change-permission Authority Decision, and
never mutates the Store. It resolves exactly one Store-owned reference kind
(`observation_evidence`) through the existing Store's own read-only `resolve_record` -- the
identical, already-established surface Boot itself calls -- calls the existing Boot owner's
own `boot_project` exactly once to independently re-verify the real Human Authority reference
(Structural Review Round 1, P13-R1-F2), and calls its one explicit `IndependentVerifier`
exactly once. Structural Review Round 2 (P13-R2-F2) adds the one real connection into
existing Evidence ownership: `route_verification_result_to_evidence` calls the existing
Evidence owner's own public `derive_evidence` exactly once, over a caller-supplied,
already-real, Change-free request -- superseding the earlier "the existing Evidence owner's
own, separate concern" stance. Structural Review Round 3 (P13-R3-F1) adds one further real
call into existing Authority ownership: `run_independent_verification` also calls the
existing Authority owner's own new, dedicated `evaluate_verifier_selection` exactly once,
requiring it to answer `VERIFIER_SELECTION_SELECTED` before the verifier is ever called --
this is real reuse of the one existing Authority owner by call (`authority` gains a second,
narrowly-scoped public evaluator of its own, documented in
`00_KERNEL/05_AUTHORITY/AUTHORITY_CONTRACT.md` §7.3; this package still never becomes a
second Authority owner itself). This package still mints no canonical Evidence itself (the
existing Evidence owner alone decides the derived record's identity and schema validation),
evaluates no Change-permission Authority Decision, sufficiency, or closure itself, and
creates no second Evidence, Difference, Authority, Reflow, or Store owner.

```text
VERIFICATION_IS_A_SECOND_EVIDENCE_OWNER=false
VERIFICATION_IS_A_SECOND_DIFFERENCE_OWNER=false
VERIFICATION_IS_A_SECOND_AUTHORITY_OWNER=false
VERIFICATION_IS_A_SECOND_REFLOW_OWNER=false
VERIFICATION_IS_A_SECOND_STORE_OWNER=false
VERIFICATION_MAY_MUTATE_STORE=false
VERIFICATION_RESULT_IS_EVIDENCE=false
VERIFICATION_RESULT_IS_AUTHORITY_DECISION=false
VERIFICATION_RESULT_IS_CLOSURE_RECEIPT=false
VERIFICATION_RESULT_IS_STATE_TRANSITION=false
VERIFICATION_RESULT_IS_MERGE_AUTHORIZATION=false
```

## 3. This is not a fixed verifier, automatic selection, or automatic closure

No product, model, provider, or bot is selected by this Phase. `VerifierSelection` is always
supplied by the caller, SHUKOU-authorized; `run_independent_verification` never selects,
defaults, infers, or falls back to one. A `VERIFIED` result is only a result for the stated
requirement -- it authorizes nothing else on its own.

```text
FIXED_VERIFIER_IMPLEMENTED=false
AUTOMATIC_VERIFIER_SELECTION_IMPLEMENTED=false
AUTOMATIC_CLOSURE_IMPLEMENTED=false
CODEX_AUTO_REVIEW_ENABLED=false
CODEX_AS_VERIFIER_DEFAULT=false
```

## 4. Canonical owner

```text
src/manosube_agent_civilization/independent_verification/
├── __init__.py         public exports
├── errors.py            IndependentVerificationError / VerificationRequirementError /
│                         VerifierOutputError / VerificationValueError /
│                         EvidenceHandoffError
├── types.py              VerificationRequirement / VerifierSelection / VerificationResult /
│                         IndependentVerifier -- immutable, non-persisted value types
├── route.py              run_independent_verification -- the one public verification route
│                         (also calls the existing Authority owner's own
│                         evaluate_verifier_selection exactly once -- Structural Review
│                         Round 3, P13-R3-F1)
└── evidence_handoff.py   route_verification_result_to_evidence -- the one public
                          VerificationResult-to-Evidence handoff (Structural Review Round 2)
```

No second Boot, Store, Binding, Evidence, Difference, Authority, or Reflow owner is created
anywhere in this package. `difference`, `reflow`, and `binding` are never imported by any
module in this package. `evidence` is importable only from `evidence_handoff.py`, and only to
call its one public `derive_evidence` exactly once (Structural Review Round 2, P13-R2-F2).
`authority` is importable only from `route.py`, and only to call its one public
`evaluate_verifier_selection` exactly once (Structural Review Round 3, P13-R3-F1) -- static
conformance proves both. This package's interaction with existing owners is: one call to the
caller-supplied `store`'s own already-public `resolve_record` method (to confirm a
Store-owned target reference is real before the verifier this route calls could otherwise be
pointed at a fabricated one), one call to the existing Boot owner's own `boot_project`
(Structural Review Round 1, P13-R1-F2, to independently re-verify the real Human Authority
reference), one call to the existing Authority owner's own `evaluate_verifier_selection`
(Structural Review Round 3, P13-R3-F1, to independently re-verify that a real Human Authority
selected this exact `VerifierSelection` for this exact `VerificationRequirement` -- resolving
the gap Round 2 disclosed), and one call to the existing Evidence owner's own `derive_evidence`
(Structural Review Round 2, P13-R2-F2, the real handoff).

## 5. Explicit non-claims

```text
INDEPENDENT_VERIFICATION_IMPLEMENTED=true
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
AUTONOMOUS_CHANGE_IMPLEMENTED=false
MULTI_AGENT_IMPLEMENTED=false
NEW_STATE_OWNER=false
NEW_EVIDENCE_OWNER=false
NEW_AUTHORITY_OWNER=false
NEW_STORE_OWNER=false
EXISTING_EVIDENCE_OWNER_HANDOFF_REQUIRED=true
VERIFIER_SELECTION_DECISION_IMPLEMENTED=true
EXISTING_AUTHORITY_OWNER_SELECTION_CHECK_REQUIRED=true
NEW_SELECTION_REGISTRY=false
NEW_SELECTION_TOKEN=false
NEW_SELECTION_CACHE=false
FAKE_DIFFERENCE_OR_STATE_FOR_AUTHORITY=false
CALLER_MAPPING_EQUALITY_AS_AUTHORITY=false
BOOT_HUMAN_AUTHORITY_REF_ALONE_IS_SELECTION_DECISION=false
PHASE_13_COMPLETE=false
PHASE_14_ALLOWED=false
```
