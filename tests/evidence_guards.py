"""The structural sweeps the Evidence guards are made of, as functions over a package root.

Every guard in ``tests/contract/evidence`` runs one of these against the live package, and
every injection control in ``tests/unit/evidence`` runs the *same* function against a copy
of that package with a real violation written into a real module. Sharing the function is
the point rather than a convenience: a control that exercised something the live guard does
not would be a control proving the wrong thing, which has happened in this repository
before and is recorded as ADR-0027 §3.6.
"""

from __future__ import annotations

import ast
from pathlib import Path

__all__ = [
    "CLOCK_CALLS",
    "CLOCK_MODULES",
    "clock_read_sites",
    "emitted_strings",
    "emitted_strings_in",
    "module_paths",
]

#: Call expressions that read the machine's clock. Written as the source spells them, and
#: matched against ``ast.unparse`` of the callee so ``now()``, ``datetime.now()`` and
#: ``dt.datetime.now()`` are all reachable by the same set.
CLOCK_CALLS: frozenset[str] = frozenset(
    {
        "now",
        "utcnow",
        "today",
        "monotonic",
        "perf_counter",
        "datetime.now",
        "datetime.utcnow",
        "datetime.today",
        "date.today",
        "time.time",
        "time.monotonic",
        "time.perf_counter",
    }
)

#: Importing these is not itself a clock read, but it is the only reason to, and a module
#: that has one has a reviewer's attention.
CLOCK_MODULES: frozenset[str] = frozenset({"time"})


def module_paths(package_root: Path) -> list[Path]:
    """Return every Python module under a package root, in a deterministic order."""

    return sorted(package_root.rglob("*.py"))


def emitted_strings(path: Path) -> set[str]:
    """Return every string constant a module *emits*, excluding its documentation.

    A docstring quoting ``CLOSED`` in order to explain why Evidence never emits one is the
    boundary being documented, not crossed. Docstrings are excluded by AST position rather
    than by a substring heuristic, so a guard cannot fail on its own explanation.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"))
    documentation: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                documentation.add(id(first.value))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in documentation
    }


def emitted_strings_in(package_root: Path) -> dict[str, set[str]]:
    """Return the emitted string constants of every module under a package root."""

    return {path.name: emitted_strings(path) for path in module_paths(package_root)}


def clock_read_sites(package_root: Path) -> dict[str, set[str]]:
    """Return every clock read under a package root, keyed by module name.

    A pure engine that reads a clock produces a verdict no reviewer can reproduce, which is
    why the recording instant and the evaluation instant are both admitted inputs. This is
    what makes that structural instead of a promise in a docstring.
    """

    sites: dict[str, set[str]] = {}
    for path in module_paths(package_root):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found = {
            ast.unparse(node.func)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and ast.unparse(node.func) in CLOCK_CALLS
        }
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        found |= imported & CLOCK_MODULES
        if found:
            sites[path.name] = found
    return sites
