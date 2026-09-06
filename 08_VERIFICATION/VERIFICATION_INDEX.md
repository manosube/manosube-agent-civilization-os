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

`run_independent_verification` never mints canonical Evidence, never evaluates Evidence
Sufficiency, never evaluates a Closure Policy, never emits a Difference Lifecycle Event or a
Closure Evaluation, never evaluates an Authority Decision, and never mutates the Store. It
resolves exactly one Store-owned reference kind (`observation_evidence`) through the existing
Store's own read-only `resolve_record` -- the identical, already-established surface Boot
itself calls -- and calls its one explicit `IndependentVerifier` exactly once. Carrying an
admissible verification result into existing Evidence-sufficiency semantics remains entirely
the existing Evidence owner's own, separate concern; this package implements no such path and
therefore cannot bypass it.

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
├── __init__.py     public exports
├── errors.py        IndependentVerificationError / VerificationRequirementError /
│                     VerifierOutputError
├── types.py          VerificationRequirement / VerifierSelection / VerificationResult /
│                     IndependentVerifier -- immutable, non-persisted value types
└── route.py          run_independent_verification -- the one public verification route
```

No second Boot, Store, Binding, Evidence, Difference, Authority, or Reflow owner is created
anywhere in this package. This package never imports `manosube_agent_civilization.evidence`,
`manosube_agent_civilization.difference`, `manosube_agent_civilization.authority`,
`manosube_agent_civilization.reflow`, `manosube_agent_civilization.boot`, or
`manosube_agent_civilization.binding` -- static conformance proves it. Its only interaction
with an existing owner is one call to the caller-supplied `store`'s own already-public
`resolve_record` method, to confirm a Store-owned target reference (`observation_evidence`)
is real before the verifier this route calls could otherwise be pointed at a fabricated one.

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
PHASE_13_COMPLETE=false
PHASE_14_ALLOWED=false
```
