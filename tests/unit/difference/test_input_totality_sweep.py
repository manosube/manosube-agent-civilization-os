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
)

from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.errors import DifferenceError

#: Depth is bounded so the case count stays a test rather than a fuzz run; every location
#: the derivation itself reads is well within it.
_MAX_DEPTH = 8


def _request() -> dict[str, Any]:
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


def _mutate(request: dict[str, Any], path: str, action: str) -> None:
    steps = _steps(path)
    node: Any = request
    for _kind, step in steps[:-1]:
        node = node[step]
    _kind, last = steps[-1]
    if action == "delete":
        del node[last]
    else:
        node[last] = 7 if not isinstance(node[last], int) else "seven"


CASES: list[tuple[str, str]] = sorted(
    {(path, action) for path in _locations(_request()) for action in ("delete", "retype")}
)


def test_the_sweep_covers_the_whole_request() -> None:
    """The surface is real: a few hundred locations, and the control derives."""

    assert len(CASES) > 300
    assert derive_differences(_request())["differences"]
    # And the locations the last four rounds each found are among them.
    paths = {path for path, _action in CASES}
    for path in (
        "bindings[0].observation_bundle.facts[0].fact_id",
        "bindings[0].observation_bundle.bindings[0].binding_id",
        "bindings[0].observation_bundle.observations[0].normalized_fact_refs",
        "bindings[0].target_predicate_id",
        "objective_revision",
    ):
        assert path in paths, path


@pytest.mark.parametrize(("path", "action"), CASES, ids=lambda item: str(item))
def test_no_reachable_input_produces_a_raw_exception(path: str, action: str) -> None:
    """Derive, or reject canonically. Never a `KeyError`, `TypeError` or `AttributeError`.

    Success is a legitimate outcome for many of these: an optional key with a default is
    absent, or a retyped Target value is a perfectly good `INTEGER` that simply does not
    match. What is asserted is the property the boundary documents -- that no input reaches
    an implementation exception -- not that every mutation is rejected.
    """

    request = _request()
    _mutate(request, path, action)
    try:
        derive_differences(request)
    except DifferenceError:
        return
    except Exception as error:  # pragma: no cover - the failure this test exists to catch
        pytest.fail(f"{action} {path} raised {type(error).__name__}: {error}")
