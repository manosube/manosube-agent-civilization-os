"""The single answer to: can this raw derivation request be read at all?

The producer's ordering is

```text
RAW REQUEST -> CONTRACT/SCHEMA-DERIVED ADMISSIBILITY -> READABLE CANONICAL REQUEST
    -> SEMANTIC DERIVATION
```

and until now the second arrow did not exist for most of the request. `_require_request_shape`
established the *required key set*; nothing established that a value about to be **hashed,
sorted, iterated, parsed or used as a mapping key** could bear it. Three findings on
`5d9f407` were that one gap, at three locations:

```text
risk_class = []                      unhashable, reached a frozenset membership test
closure_policy_requirements = {...}  malformed declared collections reached a sort
expected_value.value_type = []       unhashable, reached a wrapper-tag membership test
```

None was reachable by the mutation sweep, and the reason is structural rather than an
oversight: **a sweep enumerates the locations a fixture instantiates.** Two of those three
keys are *optional* and the fixture omits them, so no case for them can exist; the third is
a domain-shaped object the fixed substitution set cannot express. That is the fourth
distinct blind spot of the same kind, so the answer here is a declared grammar rather than
three more guards.

**What this module does not do.** It does not close the request key set -- an unknown key is
still ignored, exactly as before, because rejecting one would change the producer's accepted
interface rather than enforce it. It does not introduce a request JSON schema; the embedded
records keep the schemas they already have, and this module never re-validates them. It
answers structural admissibility and nothing else: a value that is readable and *wrong*
keeps its own diagnosis, per ADR-0013.
"""

from __future__ import annotations

from typing import Any, TypeGuard

from .errors import DifferenceError

# --------------------------------------------------------------------------- #
# The declared grammar
# --------------------------------------------------------------------------- #
#
# The derivation request is this Issue's own input interface: no file under ``00_KERNEL/``
# or ``01_SCHEMA/`` declares the envelope, which is recorded as
# ``DERIVATION_INPUT_INTERFACE_EXTENDED``. The embedded records keep their own schemas; what
# had no declaration anywhere was the envelope around them, and an input location that no
# declaration mentions is a location no harness can generate a case for -- which is exactly
# how two of the three findings stayed invisible to a 7770-case sweep.
#
# So the envelope grammar is declared here, once, and `tests/contract/difference/
# test_request_grammar_inventory.py` holds it to the producer's own read sites in *both*
# directions: a declared key the producer never reads fails, and a key the producer reads
# that is declared nowhere fails.

#: Every top-level request key the derivation reads before it can validate anything.
#: Absent, each raised an incidental ``KeyError`` in place of the canonical rejection.
REQUIRED_REQUEST_KEYS: tuple[str, ...] = (
    "project_id",
    "objective_revision",
    "state_revision",
    "state_fingerprint",
    "bindings",
)

#: Required, but by ``require_schema_version`` rather than by the shape gate, so it is not
#: in the tuple above. Declared here so the inventory's second direction does not report it
#: as a key the producer reads and nothing declares.
SCHEMA_VERSION_KEY = "schema_version"

#: Every optional top-level request key. The three profile keys default to the profiles
#: this build implements and any other value is rejected by ``_require_profiles``.
OPTIONAL_REQUEST_KEYS: frozenset[str] = frozenset(
    {
        "risk_class",
        "closure_policy_requirements",
        "observation_method",
        "identity_profile",
        "comparison_profile",
        "normalization_profile",
    }
)

#: The request key set is **not** closed: an unknown top-level key is ignored, as it always
#: has been. Enumerating the grammar is enforcement of the accepted interface; rejecting a
#: key the producer used to accept would be a change to it, which Phase 3 does not make.
REQUEST_KEYS: frozenset[str] = (
    frozenset(REQUIRED_REQUEST_KEYS) | OPTIONAL_REQUEST_KEYS | {SCHEMA_VERSION_KEY}
)

#: Every per-binding key the derivation reads before it can validate anything.
REQUIRED_BINDING_KEYS: tuple[str, ...] = (
    "target_predicate_id",
    "observation_scope",
    "observation_bundle",
)

#: Every optional per-binding key. ``historical_observation_scopes`` is the explicit,
#: immutable supply route for the Scopes an append-only Observation lineage names but this
#: derivation did not resolve; see ``engine._historical_scopes``.
OPTIONAL_BINDING_KEYS: frozenset[str] = frozenset(
    {
        "risk_class",
        "closure_policy_requirements",
        "historical_observation_scopes",
        "predecessor",
    }
)

#: Unlike the request envelope, the binding key set **is** closed, and was before this
#: change: ``engine`` rejects an unknown binding key by name. This is the same set, owned
#: once instead of restated beside the required tuple.
BINDING_KEYS: frozenset[str] = frozenset(REQUIRED_BINDING_KEYS) | OPTIONAL_BINDING_KEYS

#: Every location where a schema in ``01_SCHEMA/`` declares a property and constrains it
#: with nothing -- ``{}`` accepts any JSON value. These are the only places a *schematized*
#: record can carry an arbitrary payload, so they are the only places where crossing the
#: schema boundary does not answer readability and this module must. The set is derived
#: from the schema files by the inventory test in both directions, so a schema that adds or
#: removes an unconstrained property fails the measurement instead of silently widening the
#: grammar.
#:
#: ``INPUT`` marks a location the *Difference* producer's callers supply; ``EMITTED`` marks
#: one the Engine writes, where the payload is whatever the input location already admitted;
#: ``AUTHORITY_INPUT`` marks one supplied to a different owner, which generates against it in
#: its own suite. The tag says which suite must cover a location, so a new one cannot be
#: added without some suite claiming it.
UNCONSTRAINED_CONTRACT_LOCATIONS: dict[str, str] = {
    "objective/target_predicate.schema.json#/properties/expected_value": "INPUT",
    "observation/normalized_fact.schema.json#/properties/value": "INPUT",
    # Opaque by contract: Authority binds the operation payload into an approval's identity
    # and never interprets it. Constraining it here would be this schema deciding what a
    # Change may do, which is a later phase's to say.
    "authority/authority.schema.json#/$defs/action/properties/operation": "AUTHORITY_INPUT",
    "difference/candidate_completion_record.schema.json#/properties/claim": "EMITTED",
    "difference/difference.schema.json"
    "#/$defs/normalized_target_state/properties/expected_value": "EMITTED",
    "difference/difference.schema.json#/$defs/value_candidate/properties/value": "EMITTED",
    "difference/difference.schema.json"
    "#/$defs/structural_difference/properties/target_value": "EMITTED",
    "difference/invariant_evaluation.schema.json#/properties/expected": "EMITTED",
    "difference/invariant_evaluation.schema.json#/properties/observed": "EMITTED",
}


# --------------------------------------------------------------------------- #
# The decisions
# --------------------------------------------------------------------------- #
#
# Each comes in two forms, and both are needed. ``require_*`` is for a caller whose contract
# says the value *must* bear the shape, and it rejects. ``is_*`` is for a caller whose
# contract says another shape means something else -- a value that is not a declared wrapper
# is an ordinary value, a section that is not a list is rejected in that caller's own words
# -- and it answers without deciding what the caller does next. What neither form allows is
# a second ``isinstance`` written beside the question: a contract test scans every module
# under ``difference/`` and fails any rejection expressed as a negated type test outside
# this file, which is coarse on purpose. Counting call sites after the fact is what let the
# `a11d7c7` readability split happen (ADR-0023), and this is the same rule for the same
# reason, applied one layer earlier.


def _reject(context: str, requirement: str, value: Any, detail: str | None) -> DifferenceError:
    return DifferenceError(
        f"{context} is not a canonical {requirement}: "
        f"{detail if detail is not None else repr(value)}"
    )


def is_scalar_tag(value: Any) -> TypeGuard[str]:
    """Return whether *value* can serve as a mapping or set key.

    The predicate form exists because not every caller is rejecting. A membership test
    against a declared tag set answers *which* declared thing this is, and a value that
    cannot be a tag is simply not one of them -- so a caller whose contract says "any other
    shape is an ordinary value" asks this, and a caller whose contract says "this must be a
    declared tag" asks :func:`require_scalar_tag`. Two callers, one definition.
    """

    return isinstance(value, str) and bool(value)


def is_canonical_object(value: Any) -> TypeGuard[dict[str, Any]]:
    """Return whether *value* can be indexed as a canonical object."""

    return isinstance(value, dict)


def is_collection(value: Any) -> TypeGuard[list[Any]]:
    """Return whether *value* can be iterated or sorted as a declared collection."""

    return isinstance(value, list)


def require_scalar_tag(value: Any, context: str, *, detail: str | None = None) -> str:
    """Return *value* once it can serve as a mapping or set key; reject it otherwise.

    Every membership test hashes its operand. ``[]`` and ``{}`` raise ``unhashable type``
    from inside whichever comparison reaches them first, which is not a rejection -- it is
    the producer failing to answer. Called *before* the membership test, never beside it.
    """

    if not is_scalar_tag(value):
        raise _reject(context, "tag", value, detail)
    return value


def require_collection(value: Any, context: str, *, detail: str | None = None) -> list[Any]:
    """Return *value* once it can be iterated or sorted as a declared collection.

    A declared collection that arrives as ``None`` or a scalar reaches ``sorted`` or a
    comprehension and raises ``'NoneType' object is not iterable`` in place of the canonical
    rejection its boundary documents.
    """

    if not is_collection(value):
        raise _reject(context, "collection", value, detail)
    return value


def require_object(value: Any, context: str, *, detail: str | None = None) -> dict[str, Any]:
    """Return *value* once it can be indexed as a canonical object."""

    if not is_canonical_object(value):
        raise _reject(context, "object", value, detail)
    return value


def require_optional_object(
    value: Any, context: str, *, detail: str | None = None
) -> dict[str, Any] | None:
    """The same, for an optional input: absent and ``None`` are both legitimately empty."""

    if value is None:
        return None
    return require_object(value, context, detail=detail)
