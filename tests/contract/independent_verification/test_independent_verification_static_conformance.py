"""Phase 13 (Issue #51) Independent Verification: static conformance proofs.

A real AST walk over the ``independent_verification`` package's own module source -- never a
grep, never a hardcoded name list -- proving ``PUBLIC_VERIFICATION_ENTRY_POINT_COUNT=1``,
that ``store.resolve_record`` is the only Store method this package ever calls, that no
existing owner (Evidence, Difference, Authority, Reflow, Boot, Binding) is ever imported, and
that no module in this package imports a model, subprocess, shell, network, GitHub, Observer,
Change-execution, scheduler, or multi-Agent surface. The identical AST-walk technique
``tests/contract/agent_runtime/test_agent_runtime_static_conformance.py`` and
``tests/contract/boot/test_boot_route_static_conformance.py`` already use for their own static
proofs.
"""

from __future__ import annotations

import ast
import inspect
from types import ModuleType

import manosube_agent_civilization.independent_verification as verification_module
import manosube_agent_civilization.independent_verification.errors as errors_module
import manosube_agent_civilization.independent_verification.route as route_module
import manosube_agent_civilization.independent_verification.types as types_module

_VERIFICATION_MODULES = (route_module, types_module, errors_module)

#: Existing canonical owners this package must never import -- Issue #51's own delivery
#: constraint ("reuse existing public owners; do not copy canonical Evidence, Difference,
#: Authority, Reflow, Store, Boot, or Binding logic") made checkable rather than merely
#: asserted in prose. ``boot`` is deliberately absent here (Structural Review Round 1,
#: P13-R1-F2): this package now calls the existing Boot owner's own public
#: ``boot_project`` exactly once, to independently re-verify the real Human Authority
#: reference rather than trusting a caller-supplied equality check -- reuse by call, not a
#: second Boot owner. ``test_route_calls_boot_project_exactly_once`` below is the positive
#: proof that pairs with this negative one.
_FORBIDDEN_OWNER_MODULE_PREFIXES = (
    "manosube_agent_civilization.evidence",
    "manosube_agent_civilization.difference",
    "manosube_agent_civilization.authority",
    "manosube_agent_civilization.reflow",
    "manosube_agent_civilization.binding",
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


def _attribute_calls(module: ModuleType) -> set[str]:
    """Return every ``x.method_name(...)`` attribute-call name in *module*'s own source."""

    tree = ast.parse(inspect.getsource(module))
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
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


def test_independent_verification_package_exports_exactly_one_public_route() -> None:
    assert verification_module.__all__.count("run_independent_verification") == 1
    public_callables = [
        name
        for name in verification_module.__all__
        if callable(getattr(verification_module, name))
        and not isinstance(getattr(verification_module, name), type)
    ]
    assert public_callables == ["run_independent_verification"]


def test_independent_verification_exports_exactly_the_three_value_types_and_protocol() -> None:
    exported_types = {
        name
        for name in verification_module.__all__
        if isinstance(getattr(verification_module, name), type)
        and not issubclass(getattr(verification_module, name), BaseException)
    }
    assert exported_types == {
        "VerificationRequirement",
        "VerifierSelection",
        "VerificationResult",
        "IndependentVerifier",
    }


def test_independent_verification_never_imports_an_existing_kernel_owner() -> None:
    """Issue #51: reuse existing owners by call, never by importing their implementation."""

    for module in (verification_module, *_VERIFICATION_MODULES):
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(
                name.startswith(prefix) for prefix in _FORBIDDEN_OWNER_MODULE_PREFIXES
            ), f"{module.__name__} imports a forbidden existing-owner module: {name}"


def test_route_calls_resolve_record_and_no_other_store_method() -> None:
    """``store.resolve_record`` is the only Store method this package ever calls -- no
    ``initialize``/``commit``/``recover``/``load_current``/``read_current_consistent``/
    ``reconstruct``/``bind_project``/``boot_project`` call exists anywhere in this package."""

    forbidden = {
        "initialize",
        "commit",
        "recover",
        "load_current",
        "read_current_consistent",
        "reconstruct",
        "bind_project",
        "boot_project",
    }
    for module in _VERIFICATION_MODULES:
        called = _attribute_calls(module)
        assert not (called & forbidden), f"{module.__name__} must never call: {called & forbidden}"
    assert _call_site_count(route_module, "resolve_record") == 1


def test_independent_verification_never_imports_a_command_execution_or_network_surface() -> None:
    forbidden_substrings = (
        "subprocess",
        "socket",
        "urllib",
        "requests",
        "http.client",
        "os.system",
    )
    for module in _VERIFICATION_MODULES:
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(bad in name for bad in forbidden_substrings), (
                f"{module.__name__} imports a forbidden surface: {name}"
            )


def test_independent_verification_never_imports_a_scheduler_or_background_execution_surface() -> (
    None
):
    forbidden_substrings = ("threading", "asyncio", "sched", "multiprocessing")
    for module in _VERIFICATION_MODULES:
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(bad in name for bad in forbidden_substrings), (
                f"{module.__name__} imports a forbidden scheduler/background surface: {name}"
            )


def test_independent_verification_never_imports_a_model_github_or_observer_surface() -> None:
    forbidden_substrings = ("github", "openai", "anthropic", "observer")
    for module in _VERIFICATION_MODULES:
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(bad in name for bad in forbidden_substrings), (
                f"{module.__name__} imports a forbidden model/GitHub/Observer surface: {name}"
            )


def test_independent_verification_never_imports_os_module_directly() -> None:
    for module in _VERIFICATION_MODULES:
        assert "os" not in _imported_module_names(module)


def test_independent_verification_never_imports_development_binding_or_the_phase_8_fixture() -> (
    None
):
    for module in _VERIFICATION_MODULES:
        imported = _imported_module_names(module)
        assert not any("development_binding" in name for name in imported)
        assert not any("vertical_proof" in name for name in imported)


def test_target_ref_kinds_are_exactly_difference_change_and_observation_evidence() -> None:
    assert (
        frozenset({"difference", "change", "observation_evidence"}) == types_module.TARGET_REF_KINDS
    )


def test_verification_statuses_are_exactly_the_four_issue_51_fixes() -> None:
    assert (
        frozenset({"VERIFIED", "FAILED", "INSUFFICIENT", "UNAVAILABLE"})
        == types_module.VERIFICATION_STATUSES
    )


def test_selection_statuses_are_exactly_active_revoked_expired() -> None:
    assert frozenset({"ACTIVE", "REVOKED", "EXPIRED"}) == types_module.SELECTION_STATUSES


def test_route_calls_boot_project_exactly_once() -> None:
    """Structural Review Round 1 (P13-R1-F2): the existing Boot owner's own public
    ``boot_project`` is the surface this route reuses to independently re-verify the real
    Human Authority reference -- called exactly once, and only from ``route.py``."""

    assert _call_site_count(route_module, "boot_project") == 1
    for module in (types_module, errors_module):
        assert _call_site_count(module, "boot_project") == 0


def test_verification_value_error_is_a_distinct_independent_verification_error() -> None:
    assert issubclass(
        errors_module.VerificationValueError, errors_module.IndependentVerificationError
    )
    error_types: set[type] = {
        errors_module.VerificationValueError,
        errors_module.VerificationRequirementError,
        errors_module.VerifierOutputError,
    }
    assert len(error_types) == 3


def test_independent_verifier_protocol_declares_a_verifier_identity_attribute() -> None:
    """Structural Review Round 1 (P13-R1-F1): a conforming verifier must declare its own
    identity as a real attribute (never a method) for the route to check before invocation."""

    annotations = types_module.IndependentVerifier.__annotations__
    assert "verifier_identity" in annotations
