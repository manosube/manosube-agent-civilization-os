# ADR-0025 — Declare the input grammar, then own admissibility once

**Status:** accepted
**Supersedes nothing. Bounds:** ADR-0013 §1, ADR-0022 §7, ADR-0023 §1.

## 0. Why three fixes would have been the wrong answer

Three findings arrived against `5d9f407`:

```text
risk_class = []                                       unhashable, reached a frozenset test
closure_policy_requirements.allowed_terminal_states    malformed, reached `sorted`
expected_value = {"value_type": [], "value": "..."}    unhashable, reached a wrapper test
```

Each is one line. Correcting each where it was reported would have taken minutes, and it is
what rounds 17–24 did — every round closing the case in front of it while the next layer
stayed open. The question worth answering is not what these three lines do. It is **why a
7770-case mutation sweep, built specifically to make this class impossible, produced no case
for any of them.**

## 1. The answer, and it is structural

A mutation sweep enumerates the locations a fixture instantiates and the substitutions a
harness lists. So:

- **an optional key the fixture omits has no case at all.** `risk_class` is absent from
  every committed fixture. The fixture supplies exactly one key of
  `closure_policy_requirements`, so the other four have no case either.
- **a domain-shaped value a fixed substitution set cannot express has no case.** The
  substitutions are `{int, str, list, dict, null}` in five fixed values; none of them is
  `{"value_type": [], "value": "READY"}`.

That is the fourth distinct instance of this shape (ADR-0022 §1 records three), and it is
why every one of these findings arrived by review rather than by measurement. **A location
omitted from a fixture cannot count as covered, and a fixed sentinel set cannot be called
total.** So the order here is inverted: declare the grammar first, generate from the
declaration, and only then fix.

## 2. The grammar has three declaration sources, and one of them was empty

| Source | What it declares | State on `5d9f407` |
| --- | --- | --- |
| `01_SCHEMA/**/*.schema.json` | the embedded records | complete, and enforced |
| the same schemas, `{}` properties | 8 locations constrained by nothing | undeclared here |
| the request envelope itself | required and optional keys | **nowhere** |

The third row is the finding behind the findings. No file under `00_KERNEL/` or `01_SCHEMA/`
declares the derivation request envelope — it is this Issue's own input interface
(`DERIVATION_INPUT_INTERFACE_EXTENDED`). `engine` stated its *required* keys; nothing stated
the optional ones, and an input location no declaration mentions is a location no harness
can generate a case for.

`difference/admissibility.py` now declares it, and
`tests/contract/difference/test_request_grammar_inventory.py` holds the declaration to the
producer's own read sites **in both directions**: a declared key the producer never reads
fails, and a key the producer reads that nothing declares fails. Only the second direction
would have caught these findings, and only the second direction is new.

The eight unconstrained schema locations are derived from the schema files by the same test,
also in both directions, and classified `INPUT` or `EMITTED`. The two `INPUT` locations are
generated against with contract-shaped payloads — typed wrappers, collection wrappers,
references — because those are the shapes the contract gives meaning to and a scalar
substitution set cannot express.

**What is not done, deliberately.** The request key set is **not** closed: an unknown
top-level key is still ignored, and a test pins that behaviour by name. Enumerating the
grammar enforces the interface the producer already accepts; rejecting a key it used to
accept would change that interface, which is a contract decision and not this Issue's to
make. No request JSON schema is introduced, and no embedded record is re-validated.

## 3. What the inventory found before any fix was written

A fifth instance, at a location no fixture instantiates and no review reported:
`canonical.reject_bare_arrays` hashed a collection wrapper's `collection_kind` one line
before the check written to reject it. It appeared on the inventory's first run. That is the
evidence that building the inventory before writing the fixes was the load-bearing step, and
not process for its own sake.

## 4. One owner, and the two forms a caller needs

`difference.admissibility` answers one question — *can this raw value bear the operation
about to be applied to it* — and it answers in two forms, because two kinds of caller ask it:

- `require_object` / `require_collection` / `require_scalar_tag` **reject**, for a caller
  whose contract says the value must bear the shape;
- `is_canonical_object` / `is_collection` / `is_scalar_tag` **answer**, for a caller whose
  contract says another shape means something else — an object that is not a declared typed
  wrapper is an ordinary structured value, compared whole. Rejecting it would have been the
  `STRUCTURED` category error again, in reverse.

Measured at `5d9f407`, **21** rejections were written as a negated `dict`/`list`/`str` type
test outside the owner — `engine` 16, `canonical` 2, `conformance` 1, `predecessor` 1,
`selection` 1. All 21 now delegate, and the count is **0**. Two membership tests in
`projection` and one in `canonical` were the same question asked positively, and delegate
too. `readability` (ADR-0023) held its own `isinstance` copies of two of these predicates;
they are now aliases of the owner's — one object, so two owners cannot drift into two
answers.

Where a caller's own diagnosis is better than the owner's — *"observation bundle omits a
canonical section"* says what a caller needs told, and *"is not a canonical collection"* does
not; *"carries no canonical bindings"* deliberately answers the same way for a non-list and
for an empty list — the caller keeps its message and takes the predicate form. Owning the
decision was never the same as owning the sentence, and three existing tests asserting those
sentences are unchanged.

`tests/contract/difference/test_admissibility_authority.py` holds this in both directions.
The second direction is a source scan: **any rejection written as a negated `dict`/`list`/
`str` type test, anywhere under `difference/`, outside the owner, fails.** It is coarse on
purpose, for the reason ADR-0023 gives — counting call sites after the fact is what let the
readability split happen. A negated `int` test is left alone: *"a State revision is a
non-negative integer"* is a value-domain rule this owner does not decide, and the scan says
so rather than sweeping it into an exemption list.

## 5. The two owners do not overlap

`readability` (ADR-0023) answers whether a **typed canonical record** can be read as that
type. `admissibility` answers whether a **raw request value** can bear an operation. The
first is a consumer of the second, not a second answer to it. Neither was merged into the
other, and no gate calls both for the same question.

## 6. What is still not claimed

`INPUT_TOTALITY_PROVEN` stays **false**, for the reasons ADR-0022 §7 gives and one more of
its own: this inventory bounds the request *envelope* and the schema-unconstrained *payload*
locations. It is not a proof over the embedded records — those keep their schemas and the
sweep — and its adversarial variant set is a set, which is exactly the thing this ADR says
cannot be called total. What changed is not that the input space is closed. It is that the
part of it no fixture instantiates is now generated from a declaration instead of being
invisible.
