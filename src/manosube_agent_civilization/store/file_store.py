"""Append-only-lineage authoritative filesystem State Store."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
from typing import Any

from manosube_agent_civilization.state.canonicalize import (
    _validate,
    canonical_json_bytes,
    canonical_semantic_state_bytes,
)
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state

from .atomic_write import atomic_write, fsync_directory
from .errors import (
    AlreadyInitializedError,
    BoundaryError,
    CorruptStoreError,
    RecordConflictError,
    RevisionError,
    StaleStateError,
    TransactionConflictError,
)
from .interface import FaultInjector

STAGES=("AFTER_JOURNAL_CREATED","AFTER_STAGED_STATE_WRITTEN","AFTER_STAGED_RECORDS_WRITTEN","AFTER_COMMIT_INTENT","AFTER_LINEAGE_APPEND","AFTER_RECORDS_PROMOTED","BEFORE_CURRENT_REPLACE","AFTER_CURRENT_REPLACE","BEFORE_COMMITTED_MARKER")
TRANSITION_SCHEMA_ID="https://schemas.manosube.org/agent-civilization-os/v0.1/state/state_transition.schema.json"

class FileStateStore:
    def __init__(self, root: Path, *, schema_root: Path) -> None:
        self.root=root.resolve(); self.schema_root=schema_root.resolve()
        if self.root == Path.cwd().resolve() or self.root.is_relative_to(Path.cwd().resolve()):
            raise BoundaryError("backend root must be outside the repository working tree")
        self.root.mkdir(parents=True,exist_ok=True)
        if self.root.is_symlink(): raise BoundaryError("symlink backend root is prohibited")

    def _project(self, project_id: str) -> Path:
        if not project_id or "/" in project_id or ".." in project_id: raise BoundaryError("invalid project identity")
        path=(self.root/"projects"/project_id).resolve()
        if not path.is_relative_to(self.root): raise BoundaryError("project path escapes backend")
        return path

    @contextmanager
    def _lock(self, project_id: str) -> Iterator[None]:
        path=self._project(project_id)/"locks"/"store.lock"; path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("a+b") as stream:
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(stream.fileno(),fcntl.LOCK_UN)

    def _validate_state(self, project_id: str, state: Mapping[str,Any]) -> dict[str,Any]:
        canonical_semantic_state_bytes(state,schema_root=self.schema_root)
        value=deepcopy(dict(state)); actual=fingerprint_project_state(value,schema_root=self.schema_root).as_dict()
        if value["project_id"] != project_id or value["semantic_fingerprint"] != actual: raise CorruptStoreError("state identity or fingerprint mismatch")
        return value

    def _lineage(self, project_id: str) -> Path: return self._project(project_id)/"events"/"transitions.jsonl"
    def _current(self, project_id: str) -> Path: return self._project(project_id)/"state"/"current.json"

    def _record_kind_dir(self, project_id: str, kind: str) -> Path:
        if not kind or "/" in kind or ".." in kind: raise BoundaryError("invalid record kind")
        return self._project(project_id)/"records"/kind

    def _record_path(self, project_id: str, kind: str, record_id: str) -> Path:
        if not record_id or "/" in record_id or ".." in record_id: raise BoundaryError("invalid record identity")
        return self._record_kind_dir(project_id,kind)/f"{record_id}.json"

    def resolve_record(self, project_id: str, kind: str, record_id: str) -> dict[str,Any]|None:
        """Return the immutable committed record of *kind* addressed by *record_id*, or ``None``.

        Only records a completed transaction actually promoted are ever returned -- a
        staged-but-uncommitted journal entry is not canonical and is never visible here.
        """

        path=self._record_path(project_id,kind,record_id)
        if not path.exists(): return None
        try: return json.loads(path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: raise CorruptStoreError(f"malformed record: {kind}/{record_id}") from exc

    def resolve_transaction(self, project_id: str, transaction_id: str) -> dict[str,Any]|None:
        """Return the committed ``state_transition`` event named by *transaction_id*, or
        ``None`` -- R6-F1/R6-F4: a public read path over the existing append-only lineage
        log itself, not a second persistence location. A ``state_transition`` reference
        (``{"kind": "state_transition", "id": tx}``, minted by ``reflow/identity.py``'s
        ``transaction_id`` and published on the Completion Record, the lifecycle event, and
        every committed State's own ``lineage_head_ref``) resolves through here, the same
        way any other record kind resolves through :meth:`resolve_record` -- except the body
        already lives in the lineage log every commit already appends to, so this only reads
        it back, never writes a duplicate copy anywhere.

        Only an event whose own transaction actually reached the lineage log is ever
        returned -- the same durability guarantee :meth:`reconstruct` relies on: a
        transaction that crashed before ``AFTER_LINEAGE_APPEND`` never appears here, exactly
        as it never contributes a State revision.
        """

        for event in self._events(project_id):
            if event.get("transaction_id")==transaction_id: return deepcopy(event)
        return None

    def _events(self, project_id: str) -> list[dict[str,Any]]:
        path=self._lineage(project_id)
        if not path.exists(): return []
        try: return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        except (OSError,json.JSONDecodeError) as exc: raise CorruptStoreError("malformed lineage") from exc

    def _verify_event(self, project_id: str, event: Mapping[str,Any], prior: Mapping[str,Any]|None) -> dict[str,Any]:
        _validate(event,TRANSITION_SCHEMA_ID,self.schema_root)
        state=self._validate_state(project_id,event["after_state"]); fp=state["semantic_fingerprint"]
        if event["project_id"]!=project_id or event["after_fingerprint"]!=fp or event["to_revision"]!=state["state_revision"]: raise CorruptStoreError("event/state mismatch")
        if prior is None:
            if event["event_type"]!="GENESIS" or event["from_revision"] is not None or event["before_fingerprint"] is not None or event["to_revision"]!=0: raise RevisionError("invalid genesis")
        else:
            if event["event_type"]!="TRANSITION" or event["from_revision"]!=prior["state_revision"] or event["to_revision"]!=prior["state_revision"]+1 or event["before_fingerprint"]!=prior["semantic_fingerprint"] or state["previous_state_fingerprint"]!=prior["semantic_fingerprint"]: raise RevisionError("non-contiguous transition")
        return state

    def initialize(self, project_id: str, initial_state: Mapping[str,Any]) -> dict[str,Any]:
        with self._lock(project_id):
            if self._lineage(project_id).exists(): raise AlreadyInitializedError(project_id)
            state=self._validate_state(project_id,initial_state)
            if state["state_revision"]!=0 or state["previous_state_fingerprint"] is not None: raise RevisionError("initial revision must be zero")
            event={"schema_version":"0.1","transaction_id":"TX-GENESIS","event_type":"GENESIS","project_id":project_id,"from_revision":None,"to_revision":0,"before_fingerprint":None,"after_fingerprint":state["semantic_fingerprint"],"after_state":state,"evidence_refs":[],"committed_at":state["state_metadata"]["recorded_at"]}
            self._verify_event(project_id,event,None)
            atomic_write(self._lineage(project_id),canonical_json_bytes(event)+b"\n")
            atomic_write(self._current(project_id),canonical_json_bytes(state))
            return deepcopy(state)

    def reconstruct(self, project_id: str) -> dict[str,Any]:
        prior=None
        for event in self._events(project_id): prior=self._verify_event(project_id,event,prior)
        if prior is None: raise CorruptStoreError("lineage has no genesis")
        return deepcopy(prior)

    def load_current(self, project_id: str) -> dict[str,Any]:
        reconstructed=self.reconstruct(project_id); path=self._current(project_id)
        if not path.exists(): atomic_write(path,canonical_json_bytes(reconstructed))
        try: current=json.loads(path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: raise CorruptStoreError("invalid current view") from exc
        self._validate_state(project_id,current)
        if canonical_json_bytes(current)!=canonical_json_bytes(reconstructed): raise CorruptStoreError("current view differs from lineage")
        return current

    def _append(self, project_id: str, event: Mapping[str,Any]) -> None:
        path=self._lineage(project_id); path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("ab") as stream: stream.write(canonical_json_bytes(event)+b"\n"); stream.flush(); os.fsync(stream.fileno())
        fsync_directory(path.parent)

    def _stage_records(self, project_id: str, journal: Path, records: list[tuple[str,str,Mapping[str,Any]]]) -> list[tuple[str,str,bytes]]:
        """Return ``(kind, id, canonical_bytes)`` for every record this transaction must
        promote, after a same-ID/different-body conflict pre-check against every record
        already durably committed under a prior transaction.

        A record identical, byte-for-byte, to one already committed is dropped here: it is
        already canonical, and re-staging it would double-write the same immutable file for
        no reason. A duplicate identity *within this one manifest* is rejected the same as a
        conflict with a prior commit -- a transaction cannot stage two different bodies, or
        even two identical stagings, under one (kind, id).

        Every supplied ``(kind, id)`` -- staged fresh or already canonical -- is recorded in
        ``manifest.json``, unconditionally: R2-F3B needs this transaction's full declared
        membership to survive even for keys that needed no fresh file, so a replay can later
        prove the *set* of records this transaction claims, not only the bodies of the ones
        it happened to write.
        """

        staged: list[tuple[str,str,bytes]] = []
        seen: set[tuple[str,str]] = set()
        for kind, record_id, body in records:
            key=(kind,record_id)
            if key in seen: raise RecordConflictError(f"{kind}/{record_id}")
            seen.add(key)
            canonical=canonical_json_bytes(body)
            existing=self._record_path(project_id,kind,record_id)
            if existing.exists():
                if existing.read_bytes()!=canonical: raise RecordConflictError(f"{kind}/{record_id}")
                continue
            staged.append((kind,record_id,canonical))
        journal_records=journal/"records"
        for kind, record_id, canonical in staged:
            atomic_write(journal_records/f"{kind}__{record_id}.json",canonical)
        atomic_write(journal/"manifest.json",canonical_json_bytes([[kind,record_id] for kind,record_id in sorted(seen)]))
        return staged

    def _transaction_manifest_keys(self, project_id: str, tx: str) -> set[tuple[str,str]]:
        """Return the exact ``(kind, id)`` set a *committed* transaction's manifest claims.

        Read from the transaction's own recovery journal, which is never deleted -- the
        same durable record :meth:`recover` already relies on to finish or discard an
        interrupted commit. Absent for a transaction committed before this manifest tracking
        existed (or one that admitted no records at all), in which case the set is empty.
        """

        path=self._project(project_id)/"state"/"recovery"/tx/"manifest.json"
        if not path.exists(): return set()
        try: entries=json.loads(path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: raise CorruptStoreError(f"malformed transaction manifest: {tx}") from exc
        return {(kind,record_id) for kind,record_id in entries}

    def _promote_staged_records(self, project_id: str, journal: Path) -> None:
        records_dir=journal/"records"
        if not records_dir.exists(): return
        for path in sorted(records_dir.iterdir()):
            kind, _, record_id = path.stem.partition("__")
            canonical=path.read_bytes()
            target=self._record_path(project_id,kind,record_id)
            if target.exists():
                if target.read_bytes()!=canonical: raise CorruptStoreError(f"staged record diverges from committed: {kind}/{record_id}")
                continue
            atomic_write(target,canonical)

    def commit(self, project_id: str, expected_revision: int, expected_fingerprint: Mapping[str,str], next_state: Mapping[str,Any], transition: Mapping[str,Any], *, records: list[tuple[str,str,Mapping[str,Any]]]|None=None, fault: FaultInjector|None=None) -> dict[str,Any]:
        hit=lambda stage: fault(stage) if fault else None
        with self._lock(project_id):
            current=self.reconstruct(project_id); events=self._events(project_id); event=deepcopy(dict(transition)); tx=event["transaction_id"]
            prior=[item for item in events if item["transaction_id"]==tx]
            if prior:
                if canonical_json_bytes(prior[0])!=canonical_json_bytes(event): raise TransactionConflictError(tx)
                # R2-F3B: identical replay must also carry the identical record manifest --
                # exact (kind, id) membership, and exact canonical bytes for every member,
                # matched against what this transaction actually committed. A changed,
                # missing, additional or substituted record under the same transaction_id
                # is the same conflict a divergent event already raises on.
                supplied_keys: set[tuple[str,str]] = set()
                for kind, record_id, body in (records or []):
                    key=(kind,record_id)
                    if key in supplied_keys: raise RecordConflictError(f"{kind}/{record_id}")
                    supplied_keys.add(key)
                    committed=self.resolve_record(project_id,kind,record_id)
                    if committed is None or canonical_json_bytes(committed)!=canonical_json_bytes(body):
                        raise TransactionConflictError(tx)
                if supplied_keys!=self._transaction_manifest_keys(project_id,tx): raise TransactionConflictError(tx)
                atomic_write(self._current(project_id),canonical_json_bytes(prior[0]["after_state"])); return deepcopy(prior[0]["after_state"])
            if current["state_revision"]!=expected_revision or current["semantic_fingerprint"]!=dict(expected_fingerprint): raise StaleStateError("CAS mismatch")
            state=self._validate_state(project_id,next_state); self._verify_event(project_id,event,current)
            journal=self._project(project_id)/"state"/"recovery"/tx; journal.mkdir(parents=True,exist_ok=False)
            atomic_write(journal/"event.json",canonical_json_bytes(event)); hit(STAGES[0])
            atomic_write(journal/"state.json",canonical_json_bytes(state)); hit(STAGES[1])
            self._stage_records(project_id,journal,list(records or [])); hit(STAGES[2])
            atomic_write(journal/"COMMIT_INTENT",b"1"); hit(STAGES[3])
            self._append(project_id,event); hit(STAGES[4])
            self._promote_staged_records(project_id,journal); hit(STAGES[5])
            hit(STAGES[6])
            atomic_write(self._current(project_id),canonical_json_bytes(state)); hit(STAGES[7])
            hit(STAGES[8])
            atomic_write(journal/"COMMITTED",b"1")
            return deepcopy(state)

    def recover(self, project_id: str) -> dict[str,Any]:
        with self._lock(project_id):
            recovery=self._project(project_id)/"state"/"recovery"; events=self._events(project_id); txids={e["transaction_id"] for e in events}
            if recovery.exists():
                for journal in sorted(recovery.iterdir()):
                    if not journal.is_dir() or not (journal/"COMMIT_INTENT").exists(): continue
                    event=json.loads((journal/"event.json").read_text(encoding="utf-8"))
                    if event["transaction_id"] not in txids: self._append(project_id,event); txids.add(event["transaction_id"])
                    self._promote_staged_records(project_id,journal)
                    atomic_write(journal/"COMMITTED",b"1")
            state=self.reconstruct(project_id); atomic_write(self._current(project_id),canonical_json_bytes(state)); return state
