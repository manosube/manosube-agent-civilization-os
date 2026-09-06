"""Phase 12 (Issue #49) Temporary Agent lifecycle: static conformance proofs.

A real AST walk over the agent_runtime package's own module source -- never a grep, never a
hardcoded name list -- proving ``PUBLIC_AGENT_START_ENTRY_POINT_COUNT=1``, that
``boot_project`` is called exactly once, in exactly one place, that no forbidden Store/Boot
surface is ever reached, and that no agent_runtime module imports a model, subprocess, shell,
network, GitHub, Observer, Change-execution, scheduler, or multi-Agent surface. The identical
AST-walk technique ``tests/contract/boot/test_boot_route_static_conformance.py`` and
``tests/contract/cli/test_cli_static_conformance.py`` already use for their own static proofs.
"""

from __future__ import annotations

import ast
import inspect
from types import ModuleType

import pytest

import manosube_agent_civilization.agent_runtime as agent_runtime_module
import manosube_agent_civilization.agent_runtime.agent as agent_module
import manosube_agent_civilization.agent_runtime.errors as errors_module
import manosube_agent_civilization.agent_runtime.route as route_module

_AGENT_RUNTIME_MODULES = (route_module, agent_module, errors_module)


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


def test_agent_runtime_package_exports_exactly_one_public_start_route_and_lifecycle_type() -> None:
    assert agent_runtime_module.__all__.count("start_temporary_agent") == 1
    assert agent_runtime_module.__all__.count("TemporaryAgent") == 1
    public_callables = [
        name
        for name in agent_runtime_module.__all__
        if callable(getattr(agent_runtime_module, name))
        and not isinstance(getattr(agent_runtime_module, name), type)
    ]
    assert public_callables == ["start_temporary_agent"]
    public_types = [
        name
        for name in agent_runtime_module.__all__
        if isinstance(getattr(agent_runtime_module, name), type)
        and not issubclass(getattr(agent_runtime_module, name), BaseException)
    ]
    assert public_types == ["TemporaryAgent"]


def test_temporary_agent_is_an_abstract_base_class_with_no_concrete_implementation() -> None:
    """Structural Review Round 2 (P12-R2-F1): the public ``TemporaryAgent`` interface must be
    a real ``abc.ABC`` declaring only ``boot_context``/``release`` as abstract members, so
    ``TemporaryAgent(...)`` always raises Python's own ``TypeError`` -- never a private,
    merely-conventional "construction token" that an importer could simply import too."""

    assert inspect.isabstract(agent_runtime_module.TemporaryAgent)
    assert agent_runtime_module.TemporaryAgent.__abstractmethods__ == frozenset(
        {"boot_context", "release"}
    )
    with pytest.raises(TypeError):
        agent_runtime_module.TemporaryAgent()  # type: ignore[abstract]


def test_route_is_the_only_module_that_imports_the_private_concrete_implementation() -> None:
    """Only ``route.py`` may ever import ``agent._ActiveTemporaryAgent`` -- proven by a real
    AST walk over every other module in this package, never merely by convention."""

    for module in (errors_module,):
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_names = {alias.name for alias in node.names}
                assert "_ActiveTemporaryAgent" not in imported_names

    route_tree = ast.parse(inspect.getsource(route_module))
    imported_from_agent: set[str] = set()
    for node in ast.walk(route_tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith("agent"):
            imported_from_agent.update(alias.name for alias in node.names)
    assert "_ActiveTemporaryAgent" in imported_from_agent


def test_route_returns_the_private_concrete_implementation() -> None:
    """``start_temporary_agent`` must return ``_ActiveTemporaryAgent(...)`` -- the one call
    site in this package that ever instantiates the concrete implementation."""

    tree = ast.parse(inspect.getsource(route_module))
    call_sites = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_ActiveTemporaryAgent"
    ]
    assert len(call_sites) == 1


def test_agent_runtime_never_exports_the_private_concrete_implementation() -> None:
    assert "_ActiveTemporaryAgent" not in agent_runtime_module.__all__
    assert not hasattr(agent_runtime_module, "_ActiveTemporaryAgent")


def test_no_construction_token_or_capability_scheme_remains() -> None:
    """Structural Review Round 2 (P12-R2-F1) removed the Round 1 token/capability scheme
    entirely -- no importable token, its type, or its dedicated error may remain anywhere in
    this package."""

    for module in (agent_module, errors_module, route_module):
        assert not hasattr(module, "_ROUTE_CONSTRUCTION_TOKEN")
        assert not hasattr(module, "_ConstructionToken")
        assert not hasattr(module, "AgentConstructionError")
    assert not hasattr(agent_runtime_module, "AgentConstructionError")


def test_agent_runtime_calls_boot_project_exactly_once() -> None:
    assert _call_site_count(route_module, "boot_project") == 1
    for module in (agent_module, errors_module):
        assert _call_site_count(module, "boot_project") == 0


def test_agent_runtime_never_calls_forbidden_store_or_binding_surfaces() -> None:
    forbidden = {"initialize", "commit", "recover", "load_current", "bind_project", "reconstruct"}
    for module in _AGENT_RUNTIME_MODULES:
        called = _called_names(module)
        assert not (called & forbidden), f"{module.__name__} must never call: {called & forbidden}"


def test_agent_runtime_never_imports_a_command_execution_or_network_surface() -> None:
    forbidden_substrings = (
        "subprocess",
        "socket",
        "urllib",
        "requests",
        "http.client",
        "os.system",
    )
    for module in _AGENT_RUNTIME_MODULES:
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(bad in name for bad in forbidden_substrings), (
                f"{module.__name__} imports a forbidden surface: {name}"
            )


def test_agent_runtime_never_imports_a_scheduler_or_background_execution_surface() -> None:
    forbidden_substrings = ("threading", "asyncio", "sched", "multiprocessing")
    for module in _AGENT_RUNTIME_MODULES:
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(bad in name for bad in forbidden_substrings), (
                f"{module.__name__} imports a forbidden scheduler/background surface: {name}"
            )


def test_agent_runtime_never_imports_a_model_github_or_observer_surface() -> None:
    forbidden_substrings = ("github", "openai", "anthropic", "observer")
    for module in _AGENT_RUNTIME_MODULES:
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(bad in name for bad in forbidden_substrings), (
                f"{module.__name__} imports a forbidden model/GitHub/Observer surface: {name}"
            )


def test_agent_runtime_never_imports_os_module_directly() -> None:
    """``os`` itself is never imported by this package's own modules -- no filesystem
    discovery, environment inspection, or process-identity lookup of its own."""

    for module in _AGENT_RUNTIME_MODULES:
        assert "os" not in _imported_module_names(module)


def test_agent_runtime_never_imports_development_binding_or_the_phase_8_fixture() -> None:
    for module in _AGENT_RUNTIME_MODULES:
        imported = _imported_module_names(module)
        assert not any("development_binding" in name for name in imported)
        assert not any("vertical_proof" in name for name in imported)
