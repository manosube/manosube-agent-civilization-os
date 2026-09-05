"""R10-F2 (Phase 7 structural-review round 10): name-independent reinforcement of
``manosube_agent_civilization.topology``'s Static K-001/K-002/K-003/R-001/R-002 checks.

Round 9's own topology inventory (``tests/unit/reflow/test_structural_review_correction.py``'s
``test_r9f1_k001_k002_k003_pass_on_the_real_installed_topology`` and
``test_r9f1_k001_reports_unknown_when_the_topology_inventory_cannot_be_computed``) already
proved the *shape* of this check -- a real positive control and a real
``UNPROVEN_INVARIANT_MUST_BE_UNKNOWN=true`` control. This file proves the two things Round 10
sharpened: that a real import failure anywhere in the installed package propagates instead of
being silently excluded (``IMPORT_FAILURE_MUST_NOT_BE_SILENTLY_EXCLUDED=true``), and that a
second canonical owner reached only through a differently-named function/class, a wrapper
call, or a direct write call site is still caught -- proving
``EXPECTED_SYMBOL_NAME_COUNT_NE_CANONICAL_OWNER_COUNT=true`` is not merely asserted but real:
every scenario below leaves every *name*-based count at its real, singular value and fails
the check purely through the new content-pattern signal.
"""

from __future__ import annotations

from typing import Any

import pytest

from manosube_agent_civilization import topology


@pytest.fixture(autouse=True)
def _clear_topology_cache() -> Any:
    """``kernel_topology_inventory`` is ``@lru_cache(maxsize=1)`` -- every test in this file
    monkeypatches one of its own inputs, so the cache must not carry a result computed under
    a previous test's patched world (or leak this test's patched result into the next)."""

    topology.kernel_topology_inventory.cache_clear()
    yield
    topology.kernel_topology_inventory.cache_clear()


# --- import failures must propagate, never be silently excluded ---------------------------- #


def test_r10f2_an_import_failure_anywhere_in_the_tree_propagates_out_of_iter_installed_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact Round 9 bug: ``_iter_installed_modules`` used to wrap each import in
    ``contextlib.suppress(Exception)``, silently excluding a module that fails to import
    rather than making the whole scan indeterminate. This module no longer does."""

    real_import_module = topology.importlib.import_module

    def _flaky_import(name: str) -> Any:
        if name == f"{topology._PACKAGE_NAME}.reflow.route":
            raise ImportError("simulated broken module")
        return real_import_module(name)

    monkeypatch.setattr(topology.importlib, "import_module", _flaky_import)
    with pytest.raises(ImportError, match="simulated broken module"):
        topology._iter_installed_modules()


@pytest.mark.parametrize(
    "check",
    [
        topology.k001_single_kernel_entry_point,
        topology.k002_single_canonical_state_owner,
        topology.k003_single_authority_and_transition_owner,
        topology.r001_single_atomic_committer,
        topology.r002_single_lineage_owner,
    ],
)
def test_r10f2_every_static_check_propagates_a_real_import_failure(
    check: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every one of K-001/K-002/K-003/R-001/R-002's Static half now shares the identical
    failure mode: a real import failure anywhere in the tree propagates out of the public
    check itself (never silently narrows the scan and reports a result anyway). Each
    invariant verifier's own ``try/except Exception: return "UNKNOWN"`` (unchanged since
    R9-F1) is what turns this into the honest ``UNKNOWN`` a caller actually sees."""

    real_import_module = topology.importlib.import_module

    def _flaky_import(name: str) -> Any:
        if name == f"{topology._PACKAGE_NAME}.reflow.route":
            raise ImportError("simulated broken module")
        return real_import_module(name)

    monkeypatch.setattr(topology.importlib, "import_module", _flaky_import)
    with pytest.raises(ImportError):
        check()


# --- a second, differently-named owner reached only through content is still caught -------- #


def test_r10f2_a_second_closure_evaluation_identity_site_fails_k001_even_though_every_name_based_count_stays_singular(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``EXPECTED_SYMBOL_NAME_COUNT_NE_CANONICAL_OWNER_COUNT=true``: a second
    ``X["closure_evaluation_id"] = ...`` assignment site anywhere in the tree -- e.g. a
    second gate engine literally named ``run_closure_gates`` that Round 9's own
    ``_functions_named("evaluate_closure")`` name-based scan would never see -- fails K-001,
    even with ``closure_producers``/``kernel_entry_points`` both still real and singular."""

    real_sites = topology._identity_field_assignment_sites

    def _two_sites(field_name: str) -> list[str]:
        if field_name == "closure_evaluation_id":
            return ["manosube_agent_civilization.reflow.closure:1", "fake.module:1"]
        return real_sites(field_name)

    monkeypatch.setattr(topology, "_identity_field_assignment_sites", _two_sites)
    assert len(topology._functions_named("evaluate_closure")) == 1  # unaffected, still singular
    assert topology.k001_single_kernel_entry_point() is False


def test_r10f2_a_second_authority_decision_identity_site_fails_k003_even_though_every_name_based_count_stays_singular(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The identical proof for K-003's own Authority-Decision-producer role."""

    real_sites = topology._identity_field_assignment_sites

    def _two_sites(field_name: str) -> list[str]:
        if field_name == "authority_decision_id":
            return ["manosube_agent_civilization.authority.engine:1", "fake.module:1"]
        return real_sites(field_name)

    monkeypatch.setattr(topology, "_identity_field_assignment_sites", _two_sites)
    assert len(topology._functions_named("evaluate_authority")) == 1  # unaffected
    assert topology.k003_single_authority_and_transition_owner() is False


def test_r10f2_a_direct_filesystem_write_call_site_outside_the_store_fails_k002_even_though_the_state_store_class_count_stays_singular(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``DIRECT_FILESYSTEM_WRITE_PATH``: a stray ``atomic_write(...)`` call in some other
    module -- a second, unsanctioned write path into the on-disk Store that never touches
    ``FileStateStore`` at all -- fails K-002 even with ``state_stores`` still real and
    singular (Round 9's own class-method-name scan would never see it)."""

    real_call_sites = topology._call_sites

    def _stray_write_site(call_name: str, *, exclude_modules: frozenset[str]) -> list[str]:
        if call_name == "atomic_write":
            return ["fake.shadow_writer:1"]
        return real_call_sites(call_name, exclude_modules=exclude_modules)

    monkeypatch.setattr(topology, "_call_sites", _stray_write_site)
    assert (
        len(
            topology._classes_with_methods(
                "commit", "load_current", "reconstruct", "resolve_record"
            )
        )
        == 1
    )  # unaffected, still singular
    assert topology.k002_single_canonical_state_owner() is False


def test_r10f2_a_wrapper_commit_call_site_fails_k003_and_r001_and_r002_even_though_commit_reflow_stays_singular(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``REFLOW_TRANSITION_COMMITTER``: some other module's own wrapper calling
    ``store.commit(...)`` directly (never named or shaped like ``commit_reflow``) is a
    second transition-commit path -- caught here regardless of what that wrapper function is
    called, unlike Round 9's own name-based ``_functions_named("commit_reflow")`` scan."""

    real_call_sites = topology._call_sites

    def _stray_commit_site(call_name: str, *, exclude_modules: frozenset[str]) -> list[str]:
        if call_name == "commit":
            return ["fake.shadow_committer:1"]
        return real_call_sites(call_name, exclude_modules=exclude_modules)

    monkeypatch.setattr(topology, "_call_sites", _stray_commit_site)
    assert len(topology._functions_named("commit_reflow")) == 1  # unaffected, still singular
    assert topology.k003_single_authority_and_transition_owner() is False
    assert topology.r001_single_atomic_committer() is False
    assert topology.r002_single_lineage_owner() is False


def test_r10f2_a_second_kernel_entry_point_function_fails_k001_even_though_evaluate_closure_stays_singular(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``EVALUATE_CLOSURE_NE_WHOLE_KERNEL_ENTRYPOINT=true``, proven both ways: a second
    function literally named ``reflow`` (the real composed Kernel entry point role, distinct
    from ``evaluate_closure``) fails K-001 even with the Closure-Evaluation-producer count
    itself still real and singular."""

    real_functions_named = topology._functions_named

    def _two_entry_points(name: str) -> list[str]:
        if name == "reflow":
            return ["manosube_agent_civilization.reflow.route.reflow", "fake.module.reflow"]
        return real_functions_named(name)

    monkeypatch.setattr(topology, "_functions_named", _two_entry_points)
    assert len(topology._functions_named("evaluate_closure")) == 1  # unaffected, still singular
    assert topology.k001_single_kernel_entry_point() is False


# --- positive control: none of the above reinforcement narrows the real installed package -- #


def test_r10f2_every_static_check_still_passes_on_the_real_installed_topology() -> None:
    """The positive control every negative control above needs: this vertical's own real,
    unmodified installed package still passes every Static check unchanged -- R10-F2 is a
    real reinforcement, not a stricter check that never PASSes."""

    assert topology.k001_single_kernel_entry_point() is True
    assert topology.k002_single_canonical_state_owner() is True
    assert topology.k003_single_authority_and_transition_owner() is True
    assert topology.r001_single_atomic_committer() is True
    assert topology.r002_single_lineage_owner() is True
    inventory = topology.kernel_topology_inventory()
    assert inventory["direct_filesystem_write_sites"] == []
    assert inventory["reflow_transition_commit_sites"] == []
    assert len(inventory["kernel_entry_points"]) == 1
    assert len(inventory["closure_evaluation_identity_sites"]) == 1
    assert len(inventory["authority_decision_identity_sites"]) == 1
