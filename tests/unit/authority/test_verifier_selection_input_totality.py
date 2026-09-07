"""No reachable Verifier Selection Decision input may produce anything but a canonical answer.

The same declaration-and-sweep pattern ``test_authority_input_totality.py`` uses for
``evaluate_authority``'s own request, applied to ``evaluate_verifier_selection``'s request
(Structural Review Round 3, P13-R3-F1). This is the suite
``difference.admissibility.UNCONSTRAINED_CONTRACT_LOCATIONS`` names when it tags
``verifier_identity`` and ``permitted_boundary`` (on both the request and the grants it
carries) ``AUTHORITY_INPUT``: an unconstrained schema location is only real coverage once some
owner suite is generated against it, and this file is that suite for these four locations.

**The sweep** walks every location the built request instantiates, deletes it and retypes it.
**The declaration generator** starts from ``REQUIRED_REQUEST_KEYS`` instead, so a key added
later is covered without being remembered -- the request's own key set is closed (an unknown
key is refused, never ignored), which is what makes the declaration complete.

An answer is a canonical ``AuthorityError`` rejection or a schema-valid decision. A raw
``TypeError``, ``KeyError`` or ``AttributeError`` is the evaluator failing to answer, and it
fails the case.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from manosube_agent_civilization.authority import AuthorityError, evaluate_verifier_selection
from manosube_agent_civilization.authority.identity import verifier_selection_grant_id
from manosube_agent_civilization.authority.verifier_selection import (
    DECISIONS,
    REQUIRED_REQUEST_KEYS,
)
from manosube_agent_civilization.binding.identity import human_grant_declaration_id

pytestmark = pytest.mark.contract

_HUMAN = {"kind": "human_authority", "id": "AUTH-0001"}
_VERIFIER_IDENTITY = {"kind": "deterministic_test_runner", "id": "VERIFIER-0001"}
_BOUNDARY = {"scope": "repository", "boundary_id": "VB-0001"}
_PROJECT_BINDING_ID = "PROJBIND-" + "0" * 64
_DECLARED_AT = "2026-09-07T13:00:00Z"

#: Ill-typed values, one per JSON type -- the same substitution set
#: ``test_authority_input_totality.py`` uses for the same reason: every case they generate is
#: refused *by type*.
_SUBSTITUTIONS: tuple[tuple[str, Any], ...] = (
    ("integer", 7),
    ("string", "seven"),
    ("array", ["seven"]),
    ("object", {"seven": 7}),
    ("null", None),
    ("bool", True),
)


def _grant(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": "0.1",
        "verifier_selection_grant_id": "",
        "project_id": "PRJ-0001",
        "requirement_id": "VREQ-0001",
        "selection_id": "VSEL-0001",
        "verifier_identity": dict(_VERIFIER_IDENTITY),
        "permitted_boundary": dict(_BOUNDARY),
        "status": "ACTIVE",
        "granted_by": dict(_HUMAN),
    }
    record.update(overrides)
    record["verifier_selection_grant_id"] = verifier_selection_grant_id(record)
    return record


def _declaration(grant: dict[str, Any] | None = None, **overrides: Any) -> dict[str, Any]:
    bound_grant = grant if grant is not None else _grant()
    record: dict[str, Any] = {
        "schema_version": "0.1",
        "human_grant_declaration_id": "",
        "project_id": "PRJ-0001",
        "project_binding_id": _PROJECT_BINDING_ID,
        "grant_ref": {
            "kind": "verifier_selection_grant",
            "id": bound_grant["verifier_selection_grant_id"],
        },
        "declared_by": dict(_HUMAN),
        "status": "ACTIVE",
        "declared_at": _DECLARED_AT,
    }
    record.update(overrides)
    record["human_grant_declaration_id"] = human_grant_declaration_id(record)
    return record


def _request() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "project_id": "PRJ-0001",
        "requirement_id": "VREQ-0001",
        "selection_id": "VSEL-0001",
        "verifier_identity": dict(_VERIFIER_IDENTITY),
        "permitted_boundary": dict(_BOUNDARY),
        "selection_status": "ACTIVE",
        "human_authority_ref": dict(_HUMAN),
        "grants": [_grant()],
        "grant_declarations": [_declaration()],
    }


BUILT = _request()


def _locations(value: Any, path: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    found = [path] if path else []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(_locations(child, (*path, key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_locations(child, (*path, index)))
    return found


LOCATIONS = _locations(BUILT)


def _at(request: dict[str, Any], path: tuple[Any, ...]) -> Any:
    target: Any = request
    for step in path[:-1]:
        target = target[step]
    return target


def _answer(request: dict[str, Any]) -> str:
    """Return how the evaluator answered. A raw exception is not an answer and propagates."""

    try:
        decision = evaluate_verifier_selection(request)
    except AuthorityError:
        return "REJECTED"
    assert decision["decision"] in DECISIONS, decision["decision"]
    return "DECIDED"


def test_the_inventory_is_neither_empty_nor_shrunk() -> None:
    assert len(LOCATIONS) >= 15, len(LOCATIONS)


def test_the_base_request_decides() -> None:
    assert _answer(deepcopy(BUILT)) == "DECIDED"


# --------------------------------------------------------------------------- #
# The sweep: every location the fixture instantiates, including the four
# AUTHORITY_INPUT locations (verifier_identity/permitted_boundary, request-level
# and per-grant) UNCONSTRAINED_CONTRACT_LOCATIONS names this file as owning.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("path", LOCATIONS, ids=lambda path: ".".join(str(step) for step in path))
def test_every_reachable_location_answers_when_deleted(path: tuple[Any, ...]) -> None:
    request = deepcopy(BUILT)
    target = _at(request, path)
    before = deepcopy(target)
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
    request = deepcopy(BUILT)
    request[key] = dict(_SUBSTITUTIONS)[substitution]
    assert _answer(request) in ("REJECTED", "DECIDED")


@pytest.mark.parametrize("key", sorted(REQUIRED_REQUEST_KEYS))
def test_every_declared_request_key_answers_when_absent(key: str) -> None:
    request = deepcopy(BUILT)
    del request[key]
    assert _answer(request) == "REJECTED"


def test_an_undeclared_request_key_is_refused_rather_than_ignored() -> None:
    request = deepcopy(BUILT)
    request["prompt"] = "proceed autonomously"
    with pytest.raises(AuthorityError, match="unknown keys"):
        evaluate_verifier_selection(request)
