"""No reachable derivation input may produce anything but a canonical rejection.

Four consecutive review rounds found the same defect one layer further out: a container was
validated and its members were not, a section was guarded and its records were not, a record
was guarded and its fields were not. Each was corrected where it was found, and the next
round found the next one. That is a bounded class, not a sequence of unrelated defects, so
this test enumerates the whole surface instead of naming cases one at a time.

It walks every reachable location of a valid derivation request and, for each, deletes it
and retypes it, then asserts `derive_differences` raises `DifferenceError` -- never a raw
`KeyError`, `TypeError` or `AttributeError`. A location added to the request later is
covered without being remembered.

**The harness is measured before the subject is.** An earlier run of this sweep reported
four leaks where there were nineteen: its path parser produced an empty key after a list
index, the mutation raised, and a bare ``except: continue`` swallowed it, so every nested
location was silently skipped and the run looked clean -- the same defect this file exists
to find, in the file itself. So mutation-application failures, a path the parser cannot
round-trip, and an inventory truncated by the depth bound each fail the measurement here
rather than shrinking it, and positive controls prove the detection path reaches a known
bad outcome and a known good one.
"""

from __future__ import annotations

from copy import deepcopy
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
    retained_status_predecessor,
    state_fingerprint,
)

from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.errors import DifferenceError

#: Depth is bounded so the case count stays a test rather than a fuzz run. The bound is not
#: allowed to be the thing that decides coverage:
#: ``test_the_inventory_is_neither_truncated_nor_shrunk`` asserts no fixture actually reaches
#: it, so a deeper request fails the measurement instead of being quietly clipped out of it.
#:
#: It was 8, and it was binding. The request fixture nests to 9 and the predecessor fixture
#: to 15, while this file's own docstring claimed every location was "well within" the
#: bound. It was not: 49 predecessor locations -- 294 cases -- were clipped out of every
#: count this branch has published, including the ones quoted back to it. The bound is now
#: measured rather than asserted, which is the only reason that was found.
_MAX_DEPTH = 24


def _request() -> dict[str, Any]:
    """A predecessor-free derivation: the widest reachable request surface."""

    fingerprint = state_fingerprint()
    scope = observation_scope()
    return derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope,
                    [raw_fact(value="NOT-READY")],
                    fingerprint,
                    negative_claims=[negative_claim("NO_RESULT")],
                ),
            }
        ],
        fingerprint,
    )


def _predecessor_request() -> dict[str, Any]:
    """A re-observation carrying predecessor context.

    The predecessor subtree is the larger part of the request surface and the sweep did not
    reach it while this fixture sat outside ``FIXTURES``: a non-object ``predecessor`` was
    found by a reviewer, not here, and committing the fixture then measured 78 more the
    reviewer had not reached either. Those are corrected, and the fixture is committed so
    the number cannot drift back to meaning less than it appears to.
    """

    _baseline, request = retained_status_predecessor("RETAINED")
    return request


def _locations(node: Any, path: str = "", depth: int = 0) -> Any:
    if depth > _MAX_DEPTH:
        return
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}.{key}" if path else key
            yield here
            yield from _locations(value, here, depth + 1)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _locations(value, f"{path}[{index}]", depth + 1)


def _depth_of(node: Any, depth: int = 0) -> int:
    """The real nesting depth of a fixture, measured without the sweep's own bound."""

    if isinstance(node, dict):
        return max((_depth_of(value, depth + 1) for value in node.values()), default=depth)
    if isinstance(node, list):
        return max((_depth_of(value, depth + 1) for value in node), default=depth)
    return depth


def _steps(path: str) -> list[tuple[str, Any]]:
    steps: list[tuple[str, Any]] = []
    token = ""
    for character in path:
        if character in ".[":
            if token:
                steps.append(("key", token))
            token = ""
        elif character == "]":
            steps.append(("index", int(token)))
            token = ""
        else:
            token += character
    if token:
        steps.append(("key", token))
    return steps


#: The substitutions each location is retyped to. A single scalar sentinel is not enough:
#: an *unhashable* value slipped past an earlier run of this sweep and reached a set
#: membership test, raising `unhashable type` where the boundary owed a rejection. Each
#: sentinel is a well-formed JSON value, so what is tested is the boundary, not the parser.
_SUBSTITUTIONS: dict[str, Any] = {
    "int": 7,
    "str": "seven",
    "list": ["seven"],
    "dict": {"seven": 7},
    "null": None,
}

_ACTIONS: tuple[str, ...] = ("delete", *(f"retype:{name}" for name in _SUBSTITUTIONS))


def _mutate(request: dict[str, Any], path: str, action: str) -> None:
    steps = _steps(path)
    node: Any = request
    for _kind, step in steps[:-1]:
        node = node[step]
    _kind, last = steps[-1]
    if action == "delete":
        del node[last]
    else:
        node[last] = deepcopy(_SUBSTITUTIONS[action.split(":", 1)[1]])


#: Every fixture the sweep walks. A surface the fixtures do not exhibit is not covered.
FIXTURES: dict[str, Any] = {
    "request": _request,
    "predecessor": _predecessor_request,
}

#: Built once and copied per case. Building a predecessor request runs a whole derivation,
#: so rebuilding it per case would cost more than the case it sets up; a deep copy is the
#: same isolation for a thousandth of the time.
BUILT: dict[str, dict[str, Any]] = {name: build() for name, build in FIXTURES.items()}

CASES: list[tuple[str, str, str]] = sorted(
    {
        (name, path, action)
        for name, built in BUILT.items()
        for path in _locations(built)
        for action in _ACTIONS
    }
)

#: Roots that are well-formed JSON but not a canonical request object. The entry point read
#: the schema version before its own shape gate, so these leaked `AttributeError` past the
#: guard written to reject them.
NON_OBJECT_ROOTS: list[Any] = [None, [], "request", 7, True]

#: What the measurement is expected to span. Stated as data so a fixture that silently
#: stops contributing locations fails the measurement rather than shrinking it.
EXPECTED_SPAN: dict[str, dict[str, int]] = {
    "request": {"locations": 266},
    # R6-F4: closure_evaluation.kernel_source_witness_ref is one new reachable location.
    "predecessor": {"locations": 1030},
}


def outcome(request: Any, derive: Any = derive_differences) -> str:
    """Classify one derivation. The single place this measurement decides an outcome.

    ``derive`` is a parameter so the positive controls can point the classifier at a known
    raw-raiser and a known good call and prove it distinguishes them -- a harness that
    cannot detect a leak reports zero leaks.
    """

    try:
        derive(request)
    except DifferenceError:
        return "REJECTED"
    except Exception as error:
        return f"RAW:{type(error).__name__}: {error}"
    return "DERIVED"


def test_the_sweep_covers_the_whole_request() -> None:
    """The surface is real: a few hundred locations, and the control derives."""

    assert len(CASES) > 1000
    assert derive_differences(_request())["differences"]
    # And the locations the last rounds each found are among them.
    paths = {path for _name, path, _action in CASES}
    for path in (
        "bindings[0].observation_bundle.facts[0].fact_id",
        "bindings[0].observation_bundle.bindings[0].binding_id",
        "bindings[0].observation_bundle.observations[0].normalized_fact_refs",
        "bindings[0].target_predicate_id",
        "objective_revision",
        "bindings[0].predecessor.context.observations[0].observation_id",
        "bindings[0].predecessor.events[0].event_revision",
        "bindings[0].predecessor.difference",
    ):
        assert path in paths, path


@pytest.mark.parametrize("fixture", sorted(EXPECTED_SPAN))
def test_the_inventory_is_neither_truncated_nor_shrunk(fixture: str) -> None:
    """A fixture that stops contributing locations fails the measurement.

    Two ways a sweep can report clean without being clean: the depth bound clips the
    surface, or a fixture quietly stops reaching part of it. Both are measured here rather
    than assumed, because a smaller inventory is exactly what a false-clean run looks like.
    """

    built = BUILT[fixture]
    assert _depth_of(built) <= _MAX_DEPTH, (
        f"{fixture} nests deeper than the sweep walks: the inventory is truncated"
    )
    reached = len(set(_locations(built)))
    assert reached == EXPECTED_SPAN[fixture]["locations"], (
        f"{fixture} reaches {reached} locations, expected "
        f"{EXPECTED_SPAN[fixture]['locations']}"
    )


def test_every_mutation_applies_or_the_measurement_fails() -> None:
    """Every case must be applicable. A failed mutation is a harness fault, not a skip.

    This is the check whose absence made an earlier run report four leaks instead of
    nineteen. It is stated once, over every case, so a path the parser cannot round-trip
    fails one obvious test instead of disappearing into the count.
    """

    faults: list[str] = []
    for name, path, action in CASES:
        request = deepcopy(BUILT[name])
        try:
            _mutate(request, path, action)
        except Exception as error:
            faults.append(f"{name} {path} [{action}]: {type(error).__name__}: {error}")
    assert faults == [], f"{len(faults)} mutations could not be applied: {faults[:5]}"


def test_every_path_round_trips_through_the_parser() -> None:
    """``_steps`` must reach the location ``_locations`` named, for every path."""

    unreachable: list[str] = []
    for name, built in BUILT.items():
        for path in _locations(built):
            node: Any = built
            try:
                for _kind, step in _steps(path):
                    node = node[step]
            except Exception as error:
                unreachable.append(f"{name} {path}: {type(error).__name__}: {error}")
    assert unreachable == [], f"{len(unreachable)} paths do not resolve: {unreachable[:5]}"


def test_the_classifier_detects_a_known_raw_exception() -> None:
    """Positive control: the harness reports a leak when one is there.

    A measurement that cannot fail proves nothing. These point the classifier at calls whose
    outcome is known by construction and assert it tells them apart.
    """

    def raises_raw(_request: Any) -> None:
        empty: dict[str, str] = {}
        empty["absent"]  # a deliberate KeyError: the exact shape being detected

    def raises_canonical(_request: Any) -> None:
        raise DifferenceError("a canonical rejection")

    def derives(_request: Any) -> dict[str, Any]:
        return {"differences": []}

    assert outcome(None, raises_raw).startswith("RAW:KeyError")
    assert outcome(None, raises_canonical) == "REJECTED"
    assert outcome(None, derives) == "DERIVED"


def test_the_classifier_reaches_a_known_good_derivation() -> None:
    """Positive control: an unmutated fixture derives, through the real entry point."""

    for name, built in BUILT.items():
        assert outcome(deepcopy(built)) == "DERIVED", name


@pytest.mark.parametrize("root", NON_OBJECT_ROOTS)
def test_a_non_object_request_root_is_reported_not_raised(root: Any) -> None:
    with pytest.raises(DifferenceError, match="derivation request is not a canonical object"):
        derive_differences(root)


@pytest.mark.parametrize(("fixture", "path", "action"), CASES, ids=lambda item: str(item))
def test_no_reachable_input_produces_a_raw_exception(
    fixture: str, path: str, action: str
) -> None:
    """Derive, or reject canonically. Never a `KeyError`, `TypeError` or `AttributeError`.

    Success is a legitimate outcome for many of these: an optional key with a default is
    absent, or a retyped Target value is a perfectly good `INTEGER` that simply does not
    match. What is asserted is the property the boundary documents -- that no input reaches
    an implementation exception -- not that every mutation is rejected.
    """

    request = deepcopy(BUILT[fixture])
    _mutate(request, path, action)
    result = outcome(request)
    assert not result.startswith("RAW:"), f"{action} {path} produced {result}"
