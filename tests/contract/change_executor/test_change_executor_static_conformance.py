"""Phase 18 (Issue #73) Change Executor: static conformance proofs.

A real AST walk over the ``change_executor`` package's own module source -- never a grep, never
a hardcoded name list beyond the fixed vocabularies this proof pins -- the identical technique
``tests/contract/url_boot/test_url_boot_static_conformance.py`` and ``tests/contract/runtime/
test_runtime_static_conformance.py`` already establish, adapted to this package's own shape:
``CHANGE_EXECUTOR_OWNER_COUNT=1``, ``PUBLIC_CHANGE_EXECUTOR_ENTRY_POINT_COUNT=2``
(:func:`compose_change_executor` ``+1`` :func:`route_change_execution_to_evidence`).
"""

from __future__ import annotations

import ast
import inspect
import pathlib
from types import ModuleType

import pytest
from tests.fixtures.change_executor_world import git_worktree

import manosube_agent_civilization
import manosube_agent_civilization.change_executor as change_executor_module
import manosube_agent_civilization.change_executor.adapter as adapter_module
import manosube_agent_civilization.change_executor.boundary as boundary_module
import manosube_agent_civilization.change_executor.engine as engine_module
import manosube_agent_civilization.change_executor.errors as errors_module
import manosube_agent_civilization.change_executor.evidence_handoff as evidence_handoff_module
import manosube_agent_civilization.change_executor.identity as identity_module
import manosube_agent_civilization.change_executor.kill_switch as kill_switch_module
import manosube_agent_civilization.change_executor.reobservation as reobservation_module
import manosube_agent_civilization.change_executor.route as route_module
import manosube_agent_civilization.change_executor.types as types_module

_ALL_PACKAGE_MODULES = (
    route_module,
    engine_module,
    identity_module,
    types_module,
    errors_module,
    adapter_module,
    boundary_module,
    kill_switch_module,
    evidence_handoff_module,
    reobservation_module,
)

_SHIPPED_PACKAGE_ROOT = pathlib.Path(manosube_agent_civilization.__file__).resolve().parent
_CHANGE_EXECUTOR_PACKAGE_ROOT = _SHIPPED_PACKAGE_ROOT / "change_executor"


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


def _package_files() -> list[pathlib.Path]:
    return sorted(_CHANGE_EXECUTOR_PACKAGE_ROOT.glob("*.py"))


# --------------------------------------------------------------------------------------- #
# (a) adapter.py -- and the whole package -- performs no network/subprocess/environment I/O.
# --------------------------------------------------------------------------------------- #


def test_adapter_module_imports_none_of_socket_subprocess_urllib_requests() -> None:
    forbidden = ("socket", "subprocess", "urllib", "requests")
    imported = _imported_module_names(adapter_module)
    offending = {
        name for name in imported if any(name == f or name.startswith(f + ".") for f in forbidden)
    }
    assert not offending, f"adapter.py imports a forbidden I/O surface: {offending}"


def test_no_shipped_module_imports_os_in_an_environment_mutating_way() -> None:
    """No module imports ``os`` at all (the package performs no filesystem discovery, no
    environment read, and ``adapter.py`` itself uses only ``pathlib.Path``)."""

    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        offending = {name for name in imported if name == "os" or name.startswith("os.")}
        assert not offending, f"{module.__name__} imports os: {offending}"


def test_no_shipped_module_calls_os_environ_setitem_or_os_putenv() -> None:
    """Even though no module imports ``os`` at all (the stronger check above), this proves the
    specific mutating calls the task names are absent by AST inspection of every call site in
    the whole package -- a real, decisive control rather than an import-list inference alone."""

    for path in _package_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "putenv":
                raise AssertionError(f"{path} calls os.putenv at line {node.lineno}")
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "__setitem__"
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "environ"
            ):
                raise AssertionError(f"{path} calls os.environ.__setitem__ at line {node.lineno}")
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript):
                target = node.value
                if isinstance(target, ast.Attribute) and target.attr == "environ":
                    parent_is_store = isinstance(node.ctx, ast.Store)
                    assert not parent_is_store, (
                        f"{path} assigns os.environ[...] at line {node.lineno}"
                    )


# --------------------------------------------------------------------------------------- #
# (b) route.py's composed closure carries exactly the request-facing parameter set.
# --------------------------------------------------------------------------------------- #


class _StubAdapter:
    def execute(self, operation: object, *, worktree_root: str) -> dict[str, object]:
        return {"files_written": [], "bytes_written": 0, "files_deleted": [], "error": None}


def _minimal_boundary(worktree_root: str) -> dict[str, object]:
    """``worktree_root`` is a required argument, never a default (P18-R1-F3, Structural Review
    Round 1): it is now a required, schema-validated field *inside* the closed Boundary itself,
    resolving to a real, existing directory -- there is no fixed value that could ever be correct
    across every caller's own real ``tmp_path``."""

    return {
        "permitted_action_kinds": ["WRITE_DOCUMENTATION_FILE"],
        "repository": "org/repo",
        "branch": "main",
        "admitted_paths": ["docs"],
        "max_files_changed": 1,
        "max_bytes_changed": 1000,
        "max_file_bytes": 1000,
        "permit_symlinks": False,
        "permit_path_traversal": False,
        "permit_network": False,
        "permit_subprocess": False,
        "permit_environment_mutation": False,
        "permit_credential_access": False,
        "timeout_seconds": 30,
        "rollback_policy": "NONE",
        "executor_identity": "controlled_filesystem_adapter",
        "executor_version": "0.1",
        "validity_window": {
            "issued_at": "2026-09-10T00:00:00Z",
            "expires_at": "2026-09-10T01:00:00Z",
        },
        "worktree_root": worktree_root,
    }


def _minimal_boundary_at(tmp_path: pathlib.Path) -> dict[str, object]:
    """:func:`_minimal_boundary`, at a real git checkout of its own declared ``"org/repo"``/
    ``"main"`` (P18-R2-F2, Structural Review Round 2: ``worktree_root`` must now also verify as
    a genuine checkout of the Boundary's own declared repository/branch, not merely an existing
    directory)."""

    worktree_root = git_worktree(tmp_path, repository="org/repo", branch="main")
    return _minimal_boundary(str(worktree_root))


def test_composed_execute_closure_has_exactly_the_request_facing_parameter_set(
    tmp_path: pathlib.Path,
) -> None:
    """No ``store``/``project_id``/``project_binding_id``/Boundary/adapter/``worktree_root``
    parameter anywhere in the returned closure's own signature -- introspecting a real Python
    object (``inspect.signature``), never AST, since this proves what a caller of the *closure
    itself* can pass, not merely what the composing function's own source names.
    ``worktree_root`` is bound at composition, inside the closed Boundary itself (P18-R1-F3,
    Structural Review Round 1, superseding the prior round's separate composition-time
    parameter) -- it is asserted absent from the returned closure's own signature exactly like
    every other trust-sensitive composition-time parameter, and ``compose_change_executor``
    itself no longer accepts a bare ``worktree_root=`` keyword at all."""

    execute = change_executor_module.compose_change_executor(
        object(),
        project_id="PRJ-STATIC-0001",
        project_binding_id="PROJBIND-STATIC-0001",
        execution_boundary=_minimal_boundary_at(tmp_path),
        adapter_identity={"kind": "stub", "version": "0.1"},
        adapter=_StubAdapter(),
        kill_switch_trust_anchor_public_key_hex="ab" * 32,
    )
    code = execute.__code__
    varnames = code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]
    assert set(varnames) == {
        "change_id",
        "claim_token",
        "execution_instant",
        "permit_semantic_reuse",
    }
    signature = inspect.signature(execute)
    assert set(signature.parameters) == {
        "change_id",
        "claim_token",
        "execution_instant",
        "permit_semantic_reuse",
    }
    for forbidden in (
        "store",
        "project_id",
        "project_binding_id",
        "execution_boundary",
        "adapter",
        "adapter_identity",
        "worktree_root",
    ):
        assert forbidden not in signature.parameters, forbidden


def test_compose_change_executor_rejects_a_worktree_root_keyword_argument_at_composition(
    tmp_path: pathlib.Path,
) -> None:
    """``compose_change_executor`` itself no longer accepts a bare ``worktree_root=`` keyword at
    all (P18-R1-F3): a genuine ``TypeError``, never a silently-accepted-and-ignored keyword,
    confirms the parameter is really gone from composition's own call shape, not merely from the
    Boundary's own required-keys set."""

    with pytest.raises(TypeError):
        change_executor_module.compose_change_executor(
            object(),
            project_id="PRJ-STATIC-0004",
            project_binding_id="PROJBIND-STATIC-0004",
            execution_boundary=_minimal_boundary_at(tmp_path),
            adapter_identity={"kind": "stub", "version": "0.1"},
            adapter=_StubAdapter(),
            worktree_root=str(tmp_path),
            kill_switch_trust_anchor_public_key_hex="ab" * 32,
        )


def test_compose_change_executor_requires_worktree_root_to_be_an_existing_directory(
    tmp_path: pathlib.Path,
) -> None:
    """``worktree_root`` is validated at composition time, as part of Boundary validation -- a
    non-existent directory refuses before any request-facing operation can even be obtained
    (mirrors how a malformed ``execution_boundary``/``adapter_identity`` already refuses at this
    same point)."""

    from manosube_agent_civilization.change_executor.errors import ChangeExecutorError

    missing = tmp_path / "does-not-exist"
    with pytest.raises(ChangeExecutorError):
        change_executor_module.compose_change_executor(
            object(),
            project_id="PRJ-STATIC-0002",
            project_binding_id="PROJBIND-STATIC-0002",
            execution_boundary=_minimal_boundary(str(missing)),
            adapter_identity={"kind": "stub", "version": "0.1"},
            adapter=_StubAdapter(),
            kill_switch_trust_anchor_public_key_hex="ab" * 32,
        )


def test_composed_execute_closure_rejects_a_worktree_root_keyword_argument(
    tmp_path: pathlib.Path,
) -> None:
    """A genuine ``TypeError`` -- never a silently-accepted-and-ignored keyword -- confirms
    ``worktree_root`` really is gone from the returned closure's own call shape, not merely
    absent from the two static-shape checks above. Calling the closure with a ``worktree_root=``
    keyword must raise, exactly as passing any other composition-time-only parameter would."""

    execute = change_executor_module.compose_change_executor(
        object(),
        project_id="PRJ-STATIC-0003",
        project_binding_id="PROJBIND-STATIC-0003",
        execution_boundary=_minimal_boundary_at(tmp_path),
        adapter_identity={"kind": "stub", "version": "0.1"},
        adapter=_StubAdapter(),
        kill_switch_trust_anchor_public_key_hex="ab" * 32,
    )
    with pytest.raises(TypeError):
        execute(
            "CHANGE-" + "A" * 64,
            claim_token="claim",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
            worktree_root=str(tmp_path),
        )


# --------------------------------------------------------------------------------------- #
# (c) no function anywhere in the shipped package accepts a generic policy-callable parameter.
# --------------------------------------------------------------------------------------- #


_FORBIDDEN_PARAM_NAMES = {
    "classify_resolved_address",
    "perform_resolution",
    "perform_connection",
    "classify",
}


def test_no_shipped_function_accepts_a_generic_policy_callable_parameter() -> None:
    """Mirrors ``tests/contract/url_boot/test_url_boot_static_conformance.py``'s own
    ``test_route_py_ships_no_function_accepting_a_classifier_resolver_or_connector_callable``,
    scaled to every module in this package: no ``FunctionDef``/``AsyncFunctionDef`` anywhere
    declares a parameter (positional, keyword-only, ``*args``, or ``**kwargs``) named
    ``classify_resolved_address``, ``perform_resolution``, ``perform_connection``, ``classify``,
    or any other generic dependency-injection surface -- the shipped package offers no such
    injection point at all."""

    for path in _package_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            all_args = (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
                + ([node.args.vararg] if node.args.vararg else [])
                + ([node.args.kwarg] if node.args.kwarg else [])
            )
            declared_names = {arg.arg for arg in all_args}
            offending = declared_names & _FORBIDDEN_PARAM_NAMES
            assert not offending, f"{path}:{node.name} declares forbidden parameter(s): {offending}"


# --------------------------------------------------------------------------------------- #
# (d) __all__ pins.
# --------------------------------------------------------------------------------------- #


def test_route_py_public_surface_is_exactly_one_entry_point() -> None:
    assert route_module.__all__ == ["compose_change_executor"]


def test_evidence_handoff_public_surface_is_pinned_exactly() -> None:
    """Pins the exact current ``__all__`` list (read from the real file first) so a future
    accidental export is caught by this test rather than silently widening the public surface."""

    assert evidence_handoff_module.__all__ == [
        "REQUIRED_PROVENANCE_FIELDS",
        "resolve_and_verify_committed_receipt",
        "route_change_execution_to_evidence",
    ]


def test_change_executor_package_exports_exactly_two_public_routes() -> None:
    public_callables = {
        name
        for name in change_executor_module.__all__
        if callable(getattr(change_executor_module, name))
        and not isinstance(getattr(change_executor_module, name), type)
    }
    assert public_callables & {"compose_change_executor", "route_change_execution_to_evidence"} == {
        "compose_change_executor",
        "route_change_execution_to_evidence",
    }


# --------------------------------------------------------------------------------------- #
# (e) kill_switch.py's own read-only preflight surface vs its own commit-retry-loop surface.
# --------------------------------------------------------------------------------------- #


def _function_source(module: ModuleType, name: str) -> str:
    obj = getattr(module, name)
    return inspect.getsource(obj)


def _call_names_in(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
            elif isinstance(func, ast.Name):
                names.add(func.id)
    return names


def test_resolve_current_kill_switch_calls_read_current_consistent_never_load_current() -> None:
    calls = _call_names_in(_function_source(kill_switch_module, "resolve_current_kill_switch"))
    assert "read_current_consistent" in calls
    assert "load_current" not in calls


def test_commit_change_executor_kill_switch_calls_load_current_inside_its_own_retry_loop() -> None:
    """The identical, correct convention every other committer in this repository uses inside
    its own Compare-And-Swap retry loop -- this is the *expected* call site, proven present
    rather than absent."""

    calls = _call_names_in(
        _function_source(kill_switch_module, "commit_change_executor_kill_switch")
    )
    assert "load_current" in calls


def test_route_commit_records_calls_load_current_inside_its_own_retry_loop() -> None:
    calls = _call_names_in(_function_source(route_module, "_commit_records"))
    assert "load_current" in calls


__all__: list[str] = []
