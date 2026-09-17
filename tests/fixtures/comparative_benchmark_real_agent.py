"""PR #90 Round 6 (``ADOPT_P90_R6_REAL_AGENT_ORIGINAL_RUN_AND_FINAL_PROTOCOL``, comment
5714630885) -- the bounded, real-file-backed fixture world for the ``MANOSUBE_PRESENT``
condition of the two-task real-Agent corpus (``examples/comparative_benchmark/real_agent_corpus/
TASK_CORPUS.md``).

Deliberately generalizes ``tests/fixtures/vertical_proof.py`` (Phase 8's one-shot fixture) the
same field-for-field-faithful, independently-kept way ``tests/fixtures/long_running_proof.py``
already does (``PHASE_8_FIXTURE_BINDING_NE_PHASE_20_FIXTURE_BINDING=true`` -- each phase/round
keeps its own fixture world rather than importing another's), with one structural difference
from both: the before/after Source Snapshot bytes here are **not** static, pre-baked,
checked-in fixture files. They are the real bytes of
``examples/comparative_benchmark/real_agent_corpus/present/STATUS.md`` *at the moment this
module's own builder functions are called* -- read fresh off disk, never a module-level
constant computed once at import time -- because the whole point of Round 6 is that the
"after" state genuinely reflects a real Agent's real completed work (this session's own
native tool-using Claude Sonnet 5 identity, the identical Agent identity the
``MANOSUBE_ABSENT`` condition already used, per ``RAW_EVENTS.md``), observed post-hoc, not a
value asserted in advance.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from manosube_agent_civilization.observation.source_snapshot import build_source_snapshot

ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = ROOT / "examples/comparative_benchmark/real_agent_corpus"
STATUS_PATH = CORPUS_DIR / "present" / "STATUS.md"
STATUS_LOCATOR = "examples/comparative_benchmark/real_agent_corpus/present/STATUS.md"

PROJECT_ID = "PRJ-P90-R6-0001"
OBJECTIVE_ID = "OBJ-P90-R6-0001"
OBJECTIVE_REVISION_ID = "OBJ-REV-P90-R6-0001"
SCOPE_ID = "OBS-SCOPE-P90-R6-0001"
REPOSITORY = "manosube/manosube-agent-civilization-os"
BRANCH = "agent/issue-89-phase21-comparative-benchmark"

#: The two Round 6 corpus tasks, in their fixed, declared order -- see ``TASK_CORPUS.md``.
TASK_KEYS: tuple[str, ...] = ("task_a", "task_b")

HUMAN_AUTHORITY: dict[str, Any] = {"kind": "human_authority", "id": "AUTH-P90-R6-0001"}

OBJECTIVE_RECORDED_AT = "2026-09-17T13:00:00Z"

METHOD_REF: dict[str, Any] = {"kind": "observation_method", "id": "OBS-METHOD-P90-R6-0001"}
OBSERVATION_METHOD: dict[str, Any] = {
    "method_profile": "MANOSUBE-OBSERVATION-METHOD-SHA256-0.1",
    "procedure_kind": "CANONICAL_OBSERVER",
    "procedure_ref": {
        "kind": "observer_procedure",
        "id": "OBS-PROCEDURE-P90-R6-0001",
        "version": "0.1",
        "semantic_fingerprint": "sha256:" + "6" * 64,
    },
    "normalization_profile": "FIXTURE-0.1",
    "input_contract_ref": {"kind": "schema", "id": "OBS-INPUT-01"},
    "output_contract_refs": {
        "collection_kind": "UNORDERED_SET",
        "members": [{"kind": "schema", "id": "NORMALIZED-FACT-01"}],
    },
    "execution_boundary_ref": {"kind": "execution_boundary", "id": "KERNEL-LOCAL"},
}

ARTIFACT: dict[str, Any] = {
    "kind": "artifact",
    "id": "ARTIFACT-P90-R6-0001",
    "content_sha256": "2" * 64,
    "byte_length": 64,
    "media_type": "application/json",
}

NEGATIVE_EVIDENCE_REF: dict[str, str] = {"kind": "negative_evidence", "id": "NEG-EVID-P90-R6-0001"}

VERIFICATION_RESULT_PROVENANCE: dict[str, Any] = {
    "status": "VERIFIED",
    "requirement_id": "VREQ-P90-R6-0001",
    "selection_id": "VSEL-P90-R6-0001",
    "project_id": PROJECT_ID,
    "target_refs": {"collection_kind": "UNORDERED_SET", "members": []},
    "verifier_identity": {"kind": "deterministic_test_runner", "id": "VERIFIER-P90-R6-0001"},
    "selection_authority_ref": dict(HUMAN_AUTHORITY),
    "verification_boundary": {"scope": "repository", "boundary_id": "VB-P90-R6-0001"},
    "input_refs": {"collection_kind": "UNORDERED_SET", "members": []},
    "observations": {"summary": "Round 6 real-Agent corpus PRESENT-condition provenance"},
}


def predicate_id(k: int) -> str:
    return f"TP-P90-R6-{k:04d}"


def subject(k: int) -> str:
    return f"real_agent_corpus.{TASK_KEYS[k]}"


def claim_key(k: int) -> str:
    return f"real_agent_corpus_{TASK_KEYS[k]}"


def evidence_ref(k: int, *, role: str) -> dict[str, str]:
    return {"kind": "observation_evidence", "id": f"EVID-P90-R6-{k:04d}-{role.upper()}"}


def target_predicate(k: int) -> dict[str, Any]:
    return {
        "predicate_id": predicate_id(k),
        "subject": subject(k),
        "operator": "equals",
        "expected_value": "READY",
        "observation_scope": "real_agent_corpus",
        "evidence_requirement": "E1",
        "unknown_policy": "INCOMPLETE",
        "criticality": "mandatory",
    }


def objective_revision() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "objective_id": OBJECTIVE_ID,
        "objective_revision_id": OBJECTIVE_REVISION_ID,
        "project_id": PROJECT_ID,
        "statement": (
            "PR #90 Round 6's two real-Agent corpus tasks (task_a hash computation, "
            "task_b prime enumeration) each reach READY once the identical real-Agent "
            "identity that ran MANOSUBE_ABSENT completes the identical task under the "
            "MANOSUBE_PRESENT Difference/Authority/Change/Evidence/Reflow lifecycle."
        ),
        "owner_authority_ref": dict(HUMAN_AUTHORITY),
        "target_predicates": [target_predicate(k) for k in range(len(TASK_KEYS))],
        "completion_policy": {"mode": "ALL", "contradiction_policy": "BLOCK"},
        "boundary_ref": {"kind": "objective_boundary", "id": "BOUND-P90-R6-0001"},
        "constitutional_constraints": [],
        "status": "ACTIVE",
        "revision": 0,
        "previous_objective_ref": None,
        "change_reason": "PR #90 Round 6 real-Agent corpus objective",
        "base_semantic_fingerprint": None,
        "semantic_change_summary": "initial Round 6 real-Agent corpus objective revision",
        "human_authority_ref": dict(HUMAN_AUTHORITY),
        "recorded_at": OBJECTIVE_RECORDED_AT,
    }


def read_status_bytes() -> bytes:
    """The real, current bytes of the corpus's own real ``STATUS.md`` file, read fresh off
    disk -- never cached, never a module-level constant, so every call genuinely reflects
    whatever this repository's own working tree contains *right now* (including a real
    Agent's real just-made edit)."""

    return STATUS_PATH.read_bytes()


def status_source_snapshot(*, captured_at: str) -> dict[str, Any]:
    """A real, content-addressed Source Snapshot of :data:`STATUS_PATH`'s own real,
    current bytes -- the one real file both this proof's before- and after-Observation
    read, at two genuinely different points in real wall-clock time, exactly as a real
    long-running Project's own status file would be re-observed as real work lands."""

    current_bytes = read_status_bytes()
    return build_source_snapshot(
        source_locator=STATUS_LOCATOR,
        content_digest="sha256:" + hashlib.sha256(current_bytes).hexdigest(),
        captured_at=captured_at,
    )


def snapshot_ref(snapshot: dict[str, Any]) -> dict[str, str]:
    return {"kind": "source_snapshot", "id": snapshot["source_snapshot_id"]}


def observation_scope(k: int, *, ref: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "scope_id": f"{SCOPE_ID}-{k:04d}",
        "project_id": PROJECT_ID,
        "target_identity": predicate_id(k),
        "included_subjects": [subject(k)],
        "excluded_subjects": ["real_agent_corpus.secret"],
        "boundary_root": "/real_agent_corpus",
        "path_policy": {
            "relative_locators_only": True,
            "symlink_escape": "BLOCK",
            "submodule_traversal": "DECLARED_ONLY",
            "mount_escape": "BLOCK",
            "credential_paths": "EXCLUDE",
        },
        "observation_window": {"start": "2026-09-17T13:00:00Z", "end": "2026-12-31T00:00:00Z"},
        "target_effective_window": {
            "start": "2026-09-17T12:59:00Z",
            "end": "2026-12-31T00:00:00Z",
        },
        "freshness_limit_seconds": 31536000,
        "cutoff": "2026-12-31T00:00:00Z",
        "source_snapshot_refs": [dict(ref)],
        "enumeration_rule": {"kind": "enumeration_rule", "id": f"ENUM-P90-R6-{k:04d}"},
        "completion_predicate": {"kind": "completion_predicate", "id": f"COMPLETE-P90-R6-{k:04d}"},
        "method_ref": dict(METHOD_REF),
        "attempt_policy": {"max_attempts": 1, "timeout_seconds": 60, "retry_on": []},
        "blind_spots": [],
        "scope_status": "COMPLETE",
    }


def raw_fact(k: int, *, value: str, snapshot_id: str) -> dict[str, Any]:
    return {
        "subject": subject(k),
        "predicate": "equals@v1",
        "value": value,
        "value_type": "STRING",
        "unit": None,
        "effective_boundary": {
            "kind": "SOURCE_SNAPSHOT",
            "identity": snapshot_id,
            "start": None,
            "end": None,
        },
    }


def observation_request(
    k: int,
    *,
    value: str,
    snapshot: dict[str, Any],
    fingerprint: dict[str, Any],
    state_revision: int,
    started_at: str,
    ended_at: str,
    attempt_id: str,
    ref: dict[str, str],
) -> dict[str, Any]:
    ref_to_snapshot = snapshot_ref(snapshot)
    scope = observation_scope(k, ref=ref_to_snapshot)
    return {
        "project_id": PROJECT_ID,
        "state_revision_observed": state_revision,
        "state_fingerprint_observed": deepcopy(fingerprint),
        "target_identity": predicate_id(k),
        "target_kind": "FIXTURE",
        "scope": scope,
        "method_ref": dict(METHOD_REF),
        "time_boundary": {
            "observation_started_at": started_at,
            "observation_ended_at": ended_at,
            "target_effective_start": "2026-09-17T12:59:00Z",
            "target_effective_end": "2026-12-31T00:00:00Z",
            "source_snapshot_time": snapshot["captured_at"],
        },
        "source_snapshot_refs": [dict(ref_to_snapshot)],
        "normalization_profile": "FIXTURE-0.1",
        "source_occurrences": [
            {
                "source_ref": dict(ref_to_snapshot),
                "source_locator": snapshot["source_locator"],
                "facts": [raw_fact(k, value=value, snapshot_id=ref_to_snapshot["id"])],
            }
        ],
        "attempts": [
            {
                "attempt_id": attempt_id,
                "method_ref": dict(METHOD_REF),
                "started_at": started_at,
                "ended_at": ended_at,
                "result": "COMPLETE",
                "failure_class": None,
            }
        ],
        "blind_spots": [],
        "observation_evidence_refs": [dict(ref)],
        "negative_evidence_refs": [dict(NEGATIVE_EVIDENCE_REF)],
        "negative_claims": [],
        "collection_complete": True,
    }


def before_observation_request(
    k: int,
    *,
    snapshot: dict[str, Any],
    fingerprint: dict[str, Any],
    state_revision: int,
    started_at: str,
    ended_at: str,
    ref: dict[str, str] | None = None,
) -> dict[str, Any]:
    return observation_request(
        k,
        value="NOT-READY",
        snapshot=snapshot,
        fingerprint=fingerprint,
        state_revision=state_revision,
        started_at=started_at,
        ended_at=ended_at,
        attempt_id=f"ATTEMPT-P90-R6-{k:04d}-BEFORE",
        ref=ref if ref is not None else evidence_ref(k, role="before-seed"),
    )


def change_result_observation_request(
    k: int,
    *,
    snapshot: dict[str, Any],
    fingerprint: dict[str, Any],
    state_revision: int,
    started_at: str,
    ended_at: str,
    ref: dict[str, str] | None = None,
) -> dict[str, Any]:
    return observation_request(
        k,
        value="READY",
        snapshot=snapshot,
        fingerprint=fingerprint,
        state_revision=state_revision,
        started_at=started_at,
        ended_at=ended_at,
        attempt_id=f"ATTEMPT-P90-R6-{k:04d}-CHANGE-RESULT",
        ref=ref if ref is not None else evidence_ref(k, role="change-result-seed"),
    )


def verification_observation_request(
    k: int,
    *,
    snapshot: dict[str, Any],
    fingerprint: dict[str, Any],
    state_revision: int,
    started_at: str,
    ended_at: str,
    ref: dict[str, str] | None = None,
) -> dict[str, Any]:
    return observation_request(
        k,
        value="READY",
        snapshot=snapshot,
        fingerprint=fingerprint,
        state_revision=state_revision,
        started_at=started_at,
        ended_at=ended_at,
        attempt_id=f"ATTEMPT-P90-R6-{k:04d}-VERIFICATION",
        ref=ref if ref is not None else evidence_ref(k, role="verification-seed"),
    )


def derivation_request(
    k: int,
    *,
    observation_bundle: dict[str, Any] | None,
    fingerprint: dict[str, Any],
    state_revision: int,
    snapshot_ref_value: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "identity_profile": "MANOSUBE-DIFFERENCE-SHA256-0.1",
        "comparison_profile": "MANOSUBE-DIFFERENCE-COMPARISON-0.1",
        "normalization_profile": "MANOSUBE-DIFFERENCE-NORMALIZATION-0.1",
        "project_id": PROJECT_ID,
        "objective_revision": objective_revision(),
        "state_revision": state_revision,
        "state_fingerprint": deepcopy(fingerprint),
        "closure_policy_requirements": {"minimum_evidence_level": "E1"},
        "observation_method": deepcopy(OBSERVATION_METHOD),
        "bindings": [
            {
                "target_predicate_id": predicate_id(k),
                "observation_scope": observation_scope(k, ref=snapshot_ref_value),
                "observation_bundle": observation_bundle,
            }
        ],
    }


def action_scope() -> dict[str, Any]:
    return {
        "repository": REPOSITORY,
        "branch": BRANCH,
        "paths": [
            "examples/comparative_benchmark/real_agent_corpus/present/STATUS.md",
            "examples/comparative_benchmark/real_agent_corpus/present/task_a_output.txt",
            "examples/comparative_benchmark/real_agent_corpus/present/task_b_output.txt",
        ],
        "subjects": [],
    }


def authority_rule(*, project_id: str) -> dict[str, Any]:
    from manosube_agent_civilization.authority.identity import rule_id

    record = {
        "schema_version": "0.1",
        "authority_rule_id": "",
        "project_id": project_id,
        "action_kinds": ["WRITE_FILE"],
        "maximum_reversibility": "REVERSIBLE",
        "scope": action_scope(),
        "decision": "AUTONOMOUS",
        "declared_by": dict(HUMAN_AUTHORITY),
    }
    record["authority_rule_id"] = rule_id(record)
    return record


def requested_action(k: int) -> dict[str, Any]:
    from manosube_agent_civilization.authority.identity import action_fingerprint

    record = {
        "action_kind": "WRITE_FILE",
        "reversibility": "REVERSIBLE",
        "operation": {"body": f"perform real_agent_corpus {TASK_KEYS[k]} for real, PRESENT"},
        "action_semantic_fingerprint": "",
    }
    record["action_semantic_fingerprint"] = action_fingerprint(record)
    return record


def closure_policy(difference_id: str, *, predicate: str) -> dict[str, Any]:
    from manosube_agent_civilization.difference.identity import (
        closure_policy_id,
        policy_semantic_fingerprint,
    )

    policy: dict[str, Any] = {
        "schema_version": "0.1",
        "closure_policy_id": "",
        "policy_version": "0.1",
        "policy_semantic_fingerprint": "",
        "subject_difference_ref": {"kind": "difference", "id": difference_id},
        "target_predicate_ref": {"kind": "target_predicate", "id": predicate},
        "required_observation_scope": None,
        "minimum_evidence_level": "E1",
        "required_claims": [],
        "required_invariants": [],
        "allowed_terminal_states": ["CLOSED", "BLOCKED", "RETAINED"],
        "independent_verification_required": False,
        "maximum_evidence_age": None,
        "contradiction_policy": "FAIL_CLOSED",
        "reopen_conditions": [],
    }
    policy["policy_semantic_fingerprint"] = policy_semantic_fingerprint(policy)
    policy["closure_policy_id"] = closure_policy_id(
        policy["policy_semantic_fingerprint"], difference_id
    )
    return policy


def bind_project_kwargs(genesis_state: dict[str, Any]) -> dict[str, Any]:
    from tests.fixtures import product_binding as pb

    rule = authority_rule(project_id=PROJECT_ID)
    return {
        "project_id": PROJECT_ID,
        "objective_revision": objective_revision(),
        "boundary": pb.boundary(),
        "authority_policy_ref": {"kind": "authority_rule", "id": rule["authority_rule_id"]},
        "authority_rule": rule,
        "source_registrations": pb.source_registrations(),
        "command_policy": pb.command_policy(),
        "secret_exclusion_policy": pb.secret_exclusion_policy(),
        "human_authority_ref": dict(HUMAN_AUTHORITY),
        "human_authority_signing_key": pb.human_authority_signing_key(),
        "bound_at": OBJECTIVE_RECORDED_AT,
        "genesis_state": genesis_state,
    }
