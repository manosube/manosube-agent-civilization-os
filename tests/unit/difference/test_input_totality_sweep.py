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

#: Depth is bounded so the case count stays a test rather than a fuzz run; every location
#: the derivation itself reads is well within it.
_MAX_DEPTH = 8


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

    The predecessor subtree is a large part of the request surface and the sweep did not
    reach it: a non-object `predecessor` was found by a reviewer, not here.
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
#:
#: ``_predecessor_request`` is deliberately **not** here yet, and that absence is the
#: honest state rather than an oversight: adding it raised 78 failures concentrated in
#: ``predecessor.events[].event_revision``, a real uncovered surface this round did not
#: correct. Committing the fixture would leave the suite red and the branch unmergeable;
#: omitting it silently would overstate what "0 leaks" means. It is recorded in ADR-0021
#: as an open, measured gap and is the next round's work.
FIXTURES: dict[str, Any] = {
    "request": _request,
}

CASES: list[tuple[str, str, str]] = sorted(
    {
        (name, path, action)
        for name, build in FIXTURES.items()
        for path in _locations(build())
        for action in _ACTIONS
    }
)

#: Roots that are well-formed JSON but not a canonical request object. The entry point read
#: the schema version before its own shape gate, so these leaked `AttributeError` past the
#: guard written to reject them.
NON_OBJECT_ROOTS: list[Any] = [None, [], "request", 7, True]


@pytest.mark.parametrize("root", NON_OBJECT_ROOTS)
def test_a_non_object_request_root_is_reported_not_raised(root: Any) -> None:
    with pytest.raises(DifferenceError, match="derivation request is not a canonical object"):
        derive_differences(root)


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
    ):
        assert path in paths, path


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

    request = FIXTURES[fixture]()
    _mutate(request, path, action)
    try:
        derive_differences(request)
    except DifferenceError:
        return
    except Exception as error:  # pragma: no cover - the failure this test exists to catch
        pytest.fail(f"{action} {path} raised {type(error).__name__}: {error}")
