"""Phase 15 (Issue #64) Runtime: static conformance proofs.

A real AST walk over the ``runtime`` package's own module source -- never a grep, never a
hardcoded name list -- mirroring ``tests/contract/projection/
test_projection_static_conformance.py``'s own technique exactly, adapted to Runtime's own
disclosed architectural divergences from Projection:

- Runtime Observation is bounded by its own closed Observation Boundary, never by an
  Authority Decision -- so ``authority``/``evaluate_projection_authorization`` is legitimately
  imported and called only by ``bootstrap.py`` (V5's own trusted-provisioning concern),
  never by ``route.py`` at all (unlike Projection's own ``route.py``, which is the one and
  only Authority call site in that package).
- ``bootstrap.py`` legitimately imports the shipped ``manosube_agent_civilization.projection``
  package (the Phase 14 execution interface it provisions), ``binding.identity`` (declaration
  signature reverification), and ``difference``/``change`` identity utilities (subject
  reverification) -- none of which any other module in this package may import.
- ``boot_project`` has two legitimate call sites in this package (``route.py`` and
  ``bootstrap.py``), never a single one the way Projection's own package requires.
"""

from __future__ import annotations

import ast
import inspect
from types import ModuleType

import manosube_agent_civilization.runtime as runtime_module
import manosube_agent_civilization.runtime.adapter as adapter_module
import manosube_agent_civilization.runtime.bootstrap as bootstrap_module
import manosube_agent_civilization.runtime.engine as engine_module
import manosube_agent_civilization.runtime.errors as errors_module
import manosube_agent_civilization.runtime.evidence_handoff as evidence_handoff_module
import manosube_agent_civilization.runtime.identity as identity_module
import manosube_agent_civilization.runtime.route as route_module
import manosube_agent_civilization.runtime.types as types_module

_ALL_PACKAGE_MODULES = (
    route_module,
    engine_module,
    identity_module,
    types_module,
    errors_module,
    adapter_module,
    evidence_handoff_module,
    bootstrap_module,
)

#: Existing canonical owners no module in this package may ever import, in whole or in part --
#: Runtime is read-only and mints no Authority/Reflow decision of its own, and never reaches
#: Independent Verification's own machinery.
_FORBIDDEN_OWNER_MODULE_PREFIXES = (
    "manosube_agent_civilization.reflow",
    "manosube_agent_civilization.independent_verification",
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


def test_runtime_package_exports_exactly_three_public_routes() -> None:
    public_callables = {
        name
        for name in runtime_module.__all__
        if callable(getattr(runtime_module, name))
        and not isinstance(getattr(runtime_module, name), type)
    }
    assert public_callables == {
        "bootstrap_projection_execution_capability",
        "observe_runtime_target",
        "route_runtime_observation_to_evidence",
    }


def test_no_module_imports_a_forbidden_existing_owner() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        for forbidden_prefix in _FORBIDDEN_OWNER_MODULE_PREFIXES:
            assert not any(
                name == forbidden_prefix or name.startswith(forbidden_prefix + ".")
                for name in imported
            ), f"{module.__name__} imports forbidden owner prefix {forbidden_prefix!r}: {imported}"


def test_evidence_is_imported_only_by_evidence_handoff_and_bootstrap() -> None:
    """``evidence_handoff.py`` is the one caller of ``derive_evidence`` itself; ``bootstrap.py``
    additionally imports the read-only ``evidence.identity.evidence_semantic_fingerprint`` to
    reverify an ``EVIDENCE_ARTIFACT``-kind subject's own real fingerprint (the identical
    narrow reuse Projection's own ``route.py`` already makes of the same function) -- no other
    module in this package imports ``evidence`` in any form."""

    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        evidence_imports = {
            name
            for name in imported
            if name == "manosube_agent_civilization.evidence"
            or name.startswith("manosube_agent_civilization.evidence.")
        }
        if module is evidence_handoff_module:
            assert evidence_imports == {"manosube_agent_civilization.evidence"}
        elif module is bootstrap_module:
            assert evidence_imports == {"manosube_agent_civilization.evidence.identity"}
        else:
            assert not evidence_imports, f"{module.__name__} imports evidence: {evidence_imports}"


def test_evidence_handoff_calls_derive_evidence_exactly_once() -> None:
    assert _call_site_count(evidence_handoff_module, "derive_evidence") == 1


def test_boot_project_is_imported_only_by_route_and_bootstrap() -> None:
    for module in _ALL_PACKAGE_MODULES:
        if module in (route_module, bootstrap_module):
            continue
        imported = _imported_module_names(module)
        assert not any(
            name == "manosube_agent_civilization.boot"
            or name.startswith("manosube_agent_civilization.boot.")
            for name in imported
        ), f"{module.__name__} imports manosube_agent_civilization.boot: {imported}"


def test_route_calls_boot_project_exactly_once() -> None:
    assert _call_site_count(route_module, "boot_project") == 1


def test_bootstrap_calls_boot_project_exactly_once() -> None:
    assert _call_site_count(bootstrap_module, "boot_project") == 1


def test_authority_is_never_imported_by_route() -> None:
    """Runtime Observation is bounded by its own closed Observation Boundary, never by an
    Authority Decision -- this package's own disclosed judgment call
    (``10_RUNTIME/RUNTIME_CONTRACT.md`` §4)."""

    imported = _imported_module_names(route_module)
    assert not any(
        name == "manosube_agent_civilization.authority"
        or name.startswith("manosube_agent_civilization.authority.")
        for name in imported
    ), f"route.py imports manosube_agent_civilization.authority: {imported}"


def test_authority_is_imported_only_by_bootstrap() -> None:
    for module in _ALL_PACKAGE_MODULES:
        if module is bootstrap_module:
            continue
        imported = _imported_module_names(module)
        assert not any(
            name == "manosube_agent_civilization.authority"
            or name.startswith("manosube_agent_civilization.authority.")
            for name in imported
        ), f"{module.__name__} imports manosube_agent_civilization.authority: {imported}"


def test_bootstrap_calls_evaluate_projection_authorization_exactly_once() -> None:
    assert _call_site_count(bootstrap_module, "evaluate_projection_authorization") == 1


def test_projection_package_is_imported_only_by_bootstrap() -> None:
    """The shipped Phase 14 execution interface this delivery provisions (V5) -- imported
    exclusively by ``bootstrap.py``, never by any other module in this package."""

    for module in _ALL_PACKAGE_MODULES:
        if module is bootstrap_module:
            continue
        imported = _imported_module_names(module)
        assert not any(
            name == "manosube_agent_civilization.projection"
            or name.startswith("manosube_agent_civilization.projection.")
            for name in imported
        ), f"{module.__name__} imports manosube_agent_civilization.projection: {imported}"


def test_binding_is_imported_only_by_bootstrap_for_declaration_identity() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        binding_imports = {
            name
            for name in imported
            if name == "manosube_agent_civilization.binding"
            or name.startswith("manosube_agent_civilization.binding.")
        }
        if module is bootstrap_module:
            assert binding_imports == {"manosube_agent_civilization.binding.identity"}
        else:
            assert not binding_imports, f"{module.__name__} imports binding: {binding_imports}"


def test_only_bootstrap_imports_difference_and_change_identity() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        difference_or_change = {
            name
            for name in imported
            if name.startswith(
                ("manosube_agent_civilization.difference.", "manosube_agent_civilization.change.")
            )
        }
        if module is bootstrap_module:
            assert difference_or_change == {
                "manosube_agent_civilization.difference.identity",
                "manosube_agent_civilization.difference.validation",
                "manosube_agent_civilization.change.identity",
            }
        elif module is engine_module:
            assert difference_or_change == {"manosube_agent_civilization.difference.validation"}
        else:
            assert not difference_or_change, f"{module.__name__}: {difference_or_change}"


def test_only_route_calls_commit_state_transition() -> None:
    """Runtime Observation commits exactly once per call (no intent/materialize-attempt
    claim pair -- see ``engine.py``'s own module docstring) -- so ``route.py`` calls
    ``commit_state_transition`` from exactly one literal call site, and no other module in
    this package ever calls it."""

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


def test_only_adapter_module_imports_a_network_or_transport_surface() -> None:
    forbidden_substrings = ("urllib", "requests", "http.client", "socket", "subprocess")
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        hits = {
            name
            for name in imported
            if any(substring in name for substring in forbidden_substrings)
        }
        if module is adapter_module:
            assert hits, "adapter.py is expected to import a network/transport surface"
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


def test_shipped_kernel_package_imports_no_tests_module_anywhere() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        assert not any(name == "tests" or name.startswith("tests.") for name in imported), (
            f"{module.__name__} imports a tests module: {imported}"
        )
