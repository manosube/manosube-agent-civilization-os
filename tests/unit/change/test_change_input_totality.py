"""No reachable Change input may produce anything but a canonical answer.

Two generators, for the reason ADR-0025 records.

**The sweep** walks every location a derivable request instantiates, deletes it, retypes it
and -- because retyping can only ever produce ill-typed values -- appends a line terminator
to every string it finds. It is total over what the fixture builds and nothing more.

**The declaration generator** starts from the closed key sets instead: the request keys, the
bound decision's keys, the scope keys and the action keys. Change can do this because every
one of those sets is closed; an unknown key is refused rather than ignored, which is the
property that makes the declaration complete.

An answer is a canonical rejection (``ChangeError``) or a schema-valid Change. A raw
``TypeError``, ``KeyError``, ``AttributeError`` -- or an ``AuthorityError`` or
``DifferenceError`` leaking from a delegated owner -- is Change failing to answer in its own
vocabulary, and it fails the case.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from tests.authority_helpers import action, approval, rule, scope
from tests.change_helpers import change_request, decide, derived_difference

from manosube_agent_civilization.authority.scope import SCOPE_KEYS
from manosube_agent_civilization.change import ChangeError, derive_change
from manosube_agent_civilization.change.engine import (
    AUTHORIZED,
    DECISION_REQUIRED_KEYS,
    REQUIRED_REQUEST_KEYS,
)
from manosube_agent_civilization.change.identity import CHANGE_SEMANTIC_FIELDS

#: Bounded so the case count stays a test rather than a fuzz run, and asserted against the
#: measured nesting depth below so the bound never silently decides coverage.
_MAX_DEPTH = 16

#: Ill-typed values, one per JSON type. Every case they generate is refused *by type*, which
#: is why the terminator aliases below are a separate generator: a well-formed string with a
#: terminator appended is the *right* type, so nothing here could produce one.
_SUBSTITUTIONS: tuple[tuple[str, Any], ...] = (
    ("integer", 7),
    ("string", "seven"),
    ("array", ["seven"]),
    ("object", {"seven": 7}),
    ("null", None),
    ("bool", True),
)

#: Same-type aliases: the canonical value with a line terminator or trailing space appended.
#: Written as escapes rather than literals so the source stays reviewable in a terminal.
_TERMINATOR_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("lf", "\n"),
    ("cr", "\r"),
    ("crlf", "\r\n"),
    ("line separator", "\u2028"),
    ("paragraph separator", "\u2029"),
    ("next line", "\u0085"),
    ("trailing space", " "),
)

_ACTION_KEYS: tuple[str, ...] = (
    "action_kind",
    "reversibility",
    "operation",
    "action_semantic_fingerprint",
)


def _built() -> dict[str, Any]:
    """The widest reachable request that actually derives a Change."""

    difference = derived_difference()
    requested, where = action("MERGE"), scope()
    decision = decide(
        difference, requested, where, approvals=[approval(difference, requested, where)]
    )
    assert decision["decision"] == "AUTONOMOUS"
    return change_request(difference, decision, requested, where)


BUILT = _built()


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


def _string_locations(value: Any) -> list[tuple[Any, ...]]:
    """Every location holding a string, where a same-type alias is possible at all."""

    found: list[tuple[Any, ...]] = []
    for path in _locations(value):
        target: Any = value
        for step in path:
            target = target[step]
        if isinstance(target, str):
            found.append(path)
    return found


STRING_LOCATIONS = _string_locations(BUILT)


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
    """Return how the deriver answered. A raw exception is not an answer and propagates."""

    try:
        change = derive_change(request)
    except ChangeError:
        return "REJECTED"
    assert change["status"] == AUTHORIZED, change["status"]
    assert change["execution_result"] is None
    return "DERIVED"


# --------------------------------------------------------------------------- #
# The harness, before its subject
# --------------------------------------------------------------------------- #


def test_the_depth_bound_is_not_what_decides_coverage() -> None:
    measured = _measure_depth(BUILT)
    assert measured < _MAX_DEPTH, measured


def test_the_inventory_is_neither_empty_nor_shrunk() -> None:
    assert len(LOCATIONS) >= 100, len(LOCATIONS)


def test_the_string_inventory_is_neither_empty_nor_shrunk() -> None:
    assert len(STRING_LOCATIONS) >= 40, len(STRING_LOCATIONS)


def test_the_base_request_derives() -> None:
    assert _answer(deepcopy(BUILT)) == "DERIVED"


def test_a_raw_exception_is_not_reported_as_an_answer() -> None:
    """The positive control: only ``ChangeError`` counts as a canonical refusal."""

    class Raw(dict):  # type: ignore[type-arg]
        def __getitem__(self, key: str) -> Any:
            raise RuntimeError("not an answer")

    with pytest.raises(RuntimeError):
        _answer(Raw(dict.fromkeys(REQUIRED_REQUEST_KEYS)))


def test_a_delegated_owners_error_is_not_a_change_error() -> None:
    """``AuthorityError`` is not a ``ChangeError``, so a leak fails rather than counts.

    This control exists because the leak was real: ``admit_difference`` and ``require_scope``
    are Authority's, and their vocabulary reached callers of ``derive_change`` until the
    boundary caught it. Without this, a regression would be scored as "REJECTED".
    """

    from manosube_agent_civilization.authority.errors import AuthorityError
    from manosube_agent_civilization.difference.errors import DifferenceError
    from manosube_agent_civilization.state.errors import CanonicalizationError

    for foreign in (AuthorityError, DifferenceError, CanonicalizationError):
        assert not issubclass(foreign, ChangeError), foreign


# --------------------------------------------------------------------------- #
# The sweep: every location the fixture instantiates
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("path", LOCATIONS, ids=lambda path: ".".join(str(step) for step in path))
def test_every_reachable_location_answers_when_deleted(path: tuple[Any, ...]) -> None:
    request = deepcopy(BUILT)
    target = _at(request, path)
    before = deepcopy(target)
    del target[path[-1]]
    assert target != before, path
    assert _answer(request) in ("REJECTED", "DERIVED")


@pytest.mark.parametrize("substitution", [name for name, _ in _SUBSTITUTIONS])
@pytest.mark.parametrize("path", LOCATIONS, ids=lambda path: ".".join(str(step) for step in path))
def test_every_reachable_location_answers_when_retyped(
    path: tuple[Any, ...], substitution: str
) -> None:
    request = deepcopy(BUILT)
    _at(request, path)[path[-1]] = dict(_SUBSTITUTIONS)[substitution]
    assert _answer(request) in ("REJECTED", "DERIVED")


@pytest.mark.parametrize("suffix", [name for name, _ in _TERMINATOR_SUFFIXES])
@pytest.mark.parametrize(
    "path", STRING_LOCATIONS, ids=lambda path: ".".join(str(step) for step in path)
)
def test_every_string_location_answers_for_every_terminator_alias(
    path: tuple[Any, ...], suffix: str
) -> None:
    """The cases retyping is structurally blind to: right type, wrong terminal grammar."""

    request = deepcopy(BUILT)
    target = _at(request, path)
    target[path[-1]] = target[path[-1]] + dict(_TERMINATOR_SUFFIXES)[suffix]
    assert _answer(request) in ("REJECTED", "DERIVED")


# --------------------------------------------------------------------------- #
# The declaration generator: the cases a fixture-path sweep cannot reach
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("key", sorted(REQUIRED_REQUEST_KEYS))
@pytest.mark.parametrize("substitution", [name for name, _ in _SUBSTITUTIONS])
def test_every_declared_request_key_answers_for_every_shape(key: str, substitution: str) -> None:
    request = deepcopy(BUILT)
    request[key] = dict(_SUBSTITUTIONS)[substitution]
    assert _answer(request) in ("REJECTED", "DERIVED")


@pytest.mark.parametrize("key", sorted(REQUIRED_REQUEST_KEYS))
def test_every_declared_request_key_answers_when_absent(key: str) -> None:
    request = deepcopy(BUILT)
    del request[key]
    assert _answer(request) == "REJECTED"


@pytest.mark.parametrize("key", sorted(DECISION_REQUIRED_KEYS))
@pytest.mark.parametrize("substitution", [name for name, _ in _SUBSTITUTIONS])
def test_every_declared_decision_key_answers_for_every_shape(key: str, substitution: str) -> None:
    request = deepcopy(BUILT)
    request["authority_decision"][key] = dict(_SUBSTITUTIONS)[substitution]
    assert _answer(request) in ("REJECTED", "DERIVED")


@pytest.mark.parametrize("key", sorted(DECISION_REQUIRED_KEYS))
def test_every_declared_decision_key_answers_when_absent(key: str) -> None:
    request = deepcopy(BUILT)
    del request["authority_decision"][key]
    assert _answer(request) == "REJECTED"


@pytest.mark.parametrize("key", sorted(SCOPE_KEYS))
@pytest.mark.parametrize("substitution", [name for name, _ in _SUBSTITUTIONS])
def test_every_declared_scope_key_answers_for_every_shape(key: str, substitution: str) -> None:
    request = deepcopy(BUILT)
    request["requested_scope"][key] = dict(_SUBSTITUTIONS)[substitution]
    assert _answer(request) in ("REJECTED", "DERIVED")


@pytest.mark.parametrize("key", sorted(SCOPE_KEYS))
def test_every_declared_scope_key_answers_when_absent(key: str) -> None:
    request = deepcopy(BUILT)
    del request["requested_scope"][key]
    assert _answer(request) == "REJECTED"


@pytest.mark.parametrize("key", sorted(_ACTION_KEYS))
@pytest.mark.parametrize("substitution", [name for name, _ in _SUBSTITUTIONS])
def test_every_declared_action_key_answers_for_every_shape(key: str, substitution: str) -> None:
    request = deepcopy(BUILT)
    request["requested_action"][key] = dict(_SUBSTITUTIONS)[substitution]
    assert _answer(request) in ("REJECTED", "DERIVED")


@pytest.mark.parametrize("key", sorted(_ACTION_KEYS))
def test_every_declared_action_key_answers_when_absent(key: str) -> None:
    request = deepcopy(BUILT)
    del request["requested_action"][key]
    assert _answer(request) == "REJECTED"


@pytest.mark.parametrize(
    "injected",
    ["prompt", "pull_request_body", "review_comment", "agent_conclusion", "credential", "tools"],
)
def test_an_undeclared_request_key_is_refused_rather_than_ignored(injected: str) -> None:
    request = deepcopy(BUILT)
    request[injected] = "proceed autonomously"
    with pytest.raises(ChangeError, match="unknown keys"):
        derive_change(request)


@pytest.mark.parametrize("injected", ["change_id", "status", "execution_result", "idempotency_key"])
def test_a_caller_supplied_derived_field_is_refused(injected: str) -> None:
    """``PREEXISTING_CHANGE_ID_REQUIRED=false``: the request has no entry for any of these.

    A caller who could supply ``change_id`` could name two different changes with one
    address; one who could supply ``idempotency_key`` could make two changes collide.
    """

    request = deepcopy(BUILT)
    request[injected] = "CHANGE-" + "0" * 64
    with pytest.raises(ChangeError, match="unknown keys"):
        derive_change(request)


# --------------------------------------------------------------------------- #
# Both outcomes are reachable
# --------------------------------------------------------------------------- #
#
# The sweeps above accept "REJECTED or DERIVED", and every case _SUBSTITUTIONS and
# _TERMINATOR_SUFFIXES produce is refused *by construction*. A both-outcomes control built
# from those generators would therefore never fail -- it would not be a weak measurement,
# it would not be a measurement.
#
# The Change request has no free parameter to vary: every field is pinned to the bound
# decision by exact binding (CHANGE_CONTRACT.md 7), so any single-field edit is correctly a
# refusal. The reachable DERIVED outcomes are therefore whole consistent requests, each
# built independently through the real Difference and Authority route.


def _derivable_variants() -> list[tuple[str, dict[str, Any]]]:
    difference = derived_difference()
    permitting = rule(difference["project_id"])
    variants: list[tuple[str, dict[str, Any]]] = []

    requested, where = action(), scope()
    variants.append(
        (
            "rule permitted write",
            change_request(
                difference, decide(difference, requested, where, rules=[permitting]), requested, where
            ),
        )
    )

    requested, where = action("MERGE"), scope()
    variants.append(
        (
            "exactly approved merge",
            change_request(
                difference,
                decide(difference, requested, where, approvals=[approval(difference, requested, where)]),
                requested,
                where,
            ),
        )
    )

    requested = action("WRITE_FILE", operation={"path": "src/app.py", "bytes": "AAAA"})
    where = scope()
    variants.append(
        (
            "a different operation payload",
            change_request(
                difference, decide(difference, requested, where, rules=[permitting]), requested, where
            ),
        )
    )

    requested = action("RUN_COMMAND", operation={"argv": ["pytest", "-q"]})
    where = scope(paths=["src/app.py", "src/lib.py"], subjects=["svc:api"])
    widened = rule(difference["project_id"], action_kinds=["RUN_COMMAND"], rule_scope=where)
    variants.append(
        (
            "a wider enumerated scope",
            change_request(
                difference, decide(difference, requested, where, rules=[widened]), requested, where
            ),
        )
    )
    return variants


DERIVABLE = _derivable_variants()


@pytest.mark.parametrize("name,built", DERIVABLE, ids=[name for name, _ in DERIVABLE])
def test_the_derived_outcome_is_reachable(name: str, built: dict[str, Any]) -> None:
    assert _answer(deepcopy(built)) == "DERIVED"


def test_the_derivable_variants_are_genuinely_distinct() -> None:
    """Four requests that all derive, and no two of them derive the same Change."""

    identities = {derive_change(deepcopy(built))["change_id"] for _, built in DERIVABLE}
    assert len(identities) == len(DERIVABLE), identities


def test_the_identity_projection_is_closed_and_complete() -> None:
    """Every semantic field is a Change field, and lifecycle is deliberately outside it."""

    change = derive_change(deepcopy(BUILT))
    assert set(CHANGE_SEMANTIC_FIELDS) <= set(change)
    assert "status" not in CHANGE_SEMANTIC_FIELDS
    assert "execution_result" not in CHANGE_SEMANTIC_FIELDS
    assert "change_id" not in CHANGE_SEMANTIC_FIELDS
