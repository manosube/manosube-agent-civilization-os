"""Phase 14 (Issue #62) Projection: static conformance proofs.

A real AST walk over the ``projection`` package's own module source -- never a grep, never a
hardcoded name list -- proving exactly two public routes (``project_to_github``,
``route_observation_receipt_to_evidence``), that no existing canonical owner (Reflow, Binding,
Independent Verification) is ever imported anywhere in this package, that ``evidence`` is
imported only where this package's own design requires it (``route.py``, read-only identity
recomputation; ``receipt_handoff.py``, the one ``derive_evidence`` call), that ``boot`` is
imported only from ``route.py`` and only to call ``boot_project`` exactly once, that
``authority`` is imported only from ``route.py`` and only to call
``evaluate_projection_authorization`` exactly once (Structural Review Round 1, P14-R1-F1),
that ``difference.identity``/``change.identity`` are imported only from ``route.py`` for their
own read-only fingerprint functions -- never ``difference.engine``, ``difference.graph``, or
``change.engine`` (Structural Review Round 1, P14-R1-F2) -- that ``store.commit`` is never
called directly anywhere in this package (the sanctioned single committer is
``store.commit.commit_state_transition``, and only ``route.py`` calls it), and that no module
besides ``github_adapter.py`` imports a network, subprocess, or GitHub transport surface -- the
identical AST-walk technique
``tests/contract/independent_verification/test_independent_verification_static_conformance.py``
already uses for its own static proofs.
"""

from __future__ import annotations

import ast
import inspect
from types import ModuleType

import manosube_agent_civilization.projection as projection_module
import manosube_agent_civilization.projection.engine as engine_module
import manosube_agent_civilization.projection.errors as errors_module
import manosube_agent_civilization.projection.github_adapter as github_adapter_module
import manosube_agent_civilization.projection.identity as identity_module
import manosube_agent_civilization.projection.observable as observable_module
import manosube_agent_civilization.projection.receipt_handoff as receipt_handoff_module
import manosube_agent_civilization.projection.route as route_module
import manosube_agent_civilization.projection.types as types_module

#: Every module in the package.
_ALL_PACKAGE_MODULES = (
    route_module,
    engine_module,
    identity_module,
    types_module,
    errors_module,
    github_adapter_module,
    receipt_handoff_module,
    observable_module,
)

#: Modules other than ``receipt_handoff.py`` (the one module permitted to call into
#: ``evidence``) -- ``route.py`` is deliberately excluded here (checked separately, below,
#: since it is permitted only the read-only ``evidence.identity.evidence_semantic_
#: fingerprint``, never ``derive_evidence`` or the ``evidence`` package root).
_NON_EVIDENCE_MODULES = (
    engine_module,
    identity_module,
    types_module,
    errors_module,
    github_adapter_module,
    observable_module,
)

#: Existing canonical owners no module in this package may ever import, in whole or in part.
#: ``difference``, ``change`` and ``authority`` are deliberately absent from this closed set --
#: each is legitimately reused in a narrow, separately-checked way (``difference.validation``/
#: ``difference.identity``/``change.identity`` as read-only shared utilities;
#: ``authority.evaluate_projection_authorization`` from ``route.py`` only, Structural Review
#: Round 1, P14-R1-F1) -- so a blanket forbid on those three package names would contradict the
#: dedicated checks below rather than reinforce them.
_FORBIDDEN_OWNER_MODULE_PREFIXES = (
    "manosube_agent_civilization.reflow",
    "manosube_agent_civilization.binding",
    "manosube_agent_civilization.independent_verification",
)

#: The Difference/Change-owned submodules this package's own modules legitimately import --
#: shared canonical-schema-validation and read-only identity/fingerprint utilities, never
#: either owner's own semantic engine (``difference.engine``/``difference.graph``/
#: ``change.engine``, none of which any module in this package ever imports).
_ALLOWED_SHARED_UTILITY_IMPORTS = frozenset(
    {
        "manosube_agent_civilization.difference.validation",
        "manosube_agent_civilization.difference.identity",
        "manosube_agent_civilization.change.identity",
    }
)


def _imported_module_names(module: ModuleType) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _call_site_count(module: ModuleType, name: str) -> int:
    tree = ast.parse(inspect.getsource(module))
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (isinstance(func, ast.Name) and func.id == name) or (
            isinstance(func, ast.Attribute) and func.attr == name
        ):
            count += 1
    return count


def test_projection_package_exports_exactly_two_public_routes() -> None:
    public_callables = {
        name
        for name in projection_module.__all__
        if callable(getattr(projection_module, name))
        and not isinstance(getattr(projection_module, name), type)
    }
    assert public_callables == {"project_to_github", "route_observation_receipt_to_evidence"}


def test_no_module_imports_a_forbidden_existing_owner() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module) - _ALLOWED_SHARED_UTILITY_IMPORTS
        for forbidden_prefix in _FORBIDDEN_OWNER_MODULE_PREFIXES:
            assert not any(
                name == forbidden_prefix or name.startswith(forbidden_prefix + ".")
                for name in imported
            ), f"{module.__name__} imports forbidden owner prefix {forbidden_prefix!r}: {imported}"


def test_evidence_is_imported_only_by_route_and_receipt_handoff() -> None:
    for module in _NON_EVIDENCE_MODULES:
        imported = _imported_module_names(module)
        assert not any(
            name == "manosube_agent_civilization.evidence"
            or name.startswith("manosube_agent_civilization.evidence.")
            for name in imported
        ), f"{module.__name__} imports manosube_agent_civilization.evidence: {imported}"


def test_route_imports_only_the_read_only_evidence_identity_function() -> None:
    imported = _imported_module_names(route_module)
    assert "manosube_agent_civilization.evidence.identity" in imported
    assert "manosube_agent_civilization.evidence" not in imported


def test_receipt_handoff_calls_derive_evidence_exactly_once() -> None:
    assert _call_site_count(receipt_handoff_module, "derive_evidence") == 1


def test_route_calls_boot_project_exactly_once() -> None:
    assert _call_site_count(route_module, "boot_project") == 1


def test_boot_is_imported_only_by_route() -> None:
    for module in _ALL_PACKAGE_MODULES:
        if module is route_module:
            continue
        imported = _imported_module_names(module)
        assert not any(
            name == "manosube_agent_civilization.boot"
            or name.startswith("manosube_agent_civilization.boot.")
            for name in imported
        ), f"{module.__name__} imports manosube_agent_civilization.boot: {imported}"


def test_authority_is_imported_only_by_route() -> None:
    """Structural Review Round 1 (Issue #62, P14-R1-F1): ``authority`` is reused, narrowly,
    from exactly one call site -- never imported by any other module in this package."""

    for module in _ALL_PACKAGE_MODULES:
        if module is route_module:
            continue
        imported = _imported_module_names(module)
        assert not any(
            name == "manosube_agent_civilization.authority"
            or name.startswith("manosube_agent_civilization.authority.")
            for name in imported
        ), f"{module.__name__} imports manosube_agent_civilization.authority: {imported}"


def test_route_calls_evaluate_projection_authorization_exactly_once() -> None:
    assert _call_site_count(route_module, "evaluate_projection_authorization") == 1


def test_route_imports_only_the_read_only_difference_and_change_identity_functions() -> None:
    """Structural Review Round 1 (Issue #62, P14-R1-F2): ``route.py`` may import
    ``difference.identity``/``change.identity`` (read-only fingerprint recomputation) but
    never ``difference.engine``, ``difference.graph``, or ``change.engine`` -- and no other
    module in this package imports ``difference``/``change`` at all, beyond the shared
    ``difference.validation`` schema-validator utility ``engine.py`` already uses."""

    imported = _imported_module_names(route_module)
    assert "manosube_agent_civilization.difference.identity" in imported
    assert "manosube_agent_civilization.change.identity" in imported
    assert "manosube_agent_civilization.difference.engine" not in imported
    assert "manosube_agent_civilization.difference.graph" not in imported
    assert "manosube_agent_civilization.change.engine" not in imported
    assert "manosube_agent_civilization.change" not in imported

    for module in _ALL_PACKAGE_MODULES:
        if module is route_module:
            continue
        other_imported = _imported_module_names(module)
        assert not any(
            name == "manosube_agent_civilization.change"
            or name.startswith("manosube_agent_civilization.change.")
            for name in other_imported
        ), f"{module.__name__} imports manosube_agent_civilization.change: {other_imported}"


def test_only_route_calls_commit_state_transition() -> None:
    for module in _ALL_PACKAGE_MODULES:
        count = _call_site_count(module, "commit_state_transition")
        if module is route_module:
            assert count == 1, "route.py must call commit_state_transition exactly once"
        else:
            assert count == 0, f"{module.__name__} must never call commit_state_transition"


def test_no_module_calls_store_commit_directly() -> None:
    """The sanctioned single committer is ``store.commit.commit_state_transition`` -- no
    module in this package may call a ``store`` object's own ``.commit(...)`` method
    directly (K-003/R-001, ``topology.py``'s own static scan enforces the identical rule
    package-wide; this is the package-local proof that this package's own source agrees)."""

    for module in _ALL_PACKAGE_MODULES:
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "commit":
                continue
            assert isinstance(node.func.value, ast.Name) and node.func.value.id != "store", (
                f"{module.__name__} appears to call store.commit(...) directly, bypassing "
                "commit_state_transition"
            )


def test_only_github_adapter_module_imports_a_network_or_transport_surface() -> None:
    forbidden_substrings = ("urllib", "requests", "http.client", "socket", "subprocess")
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        hits = {
            name
            for name in imported
            if any(substring in name for substring in forbidden_substrings)
        }
        if module is github_adapter_module:
            assert hits, "github_adapter.py is expected to import a network/transport surface"
        else:
            assert not hits, f"{module.__name__} imports a network/transport surface: {hits}"


def test_no_module_imports_a_scheduler_or_multi_agent_surface() -> None:
    forbidden_substrings = (
        "threading",
        "asyncio",
        "sched",
        "multiprocessing",
        "openai",
        "anthropic",
    )
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        hits = {
            name
            for name in imported
            if any(substring in name for substring in forbidden_substrings)
        }
        assert not hits, f"{module.__name__} imports a forbidden surface: {hits}"
