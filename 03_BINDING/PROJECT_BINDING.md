# Project Binding Contract (Phase 9, Issue #43)

```text
DOC_TYPE=PROJECT_BINDING_CONTRACT
DOCUMENT_ID=BINDING-PROJECT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PRODUCT_BINDING_LAYER
```

See `BINDING_INDEX.md` for this contract set's own position and reading order.

## 1. Position

A Project Binding is the one immutable, content-addressed record that binds a real
Human-declared project to its Objective Revision, Boundary, Authority policy reference,
Source Registrations, Command Policy, and secret-exclusion policy. It is produced,
validated, and identified by exactly one owner
(`manosube_agent_civilization.binding.engine.assemble_project_binding`) and adopted by
exactly one public genesis entry point (`manosube_agent_civilization.binding.route.
bind_project`). A second public entry point, `declare_human_grant` (§11, Phase 13, Issue
#51, Structural Review Round 5), commits a distinct, post-genesis record kind through the
Store's ordinary `.commit` -- never `.initialize` -- and is not a second genesis route.

```text
PRODUCT_BINDING_OWNER_COUNT=1
PUBLIC_PRODUCT_BINDING_ENTRY_POINT_COUNT=2
PUBLIC_GENESIS_ENTRY_POINT_COUNT=1
```

## 2. Shape

Schema: `01_SCHEMA/binding/project_binding.schema.json`.

```text
schema_version              const "0.1"
project_binding_id          PROJBIND-<sha256 hex, uppercase> -- content-addressed, see §3
project_id                  common/identity.schema.json -- Human-declared, semantic, never
                             a filesystem path, URL, GitHub id, directory name, or mutable
                             locator (§4)
objective_revision_ref      {kind: "objective_revision", id} -- names the real Objective
                             Revision body bind_project also persists (§5)
boundary                    boundary.schema.json (BOUNDARY_CONTRACT.md)
authority_policy_ref        {kind: "authority_rule", id} -- resolves to a real, persisted
                             Authority Rule body (§5b), never a second Authority owner
                             (TRUST_MODEL.md §2)
source_registrations        array of source_registration.schema.json (SOURCE_REGISTRATION.md)
command_policy               command_policy.schema.json (COMMAND_EXECUTION_POLICY.md)
secret_exclusion_policy      forbidden_field_names + allowed_secret_reference_kinds
                              (SECRET_HANDLING.md) -- never an actual secret value
human_authority_ref           common/reference.schema.json
bound_at                      common/timestamp.schema.json -- excluded from identity, §3
```

`additionalProperties: false` throughout every embedded schema: an unrecognized field
anywhere in the accepted graph fails closed at schema validation, before any cross-field
reasoning runs.

## 3. Identity

`project_binding_id` is the sha256 content address (`PROJBIND-` prefix, uppercase hex) of
the closed field set `schema_version, project_id, objective_revision_ref, boundary,
authority_policy_ref, source_registrations, command_policy, secret_exclusion_policy,
human_authority_ref` -- the repo-wide canonical-serialization convention
(`state.canonicalize.canonical_json_bytes`, via `difference.canonical.canonical_bytes`),
the same one every other domain's own identity function reads rather than restates.

`bound_at` is excluded: it is the instant a declaration was adopted, never part of what was
adopted, exactly as Reflow's own `closure_evaluation_id` excludes its later-stamped
`reflow_transition_ref`.

`manosube_agent_civilization.binding.identity.verify_project_binding_identity` recomputes
the id from a record's own declared fields and requires it to equal the claimed id --
called once inside `assemble_project_binding` itself, so a forged or drifted id is refused
before any record is ever returned for persistence, not merely detected after the fact.

```text
PROJECT_BINDING_CONTENT_ADDRESSED=true
PROJECT_BINDING_IDENTITY_REVERIFIED=true
PROJECT_ID_IS_LOCATOR=false
```

## 4. `project_id` is not a locator

`project_id` uses the same generic `common/identity.schema.json` pattern
(`^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$`) every other cross-cutting canonical id in this Kernel
uses. That pattern structurally forecloses a filesystem path (no `/`), a URL (no scheme,
no `.`), a bare numeric GitHub repository id (must start with an uppercase letter), and a
lowercase directory name (must be uppercase) -- fail-closed by schema, never by inferring
meaning from the string's own content.

## 5. Objective Revision is accepted and persisted, not re-produced

`bind_project` accepts the real, Human-declared Objective Revision body and validates it
against Objective's own schema (`01_SCHEMA/objective/objective_revision.schema.json`,
never restated here). It mints no `objective_revision_id` of its own -- Objective Revision
identity remains Human-Authority-declared input, exactly as every other Kernel consumer of
it already treats it (`reflow/reference_registry.py`'s own inventory).

Unlike that existing precedent, Product Binding *does* persist the accepted Objective
Revision body as a Store-owned record (`kind="objective_revision"`), atomically alongside
the Project Binding and genesis State, through the existing, generic `FileStateStore.
initialize`. This is required to make Issue #43's own "same-id/different-body
substitution" negative control real and provable -- the Store's own generic manifest-
claimant mechanism (`FileStateStore._record_committed_by_any_transaction`) then protects it
identically to every other persisted record, with no domain-specific content-address logic
added to the Store itself.

```text
OBJECTIVE_REVISION_SECOND_PRODUCER=false
OBJECTIVE_REVISION_PERSISTED_AS_A_STORE_RECORD=true
```

## 5b. Authority Rule is accepted and persisted, not re-produced

**Added in Phase 9 Structural Review Round 1 (P9-R1-F1).** `bind_project` accepts the real
Authority Rule body `authority_policy_ref` names (a new required `authority_rule` keyword),
validates it against Authority's own existing schema (`01_SCHEMA/authority/
authority_rule.schema.json`, never restated here), and reverifies its identity via
Authority's own existing `authority.identity.rule_id` (never a second identity algorithm) --
requiring `rule_id(authority_rule) == authority_policy_ref["id"] ==
authority_rule["authority_rule_id"]`.

Two further checks, before any write:

```text
authority_rule.project_id == project_id                          (else BindingIdentityError)
authority_rule.declared_by == human_authority_ref                 (else BindingIdentityError,
                                                                    canonical-reference exact
                                                                    equality; see TRUST_MODEL
                                                                    .md §2b)
```

`authority_rule` is persisted as a Store-owned record (`kind="authority_rule"`) in the same
atomic `TX-GENESIS` manifest as the Objective Revision and Project Binding, through the
existing, generic `FileStateStore.initialize` -- protected by the Store's own generic
manifest-claimant mechanism identically to every other persisted record, with no
domain-specific content-address logic added to the Store itself.

```text
AUTHORITY_RULE_SECOND_PRODUCER=false
AUTHORITY_RULE_SECOND_IDENTITY_ALGORITHM=false
AUTHORITY_RULE_PERSISTED_AS_A_STORE_RECORD=true
AUTHORITY_POLICY_REF_RESOLVABLE_FROM_FRESH_STORE=true
```

## 6. Atomic adoption

`bind_project` builds a fully assembled genesis `project_state` dict (caller-supplied
`semantic_state`/`state_metadata`, `state_revision=0`), computes its real
`semantic_fingerprint` via `state.fingerprint.fingerprint_project_state` (the existing
State owner's own real producer), and calls `FileStateStore.initialize` once, with
`records=[objective_revision, authority_rule, project_binding,
*additional_genesis_records]` -- the identical `(kind, id, body)` shape, and the identical
atomic staged/journaled transaction mechanism (`TX-GENESIS`), R10-F1 already established for
genesis records this vertical's own State references. `additional_genesis_records` carries
whatever further records genesis State's own declared content references (its own Kernel
Source Snapshot, in particular) -- never a second genesis-record surface.

```text
BINDING_AND_GENESIS_ATOMICALLY_VISIBLE=true
SECOND_STATE_OR_STORE_OWNER_CREATED=false
```

## 7. Cross-consistency, checked before any write

```text
objective_revision.project_id == project_id                     (else BindingIdentityError,
                                                                   Round 1 P9-R1-F2)
objective_revision.human_authority_ref == human_authority_ref     (else BindingIdentityError,
                                                                    Round 1 P9-R1-F2)
genesis_state.project_id == project_id                         (else BindingIdentityError)
genesis_state.objective_revision_id == objective_revision_id    (else BindingIdentityError)
genesis_state.state_revision == 0                               (else BindingValidationError)
genesis_state.previous_state_fingerprint is None                (else BindingValidationError)
genesis_state.lineage_head_ref is None                          (else BindingValidationError)
```

See §5b for the Authority Rule's own cross-consistency checks.

## 8. Replay semantics

**Corrected in Phase 9 Structural Review Round 1 (P9-R1-F4), corrected again in Round 2
(P9-R2-F4).** `FileStateStore.initialize` treats genesis as strictly one-shot: any second
call for an already-initialized `project_id` raises `AlreadyInitializedError`, with no body
comparison of its own. `bind_project` draws the identical-replay/conflicting-replay
distinction over the Store's own existing, generic read surfaces
(`load_current`/`resolve_record`/`resolve_transaction_manifest`) -- never a second
persistence mechanism, and never any Binding-specific comparison logic added to the Store
itself.

Round 1's own version of this read the Store's private on-disk recovery-journal layout
directly (`state/recovery/TX-GENESIS/manifest.json`), which 構造参謀's Round 2
re-observation correctly found inappropriate for a module whose own Store parameter is
typed `Any` -- Binding has no business knowing the Store's internal file layout. Round 2
adds one minimal, generic, Binding-agnostic public method to `FileStateStore` itself,
`resolve_transaction_manifest(project_id, transaction_id) -> list[tuple[str, str]] | None`,
mirroring `resolve_transaction`'s own existing committed-boundary gate -- `bind_project` now
reads the manifest through this public API, never the private path.

The comparison covers the **full** atomic manifest -- every member the genesis transaction
actually adopted (Objective Revision, Authority Rule, Project Binding, and every
`additional_genesis_records` member), not merely three named records. It is
order-independent (a replay supplying `additional_genesis_records` in a different order is
still a no-op).

**Corrected in Phase 9 Structural Review Round 3 (P9-R3-F1).** Round 2's own claim directly
above this correction -- that two *identical* bodies claimed under one `(kind, id)` "collapse
harmlessly" -- was itself SHUKOU's own ratified finding: `IDENTICAL_DUPLICATE_ALLOWED=false`,
`DUPLICATE_BODY_EQUALITY_IRRELEVANT=true`. The SECOND appearance of any `(kind, id)` in one
candidate manifest is now refused outright, whether its body is identical to or differs from
the first -- `admission.admit_genesis_transaction` walks the candidate as an ordered list and
rejects on the second occurrence of any key, *before* ever folding it into a set for
order-independent comparison (`MANIFEST_MULTIPLICITY_MUST_BE_VALIDATED_BEFORE_SET_
NORMALIZATION=true`). This applies uniformly at every boundary: the very first `bind_project`
call, a caller-supplied replay candidate, and (as a tamper-detection fail-safe)
`FileStateStore.resolve_transaction_manifest`'s own read of an already-committed manifest.

**Also corrected in Round 3 (P9-R3-F2).** `resolve_transaction_manifest` (and
`resolve_transaction`) previously took the literal transaction-id string `TX-GENESIS` as
sufficient commit evidence for the bare-genesis institution, which made a project for which
`initialize` was *never called at all* indistinguishable from one whose bare genesis
legitimately committed with zero records -- both incorrectly returned `[]`.
`TRANSACTION_ID_STRING_NE_COMMIT_EVIDENCE=true`: the Store now additionally requires the
lineage log itself to durably carry the bare genesis's own event before reporting it
committed, so a never-initialized project correctly reports `None` from both public read
surfaces, agreeing with each other (`PUBLIC_TRANSACTION_READ_SURFACES_MUST_AGREE=true`) at
every crash-injection stage.

```text
IDENTICAL_REPLAY_IS_NO_OP=true       (byte-identical Objective Revision, Authority Rule,
                                       Project Binding, genesis State, and every
                                       additional_genesis_records member, any order ->
                                       the already-committed result, no new write)
CONFLICTING_REPLAY_REJECTED_BEFORE_WRITE=true   (a missing, extra, wrong-kind, or
                                                  same-kind/id-different-body member ->
                                                  AlreadyInitializedError re-raised,
                                                  nothing new persisted)
IDENTICAL_DUPLICATE_IS_REJECTED=true      (Round 3 correction -- superseding Round 2's
                                            "collapses harmlessly" claim above)
DUPLICATE_MANIFEST_MEMBER_ACCEPTED=false
MANIFEST_MULTIPLICITY_PRESERVED=true      (validated before, not merely alongside, order-
                                            independent set normalization)
NONEXISTENT_TRANSACTION_NE_EMPTY_COMMITTED_TRANSACTION=true
PUBLIC_TRANSACTION_READ_SURFACES_MUST_AGREE=true
FULL_MANIFEST_REPLAY_COMPARED=true
BINDING_ROUTE_READS_STORE_PRIVATE_PATH=false
```

**Corrected in Phase 9 Completion Repair 5 (P9-C5-F1).** An interim heuristic (Completion
Repair 4, P9-C4-F2) had distinguished a genuine bare genesis from a genesis-with-records
transaction whose recovery journal was lost by scanning whether any *other* transaction's
manifest still claimed the same record -- and that heuristic was itself defeated the moment
a later, otherwise-legitimate transaction reclaimed the identical `(kind, id, body)` under
its own still-intact manifest, making the genuinely-tampered genesis look un-orphaned again.
The Store no longer infers the genesis institution from any such circumstantial evidence.
`FileStateStore.initialize` now writes one explicit, durable genesis institution receipt
(`state/genesis_receipt.json`, outside the recovery journal so it survives the journal's own
deletion) declaring `genesis_mode` (`BARE`/`WITH_RECORDS`) and, for `WITH_RECORDS`, the exact
manifest membership's own digest and count. A genesis-with-records transaction whose journal
is later deleted or tampered now raises `CorruptStoreError` from `resolve_transaction`,
`resolve_transaction_manifest`, `load_current`, and `reconstruct` alike -- a stronger,
more definite failure than the interim heuristic's own `None`/`[]` -- while `bind_project`'s
own replay comparison is unaffected, since it only ever reads an already-committed genesis
through these same public surfaces.

```text
GENESIS_INSTITUTION_HEURISTIC_INFERENCE_IS_AUTHORITY=false
GENESIS_INSTITUTION_RECEIPT_IS_AUTHORITY=true
GENESIS_RECEIPT_SURVIVES_JOURNAL_DELETION=true
LATER_RECORD_RECLAIM_DEFEATS_HEURISTIC_DETECTION=false
```

**Corrected in Phase 9 Completion Repair 6 (P9-C6-F1).** A schema-valid, internally
self-consistent genesis receipt was itself not yet canonical: an attacker who deleted a
genesis-with-records transaction's own recovery journal and replaced its receipt with a
schema-valid, self-consistent `BARE` receipt (correct `project_id`/`transaction_id`, the
canonical empty manifest, and a `genesis_receipt_id` freshly, correctly recomputed from
those very fields) still fooled every public read surface, since the receipt was never
checked against anything external to itself. The receipt now carries a content-addressed
`genesis_receipt_id` (`GENESIS-RECEIPT-<sha256 hex>`, its own distinct domain separator
from both State's fingerprint and the manifest digest, excluded from its own preimage),
and the GENESIS event `FileStateStore.initialize` durably commits to the lineage log at
genesis time now carries a `genesis_receipt_ref` naming that exact id -- required by
schema for `event_type=GENESIS`, forbidden for `TRANSITION`. Since the lineage log is
immune to a deleted recovery journal, a substituted receipt's own (different, but
internally correct) recomputed id can never reproduce the original event's own durable
reference, so the substitution still fails closed. `bind_project`'s own replay comparison
remains unaffected, unchanged from Completion Repair 5.

```text
GENESIS_RECEIPT_SELF_DECLARATION_IS_AUTHORITY=false
GENESIS_RECEIPT_CONTENT_ADDRESSED=true
GENESIS_RECEIPT_EXTERNALLY_COMMITTED=true
SCHEMA_VALID_GENESIS_RECEIPT_SUBSTITUTION_ALLOWED=false
```

## 9b. Whole-graph admission (Round 2 P9-R2-F1/F2/F3/F5)

**Added in Phase 9 Structural Review Round 2.** Round 1's own secret-scan and reference
classification covered only the Project Binding record itself
(`assemble_project_binding`'s own internal checks). 構造参謀's Round 2 re-observation found
this insufficient: `bind_project` also accepts and persists Objective Revision, Authority
Rule, genesis State, and every `additional_genesis_records` member, none of which were
scanned or reference-checked at all -- a secret-shaped value in an Objective Revision's own
free-text field, or a genesis State naming a dangling Kernel Source Snapshot, passed
silently.

`manosube_agent_civilization.binding.admission.admit_genesis_transaction` is now the one
shared pre-commit admission every accepted body passes through, before `store.initialize`
is ever called:

0. closed additional-genesis-record kind allowlist + schema/identity reverification for
   every `additional_genesis_records` member (Round 3, P9-R3-F3 -- see below);
1. duplicate `(kind, id)` detection across the candidate manifest -- the second appearance
   of any key is refused, whether identical to or different from the first (Round 3,
   P9-R3-F1 -- see §8);
2. secret-value and moving-reference scanning over the **whole** candidate genesis manifest
   (Objective Revision, Authority Rule, Project Binding, genesis State, every
   `additional_genesis_records` member) -- `difference.canonical.reject_secret_material`
   reused, never restated;
3. typed reference-edge classification and closure over that same whole candidate manifest,
   scoped to the candidate manifest only, never an existing Store record -- see §10.

```text
SECRET_SCAN_COVERS_WHOLE_ACCEPTED_GRAPH=true
CANONICAL_BINDING_PRECOMMIT_ADMISSION_OWNER_COUNT=1
EVERY_PERSISTED_BODY_PASSES_SHARED_ADMISSION=true
ALL_VALIDATION_PRECEDES_STORE_INITIALIZE=true
```

**Added in Phase 9 Structural Review Round 3 (P9-R3-F3): closed additional-record kind
allowlist.** Before this round, any caller-supplied `kind` in `additional_genesis_records`
whose value happened to be recognized by Reflow's own `reference_registry` received a
reference-edge check, but a kind Reflow's registry did *not* recognize was persisted
verbatim -- schema-unchecked, identity-unverified, arbitrary caller-controlled data adopted
into the Store as a real record.

`admission.ADDITIONAL_GENESIS_RECORD_KIND_VERIFIERS` is now a closed allowlist; the only
kind any real Phase 9 genesis fixture or existing State contract actually requires is
`source_snapshot` (genesis State's own `state_metadata.source_snapshot_refs` is the sole
reference genesis closure needs an additional record for). Each allowed kind's own verifier
reuses that kind's real, existing schema owner and real, existing content-addressed identity
function (`observation.source_snapshot.source_snapshot_identity` for `source_snapshot`) --
never a second identity algorithm invented in this module -- and cross-checks the recomputed
identity against both the caller-supplied tuple `record_id` and the body's own declared id
field.

```text
ADDITIONAL_GENESIS_RECORD_KIND_SET=CLOSED
UNKNOWN_ADDITIONAL_GENESIS_RECORD_KIND_ALLOWED=false
EVERY_ALLOWED_ADDITIONAL_KIND_SCHEMA_VERIFIED=true
EVERY_ALLOWED_ADDITIONAL_KIND_IDENTITY_REVERIFIED=true
CALLER_SUPPLIED_CANONICAL_BODY_TRUSTED=false
```

## 10. Typed reference classification

**Added in Phase 9 Structural Review Round 1 (P9-R1-F5), extended in Round 2 (P9-R2-F2/
F3).** Round 1 classified only Project Binding's own three top-level reference fields.
構造参謀's Round 2 re-observation found this incomplete: Objective Revision, Authority Rule,
and genesis State each carry their own reference fields that were never classified at all
-- most importantly, genesis State's own `state_metadata.source_snapshot_refs` (its real
Kernel Source Snapshot) and `evidence_refs`, left completely unchecked, so a dangling
Source Snapshot reference at genesis passed silently.

`manosube_agent_civilization.binding.reference_classification` now classifies every
reference field on every record kind `bind_project` accepts, keyed
`(source_record_kind, field_path)` -- pattern-compatible with, but organizationally
separate from, `reflow/reference_registry.py` (a different domain's own vocabulary, never
repurposed as this one's owner; `additional_genesis_records` members whose kind Reflow's own
registry already recognizes delegate to that registry instead of a second, duplicated
field/path table):

```text
source_kind          field                     expected kind(s)          classification
project_binding      objective_revision_ref    objective_revision        Store-owned
project_binding      authority_policy_ref      authority_rule            Store-owned
project_binding      human_authority_ref       human_authority           external
objective_revision   owner_authority_ref       human_authority           external
objective_revision   human_authority_ref       human_authority           external
objective_revision   boundary_ref              objective_boundary        no Store producer
objective_revision   previous_objective_ref    objective_revision        Store-owned
authority_rule       declared_by               human_authority           external
project_state        state_metadata.           source_snapshot           Store-owned
                     source_snapshot_refs[]
project_state        state_metadata.           observation_scope         no Store producer
                     observation_scope_refs[]
project_state        evidence_refs[]           observation_evidence,     Store-owned
                                                negative_evidence
project_state        lineage_head_ref          state_transition          (must be null at
                                                                          genesis; see §7)
```

`objective_revision.owner_authority_ref` is classified as the Human Authority kind on the
existing Kernel contract's own authority (`00_KERNEL/01_OBJECTIVE/OBJECTIVE_CONTRACT.md`
§"owner_authority_ref resolves to Human Objective Authority") -- no new semantics invented
here. `observation_evidence`/`negative_evidence` are treated as Store-owned specifically so
that a non-empty `evidence_refs` at genesis (state_revision 0, where no Evidence can yet
exist) fails closed as unresolvable, rather than silently passing unchecked.

**Corrected in Phase 9 Structural Review Round 3 (P9-R3-F4): classification alone is not
identity equality.** The table above proves `owner_authority_ref` carries the right *kind*
(`human_authority`), but Round 1/Round 2 never checked whether its *id* actually matched the
Binding's own declared Human Authority -- a caller could substitute a different, still
correctly-kinded, `human_authority` id there undetected. `bind_project` now additionally
requires all four of `project_binding.human_authority_ref`,
`objective_revision.owner_authority_ref`, `objective_revision.human_authority_ref`, and
`authority_rule.declared_by` to be the *identical* canonical reference (see
`TRUST_MODEL.md` §2b) -- kind correctness (this table) and identity equality (that check) are
separate invariants, and both are now enforced.

```text
HUMAN_AUTHORITY_REFERENCE_COUNT_CROSS_CHECKED=4
HUMAN_AUTHORITY_FOUR_WAY_EQUALITY=true
```

**Ratified in Phase 9 Structural Review Round 3 (P9-R3-F5): reference resolution scope.**
Every Store-owned edge above must resolve against the current candidate genesis manifest --
there is nothing else to resolve against, since genesis means no record for this
`project_id` exists in the Store yet (stated already, unchanged, at the end of this
section). SHUKOU's Round 3 adoption formally ratifies this as the permanent semantic, not
merely an implementation detail: a Store-owned reference genesis declares must resolve
within THIS genesis transaction's own atomic manifest, never against a pre-existing Store
record -- even one with an identical `(kind, id, body)` already committed under this same
`project_id` from an earlier ordinary commit, and never across `project_id` namespaces. A
replay's own reference resolution is scoped identically to its own exact original genesis
manifest (see §8) -- never the current Store's full contents.

```text
FIRST_BINDING_REFERENCE_RESOLUTION_SCOPE=CURRENT_ATOMIC_GENESIS_MANIFEST_ONLY
PREEXISTING_SAME_PROJECT_RECORD_AS_FIRST_BINDING_INPUT_ALLOWED=false
GENESIS_REFERENCE_TO_PREEXISTING_STORE_RECORD_ALLOWED=false
REPLAY_REFERENCE_RESOLUTION_SCOPE=EXACT_ORIGINAL_GENESIS_MANIFEST
```

`reject_wrong_kind_reference`/`reference_edges` run before any Store lookup: a reference
whose own `kind` is not the one closed kind its field permits is refused, never silently
accepted or narrowed to whatever kind happened to be there
(`CROSS_KIND_SUBSTITUTION_ALLOWED=false`). Every Store-owned edge must resolve against the
current candidate genesis manifest -- there is nothing else to resolve against, since
genesis means no record for this `project_id` exists in the Store yet.
`resolve_binding_references` recursively resolves Project Binding's own Store-owned fields
against a real Store, proving `UNRESOLVED_STORE_OWNED_REFERENCE_COUNT=0` from both a fresh
Store instance and a fresh process.

```text
PRODUCT_BINDING_REFERENCE_CLASSIFICATION_COMPLETE=true
WRONG_KIND_REFERENCE_ACCEPTED=false
UNRESOLVED_STORE_OWNED_REFERENCE_ACCEPTED=false
GENESIS_DANGLING_CANONICAL_REFERENCE_ALLOWED=false
```

## 9. Explicit non-claims

```text
FILESYSTEM_READ_PERFORMED=false
SOURCE_REGISTRATION_GRANTS_AUTHORITY=false
COMMAND_POLICY_GRANTS_AUTHORITY=false
COMMAND_EXECUTION_PERFORMED=false
SECRET_VALUE_PERSISTED=false
```

## 11. Human Grant Declaration (Phase 13, Issue #51, Structural Review Round 5, P13-R5)

`bind_project` is not the only public route this domain exposes. `declare_human_grant`
(`binding/route.py`) is a second, independent public entry point, committing a new record
kind -- `human_grant_declaration` (`01_SCHEMA/binding/human_grant_declaration.schema.json`)
-- into an already-bound project, arbitrarily long after genesis. It is not a second genesis
route: it calls the Store's ordinary `store.commit`, never `store.initialize`, so §8's own
one-shot-genesis discipline (`AlreadyInitializedError`,
`PUBLIC_COMMITTING_ROUTE_COUNT=1` -- the count of routes reaching `store.initialize`) is
unaffected -- `declare_human_grant` is simply outside that invariant's own scope, exactly as
`reflow()`'s own post-genesis commits already are for the Reflow vertical.

`declare_human_grant` exists to answer a question Authority's own Independent Verification
layer (`08_VERIFICATION/VERIFICATION_CONTRACT.md` §12) cannot answer by itself: a
`verifier_selection_grant` that is genuinely, durably Store-committed, self-consistent, and
correctly `granted_by`-shaped is still not, by itself, proof that a **Human** (as opposed to
any Store-write-capable caller) declared *that specific grant*. `human_grant_declaration`
closes this by anchoring one grant (via `grant_ref`, a content-addressed reference to the
grant's own `verifier_selection_grant_id`) to a Human identity this Binding owner itself
re-resolves, never accepts as a caller argument:

```text
BINDING_OWNER:
  declare_human_grant independently re-resolves the real, already-committed Project Binding
  from the Store (never a caller-supplied copy) and derives the declaration's own
  declared_by from that Project Binding's own human_authority_ref -- the identical
  never-trust-a-caller-repeated-reference discipline §7's own cross-consistency checks
  already apply to every other Binding-accepted input.
AUTHORITY_OWNER:
  evaluate_verifier_selection (AUTHORITY_CONTRACT.md §7.3's Round 5 addendum) reads
  human_grant_declaration records read-only, cross-checking a candidate grant's own
  project_id/grant_ref against each declaration's anchor, its declared_by against the real
  Human Authority reference, and its status against ACTIVE -- Authority never writes a
  human_grant_declaration record, and Binding never evaluates a Verifier Selection Decision.
```

**Superseded by Structural Review Round 5-R1 (Issue #51, P13-R5-R1,
`ADOPT_P13_R5_R1_SIGNED_HUMAN_DECLARATION_AND_SINGLE_COMMITTER`).** Round 5's own original
design (immediately above, as originally written) held that `grant_ref` alone anchors every one
of the grant's own semantic fields completely, so restating them would be a redundant copy, not
a second binding. SHUKOU's own follow-on structural review explicitly overruled this: a
declaration's own durable Store commission and self-consistent, correctly-anchored shape still
never proved a **Human**, rather than any Store-write-capable caller, authored it --
`human_authority_ref` is not a secret. The only thing that closes this is a Human's own
verifiable signature, and a signature is only as meaningful as the payload it actually covers --
a signature over a payload that names another record only by hash is a weaker attestation than
one that directly covers the semantic content itself. `human_grant_declaration` therefore now
directly restates the anchored grant's own `requirement_id`/`selection_id`/`verifier_identity`/
`permitted_boundary` (never `project_id` a second time under a different name -- the top-level
`project_id` field already serves that role), and Authority independently re-verifies that this
restatement agrees with the real, resolved grant's own matching fields
(`AUTHORITY_CONTRACT.md` §7.3's Round 5-R1 addendum) -- never merely trusting `grant_ref`'s
content address as sufficient. This does not reopen the opaque-payload-location concern Round
3's own totality-sweep discipline exists to keep closed: the restated `verifier_identity`/
`permitted_boundary` locations are registered in `difference.admissibility.
UNCONSTRAINED_CONTRACT_LOCATIONS` exactly as their `verifier_selection_grant`-owned
counterparts already are.

Project Binding itself now canonically holds a public verification key,
`human_authority_signing_key` (`01_SCHEMA/binding/project_binding.schema.json#/$defs/
signing_key`: `{algorithm: "ed25519", key_id, public_key}`) -- never a secret; the Human's own
private key never touches this system's code. `human_grant_declaration` carries a `signature`
(`{algorithm: "ed25519", key_id, value}`) over its own complete adopted payload -- every field
`human_grant_declaration_id` itself addresses, `declared_at` included (see below) -- verified
read-only against the real Project Binding's own signing key, both here
(`binding/engine.py::assemble_human_grant_declaration`, via `binding/signature.py::
verify_declaration_signature`) and, independently, by Authority
(`AUTHORITY_CONTRACT.md` §7.3's Round 5-R1 addendum) before a grant may ever reach `SELECTED`.

```text
HUMAN_GRANT_DECLARATION_DECLARED_BY_CALLER_SUPPLIED=false
HUMAN_GRANT_DECLARATION_GRANT_FIELDS_RESTATED=true
HUMAN_GRANT_DECLARATION_SIGNATURE_REQUIRED=true
HUMAN_GRANT_DECLARATION_SIGNATURE_ALGORITHM=ed25519
HUMAN_GRANT_DECLARATION_PRIVATE_KEY_TOUCHES_PRODUCTION_CODE=false
HUMAN_GRANT_DECLARATION_STATUS=ACTIVE | REVOKED
```

This record, like every other canonical record this domain persists, is content-addressed
(`HGD-` + sha256 of its own adopted payload, excluding its own id and `signature` --
`binding/identity.py::human_grant_declaration_id`) and reverified against that same address
before it is ever validated against its own schema (`binding/engine.py::assemble_human_grant_
declaration`) -- the identical self-consistency discipline §3 already establishes for
`project_binding_id` itself. Unlike `project_binding_id` (which excludes `bound_at`) and Round
5's own original design (which excluded `declared_at`), the identity payload now **includes**
`declared_at` (Round 5-R1): the signature is what proves *who* declared this, and a signature
that never bound *when* would validate identically at any later replay instant. The identity
payload and the signed message are one shared derivation
(`binding/identity.py::human_grant_declaration_signing_payload`), so "what this record adopted"
and "what the signature authenticates" can never drift apart.
