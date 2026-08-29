from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import threading
import pytest

from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore, STAGES
from manosube_agent_civilization.store.errors import BoundaryError, SimulatedCrash, StaleStateError, TransactionConflictError
from tests.state_helpers import SCHEMA_ROOT, initial_state

def prepared_initial() -> dict:
    state=initial_state(); state["semantic_fingerprint"]=fingerprint_project_state(state,schema_root=SCHEMA_ROOT).as_dict(); return state

def successor(before: dict, tx: str="TX-0001") -> tuple[dict,dict]:
    state=deepcopy(before); state["state_revision"]=before["state_revision"]+1; state["previous_state_fingerprint"]=before["semantic_fingerprint"]; state["lineage_head_ref"]={"kind":"transition","id":tx}; state["semantic_state"]["code"]["status"]="KNOWN"; state["semantic_fingerprint"]=fingerprint_project_state(state,schema_root=SCHEMA_ROOT).as_dict()
    event={"schema_version":"0.1","transaction_id":tx,"event_type":"TRANSITION","project_id":state["project_id"],"from_revision":before["state_revision"],"to_revision":state["state_revision"],"before_fingerprint":before["semantic_fingerprint"],"after_fingerprint":state["semantic_fingerprint"],"after_state":state,"evidence_refs":[],"committed_at":"2026-08-29T10:00:00Z"}
    return state,event

def store(tmp_path: Path) -> FileStateStore: return FileStateStore(tmp_path/"backend",schema_root=SCHEMA_ROOT)

def test_round_trip_and_lineage_only_reconstruction(tmp_path: Path) -> None:
    s=store(tmp_path); initial=prepared_initial(); s.initialize("PRJ-0001",initial); after,event=successor(initial); s.commit("PRJ-0001",0,initial["semantic_fingerprint"],after,event)
    assert s.load_current("PRJ-0001")==after
    (tmp_path/"backend/projects/PRJ-0001/state/current.json").unlink()
    assert s.recover("PRJ-0001")==after

def test_stale_cas_changes_nothing(tmp_path: Path) -> None:
    s=store(tmp_path); initial=prepared_initial(); s.initialize("PRJ-0001",initial); after,event=successor(initial)
    lineage=(tmp_path/"backend/projects/PRJ-0001/events/transitions.jsonl").read_bytes()
    with pytest.raises(StaleStateError): s.commit("PRJ-0001",99,initial["semantic_fingerprint"],after,event)
    assert (tmp_path/"backend/projects/PRJ-0001/events/transitions.jsonl").read_bytes()==lineage

def test_duplicate_transaction_is_idempotent_and_conflict_rejected(tmp_path: Path) -> None:
    s=store(tmp_path); initial=prepared_initial(); s.initialize("PRJ-0001",initial); after,event=successor(initial); s.commit("PRJ-0001",0,initial["semantic_fingerprint"],after,event)
    assert s.commit("PRJ-0001",0,initial["semantic_fingerprint"],after,event)==after
    conflict=deepcopy(event); conflict["committed_at"]="2026-08-29T10:00:01Z"
    with pytest.raises(TransactionConflictError): s.commit("PRJ-0001",0,initial["semantic_fingerprint"],after,conflict)
    assert len(s._events("PRJ-0001"))==2

@pytest.mark.parametrize("stage",STAGES)
def test_every_crash_point_converges(stage: str,tmp_path: Path) -> None:
    s=store(tmp_path); initial=prepared_initial(); s.initialize("PRJ-0001",initial); after,event=successor(initial)
    def fault(current: str) -> None:
        if current==stage: raise SimulatedCrash(stage)
    with pytest.raises(SimulatedCrash): s.commit("PRJ-0001",0,initial["semantic_fingerprint"],after,event,fault=fault)
    recovered=s.recover("PRJ-0001")
    assert recovered == (initial if stage in STAGES[:2] else after)
    assert len(s._events("PRJ-0001")) in {1,2}

def test_competing_cas_has_one_winner(tmp_path: Path) -> None:
    s=store(tmp_path); initial=prepared_initial(); s.initialize("PRJ-0001",initial); results=[]
    def run(index: int) -> None:
        state,event=successor(initial,f"TX-000{index}")
        try: s.commit("PRJ-0001",0,initial["semantic_fingerprint"],state,event); results.append("WIN")
        except StaleStateError: results.append("STALE")
    threads=[threading.Thread(target=run,args=(i,)) for i in (1,2)]
    for t in threads:t.start()
    for t in threads:t.join()
    assert sorted(results)==["STALE","WIN"]

def test_repository_root_is_rejected() -> None:
    with pytest.raises(BoundaryError): FileStateStore(Path.cwd(),schema_root=SCHEMA_ROOT)
