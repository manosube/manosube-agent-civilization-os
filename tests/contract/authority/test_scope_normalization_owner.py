"""Scope normalization has exactly one owner, and this proves it rather than asserting it.

The first version of this guard read:

```python
for forbidden in ("sorted(scope[", "sorted(scope.get(", ...):
    assert f"sorted({forbidden}" not in source
```

The tuple entries already began ``sorted(``, so the composed search string was
``"sorted(sorted(scope["`` -- a string no source can contain. **The guard could not fail.**
It would have passed over `sorted(scope["paths"])` sitting in plain view.

Every other guard written in this repository carries a control proving it fires on a real
violation. This one did not, which is the whole reason it shipped broken.

## Two layers, and what each proves

```text
BEHAVIOURAL   a second normalizer that DISAGREES  -> permutation tests fail
STRUCTURAL    a second normalizer that AGREES today -> this file fails
```

The behavioural layer already exists in ``test_scope_permutation_identity.py``: if anything
normalized differently, twelve orderings would stop sharing one identity. What that cannot
catch is a duplicate implementation that happens to agree now and drifts later -- and drift
between two implementations of one rule is the defect this repository has recorded five
times. That is what this file is for.

## What it does not prove

```text
CONSTANT_KEYED_SCOPE_SORT_DETECTED=true
SCOPE_COLLECTION_LOOP_SORT_DETECTED=true
ARBITRARY_COMPUTED_KEY_SORT_DETECTED=false
```

A re-implementation reaching the members through a key computed at runtime is not detected
by source analysis. It is stated rather than implied, and the behavioural layer still covers
the case where such a re-implementation disagrees.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from manosube_agent_civilization.authority.scope import SCOPE_COLLECTIONS

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "src" / "manosube_agent_civilization"
OWNER = PACKAGE / "authority" / "scope.py"

MODULES = sorted(path for path in PACKAGE.rglob("*.py") if "__pycache__" not in path.parts)


def _constant(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _reads_a_scope_collection(node: ast.AST) -> bool:
    """Whether *node* reads a ``paths`` or ``subjects`` member list.

    Covers ``x["paths"]``, ``x.get("subjects", [])`` and nested forms such as
    ``record["scope"]["paths"]``, because the subscript's own key is what is inspected.
    """

    if isinstance(node, ast.Subscript):
        return _constant(node.slice) in SCOPE_COLLECTIONS
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and node.args
    ):
        return _constant(node.args[0]) in SCOPE_COLLECTIONS
    return False


def scope_sorting_sites(source: str) -> list[str]:
    """Every ``sorted()`` call in *source* that normalizes a scope member list."""

    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "sorted"
            and node.args
            and _reads_a_scope_collection(node.args[0])
        ):
            found.append(ast.unparse(node))
    return found


def loops_the_scope_collections_and_sorts(source: str) -> bool:
    """The owner's own shape: iterate ``SCOPE_COLLECTIONS`` and sort each member list.

    A copy would reach the members through a loop variable rather than a constant key, so the
    constant-key rule above cannot see it. Referencing the collection names *and* sorting is
    what a second implementation of this rule looks like.
    """

    if "SCOPE_COLLECTIONS" not in source:
        return False
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sorted"
        for node in ast.walk(ast.parse(source))
    )


def defines_a_normalizer(source: str) -> bool:
    return any(
        isinstance(node, ast.FunctionDef) and node.name == "canonical_scope"
        for node in ast.walk(ast.parse(source))
    )


# --------------------------------------------------------------------------- #
# The harness, before its subject
# --------------------------------------------------------------------------- #


def test_the_module_inventory_is_neither_empty_nor_shrunk() -> None:
    assert len(MODULES) >= 25, len(MODULES)
    assert OWNER in MODULES


#: Every form a second normalizer could plausibly take. Each must be detected.
_VIOLATIONS: tuple[tuple[str, str], ...] = (
    ("constant key on a name", 'x = sorted(scope["paths"])'),
    ("constant key, subjects", 'x = sorted(scope["subjects"])'),
    ("get with a default", 'x = sorted(scope.get("paths", []))'),
    ("get without a default", 'x = sorted(record.get("subjects"))'),
    ("nested subscript", 'x = sorted(record["scope"]["paths"])'),
    ("single quotes", "x = sorted(scope['paths'])"),
    ("inside a comprehension", 'y = [sorted(s["paths"]) for s in scopes]'),
    ("as an argument", 'f(sorted(scope["subjects"]))'),
)


@pytest.mark.parametrize("label,source", _VIOLATIONS, ids=[form[0] for form in _VIOLATIONS])
def test_the_detector_fires_on_every_violation_form(label: str, source: str) -> None:
    """The control the broken version never had.

    Without this, the whole file could be searching for a string that cannot occur -- which
    is exactly what it was doing.
    """

    assert scope_sorting_sites(source) != [], label


@pytest.mark.parametrize(
    "source",
    [
        'x = sorted(unknown)',
        'x = sorted(set(reasons))',
        'x = sorted(matched, key=lambda p: str(p["prohibition_id"]))',
        'x = sorted(scope["repository"])',
        'x = scope["paths"]',
        'x = sorted(record["action_kinds"])',
    ],
    ids=["unknown", "reason-set", "keyed-sort", "location-field", "no-sort", "other-array"],
)
def test_the_detector_does_not_fire_on_legitimate_sorting(source: str) -> None:
    """A detector that flags every ``sorted()`` would make this file meaningless.

    The package sorts reason codes, rule candidates and unknown-key lists throughout; only a
    scope member list is the rule's business.
    """

    assert scope_sorting_sites(source) == []


def test_the_loop_detector_fires_and_is_not_always_true() -> None:
    assert loops_the_scope_collections_and_sorts(
        "for key in SCOPE_COLLECTIONS:\n    out[key] = sorted(value[key])\n"
    )
    assert not loops_the_scope_collections_and_sorts("x = sorted(unknown)\n")
    assert not loops_the_scope_collections_and_sorts("for key in SCOPE_COLLECTIONS:\n    pass\n")


def test_the_definition_detector_fires_and_is_not_always_true() -> None:
    assert defines_a_normalizer("def canonical_scope(scope):\n    return scope\n")
    assert not defines_a_normalizer("def require_scope(value, context):\n    return value\n")


# --------------------------------------------------------------------------- #
# The claim
# --------------------------------------------------------------------------- #


def test_the_owner_is_the_only_module_that_defines_the_normalizer() -> None:
    defining = [
        module for module in MODULES if defines_a_normalizer(module.read_text(encoding="utf-8"))
    ]
    assert defining == [OWNER], defining


def test_the_owner_really_does_normalize() -> None:
    """Otherwise "only the owner sorts a scope" would be true of a package that never does."""

    source = OWNER.read_text(encoding="utf-8")
    assert loops_the_scope_collections_and_sorts(source)
    assert defines_a_normalizer(source)


@pytest.mark.parametrize("module", MODULES, ids=lambda path: path.name)
def test_no_module_but_the_owner_sorts_a_scope_member_list(module: Path) -> None:
    if module == OWNER:
        return
    source = module.read_text(encoding="utf-8")
    assert scope_sorting_sites(source) == [], module
    assert not loops_the_scope_collections_and_sorts(source), module


def test_the_identity_owner_reuses_the_normalizer() -> None:
    """``change_intent_fingerprint`` must call the owner, not re-implement it."""

    source = (PACKAGE / "authority" / "identity.py").read_text(encoding="utf-8")
    assert "canonical_scope(scope)" in source
    assert scope_sorting_sites(source) == []


def test_change_identity_neither_normalizes_nor_needs_to() -> None:
    """Change consumes the canonical representation Authority already produced."""

    source = (PACKAGE / "change" / "identity.py").read_text(encoding="utf-8")
    assert scope_sorting_sites(source) == []
    assert "canonical_scope" not in source


def test_the_broken_predecessor_would_now_be_caught() -> None:
    """The exact guard that shipped, applied to the exact violation it could not see.

    ``f"sorted({forbidden}"`` over entries already beginning ``sorted(`` composed
    ``"sorted(sorted(scope["``. Recorded here so the failure mode is a test, not a memory.
    """

    violation = 'x = sorted(scope["paths"])'
    broken_searches = [
        f"sorted({forbidden}"
        for forbidden in ("sorted(scope[", "sorted(scope.get(", '["paths"])', "['paths'])")
    ]
    assert not any(search in violation for search in broken_searches)
    assert scope_sorting_sites(violation) != []
