"""Issue #89 (``ADOPT_PHASE_21_COMPARATIVE_BENCHMARK``): static conformance proofs for the
Comparative Benchmark package.

A real AST/source walk over the ``comparative_benchmark`` package's own module source -- the
identical technique ``tests/contract/work_time_transparency/
test_work_time_transparency_static_conformance.py`` and ``tests/contract/change_executor/
test_change_executor_static_conformance.py`` already establish -- pinning
``PUBLIC_COMPARATIVE_BENCHMARK_ENTRY_POINT_COUNT=6`` and proving (NC-9, NC-11) that this package
can never become a new owner of Canonical State, Authority, Change, Evidence, Reflow, or
Completion: it never calls ``commit_state_transition``, only ``route.py`` ever calls
``commit_coordination_record_at_tip``, and it ships no ``evidence_handoff.py`` and never imports
the Evidence owner."""

from __future__ import annotations

import ast
import inspect
import json
import pathlib
from types import ModuleType

import manosube_agent_civilization
import manosube_agent_civilization.comparative_benchmark as comparative_benchmark_module
import manosube_agent_civilization.comparative_benchmark.engine as engine_module
import manosube_agent_civilization.comparative_benchmark.errors as errors_module
import manosube_agent_civilization.comparative_benchmark.identity as identity_module
import manosube_agent_civilization.comparative_benchmark.route as route_module
import manosube_agent_civilization.comparative_benchmark.types as types_module

_ALL_PACKAGE_MODULES = (route_module, engine_module, identity_module, types_module, errors_module)

_SHIPPED_PACKAGE_ROOT = pathlib.Path(manosube_agent_civilization.__file__).resolve().parent
_COMPARATIVE_BENCHMARK_PACKAGE_ROOT = _SHIPPED_PACKAGE_ROOT / "comparative_benchmark"
_REPO_ROOT = _SHIPPED_PACKAGE_ROOT.parent.parent


def _tree(module: ModuleType) -> ast.Module:
    return ast.parse(inspect.getsource(module))


def _package_files() -> list[pathlib.Path]:
    return sorted(_COMPARATIVE_BENCHMARK_PACKAGE_ROOT.glob("*.py"))


def _top_level_function_names(module: ModuleType) -> set[str]:
    return {
        node.name
        for node in _tree(module).body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }


def _imported_module_names(module: ModuleType) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree(module)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


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


# --- NC-11: cannot mutate existing Canonical owners through an extension surface --------------- #


def test_only_route_py_calls_commit_coordination_record_at_tip_within_this_package() -> None:
    for module in _ALL_PACKAGE_MODULES:
        source = inspect.getsource(module)
        assert "commit_state_transition(" not in source, (
            f"{module.__name__} must not call commit_state_transition -- the benchmark must "
            "never become a new owner of Canonical State/Authority/Change/Evidence-"
            "sufficiency/Completion"
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
                    "commit_coordination_record_at_tip wrapper"
                )


# --- NC-9: MANOSUBE timing/WTT/artifact records cannot become Completion Evidence -------------- #


def test_the_package_ships_no_evidence_handoff_module() -> None:
    shipped_stems = {path.stem for path in _package_files()}
    assert "evidence_handoff" not in shipped_stems


def test_no_module_imports_the_evidence_reflow_or_wtt_owners() -> None:
    forbidden_prefixes = (
        "manosube_agent_civilization.evidence",
        "manosube_agent_civilization.reflow",
        "manosube_agent_civilization.work_time_transparency",
        "manosube_agent_civilization.authority",
        "manosube_agent_civilization.change",
    )
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        offending = {
            name
            for name in imported
            if any(name == f or name.startswith(f + ".") for f in forbidden_prefixes)
        }
        assert not offending, (
            f"{module.__name__} imports {offending} -- this package must never become a second "
            "owner of Authority/Change/Evidence/Reflow, and MANOSUBE's own timing/WTT/artifact "
            "records must never become Completion Evidence"
        )


# --- public surface count / package inventory ---------------------------------------------------#


def test_public_comparative_benchmark_entry_point_count_is_exactly_six() -> None:
    public_route_functions = _top_level_function_names(route_module)
    assert public_route_functions == {
        "commit_protocol_freeze",
        "commit_reproduction_receipt",
        "commit_result_bundle",
        "resolve_protocol_freeze",
        "resolve_reproduction_receipt",
        "resolve_result_bundle",
    }
    assert (
        len(public_route_functions)
        == comparative_benchmark_module.PUBLIC_COMPARATIVE_BENCHMARK_ENTRY_POINT_COUNT
    )


def test_package_init_reexports_exactly_the_public_entry_points() -> None:
    assert set(comparative_benchmark_module.__all__) == {
        "PUBLIC_COMPARATIVE_BENCHMARK_ENTRY_POINT_COUNT",
        "commit_protocol_freeze",
        "commit_reproduction_receipt",
        "commit_result_bundle",
        "resolve_protocol_freeze",
        "resolve_reproduction_receipt",
        "resolve_result_bundle",
    }


def test_no_schema_carries_a_human_authority_ref_or_signature_field() -> None:
    """Structural, not conventional: a comparative-benchmark record must be unable to present
    itself as a Human Authority declaration or Completion Evidence."""

    schema_dir = _REPO_ROOT / "01_SCHEMA" / "comparative_benchmark"
    schema_paths = sorted(schema_dir.glob("*.schema.json"))
    assert len(schema_paths) == 3
    for path in schema_paths:
        schema = json.loads(path.read_text())
        properties = schema.get("properties", {})
        assert "human_authority_ref" not in properties, f"{path.name} carries human_authority_ref"
        assert "signature" not in properties, f"{path.name} carries a signature field"
        assert "evidence_id" not in properties, f"{path.name} carries an evidence_id field"
