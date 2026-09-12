"""Phase 19 (Issue #77) Multi-Agent Dynamic Execution: static conformance proofs.

A real AST walk over the ``multi_agent`` package's own module source -- never a grep, never a
hardcoded name list -- mirroring ``tests/contract/model_runtime/
test_model_runtime_static_conformance.py``'s own technique exactly, adapted to this delivery's
own two-Temporary-Agent-role architecture (see ``route.py``'s own module docstring for why this
package has *two* literal ``start_temporary_agent`` call sites where Model Runtime has one).
"""

from __future__ import annotations

import ast
import inspect
from types import ModuleType

import pytest

import manosube_agent_civilization.multi_agent as multi_agent_package
import manosube_agent_civilization.multi_agent.engine as engine_module
import manosube_agent_civilization.multi_agent.errors as errors_module
import manosube_agent_civilization.multi_agent.evidence_handoff as evidence_handoff_module
import manosube_agent_civilization.multi_agent.identity as identity_module
import manosube_agent_civilization.multi_agent.route as route_module
import manosube_agent_civilization.multi_agent.selection as selection_module
import manosube_agent_civilization.multi_agent.types as types_module

pytestmark = pytest.mark.contract

_ALL_PACKAGE_MODULES = (
    route_module,
    engine_module,
    identity_module,
    types_module,
    errors_module,
    selection_module,
    evidence_handoff_module,
    multi_agent_package,
)

#: Existing canonical owners this package never becomes a second implementation of, and never
#: reaches around: Reflow (re-observation/closure), Independent Verification, Projection,
#: Runtime, and Change Executor (the one existing owner able to perform a real Change side
#: effect). None of these is imported, in whole or in part, anywhere in this package.
_FORBIDDEN_OWNER_MODULE_PREFIXES = (
    "manosube_agent_civilization.reflow",
    "manosube_agent_civilization.independent_verification",
    "manosube_agent_civilization.projection",
    "manosube_agent_civilization.runtime",
    "manosube_agent_civilization.change_executor",
    "manosube_agent_civilization.change",
)


def _tree(module: ModuleType) -> ast.Module:
    return ast.parse(inspect.getsource(module))


def _imported_module_names(module: ModuleType) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree(module)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _call_site_count(module: ModuleType, name: str) -> int:
    count = 0
    for node in ast.walk(_tree(module)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (isinstance(func, ast.Name) and func.id == name) or (
            isinstance(func, ast.Attribute) and func.attr == name
        ):
            count += 1
    return count


def _function_names(module: ModuleType) -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree(module))
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def _class_defs(module: ModuleType) -> list[ast.ClassDef]:
    return [node for node in ast.walk(_tree(module)) if isinstance(node, ast.ClassDef)]


def _try_finally_releases(node: ast.Try, *, bound_name: str) -> bool:
    for handler_node in node.finalbody:
        for inner in ast.walk(handler_node):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "release"
                and isinstance(inner.func.value, ast.Name)
                and inner.func.value.id == bound_name
            ):
                return True
    return False


# =========================================================================== #
# 1. No forbidden existing owner is reached, in whole or in part
# =========================================================================== #


def test_no_module_imports_a_forbidden_existing_owner() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        hits = {
            name
            for name in imported
            if any(name.startswith(prefix) for prefix in _FORBIDDEN_OWNER_MODULE_PREFIXES)
        }
        assert not hits, f"{module.__name__} imports a forbidden owner: {hits}"


def test_no_module_calls_reflow_or_reopen() -> None:
    """P19-C10's own static-conformance proof: this package never orchestrates its own
    re-observation route -- it never calls Reflow's own ``reflow``/``reopen`` at all, by name,
    anywhere."""

    for module in _ALL_PACKAGE_MODULES:
        assert _call_site_count(module, "reflow") == 0, module.__name__
        assert _call_site_count(module, "reopen") == 0, module.__name__


def test_no_module_imports_a_change_executor_composition_or_execution_surface() -> None:
    """This package never mints or executes a Change: ``compose_change_executor`` and
    ``execute`` (Change Executor's own composed entry point) are never imported or called
    anywhere in this package."""

    for module in _ALL_PACKAGE_MODULES:
        assert _call_site_count(module, "compose_change_executor") == 0, module.__name__
        imported = _imported_module_names(module)
        assert not any("change_executor" in name for name in imported), module.__name__


def test_no_module_evaluates_authority_or_derives_a_change_itself() -> None:
    """Authority is reproduced by the existing Model Runtime/Authority owners, never minted
    here: no module in this package calls either Authority evaluator, and no module derives a
    canonical Change, Evidence record, or Closure Evaluation of its own."""

    forbidden_producers = (
        "evaluate_authority",
        "evaluate_model_execution_authorization",
        "derive_change",
        "derive_evidence",
        "evaluate_closure",
        "derive_closure_evaluation",
        "close_difference",
    )
    for module in _ALL_PACKAGE_MODULES:
        for name in forbidden_producers:
            assert _call_site_count(module, name) == 0, (module.__name__, name)
        for name in _function_names(module):
            assert name not in forbidden_producers, (module.__name__, name)


# =========================================================================== #
# 2. Exactly two Temporary Agent roles, exactly two start_temporary_agent call sites, and
#    no second Temporary-Agent-shaped implementation
# =========================================================================== #


def test_start_temporary_agent_has_exactly_two_disclosed_call_sites() -> None:
    """See ``route.py``'s own module docstring: the caller's own coordinator-liveness Agent
    (:func:`~manosube_agent_civilization.multi_agent.route._fresh_execution_contract`) and the
    per-slot execution Agent (inside :func:`~manosube_agent_civilization.multi_agent.route.
    _execute_one_slot`) are this package's own only two literal call sites -- never a third,
    drifting way to obtain one."""

    total = sum(
        _call_site_count(module, "start_temporary_agent") for module in _ALL_PACKAGE_MODULES
    )
    assert total == 2
    assert _call_site_count(route_module, "start_temporary_agent") == 2
    for module in _ALL_PACKAGE_MODULES:
        if module is not route_module:
            assert _call_site_count(module, "start_temporary_agent") == 0, module.__name__

    fresh_contract = next(
        node
        for node in ast.walk(_tree(route_module))
        if isinstance(node, ast.FunctionDef) and node.name == "_fresh_execution_contract"
    )
    execute_one_slot = next(
        node
        for node in ast.walk(_tree(route_module))
        if isinstance(node, ast.FunctionDef) and node.name == "_execute_one_slot"
    )
    for owner in (fresh_contract, execute_one_slot):
        assert any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "start_temporary_agent"
            for node in ast.walk(owner)
        ), owner.name


def test_no_module_boots_a_project_or_constructs_a_temporary_agent_directly() -> None:
    """This package never imports ``boot_project`` (Boot is reached only through Phase 12's
    own ``start_temporary_agent``) and never imports or constructs
    ``_ActiveTemporaryAgent`` -- the one private concrete Temporary Agent implementation
    Phase 12 itself never exports."""

    for module in _ALL_PACKAGE_MODULES:
        assert _call_site_count(module, "boot_project") == 0, module.__name__
        assert _call_site_count(module, "_ActiveTemporaryAgent") == 0, module.__name__
        imported = _imported_module_names(module)
        assert "manosube_agent_civilization.boot" not in imported, module.__name__
        assert "manosube_agent_civilization.boot.route" not in imported, module.__name__


def test_no_module_defines_a_second_temporary_agent_shaped_class() -> None:
    """No class defined anywhere in this package declares both a ``boot_context`` property
    and a ``release`` method -- the exact shape that would make it a second, competing
    Temporary Agent lifecycle implementation (P19-C3)."""

    for module in _ALL_PACKAGE_MODULES:
        for class_node in _class_defs(module):
            method_names = {
                node.name
                for node in class_node.body
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            }
            assert not {"boot_context", "release"} <= method_names, (
                module.__name__,
                class_node.name,
            )


def _assigned_names_from_call(node: ast.AST, *, call_name: str) -> set[str]:
    names: set[str] = set()
    for inner in ast.walk(node):
        if (
            isinstance(inner, ast.Assign)
            and len(inner.targets) == 1
            and isinstance(inner.targets[0], ast.Name)
            and isinstance(inner.value, ast.Call)
            and isinstance(inner.value.func, ast.Name)
            and inner.value.func.id == call_name
        ):
            names.add(inner.targets[0].id)
    return names


def test_every_start_temporary_agent_call_site_is_guarded_by_a_releasing_finally() -> None:
    """P19-C8's own decisive structural proof: every function in this package that assigns
    the result of a ``start_temporary_agent`` call also contains a ``Try`` node whose own
    ``finally`` clause calls ``.release()`` on that identical bound name -- so every Agent
    this package ever constructs is released even if the code between construction and
    release raises."""

    checked_any = False
    for node in ast.walk(_tree(route_module)):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        bound_names = _assigned_names_from_call(node, call_name="start_temporary_agent")
        if not bound_names:
            continue
        try_nodes = [inner for inner in ast.walk(node) if isinstance(inner, ast.Try)]
        for bound_name in bound_names:
            checked_any = True
            assert any(
                _try_finally_releases(try_node, bound_name=bound_name) for try_node in try_nodes
            ), (node.name, bound_name)
    assert checked_any


# =========================================================================== #
# 3. One sanctioned committer, reused (never a second one)
# =========================================================================== #


def test_no_module_calls_store_commit_directly() -> None:
    for module in _ALL_PACKAGE_MODULES:
        for node in ast.walk(_tree(module)):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "commit":
                continue
            assert isinstance(node.func.value, ast.Name) and node.func.value.id != "store", (
                f"{module.__name__} appears to call store.commit(...) directly, bypassing "
                "commit_state_transition"
            )


def test_commit_state_transition_is_imported_only_by_the_route() -> None:
    """``route.py`` is the one module in this package that imports the shared committer;
    ``evidence_handoff.py`` reuses ``route.py``'s own already-committing ``_commit`` helper
    (a disclosed intra-package exception -- see that module's own docstring) rather than
    importing the committer a second time."""

    for module in _ALL_PACKAGE_MODULES:
        imports_committer = "manosube_agent_civilization.store.commit" in _imported_module_names(
            module
        )
        if module is route_module:
            assert imports_committer
            assert _call_site_count(module, "commit_state_transition") == 1
        else:
            assert not imports_committer, module.__name__
            assert _call_site_count(module, "commit_state_transition") == 0, module.__name__


def test_evidence_handoff_reuses_the_routes_own_commit_helper_rather_than_a_second_one() -> None:
    imported = _imported_module_names(evidence_handoff_module)
    assert "manosube_agent_civilization.store.commit" not in imported
    assert _call_site_count(evidence_handoff_module, "_commit") == 1


# =========================================================================== #
# 4. Reused Model Runtime execution contract, reused Evidence hand-off, no second one
# =========================================================================== #


def test_model_runtime_execution_routes_are_reused_not_reimplemented() -> None:
    assert _call_site_count(route_module, "open_model_work_unit") == 1
    assert _call_site_count(route_module, "execute_model_work_unit") == 1
    for module in _ALL_PACKAGE_MODULES:
        if module is route_module:
            continue
        assert _call_site_count(module, "open_model_work_unit") == 0, module.__name__
        assert _call_site_count(module, "execute_model_work_unit") == 0, module.__name__


def test_route_model_execution_to_evidence_is_reused_exactly_once() -> None:
    assert _call_site_count(evidence_handoff_module, "route_model_execution_to_evidence") == 1
    for module in _ALL_PACKAGE_MODULES:
        if module is evidence_handoff_module:
            continue
        assert _call_site_count(module, "route_model_execution_to_evidence") == 0, module.__name__


# =========================================================================== #
# 5. Record kinds and package shape
# =========================================================================== #


def test_this_package_declares_exactly_the_record_kinds_it_owns() -> None:
    route_kinds = {
        target.id: node.value.value
        for node in ast.walk(_tree(route_module))
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id.endswith("RECORD_KIND")
    }
    assert route_kinds == {
        "PLAN_RECORD_KIND": "multi_agent_dynamic_execution_plan",
        "SLOT_OUTPUT_RECORD_KIND": "multi_agent_slot_output",
        "SLOT_ATTEMPT_ENVELOPE_CLAIM_RECORD_KIND": "multi_agent_slot_attempt_envelope_claim",
        "RELEASE_RECEIPT_RECORD_KIND": "multi_agent_agent_release_receipt",
        "CONFLICT_SET_RECORD_KIND": "multi_agent_conflict_set",
        "AGGREGATION_INPUT_RECORD_KIND": "multi_agent_evidence_aggregation_input",
        "DIFFERENCE_RECORD_KIND": "difference",
        "BOUNDARY_RECORD_KIND": "model_execution_boundary",
        "GRANT_RECORD_KIND": "model_execution_grant",
        "DECISION_RECORD_KIND": "model_execution_decision",
        "WORK_UNIT_RECORD_KIND": "model_work_unit",
        "ENVELOPE_RECORD_KIND": "model_execution_envelope",
    }
    evidence_handoff_kinds = {
        target.id: node.value.value
        for node in ast.walk(_tree(evidence_handoff_module))
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id.endswith("RECORD_KIND")
    }
    assert evidence_handoff_kinds == {
        "ORCHESTRATION_RECEIPT_RECORD_KIND": "multi_agent_orchestration_receipt"
    }


def test_the_package_declares_exactly_three_public_entry_points() -> None:
    assert multi_agent_package.PUBLIC_MULTI_AGENT_ENTRY_POINT_COUNT == 3
    routes = {
        "open_dynamic_execution_plan",
        "execute_dynamic_execution_plan",
        "route_orchestration_to_evidence",
    }
    assert routes <= set(multi_agent_package.__all__)


def test_the_package_declares_it_is_not_a_ninth_kernel_element() -> None:
    assert "KERNEL_ELEMENT=NONE_MULTI_AGENT_ORCHESTRATION_ADAPTER" in (
        multi_agent_package.__doc__ or ""
    )


def test_every_route_requires_a_live_temporary_agent_as_its_own_second_argument() -> None:
    for owner, name in (
        (route_module, "open_dynamic_execution_plan"),
        (route_module, "execute_dynamic_execution_plan"),
        (evidence_handoff_module, "route_orchestration_to_evidence"),
    ):
        signature = inspect.signature(getattr(owner, name))
        parameters = list(signature.parameters)
        assert parameters[:2] == ["store", "agent"], name


def test_the_one_canonical_serializer_is_reused_only_by_identity() -> None:
    assert "manosube_agent_civilization.state.canonicalize" in _imported_module_names(
        identity_module
    )
    for module in _ALL_PACKAGE_MODULES:
        if module is identity_module:
            continue
        assert "manosube_agent_civilization.state.canonicalize" not in _imported_module_names(
            module
        ), module.__name__
        assert _call_site_count(module, "canonical_json_bytes") == 0, module.__name__


def test_shipped_package_imports_no_tests_module_anywhere() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        assert not any(name == "tests" or name.startswith("tests.") for name in imported), (
            f"{module.__name__} imports a tests module: {imported}"
        )


def test_the_capability_vocabulary_is_reused_never_restated() -> None:
    """P19-C1's own research note: this package's own capability vocabulary is literally the
    Model Runtime one, never a second definition of the same one value."""

    assert types_module.MULTI_AGENT_CAPABILITIES is not None
    from manosube_agent_civilization.model_runtime.types import MODEL_EXECUTION_CAPABILITIES

    assert types_module.MULTI_AGENT_CAPABILITIES == MODEL_EXECUTION_CAPABILITIES
    assert types_module.MULTI_AGENT_SLOT_OUTCOMES == (
        __import__(
            "manosube_agent_civilization.model_runtime.types", fromlist=["MODEL_EXECUTION_OUTCOMES"]
        ).MODEL_EXECUTION_OUTCOMES
    )
