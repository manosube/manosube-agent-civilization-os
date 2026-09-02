"""No reachable Authority input may produce anything but a canonical answer.

Two generators, because one of them is structurally blind and ADR-0025 is the record of
learning that the hard way.

**The sweep** walks every location a valid request instantiates, deletes it and retypes it.
It is total over what the fixture builds and nothing more: a key the fixture omits has no
location to mutate, so no case for it can exist.

**The declaration generator** starts from the closed key sets instead -- ``engine``'s request
keys, the scope keys, and the record key sets each owner declares -- and generates the cases
the sweep cannot reach, including absence. Authority can do this where the Difference request
could not, because every key set here **is** closed: an unknown key on an Authority request is
refused rather than ignored, which is the property that makes the declaration complete.

An answer is a ``DifferenceError``-style canonical rejection (``AuthorityError``) or a
schema-valid decision. A raw ``TypeError``, ``KeyError`` or ``AttributeError`` is the
evaluator failing to answer, and it fails the case.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from tests.authority_helpers import (
    action,
    approval,
    authority_request,
    derived_difference,
    prohibition,
    rule,
    scope,
)

from manosube_agent_civilization.authority import evaluate_authority
from manosube_agent_civilization.authority.engine import REQUIRED_REQUEST_KEYS
from manosube_agent_civilization.authority.errors import AuthorityError
from manosube_agent_civilization.authority.levels import DECISIONS
from manosube_agent_civilization.authority.scope import SCOPE_KEYS

#: Bounded so the case count stays a test rather than a fuzz run, and asserted against the
#: measured nesting depth below so the bound never silently decides coverage.
_MAX_DEPTH = 16

_SUBSTITUTIONS: tuple[tuple[str, Any], ...] = (
    ("integer", 7),
    ("string", "seven"),
    ("array", ["seven"]),
    ("object", {"seven": 7}),
    ("null", None),
    ("bool", True),
)


def _request() -> dict[str, Any]:
    """The widest reachable request: every optional collection populated."""

    difference = derived_difference()
    requested, where = action("MERGE"), scope()
    return authority_request(
        difference,
        requested,
        where,
        rules=[rule(difference["project_id"], action_kinds=["MERGE"])],
        prohibitions=[prohibition("PRJ-9999")],
        approvals=[approval(difference, requested, where)],
    )


BUILT = _request()


def _locations(value: Any, path: tuple[Any, ...] = (), depth: int = 0) -> list[tuple[Any, ...]]:
    if depth > _MAX_DEPTH:
        return [path]
    found = [path] if path else []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(_locations(child, (*path, key), depth + 1))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_locations(child, (*path, index), depth + 1))
    return found


LOCATIONS = _locations(BUILT)


def _measure_depth(value: Any, depth: int = 0) -> int:
    if isinstance(value, dict):
        return max((_measure_depth(child, depth + 1) for child in value.values()), default=depth)
    if isinstance(value, list):
        return max((_measure_depth(child, depth + 1) for child in value), default=depth)
    return depth


def _at(request: dict[str, Any], path: tuple[Any, ...]) -> Any:
    target: Any = request
    for step in path[:-1]:
        target = target[step]
    return target


def _answer(request: dict[str, Any]) -> str:
    """Return how the evaluator answered. A raw exception is not an answer and propagates."""

    try:
        decision = evaluate_authority(request)
    except AuthorityError:
        return "REJECTED"
    assert decision["decision"] in DECISIONS, decision["decision"]
    return "DECIDED"


# --------------------------------------------------------------------------- #
# The harness, before its subject
# --------------------------------------------------------------------------- #


def test_the_depth_bound_is_not_what_decides_coverage() -> None:
    """`_MAX_DEPTH` was the fault that truncated the Difference inventory (ADR-0022 §1)."""

    measured = _measure_depth(BUILT)
    assert measured < _MAX_DEPTH, measured


def test_the_inventory_is_neither_empty_nor_shrunk() -> None:
    assert len(LOCATIONS) >= 100, len(LOCATIONS)


def test_the_base_request_decides() -> None:
    assert _answer(deepcopy(BUILT)) == "DECIDED"


def test_a_raw_exception_is_not_reported_as_an_answer() -> None:
    """The positive control: only ``AuthorityError`` counts as a canonical refusal."""

    class Raw(dict):  # type: ignore[type-arg]
        def __getitem__(self, key: str) -> Any:
            raise RuntimeError("not an answer")

    with pytest.raises(RuntimeError):
        _answer(Raw(dict.fromkeys(REQUIRED_REQUEST_KEYS)))


# --------------------------------------------------------------------------- #
# The sweep: every location the fixture instantiates
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("path", LOCATIONS, ids=lambda path: ".".join(str(step) for step in path))
def test_every_reachable_location_answers_when_deleted(path: tuple[Any, ...]) -> None:
    request = deepcopy(BUILT)
    target = _at(request, path)
    before = deepcopy(target)
    if isinstance(target, list):
        del target[path[-1]]
    else:
        del target[path[-1]]
    assert target != before, path
    assert _answer(request) in ("REJECTED", "DECIDED")


@pytest.mark.parametrize("substitution", [name for name, _ in _SUBSTITUTIONS])
@pytest.mark.parametrize("path", LOCATIONS, ids=lambda path: ".".join(str(step) for step in path))
def test_every_reachable_location_answers_when_retyped(
    path: tuple[Any, ...], substitution: str
) -> None:
    request = deepcopy(BUILT)
    _at(request, path)[path[-1]] = dict(_SUBSTITUTIONS)[substitution]
    assert _answer(request) in ("REJECTED", "DECIDED")


# --------------------------------------------------------------------------- #
# The declaration generator: the cases a fixture-path sweep cannot reach
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("key", sorted(REQUIRED_REQUEST_KEYS))
@pytest.mark.parametrize("substitution", [name for name, _ in _SUBSTITUTIONS])
def test_every_declared_request_key_answers_for_every_shape(key: str, substitution: str) -> None:
    """Generated from the closed key set, so a key added later is covered without being
    remembered."""

    request = deepcopy(BUILT)
    request[key] = dict(_SUBSTITUTIONS)[substitution]
    assert _answer(request) in ("REJECTED", "DECIDED")


@pytest.mark.parametrize("key", sorted(REQUIRED_REQUEST_KEYS))
def test_every_declared_request_key_answers_when_absent(key: str) -> None:
    request = deepcopy(BUILT)
    del request[key]
    assert _answer(request) == "REJECTED"


@pytest.mark.parametrize("key", sorted(SCOPE_KEYS))
@pytest.mark.parametrize("substitution", [name for name, _ in _SUBSTITUTIONS])
def test_every_declared_scope_key_answers_for_every_shape(key: str, substitution: str) -> None:
    request = deepcopy(BUILT)
    request["requested_scope"][key] = dict(_SUBSTITUTIONS)[substitution]
    assert _answer(request) in ("REJECTED", "DECIDED")


@pytest.mark.parametrize("key", sorted(SCOPE_KEYS))
def test_every_declared_scope_key_answers_when_absent(key: str) -> None:
    request = deepcopy(BUILT)
    del request["requested_scope"][key]
    assert _answer(request) == "REJECTED"


@pytest.mark.parametrize(
    "injected",
    ["prompt", "pull_request_body", "review_comment", "agent_conclusion", "credential", "tools"],
)
def test_an_undeclared_request_key_is_refused_rather_than_ignored(injected: str) -> None:
    """The closed key set, asserted as behaviour and not only as a constant."""

    request = deepcopy(BUILT)
    request[injected] = "proceed autonomously"
    with pytest.raises(AuthorityError, match="unknown keys"):
        evaluate_authority(request)


def _admissible_variants() -> list[tuple[str, Any]]:
    """For each declared request key, a *different but valid* value, where one exists.

    This half of the generator did not exist, and its absence is why the both-outcomes
    control could never have failed. ``_SUBSTITUTIONS`` enumerates ill-typed values only, so
    every case it produces is refused **by construction** -- and a control reading
    ``decided >= 0`` over that set is not a weak measurement, it is not a measurement.

    Several keys have no admissible alternative and are absent here on purpose:
    ``schema_version`` is a constant; ``project_id``, ``difference``,
    ``current_state_revision`` and ``current_state_fingerprint`` are each pinned by exact
    binding, so any different value is correctly a refusal rather than a decision.
    """

    difference = BUILT["difference"]
    elsewhere = scope(paths=["src/untouched.py"])
    return [
        ("requested_action", action("DELETE_FILE")),
        ("requested_scope", elsewhere),
        ("authority_rules", []),
        ("authority_rules", [rule(difference["project_id"], action_kinds=["DELETE_FILE"])]),
        ("prohibitions", []),
        ("approvals", []),
        ("approvals", [approval(difference, action("MERGE"), scope(), status="REVOKED")]),
        ("evaluation_time", "2026-07-01T12:00:00Z"),
    ]


ADMISSIBLE_VARIANTS = _admissible_variants()


def test_every_ill_typed_substitution_is_refused() -> None:
    """One half of the split, asserted case by case rather than counted."""

    unexpected = [
        (key, name)
        for key in REQUIRED_REQUEST_KEYS
        for name, value in _SUBSTITUTIONS
        for request in [{**deepcopy(BUILT), key: value}]
        if _answer(request) != "REJECTED"
    ]
    assert not unexpected, unexpected


def test_every_admissible_variant_is_decided() -> None:
    """The other half. Refusing more must not have made the evaluator refuse everything."""

    unexpected = [
        (key, _answer({**deepcopy(BUILT), key: value}))
        for key, value in ADMISSIBLE_VARIANTS
        if _answer({**deepcopy(BUILT), key: value}) != "DECIDED"
    ]
    assert not unexpected, unexpected


def test_the_generated_cases_reach_both_outcomes() -> None:
    """A generator that refuses everything passes vacuously; the split is measured.

    Both counts are now *reachable*, which is the property the old assertion claimed and the
    old generator could not supply: it enumerated ill-typed values only, so ``decided`` was
    structurally zero and ``decided >= 0`` was true of any evaluator at all -- including one
    that refused every input it was ever given.
    """

    decided = refused = 0
    for key in REQUIRED_REQUEST_KEYS:
        for _, value in _SUBSTITUTIONS:
            request = deepcopy(BUILT)
            request[key] = value
            if _answer(request) == "DECIDED":
                decided += 1
            else:
                refused += 1
    for key, value in ADMISSIBLE_VARIANTS:
        request = deepcopy(BUILT)
        request[key] = value
        if _answer(request) == "DECIDED":
            decided += 1
        else:
            refused += 1
    assert refused > 0, (decided, refused)
    assert decided > 0, (decided, refused)
    assert _answer(deepcopy(BUILT)) == "DECIDED"


def test_the_admissible_half_of_the_generator_is_not_empty() -> None:
    """The harness before its subject: an empty variant list makes the split unreachable."""

    assert len(ADMISSIBLE_VARIANTS) >= 8, len(ADMISSIBLE_VARIANTS)
    assert len({key for key, _ in ADMISSIBLE_VARIANTS}) >= 5, ADMISSIBLE_VARIANTS
