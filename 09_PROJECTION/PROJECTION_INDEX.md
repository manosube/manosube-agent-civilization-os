# Identity-Preserving GitHub Projection Index (Phase 14, Issue #62)

```text
DOC_TYPE=PROJECTION_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=PROJECTION-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PROJECTION_ADAPTER
CANONICAL_KERNEL_COUNT=1
PROJECTION_OWNER_COUNT=1
PUBLIC_PROJECTION_ENTRY_POINT_COUNT=1
```

---

## 0. What this document is

This is the one entry point for the **Identity-Preserving GitHub Projection** contract set --
the two documents under `09_PROJECTION/` that define how an already-real canonical
Difference/Change/Evidence subject is projected to a GitHub Issue/Pull Request/artifact
without losing identity or lineage, while GitHub itself remains a projection/audit surface
only, never canonical.

```text
1. PROJECTION_INDEX.md      (this document)
2. PROJECTION_CONTRACT.md   the one public route, its frozen semantics, and its negative
                             controls
```

Read `PROJECTION_CONTRACT.md` for the load-bearing design; this document only fixes this
layer's own position relative to the rest of the Kernel and to Boot, Store, Evidence, and
Independent Verification.

## 1. This is not a ninth Kernel element

`00_KERNEL/KERNEL_INDEX.md` §4 fixes exactly eight Kernel elements (Objective through
Reflow). Identity-Preserving GitHub Projection is not a ninth -- the same
`KERNEL_ELEMENT=none`-style convention Boot, the CLI, the Temporary Agent lifecycle, and
Independent Verification already use (here spelled `NONE_PROJECTION_ADAPTER`, since it is
specifically an outward projection of already-real canonical facts, never a persisted or
authoritative owner of any of them). It does not appear in `00_KERNEL/`'s own numbered
reading order, and it redefines no Kernel Contract's own semantics.

```text
KERNEL_ELEMENT=NONE_PROJECTION_ADAPTER
CANONICAL_KERNEL_COUNT=1
```

## 2. This is not a second State, Difference, Authority, Evidence, Store, or Closure owner

`project_to_github` never mints canonical Difference/Change/Evidence content, never evaluates
Evidence sufficiency, never evaluates a Closure Policy, never emits a Difference Lifecycle
Event or a Closure Evaluation, and mutates the Store exactly once, through the existing
Store's own single sanctioned committer (`store.commit.commit_state_transition` -- the
identical primitive Reflow and Binding already share), and only to persist a genuinely new
Projection Envelope. It resolves the one Store-owned subject reference kind
(`observation_evidence`) through the existing Store's own read-only `resolve_record` -- the
identical, already-established surface Boot and Independent Verification already call -- and
admits a `difference`/`change` subject from the caller-supplied real record body, independently
schema-validated and identity-recomputed through the existing Difference/Change owners' own
identity functions, never Store-resolved by this package itself (Structural Review Round 1,
P14-R1-F2, since neither is a Store-owned record kind in this vertical). It calls the existing
Boot owner's own `boot_project` exactly once to independently re-verify the real Human
Authority reference (the identical pattern Independent Verification's own Structural Review
Round 1, P13-R1-F2, already established), and it does evaluate one Authority Decision -- not a
Change-permission one, but a `github_projection_grant`-bound `evaluate_projection_authorization`
(Structural Review Round 1, P14-R1-F1, an extension of the existing Authority owner, never a
new one) gating every projection operation. It calls its one explicit `GitHubAdapter` at most
three times per request (`find_by_correlation_key` at most once, `materialize` at most once,
`observe` exactly once). `route_observation_receipt_to_evidence` calls the existing Evidence
owner's own public `derive_evidence` exactly once, over a caller-supplied, already-real,
Change-free request grounded in the existing Change-Free Verification Evidence position --
never a second Evidence owner.

```text
PROJECTION_IS_A_SECOND_STATE_OWNER=false
PROJECTION_IS_A_SECOND_DIFFERENCE_OWNER=false
PROJECTION_IS_A_SECOND_AUTHORITY_OWNER=false
PROJECTION_IS_A_SECOND_EVIDENCE_OWNER=false
PROJECTION_IS_A_SECOND_STORE_OWNER=false
PROJECTION_IS_A_SECOND_CLOSURE_OWNER=false
GITHUB_IS_CANONICAL=false
GITHUB_IS_PROJECTION_AND_AUDIT_SURFACE_ONLY=true
PROJECTION_RESULT_IS_EVIDENCE=false
PROJECTION_RESULT_IS_AUTHORITY_DECISION=false
PROJECTION_RESULT_IS_CLOSURE_RECEIPT=false
PROJECTION_RESULT_IS_MERGE_AUTHORIZATION=false
```

## 3. This is not automatic merge, automatic closure, or a fixed adapter

No product, transport, or GitHub App identity is selected by this Phase. A `GitHubAdapter`
is always supplied by the caller; `project_to_github` never merges a Pull Request, never
closes a GitHub Issue, never closes a canonical Difference, and never selects, defaults,
infers, or falls back to an adapter implementation of its own.

```text
FIXED_ADAPTER_IMPLEMENTED=false
AUTOMATIC_MERGE_IMPLEMENTED=false
AUTOMATIC_GITHUB_ISSUE_CLOSE_IMPLEMENTED=false
AUTOMATIC_DIFFERENCE_CLOSURE_IMPLEMENTED=false
```

## 4. Canonical owner

```text
src/manosube_agent_civilization/projection/
├── __init__.py           public exports
├── errors.py              ProjectionError / ProjectionRequirementError /
│                           ConflictingProjectionPayloadError / ProjectionValueError /
│                           ProjectionAdapterError
├── types.py               vocab frozensets, GitHubAdapter Protocol,
│                           GitHubObservationReceipt -- immutable, non-persisted value types
├── identity.py             projection_mapping_key / projection_envelope_id /
│                           projection_envelope_semantic_fingerprint /
│                           projection_payload_fingerprint
├── observable.py           expected_observable_projection / expected_observable_fingerprint
│                           (Structural Review Round 1, P14-R1-F3/F7)
├── engine.py               derive_projection_envelope -- pure, no Store/Boot/Adapter I/O
├── github_adapter.py       FakeGitHubAdapter (controlled, in-memory) and RealGitHubAdapter
│                           (stdlib urllib only) -- the two GitHubAdapter implementations
├── receipt_handoff.py      route_observation_receipt_to_evidence -- the one public
│                           GitHubObservationReceipt-to-Evidence handoff
└── route.py                project_to_github -- the one public projection route

src/manosube_agent_civilization/authority/
└── projection_authorization.py   evaluate_projection_authorization (Structural Review
                                    Round 1, P14-R1-F1) -- an extension of the existing
                                    Authority owner, not a new one
```

No second Boot, Store, Binding, Evidence, Difference, Authority, or Reflow owner is created
anywhere in this package. `reflow`, `binding`, and `independent_verification` are never
imported by any module in this package. `difference`/`change` are importable only from
`route.py`, and only for their own read-only identity/fingerprint functions
(`difference.identity`/`change.identity`) -- never `difference.engine`, `difference.graph`, or
`change.engine` (Structural Review Round 1, P14-R1-F2); `difference.validation` remains the
one shared canonical-schema-validator exception every owner module in this repository already
reuses, not a reuse of the Difference owner's own semantic engine. `evidence` is importable
only from `route.py` (read-only `evidence.identity.evidence_semantic_fingerprint`, to
recompute an `observation_evidence` subject's own real fingerprint) and
`receipt_handoff.py` (the one `derive_evidence` call). `boot` is importable only from
`route.py`, and only to call `boot_project` exactly once. `authority` is importable only from
`route.py`, and only to call `evaluate_projection_authorization` exactly once (Structural
Review Round 1, P14-R1-F1). A network/transport surface (`urllib`) is importable only from
`github_adapter.py` -- static conformance proves all of this by AST walk, the identical
technique
`tests/contract/independent_verification/test_independent_verification_static_conformance.py`
already uses.

## 5. Explicit non-claims

```text
PROJECTION_ENVELOPE_IMPLEMENTED=true
GITHUB_ADAPTER_BOUNDARY_IMPLEMENTED=true
REAL_GITHUB_ADAPTER_IMPLEMENTED=true
REAL_GITHUB_ADAPTER_EXECUTED_AGAINST_A_LIVE_TARGET=false
V3_EXTERNAL_WRITE_ALLOWED_BY_THIS_DELIVERY=false
GITHUB_ISSUE_CLOSE_IMPLEMENTED=false
GITHUB_PULL_REQUEST_MERGE_IMPLEMENTED=false
DIFFERENCE_CLOSURE_FROM_GITHUB_STATE_IMPLEMENTED=false
NEW_STATE_OWNER=false
NEW_EVIDENCE_OWNER=false
NEW_AUTHORITY_OWNER=false
NEW_STORE_OWNER=false
EVIDENCE_ARTIFACT_MATERIALIZE_IMPLEMENTED_ON_REAL_ADAPTER=true
DIFFERENCE_SUBJECT_FINGERPRINT_INDEPENDENTLY_RECONSTRUCTED=true
CHANGE_SUBJECT_FINGERPRINT_INDEPENDENTLY_RECONSTRUCTED=true
GITHUB_PROJECTION_AUTHORITY_DECISION_IMPLEMENTED=true
RECOVERABLE_IDEMPOTENCY_ACROSS_EXTERNAL_WRITE_BOUNDARY_IMPLEMENTED=true
TYPED_OBSERVATION_OUTCOMES_IMPLEMENTED=true
GENUINE_SHA256_OBSERVABLE_FINGERPRINT_IMPLEMENTED=true
CROSS_PROJECT_RECEIPT_RELABELING_REFUSED=true
SIGNED_HUMAN_DECLARATION_ANCHOR_FOR_GITHUB_PROJECTION_GRANT_IMPLEMENTED=true
ATOMIC_RECOVERABLE_PROJECTION_CLAIM_STATE_MACHINE_IMPLEMENTED=true
RECEIPT_HANDOFF_INDEPENDENTLY_RESOLVED_AGAINST_COMMITTED_ENVELOPE=true
EXTERNAL_ARTIFACT_LOCATOR_GRAMMAR_VALIDATED=true
CORRELATION_MARKER_ROUND_TRIP_FIXED=true
TRANSPORT_LEVEL_GITHUB_CONTRACT_FIXTURES_IMPLEMENTED=true
V3_TARGET_BOUND_CONFIGURATION_IMPLEMENTED=true
EXPLICIT_CLAIM_TOKEN_INDEPENDENT_OF_TIMESTAMP_IMPLEMENTED=true
RECEIPT_HANDOFF_INDEPENDENTLY_RE_OBSERVED_NEVER_TRUSTED_FROM_RECEIPT=true
V3_CONFIGURATION_CONTRACT_VALIDATED_ZERO_NETWORK_ACCESS=true
TERMINAL_CLAIM_TOKEN_BOUND_TO_ENVELOPE_IMPLEMENTED=true
SAME_ATTEMPT_RETRY_SEPARATED_FROM_SEMANTIC_REUSE_IMPLEMENTED=true
RECEIPT_ATTESTATION_EXACT_MATCH_REQUIRED_BEFORE_VERIFIED_EVIDENCE=true
V3_LIVE_ADAPTER_TESTS_GATED_BY_RUNTIME_CHECK_NOT_UNCONDITIONAL_SKIP=true
V3_ARTIFACT_KINDS_AND_COUNT_AND_CLEANUP_AND_NO_MERGE_BOUND_AS_CONFIGURATION_FIELDS=true
CLAIM_TOKEN_COVERED_BY_ENVELOPE_SEMANTIC_FINGERPRINT=true
RESOLVED_ENVELOPE_INTEGRITY_INDEPENDENTLY_RE_VERIFIED_BEFORE_REUSE_CLASSIFICATION=true
V3_LIVE_WRITE_AUTHORITY_BOUND_TO_EXACT_CONFIGURATION_FINGERPRINT=true
V3_WHOLE_RUN_ARTIFACT_COUNT_ENFORCED_ACROSS_ALL_THREE_PROJECTION_KINDS=true
V3_CLEANUP_TERMINAL_IMPLEMENTED_INCLUDING_PARTIAL_RUN_FAILURE=true
CLEANUP_REGISTERED_AT_EXTERNAL_WRITE_BOUNDARY_NOT_AFTER_ROUTE_RETURN=true
CLEANUP_TERMINAL_STATE_INDEPENDENTLY_VERIFIED_NOT_HTTP_SUCCESS_ALONE=true
V3_LIVE_WRITE_AUTHORITY_IS_A_GENUINE_SIGNED_HUMAN_AUTHORITY_RECORD=true
UNAUTHORIZED_OR_MISMATCHED_V3_AUTHORITY_CAUSES_ZERO_NETWORK_CALLS=true
V3_LIVE_TRUST_ANCHOR_HAS_NO_MATCHING_PRIVATE_KEY_IN_SHIPPED_OR_LIVE_CODE=true
V3_LIVE_CALL_SITE_HARDCODES_ITS_OWN_TRUST_ANCHOR_NO_CALLER_INJECTION=true
TEST_ONLY_SIGNER_STRUCTURALLY_UNREACHABLE_FROM_THE_LIVE_GATE=true
V3_LIVE_WRITE_AUTHORITY_ROUTED_THROUGH_CANONICAL_PROJECTION_AUTHORIZATION=true
V3_LIVE_WRITE_AUTHORITY_ISSUABLE_VIA_REAL_PROJECT_BINDING_AND_SIGNED_GRANT_DECLARATION=true
V3_TARGET_CONFIGURATION_SUBJECT_KIND_ADDED_TO_AUTHORITY_AND_BINDING_SCHEMAS=true
ORPHAN_V3_TEST_SIGNER_AND_TRUST_ANCHOR_REMOVED=true
V3_LIVE_WRITE_AUTHORITY_RESOLVED_FROM_REAL_STORE_VIA_BOOT=true
V3_LIVE_WRITE_AUTHORITY_ACCEPTS_REFERENCES_NEVER_BODIES=true
V3_AUTHORIZED_CONTEXT_THREADED_UNCHANGED_INTO_EXECUTION=true
V3_STALE_STORE_REVISION_DETECTED_AND_REFUSED=true
PHASE_14_COMPLETE=false
PHASE_15_ALLOWED=false
```

The last five lines before the Round 2 additions above record Structural Review Round 1's own
corrections (Issue #62, `ADOPT_P14_R1_CANONICAL_AUTHORITY_SUBJECT_AND_RECOVERABLE_PROJECTION`)
-- see `PROJECTION_CONTRACT.md` §3 items 13-17 for the full frozen semantics each one fixes.
The seven `..._IMPLEMENTED`/`..._FIXED`/`..._VALIDATED` lines after those record Structural
Review Round 2's own corrections (`ADOPT_P14_R2_SIGNED_AUTHORITY_ATOMIC_PROJECTION_AND_REAL_
V3`) -- see `PROJECTION_CONTRACT.md` §10 for the full detail each one fixes.
`V3_TARGET_BOUND_CONFIGURATION_IMPLEMENTED` was `false` at the end of Round 2, disclosed as a
deliberately-unclosed item; it is now `true`. The three lines immediately above it record
Structural Review Round 3's own corrections
(`ADOPT_P14_R3_UNIQUE_CLAIM_ATTESTED_RECEIPT_AND_CONFIGURABLE_V3`) -- see
`PROJECTION_CONTRACT.md` §11 for the full detail each one fixes, including a correction to
Round 2's own mistaken belief that its F2 (atomic claims) and F3 (receipt corroboration) were
already fully closed. `V3_LIVE_EXTERNAL_WRITE_AUTHORITY=false` still holds, unchanged by any
of this: `V3_TARGET_BOUND_CONFIGURATION_IMPLEMENTED=true` closes the *configuration*
requirement only, never live-write authorization.
The five lines immediately above `PHASE_14_COMPLETE` record Structural Review Round 4's own
corrections (`ADOPT_P14_R4_TERMINAL_CLAIM_ATTESTED_RECEIPT_AND_SOURCE_EDIT_FREE_V3`) -- see
`PROJECTION_CONTRACT.md` §12 for the full detail each one fixes, including a correction to
Round 3's own mistaken belief that its F1 (claim ownership), F2 (receipt corroboration), and
F3 (V3 configuration) were already fully closed. `V3_LIVE_ADAPTER_TESTS_GATED_BY_RUNTIME_
CHECK_NOT_UNCONDITIONAL_SKIP=true` and `V3_LIVE_EXTERNAL_WRITE_AUTHORITY=false` both hold
together, unchanged by any of this: the real-adapter tests are now gated by a fail-closed
runtime check reading the environment rather than a hardcoded skip, but that gate still
evaluates `False` in this delivery -- no live write occurs.
The five lines immediately above `PHASE_14_COMPLETE` record Structural Review Round 5's own
corrections (`ADOPT_P14_R5_TERMINAL_CLAIM_INTEGRITY_AND_BOUND_V3_EXECUTION`) -- see
`PROJECTION_CONTRACT.md` §13 for the full detail each one fixes: `claim_token` is now part of
`projection_envelope_semantic_fingerprint`, a resolved Envelope's own fingerprint is
independently re-verified (`ProjectionEnvelopeIntegrityError`) before same-attempt/semantic-
reuse classification is ever reached, V3 live-write authority is now bound to the exact
`configuration_fingerprint` of the configuration it authorizes (not the unscoped literal
`"true"` Round 4 used), the authorized artifact count is enforced as one shared budget across
the complete three-projection run, and a cleanup terminal closes every artifact a run actually
materializes, including under partial-run failure. `V3_LIVE_EXTERNAL_WRITE_AUTHORITY=false`
still holds, unchanged by any of this.
The four lines immediately above `PHASE_14_COMPLETE` record Structural Review Round 6's own
corrections (`ADOPT_P14_R6_AUTHORITY_BOUND_V3_AND_OBSERVED_CLEANUP`) -- see
`PROJECTION_CONTRACT.md` §14 for the full detail each one fixes: cleanup is now registered at
the true external-write boundary itself (inside the adapter wrapper's own `materialize()` call,
via an `on_materialized` callback), not after the whole enclosing route call has already
returned, so a later route step (`observe`, Envelope derivation, Store commit) failing after a
genuine external write already succeeded no longer leaves that artifact untracked; a cleanup
result is reported closed only after the returned response body is independently parsed and
found to actually reflect the closed/cancelled terminal state, never on a non-error HTTP status
alone. V3 live-write authority is now a genuine Ed25519-signed SHUKOU/Human Authority record
(`tests/fixtures/v3_live_write_authority.py`), verified with the identical primitive this
repository's own signed Human Grant Declarations already use, replacing Round 5's own
caller-computable-digest mechanism (`LIVE_WRITE_AUTHORIZED_ENV` equal to the configuration's
own `configuration_fingerprint`) outright -- a value any caller could compute unaided was never
itself Authority. A fabricated, stale, wrong-fingerprint, wrong-target, wrong-action, or
widened-boundary authority record refuses before any network call this harness would have made
on its strength, proved by a monkeypatched `urllib.request.urlopen` that raises if ever
invoked. `V3_LIVE_EXTERNAL_WRITE_AUTHORITY=false` still holds, unchanged by any of this.
The three lines immediately above `PHASE_14_COMPLETE` record Structural Review Round 7's own
correction (`ADOPT_P14_R7_EXTERNAL_TRUST_ANCHOR_FOR_V3_AUTHORITY`) -- see
`PROJECTION_CONTRACT.md` §15 for the full detail: the V3 Live Write Authority's live trust
anchor (`tests/fixtures/v3_live_write_authority.py`) is now a fixed public key with no matching
private key anywhere in this repository, its runtime package, or its live harness --
Round 6's own signing helpers (`assemble_v3_live_write_authority` and the private key behind
it) are removed from that module entirely, replaced by `V3_LIVE_TRUST_ANCHOR` and a
`v3_live_write_authorized` that now requires its `trust_anchor` as an explicit, required
keyword argument. The one live call site hardcodes that exact anchor in its own source, with
no environment variable, record field, or other caller-reachable input able to substitute a
different one. A dedicated, structurally separate test-only signer
(`tests/fixtures/v3_live_write_authority_test_signer.py`) lets offline tests still exercise the
verification logic under an explicitly injected, distinct test trust anchor that can never be
mistaken for, and can never verify against, the live one -- proven by a new AST-based static
conformance test rather than by convention. `V3_LIVE_EXTERNAL_WRITE_AUTHORITY=false` still
holds, unchanged by any of this.
The four lines immediately above `PHASE_14_COMPLETE` record Structural Review Round 8's own
correction (`ADOPT_P14_R8_CANONICAL_ISSUABLE_V3_AUTHORITY`) -- see `PROJECTION_CONTRACT.md`
§16 for the full detail: Round 7's own fixed, un-issuable trust anchor is replaced outright by
direct reuse of the same canonical Authority/Binding route a real GitHub projection operation
already uses (`authority.projection_authorization.evaluate_projection_authorization`, fed a
genuinely content-address-verified `project_binding` plus signed
`github_projection_grant`/`github_projection_grant_declaration` records), so a genuine V3 Live
Write Authority record can now actually be issued by the project's real canonical Human
Authority -- something no prior round's construction made possible. `human_authority_ref`/
`human_authority_signing_key` are read only from the verified `project_binding` record itself,
never independently caller-supplied. One new closed subject kind,
`"v3_target_configuration"`, was added to the previously three-member `subject_ref.kind` enum
in both `01_SCHEMA/authority/github_projection_grant.schema.json` and
`01_SCHEMA/binding/github_projection_grant_declaration.schema.json` -- disclosed here as this
round's one deliberate design decision, an additive extension of the existing single canonical
owner's own vocabulary, never a second owner. Round 7's now-superseded orphan test signer
(`tests/fixtures/v3_live_write_authority_test_signer.py`) is deleted; the new test-only
material builder (`tests/fixtures/v3_authority_test_material.py`) reuses this repository's own
established Product Binding fixtures rather than inventing a second signing convention.
`V3_LIVE_EXTERNAL_WRITE_AUTHORITY=false` still holds, unchanged by any of this.
The four lines immediately above `PHASE_14_COMPLETE` record Structural Review Round 9's own
correction (`ADOPT_P14_R9_STORE_RESOLVED_AUTHORITY_TO_EXECUTION`) -- see
`PROJECTION_CONTRACT.md` §17 for the full detail: the V3 live gate no longer accepts
caller-supplied `project_binding`/`grants`/`grant_declarations` **bodies** at all -- only
project-scoped **references** (a Store root, `project_id`, `project_binding_id`, grant/
declaration ids), resolved against the real canonical Store through the identical Boot route
(`boot.boot_project`) a real GitHub projection call already uses. A fully self-consistent,
correctly-signed, but never-committed set of bodies now authorizes nothing, since
`store.resolve_record` never resolves a reference nothing ever committed. The resolved,
verified authority context (`V3AuthorizedExecutionContext`) is threaded unchanged into the
exact execution function that reaches the adapter -- closing the "detached pre-check followed
by separately fixture-authorized projection" gap Round 8's own design still had, where the
live-gated test checked embedded material against nothing, then executed against an entirely
disconnected throwaway Store. `v3_execution_context_still_current` fails the whole run closed
if the Store mutates between authorization and execution. `V3_LIVE_EXTERNAL_WRITE_AUTHORITY=
false` still holds, unchanged by any of this; the Round 8 `v3_target_configuration` schema
extension remains unchanged and, per this round's own adoption, provisional until this
canonical admission path passes structural review.
`PHASE_14_COMPLETE` and `PHASE_15_ALLOWED` remain `false`: these correction rounds close their
own respective structural findings, not Phase 14 itself, which still awaits a separate SHUKOU
decision.
