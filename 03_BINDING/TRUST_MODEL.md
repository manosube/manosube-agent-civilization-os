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

## 2. Authority stays reference-only

`authority_policy_ref` is a caller-declared typed reference (`{kind: "authority_rule",
id}`), checked structurally (const `kind`, id pattern) and never resolved against a Store
record -- the identical treatment `reflow/reference_registry.py`'s own inventory already
gives `authority_decision`/`objective_revision`: canonical-reference equality against
caller input, never a second Store-owned kind.

```text
SOURCE_REGISTRATION_GRANTS_AUTHORITY=false
AUTHORITY_POLICY_REFERENCE_RESOLVED_AGAINST_STORE=false
```

A missing, wrong-kind, or shape-ambiguous `authority_policy_ref` fails schema/engine
validation before any commit -- see `PROJECT_BINDING.md` §2 and the negative controls in
`tests/integration/binding/test_project_binding_route.py`.

## 3. Source Registration declares trust; it does not observe

Registering a source is a declaration that it is trusted material within the Boundary. It
creates no Observation, Evidence, Difference, Change, or Authority of its own -- see
`SOURCE_REGISTRATION.md`.

## 4. Moving references are rejected

Every reference this domain accepts is walked (`difference.canonical.walk_references`,
the same repo-wide primitive Reflow's own admission paths reuse) and any identity matching
a moving-pointer shape (`HEAD`, `LATEST`, `CURRENT`, ...) is refused -- an immutable
Binding cannot cite a target that could silently move underneath it.
