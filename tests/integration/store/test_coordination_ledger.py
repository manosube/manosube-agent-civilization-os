"""Decisive proofs for :class:`FileStateStore`'s orthogonal coordination ledger (Structural
Review Round 2, P84-R2-F1/F4, ``ADOPT_P84_PROJECT_STATE_ORTHOGONAL_COORDINATION_REBIND``;
hardened Structural Review Round 3, P84-R3-F1/F2/F3, ``ADOPT_P84_R3_COORDINATION_LEDGER_
CLOSURE``).

This ledger is the Store's own second, independent append-only lane -- entirely disjoint from
Project State's own lineage/current/records/recovery-journal (``events/``, ``state/``,
``records/``) -- that the Work Time Transparency vertical now commits every coordination record
through, never through ``commit_state_transition``. These tests exercise the ledger directly
against a real :class:`FileStateStore`, independent of WTT's own schema/engine layer, proving:
idempotent same-body replay, fail-closed conflicting replay, fail-closed tampered-ledger-entry
resolution, crash/restart recovery, concurrent-writer single lineage, and the central guarantee
this whole rebind exists for -- that no coordination commit ever touches Project State.

Round 3 adds: an atomic per-chain tip guard that admits exactly one winner of a concurrent
update-vs-terminal race even when the two racing writes carry different ``record_id``s
(P84-R3-F1); resolve-time re-verification of the materialized cache against its own unique
authoritative ledger fact, refusing a schema-valid substituted cache body and a duplicate
divergent ledger entry (P84-R3-F2); and tolerance of (and healing for) an interrupted, torn
trailing ledger write, at every persistence stage a crash could land in (P84-R3-F3).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import threading
from typing import Any

import pytest
from tests.state_helpers import SCHEMA_ROOT, initial_state

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.errors import (
    CoordinationTipConflictError,
    CorruptStoreError,
    RecordConflictError,
)


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


def _ledger_path(tmp_path: Path, project_id: str) -> Path:
    return tmp_path / "backend" / "projects" / project_id / "coordination" / "ledger.jsonl"


def _record_path(tmp_path: Path, project_id: str, kind: str, record_id: str) -> Path:
    return (
        tmp_path
        / "backend"
        / "projects"
        / project_id
        / "coordination"
        / "records"
        / kind
        / f"{record_id}.json"
    )


def _commit_singleton(
    s: FileStateStore, project_id: str, kind: str, record_id: str, body: dict[str, Any]
) -> dict[str, Any]:
    """A record whose own chain is itself alone -- the shape every pre-Round-3 test in this
    file already used, still valid: a chain of one never has a tip other than ``None`` before
    its own first (and only) entry."""

    return s.commit_coordination_record_at_tip(
        project_id, record_id, kind, record_id, body, expected_predecessor=None
    )


# --------------------------------------------------------------------------------------- #
# Carried forward from Structural Review Round 2, adapted to the new tip-guarded API.
# --------------------------------------------------------------------------------------- #


def test_commit_and_resolve_round_trip(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    committed = _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-A", body)
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
    _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-A", body)
    before = _ledger_path(tmp_path, project_id).read_bytes()
    replayed = _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-A", body)
    assert replayed == body
    assert _ledger_path(tmp_path, project_id).read_bytes() == before


def test_conflicting_replay_under_the_same_identity_is_refused(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-A", body)
    conflicting = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 2}
    with pytest.raises(RecordConflictError):
        _commit_singleton(
            s, project_id, "work_time_coordination_open", "WTC-OPEN-A", conflicting
        )
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
    _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-A", body)

    ledger_path = _ledger_path(tmp_path, project_id)
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["body"]["value"] = 999  # tamper the body without recomputing its own fingerprint
    lines[0] = json.dumps(entry, sort_keys=True)
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    record_path = _record_path(tmp_path, project_id, "work_time_coordination_open", "WTC-OPEN-A")
    record_path.unlink()

    with pytest.raises(CorruptStoreError):
        s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A")


def test_crash_between_ledger_append_and_materialization_heals_on_resolve(tmp_path: Path) -> None:
    """Simulates the exact crash window this ledger's own docstring describes: a durable ledger
    entry exists, but the permanent per-record file was never written. The next resolve call
    must self-heal -- materialize the record from the ledger's own durable copy -- rather than
    report it missing."""

    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-A", body)

    record_path = _record_path(tmp_path, project_id, "work_time_coordination_open", "WTC-OPEN-A")
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
        _commit_singleton(
            s,
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
    assert s.recover_coordination_ledger(project_id) == 0


def test_concurrent_conflicting_writers_admit_exactly_one_winner(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    results: list[str] = []

    def attempt(value: int) -> None:
        body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-RACE", "value": value}
        try:
            _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-RACE", body)
            results.append("WIN")
        except RecordConflictError:
            results.append("CONFLICT")

    threads = [threading.Thread(target=attempt, args=(i,)) for i in (1, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == ["CONFLICT", "WIN"]
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
            _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-SAME", body)
        )

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == [body, body]


def test_no_coordination_commit_ever_touches_project_state(tmp_path: Path) -> None:
    """The central proof this whole rebind exists for: committing several coordination records
    -- open, update, terminal kinds alike, chained through one real ``chain_id`` -- leaves
    ``state/``, ``events/``, and Project State's own ``records/`` byte-for-byte unchanged, and
    ``state_revision``/``semantic_fingerprint`` exactly what they were before any of them. Every
    mutation lands only under this project's own ``coordination/`` directory."""

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

    chain_id = "WTC-CHAIN-A"
    s.commit_coordination_record_at_tip(
        project_id,
        chain_id,
        "work_time_coordination_open",
        chain_id,
        {"kind": "work_time_coordination_open", "id": chain_id},
        expected_predecessor=None,
    )
    s.commit_coordination_record_at_tip(
        project_id,
        chain_id,
        "work_time_coordination_update",
        "WTC-UPDATE-A-1",
        {"kind": "work_time_coordination_update", "id": "WTC-UPDATE-A-1"},
        expected_predecessor={"kind": "work_time_coordination_open", "id": chain_id},
    )
    s.commit_coordination_record_at_tip(
        project_id,
        chain_id,
        "work_time_coordination_terminal",
        "WTC-TERMINAL-A",
        {"kind": "work_time_coordination_terminal", "id": "WTC-TERMINAL-A"},
        expected_predecessor={"kind": "work_time_coordination_update", "id": "WTC-UPDATE-A-1"},
    )

    after = snapshot()
    after_current = s.load_current(project_id)

    assert after == before, "coordination commits must never touch any non-coordination Store file"
    assert after_current == before_current
    assert after_current["state_revision"] == initial["state_revision"]
    assert after_current["semantic_fingerprint"] == initial["semantic_fingerprint"]


# --------------------------------------------------------------------------------------- #
# Structural Review Round 3, P84-R3-F1: atomic coordination-tip admission.
# --------------------------------------------------------------------------------------- #


def test_chain_tip_progresses_across_open_update_and_terminal(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    chain_id = "WTC-CHAIN-B"
    s.commit_coordination_record_at_tip(
        project_id,
        chain_id,
        "work_time_coordination_open",
        chain_id,
        {"kind": "work_time_coordination_open", "id": chain_id},
        expected_predecessor=None,
    )
    s.commit_coordination_record_at_tip(
        project_id,
        chain_id,
        "work_time_coordination_update",
        "WTC-UPDATE-B-1",
        {"kind": "work_time_coordination_update", "id": "WTC-UPDATE-B-1"},
        expected_predecessor={"kind": "work_time_coordination_open", "id": chain_id},
    )
    terminal = s.commit_coordination_record_at_tip(
        project_id,
        chain_id,
        "work_time_coordination_terminal",
        "WTC-TERMINAL-B",
        {"kind": "work_time_coordination_terminal", "id": "WTC-TERMINAL-B"},
        expected_predecessor={"kind": "work_time_coordination_update", "id": "WTC-UPDATE-B-1"},
    )
    assert terminal["id"] == "WTC-TERMINAL-B"


def test_a_stale_expected_predecessor_is_refused_atomically(tmp_path: Path) -> None:
    """A caller that resolved the chain's tip, then found the tip had *already* moved on by the
    time it tried to commit against it, is refused -- even though its own ``expected_predecessor``
    was genuinely correct at the moment it was resolved."""

    s, project_id, _ = _bounded_project(tmp_path)
    chain_id = "WTC-CHAIN-C"
    s.commit_coordination_record_at_tip(
        project_id,
        chain_id,
        "work_time_coordination_open",
        chain_id,
        {"kind": "work_time_coordination_open", "id": chain_id},
        expected_predecessor=None,
    )
    s.commit_coordination_record_at_tip(
        project_id,
        chain_id,
        "work_time_coordination_update",
        "WTC-UPDATE-C-1",
        {"kind": "work_time_coordination_update", "id": "WTC-UPDATE-C-1"},
        expected_predecessor={"kind": "work_time_coordination_open", "id": chain_id},
    )
    # A second update at sequence 1 resolving the *open* as its predecessor -- as if the tip
    # had never moved -- is now stale: the real tip is WTC-UPDATE-C-1, not the open.
    with pytest.raises(CoordinationTipConflictError):
        s.commit_coordination_record_at_tip(
            project_id,
            chain_id,
            "work_time_coordination_update",
            "WTC-UPDATE-C-1-ALT",
            {"kind": "work_time_coordination_update", "id": "WTC-UPDATE-C-1-ALT"},
            expected_predecessor={"kind": "work_time_coordination_open", "id": chain_id},
        )


def test_a_second_open_for_a_non_empty_chain_is_refused(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    chain_id = "WTC-CHAIN-D"
    s.commit_coordination_record_at_tip(
        project_id,
        chain_id,
        "work_time_coordination_open",
        chain_id,
        {"kind": "work_time_coordination_open", "id": chain_id},
        expected_predecessor=None,
    )
    with pytest.raises(CoordinationTipConflictError):
        s.commit_coordination_record_at_tip(
            project_id,
            chain_id,
            "work_time_coordination_open",
            chain_id + "-DUPLICATE",
            {"kind": "work_time_coordination_open", "id": chain_id + "-DUPLICATE"},
            expected_predecessor=None,
        )


def test_concurrent_update_vs_terminal_racing_the_identical_predecessor_admits_exactly_one_winner(
    tmp_path: Path,
) -> None:
    """P84-R3-F1's own decisive counterexample: an Update and a Terminal Notice, each keyed by a
    genuinely *different* ``record_id``, race to commit against the identical predecessor. A
    same-``(kind, id)``-only conflict check could never see this race (their ids differ); the
    atomic tip guard must still admit exactly one winner and refuse the other, atomically."""

    s, project_id, _ = _bounded_project(tmp_path)
    chain_id = "WTC-CHAIN-RACE"
    s.commit_coordination_record_at_tip(
        project_id,
        chain_id,
        "work_time_coordination_open",
        chain_id,
        {"kind": "work_time_coordination_open", "id": chain_id},
        expected_predecessor=None,
    )
    predecessor = {"kind": "work_time_coordination_open", "id": chain_id}

    barrier = threading.Barrier(2)
    outcomes: dict[str, str] = {}

    def commit_update() -> None:
        barrier.wait()
        try:
            s.commit_coordination_record_at_tip(
                project_id,
                chain_id,
                "work_time_coordination_update",
                "WTC-UPDATE-RACE-1",
                {"kind": "work_time_coordination_update", "id": "WTC-UPDATE-RACE-1"},
                expected_predecessor=predecessor,
            )
            outcomes["update"] = "WIN"
        except CoordinationTipConflictError:
            outcomes["update"] = "LOSE"

    def commit_terminal() -> None:
        barrier.wait()
        try:
            s.commit_coordination_record_at_tip(
                project_id,
                chain_id,
                "work_time_coordination_terminal",
                "WTC-TERMINAL-RACE",
                {"kind": "work_time_coordination_terminal", "id": "WTC-TERMINAL-RACE"},
                expected_predecessor=predecessor,
            )
            outcomes["terminal"] = "WIN"
        except CoordinationTipConflictError:
            outcomes["terminal"] = "LOSE"

    threads = [threading.Thread(target=commit_update), threading.Thread(target=commit_terminal)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(outcomes.values()) == ["LOSE", "WIN"]
    winner_kind = "work_time_coordination_update" if outcomes["update"] == "WIN" else (
        "work_time_coordination_terminal"
    )
    winner_id = "WTC-UPDATE-RACE-1" if winner_kind == "work_time_coordination_update" else (
        "WTC-TERMINAL-RACE"
    )
    loser_kind = (
        "work_time_coordination_terminal"
        if winner_kind == "work_time_coordination_update"
        else "work_time_coordination_update"
    )
    loser_id = "WTC-TERMINAL-RACE" if loser_kind == "work_time_coordination_terminal" else (
        "WTC-UPDATE-RACE-1"
    )
    assert s.resolve_coordination_record(project_id, winner_kind, winner_id) is not None
    assert s.resolve_coordination_record(project_id, loser_kind, loser_id) is None


# --------------------------------------------------------------------------------------- #
# Structural Review Round 3, P84-R3-F2: authoritative-ledger read verification.
# --------------------------------------------------------------------------------------- #


def test_resolve_refuses_a_schema_valid_substituted_materialized_cache(tmp_path: Path) -> None:
    """The materialized cache file is replaced with a *different*, internally self-consistent,
    still-JSON body -- never touching the ledger line itself. The pre-Round-3 design's own
    return-the-cache-file-directly fast path could not catch this; Round 3's resolve must."""

    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-A", body)

    record_path = _record_path(tmp_path, project_id, "work_time_coordination_open", "WTC-OPEN-A")
    substituted = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 999}
    record_path.write_bytes(canonical_json_bytes(substituted))

    with pytest.raises(CorruptStoreError):
        s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A")


def test_resolve_refuses_duplicate_divergent_ledger_entries(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-A", body)

    ledger_path = _ledger_path(tmp_path, project_id)
    divergent_body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 2}
    divergent_entry = {
        "kind": "work_time_coordination_open",
        "id": "WTC-OPEN-A",
        "project_id": project_id,
        "chain_id": "WTC-OPEN-A",
        "fingerprint": hashlib.sha256(canonical_json_bytes(divergent_body)).hexdigest(),
        "body": divergent_body,
    }
    with ledger_path.open("ab") as stream:
        stream.write(canonical_json_bytes(divergent_entry) + b"\n")

    with pytest.raises(CorruptStoreError):
        s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A")


def test_resolve_tolerates_duplicate_identical_ledger_entries(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-A", body)

    ledger_path = _ledger_path(tmp_path, project_id)
    existing_line = ledger_path.read_bytes()
    with ledger_path.open("ab") as stream:
        stream.write(existing_line)  # append the identical line a second time

    resolved = s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A")
    assert resolved == body


def test_resolve_refuses_an_orphaned_cache_with_no_ledger_backing(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    record_path = _record_path(tmp_path, project_id, "work_time_coordination_open", "WTC-ORPHAN")
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes(
        canonical_json_bytes({"kind": "work_time_coordination_open", "id": "WTC-ORPHAN"})
    )

    with pytest.raises(CorruptStoreError):
        s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-ORPHAN")


# --------------------------------------------------------------------------------------- #
# Structural Review Round 3, P84-R3-F3: interrupted-append recovery boundary.
# --------------------------------------------------------------------------------------- #


def test_a_torn_trailing_write_is_excluded_not_treated_as_whole_file_corruption(
    tmp_path: Path,
) -> None:
    """Real fault injection: a crash strictly mid-append leaves the ledger file's own final
    line incomplete (no terminating ``b"\\n"``) -- the file's *prior*, fully-committed line must
    still resolve cleanly, never raising :class:`CorruptStoreError` for the whole file."""

    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-A", body)

    ledger_path = _ledger_path(tmp_path, project_id)
    with ledger_path.open("ab") as stream:
        # A torn write: a syntactically-incomplete JSON fragment with no trailing newline --
        # exactly what an interrupted ``stream.write(...)`` could leave on disk.
        stream.write(b'{"kind": "work_time_coordination_open", "id": "WTC-OPEN-B", "bo')

    resolved = s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A")
    assert resolved == body
    assert s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-B") is None


def test_the_next_commit_heals_the_torn_tail_before_appending_its_own_new_entry(
    tmp_path: Path,
) -> None:
    """A torn trailing write left by a crash must never be silently concatenated onto: the next
    commit must physically truncate it away first, so the ledger file, read back afterward,
    contains exactly the original entry plus the new one -- never a corrupted merge of the two."""

    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-A", body)

    ledger_path = _ledger_path(tmp_path, project_id)
    with ledger_path.open("ab") as stream:
        stream.write(b'{"kind": "work_time_coordination_open", "id": "torn-partial-wri')
    assert not ledger_path.read_bytes().endswith(b"\n")

    new_body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-NEW", "value": 2}
    committed = _commit_singleton(
        s, project_id, "work_time_coordination_open", "WTC-OPEN-NEW", new_body
    )
    assert committed == new_body

    raw = ledger_path.read_bytes()
    assert raw.endswith(b"\n")
    lines = [line for line in raw.split(b"\n") if line]
    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["id"] == "WTC-OPEN-A"
    assert parsed[1]["id"] == "WTC-OPEN-NEW"
    assert (
        s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A")
        == body
    )
    assert (
        s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-NEW")
        == new_body
    )


def test_recover_coordination_ledger_also_heals_a_torn_tail(tmp_path: Path) -> None:
    s, project_id, _ = _bounded_project(tmp_path)
    body = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1}
    _commit_singleton(s, project_id, "work_time_coordination_open", "WTC-OPEN-A", body)

    ledger_path = _ledger_path(tmp_path, project_id)
    with ledger_path.open("ab") as stream:
        stream.write(b'{"partial": "fragm')
    assert not ledger_path.read_bytes().endswith(b"\n")

    s.recover_coordination_ledger(project_id)
    assert ledger_path.read_bytes().endswith(b"\n")
    lines = [line for line in ledger_path.read_bytes().split(b"\n") if line]
    assert len(lines) == 1
    assert (
        s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-A")
        == body
    )


def test_a_genuinely_malformed_non_trailing_line_is_still_treated_as_corruption(
    tmp_path: Path,
) -> None:
    """Only the ledger file's own *final* line can ever be a torn write under an append-only
    file -- a malformed *earlier* line is genuine corruption and must still be refused."""

    s, project_id, _ = _bounded_project(tmp_path)
    _commit_singleton(
        s,
        project_id,
        "work_time_coordination_open",
        "WTC-OPEN-A",
        {"kind": "work_time_coordination_open", "id": "WTC-OPEN-A", "value": 1},
    )
    _commit_singleton(
        s,
        project_id,
        "work_time_coordination_open",
        "WTC-OPEN-B",
        {"kind": "work_time_coordination_open", "id": "WTC-OPEN-B", "value": 2},
    )

    ledger_path = _ledger_path(tmp_path, project_id)
    lines = ledger_path.read_bytes().split(b"\n")
    lines = [line for line in lines if line]
    assert len(lines) == 2
    lines[0] = b"{not-valid-json-at-all"
    ledger_path.write_bytes(b"\n".join(lines) + b"\n")

    with pytest.raises(CorruptStoreError):
        s.resolve_coordination_record(project_id, "work_time_coordination_open", "WTC-OPEN-B")
