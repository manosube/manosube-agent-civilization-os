"""R13-F1 (SHUKOU post-Final-Closure correction): R-002's Lineage-write-primitive vocabulary
widened to match the general filesystem scan's own create/append/replace/rename/copy
coverage.

R12-F2's own ``_lineage_reference_and_primitive_functions`` recognized only the raw
``atomic_write``/``write_text``/``write_bytes``/bare-``.write()`` primitive names -- never
the write-mode-``open``/``os.replace``/``os.rename``/``shutil.copy*`` shapes
``_direct_filesystem_write_sites`` (the *general* filesystem scan, R11-F2) already
recognizes. A rogue Lineage rewrite expressed through any of those forms was invisible to
R-002 even though the identical primitive shape already fails the general scan for an
unsanctioned module. This file proves the widened scan catches every one of those forms,
inside and outside the one sanctioned module, independently of R-001's own result, while
the real installed package still passes and a source-acquisition failure still falls to the
identical, pre-existing ``UNKNOWN`` path rather than a silent PASS.
"""

from __future__ import annotations

import ast
import types
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


_SANCTIONED_MODULE = f"{topology._PACKAGE_NAME}.store.file_store"
_OTHER_MODULE = "fake.shadow_lineage_module"


def _assert_r002_fails_on(module_name: str, source: str) -> None:
    trees = _trees(module_name, source)
    write_functions, _read = topology._lineage_reference_and_primitive_functions(trees=trees)
    assert write_functions == [f"{module_name}._rogue"]
    real_scan = topology._lineage_reference_and_primitive_functions

    def _patched_scan(*, trees: Any = None) -> tuple[list[str], list[str]]:
        return real_scan(trees=_trees(module_name, source))

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(topology, "_lineage_reference_and_primitive_functions", _patched_scan)
        assert topology.r002_single_lineage_owner() is False


# --- 1: os.replace onto the Lineage path fails R-002 ----------------------------------------- #


def test_r13f1_an_os_replace_rewrite_of_the_lineage_path_fails_r002() -> None:
    source = (
        "def _rogue(self, project_id):\n"
        "    import os\n"
        "    os.replace(source, self._lineage(project_id))\n"
    )
    _assert_r002_fails_on(_OTHER_MODULE, source)


# --- 2: os.rename onto the Lineage path fails R-002 ------------------------------------------ #


def test_r13f1_an_os_rename_rewrite_of_the_lineage_path_fails_r002() -> None:
    source = (
        "def _rogue(self, project_id):\n"
        "    import os\n"
        "    os.rename(source, self._lineage(project_id))\n"
    )
    _assert_r002_fails_on(_OTHER_MODULE, source)


# --- 3: shutil.copy2 onto the Lineage path fails R-002 --------------------------------------- #


def test_r13f1_a_shutil_copy2_rewrite_of_the_lineage_path_fails_r002() -> None:
    source = (
        "def _rogue(self, project_id):\n"
        "    import shutil\n"
        "    shutil.copy2(source, self._lineage(project_id))\n"
    )
    _assert_r002_fails_on(_OTHER_MODULE, source)


# --- 4: a write-mode open() rewrite of the Lineage path fails R-002 -------------------------- #


def test_r13f1_a_write_mode_open_rewrite_of_the_lineage_path_fails_r002() -> None:
    source = (
        "def _rogue(self, project_id):\n"
        "    with open(self._lineage(project_id), 'w') as stream:\n"
        "        stream.write('TAMPERED')\n"
    )
    _assert_r002_fails_on(_OTHER_MODULE, source)


# --- 5: the identical shapes still fail even added inside the sanctioned module -------------- #


@pytest.mark.parametrize(
    "source",
    [
        "def _rogue(self, project_id):\n    import os\n    os.replace(source, self._lineage(project_id))\n",
        "def _rogue(self, project_id):\n    import os\n    os.rename(source, self._lineage(project_id))\n",
        (
            "def _rogue(self, project_id):\n"
            "    import shutil\n"
            "    shutil.copy2(source, self._lineage(project_id))\n"
        ),
        (
            "def _rogue(self, project_id):\n"
            "    with open(self._lineage(project_id), 'w') as stream:\n"
            "        stream.write('TAMPERED')\n"
        ),
    ],
)
def test_r13f1_the_same_shapes_still_fail_r002_inside_the_sanctioned_module(source: str) -> None:
    """``SANCTIONED_MODULE_MEMBERSHIP_NE_WRITE_AUTHORIZATION=true``: ``file_store.py`` is
    the one sanctioned module for filesystem-write-primitive purposes generally, but R-002's
    own inventory is not fooled by that -- a rogue rewrite added directly inside it is still
    a second Lineage writer."""

    _assert_r002_fails_on(_SANCTIONED_MODULE, source)


# --- 6: R-002 is independent of R-001's own result, for every widened primitive shape -------- #


@pytest.mark.parametrize(
    "source",
    [
        "def _rogue(self, project_id):\n    import os\n    os.replace(source, self._lineage(project_id))\n",
        (
            "def _rogue(self, project_id):\n"
            "    with open(self._lineage(project_id), 'w') as stream:\n"
            "        stream.write('TAMPERED')\n"
        ),
    ],
)
def test_r13f1_r002_is_independent_of_r001s_own_result_for_the_widened_shapes(
    source: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(topology, "r001_single_atomic_committer", lambda: True)
    real_scan = topology._lineage_reference_and_primitive_functions

    def _patched_scan(*, trees: Any = None) -> tuple[list[str], list[str]]:
        return real_scan(trees=_trees(_SANCTIONED_MODULE, source))

    monkeypatch.setattr(topology, "_lineage_reference_and_primitive_functions", _patched_scan)
    assert topology.r001_single_atomic_committer() is True
    assert topology.r002_single_lineage_owner() is False


# --- 7: positive control -- the real installed package still passes ------------------------- #


def test_r13f1_r002_still_passes_on_the_real_installed_topology() -> None:
    assert topology.r002_single_lineage_owner() is True
    write_functions, read_functions = topology._lineage_reference_and_primitive_functions()
    assert set(write_functions) == topology._AUTHORIZED_LINEAGE_WRITE_FUNCTIONS
    assert f"{topology._PACKAGE_NAME}.store.file_store._events" in read_functions


# --- 8: source acquisition/parse failure still falls to UNKNOWN, never a silent PASS --------- #


def test_r13f1_source_read_failure_still_propagates_rather_than_passing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = types.ModuleType(f"{topology._PACKAGE_NAME}._fake_unreadable_module_r13")
    fake.__file__ = "/nonexistent/path/does/not/exist.py"
    real_iter = topology._iter_installed_modules
    monkeypatch.setattr(topology, "_iter_installed_modules", lambda: [*real_iter(), fake])
    with pytest.raises((OSError, TypeError)):
        topology.r002_single_lineage_owner()


# --- disclosed, bounded detection boundary: a dynamically-constructed call name -------------- #


def test_r13f1_a_dynamically_constructed_replace_call_name_is_the_same_disclosed_boundary() -> None:
    """``DYNAMICALLY_CONSTRUCTED_CALL_NAME_STATIC_PROOF_REQUIRED=false``: a call reached
    through a runtime-constructed name (e.g. ``getattr(os, "repl" + "ace")(...)``) carries no
    static ``.attr``/``.id`` this AST scan can read, so it remains outside what this widened
    scan -- or any of this module's other content-pattern scans -- can prove. This is the
    identical, already-disclosed boundary named in ``test_topology_round12.py``'s own
    equivalent test, not a new gap R13-F1 introduces."""

    source = (
        "def _rogue(self, project_id):\n"
        "    import os\n"
        "    getattr(os, 'repl' + 'ace')(source, self._lineage(project_id))\n"
    )
    trees = _trees(_OTHER_MODULE, source)
    write_functions, _read = topology._lineage_reference_and_primitive_functions(trees=trees)
    assert write_functions == []
