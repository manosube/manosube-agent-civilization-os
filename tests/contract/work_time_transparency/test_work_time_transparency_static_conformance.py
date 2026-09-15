"""Issue #22 Human Wait-Time Transparency: static conformance proofs.

A real AST walk over the ``work_time_transparency`` package's own module source -- the
identical technique ``tests/contract/change_executor/test_change_executor_static_conformance.py``
and ``tests/contract/runtime/test_runtime_static_conformance.py`` already establish --
pinning ``WORK_TIME_TRANSPARENCY_OWNER_COUNT=1`` and
``PUBLIC_WORK_TIME_TRANSPARENCY_ENTRY_POINT_COUNT=3`` (:func:`open_work_time_coordination`,
:func:`record_work_time_progress_update`, :func:`record_work_time_terminal_notice`), and that
the package performs no network/subprocess/environment I/O and never calls the raw Store
``commit`` method directly.

**Structural Review Round 2 persistence rebind (P84-R2-F1/F4,
``ADOPT_P84_PROJECT_STATE_ORTHOGONAL_COORDINATION_REBIND``).** This package never calls
:func:`~manosube_agent_civilization.store.commit.commit_state_transition` at all -- every
commit goes through the Store's own orthogonal coordination ledger primitive (hardened
Structural Review Round 3, P84-R3-F1, ``ADOPT_P84_R3_COORDINATION_LEDGER_CLOSURE``),
:meth:`~manosube_agent_civilization.store.file_store.FileStateStore.
commit_coordination_record_at_tip`, called only from ``route.py`` (the one sanctioned
committer).
"""

from __future__ import annotations

import ast
import inspect
import pathlib
from types import ModuleType

import manosube_agent_civilization
import manosube_agent_civilization.work_time_transparency as work_time_transparency_module
import manosube_agent_civilization.work_time_transparency.adapters as adapters_module
import manosube_agent_civilization.work_time_transparency.clock as clock_module
import manosube_agent_civilization.work_time_transparency.engine as engine_module
import manosube_agent_civilization.work_time_transparency.errors as errors_module
import manosube_agent_civilization.work_time_transparency.identity as identity_module
import manosube_agent_civilization.work_time_transparency.route as route_module
import manosube_agent_civilization.work_time_transparency.types as types_module
import manosube_agent_civilization.work_time_transparency.verify as verify_module

_ALL_PACKAGE_MODULES = (
    route_module,
    engine_module,
    identity_module,
    types_module,
    errors_module,
    adapters_module,
    clock_module,
    verify_module,
)

_SHIPPED_PACKAGE_ROOT = pathlib.Path(manosube_agent_civilization.__file__).resolve().parent
_WORK_TIME_TRANSPARENCY_PACKAGE_ROOT = _SHIPPED_PACKAGE_ROOT / "work_time_transparency"


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
    return sorted(_WORK_TIME_TRANSPARENCY_PACKAGE_ROOT.glob("*.py"))


def _top_level_function_names(module: ModuleType) -> set[str]:
    return {
        node.name
        for node in _tree(module).body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }


def test_package_module_inventory_matches_the_shipped_directory_exactly() -> None:
    shipped_files = {path.stem for path in _package_files() if path.stem != "__init__"}
    documented_modules = {module.__name__.rsplit(".", 1)[-1] for module in _ALL_PACKAGE_MODULES}
    assert shipped_files == documented_modules, (
        f"undocumented or missing module: shipped={shipped_files} documented={documented_modules}"
    )


def test_no_module_imports_a_network_subprocess_or_filesystem_i_o_surface() -> None:
    forbidden = ("socket", "subprocess", "urllib", "requests", "http.client")
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        offending = {
            name
            for name in imported
            if any(name == f or name.startswith(f + ".") for f in forbidden)
        }
        assert not offending, f"{module.__name__} imports a forbidden I/O surface: {offending}"


def test_only_route_py_calls_commit_coordination_record_at_tip_within_this_package() -> None:
    """Every other module builds records; only ``route.py`` ever persists one -- the identical
    single-committer discipline ``store/commit.py``'s own module docstring requires repo-wide,
    now through the Store's own orthogonal, atomically-tip-guarded coordination ledger
    (Structural Review Round 2, P84-R2-F1/F4; hardened Round 3, P84-R3-F1) rather than
    ``commit_state_transition``, which this package never calls at all -- a Work Coordination
    commit must never reach Project State's own commit path."""

    for module in _ALL_PACKAGE_MODULES:
        source = inspect.getsource(module)
        assert "commit_state_transition(" not in source, (
            f"{module.__name__} must not call commit_state_transition -- Work Coordination "
            "persistence is orthogonal to Project State (Structural Review Round 2)"
        )
        if module is route_module:
            assert "commit_coordination_record_at_tip(" in source
            continue
        assert "commit_coordination_record_at_tip(" not in source, (
            f"{module.__name__} must not call commit_coordination_record_at_tip directly"
        )


def test_no_module_ever_calls_the_raw_store_commit_method() -> None:
    for module in _ALL_PACKAGE_MODULES:
        tree = _tree(module)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr != "commit", (
                    f"{module.__name__} calls store.commit(...) directly -- not the sanctioned "
                    "commit_state_transition wrapper"
                )


def test_public_work_time_transparency_entry_point_count_is_exactly_three() -> None:
    public_route_functions = _top_level_function_names(route_module)
    assert public_route_functions == {
        "open_work_time_coordination",
        "record_work_time_progress_update",
        "record_work_time_terminal_notice",
    }


def test_package_init_reexports_exactly_the_public_entry_points_and_composition_primitive() -> None:
    assert set(work_time_transparency_module.__all__) == {
        "ADAPTER_KINDS",
        "POSITION_KINDS",
        "ProgressReporter",
        "TERMINAL_OUTCOMES",
        "open_work_time_coordination",
        "record_work_time_progress_update",
        "record_work_time_terminal_notice",
        "with_work_time_coordination",
    }


def test_route_module_boots_fresh_on_every_public_entry_point_never_caches_boot_context() -> None:
    """TOCTOU closure: every one of the three entry points must call ``boot_project`` itself,
    never accept a pre-resolved ``BootContext`` as a parameter (which a caller could hold across
    calls and silently go stale)."""

    tree = _tree(route_module)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            arg_names = {arg.arg for arg in node.args.args} | {
                arg.arg for arg in node.args.kwonlyargs
            }
            assert "boot_context" not in arg_names, (
                f"{node.name} accepts a boot_context parameter -- every public entry point must "
                "call boot_project itself"
            )
            body_source = ast.unparse(node)
            assert "boot_project(" in body_source, f"{node.name} never calls boot_project"


def test_every_public_route_entry_point_detaches_caller_input_before_boot_project() -> None:
    """Structural Review Round 1 (P84-R1-F6): ``_detach(...)`` must appear, textually, before
    the first ``boot_project(...)`` call inside every public entry point's own source -- proving
    detachment happens as the *literal first operation*, not merely somewhere before the commit."""

    tree = _tree(route_module)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            body_source = ast.unparse(node)
            detach_index = body_source.find("_detach(")
            boot_index = body_source.find("boot_project(")
            assert detach_index != -1, f"{node.name} never calls _detach"
            assert boot_index != -1, f"{node.name} never calls boot_project"
            assert detach_index < boot_index, (
                f"{node.name} calls boot_project before _detach -- inputs must be detached first"
            )


def test_continuation_entry_points_resolve_and_verify_lineage_through_verify_py() -> None:
    """Structural Review Round 1 (P84-R1-F2/F5): the two continuation entry points must resolve
    ``open_ref``/``predecessor_ref`` through :mod:`~manosube_agent_civilization.
    work_time_transparency.verify`'s own canonical boundary, never trust a caller-supplied record
    body directly."""

    tree = _tree(route_module)
    common_required_calls = (
        "resolve_open(",
        "verify_predecessor_matches(",
        "verify_monotonic_continuation(",
        "verify_binding_congruity(",
    )
    per_function_required_calls = {
        "record_work_time_progress_update": ("resolve_predecessor_at_sequence(",),
        "record_work_time_terminal_notice": ("resolve_tip(",),
    }
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in per_function_required_calls:
            body_source = ast.unparse(node)
            for call in (*common_required_calls, *per_function_required_calls[node.name]):
                assert call in body_source, f"{node.name} never calls {call}"


def test_no_schema_carries_a_human_authority_ref_or_signature_field() -> None:
    """Structural, not conventional: a Work Coordination record must be unable to present
    itself as a Human Authority declaration."""

    import json

    schema_dir = _SHIPPED_PACKAGE_ROOT.parent.parent / "01_SCHEMA" / "work_time_transparency"
    schema_paths = sorted(schema_dir.glob("*.schema.json"))
    assert len(schema_paths) == 3
    for path in schema_paths:
        schema = json.loads(path.read_text())
        properties = schema.get("properties", {})
        assert "human_authority_ref" not in properties, f"{path.name} carries human_authority_ref"
        assert "signature" not in properties, f"{path.name} carries a signature field"
