"""Phase 10 (Issue #45) Boot: the one public route (``boot_project``), end-to-end, over a
real ``FileStateStore``, plus a targeted cross-record consistency matrix over a minimal
in-memory stand-in store for the handful of invariants a real, honestly-operating Store and
Product Binding pairing can never itself produce (each such state is already foreclosed by
Store's or Binding's own existing fail-closed guarantees at genesis-commit time -- these
cases prove ``boot_project``'s own defense-in-depth code independently, the identical
direct-tampered-dict technique ``tests/integration/binding/test_project_binding_route.py::
test_resolve_binding_references_rejects_a_wrong_kind_reference_before_store_lookup`` already
uses for the same reason).

Proves the canonical successful route (``BOOT_CONTRACT.md`` §5), the required negative and
interruption proofs (§6), and that no rejection ever mutates canonical Binding, State,
Lineage, record, or transaction-manifest visibility.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Any

import pytest
from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import rule_id as _rule_id
from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.binding.errors import BindingIdentityError, BindingValidationError
from manosube_agent_civilization.binding.identity import project_binding_id as _project_binding_id
from manosube_agent_civilization.boot import (
    BootConsistencyError,
    BootContext,
    BootNotFoundError,
    boot_project,
)
from manosube_agent_civilization.store import STAGES, FileStateStore
from manosube_agent_civilization.store.errors import (
    CorruptStoreError,
    SimulatedCrash,
    StateNotFoundError,
)


def _kwargs() -> dict[str, Any]:
    return bind_project_kwargs()


def _bound(tmp_path: Path) -> tuple[FileStateStore, dict[str, Any], dict[str, Any]]:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store, kwargs, result


def _unfreeze(value: Any) -> Any:
    """Recursively convert a ``BootContext`` field's own frozen shape (``MappingProxyType``
    over ``dict``, ``tuple`` in place of ``list``) back into plain ``dict``/``list`` for
    equality comparison against a JSON-shaped body -- P10-R1-F1's own deep-freeze
    (:func:`~manosube_agent_civilization.boot.context._deep_freeze`) intentionally changes
    every nested container's own type, so a bare ``dict(...)``/``==`` comparison against the
    original plain body no longer applies at any depth beyond the outermost mapping."""

    if isinstance(value, dict):
        return {key: _unfreeze(item) for key, item in value.items()}
    if hasattr(value, "items"):  # MappingProxyType and other Mapping implementations
        return {key: _unfreeze(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_unfreeze(item) for item in value]
    return value


def _snapshot(store: FileStateStore, project_id: str) -> dict[str, str]:
    """A content-hash snapshot of every file under *project_id*'s own Store directory --
    proves ``RECORD_COUNT_DELTA=0``/``LINEAGE_APPEND_COUNT_DELTA=0``/
    ``TRANSACTION_MANIFEST_COUNT_DELTA=0``/``STATE_TRANSITION_COUNT_DELTA=0`` together, since
    any one of those changes the bytes of at least one file this walk covers."""

    project_dir = store.root / "projects" / project_id
    if not project_dir.is_dir():
        return {}
    return {
        str(path.relative_to(project_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(project_dir.rglob("*"))
        if path.is_file()
    }


class _FakeStore:
    """Minimal in-memory stand-in for the two public read surfaces ``boot_project`` calls."""

    def __init__(
        self,
        records: dict[tuple[str, str, str], dict[str, Any]],
        current_state: dict[str, Any] | BaseException,
    ) -> None:
        self._records = records
        self._current_state = current_state

    def resolve_record(self, project_id: str, kind: str, record_id: str) -> dict[str, Any] | None:
        return self._records.get((project_id, kind, record_id))

    def read_current_consistent(self, project_id: str) -> dict[str, Any]:
        if isinstance(self._current_state, BaseException):
            raise self._current_state
        return self._current_state


def _real_graph(tmp_path: Path) -> dict[str, Any]:
    """One real, mutually-consistent Binding/Objective/Authority/State graph, produced by a
    real ``bind_project`` call over a throwaway Store -- never hand-assembled here, so every
    FakeStore-based test below tampers a genuinely real, previously-valid graph, not a
    fixture invented for this test file."""

    _store, kwargs, result = _bound(tmp_path)
    return {
        "project_id": kwargs["project_id"],
        "project_binding": deepcopy(result["project_binding"]),
        "objective_revision": deepcopy(result["objective_revision"]),
        "authority_rule": deepcopy(result["authority_rule"]),
        "current_state": deepcopy(result["committed_state"]),
    }


def _fake_store_for(
    graph: dict[str, Any],
    *,
    project_binding: dict[str, Any] | None = None,
    objective_revision: dict[str, Any] | None = None,
    authority_rule: dict[str, Any] | None = None,
    current_state: Any = None,
    include_objective: bool = True,
    include_authority: bool = True,
) -> _FakeStore:
    pid = graph["project_id"]
    pb = project_binding if project_binding is not None else graph["project_binding"]
    orev = objective_revision if objective_revision is not None else graph["objective_revision"]
    arule = authority_rule if authority_rule is not None else graph["authority_rule"]
    records: dict[tuple[str, str, str], dict[str, Any]] = {
        (pid, "project_binding", pb["project_binding_id"]): pb,
    }
    if include_objective:
        records[(pid, "objective_revision", orev["objective_revision_id"])] = orev
    if include_authority:
        records[(pid, "authority_rule", arule["authority_rule_id"])] = arule
    return _FakeStore(
        records, current_state if current_state is not None else graph["current_state"]
    )


# --- canonical successful route --------------------------------------------------------- #


def test_boot_project_restores_the_real_bound_project(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    ctx = boot_project(
        store, project_id=kwargs["project_id"], project_binding_id=result["project_binding_id"]
    )
    assert isinstance(ctx, BootContext)
    assert ctx.project_id == kwargs["project_id"]
    assert ctx.project_binding_id == result["project_binding_id"]
    assert _unfreeze(ctx.project_binding) == result["project_binding"]
    assert _unfreeze(ctx.objective_revision) == result["objective_revision"]
    assert _unfreeze(ctx.authority_rule) == result["authority_rule"]
    assert _unfreeze(ctx.current_state) == result["committed_state"]
    assert ctx.authority_rule_id == result["authority_rule"]["authority_rule_id"]
    assert ctx.objective_revision_id == result["objective_revision"]["objective_revision_id"]
    assert _unfreeze(ctx.human_authority_ref) == result["project_binding"]["human_authority_ref"]


def test_boot_context_mapping_fields_are_immutable(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    ctx = boot_project(
        store, project_id=kwargs["project_id"], project_binding_id=result["project_binding_id"]
    )
    for mapping in (
        ctx.project_binding,
        ctx.objective_revision,
        ctx.authority_rule,
        ctx.current_state,
        ctx.human_authority_ref,
    ):
        with pytest.raises(TypeError):
            mapping["tampered"] = True  # type: ignore[index]
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        ctx.project_id = "OTHER"  # type: ignore[misc]


# --- P10-R1-F1: BootContext immutability covers the full accepted graph, not merely each
#     field's own outer mapping ---------------------------------------------------------- #


def test_nested_mapping_mutation_is_rejected(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    before = _snapshot(store, project_id)
    ctx = boot_project(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )
    with pytest.raises(TypeError):
        ctx.project_binding["command_policy"]["max_commands_per_change"] = 999
    assert _snapshot(store, project_id) == before


def test_deeply_nested_mapping_mutation_is_rejected(tmp_path: Path) -> None:
    """At least two levels deep -- ``state_metadata`` inside ``current_state``."""

    store, kwargs, result = _bound(tmp_path)
    ctx = boot_project(
        store, project_id=kwargs["project_id"], project_binding_id=result["project_binding_id"]
    )
    with pytest.raises(TypeError):
        ctx.current_state["state_metadata"]["producer"] = "tampered"


def test_nested_sequence_mutation_is_rejected(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    ctx = boot_project(
        store, project_id=kwargs["project_id"], project_binding_id=result["project_binding_id"]
    )
    assert isinstance(ctx.project_binding["boundary"]["root_paths"], tuple)
    with pytest.raises(AttributeError):
        ctx.project_binding["boundary"]["root_paths"].append("injected")  # type: ignore[attr-defined]
    with pytest.raises(TypeError):
        ctx.project_binding["boundary"]["root_paths"][0] = "injected"  # type: ignore[index]


def test_nested_mapping_inside_a_sequence_is_also_immutable(tmp_path: Path) -> None:
    """``source_registrations`` is a list of objects on the real schema -- each element must
    itself be frozen, not merely the outer list-turned-tuple."""

    store, kwargs, result = _bound(tmp_path)
    ctx = boot_project(
        store, project_id=kwargs["project_id"], project_binding_id=result["project_binding_id"]
    )
    registrations = ctx.project_binding["source_registrations"]
    assert isinstance(registrations, tuple) and len(registrations) >= 1
    with pytest.raises(TypeError):
        registrations[0]["locator"] = "injected"


def test_mutating_the_original_resolved_body_after_boot_never_affects_the_context(
    tmp_path: Path,
) -> None:
    store, kwargs, result = _bound(tmp_path)
    ctx = boot_project(
        store, project_id=kwargs["project_id"], project_binding_id=result["project_binding_id"]
    )
    original_before = ctx.project_binding["command_policy"]["max_commands_per_change"]

    # A fresh, independent resolve of the same committed record, then mutate that copy --
    # BootContext must not alias it.
    separately_resolved = store.resolve_record(
        kwargs["project_id"], "project_binding", result["project_binding_id"]
    )
    assert separately_resolved is not None
    separately_resolved["command_policy"]["max_commands_per_change"] = 424242

    assert ctx.project_binding["command_policy"]["max_commands_per_change"] == original_before


def test_mutating_the_callers_own_kwargs_before_boot_never_leaks_into_the_context(
    tmp_path: Path,
) -> None:
    """Defensive full-projection construction: even the exact dict objects the Store itself
    returned to ``boot_project`` must not be shared with the returned ``BootContext`` -- a
    caller that later mutates its own reference to what it thinks is "the same" body must
    never retroactively alter an already-returned context."""

    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    binding_id = result["project_binding_id"]

    real_resolve_record = store.resolve_record
    captured: dict[str, Any] = {}

    def _capturing_resolve_record(pid: str, kind: str, rid: str) -> dict[str, Any] | None:
        body = real_resolve_record(pid, kind, rid)
        if kind == "project_binding" and body is not None:
            captured["project_binding"] = body
        return body

    store_any: Any = store
    store_any.resolve_record = _capturing_resolve_record
    try:
        ctx = boot_project(store_any, project_id=project_id, project_binding_id=binding_id)
    finally:
        del store_any.resolve_record  # restore the bound method

    assert "project_binding" in captured
    captured["project_binding"]["command_policy"]["max_commands_per_change"] = 999999
    assert ctx.project_binding["command_policy"]["max_commands_per_change"] != 999999


def test_fresh_file_state_store_boots_the_identical_context(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    fresh = FileStateStore(store.root, schema_root=SCHEMA_ROOT)
    ctx = boot_project(
        fresh, project_id=kwargs["project_id"], project_binding_id=result["project_binding_id"]
    )
    assert _unfreeze(ctx.current_state) == result["committed_state"]
    assert _unfreeze(ctx.project_binding) == result["project_binding"]


def test_a_fresh_python_process_boots_successfully(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    store_root = str(store.root)
    project_id = kwargs["project_id"]
    binding_id = result["project_binding_id"]

    script = textwrap.dedent(
        f"""
        import json, pathlib, sys
        sys.path.insert(0, {str(Path.cwd())!r})
        from manosube_agent_civilization.boot import boot_project
        from manosube_agent_civilization.store import FileStateStore
        from tests.state_helpers import SCHEMA_ROOT
        store = FileStateStore(pathlib.Path({store_root!r}), schema_root=SCHEMA_ROOT)
        ctx = boot_project(store, project_id={project_id!r}, project_binding_id={binding_id!r})
        print(json.dumps({{
            "project_id": ctx.project_id,
            "project_binding_id": ctx.project_binding_id,
            "state_revision": ctx.current_state["state_revision"],
        }}))
        """
    )
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(Path.cwd()),
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["project_id"] == project_id
    assert payload["project_binding_id"] == binding_id
    assert payload["state_revision"] == 0


def test_repeated_boot_is_deterministic_and_mutation_free(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    before = _snapshot(store, project_id)

    first = boot_project(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )
    second = boot_project(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )

    assert dict(first.project_binding) == dict(second.project_binding)
    assert dict(first.objective_revision) == dict(second.objective_revision)
    assert dict(first.authority_rule) == dict(second.authority_rule)
    assert dict(first.current_state) == dict(second.current_state)
    assert _snapshot(store, project_id) == before


# --- missing project / missing binding ---------------------------------------------------- #


def test_missing_project_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    with pytest.raises(BootNotFoundError):
        boot_project(
            store, project_id="PRJ-NEVER-BOUND-0001", project_binding_id="PROJBIND-" + "0" * 64
        )


def test_missing_product_binding_is_rejected(tmp_path: Path) -> None:
    store, kwargs, _result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    before = _snapshot(store, project_id)
    with pytest.raises(BootNotFoundError):
        boot_project(store, project_id=project_id, project_binding_id="PROJBIND-" + "9" * 64)
    assert _snapshot(store, project_id) == before


def test_a_binding_from_another_project_never_resolves_under_a_different_project_id(
    tmp_path: Path,
) -> None:
    """Store records are scoped per-project directory -- requesting project A's real
    Project Binding under project B's own identity never resolves, whatever the reason a
    caller supplies the wrong project_id for (frozen semantic decision 2: project_id is
    never a locator to search across)."""

    store_a, _kwargs_a, result_a = _bound(tmp_path)
    other_kwargs = _kwargs()
    other_kwargs["project_id"] = "PRJ-BIND-OTHER-BOOT-0001"
    other_kwargs["objective_revision"]["project_id"] = other_kwargs["project_id"]
    other_kwargs["authority_rule"]["project_id"] = other_kwargs["project_id"]
    other_kwargs["authority_rule"]["authority_rule_id"] = _rule_id(
        {k: v for k, v in other_kwargs["authority_rule"].items() if k != "authority_rule_id"}
    )
    other_kwargs["authority_policy_ref"] = {
        "kind": "authority_rule",
        "id": other_kwargs["authority_rule"]["authority_rule_id"],
    }
    other_kwargs["genesis_state"]["project_id"] = other_kwargs["project_id"]
    other_records = genesis_records()
    for index, (kind, record_id, body) in enumerate(other_records):
        other_records[index] = (kind, record_id, body)
    bind_project(
        store_a, **other_kwargs, additional_genesis_records=other_records, schema_root=SCHEMA_ROOT
    )

    before = _snapshot(store_a, other_kwargs["project_id"])
    with pytest.raises(BootNotFoundError):
        boot_project(
            store_a,
            project_id=other_kwargs["project_id"],
            project_binding_id=result_a["project_binding_id"],
        )
    assert _snapshot(store_a, other_kwargs["project_id"]) == before


@pytest.mark.parametrize(
    "bad_value",
    ["/home/user/project", "https://github.com/example/repo", "../escape", "a/b"],
)
def test_project_id_locator_shaped_substitution_is_rejected(bad_value: str, tmp_path: Path) -> None:
    store, _, result = _bound(tmp_path)
    with pytest.raises(BootNotFoundError):
        boot_project(store, project_id=bad_value, project_binding_id=result["project_binding_id"])


@pytest.mark.parametrize(
    "bad_value",
    ["/etc/passwd", "https://example.com/x", "../escape", "a/b"],
)
def test_project_binding_id_locator_shaped_substitution_is_rejected(
    bad_value: str, tmp_path: Path
) -> None:
    store, kwargs, _result = _bound(tmp_path)
    with pytest.raises(BootNotFoundError):
        boot_project(store, project_id=kwargs["project_id"], project_binding_id=bad_value)


# --- an uninitialized Store / an interrupted transaction ---------------------------------- #


def test_a_project_with_only_an_interrupted_genesis_is_rejected(tmp_path: Path) -> None:
    """A crash before ``AFTER_COMMIT_INTENT`` leaves nothing committed at all -- Boot must
    never silently treat this as a fresh, bootable-from-nothing project."""

    def fault(current: str, _stage: str = "AFTER_STAGED_RECORDS_WRITTEN") -> None:
        if current == _stage:
            raise SimulatedCrash(_stage)

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    with pytest.raises(SimulatedCrash):
        bind_project(
            store,
            **kwargs,
            additional_genesis_records=genesis_records(),
            schema_root=SCHEMA_ROOT,
            fault=fault,
        )
    from manosube_agent_civilization.binding.engine import assemble_project_binding

    would_be_binding_id = assemble_project_binding(
        project_id=kwargs["project_id"],
        objective_revision_ref={
            "kind": "objective_revision",
            "id": kwargs["objective_revision"]["objective_revision_id"],
        },
        boundary=kwargs["boundary"],
        authority_policy_ref=kwargs["authority_policy_ref"],
        source_registrations=kwargs["source_registrations"],
        command_policy=kwargs["command_policy"],
        secret_exclusion_policy=kwargs["secret_exclusion_policy"],
        human_authority_ref=kwargs["human_authority_ref"],
        bound_at=kwargs["bound_at"],
        schema_root=SCHEMA_ROOT,
    )["project_binding_id"]

    with pytest.raises(BootNotFoundError):
        boot_project(store, project_id=kwargs["project_id"], project_binding_id=would_be_binding_id)
    with pytest.raises(StateNotFoundError):
        store.recover(kwargs["project_id"])


def test_boot_project_never_completes_an_interrupted_transaction_via_recover(
    tmp_path: Path,
) -> None:
    """A crash after the lineage append but before the ``COMMITTED`` marker leaves a real,
    on-disk recovery journal only ``store.recover`` would complete. ``boot_project`` must
    fail closed on this project without ever completing it -- proven by checking the
    transaction is *still* unresolved afterward, exactly as it was before the boot attempt."""

    def fault(current: str, _stage: str = "AFTER_LINEAGE_APPEND") -> None:
        if current == _stage:
            raise SimulatedCrash(_stage)

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    with pytest.raises(SimulatedCrash):
        bind_project(
            store,
            **kwargs,
            additional_genesis_records=genesis_records(),
            schema_root=SCHEMA_ROOT,
            fault=fault,
        )
    assert store.resolve_transaction(kwargs["project_id"], "TX-GENESIS") is None

    from manosube_agent_civilization.binding.engine import assemble_project_binding

    would_be_binding_id = assemble_project_binding(
        project_id=kwargs["project_id"],
        objective_revision_ref={
            "kind": "objective_revision",
            "id": kwargs["objective_revision"]["objective_revision_id"],
        },
        boundary=kwargs["boundary"],
        authority_policy_ref=kwargs["authority_policy_ref"],
        source_registrations=kwargs["source_registrations"],
        command_policy=kwargs["command_policy"],
        secret_exclusion_policy=kwargs["secret_exclusion_policy"],
        human_authority_ref=kwargs["human_authority_ref"],
        bound_at=kwargs["bound_at"],
        schema_root=SCHEMA_ROOT,
    )["project_binding_id"]

    with pytest.raises((BootNotFoundError, CorruptStoreError)):
        boot_project(store, project_id=kwargs["project_id"], project_binding_id=would_be_binding_id)

    # Still unresolved -- boot_project never called store.recover() to complete it.
    assert store.resolve_transaction(kwargs["project_id"], "TX-GENESIS") is None


def test_lineage_corruption_after_binding_is_rejected_at_reconstruct(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    lineage_path = store.root / "projects" / project_id / "events" / "transitions.jsonl"
    assert lineage_path.is_file()
    lineage_path.write_text("not-json\n", encoding="utf-8")

    with pytest.raises(CorruptStoreError):
        boot_project(store, project_id=project_id, project_binding_id=result["project_binding_id"])


# --- P10-R1-F2: Boot is transactionally read-only -- a missing materialized current.json
#     view is restored from canonical lineage, never repaired as a side effect ------------- #


def test_boot_succeeds_when_the_materialized_current_view_is_missing(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    current_path = store.root / "projects" / project_id / "state" / "current.json"
    assert current_path.is_file()
    current_path.unlink()
    assert not current_path.is_file()

    ctx = boot_project(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )
    assert ctx.current_state["state_revision"] == 0
    assert _unfreeze(ctx.current_state) == result["committed_state"]


def test_boot_never_recreates_a_missing_materialized_current_view(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    current_path = store.root / "projects" / project_id / "state" / "current.json"
    current_path.unlink()

    boot_project(store, project_id=project_id, project_binding_id=result["project_binding_id"])

    assert not current_path.is_file()


def test_boot_with_a_missing_current_view_writes_nothing_anywhere_in_the_store(
    tmp_path: Path,
) -> None:
    """The strongest form of the read-only proof: not merely "current.json is still absent",
    but the entire project directory's file set and every file's own bytes are identical
    before and after -- Boot introduces no new file, deletes none, and rewrites none."""

    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    current_path = store.root / "projects" / project_id / "state" / "current.json"
    current_path.unlink()
    before = _snapshot(store, project_id)

    boot_project(store, project_id=project_id, project_binding_id=result["project_binding_id"])

    assert _snapshot(store, project_id) == before


def test_boot_with_the_current_view_already_present_writes_nothing_either(
    tmp_path: Path,
) -> None:
    """Positive control: the ordinary case (current.json already present and up to date) is
    equally read-only -- this was already implied by the mutation-free repeated-boot proof,
    stated here explicitly against the exact file this Round's finding was about."""

    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    current_path = store.root / "projects" / project_id / "state" / "current.json"
    assert current_path.is_file()
    before_bytes = current_path.read_bytes()
    before = _snapshot(store, project_id)

    boot_project(store, project_id=project_id, project_binding_id=result["project_binding_id"])

    assert current_path.read_bytes() == before_bytes
    assert _snapshot(store, project_id) == before


# --- P10-R2-F1: Boot requires a quiescent Store -- a present but corrupted materialized
#     current.json view must not be silently ignored ------------------------------------- #


def test_boot_rejects_a_present_current_view_with_the_wrong_project_id(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    current_path = store.root / "projects" / project_id / "state" / "current.json"
    body = json.loads(current_path.read_text(encoding="utf-8"))
    body["project_id"] = "PRJ-SOMETHING-ELSE"
    current_path.write_text(json.dumps(body), encoding="utf-8")

    with pytest.raises(CorruptStoreError):
        boot_project(store, project_id=project_id, project_binding_id=result["project_binding_id"])


def test_boot_rejects_a_present_current_view_behind_committed_lineage(tmp_path: Path) -> None:
    """Requires a real second committed transition so the present view can legitimately be
    made to lag behind it."""

    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    genesis_state = result["committed_state"]
    successor = deepcopy(genesis_state)
    successor["state_revision"] = genesis_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = genesis_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": "TX-ADVANCE-0001"}
    from manosube_agent_civilization.state.fingerprint import fingerprint_project_state

    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": "TX-ADVANCE-0001",
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": genesis_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": genesis_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-09-06T10:00:00Z",
    }
    store.commit(
        project_id,
        genesis_state["state_revision"],
        genesis_state["semantic_fingerprint"],
        successor,
        event,
    )
    current_path = store.root / "projects" / project_id / "state" / "current.json"
    current_path.write_text(json.dumps(genesis_state), encoding="utf-8")

    with pytest.raises(CorruptStoreError):
        boot_project(store, project_id=project_id, project_binding_id=result["project_binding_id"])


# --- P10-R2-F2: Boot requires a quiescent Store -- a later, still-pending transaction must
#     never be silently ignored in favor of the last committed State ---------------------- #


@pytest.mark.parametrize("stage", STAGES)
def test_boot_rejects_every_crash_stage_of_a_later_pending_transaction(
    stage: str, tmp_path: Path
) -> None:
    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    genesis_state = result["committed_state"]
    successor = deepcopy(genesis_state)
    successor["state_revision"] = genesis_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = genesis_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": "TX-ADVANCE-0001"}
    from manosube_agent_civilization.state.fingerprint import fingerprint_project_state

    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": "TX-ADVANCE-0001",
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": genesis_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": genesis_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-09-06T10:00:00Z",
    }

    def fault(current: str, _stage: str = stage) -> None:
        if current == _stage:
            raise SimulatedCrash(_stage)

    with pytest.raises(SimulatedCrash):
        store.commit(
            project_id,
            genesis_state["state_revision"],
            genesis_state["semantic_fingerprint"],
            successor,
            event,
            fault=fault,
        )
    before = _snapshot(store, project_id)

    with pytest.raises(CorruptStoreError):
        boot_project(store, project_id=project_id, project_binding_id=result["project_binding_id"])

    # No mutation from the rejection itself, and the pending transaction was never
    # completed via recover() -- its own journal is exactly as the crash left it.
    assert _snapshot(store, project_id) == before
    journal = (
        store.root
        / "projects"
        / project_id
        / "state"
        / "recovery"
        / "TX-ADVANCE-0001"
        / "COMMITTED"
    )
    assert not journal.is_file()


# --- P10-R3-F1: a durable lineage event whose own recovery journal has been deleted must
#     never be silently excluded -- Boot requires every durable lineage event, not merely
#     every still-existing journal, to resolve to committed-transaction evidence ---------- #


def _advance(
    store: FileStateStore, project_id: str, genesis_state: dict[str, Any]
) -> dict[str, Any]:
    """Build and commit a real second State transition -- shared by both Round 3 tests below,
    mirroring the identical shape ``test_boot_rejects_a_present_current_view_behind_committed_
    lineage`` and the Round 2 crash-stage matrix already build inline."""

    from manosube_agent_civilization.state.fingerprint import fingerprint_project_state

    successor = deepcopy(genesis_state)
    successor["state_revision"] = genesis_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = genesis_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": "TX-ADVANCE-0001"}
    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": "TX-ADVANCE-0001",
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": genesis_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": genesis_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-09-06T10:00:00Z",
    }
    store.commit(
        project_id,
        genesis_state["state_revision"],
        genesis_state["semantic_fingerprint"],
        successor,
        event,
    )
    return successor


def test_boot_rejects_a_committed_later_transaction_whose_journal_was_deleted(
    tmp_path: Path,
) -> None:
    """The exact P10-R3-F1 scenario: a real, honestly-committed later transition whose own
    recovery journal directory is later destroyed -- the last durable evidence that it was
    ever completed -- while the prior, matching ``current.json`` is left untouched. Boot must
    reject, never silently reconstruct and return the stale prior revision."""

    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    genesis_state = result["committed_state"]
    _advance(store, project_id, genesis_state)
    current_path = store.root / "projects" / project_id / "state" / "current.json"
    current_path.write_text(json.dumps(genesis_state), encoding="utf-8")
    journal = store.root / "projects" / project_id / "state" / "recovery" / "TX-ADVANCE-0001"
    assert journal.is_dir()
    import shutil

    shutil.rmtree(journal)
    before = _snapshot(store, project_id)

    with pytest.raises(CorruptStoreError):
        boot_project(store, project_id=project_id, project_binding_id=result["project_binding_id"])

    assert _snapshot(store, project_id) == before


def test_boot_rejects_when_a_later_transactions_journal_and_current_view_are_both_removed(
    tmp_path: Path,
) -> None:
    """A sharper variant: the materialized ``current.json`` view is also removed, so nothing
    is left to contradict except the raw lineage itself -- Boot must still reject rather than
    reconstruct and return the last revision it can still fully account for."""

    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    genesis_state = result["committed_state"]
    _advance(store, project_id, genesis_state)
    journal = store.root / "projects" / project_id / "state" / "recovery" / "TX-ADVANCE-0001"
    current_path = store.root / "projects" / project_id / "state" / "current.json"
    import shutil

    shutil.rmtree(journal)
    current_path.unlink()
    before = _snapshot(store, project_id)

    with pytest.raises(CorruptStoreError):
        boot_project(store, project_id=project_id, project_binding_id=result["project_binding_id"])

    assert _snapshot(store, project_id) == before


# --- P10-R4-F1: a plain filesystem entry substituted for a deleted recovery journal
#     directory must not be mistaken for journal evidence -------------------------------- #


def test_boot_rejects_a_committed_later_transactions_journal_replaced_by_a_file(
    tmp_path: Path,
) -> None:
    """The exact P10-R4-F1 scenario at the Boot level: a real, honestly-committed later
    transition whose recovery journal directory is destroyed and replaced by a plain regular
    file at the identical path, while the prior, matching ``current.json`` is left untouched.
    Boot must reject, never mistake the substituted file for journal evidence."""

    store, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    genesis_state = result["committed_state"]
    _advance(store, project_id, genesis_state)
    current_path = store.root / "projects" / project_id / "state" / "current.json"
    current_path.write_text(json.dumps(genesis_state), encoding="utf-8")
    journal = store.root / "projects" / project_id / "state" / "recovery" / "TX-ADVANCE-0001"
    assert journal.is_dir()
    import shutil

    shutil.rmtree(journal)
    journal.write_text("not-a-journal-directory", encoding="utf-8")
    assert journal.exists() and not journal.is_dir()
    before = _snapshot(store, project_id)

    with pytest.raises(CorruptStoreError):
        boot_project(store, project_id=project_id, project_binding_id=result["project_binding_id"])

    assert _snapshot(store, project_id) == before


# --- persisted-record tamper detection (Store's own generic mechanism) -------------------- #


def _record_path(store: FileStateStore, project_id: str, kind: str, record_id: str) -> Path:
    return store.root / "projects" / project_id / "records" / kind / f"{record_id}.json"


def test_a_tampered_persisted_project_binding_is_detected_on_resolution(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    path = _record_path(
        store, kwargs["project_id"], "project_binding", result["project_binding_id"]
    )
    body = json.loads(path.read_text(encoding="utf-8"))
    body["command_policy"]["max_commands_per_change"] = 999999
    path.write_text(json.dumps(body), encoding="utf-8")

    with pytest.raises(CorruptStoreError):
        boot_project(
            store, project_id=kwargs["project_id"], project_binding_id=result["project_binding_id"]
        )


def test_a_tampered_persisted_objective_revision_is_detected_on_resolution(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    path = _record_path(
        store,
        kwargs["project_id"],
        "objective_revision",
        result["objective_revision"]["objective_revision_id"],
    )
    body = json.loads(path.read_text(encoding="utf-8"))
    body["statement"] = "a substituted statement"
    path.write_text(json.dumps(body), encoding="utf-8")

    with pytest.raises(CorruptStoreError):
        boot_project(
            store, project_id=kwargs["project_id"], project_binding_id=result["project_binding_id"]
        )


def test_a_tampered_persisted_authority_rule_is_detected_on_resolution(tmp_path: Path) -> None:
    store, kwargs, result = _bound(tmp_path)
    path = _record_path(
        store,
        kwargs["project_id"],
        "authority_rule",
        result["authority_rule"]["authority_rule_id"],
    )
    body = json.loads(path.read_text(encoding="utf-8"))
    body["scope"]["subjects"] = ["tampered"]
    path.write_text(json.dumps(body), encoding="utf-8")

    with pytest.raises(CorruptStoreError):
        boot_project(
            store, project_id=kwargs["project_id"], project_binding_id=result["project_binding_id"]
        )


def test_an_orphan_unmanifested_record_never_substitutes_for_a_real_binding(tmp_path: Path) -> None:
    """A record written directly to disk, claimed by no committed transaction's own
    manifest, never resolves -- the same guarantee that forecloses a Development Binding or
    a Phase 8 fixture object substituting for a real Product Binding: neither is ever
    persisted through ``bind_project``'s own atomic route, so neither is ever claimed by any
    transaction manifest."""

    store, kwargs, _result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    fake_id = "PROJBIND-" + "7" * 64
    path = _record_path(store, project_id, "project_binding", fake_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"not": "a real binding", "project_binding_id": fake_id}), encoding="utf-8"
    )

    before = _snapshot(store, project_id)
    with pytest.raises((BootNotFoundError, CorruptStoreError)):
        boot_project(store, project_id=project_id, project_binding_id=fake_id)
    # The orphan file itself is untouched, but it was never part of the snapshot's
    # committed contract either way -- re-snapshot excluding it to confirm no *other* file
    # changed.
    after = _snapshot(store, project_id)
    after.pop(f"records/project_binding/{fake_id}.json", None)
    before.pop(f"records/project_binding/{fake_id}.json", None)
    assert after == before


# --- FakeStore-based cross-record consistency matrix (structurally unreachable via a real,
#     honestly-operating Store + Product Binding pairing) ---------------------------------- #


def test_wrong_kind_objective_revision_ref_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    pb2 = deepcopy(graph["project_binding"])
    pb2["objective_revision_ref"] = {
        "kind": "authority_rule",
        "id": graph["objective_revision"]["objective_revision_id"],
    }
    pb2["project_binding_id"] = _project_binding_id(pb2)
    store = _fake_store_for(graph, project_binding=pb2)
    with pytest.raises(BindingValidationError, match="CROSS_KIND_SUBSTITUTION_ALLOWED"):
        boot_project(
            store, project_id=graph["project_id"], project_binding_id=pb2["project_binding_id"]
        )


def test_wrong_kind_authority_policy_ref_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    pb2 = deepcopy(graph["project_binding"])
    pb2["authority_policy_ref"] = {
        "kind": "objective_revision",
        "id": graph["authority_rule"]["authority_rule_id"],
    }
    pb2["project_binding_id"] = _project_binding_id(pb2)
    store = _fake_store_for(graph, project_binding=pb2)
    with pytest.raises(BindingValidationError, match="CROSS_KIND_SUBSTITUTION_ALLOWED"):
        boot_project(
            store, project_id=graph["project_id"], project_binding_id=pb2["project_binding_id"]
        )


def test_wrong_kind_human_authority_ref_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    pb2 = deepcopy(graph["project_binding"])
    pb2["human_authority_ref"] = {"kind": "objective_revision", "id": "OBJ-REV-FAKE-0001"}
    pb2["project_binding_id"] = _project_binding_id(pb2)
    store = _fake_store_for(graph, project_binding=pb2)
    with pytest.raises(BindingValidationError, match="CROSS_KIND_SUBSTITUTION_ALLOWED"):
        boot_project(
            store, project_id=graph["project_id"], project_binding_id=pb2["project_binding_id"]
        )


def test_unresolved_objective_revision_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    store = _fake_store_for(graph, include_objective=False)
    with pytest.raises(BootNotFoundError):
        boot_project(
            store,
            project_id=graph["project_id"],
            project_binding_id=graph["project_binding"]["project_binding_id"],
        )


# --- P10-R1-F3: Objective Revision's own declared id must equal the Binding's
#     objective_revision_ref.id (Objective Revision carries no content-addressed identity of
#     its own, so lookup-key success alone never proves this) ----------------------------- #


def test_objective_revision_declared_id_differing_from_binding_ref_is_rejected(
    tmp_path: Path,
) -> None:
    """A Store (or adapter) that returns a body resolving under the requested
    ``objective_revision_ref.id`` lookup key, but whose own declared ``objective_revision_id``
    field names a different id, must fail closed -- lookup-key success is not identity
    equality."""

    graph = _real_graph(tmp_path)
    ref_id = graph["project_binding"]["objective_revision_ref"]["id"]
    self_inconsistent_orev = dict(graph["objective_revision"])
    self_inconsistent_orev["objective_revision_id"] = "OBJ-REV-DECLARED-DIFFERENTLY-0001"

    store = _FakeStore(
        {
            (
                graph["project_id"],
                "project_binding",
                graph["project_binding"]["project_binding_id"],
            ): graph["project_binding"],
            (graph["project_id"], "objective_revision", ref_id): self_inconsistent_orev,
            (
                graph["project_id"],
                "authority_rule",
                graph["authority_rule"]["authority_rule_id"],
            ): graph["authority_rule"],
        },
        graph["current_state"],
    )
    with pytest.raises(BootConsistencyError, match="objective_revision_id"):
        boot_project(
            store,
            project_id=graph["project_id"],
            project_binding_id=graph["project_binding"]["project_binding_id"],
        )


def test_objective_revision_declared_id_matching_binding_ref_succeeds(tmp_path: Path) -> None:
    """Positive control: the ordinary, self-consistent case (declared id equals the lookup
    key equals the Binding's own reference) still boots successfully -- the new check does
    not reject everything."""

    graph = _real_graph(tmp_path)
    ref_id = graph["project_binding"]["objective_revision_ref"]["id"]
    assert graph["objective_revision"]["objective_revision_id"] == ref_id
    store = _fake_store_for(graph)
    ctx = boot_project(
        store,
        project_id=graph["project_id"],
        project_binding_id=graph["project_binding"]["project_binding_id"],
    )
    assert ctx.objective_revision_id == ref_id


def test_unresolved_authority_rule_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    store = _fake_store_for(graph, include_authority=False)
    with pytest.raises(BootNotFoundError):
        boot_project(
            store,
            project_id=graph["project_id"],
            project_binding_id=graph["project_binding"]["project_binding_id"],
        )


def test_authority_rule_own_id_not_reproducing_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    arule2 = deepcopy(graph["authority_rule"])
    arule2["scope"]["subjects"] = ["tampered-without-recomputing-id"]
    store = _fake_store_for(graph, authority_rule=arule2)
    with pytest.raises(BootConsistencyError, match="authority_rule_id"):
        boot_project(
            store,
            project_id=graph["project_id"],
            project_binding_id=graph["project_binding"]["project_binding_id"],
        )


def test_authority_policy_ref_id_not_matching_recomputed_rule_id_is_rejected(
    tmp_path: Path,
) -> None:
    graph = _real_graph(tmp_path)
    arule2 = deepcopy(graph["authority_rule"])
    arule2["scope"]["subjects"] = ["a-different-but-self-consistent-rule"]
    new_id = _rule_id({k: v for k, v in arule2.items() if k != "authority_rule_id"})
    arule2["authority_rule_id"] = new_id
    # project_binding still names the OLD id -- resolve_binding_references looks the new
    # body up under the old key, simulating a Store that (impossibly, for a real one)
    # returned a different, self-consistent body under the requested id.
    old_id = graph["authority_rule"]["authority_rule_id"]
    store = _FakeStore(
        {
            (
                graph["project_id"],
                "project_binding",
                graph["project_binding"]["project_binding_id"],
            ): graph["project_binding"],
            (
                graph["project_id"],
                "objective_revision",
                graph["objective_revision"]["objective_revision_id"],
            ): graph["objective_revision"],
            (graph["project_id"], "authority_rule", old_id): arule2,
        },
        graph["current_state"],
    )
    with pytest.raises(BootConsistencyError, match=r"authority_policy_ref\.id"):
        boot_project(
            store,
            project_id=graph["project_id"],
            project_binding_id=graph["project_binding"]["project_binding_id"],
        )


def test_authority_rule_project_id_mismatch_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    arule2 = deepcopy(graph["authority_rule"])
    arule2["project_id"] = "PRJ-DIFFERENT-BOOT-0001"
    arule2["authority_rule_id"] = _rule_id(
        {k: v for k, v in arule2.items() if k != "authority_rule_id"}
    )
    pb2 = deepcopy(graph["project_binding"])
    pb2["authority_policy_ref"] = {"kind": "authority_rule", "id": arule2["authority_rule_id"]}
    pb2["project_binding_id"] = _project_binding_id(pb2)
    store = _fake_store_for(graph, project_binding=pb2, authority_rule=arule2)
    with pytest.raises(BootConsistencyError, match=r"authority_rule\.project_id"):
        boot_project(
            store, project_id=graph["project_id"], project_binding_id=pb2["project_binding_id"]
        )


def test_objective_revision_project_id_mismatch_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    orev2 = deepcopy(graph["objective_revision"])
    orev2["project_id"] = "PRJ-DIFFERENT-BOOT-0002"
    store = _fake_store_for(graph, objective_revision=orev2)
    with pytest.raises(BootConsistencyError, match=r"objective_revision\.project_id"):
        boot_project(
            store,
            project_id=graph["project_id"],
            project_binding_id=graph["project_binding"]["project_binding_id"],
        )


def test_owner_authority_ref_mismatch_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    orev2 = deepcopy(graph["objective_revision"])
    orev2["owner_authority_ref"] = {"kind": "human_authority", "id": "AUTH-DIFFERENT-BOOT-0001"}
    store = _fake_store_for(graph, objective_revision=orev2)
    with pytest.raises(BootConsistencyError, match="owner_authority_ref"):
        boot_project(
            store,
            project_id=graph["project_id"],
            project_binding_id=graph["project_binding"]["project_binding_id"],
        )


def test_objective_revision_human_authority_ref_mismatch_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    orev2 = deepcopy(graph["objective_revision"])
    orev2["human_authority_ref"] = {"kind": "human_authority", "id": "AUTH-DIFFERENT-BOOT-0002"}
    store = _fake_store_for(graph, objective_revision=orev2)
    with pytest.raises(BootConsistencyError, match=r"objective_revision\.human_authority_ref"):
        boot_project(
            store,
            project_id=graph["project_id"],
            project_binding_id=graph["project_binding"]["project_binding_id"],
        )


def test_authority_rule_declared_by_mismatch_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    arule2 = deepcopy(graph["authority_rule"])
    arule2["declared_by"] = {"kind": "human_authority", "id": "AUTH-DIFFERENT-BOOT-0003"}
    arule2["authority_rule_id"] = _rule_id(
        {k: v for k, v in arule2.items() if k != "authority_rule_id"}
    )
    pb2 = deepcopy(graph["project_binding"])
    pb2["authority_policy_ref"] = {"kind": "authority_rule", "id": arule2["authority_rule_id"]}
    pb2["project_binding_id"] = _project_binding_id(pb2)
    store = _fake_store_for(graph, project_binding=pb2, authority_rule=arule2)
    with pytest.raises(BootConsistencyError, match=r"authority_rule\.declared_by"):
        boot_project(
            store, project_id=graph["project_id"], project_binding_id=pb2["project_binding_id"]
        )


def test_reconstructed_state_project_id_mismatch_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    state2 = deepcopy(graph["current_state"])
    state2["project_id"] = "PRJ-DIFFERENT-BOOT-0004"
    store = _fake_store_for(graph, current_state=state2)
    with pytest.raises(BootConsistencyError, match="current State's own project_id"):
        boot_project(
            store,
            project_id=graph["project_id"],
            project_binding_id=graph["project_binding"]["project_binding_id"],
        )


def test_reconstructed_state_objective_revision_id_mismatch_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    state2 = deepcopy(graph["current_state"])
    state2["objective_revision_id"] = "OBJ-REV-DIFFERENT-BOOT-0001"
    store = _fake_store_for(graph, current_state=state2)
    with pytest.raises(BootConsistencyError, match="objective_revision_id"):
        boot_project(
            store,
            project_id=graph["project_id"],
            project_binding_id=graph["project_binding"]["project_binding_id"],
        )


def test_caller_supplied_project_binding_id_differing_from_bodys_own_id_is_rejected(
    tmp_path: Path,
) -> None:
    graph = _real_graph(tmp_path)
    other_id = "PROJBIND-" + "5" * 64
    store = _FakeStore(
        {
            (graph["project_id"], "project_binding", other_id): graph["project_binding"],
            (
                graph["project_id"],
                "objective_revision",
                graph["objective_revision"]["objective_revision_id"],
            ): graph["objective_revision"],
            (
                graph["project_id"],
                "authority_rule",
                graph["authority_rule"]["authority_rule_id"],
            ): graph["authority_rule"],
        },
        graph["current_state"],
    )
    with pytest.raises(BootConsistencyError, match="does not match the requested"):
        boot_project(store, project_id=graph["project_id"], project_binding_id=other_id)


def test_project_binding_project_id_mismatch_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    pb2 = deepcopy(graph["project_binding"])
    pb2["project_id"] = "PRJ-DIFFERENT-BOOT-0005"
    pb2["project_binding_id"] = _project_binding_id(pb2)
    store = _fake_store_for(graph, project_binding=pb2)
    with pytest.raises(BootConsistencyError, match=r"project_binding\.project_id"):
        boot_project(
            store, project_id=graph["project_id"], project_binding_id=pb2["project_binding_id"]
        )


def test_binding_body_not_reproducing_its_own_identity_is_rejected(tmp_path: Path) -> None:
    graph = _real_graph(tmp_path)
    pb2 = deepcopy(graph["project_binding"])
    pb2["project_binding_id"] = "PROJBIND-" + "6" * 64
    store = _fake_store_for(graph, project_binding=pb2)
    with pytest.raises(BindingIdentityError):
        boot_project(
            store, project_id=graph["project_id"], project_binding_id=pb2["project_binding_id"]
        )
