"""Unit/contract proof for the Long-Running Proof Artifact Bundle package (Issue #86 section
10, P87-R1-F8): schema validity, deterministic identity, and the coordination-ledger commit
semantics (idempotent replay, conflict refusal, non-state-advancing commit) -- all at the fast,
minimal-genesis level, independent of any real tier run (the real-run reload/tamper-refusal
proof against a genuine Gate 20 dataset lives in ``tests/long_running_proof/test_long_running_
proof_negative_controls.py``'s own section 12, sharing that file's already-expensive real run
rather than paying for a second one here)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.fixtures import long_running_proof as lrp
from tests.long_running_proof import cycle

from manosube_agent_civilization.long_running_proof_artifact import route as artifact_route
from manosube_agent_civilization.long_running_proof_artifact.engine import (
    build_artifact_bundle,
    stringify_floats,
)
from manosube_agent_civilization.long_running_proof_artifact.identity import (
    artifact_bundle_id,
    artifact_bundle_semantic_fingerprint,
)
from manosube_agent_civilization.store.errors import RecordConflictError


def _minimal_kwargs(
    *, committed_state: dict[str, Any], generated_at: str, tier: int = 1
) -> dict[str, Any]:
    return {
        "project_binding_ref": {"kind": "project_binding", "id": "PB-TEST-0001"},
        "tier": tier,
        "corpus_manifest": {
            "corpus_kind": "long_running_proof",
            "max_cycles": lrp.MAX_CYCLES,
            "tier": tier,
            "predicate_ids": [lrp.predicate_id(0)],
        },
        "lineage_refs": {
            "final_state_revision": committed_state["state_revision"],
            "committed_cycle_count": cycle.committed_cycle_count(committed_state),
            "identity_refs": committed_state["semantic_state"]["lineage"]["identity_refs"],
        },
        "raw_events": [],
        "metrics": {"raw_event_count": 0, "committed_cycle_count": 0, "rate": 0.5},
        "session_loss_receipts": [],
        "agent_swap_refs": [],
        "runtime_observation_refs": [],
        "environment_manifest": {
            "python_implementation": "CPython",
            "python_version": "3.12.0",
            "platform": "test-platform",
        },
        "reproduction_procedure": {
            "entrypoint": "tests.long_running_proof.orchestrator.run_long_running_proof",
            "tier": tier,
            "corpus_kind": "long_running_proof",
            "project_id_constant": lrp.PROJECT_ID,
        },
        "generated_at": generated_at,
    }


def test_build_artifact_bundle_produces_a_schema_valid_content_addressed_record(
    tmp_path: Path,
) -> None:
    store = cycle.build_store(tmp_path)
    bind_result = cycle.bind_genesis(store)
    kwargs = _minimal_kwargs(
        committed_state=bind_result["committed_state"], generated_at="2026-01-01T00:00:00.000001Z"
    )

    record = build_artifact_bundle(project_id=lrp.PROJECT_ID, **kwargs)

    assert record["artifact_bundle_id"].startswith("LRPA-")
    assert record["artifact_bundle_semantic_fingerprint"].startswith("sha256:")
    assert record["artifact_bundle_id"] == artifact_bundle_id(record)
    assert record["artifact_bundle_semantic_fingerprint"] == artifact_bundle_semantic_fingerprint(
        record
    )
    # metrics floats survive only as their deterministic string encoding (canonical_json_bytes
    # itself prohibits floats outright) -- never a raw float in the committed body.
    assert record["metrics"]["rate"] == repr(0.5)


def test_artifact_bundle_id_is_independent_of_generated_at_and_content_fields(
    tmp_path: Path,
) -> None:
    store = cycle.build_store(tmp_path)
    bind_result = cycle.bind_genesis(store)

    first = build_artifact_bundle(
        project_id=lrp.PROJECT_ID,
        **_minimal_kwargs(
            committed_state=bind_result["committed_state"],
            generated_at="2026-01-01T00:00:00.000001Z",
        ),
    )
    later_kwargs = _minimal_kwargs(
        committed_state=bind_result["committed_state"], generated_at="2026-06-15T12:30:00.000001Z"
    )
    later_kwargs["metrics"] = {"raw_event_count": 3, "committed_cycle_count": 3, "rate": 0.75}
    second = build_artifact_bundle(project_id=lrp.PROJECT_ID, **later_kwargs)

    assert first["artifact_bundle_id"] == second["artifact_bundle_id"]
    assert (
        first["artifact_bundle_semantic_fingerprint"]
        != second["artifact_bundle_semantic_fingerprint"]
    )


def test_commit_artifact_bundle_is_idempotent_for_an_identical_body(tmp_path: Path) -> None:
    store = cycle.build_store(tmp_path)
    bind_result = cycle.bind_genesis(store)
    kwargs = _minimal_kwargs(
        committed_state=bind_result["committed_state"], generated_at="2026-01-01T00:00:00.000001Z"
    )

    first = artifact_route.commit_artifact_bundle(store, project_id=lrp.PROJECT_ID, **kwargs)
    second = artifact_route.commit_artifact_bundle(store, project_id=lrp.PROJECT_ID, **kwargs)

    assert first == second


def test_commit_artifact_bundle_refuses_a_conflicting_body_for_the_identical_identity(
    tmp_path: Path,
) -> None:
    store = cycle.build_store(tmp_path)
    bind_result = cycle.bind_genesis(store)
    kwargs = _minimal_kwargs(
        committed_state=bind_result["committed_state"], generated_at="2026-01-01T00:00:00.000001Z"
    )
    artifact_route.commit_artifact_bundle(store, project_id=lrp.PROJECT_ID, **kwargs)

    conflicting = dict(kwargs)
    conflicting["reproduction_procedure"] = dict(kwargs["reproduction_procedure"])
    conflicting["reproduction_procedure"]["entrypoint"] = "some.other.entrypoint"

    with pytest.raises(RecordConflictError):
        artifact_route.commit_artifact_bundle(store, project_id=lrp.PROJECT_ID, **conflicting)


def test_commit_artifact_bundle_never_advances_canonical_state(tmp_path: Path) -> None:
    store = cycle.build_store(tmp_path)
    bind_result = cycle.bind_genesis(store)
    before_revision = bind_result["committed_state"]["state_revision"]
    kwargs = _minimal_kwargs(
        committed_state=bind_result["committed_state"], generated_at="2026-01-01T00:00:00.000001Z"
    )

    artifact_route.commit_artifact_bundle(store, project_id=lrp.PROJECT_ID, **kwargs)

    after = store.load_current(lrp.PROJECT_ID)
    assert after["state_revision"] == before_revision


def test_resolve_artifact_bundle_returns_none_when_never_committed(tmp_path: Path) -> None:
    store = cycle.build_store(tmp_path)
    cycle.bind_genesis(store)
    never_committed_id = "LRPA-" + ("0" * 64)

    assert (
        artifact_route.resolve_artifact_bundle(
            store, project_id=lrp.PROJECT_ID, artifact_bundle_id=never_committed_id
        )
        is None
    )


def test_stringify_floats_round_trips_exactly() -> None:
    value = {"rate": 0.3333333333333333, "count": 3, "nested": [0.1, {"a": None, "b": True}]}
    converted = stringify_floats(value)
    assert converted["rate"] == repr(0.3333333333333333)
    assert float(converted["rate"]) == 0.3333333333333333
    assert converted["count"] == 3
    assert converted["nested"][0] == repr(0.1)
    assert converted["nested"][1] == {"a": None, "b": True}
