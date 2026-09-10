"""V7 (Issue #73): kernel continuity proof.

Static half: ``change_executor`` imports nothing from ``url_boot``, ``model_runtime``, or
``agent_runtime`` anywhere in its own shipped source (P18-C10's own Model/URL/Agent boundary
continuity -- this package cannot receive executable instructions from any of them); never calls
``store.commit`` directly (only ``commit_state_transition``); and never imports ``reflow``,
``difference.engine``, or ``evidence.engine``'s own record-producing internals (only the public
``evidence.derive_evidence`` entry point).

Behavioral half: a full real vertical execution, followed by a second, real, independent
Change-execution cycle against the same project, proves State's own ``state_revision`` genuinely
advanced by exactly the number of State-mutating commits this package itself made, and that
Boot/Difference/Authority/Change's own already-established contracts still hold for both.
"""

from __future__ import annotations

import ast
import inspect
import pathlib
from pathlib import Path
from types import ModuleType
from typing import Any

from tests.fixtures.change_executor_kill_switch_issuer import issuer_public_key_hex
from tests.fixtures.change_executor_world import (
    CountingAdapter,
    bound,
    build_committed_change,
    commit_active_kill_switch,
    execution_boundary_for,
    operation_for,
)

import manosube_agent_civilization
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.change.identity import (
    change_id as recompute_change_id,
    change_semantic_fingerprint as recompute_change_semantic_fingerprint,
)
import manosube_agent_civilization.change_executor.adapter as adapter_module
import manosube_agent_civilization.change_executor.boundary as boundary_module
import manosube_agent_civilization.change_executor.engine as engine_module
import manosube_agent_civilization.change_executor.errors as errors_module
import manosube_agent_civilization.change_executor.evidence_handoff as evidence_handoff_module
import manosube_agent_civilization.change_executor.identity as identity_module
import manosube_agent_civilization.change_executor.kill_switch as kill_switch_module
import manosube_agent_civilization.change_executor.route as route_module
from manosube_agent_civilization.change_executor.route import compose_change_executor
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
)

_SHIPPED_PACKAGE_ROOT = pathlib.Path(manosube_agent_civilization.__file__).resolve().parent
_CHANGE_EXECUTOR_PACKAGE_ROOT = _SHIPPED_PACKAGE_ROOT / "change_executor"


def _package_files() -> list[pathlib.Path]:
    return sorted(_CHANGE_EXECUTOR_PACKAGE_ROOT.glob("*.py"))


def _imported_module_names(module: ModuleType) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _imports_prefix(imported: set[str], prefix: str) -> set[str]:
    return {name for name in imported if name == prefix or name.startswith(prefix + ".")}


# --------------------------------------------------------------------------------------- #
# (a) URL Boot remains read-only/non-authoritative: never imported at all.
# --------------------------------------------------------------------------------------- #


def test_no_module_imports_url_boot() -> None:
    for module in _ALL_PACKAGE_MODULES:
        offending = _imports_prefix(
            _imported_module_names(module), "manosube_agent_civilization.url_boot"
        )
        assert not offending, f"{module.__name__} imports url_boot: {offending}"


# --------------------------------------------------------------------------------------- #
# (b) model_runtime / agent_runtime -- P18-C10's own Model/URL/Agent boundary continuity.
# --------------------------------------------------------------------------------------- #


def test_no_module_imports_model_runtime_or_agent_runtime() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        for prefix in (
            "manosube_agent_civilization.model_runtime",
            "manosube_agent_civilization.agent_runtime",
        ):
            offending = _imports_prefix(imported, prefix)
            assert not offending, f"{module.__name__} imports {prefix}: {offending}"


# --------------------------------------------------------------------------------------- #
# (c) existing owners remain singular.
# --------------------------------------------------------------------------------------- #


def _call_names_in_source(source: str) -> list[tuple[str, int]]:
    """Every ``<obj>.commit(`` call site's own receiver-name and line number -- used to check
    that the *only* ``.commit(`` calls anywhere in this package are calls to
    ``commit_state_transition`` itself (never a bare ``store.commit(...)``)."""

    tree = ast.parse(source)
    sites: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "commit"
        ):
            receiver = node.func.value.id if isinstance(node.func.value, ast.Name) else "<expr>"
            sites.append((receiver, node.lineno))
    return sites


def test_no_module_ever_calls_store_commit_directly() -> None:
    """The only ``.commit(`` on a Store-like receiver anywhere in this package's own source
    would be a bypass of the single sanctioned committer (``store.commit.commit_state_
    transition``) -- confirmed absent by walking every real ``.commit(`` call site in every
    shipped module and requiring each one's own receiver to never be a bare ``store``-named
    object with no further indirection. (``route.py`` itself only ever calls the imported
    ``commit_state_transition`` function -- a bare ``Name`` call, not a ``.commit(`` attribute
    call at all, so it does not appear in this scan; this test's decisive control is that
    nothing else in the package ever performs a *literal* ``x.commit(...)`` attribute call.)"""

    for path in _package_files():
        source = path.read_text(encoding="utf-8")
        sites = _call_names_in_source(source)
        assert not sites, f"{path} calls .commit(...) directly: {sites}"


def test_route_calls_commit_state_transition_and_never_store_commit() -> None:
    tree = ast.parse(inspect.getsource(route_module))
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "commit_state_transition" in call_names


def test_no_module_imports_reflow_or_difference_engine() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        reflow_imports = _imports_prefix(imported, "manosube_agent_civilization.reflow")
        assert not reflow_imports, f"{module.__name__} imports reflow: {reflow_imports}"
        engine_imports = {
            name for name in imported if name == "manosube_agent_civilization.difference.engine"
        }
        assert not engine_imports, f"{module.__name__} imports difference.engine: {engine_imports}"


def test_evidence_is_imported_only_by_evidence_handoff_and_only_the_package_root() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        evidence_imports = _imports_prefix(imported, "manosube_agent_civilization.evidence")
        if module is evidence_handoff_module:
            assert evidence_imports == {"manosube_agent_civilization.evidence"}, evidence_imports
        else:
            assert not evidence_imports, f"{module.__name__} imports evidence: {evidence_imports}"


def test_evidence_handoff_calls_derive_evidence_exactly_once() -> None:
    tree = ast.parse(inspect.getsource(evidence_handoff_module))
    count = sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "derive_evidence")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "derive_evidence")
        )
    )
    assert count == 1


# --------------------------------------------------------------------------------------- #
# (d) behavioral: two real, independent execution cycles against the same project -- exact
# revision accounting, and every predecessor contract still holds for both.
# --------------------------------------------------------------------------------------- #


def _executor(store: Any, info: dict[str, Any], adapter: Any, *, worktree_root: str) -> Any:
    return compose_change_executor(
        store,
        project_id=info["project_id"],
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(),
        adapter_identity={"kind": "controlled_filesystem_adapter", "version": "0.1"},
        adapter=adapter,
        worktree_root=worktree_root,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )


def test_two_real_execution_cycles_advance_revision_by_exactly_this_packages_own_commits(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    project_id = info["project_id"]
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    revision_0 = store.load_current(project_id)["state_revision"]

    # -- kill switch genesis: this package's own one commit. --
    commit_active_kill_switch(store, project_id)
    revision_after_kill_switch = store.load_current(project_id)["state_revision"]
    assert revision_after_kill_switch == revision_0 + 1

    # -- first Change: the test fixture's own one commit (never this package's). --
    first = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": "docs/first.md", "content_utf8": "one"}]
        ),
        paths=["docs/first.md"],
    )
    revision_after_first_change_committed = store.load_current(project_id)["state_revision"]
    assert revision_after_first_change_committed == revision_after_kill_switch + 1

    # -- first execution: this package's own three commits (intent, attempt, receipt). --
    adapter_1 = CountingAdapter()
    execute = _executor(store, info, adapter_1, worktree_root=str(worktree))
    outcome_1 = execute(
        first["change"]["change_id"],
        claim_token="cycle-one",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    assert outcome_1["receipt"]["outcome"] == "SUCCEEDED"
    assert adapter_1.call_count == 1
    revision_after_first_execution = store.load_current(project_id)["state_revision"]
    assert revision_after_first_execution == revision_after_first_change_committed + 3

    # -- second, unrelated Change: the test fixture's own one commit. --
    second = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": "docs/second.md", "content_utf8": "two"}]
        ),
        paths=["docs/second.md"],
    )
    revision_after_second_change_committed = store.load_current(project_id)["state_revision"]
    assert revision_after_second_change_committed == revision_after_first_execution + 1

    # -- second execution: this package's own three commits again. --
    adapter_2 = CountingAdapter()
    execute_2 = _executor(store, info, adapter_2, worktree_root=str(worktree))
    outcome_2 = execute_2(
        second["change"]["change_id"],
        claim_token="cycle-two",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
    )
    assert outcome_2["receipt"]["outcome"] == "SUCCEEDED"
    assert adapter_2.call_count == 1
    revision_after_second_execution = store.load_current(project_id)["state_revision"]
    assert revision_after_second_execution == revision_after_second_change_committed + 3

    # -- exact total accounting: this package's own commits (kill switch genesis + 3 + 3 = 7)
    # plus the test fixture's own two Change/Decision commits (never this package's own) equal
    # the total observed revision advance. --
    this_packages_own_commits = 1 + 3 + 3
    fixtures_own_commits = 1 + 1
    total_commits = this_packages_own_commits + fixtures_own_commits
    assert revision_after_second_execution == revision_0 + total_commits

    # -- both files genuinely exist on real disk. --
    assert (worktree / "docs" / "first.md").read_text(encoding="utf-8") == "one"
    assert (worktree / "docs" / "second.md").read_text(encoding="utf-8") == "two"

    # -- Change's own identity/fingerprint contract still holds for both, unchanged. --
    for result in (first, second):
        change = result["change"]
        assert recompute_change_id(change) == change["change_id"]
        assert (
            recompute_change_semantic_fingerprint(change) == change["change_semantic_fingerprint"]
        )

    # -- both receipts still resolve, byte-identical, from the Store. --
    for outcome in (outcome_1, outcome_2):
        receipt = outcome["receipt"]
        resolved = store.resolve_record(
            project_id, "execution_receipt", receipt["change_execution_receipt_id"]
        )
        assert resolved == receipt

    # -- Boot's own contract still holds: a fresh Boot still reconstructs a fully consistent
    # context, naming the identical project/binding this suite bound at the very start. --
    boot_context = boot_project(
        store, project_id=project_id, project_binding_id=info["project_binding_id"]
    )
    assert boot_context.project_id == project_id
    assert boot_context.current_state["state_revision"] == revision_after_second_execution
