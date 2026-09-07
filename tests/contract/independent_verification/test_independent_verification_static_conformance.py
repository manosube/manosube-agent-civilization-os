"""Phase 13 (Issue #51) Independent Verification: static conformance proofs.

A real AST walk over the ``independent_verification`` package's own module source -- never a
grep, never a hardcoded name list -- proving exactly two public callables
(``run_independent_verification``, and Structural Review Round 2's
``route_verification_result_to_evidence``), that ``store.resolve_record`` is the only Store
method this package ever calls, that no existing owner (Difference, Reflow, Binding) is ever
imported anywhere, that ``evidence`` is imported only from ``evidence_handoff.py`` and only to
call ``derive_evidence`` exactly once, that ``authority`` is imported only from ``route.py``
and only to call the existing Authority owner's own
``evaluate_verifier_selection`` exactly once (Structural Review Round 3, P13-R3-F1 -- the
identical reuse-by-call pattern Round 1 already established for ``boot_project``), and that no
module in this package imports a model, subprocess, shell, network, GitHub, Observer,
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
import manosube_agent_civilization.independent_verification.evidence_handoff as evidence_handoff_module
import manosube_agent_civilization.independent_verification.route as route_module
import manosube_agent_civilization.independent_verification.types as types_module

#: Modules that must never import the existing Evidence owner -- ``evidence_handoff.py`` is
#: deliberately excluded (Structural Review Round 2, P13-R2-F2): it alone calls the existing
#: Evidence owner's own public ``derive_evidence``, and is checked separately below.
_VERIFICATION_MODULES = (route_module, types_module, errors_module)

#: Every module in the package, including ``evidence_handoff.py`` -- used only for checks
#: that apply regardless of the Evidence exemption (no subprocess/network/scheduler/model
#: surface, no Store method beyond ``resolve_record``, no development-binding fixture).
_ALL_PACKAGE_MODULES = (route_module, types_module, errors_module, evidence_handoff_module)

#: Existing canonical owners no module in this package may ever import -- Issue #51's own
#: delivery constraint ("reuse existing public owners; do not copy canonical Evidence,
#: Difference, Authority, Reflow, Store, Boot, or Binding logic") made checkable rather than
#: merely asserted in prose. Neither ``evidence`` nor ``authority`` appears here: each has
#: exactly one module permitted to import it, checked by name below rather than folded into
#: one shared list, so a permission granted to one module can never silently cover another.
_FORBIDDEN_OWNER_MODULE_PREFIXES = (
    "manosube_agent_civilization.difference",
    "manosube_agent_civilization.reflow",
    "manosube_agent_civilization.binding",
)

#: Applied to every module except ``evidence_handoff.py`` (Structural Review Round 2,
#: P13-R2-F2: it alone calls the existing Evidence owner's own public ``derive_evidence`` --
#: reuse by call, not a second Evidence owner).
_FORBIDDEN_FOR_NON_EVIDENCE_HANDOFF = (
    *_FORBIDDEN_OWNER_MODULE_PREFIXES,
    "manosube_agent_civilization.evidence",
)

#: Applied to every module except ``route.py`` (Structural Review Round 1, P13-R1-F2 for
#: ``boot``, and Round 3, P13-R3-F1 for ``authority``: ``route.py`` alone calls the existing
#: Boot owner's own public ``boot_project`` and the existing Authority owner's own public
#: ``evaluate_verifier_selection``, each exactly once -- reuse by call, not a second owner of
#: either). ``boot`` was never added to ``_FORBIDDEN_OWNER_MODULE_PREFIXES`` at all (Round 1),
#: so only ``authority`` needs adding here; the positive proofs
#: ``test_route_calls_boot_project_exactly_once`` and
#: ``test_route_calls_evaluate_verifier_selection_exactly_once`` below pair with both.
_FORBIDDEN_FOR_NON_ROUTE = (
    *_FORBIDDEN_FOR_NON_EVIDENCE_HANDOFF,
    "manosube_agent_civilization.authority",
)

#: ``evidence_handoff.py``'s own forbidden set: it may import ``evidence`` (its whole
#: purpose), but not ``authority`` -- that reuse belongs to ``route.py`` alone.
_FORBIDDEN_FOR_EVIDENCE_HANDOFF = (
    *_FORBIDDEN_OWNER_MODULE_PREFIXES,
    "manosube_agent_civilization.authority",
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


def test_independent_verification_package_exports_exactly_two_public_routes() -> None:
    """Structural Review Round 2 (P13-R2-F2) adds one public callable --
    ``route_verification_result_to_evidence`` -- alongside ``run_independent_verification``;
    no third public callable exists."""

    assert verification_module.__all__.count("run_independent_verification") == 1
    assert verification_module.__all__.count("route_verification_result_to_evidence") == 1
    public_callables = {
        name
        for name in verification_module.__all__
        if callable(getattr(verification_module, name))
        and not isinstance(getattr(verification_module, name), type)
    }
    assert public_callables == {
        "run_independent_verification",
        "route_verification_result_to_evidence",
    }


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
    """Issue #51: reuse existing owners by call, never by importing their implementation.

    ``types.py``/``errors.py``/``__init__.py`` may never import ``evidence`` or ``authority``
    -- only ``evidence_handoff.py`` may import ``evidence`` (Structural Review Round 2,
    P13-R2-F2) and only ``route.py`` may import ``authority`` (Structural Review Round 3,
    P13-R3-F1); both checked separately below."""

    for module in (verification_module, types_module, errors_module):
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(name.startswith(prefix) for prefix in _FORBIDDEN_FOR_NON_ROUTE), (
                f"{module.__name__} imports a forbidden existing-owner module: {name}"
            )


def test_route_never_imports_evidence_or_a_difference_reflow_binding_owner() -> None:
    """``route.py`` may import ``authority`` (to call ``evaluate_verifier_selection``, checked
    separately below) and ``boot``, but never ``evidence``, ``difference``, ``reflow``, or
    ``binding`` -- it stays a thin route, not a second owner of any of those."""

    imported = _imported_module_names(route_module)
    for name in imported:
        assert not any(name.startswith(prefix) for prefix in _FORBIDDEN_FOR_NON_EVIDENCE_HANDOFF), (
            f"{route_module.__name__} imports a forbidden existing-owner module: {name}"
        )


def test_evidence_handoff_never_imports_a_non_evidence_existing_owner() -> None:
    """``evidence_handoff.py`` may import ``evidence`` (to call ``derive_evidence``), but
    never ``difference``, ``authority``, ``reflow``, or ``binding`` -- it stays a thin,
    single-purpose handoff, not a second owner of any of those."""

    imported = _imported_module_names(evidence_handoff_module)
    for name in imported:
        assert not any(name.startswith(prefix) for prefix in _FORBIDDEN_FOR_EVIDENCE_HANDOFF), (
            f"{evidence_handoff_module.__name__} imports a forbidden existing-owner module: {name}"
        )


def test_evidence_handoff_calls_derive_evidence_exactly_once_and_only_there() -> None:
    """Structural Review Round 2 (P13-R2-F2): the existing Evidence owner's own public
    ``derive_evidence`` is the surface this handoff reuses -- called exactly once, and only
    from ``evidence_handoff.py``."""

    assert _call_site_count(evidence_handoff_module, "derive_evidence") == 1
    for module in _VERIFICATION_MODULES:
        assert _call_site_count(module, "derive_evidence") == 0


def test_route_calls_evaluate_verifier_selection_exactly_once() -> None:
    """Structural Review Round 3 (P13-R3-F1): the existing Authority owner's own public
    ``evaluate_verifier_selection`` is the surface this route reuses to independently
    re-verify that a real Human Authority selected this exact ``VerifierSelection`` -- called
    exactly once, and only from ``route.py``."""

    assert _call_site_count(route_module, "evaluate_verifier_selection") == 1
    for module in (types_module, errors_module, evidence_handoff_module):
        assert _call_site_count(module, "evaluate_verifier_selection") == 0


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
    for module in _ALL_PACKAGE_MODULES:
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
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(bad in name for bad in forbidden_substrings), (
                f"{module.__name__} imports a forbidden surface: {name}"
            )


def test_independent_verification_never_imports_a_scheduler_or_background_execution_surface() -> (
    None
):
    forbidden_substrings = ("threading", "asyncio", "sched", "multiprocessing")
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(bad in name for bad in forbidden_substrings), (
                f"{module.__name__} imports a forbidden scheduler/background surface: {name}"
            )


def test_independent_verification_never_imports_a_model_github_or_observer_surface() -> None:
    forbidden_substrings = ("github", "openai", "anthropic", "observer")
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        for name in imported:
            assert not any(bad in name for bad in forbidden_substrings), (
                f"{module.__name__} imports a forbidden model/GitHub/Observer surface: {name}"
            )


def test_independent_verification_never_imports_os_module_directly() -> None:
    for module in _ALL_PACKAGE_MODULES:
        assert "os" not in _imported_module_names(module)


def test_independent_verification_never_imports_development_binding_or_the_phase_8_fixture() -> (
    None
):
    for module in _ALL_PACKAGE_MODULES:
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
    assert issubclass(
        errors_module.EvidenceHandoffError, errors_module.IndependentVerificationError
    )
    error_types: set[type] = {
        errors_module.VerificationValueError,
        errors_module.VerificationRequirementError,
        errors_module.VerifierOutputError,
        errors_module.EvidenceHandoffError,
    }
    assert len(error_types) == 4


def test_independent_verifier_protocol_declares_a_verifier_identity_attribute() -> None:
    """Structural Review Round 1 (P13-R1-F1): a conforming verifier must declare its own
    identity as a real attribute (never a method) for the route to check before invocation."""

    annotations = types_module.IndependentVerifier.__annotations__
    assert "verifier_identity" in annotations
