"""Input admissibility has exactly one owner, and no consumer restates it.

`5d9f407` carried three findings and they were one defect: a value was hashed, sorted or
indexed before anything established it could be. Correcting them where they were reported
would have been three guards -- and three guards is how the previous four rounds went, each
closing the case in front of it while the next layer stayed open.

So the decision is owned once, in `difference.admissibility`, and this file holds that in
both directions:

* every module that decides whether an input can be read delegates to the owner;
* no module outside it expresses that decision itself.

The second direction is the one that matters, and it is deliberately coarse. A source-level
scan fails any rejection written as a negated type test anywhere under ``difference/``,
whether or not anyone remembered to add a delegation assertion for it. Counting call sites
after the fact is exactly what let the `a11d7c7` readability split happen (ADR-0023): the
gate and the record boundary disagreed about what a readable record was, inside the gate
written so they could not.

The two owners are not merged and do not overlap. ``readability`` answers whether a *typed
canonical record* can be read as that type; ``admissibility`` answers whether a *raw request
value* can bear the operation about to be applied to it. ``readability`` is a consumer of
the second question, not a second answer to it.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from manosube_agent_civilization.difference import (
    admissibility,
    canonical,
    conformance,
    engine,
    predecessor,
    projection,
    readability,
    selection,
)

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "src" / "manosube_agent_civilization" / "difference"
OWNER = SOURCE / "admissibility.py"

#: Everything the owner decides. A name added to the owner is delegated-or-not by name here,
#: rather than by whoever remembers to extend a list.
DECISIONS = (
    "is_scalar_tag",
    "is_canonical_object",
    "is_collection",
    "require_scalar_tag",
    "require_object",
    "require_collection",
    "require_optional_object",
)

#: Every module that asks the question. Adding a consumer without adding it here is caught
#: by ``test_no_module_outside_the_owner_expresses_the_decision``, not by this list.
DELEGATING_MODULES: dict[str, Any] = {
    "difference.canonical": canonical,
    "difference.conformance": conformance,
    "difference.engine": engine,
    "difference.predecessor": predecessor,
    "difference.projection": projection,
    "difference.readability": readability,
    "difference.selection": selection,
}


def test_the_record_readability_owner_asks_rather_than_answers_again() -> None:
    """The two owners meet here, and the meeting is an alias rather than a second answer.

    ``readability.is_record_list`` is the name its callers ask by; the object is
    ``admissibility.is_collection``. An alias cannot drift, a re-implementation can, and a
    re-implementation of exactly this predicate under a second name is the `a11d7c7` fault.
    """

    assert vars(readability)["is_record_list"] is admissibility.is_collection
    assert vars(readability)["is_canonical_object"] is admissibility.is_canonical_object


def test_the_owner_declares_every_decision_this_file_pins() -> None:
    """The list above is held to the owner, so a renamed decision fails loudly."""

    for name in DECISIONS:
        assert callable(getattr(admissibility, name)), name


@pytest.mark.parametrize("module_name", sorted(DELEGATING_MODULES))
def test_every_consumer_holds_the_owner_and_not_a_copy(module_name: str) -> None:
    """Object identity, not name equality: a re-implementation under the same name fails."""

    module = DELEGATING_MODULES[module_name]
    bound = [name for name in DECISIONS if name in vars(module)]
    assert bound, f"{module_name} imports no decision and should not be listed"
    for name in bound:
        assert vars(module)[name] is getattr(admissibility, name), f"{module_name}.{name}"


def test_every_module_that_imports_a_decision_is_listed() -> None:
    """The other direction of the consumer list itself."""

    listed = {module.__name__.split(".", 1)[1] for module in DELEGATING_MODULES.values()}
    importing = set()
    for path in sorted(SOURCE.glob("*.py")):
        if path == OWNER:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "admissibility"
                and any(alias.name in DECISIONS for alias in node.names)
            ):
                importing.add(f"difference.{path.stem}")
    assert importing == listed


# --------------------------------------------------------------------------- #
# The coarse direction
# --------------------------------------------------------------------------- #

#: The three shapes the owner answers for -- object, collection, tag -- and only those. A
#: negated ``isinstance(x, int)`` guarding a raise is a *value-domain* rule (a State revision
#: is a non-negative integer), which the owner does not decide and this scan does not claim.
_TYPE_NAMES = frozenset({"dict", "list", "str"})


def _rejections_by_type_test_in(source: str) -> list[int]:
    """Return the lines where this module rejects on a negated ``isinstance``.

    A *negated* type test guarding a raise is the restatement pattern, and only that: a
    positive ``isinstance`` guarding a raise states a rule about a shape that is legitimately
    present -- a bare array reachable from an identity projection, a string that carries
    secret material -- which is a different question with a different owner, and is left
    alone rather than swept into an exemption list.
    """

    found: list[int] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if not any(isinstance(statement, ast.Raise) for statement in node.body):
            continue
        for sub in ast.walk(node.test):
            if not (isinstance(sub, ast.UnaryOp) and isinstance(sub.op, ast.Not)):
                continue
            for call in ast.walk(sub.operand):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "isinstance"
                    and len(call.args) == 2
                ):
                    annotation = call.args[1]
                    names = (
                        [annotation]
                        if isinstance(annotation, ast.Name)
                        else list(getattr(annotation, "elts", []))
                    )
                    if any(
                        isinstance(name, ast.Name) and name.id in _TYPE_NAMES for name in names
                    ):
                        found.append(node.lineno)
    return sorted(set(found))


def _rejections_by_type_test(path: Path) -> list[int]:
    return _rejections_by_type_test_in(path.read_text(encoding="utf-8"))


def test_the_scan_detects_the_pattern_it_is_asked_to_forbid() -> None:
    """The harness before the subject: a scan that finds nothing passes every assertion.

    The controls are written here rather than pointed at a module, because the owner's own
    implementation is free to change and a control that depends on it stops being one.
    """

    restating = "def f(value):\n    if not isinstance(value, dict):\n        raise ValueError\n"
    assert _rejections_by_type_test_in(restating) == [2]
    # And the three shapes it must not claim: a value-domain rule, a positive type test
    # stating a rule about a shape that is legitimately present, and a delegated predicate.
    for allowed in (
        "def f(v):\n    if not isinstance(v, int):\n        raise ValueError\n",
        "def f(v):\n    if isinstance(v, list):\n        raise ValueError\n",
        "def f(v):\n    if not is_canonical_object(v):\n        raise ValueError\n",
    ):
        assert _rejections_by_type_test_in(allowed) == []


def test_no_module_outside_the_owner_expresses_the_decision() -> None:
    """One answer to 'can this be read', everywhere under ``difference/``."""

    restated = {
        path.name: lines
        for path in sorted(SOURCE.glob("*.py"))
        if path != OWNER and (lines := _rejections_by_type_test(path))
    }
    assert not restated, restated


# --------------------------------------------------------------------------- #
# The decision itself
# --------------------------------------------------------------------------- #

_VALUES: tuple[Any, ...] = (
    None,
    False,
    True,
    0,
    7,
    "",
    "seven",
    [],
    ["seven"],
    {},
    {"seven": 7},
    (),
    3.5,
)


@pytest.mark.parametrize("value", _VALUES, ids=repr)
def test_the_predicate_and_the_rejection_are_the_same_decision(value: Any) -> None:
    """Two forms, one answer. A caller may choose either and get the same verdict."""

    from manosube_agent_civilization.difference.errors import DifferenceError

    for predicate, require in (
        (admissibility.is_scalar_tag, admissibility.require_scalar_tag),
        (admissibility.is_canonical_object, admissibility.require_object),
        (admissibility.is_collection, admissibility.require_collection),
    ):
        if predicate(value):
            assert require(value, "context") == value
        else:
            with pytest.raises(DifferenceError):
                require(value, "context")


def test_an_optional_object_distinguishes_absent_from_unreadable() -> None:
    """``None`` is legitimately empty; a scalar is not, and the two are not the same answer."""

    from manosube_agent_civilization.difference.errors import DifferenceError

    assert admissibility.require_optional_object(None, "context") is None
    assert admissibility.require_optional_object({"a": 1}, "context") == {"a": 1}
    with pytest.raises(DifferenceError):
        admissibility.require_optional_object(7, "context")


def test_a_rejection_names_the_location_rather_than_only_the_value() -> None:
    """The ``detail`` form exists so delegating never costs a caller its diagnosis."""

    from manosube_agent_civilization.difference.errors import DifferenceError

    with pytest.raises(
        DifferenceError,
        match=r"derivation binding is not a canonical object: bindings\[3\]",
    ):
        admissibility.require_object(7, "derivation binding", detail="bindings[3]")
    with pytest.raises(DifferenceError, match=r"requested risk class is not a canonical tag: 7"):
        admissibility.require_scalar_tag(7, "requested risk class")
