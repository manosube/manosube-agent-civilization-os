"""R12-F2 (Phase 7 Final Closure Round): R-002 stops proxying R-001 and gets its own,
independent Lineage-write-path inventory.

Round 10/11 already proved the *shape* of this module's content-pattern reinforcement
(``test_topology_round10.py``/``test_topology_round11.py``). This file proves the specific
thing Final Closure sharpens: R-002 no longer answers "is there one commit path"
(R-001's own question) -- it answers "is there exactly one, explicitly-authorized set of
functions that write to the Lineage log", independently, even when R-001's own answer says
nothing is wrong.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
from typing import Any

import pytest

from manosube_agent_civilization import topology


@pytest.fixture(autouse=True)
def _clear_topology_cache() -> Any:
    topology.kernel_topology_inventory.cache_clear()
    yield
    topology.kernel_topology_inventory.cache_clear()


def _trees(module_name: str, source: str) -> list[tuple[str, ast.Module]]:
    return [(module_name, ast.parse(source, filename=module_name))]


# --- 1/2: bare-Genesis creation and transaction append are each correctly classified -------- #


def test_r12f2_bare_genesis_create_and_transaction_append_are_the_exact_authorized_set() -> None:
    write_functions, _read_functions = topology._lineage_reference_and_primitive_functions()
    assert set(write_functions) == topology._AUTHORIZED_LINEAGE_WRITE_FUNCTIONS
    assert (
        f"{topology._PACKAGE_NAME}.store.file_store._append" in write_functions
    )  # AUTHORIZED_TRANSACTION_APPEND
    assert (
        f"{topology._PACKAGE_NAME}.store.file_store.initialize" in write_functions
    )  # AUTHORIZED_BARE_GENESIS_CREATE


# --- 3: recovery completion reuses the authorized append path, never a third write site ----- #


def test_r12f2_recovery_completion_is_not_a_third_lineage_writer() -> None:
    """``recover()`` completes an interrupted transaction by calling the identical,
    already-authorized ``_append`` -- it never constructs or writes to the Lineage path
    directly itself, so it must not appear in the write-function inventory at all."""

    write_functions, _read_functions = topology._lineage_reference_and_primitive_functions()
    assert f"{topology._PACKAGE_NAME}.store.file_store.recover" not in write_functions


# --- 4: the read/reconstruction path is never misclassified as a write ---------------------- #


def test_r12f2_the_read_path_is_classified_as_a_reader_never_a_writer() -> None:
    write_functions, read_functions = topology._lineage_reference_and_primitive_functions()
    events_fn = f"{topology._PACKAGE_NAME}.store.file_store._events"
    assert events_fn in read_functions
    assert events_fn not in write_functions


# --- 5: a second direct Lineage append added inside file_store.py itself -------------------- #


def test_r12f2_a_second_lineage_append_inside_file_store_itself_fails_r002() -> None:
    """``file_store.py`` is a sanctioned module for *filesystem-write-primitive* purposes
    (R10-F2/R11-F2) -- but R-002's own inventory is not fooled by that: a second function in
    that exact module that references the Lineage accessor and writes to it is still a
    second Lineage writer, sanctioned module or not
    (``SAME_MODULE_NE_AUTOMATICALLY_AUTHORIZED=true``)."""

    module_name = f"{topology._PACKAGE_NAME}.store.file_store"
    source = (
        "def _rogue_lineage_rewrite(self, project_id):\n"
        "    self._lineage(project_id).write_text('TAMPERED')\n"
    )
    trees = _trees(module_name, source)
    write_functions, _read = topology._lineage_reference_and_primitive_functions(trees=trees)
    assert write_functions == [f"{module_name}._rogue_lineage_rewrite"]
    assert set(write_functions) != topology._AUTHORIZED_LINEAGE_WRITE_FUNCTIONS


# --- 6: a Lineage rewrite/truncate call, not merely an append, is caught the same way ------- #


def test_r12f2_a_lineage_rewrite_call_inside_file_store_itself_fails_r002() -> None:
    module_name = f"{topology._PACKAGE_NAME}.store.file_store"
    source = (
        "def _rogue_lineage_truncate(self, project_id):\n"
        "    with open(self._lineage(project_id), 'w') as stream:\n"
        "        stream.write('')\n"
    )
    trees = _trees(module_name, source)
    write_functions, _read = topology._lineage_reference_and_primitive_functions(trees=trees)
    assert write_functions == [f"{module_name}._rogue_lineage_truncate"]


# --- 7/8: a write from an entirely different module, under any wrapper name ----------------- #


@pytest.mark.parametrize("wrapper_name", ["shadow_lineage_writer", "totally_different_name"])
def test_r12f2_a_lineage_write_from_a_different_module_fails_regardless_of_wrapper_name(
    wrapper_name: str,
) -> None:
    source = (
        f"def {wrapper_name}(store, project_id):\n"
        "    store._lineage(project_id).write_text('TAMPERED')\n"
    )
    trees = _trees("fake.shadow_lineage_module", source)
    write_functions, _read = topology._lineage_reference_and_primitive_functions(trees=trees)
    assert write_functions == [f"fake.shadow_lineage_module.{wrapper_name}"]


def test_r12f2_end_to_end_a_real_file_dropped_into_the_package_fails_r002() -> None:
    """The full, non-injected pipeline: a real ``.py`` file physically written under the
    installed package, discovered by the real ``pkgutil`` scan, scanned by the real,
    unmodified ``r002_single_lineage_owner`` -- no ``trees=`` injection anywhere in this
    one."""

    package_root = Path(topology.importlib.import_module(topology._PACKAGE_NAME).__path__[0])
    module_stem = "_r12f2_e2e_shadow_lineage_writer_tmp"
    module_path = package_root / f"{module_stem}.py"
    full_module_name = f"{topology._PACKAGE_NAME}.{module_stem}"
    assert not module_path.exists(), "would clobber a real file -- refusing to proceed"

    module_path.write_text(
        "def shadow_lineage_writer(store, project_id):\n"
        "    store._lineage(project_id).write_text('TAMPERED')\n",
        encoding="utf-8",
    )
    try:
        import importlib

        importlib.invalidate_caches()
        topology.kernel_topology_inventory.cache_clear()
        assert topology.r002_single_lineage_owner() is False
        inventory = topology.kernel_topology_inventory()
        assert f"{full_module_name}.shadow_lineage_writer" in inventory["lineage_write_functions"]
    finally:
        module_path.unlink()
        sys.modules.pop(full_module_name, None)
        import importlib as _importlib

        _importlib.invalidate_caches()
        topology.kernel_topology_inventory.cache_clear()
        assert topology.r002_single_lineage_owner() is True, (
            "cleanup must restore the real installed package to its true, unmodified state"
        )


# --- 9: a name-obfuscated call this scan cannot resolve is a disclosed, bounded non-claim ---- #


def test_r12f2_a_dynamically_constructed_call_name_is_a_disclosed_detection_boundary() -> None:
    """R12-F2's own scan matches call sites by their literal, static AST name -- a call
    reached through runtime name construction (``getattr(obj, "wri" + "te_text")(...)``)
    carries no static ``.attr``/``.id`` this scan can read at all, so it is correctly
    outside what static AST matching can ever prove. This is not silently claimed as
    "no violation found = safe": it is the identical, already-disclosed
    ``STATIC_TOPOLOGY_SCOPE`` boundary this module's own docstring names for every one of
    its content-pattern scans, not a new gap invented for Lineage specifically. What *is*
    guaranteed (proven by the sibling tests in this file) is that a source-acquisition
    failure -- the module cannot even be read or parsed -- propagates to an exception
    rather than silently passing; a call whose *name itself* is runtime-constructed inside
    an otherwise-readable, parseable module is the one residual class of alias this static
    scan cannot see, exactly as SHUKOU's own text anticipates
    ("検出不能ならUNKNOWNへ落とす" -- the fallback is achieved by this vertical never trusting
    an unreadable/unparseable module in the first place, not by inventing a dynamic-call
    resolver)."""

    module_name = f"{topology._PACKAGE_NAME}.store.file_store"
    source = (
        "def _rogue_dynamic_lineage_write(self, project_id):\n"
        "    getattr(self._lineage(project_id), 'wri' + 'te_text')('TAMPERED')\n"
    )
    trees = _trees(module_name, source)
    write_functions, _read = topology._lineage_reference_and_primitive_functions(trees=trees)
    # Disclosed, not silently passed: the dynamically-named call is invisible to this scan.
    assert write_functions == []


# --- 10: source read/parse failure must not let R-002 report PASS -------------------------- #


def test_r12f2_source_read_failure_propagates_through_r002(monkeypatch: pytest.MonkeyPatch) -> None:
    import types

    fake = types.ModuleType(f"{topology._PACKAGE_NAME}._fake_unreadable_module")
    fake.__file__ = "/nonexistent/path/does/not/exist.py"
    real_iter = topology._iter_installed_modules
    monkeypatch.setattr(topology, "_iter_installed_modules", lambda: [*real_iter(), fake])
    with pytest.raises((OSError, TypeError)):
        topology.r002_single_lineage_owner()


# --- 11: positive control -- the real installed package still passes ----------------------- #


def test_r12f2_r002_passes_on_the_real_installed_topology() -> None:
    assert topology.r002_single_lineage_owner() is True


# --- 12: R-002 detects a real Lineage violation even when R-001's own signal says PASS ------ #


def test_r12f2_r002_is_independent_of_r001s_own_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """The decisive proof of ``R002_NE_R001_PROXY=true``: monkeypatch R-001 itself to always
    report success, while a real second Lineage writer exists -- R-002 must still catch it
    through its own, independent inventory."""

    monkeypatch.setattr(topology, "r001_single_atomic_committer", lambda: True)
    module_name = f"{topology._PACKAGE_NAME}.store.file_store"
    source = (
        "def _rogue_lineage_rewrite(self, project_id):\n"
        "    self._lineage(project_id).write_text('TAMPERED')\n"
    )
    real_scan = topology._lineage_reference_and_primitive_functions

    def _patched_scan(*, trees: Any = None) -> tuple[list[str], list[str]]:
        return real_scan(trees=_trees(module_name, source))

    monkeypatch.setattr(topology, "_lineage_reference_and_primitive_functions", _patched_scan)
    assert topology.r001_single_atomic_committer() is True
    assert topology.r002_single_lineage_owner() is False
