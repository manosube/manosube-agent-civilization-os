"""Phase 12 (Issue #49) Temporary Agent lifecycle: the one public start route
(``start_temporary_agent``), end-to-end, over a real ``FileStateStore``.

Proves the canonical successful route (``AGENT_RUNTIME_CONTRACT.md`` §5), the required
rejection proofs (§6), and that no rejection or lifecycle operation ever mutates canonical
Binding, State, Lineage, record, or transaction-manifest visibility.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
from types import MappingProxyType
from typing import Any

import pytest
from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.agent_runtime import (
    AgentReleasedError,
    TemporaryAgent,
    start_temporary_agent,
)
import manosube_agent_civilization.agent_runtime.route as agent_runtime_route_module
from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.boot import BootNotFoundError, boot_project
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import STAGES, FileStateStore
from manosube_agent_civilization.store.errors import CorruptStoreError, SimulatedCrash


def _bound(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    store_root = tmp_path / "backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store_root, kwargs, result


def _unfreeze(value: Any) -> Any:
    """Recursively convert a ``BootContext`` field's own frozen shape (``MappingProxyType``
    over ``dict``, ``tuple`` in place of ``list``) back into plain ``dict``/``list`` for
    equality comparison against a JSON-shaped body -- the identical helper
    ``tests/integration/boot/test_boot_project_route.py::_unfreeze`` already uses for this
    same reason: a bare ``==`` comparison against the original plain body no longer applies
    once nested containers change type."""

    if isinstance(value, dict):
        return {key: _unfreeze(item) for key, item in value.items()}
    if hasattr(value, "items"):  # MappingProxyType and other Mapping implementations
        return {key: _unfreeze(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_unfreeze(item) for item in value]
    return value


def _snapshot(store_root: Path, project_id: str) -> dict[str, str]:
    project_dir = store_root / "projects" / project_id
    if not project_dir.is_dir():
        return {}
    return {
        str(path.relative_to(project_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(project_dir.rglob("*"))
        if path.is_file()
    }


def _advance(
    store: FileStateStore, project_id: str, genesis_state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a real second State transition -- the identical shape ``tests/integration/boot/
    test_boot_project_route.py::_advance`` and ``tests/integration/cli/
    test_cli_boot_command.py::_advance`` already build for their own equivalent tests."""

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
    return successor, event


# --- canonical successful route ------------------------------------------------------------ #


def test_start_temporary_agent_boots_a_real_bound_project(tmp_path: Path) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    before = _snapshot(store_root, project_id)

    agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )

    assert isinstance(agent, TemporaryAgent)
    assert agent.boot_context.project_id == project_id
    assert agent.boot_context.project_binding_id == result["project_binding_id"]
    assert _unfreeze(agent.boot_context.current_state) == result["committed_state"]
    assert _snapshot(store_root, project_id) == before


def test_start_calls_boot_project_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)

    calls: list[int] = []
    real_boot_project = boot_project

    def counting_boot_project(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        return real_boot_project(*args, **kwargs)

    monkeypatch.setattr(agent_runtime_route_module, "boot_project", counting_boot_project)

    start_temporary_agent(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )

    assert len(calls) == 1


def test_agent_boot_context_agrees_with_a_direct_boot_project_call(tmp_path: Path) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)

    agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )
    direct = boot_project(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )

    assert agent.boot_context == direct


def test_agent_boot_context_is_deeply_immutable(tmp_path: Path) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)

    agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )

    assert isinstance(agent.boot_context.project_binding, MappingProxyType)
    with pytest.raises(TypeError):
        agent.boot_context.project_binding["command_policy"] = {}  # type: ignore[index]
    with pytest.raises(Exception):  # noqa: B017 - frozen dataclass, exact type is not load-bearing
        agent.boot_context.project_id = "OTHER"  # type: ignore[misc]


def test_start_temporary_agent_makes_zero_store_mutation(tmp_path: Path) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    before = _snapshot(store_root, project_id)

    agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )
    _ = agent.boot_context
    agent.release()

    assert _snapshot(store_root, project_id) == before


# --- release lifecycle ----------------------------------------------------------------------- #


def test_release_is_idempotent_and_makes_zero_store_mutation(tmp_path: Path) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    before = _snapshot(store_root, project_id)

    agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )
    agent.release()
    agent.release()
    agent.release()

    assert _snapshot(store_root, project_id) == before


def test_released_agent_rejects_boot_context_access(tmp_path: Path) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)

    agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )
    agent.release()

    with pytest.raises(AgentReleasedError):
        _ = agent.boot_context


def test_a_released_agent_cannot_be_restarted_or_resumed(tmp_path: Path) -> None:
    """No method on a released -- or active -- ``TemporaryAgent`` restarts, resumes, restores,
    or recovers anything: the only public surface is ``boot_context`` (a property) and
    ``release`` (frozen semantic decision 6)."""

    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)

    agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )
    original_context = agent.boot_context
    agent.release()

    public_attrs = {name for name in dir(agent) if not name.startswith("_")}
    assert public_attrs == {"boot_context", "release"}

    # A brand-new start is independent of the released Agent's own lifecycle state.
    second_agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=result["project_binding_id"]
    )
    assert second_agent.boot_context == original_context  # via BootContext's own equality
    with pytest.raises(AgentReleasedError):
        _ = agent.boot_context  # still released, unaffected by the second start


# --- required rejection proofs (propagated unchanged from Boot/Store) ----------------------- #


def test_start_rejects_a_missing_project_or_binding(tmp_path: Path) -> None:
    store_root, kwargs, _result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    before = _snapshot(store_root, project_id)

    with pytest.raises(BootNotFoundError):
        start_temporary_agent(
            store, project_id=project_id, project_binding_id="PROJBIND-DOES-NOT-EXIST"
        )

    assert _snapshot(store_root, project_id) == before


def _record_path(store_root: Path, project_id: str, kind: str, record_id: str) -> Path:
    return store_root / "projects" / project_id / "records" / kind / f"{record_id}.json"


def test_start_rejects_a_tampered_persisted_project_binding(tmp_path: Path) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    pbid = result["project_binding_id"]
    record_path = _record_path(store_root, project_id, "project_binding", pbid)
    body = json.loads(record_path.read_text(encoding="utf-8"))
    body["command_policy"]["max_commands_per_change"] = 999
    record_path.write_text(json.dumps(body), encoding="utf-8")
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)

    with pytest.raises(CorruptStoreError):
        start_temporary_agent(store, project_id=project_id, project_binding_id=pbid)


def test_start_rejects_a_malformed_present_current_view(tmp_path: Path) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    current_path = store_root / "projects" / project_id / "state" / "current.json"
    current_path.write_text("not-json", encoding="utf-8")
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    before = _snapshot(store_root, project_id)

    with pytest.raises(CorruptStoreError):
        start_temporary_agent(
            store, project_id=project_id, project_binding_id=result["project_binding_id"]
        )

    assert _snapshot(store_root, project_id) == before


@pytest.mark.parametrize("stage", [STAGES[0], STAGES[4], STAGES[-1]])
def test_start_rejects_a_representative_interrupted_later_transaction(
    stage: str, tmp_path: Path
) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    genesis_state = result["committed_state"]
    successor, event = _advance(store, project_id, genesis_state)

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
    before = _snapshot(store_root, project_id)

    with pytest.raises(CorruptStoreError):
        start_temporary_agent(
            store, project_id=project_id, project_binding_id=result["project_binding_id"]
        )

    assert _snapshot(store_root, project_id) == before


def test_start_rejects_a_later_transactions_journal_replaced_by_a_non_directory_entry(
    tmp_path: Path,
) -> None:
    """P10-R4-F1's own scenario, proven through this layer's own boundary."""

    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    genesis_state = result["committed_state"]
    successor, event = _advance(store, project_id, genesis_state)
    store.commit(
        project_id,
        genesis_state["state_revision"],
        genesis_state["semantic_fingerprint"],
        successor,
        event,
    )
    current_path = store_root / "projects" / project_id / "state" / "current.json"
    current_path.write_text(json.dumps(genesis_state), encoding="utf-8")
    journal = store_root / "projects" / project_id / "state" / "recovery" / "TX-ADVANCE-0001"
    shutil.rmtree(journal)
    journal.write_text("not-a-journal-directory", encoding="utf-8")
    before = _snapshot(store_root, project_id)

    with pytest.raises(CorruptStoreError):
        start_temporary_agent(
            store, project_id=project_id, project_binding_id=result["project_binding_id"]
        )

    assert _snapshot(store_root, project_id) == before


# --- fresh-process determinism (frozen semantic decision 8) --------------------------------- #


_FRESH_PROCESS_SCRIPT = textwrap.dedent(
    """
    import sys
    from pathlib import Path

    from manosube_agent_civilization.agent_runtime import start_temporary_agent
    from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
    from manosube_agent_civilization.store import FileStateStore

    def _plain(value):
        if hasattr(value, "items"):
            return {key: _plain(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes)):
            return [_plain(item) for item in value]
        return value

    store_root, schema_root, project_id, project_binding_id = sys.argv[1:5]
    store = FileStateStore(Path(store_root), schema_root=Path(schema_root))
    agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    projection = {
        "project_id": agent.boot_context.project_id,
        "project_binding_id": agent.boot_context.project_binding_id,
        "objective_revision_id": agent.boot_context.objective_revision_id,
        "authority_rule_id": agent.boot_context.authority_rule_id,
        "project_binding": _plain(agent.boot_context.project_binding),
        "objective_revision": _plain(agent.boot_context.objective_revision),
        "authority_rule": _plain(agent.boot_context.authority_rule),
        "current_state": _plain(agent.boot_context.current_state),
        "human_authority_ref": _plain(agent.boot_context.human_authority_ref),
    }
    agent.release()
    sys.stdout.buffer.write(canonical_json_bytes(projection) + b"\\n")
    """
)


def test_repeated_fresh_process_starts_give_byte_equivalent_boot_context_projections(
    tmp_path: Path,
) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    before = _snapshot(store_root, project_id)
    argv = [
        sys.executable,
        "-c",
        _FRESH_PROCESS_SCRIPT,
        str(store_root),
        str(SCHEMA_ROOT),
        project_id,
        result["project_binding_id"],
    ]

    first = subprocess.run(argv, capture_output=True)  # noqa: S603
    second = subprocess.run(argv, capture_output=True)  # noqa: S603

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout
    assert first.stdout.endswith(b"\n")
    assert _snapshot(store_root, project_id) == before
