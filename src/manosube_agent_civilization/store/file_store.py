"""Append-only-lineage authoritative filesystem State Store."""

from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
from typing import Any, Iterator, Mapping

from manosube_agent_civilization.state.canonicalize import _validate, canonical_json_bytes, canonical_semantic_state_bytes
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from .atomic_write import atomic_write, fsync_directory
from .errors import AlreadyInitializedError, BoundaryError, CorruptStoreError, RevisionError, StaleStateError, TransactionConflictError
from .interface import FaultInjector

STAGES=("AFTER_JOURNAL_CREATED","AFTER_STAGED_STATE_WRITTEN","AFTER_COMMIT_INTENT","AFTER_LINEAGE_APPEND","BEFORE_CURRENT_REPLACE","AFTER_CURRENT_REPLACE","BEFORE_COMMITTED_MARKER")
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

    def commit(self, project_id: str, expected_revision: int, expected_fingerprint: Mapping[str,str], next_state: Mapping[str,Any], transition: Mapping[str,Any], *, fault: FaultInjector|None=None) -> dict[str,Any]:
        hit=lambda stage: fault(stage) if fault else None
        with self._lock(project_id):
            current=self.reconstruct(project_id); events=self._events(project_id); event=deepcopy(dict(transition)); tx=event["transaction_id"]
            prior=[item for item in events if item["transaction_id"]==tx]
            if prior:
                if canonical_json_bytes(prior[0])!=canonical_json_bytes(event): raise TransactionConflictError(tx)
                atomic_write(self._current(project_id),canonical_json_bytes(prior[0]["after_state"])); return deepcopy(prior[0]["after_state"])
            if current["state_revision"]!=expected_revision or current["semantic_fingerprint"]!=dict(expected_fingerprint): raise StaleStateError("CAS mismatch")
            state=self._validate_state(project_id,next_state); self._verify_event(project_id,event,current)
            journal=self._project(project_id)/"state"/"recovery"/tx; journal.mkdir(parents=True,exist_ok=False)
            atomic_write(journal/"event.json",canonical_json_bytes(event)); hit(STAGES[0])
            atomic_write(journal/"state.json",canonical_json_bytes(state)); hit(STAGES[1])
            atomic_write(journal/"COMMIT_INTENT",b"1"); hit(STAGES[2])
            self._append(project_id,event); hit(STAGES[3]); hit(STAGES[4])
            atomic_write(self._current(project_id),canonical_json_bytes(state)); hit(STAGES[5]); hit(STAGES[6])
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
                    atomic_write(journal/"COMMITTED",b"1")
            state=self.reconstruct(project_id); atomic_write(self._current(project_id),canonical_json_bytes(state)); return state
