"""Static conformance (FD4-C10, V7): no parallel Authority/State/Evidence/Reflow/Store owner,
every schema is Draft 2020-12 valid and internally resolvable, and the public surface is
exactly what :mod:`manosube_agent_civilization.acceptance_policy` declares.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from jsonschema import Draft202012Validator

from manosube_agent_civilization import acceptance_policy as ap
from manosube_agent_civilization.acceptance_policy import engine, identity, route, types
from manosube_agent_civilization.state.canonicalize import _schema_registry

_PACKAGE_ROOT = Path(inspect.getfile(ap)).parent
_SCHEMA_ROOT = Path(inspect.getfile(ap)).parents[3] / "01_SCHEMA"
_REPO_ROOT = Path(inspect.getfile(ap)).parents[3]


def _module_source_files() -> list[Path]:
    return sorted(p for p in _PACKAGE_ROOT.glob("*.py") if p.name != "__init__.py")


def _imported_dotted_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


def test_only_route_py_imports_the_store_commit_module() -> None:
    """FD4-C10/SINGLE_COMMITTER_REQUIRED: exactly one module in this package ever touches
    ``store.commit`` -- the same discipline every other domain package in this repository
    holds itself to (``topology.py``'s own sanctioned-commit-call-module scan)."""

    committing_modules = [
        path.name
        for path in _module_source_files()
        if "manosube_agent_civilization.store.commit" in _imported_dotted_names(path)
    ]
    assert committing_modules == ["route.py"]


def test_no_module_constructs_a_filestatestore_directly() -> None:
    """This package is a caller of an existing Store, never a second Store owner."""

    for path in _module_source_files():
        assert (
            "manosube_agent_civilization.store"
            not in {name for name in _imported_dotted_names(path) if name.endswith(".store")}
            or path.name == "route.py"
        ), f"{path.name} imports the store package directly"


def test_no_module_imports_the_authority_engine_or_mints_a_decision() -> None:
    """FD4-C10: this package never mints its own Authority Decision -- it recognises exactly
    one literal Human Authority (``SHUKOU``) as a closed constant, never an evaluator call."""

    for path in _module_source_files():
        imported = _imported_dotted_names(path)
        assert not any(
            name.startswith("manosube_agent_civilization.authority") for name in imported
        )


def test_no_module_imports_difference_evidence_or_reflow_engines() -> None:
    """FD4-C10: acceptance-policy lineage is its own closed record set -- it never reuses (and
    so never risks conflating itself with) the Difference/Evidence/Reflow lifecycle owners."""

    forbidden_prefixes = (
        "manosube_agent_civilization.difference",
        "manosube_agent_civilization.evidence",
        "manosube_agent_civilization.reflow",
    )
    for path in _module_source_files():
        imported = _imported_dotted_names(path)
        assert not any(name.startswith(forbidden_prefixes) for name in imported)


def test_engine_module_never_imports_the_store_package() -> None:
    """:mod:`.engine` is pure -- no Store, no clock, no network."""

    imported = _imported_dotted_names(_PACKAGE_ROOT / "engine.py")
    assert not any(name.startswith("manosube_agent_civilization.store") for name in imported)


def test_public_package_surface_matches_dunder_all() -> None:
    exported = set(ap.__all__)
    for name in exported:
        assert hasattr(ap, name), f"__all__ names {name!r} but it is not importable"


def test_route_module_exposes_exactly_the_documented_public_functions() -> None:
    public_names = {
        name
        for name in dir(route)
        if not name.startswith("_")
        and inspect.isfunction(getattr(route, name))
        and getattr(route, name).__module__ == route.__name__
    }
    assert public_names == set(route.__all__)


def test_engine_and_identity_modules_expose_no_undocumented_leading_underscore_escape() -> None:
    for module in (engine, identity, types):
        for name in dir(module):
            if name.startswith("__"):
                continue
            value = getattr(module, name)
            if inspect.isfunction(value) and value.__module__ == module.__name__:
                assert not name.startswith("_") or name in {
                    "_require_object",
                    "_clause_comparison_projection",
                    "_true_blocking_fields",
                    "_find_known_clause_id_mentions",
                    "_mentions_in_text",
                    "_semantic_projection",
                    "_semantic_fingerprint",
                    "_record_id",
                }


# --- schema totality (V1) -------------------------------------------------------------------- #

_EXPECTED_SCHEMA_FILES = frozenset(
    {
        "acceptance_policy_baseline.schema.json",
        "acceptance_policy_clause.schema.json",
        "acceptance_policy_transition.schema.json",
        "acceptance_policy_adoption.schema.json",
        "acceptance_policy_effective_view.schema.json",
        "acceptance_policy_impact_preview.schema.json",
        "acceptance_policy_refusal_outcome.schema.json",
    }
)


def test_all_seven_required_schema_files_exist() -> None:
    schema_dir = _SCHEMA_ROOT / "acceptance_policy"
    actual = {p.name for p in schema_dir.glob("*.schema.json")}
    assert actual == _EXPECTED_SCHEMA_FILES


def test_every_schema_is_draft_2020_12_valid_and_resolvable() -> None:
    schemas, registry = _schema_registry(_SCHEMA_ROOT)
    for name in _EXPECTED_SCHEMA_FILES:
        schema_id = (
            f"https://schemas.manosube.org/agent-civilization-os/v0.1/acceptance_policy/{name}"
        )
        assert schema_id in schemas, f"{name} is not registered under its own $id"
        Draft202012Validator.check_schema(schemas[schema_id])
        validator = Draft202012Validator(schemas[schema_id], registry=registry)
        # Resolving every $ref reachable from the root is exercised by validating a minimal
        # non-matching instance -- this raises on an unresolved $ref before it ever reaches a
        # keyword-mismatch error.
        list(validator.iter_errors({}))
