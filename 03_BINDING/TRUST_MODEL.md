# Trust Model (Phase 9, Issue #43)

```text
DOC_TYPE=TRUST_MODEL_CONTRACT
DOCUMENT_ID=BINDING-TRUST-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PRODUCT_BINDING_LAYER
```

## 1. Human declaration is authoritative input

The Binding engine validates an explicit Human-supplied declaration. It does not infer the
project's meaning from repository contents, paths, or GitHub information, and it does not
silently trust anything not present in the declaration itself.

```text
HUMAN_DECLARATION_IS_AUTHORITY=true
PROJECT_MEANING_INFERRED_FROM_ENVIRONMENT=false
```

## 2. Authority policy resolves to a real, persisted body

**Corrected in Phase 9 Structural Review Round 1 (P9-R1-F1).** The design this section
originally described -- `authority_policy_ref` staying reference-only, never resolved
against a Store record, mirroring Reflow's own `authority_decision`/`objective_revision`
treatment -- was found insufficient: a Binding's own claim to operate under a given
Authority policy is not provable if that policy is never itself a real, checkable body.

`bind_project` now accepts the real Authority Rule body `authority_policy_ref` names,
validates it against Authority's own existing schema (`01_SCHEMA/authority/
authority_rule.schema.json`, never restated here), reverifies its identity via Authority's
own existing `authority.identity.rule_id` (never a second identity algorithm), requires its
own `project_id` to equal the Binding's, requires its own `declared_by` to canonically
equal the Binding's `human_authority_ref`, and persists it as a Store-owned record
(`kind="authority_rule"`) in the same atomic `TX-GENESIS` manifest as the Project Binding
and Objective Revision -- see `PROJECT_BINDING.md` §5b.

```text
SOURCE_REGISTRATION_GRANTS_AUTHORITY=false
AUTHORITY_POLICY_REFERENCE_RESOLVED_AGAINST_STORE=true
AUTHORITY_RULE_SECOND_PRODUCER=false
AUTHORITY_RULE_SECOND_IDENTITY_ALGORITHM=false
```

A missing, wrong-kind, shape-ambiguous, schema-invalid, non-reproducing-identity, or
project/declarer-mismatched `authority_policy_ref`/`authority_rule` fails validation before
any commit -- see `PROJECT_BINDING.md` §5b and the negative controls in
`tests/integration/binding/test_project_binding_route.py`.

Human Authority itself is unaffected by this correction and keeps its own, separate
position: `human_authority_ref` is an external constitutional identity, never a Store
record of its own kind (`HUMAN_AUTHORITY_STORE_RECORD_REQUIRED=false`) -- only
cross-consistency between its four declared appearances (Project Binding, Objective
Revision's two fields, Authority Rule) is enforced, per §2b.

## 2b. Four-way Human Authority cross-match

**Added in Phase 9 Structural Review Round 1 (P9-R1-F2) as a three-way check; extended to
four in Phase 9 Structural Review Round 3 (P9-R3-F4).** Round 1/Round 2 enforced
`human_authority_ref` (the Binding's own) == `objective_revision.human_authority_ref` ==
`authority_rule.declared_by`, but left `objective_revision.owner_authority_ref` checked for
*kind* correctness only (`reference_classification.py`'s own closed-kind gate) -- never for
*identity* equality. A caller could declare a different, but still correctly-kinded,
`human_authority` id there and nothing rejected it; kind correctness and identity equality
are separate invariants, and only the first was enforced.

`bind_project` now requires all four canonical references to be identical (`{kind, id}`
exact equality, ``CANONICAL_REFERENCE_EXACT_EQUALITY_REQUIRED=true``):

```text
project_binding.human_authority_ref
== objective_revision.owner_authority_ref
== objective_revision.human_authority_ref
== authority_rule.declared_by
```

Objective's own existing contract (`00_KERNEL/01_OBJECTIVE/OBJECTIVE_CONTRACT.md`
§"owner_authority_ref resolves to Human Objective Authority") already settles
`owner_authority_ref`'s semantic as the Human Authority kind -- this correction reuses that
existing decision rather than inventing a new one.

```text
THREE_WAY_HUMAN_AUTHORITY_CROSS_MATCH_ENFORCED=true (Round 1, superseded below)
HUMAN_AUTHORITY_FOUR_WAY_EQUALITY=true
HUMAN_AUTHORITY_KIND_CORRECTNESS=true
HUMAN_AUTHORITY_IDENTITY_EQUALITY=true
CANONICAL_REFERENCE_EXACT_EQUALITY=true
```

## 3. Source Registration declares trust; it does not observe

Registering a source is a declaration that it is trusted material within the Boundary. It
creates no Observation, Evidence, Difference, Change, or Authority of its own -- see
`SOURCE_REGISTRATION.md`.

## 4. Moving references are rejected

Every reference this domain accepts is walked (`difference.canonical.walk_references`,
the same repo-wide primitive Reflow's own admission paths reuse) and any identity matching
a moving-pointer shape (`HEAD`, `LATEST`, `CURRENT`, ...) is refused -- an immutable
Binding cannot cite a target that could silently move underneath it.

## 5. A Human Grant Declaration anchors provenance without a secret (Phase 13, Issue #51,
## Structural Review Round 5, P13-R5)

Independent Verification's own Authority-owned check (`AUTHORITY_CONTRACT.md` §7.3) needed a
way to distinguish "a Human declared this specific `verifier_selection_grant`" from "some
Store-write-capable caller committed a record that merely repeats a real `human_authority_ref`
value" -- durable Store commission alone answers only the latter. This domain's existing,
already-established non-cryptographic trust philosophy (§1/§2's own `HUMAN_AUTHORITY_STORE_
RECORD_REQUIRED=false` position: Human Authority is an external constitutional identity, never
a Store record whose possession could be forged or stolen) is deliberately not abandoned to
answer this -- `declare_human_grant` introduces no signing key, bearer token, or secret of any
kind. It relies on exactly the same structural discipline every other cross-consistency check
in this document already relies on: `declare_human_grant` never accepts `declared_by` as a
caller argument, and instead independently re-resolves it from the real, already-committed
Project Binding's own `human_authority_ref`, the identical never-trust-a-caller-repeated-value
convention §2b's own four-way cross-match already applies. A `human_grant_declaration` record
is therefore never stronger evidence than the Project Binding it was derived from -- it does
not add a new, independent source of Human provenance; it is a second, content-addressed,
explicitly-timestamped assertion, anchored to one specific grant, drawn from the identical
single source of Human identity truth this whole domain already has exactly one of.

```text
HUMAN_GRANT_DECLARATION_INTRODUCES_A_SECRET=false
HUMAN_GRANT_DECLARATION_INTRODUCES_A_SECOND_HUMAN_IDENTITY_SOURCE=false
HUMAN_GRANT_DECLARATION_DECLARED_BY_CALLER_SUPPLIED=false
```

See `PROJECT_BINDING.md` §11 for the record's own shape and `AUTHORITY_CONTRACT.md` §7.3's
Round 5 addendum and `08_VERIFICATION/VERIFICATION_CONTRACT.md` §12 for how Authority and
Independent Verification each consume it, read-only.
