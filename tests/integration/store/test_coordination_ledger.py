"""Decisive proofs for :class:`FileStateStore`'s orthogonal coordination ledger (Structural
Review Round 2, P84-R2-F1/F4, ``ADOPT_P84_PROJECT_STATE_ORTHOGONAL_COORDINATION_REBIND``).

This ledger is the Store's own second, independent append-only lane -- entirely disjoint from
Project State's own lineage/current/records/recovery-journal (``events/``, ``state/``,
``records/``) -- that the Work Time Transparency vertical now commits every coordination record
through, never through ``commit_state_transition``. These tests exercise the ledger directly
against a real :class:`FileStateStore`, independent of WTT's own schema/engine layer, proving:
idempotent same-body replay, fail-closed conflicting replay, fail-closed tampered-ledger-entry
resolution, crash/restart recovery (a ledger entry with no materialized record file heals on the
next resolve or commit), concurrent-writer single lineage (the shared per-project lock admits
exactly one winner), and -- the central guarantee this whole rebind exists for -- that no
coordination commit ever touches Project State's own ``state_revision``/``semantic_fingerprint``/
``lineage_head_ref``/lineage log/records, structurally, not merely by convention.
"""

from __future__ import annotations

import json
from pathlib import Path
import threading
from typing import Any

import pytest
from tests.state_helpers import SCHEMA_ROOT, initial_state

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.errors import CorruptStoreError, RecordConflictError


def _prepared_initial() -> dict[str, Any]:
    state = initial_state()
    state["semantic_fingerprint"] = fingerprint_project_state(
        state, schema_root=SCHEMA_ROOT
    ).as_dict()
    return state


def _store(tmp_path: Path) -> FileStateStore:
    return FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)


def _bounded_project(tmp_path: Path) -> tuple[FileStateStore, str, dict[str, Any]]:
    s = _store(tmp_path)
    initial = _prepared_initial()
    s.initialize("PRJ-0001", initial)
    return s, "PRJ-0001", initial


def test_commit_and_resolve_round_trip(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    committed = s.commit_coordination_record(
        project_id, "work_time_coordination_open", "WTC-OPEN-A", body
    )
    assert committed == body
    assert (
        s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A")
        == body
    )


def test_resolve_of_never_committed_id_is_none(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    assert s.resolve_coordination_record(project_id, "work_time_coordination_open", "NEVER") is None


def test_same_body_replay_is_idempotent_and_appends_no_new_ledger_line(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    s.commit_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A", body)
    ledger_path = tmp_path / "backend" / "projects" / project_id / "coordination" / "ledger.jsonl"
    before = ledger_path.read_bytes()
    replayed = s.commit_coordination_record(
        project_id, "work_time_coordination_open", "WTC-OPEN-A", body
    )
    assert replayed == body
    assert ledger_path.read_bytes() == before


def test_conflicting_replay_under_the_same_identity_is_refused(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    s.commit_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A", body)
    conflicting = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 2}
    with pytest.raises(RecordConflictError):
        s.commit_coordination_record(
            project_id, "work_time_coordination_open", "WTC-OPEN-A", conflicting
        )
    # the original body is still exactly what resolves -- the refused conflict changed nothing.
    assert (
        s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A")
        == body
    )


def test_a_tampered_ledger_entry_is_refused_fail_closed(tmp_path: Path) -> None:
    """A ledger line whose own embedded ``fingerprint`` no longer matches its own embedded
    ``body`` -- a hand-edited/corrupted ledger, never produced by any real commit -- is refused
    the moment this Store tries to materialize or resolve it, never silently trusted."""

    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    s.commit_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A", body)

    ledger_path = tmp_path / "backend" / "projects" / project_id / "coordination" / "ledger.jsonl"
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["body"]["value"] = 999  # tamper the body without recomputing its own fingerprint
    lines[0] = json.dumps(entry, sort_keys=True)
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Force re-materialization from the (now tampered) ledger by removing the cached record file.
    record_path = (
        tmp_path
        / "backend"
        / "projects"
        / project_id
        / "coordination"
        / "records"
        / "work_time_coordination_open"
        / "WTC-OPEN-A.json"
    )
    record_path.unlink()

    with pytest.raises(CorruptStoreError):
        s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A")


def test_crash_between_ledger_append_and_materialization_heals_on_resolve(tmp_path: Path) -> None:
    """Simulates the exact crash window ``commit_coordination_record``'s own docstring
    describes: a durable ledger entry exists, but the permanent per-record file was never
    written. The next resolve call must self-heal -- materialize the record from the ledger's
    own durable copy -- rather than report it missing."""

    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    s.commit_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A", body)

    record_path = (
        tmp_path
        / "backend"
        / "projects"
        / project_id
        / "coordination"
        / "records"
        / "work_time_coordination_open"
        / "WTC-OPEN-A.json"
    )
    assert record_path.exists()
    record_path.unlink()
    assert not record_path.exists()

    resolved = s.resolve_coordination_record(
        project_id, "work_time_coordination_open", "WTC-OPEN-A"
    )
    assert resolved == body
    assert record_path.exists()
    assert canonical_json_bytes(body) == record_path.read_bytes()


def test_recover_coordination_ledger_heals_every_missing_materialization_and_is_idempotent(
    tmp_path: Path,
) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    for index in range(3):
        s.commit_coordination_record(
            project_id,
            "work_time_coordination_open",
            f"WTC-OPEN-{index}",
            {"kind": "work_time_coordination_open", "id": f"WTC-OPEN-{index}", "value": index},
        )
    records_dir = (
        tmp_path
        / "backend"
        / "projects"
        / project_id
        / "coordination"
        / "records"
        / "work_time_coordination_open"
    )
    for path in records_dir.iterdir():
        path.unlink()

    healed = s.recover_coordination_ledger(project_id)
    assert healed == 3
    assert sorted(p.name for p in records_dir.iterdir()) == [
        "WTC-OPEN-0.json",
        "WTC-OPEN-1.json",
        "WTC-OPEN-2.json",
    ]
    # idempotent: nothing left to heal on a second call.
    assert s.recover_coordination_ledger(project_id) == 0


def test_concurrent_conflicting_writers_admit_exactly_one_winner(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    results: list[str] = []

    def attempt(value: int) -> None:
        body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-RACE", "value": value}
        try:
            s.commit_coordination_record(
                project_id, "work_time_coordination_open", "WTC-OPEN-RACE", body
            )
            results.append("WIN")
        except RecordConflictError:
            results.append("CONFLICT")

    threads = [threading.Thread(target=attempt, args=(i,)) for i in (1, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == ["CONFLICT", "WIN"]
    # exactly one lineage: the resolved body is whichever value genuinely won, never a blend.
    resolved = s.resolve_coordination_record(
        project_id, "work_time_coordination_open", "WTC-OPEN-RACE"
    )
    assert resolved is not None and resolved["value"] in (1, 2)


def test_concurrent_identical_writers_are_both_idempotent_winners(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-SAME", "value": 7}
    results: list[dict[str, Any]] = []

    def attempt() -> None:
        results.append(
            s.commit_coordination_record(
                project_id, "work_time_coordination_open", "WTC-OPEN-SAME", body
            )
        )

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == [body, body]


def test_no_coordination_commit_ever_touches_project_state(tmp_path: Path) -> None:
    """The central proof this whole rebind exists for: committing several coordination records
    -- open, update, terminal kinds alike -- leaves ``state/``, ``events/``, and Project State's
    own ``records/`` byte-for-byte unchanged, and ``state_revision``/``semantic_fingerprint``
    exactly what they were before any of them. Every mutation lands only under this project's
    own ``coordination/`` directory."""

    s, project_id, initial = _bounded_project(tmp_path)
    project_dir = tmp_path / "backend" / "projects" / project_id

    def snapshot() -> dict[str, bytes]:
        return {
            str(path.relative_to(project_dir)): path.read_bytes()
            for path in sorted(project_dir.rglob("*"))
            if path.is_file() and not str(path.relative_to(project_dir)).startswith("coordination/")
        }

    before = snapshot()
    before_current = s.load_current(project_id)

    for kind, record_id in (
        ("work_time_coordination_open", "WTC-OPEN-A"),
        ("work_time_coordination_update", "WTC-UPDATE-A-1"),
        ("work_time_coordination_terminal", "WTC-TERMINAL-A"),
    ):
        s.commit_coordination_record(project_id, kind, record_id, {"kind": kind, "id": record_id})

    after = snapshot()
    after_current = s.load_current(project_id)

    assert after == before, "coordination commits must never touch any non-coordination Store file"
    assert after_current == before_current
    assert after_current["state_revision"] == initial["state_revision"]
    assert after_current["semantic_fingerprint"] == initial["semantic_fingerprint"]
