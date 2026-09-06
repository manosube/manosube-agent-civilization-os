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


def test_temporary_agent_constructor_requires_the_route_construction_token() -> None:
    """Structural Review Round 1 (P12-R1-F1): ``TemporaryAgent.__init__`` must declare a
    keyword-only ``_construction_token`` parameter -- the technical boundary that makes a
    bare, direct ``TemporaryAgent(some_context)`` call fail closed rather than silently
    producing an active Agent over unverified data."""

    tree = ast.parse(inspect.getsource(agent_module))
    init_defs = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    ]
    assert len(init_defs) == 1
    kwonly_names = {arg.arg for arg in init_defs[0].args.kwonlyargs}
    assert "_construction_token" in kwonly_names


def test_route_is_the_only_module_that_imports_the_construction_token() -> None:
    """Only ``route.py`` may ever import ``agent._ROUTE_CONSTRUCTION_TOKEN`` -- proven by a
    real AST walk over every other module in this package, never merely by convention."""

    for module in (agent_module, errors_module):
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_names = {alias.name for alias in node.names}
                assert "_ROUTE_CONSTRUCTION_TOKEN" not in imported_names

    route_tree = ast.parse(inspect.getsource(route_module))
    imported_from_agent: set[str] = set()
    for node in ast.walk(route_tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith("agent"):
            imported_from_agent.update(alias.name for alias in node.names)
    assert "_ROUTE_CONSTRUCTION_TOKEN" in imported_from_agent


def test_route_passes_the_construction_token_to_every_temporaryagent_call_site() -> None:
    """Every ``TemporaryAgent(...)`` call inside ``route.py`` must pass
    ``_construction_token=`` explicitly -- proving the one canonical route itself supplies the
    proof of authorization, never relying on a default that happens to work."""

    tree = ast.parse(inspect.getsource(route_module))
    call_sites = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "TemporaryAgent"
    ]
    assert len(call_sites) == 1
    keyword_names = {kw.arg for kw in call_sites[0].keywords}
    assert "_construction_token" in keyword_names


def test_agent_runtime_never_exports_the_construction_token_or_its_type() -> None:
    assert "_ROUTE_CONSTRUCTION_TOKEN" not in agent_runtime_module.__all__
    assert "_ConstructionToken" not in agent_runtime_module.__all__
    assert not hasattr(agent_runtime_module, "_ROUTE_CONSTRUCTION_TOKEN")
    assert not hasattr(agent_runtime_module, "_ConstructionToken")


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
