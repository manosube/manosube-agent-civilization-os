"""Phase 10 (Issue #45) Boot: static conformance proofs.

A real AST walk over ``boot/route.py``'s own module source -- never a grep, never a
hardcoded name list -- proving ``BOOT_OWNER_COUNT=1``, ``PUBLIC_BOOT_ENTRY_POINT_COUNT=1``,
that no Boot path ever calls ``store.initialize``/``store.commit``/``store.recover``, and
that no Boot module ever imports a command-execution, filesystem-discovery, network, or
Development-Binding/Phase-8-fixture-shaped surface.
"""

from __future__ import annotations

import ast
import inspect
from types import ModuleType

import manosube_agent_civilization.boot as boot_module
import manosube_agent_civilization.boot.context as context_module
import manosube_agent_civilization.boot.errors as errors_module
import manosube_agent_civilization.boot.route as route_module

_BOOT_MODULES = (route_module, context_module, errors_module)


def _imported_module_names(module: ModuleType) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _called_names(module: ModuleType) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    return called


def test_boot_package_exports_exactly_one_public_entry_point() -> None:
    assert boot_module.__all__.count("boot_project") == 1
    public_callables = [
        name
        for name in boot_module.__all__
        if callable(getattr(boot_module, name)) and not isinstance(getattr(boot_module, name), type)
    ]
    assert public_callables == ["boot_project"]


def test_boot_route_never_calls_store_initialize_commit_or_recover() -> None:
    forbidden = {"initialize", "commit", "recover"}
    called = _called_names(route_module)
    assert not (called & forbidden), f"boot/route.py must never call: {called & forbidden}"


def test_boot_route_never_calls_load_current() -> None:
    """Phase 10 Structural Review Round 1 (P10-R1-F2): ``FileStateStore.load_current``
    performs a real write to materialize a missing ``current.json`` view, which is not a
    read-only operation -- ``boot_project`` must never reach it, on any code path, ever
    again."""

    assert "load_current" not in _called_names(route_module)


def test_boot_route_calls_reconstruct() -> None:
    """The positive counterpart of the above: current State restoration must go through
    ``FileStateStore.reconstruct`` -- the pure, read-only lineage replay -- and not merely
    lack a call to ``load_current`` by omission."""

    assert "reconstruct" in _called_names(route_module)


def test_boot_route_never_imports_a_command_execution_or_network_surface() -> None:
    forbidden_substrings = (
        "subprocess",
        "socket",
        "urllib",
        "requests",
        "http.client",
        "os.system",
    )
    for module in _BOOT_MODULES:
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(bad in name for bad in forbidden_substrings), (
                f"{module.__name__} imports a forbidden surface: {name}"
            )


def test_boot_never_imports_development_binding_or_the_phase_8_fixture() -> None:
    for module in _BOOT_MODULES:
        imported = _imported_module_names(module)
        assert not any("development_binding" in name for name in imported)
        assert not any("vertical_proof" in name for name in imported)


def test_boot_route_never_imports_os_module_directly() -> None:
    """``os`` itself is never imported by ``boot/route.py`` -- Boot performs no filesystem
    discovery, environment inspection, or process-identity lookup of its own."""

    imported = _imported_module_names(route_module)
    assert "os" not in imported
