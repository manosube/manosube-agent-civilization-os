"""R11-F2 (Phase 7 structural-review round 11): real-source topology detection.

Round 10's own reinforcement (``tests/unit/reflow/test_topology_round10.py``) proved its
content-pattern scans by monkeypatching the *helper functions' own return values* -- a real
source-acquisition or source-pattern gap in the scanner itself would never surface that way.
This file instead feeds the real scanner (``ast.parse``, then the real detector functions)
genuine Python source text, or a genuine module object whose ``inspect.getsource`` genuinely
fails, so every negative control here proves the *real* detection path, never a stand-in for
it (``HELPER_RETURN_MONKEYPATCH_ONLY_SUFFICIENT=false``).
"""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path
import sys
import types

import pytest

from manosube_agent_civilization import topology


@pytest.fixture(autouse=True)
def _clear_topology_cache():
    topology.kernel_topology_inventory.cache_clear()
    yield
    topology.kernel_topology_inventory.cache_clear()


def _trees(module_name: str, source: str) -> list[tuple[str, ast.Module]]:
    return [(module_name, ast.parse(source, filename=module_name))]


# --- 1: Path.write_text() shadow writer, real source ---------------------------------------- #


def test_r11f2_real_source_path_write_text_shadow_writer_is_detected() -> None:
    source = (
        "from pathlib import Path\n"
        "def shadow_writer(path, data):\n"
        "    Path(path).write_text(data)\n"
    )
    trees = _trees("fake.shadow_write_text", source)
    sites = topology._call_sites(
        frozenset({"write_text", "write_bytes", "write"}),
        exclude_modules=topology._SANCTIONED_DIRECT_WRITE_MODULES,
        trees=trees,
    )
    assert sites == ["fake.shadow_write_text:3"]


# --- 2: open(..., "wb").write(...) shadow writer, real source ------------------------------- #


def test_r11f2_real_source_open_write_shadow_writer_is_detected() -> None:
    source = (
        "def shadow_writer(path, data):\n"
        "    with open(path, 'wb') as stream:\n"
        "        stream.write(data)\n"
    )
    trees = _trees("fake.shadow_open_write", source)
    open_sites = topology._open_write_call_sites(
        exclude_modules=topology._SANCTIONED_DIRECT_WRITE_MODULES, trees=trees
    )
    write_sites = topology._call_sites(
        frozenset({"write_text", "write_bytes", "write"}),
        exclude_modules=topology._SANCTIONED_DIRECT_WRITE_MODULES,
        trees=trees,
    )
    assert open_sites == ["fake.shadow_open_write:2"]
    assert write_sites == ["fake.shadow_open_write:3"]


def test_r11f2_a_default_mode_open_call_is_not_flagged_as_a_write() -> None:
    """The positive control: a real, ordinary read-only ``open(path)`` (default mode, no
    write) is never mistaken for a write path."""

    source = "def reader(path):\n    with open(path) as stream:\n        return stream.read()\n"
    trees = _trees("fake.real_reader", source)
    assert (
        topology._open_write_call_sites(
            exclude_modules=topology._SANCTIONED_DIRECT_WRITE_MODULES, trees=trees
        )
        == []
    )


# --- 3: os.replace() shadow atomic writer, real source --------------------------------------- #


def test_r11f2_real_source_os_replace_shadow_atomic_writer_is_detected() -> None:
    source = "import os\ndef shadow_atomic_writer(tmp, dst):\n    os.replace(tmp, dst)\n"
    trees = _trees("fake.shadow_os_replace", source)
    sites = topology._call_sites(
        frozenset({"replace", "rename"}),
        exclude_modules=topology._SANCTIONED_DIRECT_WRITE_MODULES,
        required_receiver="os",
        trees=trees,
    )
    assert sites == ["fake.shadow_os_replace:3"]


def test_r11f2_an_unrelated_string_replace_call_is_never_flagged() -> None:
    """The positive control: ``os.replace`` requires the literal ``os`` receiver --
    ``some_string.replace(...)`` (used throughout this vertical's own real timestamp
    normalization code) must never be mistaken for the filesystem primitive of the same
    name."""

    source = "def normalize(value):\n    return value.replace('Z', '+00:00')\n"
    trees = _trees("fake.real_string_replace_user", source)
    sites = topology._call_sites(
        frozenset({"replace", "rename"}),
        exclude_modules=topology._SANCTIONED_DIRECT_WRITE_MODULES,
        required_receiver="os",
        trees=trees,
    )
    assert sites == []


def test_r11f2_an_unrelated_dict_copy_call_is_never_flagged() -> None:
    """The identical positive control for ``shutil.copy*`` vs. the ubiquitous ``dict.copy``/
    ``list.copy`` idiom."""

    source = "def clone(d):\n    return d.copy()\n"
    trees = _trees("fake.real_dict_copy_user", source)
    sites = topology._call_sites(
        frozenset({"copy", "copyfile", "copy2"}),
        exclude_modules=topology._SANCTIONED_DIRECT_WRITE_MODULES,
        required_receiver="shutil",
        trees=trees,
    )
    assert sites == []


# --- 4: a wrapper-based second Reflow transition commit path, real source -------------------- #


def test_r11f2_real_source_wrapper_commit_bypass_is_detected() -> None:
    source = "def shadow_committer(store, **kwargs):\n    return store.commit(**kwargs)\n"
    trees = _trees("fake.shadow_committer", source)
    sites = topology._call_sites(
        frozenset({"commit"}),
        exclude_modules=topology._SANCTIONED_COMMIT_CALL_MODULES,
        trees=trees,
    )
    assert sites == ["fake.shadow_committer:2"]


# --- 5: a dict-literal closure_evaluation_id producer, real source --------------------------- #


def test_r11f2_real_source_dict_literal_identity_producer_is_detected() -> None:
    source = (
        "def shadow_producer(evaluation):\n"
        "    return {'closure_evaluation_id': mint(evaluation), 'other': 1}\n"
    )
    trees = _trees("fake.dict_literal_producer", source)
    sites = topology._identity_field_assignment_sites("closure_evaluation_id", trees=trees)
    assert sites == ["fake.dict_literal_producer:2"]


def test_r11f2_a_bare_positional_string_argument_naming_the_field_is_never_flagged() -> None:
    """The positive control this vertical's own real code needs: a plain function call
    passing the field's own name as one of several positional arguments (a schema-key
    reference, e.g. ``difference/conformance.py``'s own ``validate_identity_field(
    "closure_evaluation_id", "closure_evaluation.schema.json", DIFFERENCE_BASE)``) is a
    read-only reference, never a production site -- ``AST_PATTERN_NOT_MATCHED_NE_OWNER_
    ABSENT=true`` cuts both ways: a documentation/schema-key mention must not count either."""

    source = (
        "def validate_identity_field(field, schema, base):\n"
        "    pass\n"
        "validate_identity_field('closure_evaluation_id', 'closure_evaluation.schema.json', "
        "'BASE')\n"
    )
    trees = _trees("fake.real_schema_key_reference", source)
    assert topology._identity_field_assignment_sites("closure_evaluation_id", trees=trees) == []


# --- 6: a constructor-keyword authority_decision_id producer, real source -------------------- #


def test_r11f2_real_source_constructor_keyword_identity_producer_is_detected() -> None:
    source = (
        "def shadow_producer(request):\n"
        "    return SomeDecision(authority_decision_id=mint(request))\n"
    )
    trees = _trees("fake.constructor_keyword_producer", source)
    sites = topology._identity_field_assignment_sites("authority_decision_id", trees=trees)
    assert sites == ["fake.constructor_keyword_producer:2"]


# --- 7: import succeeds, inspect.getsource() fails -------------------------------------------- #


def test_r11f2_a_module_whose_source_cannot_be_read_makes_the_scan_propagate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``MODULE_IMPORTED_NE_SOURCE_OBSERVED=true``/``SOURCE_READ_FAILURE_MUST_NOT_BE_
    SILENTLY_EXCLUDED=true``: a real, successfully-imported module whose own
    ``inspect.getsource`` genuinely raises must make the whole content-pattern scan
    propagate -- never be silently skipped as though it had nothing to see."""

    fake = types.ModuleType("manosube_agent_civilization._fake_unreadable_module")
    fake.__file__ = "/nonexistent/path/does/not/exist.py"
    with pytest.raises((OSError, TypeError)):
        inspect.getsource(fake)  # positive control: this really does fail

    with pytest.raises((OSError, TypeError)):
        topology._module_source_trees(modules=[fake])


def test_r11f2_source_read_failure_propagates_through_the_full_static_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = types.ModuleType("manosube_agent_civilization._fake_unreadable_module")
    fake.__file__ = "/nonexistent/path/does/not/exist.py"
    real_iter = topology._iter_installed_modules
    monkeypatch.setattr(topology, "_iter_installed_modules", lambda: [*real_iter(), fake])
    with pytest.raises((OSError, TypeError)):
        topology.k001_single_kernel_entry_point()
    with pytest.raises((OSError, TypeError)):
        topology.k002_single_canonical_state_owner()


# --- 8: import succeeds, source is genuinely unparseable -------------------------------------- #


def test_r11f2_a_module_whose_source_cannot_be_parsed_makes_the_scan_propagate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``AST_PATTERN_NOT_MATCHED_NE_OWNER_ABSENT`` extends to acquisition itself: genuinely
    malformed source (real text, real ``ast.parse``, real ``SyntaxError``) must propagate
    the identical way a read failure does, never be treated as "nothing here"."""

    real_getsource = inspect.getsource
    fake = types.ModuleType("manosube_agent_civilization._fake_unparseable_module")

    def _patched_getsource(obj: object) -> str:
        if obj is fake:
            return "def broken(:\n    this is not valid python\n"
        return real_getsource(obj)

    monkeypatch.setattr(topology.inspect, "getsource", _patched_getsource)
    with pytest.raises(SyntaxError):
        topology._module_source_trees(modules=[fake])


def test_r11f2_source_parse_failure_propagates_through_the_full_static_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_getsource = inspect.getsource
    fake = types.ModuleType("manosube_agent_civilization._fake_unparseable_module")

    def _patched_getsource(obj: object) -> str:
        if obj is fake:
            return "def broken(:\n    this is not valid python\n"
        return real_getsource(obj)

    monkeypatch.setattr(topology.inspect, "getsource", _patched_getsource)
    real_iter = topology._iter_installed_modules
    monkeypatch.setattr(topology, "_iter_installed_modules", lambda: [*real_iter(), fake])
    with pytest.raises(SyntaxError):
        topology.k003_single_authority_and_transition_owner()


# --- end-to-end: a real file, dropped into the real installed package, scanned for real ------ #


def test_r11f2_a_real_file_dropped_into_the_installed_package_fails_k002_end_to_end() -> None:
    """The full, non-injected pipeline: a real ``.py`` file, physically written under the
    real installed package directory, discovered by the real ``pkgutil.walk_packages``,
    imported by the real ``importlib.import_module``, and scanned by the real, unmodified
    :func:`~manosube_agent_civilization.topology.kernel_topology_inventory` -- no ``trees=``
    injection anywhere in this one. Proves the whole assembly, not just its parts."""

    package_root = Path(topology.importlib.import_module(topology._PACKAGE_NAME).__path__[0])
    module_stem = "_r11f2_e2e_shadow_writer_tmp"
    module_path = package_root / f"{module_stem}.py"
    full_module_name = f"{topology._PACKAGE_NAME}.{module_stem}"
    assert not module_path.exists(), "would clobber a real file -- refusing to proceed"

    module_path.write_text(
        "from pathlib import Path\n"
        "def shadow_writer(path, data):\n"
        "    Path(path).write_text(data)\n",
        encoding="utf-8",
    )
    try:
        importlib.invalidate_caches()
        topology.kernel_topology_inventory.cache_clear()
        assert topology.k002_single_canonical_state_owner() is False
        inventory = topology.kernel_topology_inventory()
        assert any(
            site.startswith(f"{full_module_name}:")
            for site in inventory["direct_filesystem_write_sites"]
        )
    finally:
        module_path.unlink()
        sys.modules.pop(full_module_name, None)
        importlib.invalidate_caches()
        topology.kernel_topology_inventory.cache_clear()
        assert topology.k002_single_canonical_state_owner() is True, (
            "cleanup must restore the real installed package to its true, unmodified state"
        )
