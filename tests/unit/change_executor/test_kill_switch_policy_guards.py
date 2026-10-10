"""Signed chain policy and bounded retry controls using a lookup/commit double.

The double records transition plans and reports contention; it is not a durable
Store implementation. Real crash durability remains an integration proof.
"""

from copy import deepcopy

import pytest
from tests.fixtures.change_executor_kill_switch_issuer import (
    issuer_public_key_hex,
    mint_kill_switch_signature,
    wrong_kill_switch_signature,
)
from tests.fixtures.product_binding import bind_project_kwargs

from manosube_agent_civilization.change_executor import kill_switch as switch
from manosube_agent_civilization.change_executor.errors import ChangeExecutorError
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

POINTER = "CHANGE_EXECUTOR_KILL_SWITCH_CURRENT_ID"


def signed_record(project, *, status="ACTIVE", generation=0, predecessor=None):
    record = {
        "schema_version": "0.1",
        "project_id": project,
        "status": status,
        "generation": generation,
        "predecessor_ref": predecessor,
    }
    record["change_executor_kill_switch_id"] = switch.kill_switch_id(record)
    record["change_executor_kill_switch_semantic_fingerprint"] = (
        switch.kill_switch_semantic_fingerprint(record)
    )
    record["signature"] = mint_kill_switch_signature(switch.kill_switch_signing_payload(record))
    return record


class PlanStore:
    def __init__(self):
        self.state = bind_project_kwargs()["genesis_state"]
        self.records = {}
        self.failures = []
        self.attempts = 0

    def current(self, record):
        self.records[record["change_executor_kill_switch_id"]] = deepcopy(record)
        self.state["semantic_state"]["deployment"]["claims"][POINTER] = record[
            "change_executor_kill_switch_id"
        ]
        self.state["semantic_fingerprint"] = fingerprint_project_state(self.state).as_dict()

    def load_current(self, project):
        return deepcopy(self.state)

    read_current_consistent = load_current

    def resolve_record(self, project, kind, record_id):
        return deepcopy(self.records.get(record_id))

    def commit(
        self,
        project,
        expected_revision,
        expected_fingerprint,
        next_state,
        transition,
        *,
        records,
        fault,
    ):
        self.attempts += 1
        if self.failures:
            raise self.failures.pop(0)
        assert expected_revision == self.state["state_revision"]
        assert expected_fingerprint == self.state["semantic_fingerprint"]
        assert next_state["state_revision"] == expected_revision + 1
        assert next_state["semantic_fingerprint"] == fingerprint_project_state(next_state).as_dict()
        assert transition["after_state"] == next_state
        self.state = deepcopy(next_state)
        for kind, record_id, record in records:
            assert kind == "change_executor_kill_switch"
            self.records[record_id] = deepcopy(record)
        return deepcopy(next_state)


def commit(store, record, *, key=None, instant="2026-09-10T00:00:01Z"):
    return switch.commit_change_executor_kill_switch(
        store,
        store.state["project_id"],
        record,
        trust_anchor_public_key_hex=issuer_public_key_hex() if key is None else key,
        committed_at=instant,
    )


def test_genuine_signed_genesis_then_successor_retains_the_one_pointer():
    store = PlanStore()
    first = signed_record(store.state["project_id"])
    assert commit(store, first)["generation"] == 0
    successor = signed_record(
        store.state["project_id"],
        generation=1,
        predecessor={
            "kind": "change_executor_kill_switch",
            "id": first["change_executor_kill_switch_id"],
        },
    )
    result = commit(store, successor)
    assert result["generation"] == 1 and store.attempts == 2
    assert (
        switch.require_active_kill_switch(store, store.state["project_id"], stage="unit")
        == successor
    )


@pytest.mark.parametrize("bad", [None, [], {"deployment": None}, {"deployment": {"claims": None}}])
def test_unreadable_pointer_state_never_opens_execution(bad):
    store = PlanStore()
    store.state["semantic_state"] = bad
    with pytest.raises(ChangeExecutorError):
        switch.require_active_kill_switch(store, store.state["project_id"], stage="unit")
    assert store.attempts == 0


@pytest.mark.parametrize("bad", [None, [], {"deployment": None}, {"deployment": {"claims": None}}])
def test_unreadable_successor_state_never_reaches_commit(bad):
    store = PlanStore()
    record = signed_record(store.state["project_id"])
    store.state["semantic_state"] = bad
    with pytest.raises(ChangeExecutorError):
        commit(store, record)
    assert store.attempts == 0


def test_a_dangling_current_pointer_cannot_be_rotated():
    store = PlanStore()
    store.state["semantic_state"]["deployment"]["claims"][POINTER] = "EXEC-KILLSWITCH-" + "F" * 64
    with pytest.raises(ChangeExecutorError):
        commit(store, signed_record(store.state["project_id"]))
    with pytest.raises(ChangeExecutorError):
        switch.require_active_kill_switch(store, store.state["project_id"], stage="unit")
    assert store.attempts == 0


@pytest.mark.parametrize("field", ["project_id", "status", "generation", "predecessor_ref"])
def test_no_semantic_identity_is_minted_from_an_incomplete_record(field):
    record = signed_record("PRJ-UNIT")
    del record[field]
    with pytest.raises(ChangeExecutorError):
        switch.kill_switch_id(record)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("change_executor_kill_switch_id", "EXEC-KILLSWITCH-" + "F" * 64),
        ("change_executor_kill_switch_semantic_fingerprint", "sha256:" + "f" * 64),
        ("generation", "not-a-generation"),
    ],
)
def test_inconsistent_or_schema_invalid_current_record_is_refused(field, bad):
    store = PlanStore()
    record = signed_record(store.state["project_id"])
    store.current(record)
    store.records[record["change_executor_kill_switch_id"]][field] = bad
    with pytest.raises(ChangeExecutorError):
        switch.require_active_kill_switch(store, store.state["project_id"], stage="unit")
    assert store.attempts == 0


@pytest.mark.parametrize("key", ["", 0, [], "00" * 32])
def test_missing_or_foreign_trust_anchor_never_commits(key):
    store = PlanStore()
    with pytest.raises(ChangeExecutorError):
        commit(store, signed_record(store.state["project_id"]), key=key)
    assert store.attempts == 0


def test_a_real_signature_from_a_different_key_is_refused():
    store = PlanStore()
    record = signed_record(store.state["project_id"])
    record["signature"] = wrong_kill_switch_signature(switch.kill_switch_signing_payload(record))
    with pytest.raises(ChangeExecutorError):
        commit(store, record)
    assert store.attempts == 0


@pytest.mark.parametrize("instant", [None, "", 0])
def test_no_implicit_commit_instant_is_invented(instant):
    store = PlanStore()
    with pytest.raises(ChangeExecutorError):
        commit(store, signed_record(store.state["project_id"]), instant=instant)
    assert store.attempts == 0


@pytest.mark.parametrize(
    "failures,expected_attempts",
    [
        ([StaleStateError("contention")], 2),
        ([StaleStateError("contention")] * 8, 8),
        ([RecordConflictError("foreign record")], 1),
    ],
)
def test_contention_is_bounded_and_record_conflicts_are_not_reported_as_success(
    failures, expected_attempts
):
    store = PlanStore()
    store.failures = list(failures)
    record = signed_record(store.state["project_id"])
    before = deepcopy(store.state)
    if expected_attempts == 2:
        result = commit(store, record)
        assert result["generation"] == 0
        assert store.state["state_revision"] == before["state_revision"] + 1
    else:
        with pytest.raises(ChangeExecutorError):
            commit(store, record)
        assert store.state == before and store.records == {}
    assert store.attempts == expected_attempts


@pytest.mark.parametrize(
    "status,generation,predecessor,current",
    [
        ("REVOKED", 0, None, None),
        ("ACTIVE", 1, None, None),
        (
            "ACTIVE",
            0,
            {"kind": "change_executor_kill_switch", "id": "EXEC-KILLSWITCH-" + "F" * 64},
            None,
        ),
        ("ACTIVE", 0, None, "ACTIVE"),
        ("ACTIVE", 0, None, "REVOKED"),
        ("ACTIVE", 4, "current", "ACTIVE"),
        (
            "ACTIVE",
            1,
            {"kind": "change_executor_kill_switch", "id": "EXEC-KILLSWITCH-" + "F" * 64},
            "ACTIVE",
        ),
    ],
)
def test_genesis_successor_and_revocation_rules_cannot_be_bypassed(
    status, generation, predecessor, current
):
    store = PlanStore()
    if current:
        genesis = signed_record(store.state["project_id"])
        store.current(genesis)
        prior = signed_record(
            store.state["project_id"],
            status=current,
            generation=1,
            predecessor={
                "kind": "change_executor_kill_switch",
                "id": genesis["change_executor_kill_switch_id"],
            },
        )
        store.current(prior)
        if predecessor == "current":
            predecessor = {
                "kind": "change_executor_kill_switch",
                "id": prior["change_executor_kill_switch_id"],
            }
    record = signed_record(
        store.state["project_id"], status=status, generation=generation, predecessor=predecessor
    )
    with pytest.raises(ChangeExecutorError):
        commit(store, record)
    assert store.attempts == 0


def test_replaying_the_current_signed_record_does_not_commit_again():
    store = PlanStore()
    record = signed_record(store.state["project_id"])
    commit(store, record)
    before = deepcopy(store.state)
    result = commit(store, record)
    assert result["committed_state"] is None
    assert store.state == before and store.attempts == 1


def test_a_legally_revoked_pointer_cannot_open_execution():
    store = PlanStore()
    genesis = signed_record(store.state["project_id"])
    commit(store, genesis)
    revoked = signed_record(
        store.state["project_id"],
        status="REVOKED",
        generation=1,
        predecessor={
            "kind": "change_executor_kill_switch",
            "id": genesis["change_executor_kill_switch_id"],
        },
    )
    commit(store, revoked)
    with pytest.raises(ChangeExecutorError):
        switch.require_active_kill_switch(store, store.state["project_id"], stage="unit")
    assert store.attempts == 2
