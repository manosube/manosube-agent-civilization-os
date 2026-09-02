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
`tests/contract/difference/test_request_grammar_inventory.py` **generates from that
declaration**: every declared request and binding key becomes a case that runs the public
`derive_differences` route and must be answered. An optional key the fixtures omit therefore
has cases, which is the whole of what the findings turned on.

The first version of that file also compared the declaration against the producer's Python
read sites and called the comparison complete in both directions. That claim is withdrawn;
§6 records why, and it is the only claim removed — the generated coverage is unchanged.

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

## 6. The static read-site proof is withdrawn, not repaired

The inventory originally made two claims. One is behavioural: every declared input location
becomes a case the public producer must *answer*. The other was static: that the declaration
and the producer's Python read sites match completely in both directions, established by
parsing `engine.py`. **Only the first survives.**

The static half failed twice, in the same way, in the instrument written to eliminate that
exact way:

```text
b65ad30   assert f'"{key}"' in source      a literal search cannot tell a read from a write
5146ef6   accepts any ast.Subscript        a *store* subscript counted as a read
```

Both were found by review, not by the controls written alongside them — because those
controls all mutate toward *absence*, proving the scanner notices a **removal** and never
that it distinguishes a **read from a write**. The second finding also reached further than
it was reported: the same hole was in `_read_sites_in`, the scan behind every comparison in
the file, not only in the delegation branch.

A third repair was available and is not being made. `isinstance(node.ctx, ast.Load)` is one
line in each scanner, and the reason to decline it is not the line — it is that the
scanner's own correctness had become a second verification problem stacked on the first,
with each round's fix authored by the same hand that missed the previous channel. That is
the non-convergent loop this branch has been in, and repairing the proof once more would
have extended it rather than ended it.

**Nothing downstream depended on the static half.** The v0.1 contract requires deterministic
Difference behaviour, schema and version conformance, single semantic owners, evidence, and
one full natural cycle. It does not require Python-AST read-site totality, and `scripts/` is
a Verification Utility rather than a hidden contract authority. Every finding this branch
has fixed was ever about one thing: **whether the public producer answers for a declared
input.** Running `derive_differences` settles that; reading its source does not.

So the machinery is removed — `DELEGATED_PROVEN`, the read-site scan, the call-following,
the exemption mechanism and the five controls that existed only to prove them — along with
every statement calling it a complete bidirectional contract proof.

```text
STATIC_READ_SITE_TOTALITY_CLAIMED=false
```

What remains is what was doing the work. The declaration in `difference.admissibility`
drives **generation**: every declared request and binding key, the four declared Closure
Policy sets, and the schema-unconstrained payload locations become cases — including the
optional keys no committed fixture instantiates, which is the class that produced the
findings — and each one runs the public route and must be answered. One comparison stays
bidirectional, and it is between two pieces of **data**: the eight properties `01_SCHEMA/**`
declares with `{}`, against the list kept here.

The declaration was accurate at every point in this sequence. What was defective, twice, was
the guard that would have caught it drifting — and the honest response to a guard that keeps
failing in the way it forbids is to stop claiming what it cannot support.

## 7. What is still not claimed

`INPUT_TOTALITY_PROVEN` stays **false**, for the reasons ADR-0022 §7 gives and one more of
its own: this inventory bounds the request *envelope* and the schema-unconstrained *payload*
locations. It is not a proof over the embedded records — those keep their schemas and the
sweep — and its adversarial variant set is a set, which is exactly the thing this ADR says
cannot be called total. What changed is not that the input space is closed. It is that the
part of it no fixture instantiates is now generated from a declaration instead of being
invisible.
