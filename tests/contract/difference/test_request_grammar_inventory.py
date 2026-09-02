"""The producer's input grammar, taken from the contract and compared in both directions.

Four review rounds found the same class of defect, and the 7770-case mutation sweep found
none of them. That is not a gap in the sweep's effort; it is what a sweep *is*. A mutation
sweep enumerates the locations a fixture instantiates and the substitutions a harness
lists, so an **optional key the fixture omits has no case**, and a **domain-shaped value the
substitution set cannot express has no case**. Both of the invisible findings on `5d9f407`
were exactly one of those two things:

```text
risk_class                  optional, absent from every committed fixture
closure_policy_requirements.allowed_terminal_states   absent: the fixture supplies one key
expected_value.value_type   a domain-shaped object no fixed substitution set contains
```

So this file does not extend the sweep. It starts from the *declarations* -- the producer's
own read sites and the schema files under ``01_SCHEMA/`` -- and generates from them, which
is the only order in which an absent location can be covered at all.

Every comparison here runs in **both** directions, because only one of them is the one that
has been failing. "Every declared key is read" catches a stale declaration; "every key read
is declared" catches the new optional key that nobody remembered to declare, which is the
one that produced these findings. The same applies to the schema sweep: a property the
schemas leave unconstrained and this repository does not list is a location where crossing
the schema boundary answers nothing and no generated case exists.

What is **not** claimed: this bounds the *envelope* grammar and the schema-unconstrained
payload locations. It is not a proof of totality over the embedded records -- those keep
their own schemas and the sweep -- and it does not close the request key set. See
``difference.admissibility``.
"""

from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    state_fingerprint,
    target_predicate,
)

from manosube_agent_civilization.difference import admissibility, derive_differences
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.difference.identity import POLICY_UNORDERED_SET_FIELDS

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "src" / "manosube_agent_civilization" / "difference"
ENGINE = SOURCE / "engine.py"
SCHEMA_ROOT = ROOT / "01_SCHEMA"


# --------------------------------------------------------------------------- #
# Direction one and two: the declaration against the producer's own read sites
# --------------------------------------------------------------------------- #
#
# Every comparison below is structural. An earlier version of this file closed its last gap
# with `assert f'"{key}"' in source`, and that assertion was **vacuous**: each of the four
# keys it covered is also written as a dict key into an emitted record in the same file, so
# the literal is present whether or not any gate reads it. For ``schema_version`` it was
# already passing on emitted-record writes alone, because `engine.py` never reads that key
# off the request at all -- the read is one call away, in `validation.py`.
#
# That is the same fault the file exists to prevent, one level up: a check that cannot fail
# reports success. `test_a_literal_search_cannot_tell_a_read_from_a_write` pins the exact
# false-positive mechanism, and every control below drives the real scanners with synthetic
# source so each is proven able to fail.

#: The functions whose ``request`` parameter is a *derivation request* and whose ``binding``
#: parameter is a *derivation binding*. Every other ``request`` and ``binding`` in the file
#: names a different record type that happens to share the word -- an Observation request,
#: a Fact/Observation binding -- and scanning those reported keys of other grammars as
#: undeclared keys of this one. The scope list is held to the source below, so renaming a
#: function empties its scan loudly instead of quietly.
REQUEST_SCOPES = (
    "derive_differences",
    "_require_request_shape",
    "_iter_request_records",
    "_reject_hostile_input",
    "_historical_scopes",
    "_require_profiles",
)


def _read_sites_in(source: str, *, require_scopes: bool = True) -> dict[str, set[str]]:
    """Return every constant key read off ``request`` / ``binding`` inside those functions.

    Takes source text rather than a path so the controls can drive this exact scanner with a
    synthetic module and prove it reports what is really there.
    """

    tree = ast.parse(source)
    found: dict[str, set[str]] = {"request": set(), "binding": set()}
    seen_scopes: set[str] = set()
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef) or function.name not in REQUEST_SCOPES:
            continue
        seen_scopes.add(function.name)
        for node in ast.walk(function):
            root = key = None
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id in found
                and isinstance(node.slice, ast.Constant)
            ):
                root, key = node.value.id, node.slice.value
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in found
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                root, key = node.func.value.id, node.args[0].value
            if root is not None and isinstance(key, str):
                found[root].add(key)
    # The scan is measured before its subject is. A renamed or deleted function would empty
    # its contribution silently, and an empty contribution passes every comparison below.
    if require_scopes:
        assert seen_scopes == set(REQUEST_SCOPES), sorted(set(REQUEST_SCOPES) - seen_scopes)
    return found


# --------------------------------------------------------------------------- #
# The one key no request scope reads, followed to the gate that does
# --------------------------------------------------------------------------- #

#: ``schema_version`` is required, and `engine.py` never reads it: it hands the whole request
#: to ``validation.require_schema_version``, which reads it off its own parameter. So the
#: declaration names the delegation exactly -- module, function, and the parameter the
#: request arrives as -- and the scan **follows** it rather than accepting the key's presence
#: anywhere in the producer. There is no other exemption, and no literal search remains.
DELEGATED_READS: dict[str, tuple[str, str, str]] = {
    admissibility.SCHEMA_VERSION_KEY: ("validation.py", "require_schema_version", "record"),
}


def _reads_key_off(source: str, function_name: str, parameter: str, key: str) -> bool:
    """Whether *function_name* reads *key* off its *parameter* -- a read, never a write.

    ``{"schema_version": SCHEMA_VERSION}`` is a dict-key literal in a record the producer
    *builds*. It is the construct that made the old assertion vacuous, and only
    ``parameter.get("key")`` or ``parameter["key"]`` counts here.
    """

    for function in ast.walk(ast.parse(source)):
        if not isinstance(function, ast.FunctionDef) or function.name != function_name:
            continue
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == parameter
                and isinstance(node.slice, ast.Constant)
                and node.slice.value == key
            ):
                return True
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == parameter
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == key
            ):
                return True
    return False


def _hands_the_request_to(source: str, callee: str) -> bool:
    """Whether a scanned request scope calls *callee* with the request itself as first arg."""

    for function in ast.walk(ast.parse(source)):
        if not isinstance(function, ast.FunctionDef) or function.name not in REQUEST_SCOPES:
            continue
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == callee
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "request"
            ):
                return True
    return False


def _delegated_reads_proven(engine_source: str) -> set[str]:
    """Return the delegated keys proven read, by following each declared delegation."""

    proven: set[str] = set()
    for key, (module, function_name, parameter) in DELEGATED_READS.items():
        if not _hands_the_request_to(engine_source, function_name):
            continue
        target = (SOURCE / module).read_text(encoding="utf-8")
        if _reads_key_off(target, function_name, parameter, key):
            proven.add(key)
    return proven


ENGINE_SOURCE = ENGINE.read_text(encoding="utf-8")
READ_SITES = _read_sites_in(ENGINE_SOURCE)
DELEGATED_PROVEN = _delegated_reads_proven(ENGINE_SOURCE)

DECLARED_REQUEST_KEYS = (
    set(admissibility.REQUIRED_REQUEST_KEYS)
    | admissibility.OPTIONAL_REQUEST_KEYS
    | {admissibility.SCHEMA_VERSION_KEY}
)
DECLARED_BINDING_KEYS = set(admissibility.BINDING_KEYS)

#: Every key proven read, by either route. Nothing is exempt.
PROVEN_REQUEST_READS = READ_SITES["request"] | DELEGATED_PROVEN


def test_every_declared_request_key_is_read_by_the_producer() -> None:
    """A declared key the producer never reads is a grammar that has drifted from the code."""

    unread = DECLARED_REQUEST_KEYS - PROVEN_REQUEST_READS
    assert not unread, sorted(unread)


def test_every_request_key_the_producer_reads_is_declared() -> None:
    """The direction that was failing: an optional key nothing declares gets no case."""

    undeclared = PROVEN_REQUEST_READS - DECLARED_REQUEST_KEYS
    assert not undeclared, sorted(undeclared)


def test_every_declared_binding_key_is_read_by_the_producer() -> None:
    unread = DECLARED_BINDING_KEYS - READ_SITES["binding"]
    assert not unread, sorted(unread)


def test_every_binding_key_the_producer_reads_is_declared() -> None:
    undeclared = READ_SITES["binding"] - DECLARED_BINDING_KEYS
    assert not undeclared, sorted(undeclared)


def test_every_declared_delegation_is_followed_to_a_real_read() -> None:
    """The one delegation is proven end to end, not asserted."""

    assert set(DELEGATED_READS) == DELEGATED_PROVEN, sorted(
        set(DELEGATED_READS) - DELEGATED_PROVEN
    )
    assert not set(DELEGATED_READS) & READ_SITES["request"], (
        "a delegated key the scan can already see should be scanned, not delegated"
    )


def test_the_three_profile_keys_are_scanned_rather_than_delegated() -> None:
    """``_require_profiles`` is in scope now, so the three keys need no special case."""

    for key in ("identity_profile", "comparison_profile", "normalization_profile"):
        assert key in READ_SITES["request"], key
        assert key not in DELEGATED_READS, key


# --------------------------------------------------------------------------- #
# The two key sets differ, deliberately, and the difference is pinned
# --------------------------------------------------------------------------- #


def test_the_binding_key_set_is_closed_and_owned_once() -> None:
    """One set, derived from the required and optional halves rather than restated."""

    assert (
        set(admissibility.REQUIRED_BINDING_KEYS) | admissibility.OPTIONAL_BINDING_KEYS
    ) == admissibility.BINDING_KEYS
    assert not set(admissibility.REQUIRED_BINDING_KEYS) & admissibility.OPTIONAL_BINDING_KEYS
    request = _base_request()
    request["bindings"][0]["unexpected"] = 1
    with pytest.raises(DifferenceError, match="unknown sections"):
        derive_differences(request)


def test_an_undeclared_request_key_is_ignored() -> None:
    """The request envelope is **not** closed, and this pins that rather than assuming it.

    Enumerating the grammar is enforcement of the interface the producer already accepts.
    Rejecting a top-level key it used to ignore would be a change to that interface, which
    is a contract decision and not this Issue's to make -- so the behaviour is asserted here
    in the shape it has, and a later decision to close the set fails this test by name.
    """

    request = _base_request()
    request["undeclared_key"] = {"anything": [1, 2, 3]}
    assert derive_differences(request)["differences"]


# --------------------------------------------------------------------------- #
# Direction three: the schema files against the declared unconstrained locations
# --------------------------------------------------------------------------- #


def _unconstrained_schema_locations() -> set[str]:
    """Every property a schema declares and constrains with nothing.

    ``{}`` and ``true`` both accept any JSON value, so crossing the schema boundary at such
    a location establishes nothing at all about the value -- which makes these the exact
    places the producer, not the schema, has to answer readability.
    """

    found: set[str] = set()

    def walk(node: Any, path: str, rel: str) -> None:
        if not isinstance(node, dict):
            return
        for name, sub in (node.get("properties") or {}).items():
            child = f"{path}/properties/{name}"
            if sub == {} or sub is True:
                found.add(f"{rel}#{child}")
            else:
                walk(sub, child, rel)
        for keyword in ("items", "additionalProperties", "contains"):
            sub = node.get(keyword)
            if sub == {} or sub is True:
                found.add(f"{rel}#{path}/{keyword}")
            else:
                walk(sub, f"{path}/{keyword}", rel)
        for keyword in ("allOf", "anyOf", "oneOf", "prefixItems"):
            for index, sub in enumerate(node.get(keyword) or ()):
                if sub == {} or sub is True:
                    found.add(f"{rel}#{path}/{keyword}/{index}")
                else:
                    walk(sub, f"{path}/{keyword}/{index}", rel)
        for keyword in ("if", "then", "else", "not"):
            walk(node.get(keyword), f"{path}/{keyword}", rel)
        for name, sub in (node.get("$defs") or {}).items():
            walk(sub, f"{path}/$defs/{name}", rel)

    schemas = sorted(SCHEMA_ROOT.rglob("*.schema.json"))
    # A scan that reads no files reports nothing unconstrained and passes.
    assert len(schemas) > 10, len(schemas)
    for path in schemas:
        walk(json.loads(path.read_text(encoding="utf-8")), "", str(path.relative_to(SCHEMA_ROOT)))
    return found


def test_the_declared_unconstrained_locations_match_the_schemas_in_both_directions() -> None:
    """A schema that opens a new payload location fails here instead of widening in silence."""

    assert _unconstrained_schema_locations() == set(admissibility.UNCONSTRAINED_CONTRACT_LOCATIONS)
    assert set(admissibility.UNCONSTRAINED_CONTRACT_LOCATIONS.values()) == {"INPUT", "EMITTED"}


def test_every_input_side_unconstrained_location_has_generated_coverage() -> None:
    """The classification is not decoration: each ``INPUT`` location is generated against."""

    inputs = {
        location
        for location, side in admissibility.UNCONSTRAINED_CONTRACT_LOCATIONS.items()
        if side == "INPUT"
    }
    assert inputs == set(_PAYLOAD_BUILDERS)


# --------------------------------------------------------------------------- #
# Generated coverage, from the declarations rather than from a fixture's shape
# --------------------------------------------------------------------------- #

#: The structural variants every declared location is generated against. This set is
#: deliberately *not* called total -- a fixed substitution set never is, and saying so is
#: how the third finding was missed. It is the shapes a JSON document can take at a
#: location plus the members those shapes can carry; the domain-shaped variants below are
#: derived from the contract rather than listed here.
_VARIANTS: tuple[tuple[str, Any], ...] = (
    ("null", None),
    ("false", False),
    ("true", True),
    ("zero", 0),
    ("integer", 7),
    ("empty-string", ""),
    ("string", "seven"),
    ("empty-array", []),
    ("array-of-string", ["seven"]),
    ("array-of-null", [None]),
    ("array-of-integer", [7]),
    ("array-of-array", [[]]),
    ("array-of-object", [{}]),
    ("empty-object", {}),
    ("object", {"seven": 7}),
    ("object-of-array", {"seven": []}),
)

#: The shapes the contract itself gives meaning to, applied where the schema gives none.
#: A fixed scalar substitution set cannot express any of these, which is why
#: ``expected_value.value_type = []`` survived 7770 cases.
def _domain_shaped(value: Any) -> tuple[tuple[str, Any], ...]:
    return (
        ("wrapper-tag", {"value_type": value, "value": "READY"}),
        ("wrapper-payload", {"value_type": "DECIMAL", "value": value}),
        ("wrapper-extra-key", {"value_type": "STRING", "value": "READY", "extra": value}),
        ("collection-wrapper", {"collection_kind": value, "items": []}),
        ("reference-shaped", {"kind": value, "id": "X-0001"}),
    )


#: ``normalized_fact.schema.json`` leaves ``value`` unconstrained and then *conditions* it
#: on ``value_type`` with ``if``/``then``. So a Fact carrying an arbitrary payload has to
#: declare the matching type, or the record is refused for the contradiction rather than
#: for the payload -- a different case, and one the mutation sweep already covers. This
#: mapping is the schema's own conditional block, read in the direction the generator needs.
def _declared_value_type(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "INTEGER"
    if isinstance(value, str):
        return "STRING"
    if isinstance(value, list):
        return "ORDERED_COLLECTION"
    return "STRUCTURED"


def _base_request(
    *,
    expected_value: Any = "READY",
    fact_value: Any = "NOT-READY",
) -> dict[str, Any]:
    """A derivation that succeeds, with the two unconstrained payload locations open."""

    fingerprint = state_fingerprint()
    scope = observation_scope()
    return derivation_request(
        objective_revision([target_predicate(expected_value=expected_value)]),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope,
                    [raw_fact(value=fact_value, value_type=_declared_value_type(fact_value))],
                    fingerprint,
                    negative_claims=[negative_claim("NO_RESULT")],
                ),
            }
        ],
        fingerprint,
    )


#: Each ``INPUT`` unconstrained schema location, and how to build a request carrying an
#: arbitrary payload there. Both go through the ordinary helpers, so the surrounding record
#: stays identity-valid and the payload is what the derivation actually reaches.
_PAYLOAD_BUILDERS = {
    "objective/target_predicate.schema.json#/properties/expected_value": (
        lambda value: _base_request(expected_value=value)
    ),
    "observation/normalized_fact.schema.json#/properties/value": (
        lambda value: _base_request(fact_value=value)
    ),
}


def _apply(path: tuple[Any, ...], value: Any) -> dict[str, Any]:
    request = _base_request()
    _set(request, path, value)
    return request


def _set(request: dict[str, Any], path: tuple[Any, ...], value: Any) -> None:
    target: Any = request
    for step in path[:-1]:
        target = target[step]
    target[path[-1]] = value


def _delete(request: dict[str, Any], path: tuple[Any, ...]) -> None:
    target: Any = request
    for step in path[:-1]:
        target = target[step]
    if path[-1] in target:
        del target[path[-1]]


def _declared_locations() -> dict[str, tuple[Any, ...]]:
    """Every envelope location the grammar declares, generated rather than listed.

    Adding an optional key to ``admissibility`` adds its cases here without anyone
    remembering to, which is the property the sweep could not have.
    """

    locations: dict[str, tuple[Any, ...]] = {}
    for key in sorted(DECLARED_REQUEST_KEYS):
        locations[f"request.{key}"] = (key,)
    for key in sorted(DECLARED_BINDING_KEYS):
        locations[f"binding.{key}"] = ("bindings", 0, key)
    # The declared collections *inside* an optional fragment. The fixture supplies exactly
    # one key of this fragment, so the other four were unreachable by any fixture-path
    # mutation -- and three of them were the first finding.
    for field in POLICY_UNORDERED_SET_FIELDS:
        locations[f"request.closure_policy_requirements.{field}"] = (
            "closure_policy_requirements",
            field,
        )
    return locations


LOCATIONS = _declared_locations()


def _answer(request: dict[str, Any]) -> str:
    """Return how the producer answered. A raw exception is not an answer and propagates.

    ``DifferenceError`` and nothing else. The Observation authority owns Fact normalization
    and raises its own ``ObservationError``, so a wider vocabulary was considered and
    measured: across all 551 generated cases the producer answers 83 times by deriving and
    468 times with a ``DifferenceError``, and never with an ``ObservationError``. Widening
    the accepted set on the strength of an import rather than a measurement is how a
    classifier stops discriminating, so it stays narrow.
    """

    try:
        derive_differences(request)
    except DifferenceError:
        return "REJECTED"
    return "DERIVED"


@pytest.mark.parametrize("location", sorted(LOCATIONS))
@pytest.mark.parametrize("variant", [name for name, _ in _VARIANTS])
def test_every_declared_location_answers_for_every_structural_variant(
    location: str, variant: str
) -> None:
    """Never a raw ``TypeError``, ``KeyError`` or ``AttributeError`` -- an answer, always."""

    value = dict(_VARIANTS)[variant]
    request = _base_request()
    before = deepcopy(request)
    _set(request, LOCATIONS[location], value)
    assert request != before, f"{location}={variant} changed nothing"
    assert _answer(request) in ("REJECTED", "DERIVED")


@pytest.mark.parametrize("location", sorted(LOCATIONS))
def test_every_declared_location_answers_when_it_is_absent(location: str) -> None:
    """Absence is a variant a mutation sweep can only apply where a fixture put something."""

    request = _base_request()
    _delete(request, LOCATIONS[location])
    assert _answer(request) in ("REJECTED", "DERIVED")


@pytest.mark.parametrize("location", sorted(_PAYLOAD_BUILDERS))
@pytest.mark.parametrize("shape", [name for name, _ in _domain_shaped(None)])
@pytest.mark.parametrize("variant", [name for name, _ in _VARIANTS])
def test_every_unconstrained_payload_location_answers_for_a_domain_shaped_value(
    location: str, shape: str, variant: str
) -> None:
    """Where the schema constrains nothing, the producer answers -- for wrapper shapes too."""

    payload = dict(_domain_shaped(dict(_VARIANTS)[variant]))[shape]
    assert _answer(_PAYLOAD_BUILDERS[location](payload)) in ("REJECTED", "DERIVED")


@pytest.mark.parametrize("field", POLICY_UNORDERED_SET_FIELDS)
@pytest.mark.parametrize("variant", [name for name, _ in _VARIANTS])
def test_every_declared_policy_set_answers_for_a_malformed_member(
    field: str, variant: str
) -> None:
    """A member, not only the container: the container guard is half the rule."""

    request = _base_request()
    request["closure_policy_requirements"][field] = [dict(_VARIANTS)[variant]]
    assert _answer(request) in ("REJECTED", "DERIVED")


# --------------------------------------------------------------------------- #
# The harness before the subject
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# The instrument this file used to trust, and the one that replaced it
# --------------------------------------------------------------------------- #
#
# Each control drives the *real* scanner with a synthetic module, so the thing proven able
# to fail is the code the comparisons above actually run -- not a restatement of it.

#: A producer that **writes** three keys into an emitted record and **reads** none of them.
#: Every key the old assertion covered appears in `engine.py` in exactly this shape.
_WRITES_BUT_DOES_NOT_READ = """
def derive_differences(request):
    return {
        "schema_version": SCHEMA_VERSION,
        "identity_profile": IDENTITY_PROFILE,
        "comparison_profile": COMPARISON_PROFILE,
    }
"""

#: The same producer, reading one of them off the request as a gate actually would.
_READS_ONE = """
def derive_differences(request):
    declared = request.get("identity_profile", IDENTITY_PROFILE)
    return {"schema_version": SCHEMA_VERSION, "identity_profile": IDENTITY_PROFILE}
"""


def test_a_literal_search_cannot_tell_a_read_from_a_write() -> None:
    """The exact false-positive mechanism this file used to depend on, pinned as a case.

    `assert f'"{key}"' in source` was the last comparison here, and it could not fail: each
    key it covered is also a dict-key literal in a record the producer *builds*. For
    ``schema_version`` that was not even hypothetical -- `engine.py` has no request read of
    it at all, so the assertion was passing on emitted-record writes alone.
    """

    for key in ("schema_version", "identity_profile", "comparison_profile"):
        assert f'"{key}"' in _WRITES_BUT_DOES_NOT_READ, key   # the old check: green
        assert key not in _read_sites_in(                      # the new one: correct
            _WRITES_BUT_DOES_NOT_READ, require_scopes=False
        )["request"], key


def test_the_scan_reports_a_read_when_one_is_there() -> None:
    """And the other half of the control: it is not simply reporting nothing."""

    found = _read_sites_in(_READS_ONE, require_scopes=False)["request"]
    assert found == {"identity_profile"}, found


def test_the_scan_fails_when_a_named_gate_stops_reading_its_key() -> None:
    """Negative control on the live source: delete the read, keep the write, expect a miss.

    This is the mutation that would have slipped past the old assertion. The mutation is
    asserted to apply, so a rename that made it a no-op fails the control instead of
    quietly passing it.
    """

    mutated = ENGINE_SOURCE.replace(
        '"identity_profile": (request.get("identity_profile", IDENTITY_PROFILE),'
        " IDENTITY_PROFILE),",
        '"identity_profile": (IDENTITY_PROFILE, IDENTITY_PROFILE),',
        1,
    )
    assert mutated != ENGINE_SOURCE, "the mutation did not apply; the control proves nothing"
    assert '"identity_profile"' in mutated, "the write must survive for this to be a control"
    assert "identity_profile" not in _read_sites_in(mutated)["request"]


def test_the_delegation_follow_fails_when_the_target_stops_reading() -> None:
    """The same control for the delegated key, on the gate the declaration names."""

    validation = (SOURCE / "validation.py").read_text(encoding="utf-8")
    assert _reads_key_off(validation, "require_schema_version", "record", "schema_version")

    mutated = validation.replace('record.get("schema_version")', "None", 1)
    assert mutated != validation, "the mutation did not apply; the control proves nothing"
    assert '"schema_version"' in ENGINE_SOURCE, "the producer's writes must still be present"
    assert not _reads_key_off(mutated, "require_schema_version", "record", "schema_version")


def test_the_delegation_follow_fails_when_the_producer_stops_delegating() -> None:
    """And when the producer no longer hands the request to the gate it names."""

    assert _hands_the_request_to(ENGINE_SOURCE, "require_schema_version")
    mutated = ENGINE_SOURCE.replace(
        'require_schema_version(request, "derivation request")', "pass", 1
    )
    assert mutated != ENGINE_SOURCE, "the mutation did not apply; the control proves nothing"
    assert not _hands_the_request_to(mutated, "require_schema_version")
    assert not _delegated_reads_proven(mutated)


def test_no_comparison_in_this_file_rests_on_a_literal_search() -> None:
    """`LITERAL_EXEMPTION_COUNT=0`, measured from this file rather than asserted in prose.

    Measured **structurally**, and the first attempt at this test is the reason why: written
    as ``"in source" not in body`` it failed on the paragraph *describing* the defect. A text
    search cannot tell a claim from its own explanation, which is the same confusion between
    a mention and a use that made the old assertion vacuous. So this parses instead, and
    looks for the shape ``f'"{key}"' in <name>`` -- permitted in exactly one place, the
    control that exists to demonstrate it.
    """

    guilty: set[str] = set()
    module = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    for function in ast.walk(module):
        if not isinstance(function, ast.FunctionDef):
            continue
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Compare)
                and any(isinstance(op, ast.In) for op in node.ops)
                and isinstance(node.left, ast.JoinedStr)
            ):
                guilty.add(function.name)
    assert guilty == {"test_a_literal_search_cannot_tell_a_read_from_a_write"}, sorted(guilty)
    assert "UNSCANNED_DECLARED_REQUEST_KEYS" not in globals()


def test_the_generated_cases_reach_both_outcomes() -> None:
    """A generator that rejects everything passes vacuously, which is a harness fault.

    ADR-0022 records three of those in this repository's own measurements, so the outcome
    split is measured here rather than assumed.
    """

    outcomes = Counter(
        _answer(_apply(LOCATIONS[location], value))
        for location in LOCATIONS
        for _, value in _VARIANTS
    )
    assert outcomes["DERIVED"] > 0, outcomes
    assert outcomes["REJECTED"] > 0, outcomes


def test_the_base_request_derives() -> None:
    """Every generated case starts here, so a broken base would make them all vacuous."""

    assert _base_request() != {}
    assert derive_differences(_base_request())["differences"]


def test_a_raw_exception_is_not_reported_as_an_answer() -> None:
    """The positive control for the classifier: only ``DifferenceError`` is an answer."""

    class Raw(dict):  # type: ignore[type-arg]
        """A request that is a canonical object and still cannot be read."""

        def __getitem__(self, key: str) -> Any:
            raise RuntimeError("not an answer")

    raw = Raw(dict.fromkeys(admissibility.REQUIRED_REQUEST_KEYS))
    with pytest.raises(RuntimeError):
        _answer(raw)


def test_a_semantic_rejection_is_still_an_answer() -> None:
    """And the negative control: a readable, wrong value keeps its own diagnosis."""

    request = _base_request()
    request["risk_class"] = "NOT-A-RISK-CLASS"
    with pytest.raises(DifferenceError, match="unknown risk class"):
        derive_differences(request)


def test_the_generated_locations_reach_what_no_committed_fixture_instantiates() -> None:
    """The reason this file exists, stated as a measurement rather than as a claim.

    If every declared location were present in the base request, this file would be adding
    nothing a mutation sweep could not reach, and the four blind spots would have to be
    explained some other way. They are not: these locations are absent, so no sweep over
    this fixture can produce a single case for them.
    """

    request = _base_request()

    def present(path: tuple[Any, ...]) -> bool:
        target: Any = request
        for step in path[:-1]:
            target = target[step]
        return path[-1] in target

    absent = sorted(name for name, path in LOCATIONS.items() if not present(path))
    assert "request.risk_class" in absent
    assert "binding.risk_class" in absent
    assert "request.closure_policy_requirements.allowed_terminal_states" in absent
    assert len(absent) >= 8, absent
