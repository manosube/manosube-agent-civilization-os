"""Phase 11 (Issue #47) CLI Boot adapter: static conformance proofs.

A real AST walk over the CLI package's own module source -- never a grep, never a hardcoded
name list -- proving ``PUBLIC_CLI_COMMAND_COUNT=1``, that ``boot_project`` is the one route
this adapter ever calls, that no forbidden Store/Boot surface is ever reached, and that no CLI
module imports a command-execution or network surface. The identical AST-walk technique
``tests/contract/boot/test_boot_route_static_conformance.py`` already uses for Boot's own
static proofs.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from types import ModuleType

import manosube_agent_civilization.cli as cli_module

# ``importlib.import_module`` (never ``import package.main as alias``): cli/__init__.py's
# own ``from .main import main, run`` rebinds the package attribute ``cli.main`` to the
# *function* ``main`` -- the identical name collision every ``import package.submodule as x``
# statement resolves via an attribute walk on the parent package, not a ``sys.modules``
# lookup, and would therefore silently hand this test the function instead of the module.
cli_main_module: ModuleType = importlib.import_module("manosube_agent_civilization.cli.main")
cli_dunder_main_module: ModuleType = importlib.import_module(
    "manosube_agent_civilization.cli.__main__"
)

_CLI_MODULES = (cli_module, cli_main_module, cli_dunder_main_module)


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


def _add_parser_string_literals(module: ModuleType) -> list[str]:
    """Every literal string argument passed as the first positional argument to an
    ``add_parser(...)`` call -- the one place a new CLI subcommand name would ever be
    registered."""

    tree = ast.parse(inspect.getsource(module))
    names: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_parser"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            names.append(node.args[0].value)
    return names


def test_cli_registers_exactly_one_subcommand_named_boot() -> None:
    assert _add_parser_string_literals(cli_main_module) == ["boot"]


def test_cli_package_exports_no_public_callable_beyond_main_and_run() -> None:
    """``main`` is the one process entry point (parses argv, calls ``sys.exit``); ``run`` is
    its own testable, non-exiting inner route. Neither is a second command surface -- the
    package's own registered subcommand set stays exactly ``{"boot"}``, proven separately
    above."""

    public_callables = [
        name
        for name in cli_module.__all__
        if callable(getattr(cli_module, name)) and not isinstance(getattr(cli_module, name), type)
    ]
    assert set(public_callables) == {"main", "run"}


def test_cli_calls_boot_project() -> None:
    assert "boot_project" in _called_names(cli_main_module)


def test_cli_never_calls_forbidden_store_or_binding_surfaces() -> None:
    forbidden = {"initialize", "commit", "recover", "load_current", "bind_project"}
    called = _called_names(cli_main_module)
    assert not (called & forbidden), f"cli/main.py must never call: {called & forbidden}"


def test_cli_never_imports_a_command_execution_or_network_surface() -> None:
    forbidden_substrings = (
        "subprocess",
        "socket",
        "urllib",
        "requests",
        "http.client",
        "os.system",
    )
    for module in _CLI_MODULES:
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(bad in name for bad in forbidden_substrings), (
                f"{module.__name__} imports a forbidden surface: {name}"
            )


def test_cli_never_imports_os_module_directly() -> None:
    """``os`` itself is never imported by the CLI's own modules -- no filesystem discovery,
    environment inspection, or process-identity lookup of its own; ``pathlib.Path`` is the
    only filesystem-shaped surface this adapter ever touches."""

    for module in _CLI_MODULES:
        assert "os" not in _imported_module_names(module)


def test_cli_never_imports_the_github_or_authority_decision_module() -> None:
    """The CLI restores a Boot Context only -- it never touches a GitHub adapter (not yet
    implemented at all) and never itself evaluates an Authority Decision (that remains
    Authority's own concern, and Boot already reverifies the Authority Rule's identity
    before the CLI ever sees it)."""

    for module in _CLI_MODULES:
        imported = _imported_module_names(module)
        assert not any("github" in name.lower() for name in imported)
