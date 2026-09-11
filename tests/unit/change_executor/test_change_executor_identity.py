"""V1 (Issue #73): deterministic Change Executor identity + schema round-trip proof.

Pure-function proof of :mod:`manosube_agent_civilization.change_executor.identity` and
:mod:`manosube_agent_civilization.change_executor.kill_switch` -- no Store, no Boot, no adapter.
Proves every id/fingerprint function is a deterministic pure function of its declared semantic
fields, sensitive to *each* field individually (parametrized over every member of
``EXECUTION_INTENT_SEMANTIC_FIELDS``/``EXECUTION_ATTEMPT_SEMANTIC_FIELDS``/
``CHANGE_EXECUTION_RECEIPT_SEMANTIC_FIELDS``/``KILL_SWITCH_SEMANTIC_FIELDS``), that
``execution_mapping_slot_key`` depends on exactly ``(change_id, execution_boundary_fingerprint,
adapter_identity_fingerprint)`` and nothing else, and that every record ``engine.py``'s builders
produce validates cleanly against its own canonical JSON Schema.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from manosube_agent_civilization.change_executor.boundary import (
    CHANGE_EXECUTOR_SCHEMA_BASE,
    execution_boundary_fingerprint,
    validate_execution_boundary,
)
from manosube_agent_civilization.change_executor.engine import (
    build_change_execution_receipt,
    build_execution_attempt,
    build_execution_intent,
)
from manosube_agent_civilization.change_executor.identity import (
    CHANGE_EXECUTION_RECEIPT_SEMANTIC_FIELDS,
    EXECUTION_ATTEMPT_SEMANTIC_FIELDS,
    EXECUTION_INTENT_SEMANTIC_FIELDS,
    change_execution_receipt_id,
    change_execution_receipt_semantic_fingerprint,
    execution_attempt_id,
    execution_attempt_semantic_fingerprint,
    execution_intent_id,
    execution_intent_semantic_fingerprint,
    execution_mapping_slot_key,
)
from manosube_agent_civilization.change_executor.kill_switch import (
    KILL_SWITCH_SEMANTIC_FIELDS,
    kill_switch_id,
    kill_switch_semantic_fingerprint,
)
from manosube_agent_civilization.difference.validation import validate_record

# --------------------------------------------------------------------------------------- #
# execution_intent
# --------------------------------------------------------------------------------------- #

_CHANGE_REF_A: dict[str, str] = {"kind": "change", "id": "CHANGE-" + "A" * 64}
_CHANGE_REF_B: dict[str, str] = {"kind": "change", "id": "CHANGE-" + "B" * 64}

BASE_INTENT: dict[str, Any] = {
    "project_id": "PRJ-CE-0001",
    "change_ref": dict(_CHANGE_REF_A),
    "execution_boundary_fingerprint": "sha256:" + "1" * 64,
    "adapter_identity_fingerprint": "sha256:" + "2" * 64,
    "claim_token": "claim-alpha",
    "requested_at": "2026-09-10T00:00:00Z",
}

VARIANTS_INTENT: dict[str, Any] = {
    "project_id": "PRJ-CE-0002",
    "change_ref": dict(_CHANGE_REF_B),
    "execution_boundary_fingerprint": "sha256:" + "3" * 64,
    "adapter_identity_fingerprint": "sha256:" + "4" * 64,
    "claim_token": "claim-beta",
    "requested_at": "2026-09-10T00:00:01Z",
}

assert set(BASE_INTENT) == set(EXECUTION_INTENT_SEMANTIC_FIELDS)
assert set(VARIANTS_INTENT) == set(EXECUTION_INTENT_SEMANTIC_FIELDS)


def test_execution_intent_semantic_fingerprint_is_deterministic() -> None:
    first = execution_intent_semantic_fingerprint(BASE_INTENT)
    second = execution_intent_semantic_fingerprint(deepcopy(BASE_INTENT))
    assert first == second
    assert first.startswith("sha256:")


@pytest.mark.parametrize("field", sorted(EXECUTION_INTENT_SEMANTIC_FIELDS))
def test_execution_intent_semantic_fingerprint_is_sensitive_to_each_field(field: str) -> None:
    baseline_fp = execution_intent_semantic_fingerprint(BASE_INTENT)
    mutated = deepcopy(BASE_INTENT)
    mutated[field] = deepcopy(VARIANTS_INTENT[field])
    mutated_fp = execution_intent_semantic_fingerprint(mutated)
    assert mutated_fp != baseline_fp, f"changing {field!r} alone did not change the fingerprint"


def test_execution_intent_id_is_deterministic() -> None:
    assert execution_intent_id(BASE_INTENT) == execution_intent_id(deepcopy(BASE_INTENT))


@pytest.mark.parametrize("field", ("project_id", "claim_token", "requested_at"))
def test_execution_intent_id_is_insensitive_to_non_slot_fields(field: str) -> None:
    """The mapping-slot id depends on exactly ``change_ref``/``execution_boundary_fingerprint``/
    ``adapter_identity_fingerprint`` -- changing anything else must not move it."""

    baseline_id = execution_intent_id(BASE_INTENT)
    mutated = deepcopy(BASE_INTENT)
    mutated[field] = deepcopy(VARIANTS_INTENT[field])
    assert execution_intent_id(mutated) == baseline_id


@pytest.mark.parametrize(
    "field", ("change_ref", "execution_boundary_fingerprint", "adapter_identity_fingerprint")
)
def test_execution_intent_id_is_sensitive_to_each_slot_field(field: str) -> None:
    baseline_id = execution_intent_id(BASE_INTENT)
    mutated = deepcopy(BASE_INTENT)
    mutated[field] = deepcopy(VARIANTS_INTENT[field])
    assert execution_intent_id(mutated) != baseline_id


# --------------------------------------------------------------------------------------- #
# execution_mapping_slot_key -- proven directly, and cross-checked against execution_intent_id.
# --------------------------------------------------------------------------------------- #


def test_execution_mapping_slot_key_is_deterministic() -> None:
    first = execution_mapping_slot_key(
        "CHANGE-" + "A" * 64, "sha256:" + "1" * 64, "sha256:" + "2" * 64
    )
    second = execution_mapping_slot_key(
        "CHANGE-" + "A" * 64, "sha256:" + "1" * 64, "sha256:" + "2" * 64
    )
    assert first == second
    assert first.startswith("EXEC-SLOT-")


def test_execution_mapping_slot_key_depends_on_exactly_the_three_declared_inputs() -> None:
    baseline = execution_mapping_slot_key(
        "CHANGE-" + "A" * 64, "sha256:" + "1" * 64, "sha256:" + "2" * 64
    )
    assert (
        execution_mapping_slot_key("CHANGE-" + "B" * 64, "sha256:" + "1" * 64, "sha256:" + "2" * 64)
        != baseline
    )
    assert (
        execution_mapping_slot_key("CHANGE-" + "A" * 64, "sha256:" + "3" * 64, "sha256:" + "2" * 64)
        != baseline
    )
    assert (
        execution_mapping_slot_key("CHANGE-" + "A" * 64, "sha256:" + "1" * 64, "sha256:" + "4" * 64)
        != baseline
    )


def test_execution_mapping_slot_key_never_depends_on_claim_token_or_requested_at() -> None:
    """Two callers proposing the identical (change, Boundary, adapter) triple, under different
    ``claim_token``/``requested_at`` values, must collide at the identical slot -- the exact
    concurrency-barrier property ``identity.py``'s own module docstring names as load-bearing."""

    first = execution_mapping_slot_key(
        _CHANGE_REF_A["id"],
        BASE_INTENT["execution_boundary_fingerprint"],
        BASE_INTENT["adapter_identity_fingerprint"],
    )
    assert execution_intent_id(BASE_INTENT) == first

    other_caller = deepcopy(BASE_INTENT)
    other_caller["claim_token"] = "an-entirely-different-claim-token"  # noqa: S105
    other_caller["requested_at"] = "2030-01-01T00:00:00Z"
    assert execution_intent_id(other_caller) == first
    # The two records' own *semantic* fingerprints still genuinely differ (full tamper
    # detection is never lost even though the id collides).
    assert execution_intent_semantic_fingerprint(
        other_caller
    ) != execution_intent_semantic_fingerprint(BASE_INTENT)


# --------------------------------------------------------------------------------------- #
# execution_attempt
# --------------------------------------------------------------------------------------- #

_INTENT_ID = execution_intent_id(BASE_INTENT)
_OTHER_INTENT_ID = execution_mapping_slot_key(
    _CHANGE_REF_B["id"], "sha256:" + "3" * 64, "sha256:" + "4" * 64
)

BASE_ATTEMPT: dict[str, Any] = {
    **deepcopy(BASE_INTENT),
    "execution_intent_ref": {"kind": "execution_intent", "id": _INTENT_ID},
    "attempt_nonce": "a" * 32,
}
VARIANTS_ATTEMPT: dict[str, Any] = {
    **deepcopy(VARIANTS_INTENT),
    "execution_intent_ref": {"kind": "execution_intent", "id": _OTHER_INTENT_ID},
    "attempt_nonce": "b" * 32,
}

assert set(BASE_ATTEMPT) == set(EXECUTION_ATTEMPT_SEMANTIC_FIELDS)


def test_execution_attempt_semantic_fingerprint_is_deterministic() -> None:
    assert execution_attempt_semantic_fingerprint(
        BASE_ATTEMPT
    ) == execution_attempt_semantic_fingerprint(deepcopy(BASE_ATTEMPT))


@pytest.mark.parametrize("field", sorted(EXECUTION_ATTEMPT_SEMANTIC_FIELDS))
def test_execution_attempt_semantic_fingerprint_is_sensitive_to_each_field(field: str) -> None:
    baseline_fp = execution_attempt_semantic_fingerprint(BASE_ATTEMPT)
    mutated = deepcopy(BASE_ATTEMPT)
    mutated[field] = deepcopy(VARIANTS_ATTEMPT[field])
    assert execution_attempt_semantic_fingerprint(mutated) != baseline_fp


def test_execution_attempt_id_equals_the_identical_slot_key_execution_intent_id_computes() -> None:
    assert execution_attempt_id(BASE_ATTEMPT) == execution_intent_id(BASE_INTENT) == _INTENT_ID


@pytest.mark.parametrize(
    "field", ("claim_token", "requested_at", "execution_intent_ref", "attempt_nonce")
)
def test_execution_attempt_id_is_insensitive_to_non_slot_fields(field: str) -> None:
    baseline_id = execution_attempt_id(BASE_ATTEMPT)
    mutated = deepcopy(BASE_ATTEMPT)
    mutated[field] = deepcopy(VARIANTS_ATTEMPT[field])
    assert execution_attempt_id(mutated) == baseline_id


# --------------------------------------------------------------------------------------- #
# change_execution_receipt
# --------------------------------------------------------------------------------------- #

_SLOT_KEY = _INTENT_ID

BASE_RECEIPT: dict[str, Any] = {
    "change_ref": dict(_CHANGE_REF_A),
    "idempotency_key": "sha256:" + "5" * 64,
    "authority_ref": {"kind": "authority_decision", "id": "AUTH-DEC-" + "A" * 64},
    "project_id": "PRJ-CE-0001",
    "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-" + "A" * 64},
    "boot_state_fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "a" * 64},
    "execution_boundary_fingerprint": "sha256:" + "1" * 64,
    "executor_identity": "controlled_filesystem_adapter",
    "executor_version": "0.1",
    "target": {"repository": "org/repo", "branch": "main", "worktree_root": "/tmp/worktree-a"},  # noqa: S108
    "operation": {
        "operation_kind": "WRITE_DOCUMENTATION_FILE",
        "file_writes": [{"path": "docs/x.md", "content_utf8": "hello"}],
        "file_deletes": [],
    },
    "execution_started_at": "2026-09-10T00:00:01Z",
    "execution_ended_at": "2026-09-10T00:00:02Z",
    "outcome": "SUCCEEDED",
    "performed_result_fingerprint": "sha256:" + "6" * 64,
    "performed_result_summary": {
        "files_written": ["docs/x.md"],
        "bytes_written": 5,
        "files_deleted": [],
    },
    "rollback_outcome": None,
    "claim_token": "claim-alpha",
    "reobservation_request": {
        "kind": "change_execution_reobservation_request",
        "target": {"repository": "org/repo", "branch": "main", "paths": ["docs/x.md"]},
        "reason_codes": ["AUTONOMOUS_CHANGE_EXECUTION_ATTEMPTED"],
        "requested_at": "2026-09-10T00:00:01Z",
    },
    "independent_after_state_observation": {
        "outcome": "MATCHED",
        "checked_files": [{"path": "docs/x.md", "kind": "write", "status": "MATCHED"}],
    },
}

VARIANTS_RECEIPT: dict[str, Any] = {
    "change_ref": dict(_CHANGE_REF_B),
    "idempotency_key": "sha256:" + "7" * 64,
    "authority_ref": {"kind": "authority_decision", "id": "AUTH-DEC-" + "B" * 64},
    "project_id": "PRJ-CE-0002",
    "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-" + "B" * 64},
    "boot_state_fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "b" * 64},
    "execution_boundary_fingerprint": "sha256:" + "3" * 64,
    "executor_identity": "different_adapter",
    "executor_version": "0.2",
    "target": {"repository": "org/other", "branch": "dev", "worktree_root": "/tmp/worktree-b"},  # noqa: S108
    "operation": {
        "operation_kind": "WRITE_DOCUMENTATION_FILE",
        "file_writes": [{"path": "docs/y.md", "content_utf8": "world"}],
        "file_deletes": [],
    },
    "execution_started_at": "2026-09-10T00:10:01Z",
    "execution_ended_at": "2026-09-10T00:10:02Z",
    "outcome": "PARTIAL_MUTATION",
    "performed_result_fingerprint": "sha256:" + "8" * 64,
    "performed_result_summary": {
        "files_written": ["docs/y.md"],
        "bytes_written": 9,
        "files_deleted": [],
    },
    "rollback_outcome": "NOT_ATTEMPTED",
    "claim_token": "claim-beta",
    "reobservation_request": {
        "kind": "change_execution_reobservation_request",
        "target": {"repository": "org/other", "branch": "dev", "paths": ["docs/y.md"]},
        "reason_codes": ["AUTONOMOUS_CHANGE_EXECUTION_ATTEMPTED"],
        "requested_at": "2026-09-10T00:10:01Z",
    },
    "independent_after_state_observation": {
        "outcome": "MISMATCH",
        "checked_files": [{"path": "docs/y.md", "kind": "write", "status": "MISMATCH"}],
    },
}

assert set(BASE_RECEIPT) == set(CHANGE_EXECUTION_RECEIPT_SEMANTIC_FIELDS)
assert set(VARIANTS_RECEIPT) == set(CHANGE_EXECUTION_RECEIPT_SEMANTIC_FIELDS)


def test_change_execution_receipt_semantic_fingerprint_is_deterministic() -> None:
    assert change_execution_receipt_semantic_fingerprint(
        BASE_RECEIPT
    ) == change_execution_receipt_semantic_fingerprint(deepcopy(BASE_RECEIPT))


@pytest.mark.parametrize("field", sorted(CHANGE_EXECUTION_RECEIPT_SEMANTIC_FIELDS))
def test_change_execution_receipt_semantic_fingerprint_is_sensitive_to_each_field(
    field: str,
) -> None:
    baseline_fp = change_execution_receipt_semantic_fingerprint(BASE_RECEIPT)
    mutated = deepcopy(BASE_RECEIPT)
    mutated[field] = deepcopy(VARIANTS_RECEIPT[field])
    mutated_fp = change_execution_receipt_semantic_fingerprint(mutated)
    assert mutated_fp != baseline_fp, f"changing {field!r} alone did not change the fingerprint"


def test_change_execution_receipt_id_is_always_exactly_execution_request_id() -> None:
    record = {**BASE_RECEIPT, "execution_request_id": _SLOT_KEY}
    assert change_execution_receipt_id(record) == _SLOT_KEY
    other = {**BASE_RECEIPT, "execution_request_id": "EXEC-SLOT-" + "F" * 64}
    assert change_execution_receipt_id(other) == "EXEC-SLOT-" + "F" * 64


# --------------------------------------------------------------------------------------- #
# change_executor_kill_switch
# --------------------------------------------------------------------------------------- #

BASE_KILL_SWITCH: dict[str, Any] = {
    "project_id": "PRJ-CE-0001",
    "status": "ACTIVE",
    "generation": 0,
    "predecessor_ref": None,
}
VARIANTS_KILL_SWITCH: dict[str, Any] = {
    "project_id": "PRJ-CE-0002",
    "status": "REVOKED",
    "generation": 1,
    "predecessor_ref": {"kind": "change_executor_kill_switch", "id": "EXEC-KILLSWITCH-" + "A" * 64},
}

assert set(BASE_KILL_SWITCH) == set(KILL_SWITCH_SEMANTIC_FIELDS)
assert set(VARIANTS_KILL_SWITCH) == set(KILL_SWITCH_SEMANTIC_FIELDS)


def test_kill_switch_semantic_fingerprint_is_deterministic() -> None:
    assert kill_switch_semantic_fingerprint(BASE_KILL_SWITCH) == kill_switch_semantic_fingerprint(
        deepcopy(BASE_KILL_SWITCH)
    )


def test_kill_switch_id_is_deterministic() -> None:
    assert kill_switch_id(BASE_KILL_SWITCH) == kill_switch_id(deepcopy(BASE_KILL_SWITCH))
    assert kill_switch_id(BASE_KILL_SWITCH).startswith("EXEC-KILLSWITCH-")


@pytest.mark.parametrize("field", sorted(KILL_SWITCH_SEMANTIC_FIELDS))
def test_kill_switch_semantic_fingerprint_is_sensitive_to_each_field(field: str) -> None:
    baseline_fp = kill_switch_semantic_fingerprint(BASE_KILL_SWITCH)
    mutated = deepcopy(BASE_KILL_SWITCH)
    mutated[field] = deepcopy(VARIANTS_KILL_SWITCH[field])
    assert kill_switch_semantic_fingerprint(mutated) != baseline_fp, field


@pytest.mark.parametrize("field", sorted(KILL_SWITCH_SEMANTIC_FIELDS))
def test_kill_switch_id_is_sensitive_to_each_field(field: str) -> None:
    baseline_id = kill_switch_id(BASE_KILL_SWITCH)
    mutated = deepcopy(BASE_KILL_SWITCH)
    mutated[field] = deepcopy(VARIANTS_KILL_SWITCH[field])
    assert kill_switch_id(mutated) != baseline_id, field


# --------------------------------------------------------------------------------------- #
# V1's own required schema round-trip: every record engine.py's builders produce validates
# cleanly against its own canonical JSON Schema (independently re-validated here, not merely
# trusted from the builder's own internal call, which this schema check would also catch if
# ever silently removed).
# --------------------------------------------------------------------------------------- #


def test_build_execution_intent_round_trips_through_its_own_schema() -> None:
    change_ref = dict(_CHANGE_REF_A)
    boundary_fp = "sha256:" + "1" * 64
    adapter_fp = "sha256:" + "2" * 64
    record = build_execution_intent(
        project_id="PRJ-CE-0001",
        change_ref=change_ref,
        execution_boundary_fingerprint=boundary_fp,
        adapter_identity_fingerprint=adapter_fp,
        claim_token="claim-alpha",  # noqa: S106
        requested_at="2026-09-10T00:00:00Z",
    )
    validate_record(record, "execution_intent.schema.json", base=CHANGE_EXECUTOR_SCHEMA_BASE)
    assert record["execution_intent_id"] == execution_mapping_slot_key(
        change_ref["id"], boundary_fp, adapter_fp
    )


def test_build_execution_attempt_round_trips_through_its_own_schema() -> None:
    change_ref = dict(_CHANGE_REF_A)
    boundary_fp = "sha256:" + "1" * 64
    adapter_fp = "sha256:" + "2" * 64
    slot_key = execution_mapping_slot_key(change_ref["id"], boundary_fp, adapter_fp)
    record = build_execution_attempt(
        project_id="PRJ-CE-0001",
        change_ref=change_ref,
        execution_boundary_fingerprint=boundary_fp,
        adapter_identity_fingerprint=adapter_fp,
        claim_token="claim-alpha",  # noqa: S106
        requested_at="2026-09-10T00:00:00Z",
        execution_intent_ref={"kind": "execution_intent", "id": slot_key},
        attempt_nonce="f" * 32,
    )
    validate_record(record, "execution_attempt.schema.json", base=CHANGE_EXECUTOR_SCHEMA_BASE)
    assert record["attempt_nonce"] == "f" * 32
    assert record["execution_attempt_id"] == slot_key


def test_build_change_execution_receipt_round_trips_through_its_own_schema() -> None:
    slot_key = execution_mapping_slot_key(
        _CHANGE_REF_A["id"], "sha256:" + "1" * 64, "sha256:" + "2" * 64
    )
    record = build_change_execution_receipt(
        execution_request_id=slot_key,
        change_ref=dict(_CHANGE_REF_A),
        idempotency_key="sha256:" + "5" * 64,
        authority_ref={"kind": "authority_decision", "id": "AUTH-DEC-" + "A" * 64},
        project_id="PRJ-CE-0001",
        project_binding_ref={"kind": "project_binding", "id": "PROJBIND-" + "A" * 64},
        boot_state_fingerprint={"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "a" * 64},
        execution_boundary_fingerprint="sha256:" + "1" * 64,
        executor_identity="controlled_filesystem_adapter",
        executor_version="0.1",
        target={"repository": "org/repo", "branch": "main", "worktree_root": "/tmp/worktree-a"},  # noqa: S108
        operation={
            "operation_kind": "WRITE_DOCUMENTATION_FILE",
            "file_writes": [{"path": "docs/x.md", "content_utf8": "hello"}],
            "file_deletes": [],
        },
        execution_started_at="2026-09-10T00:00:01Z",
        execution_ended_at="2026-09-10T00:00:02Z",
        outcome="SUCCEEDED",
        performed_result_fingerprint="sha256:" + "6" * 64,
        performed_result_summary={
            "files_written": ["docs/x.md"],
            "bytes_written": 5,
            "files_deleted": [],
        },
        rollback_outcome=None,
        claim_token="claim-alpha",  # noqa: S106
        reobservation_request={
            "kind": "change_execution_reobservation_request",
            "target": {"repository": "org/repo", "branch": "main", "paths": ["docs/x.md"]},
            "reason_codes": ["AUTONOMOUS_CHANGE_EXECUTION_ATTEMPTED"],
            "requested_at": "2026-09-10T00:00:01Z",
        },
        independent_after_state_observation={
            "outcome": "MATCHED",
            "checked_files": [{"path": "docs/x.md", "kind": "write", "status": "MATCHED"}],
        },
    )
    validate_record(record, "execution_receipt.schema.json", base=CHANGE_EXECUTOR_SCHEMA_BASE)
    assert record["change_execution_receipt_id"] == slot_key
    assert record["execution_request_id"] == slot_key


# --------------------------------------------------------------------------------------- #
# P18-R1-F3 (Structural Review Round 1): worktree_root, now a required field *inside* the
# closed Execution Boundary itself, participates in execution_boundary_fingerprint -- and
# therefore in execution_mapping_slot_key -- the identical way every other Boundary field
# already does (extends this file's own fingerprint-sensitivity discipline to the Boundary
# itself, not merely to the three request-scoped record kinds above).
# --------------------------------------------------------------------------------------- #


def _boundary_with(worktree_root: str) -> dict[str, Any]:
    return {
        "permitted_action_kinds": ["WRITE_DOCUMENTATION_FILE"],
        "repository": "org/repo",
        "branch": "main",
        "admitted_paths": ["docs"],
        "max_files_changed": 1,
        "max_bytes_changed": 1000,
        "max_file_bytes": 1000,
        "permit_symlinks": False,
        "permit_path_traversal": False,
        "permit_network": False,
        "permit_subprocess": False,
        "permit_environment_mutation": False,
        "permit_credential_access": False,
        "timeout_seconds": 30,
        "rollback_policy": "NONE",
        "executor_identity": "controlled_filesystem_adapter",
        "executor_version": "0.1",
        "validity_window": {
            "issued_at": "2026-09-10T00:00:00Z",
            "expires_at": "2026-09-10T01:00:00Z",
        },
        "worktree_root": worktree_root,
    }


def test_execution_boundary_fingerprint_is_sensitive_to_worktree_root_alone(
    tmp_path: Path,
) -> None:
    """Two Boundaries, identical in every field except ``worktree_root``, must produce two
    genuinely distinct fingerprints -- and, since ``execution_mapping_slot_key`` is itself a pure
    function of ``execution_boundary_fingerprint`` (among two other inputs), two genuinely
    distinct mapping slots for the identical ``change_id``/``adapter_identity_fingerprint``.
    Both worktree roots are real, existing directories (``validate_execution_boundary`` now
    requires this)."""

    worktree_a = tmp_path / "worktree-a"
    worktree_b = tmp_path / "worktree-b"
    worktree_a.mkdir()
    worktree_b.mkdir()

    boundary_a = validate_execution_boundary(_boundary_with(str(worktree_a)))
    boundary_b = validate_execution_boundary(_boundary_with(str(worktree_b)))

    fingerprint_a = execution_boundary_fingerprint(boundary_a)
    fingerprint_b = execution_boundary_fingerprint(boundary_b)
    assert fingerprint_a != fingerprint_b, (
        "two Boundaries differing only in worktree_root must fingerprint differently"
    )

    change_id = "CHANGE-" + "A" * 64
    adapter_fp = "sha256:" + "2" * 64
    slot_a = execution_mapping_slot_key(change_id, fingerprint_a, adapter_fp)
    slot_b = execution_mapping_slot_key(change_id, fingerprint_b, adapter_fp)
    assert slot_a != slot_b, (
        "two composed executors bound to different worktree roots must get different mapping "
        "slots for the identical change_id/adapter_identity_fingerprint"
    )
