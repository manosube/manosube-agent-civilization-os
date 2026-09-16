"""Unit/contract proof for the Comparative Benchmark package (Issue #89 section 9, P89-adoption,
``ADOPT_PHASE_21_COMPARATIVE_BENCHMARK``): schema validity, deterministic identity, and the
coordination-ledger commit semantics (idempotent replay, conflict refusal, non-state-advancing
commit) for all three record kinds -- all at the fast, minimal level, independent of any real
full comparative-benchmark run (the real-run proof, Gate 21, and the 13 decisive negative
controls live in ``tests/comparative_benchmark/``, sharing that package's own already-expensive
real run rather than paying for a second one here)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.fixtures import comparative_benchmark as cb
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.comparative_benchmark import route as cb_route
from manosube_agent_civilization.comparative_benchmark.engine import (
    build_protocol_freeze,
    build_reproduction_receipt,
    build_result_bundle,
)
from manosube_agent_civilization.comparative_benchmark.errors import (
    ProtocolFreezeValidationError,
    ResultBundleValidationError,
)
from manosube_agent_civilization.comparative_benchmark.identity import (
    protocol_freeze_id,
    protocol_freeze_semantic_fingerprint,
    reproduction_receipt_id,
    result_bundle_id,
)
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.errors import RecordConflictError

_GENERATED_AT = "2026-01-01T00:00:00.000001Z"
_LATER_GENERATED_AT = "2026-06-15T12:30:00.000001Z"
_PROJECT_BINDING_REF = {"kind": "project_binding", "id": cb.PROJECT_BINDING_ID}
_ENVIRONMENT_MANIFEST = {
    "python_implementation": "CPython",
    "python_version": "3.12.0",
    "platform": "test-platform",
}


def _store(tmp_path: Path) -> FileStateStore:
    return FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)


def _freeze_kwargs(*, generated_at: str = _GENERATED_AT) -> dict[str, Any]:
    return cb.protocol_freeze_kwargs(generated_at=generated_at)


def _minimal_raw_events(
    protocol_freeze: dict[str, Any], *, outcome: str = "FAILED"
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for group in protocol_freeze["comparison_groups"]:
        for task_id in protocol_freeze["corpus_manifest"]["task_ids"]:
            events.append(
                {
                    "kind": "task_attempt",
                    "comparison_group_id": group["comparison_group_id"],
                    "task_id": task_id,
                    "outcome": outcome,
                }
            )
    return events


# --- protocol freeze --------------------------------------------------------------------------- #


def test_build_protocol_freeze_produces_a_schema_valid_content_addressed_record() -> None:
    record = build_protocol_freeze(project_id=cb.PROJECT_ID, **_freeze_kwargs())

    assert record["protocol_freeze_id"].startswith("CBPF-")
    assert record["protocol_freeze_semantic_fingerprint"].startswith("sha256:")
    assert record["protocol_freeze_id"] == protocol_freeze_id(record)
    assert record["protocol_freeze_semantic_fingerprint"] == protocol_freeze_semantic_fingerprint(
        record
    )
    # resource_budget_manifest's float fields survive only as their deterministic repr()
    # string encoding (the canonical-JSON profile prohibits raw floats outright).
    assert record["resource_budget_manifest"]["per_task_timeout_seconds"] == repr(30.0)


def test_protocol_freeze_id_is_independent_of_policy_and_generated_at_fields() -> None:
    first = build_protocol_freeze(project_id=cb.PROJECT_ID, **_freeze_kwargs())
    later_kwargs = _freeze_kwargs(generated_at=_LATER_GENERATED_AT)
    later_kwargs["metric_definitions"] = [
        {"metric_name": "a_different_metric", "formula": "x", "denominator": "y"}
    ]
    second = build_protocol_freeze(project_id=cb.PROJECT_ID, **later_kwargs)

    assert first["protocol_freeze_id"] == second["protocol_freeze_id"]
    assert (
        first["protocol_freeze_semantic_fingerprint"]
        != second["protocol_freeze_semantic_fingerprint"]
    )


def test_build_protocol_freeze_rejects_fewer_than_two_comparison_groups() -> None:
    kwargs = _freeze_kwargs()
    kwargs["comparison_groups"] = [kwargs["comparison_groups"][0]]
    with pytest.raises(ProtocolFreezeValidationError, match="at least 2 groups"):
        build_protocol_freeze(project_id=cb.PROJECT_ID, **kwargs)


def test_build_protocol_freeze_rejects_a_missing_present_or_absent_role() -> None:
    kwargs = _freeze_kwargs()
    only_absent = [
        dict(g)
        for g in kwargs["comparison_groups"]
        if g["comparison_group_role"] == "MANOSUBE_ABSENT"
    ]
    kwargs["comparison_groups"] = only_absent
    with pytest.raises(ProtocolFreezeValidationError, match="MANOSUBE_PRESENT"):
        build_protocol_freeze(project_id=cb.PROJECT_ID, **kwargs)

    kwargs2 = _freeze_kwargs()
    only_present = [
        dict(g)
        for g in kwargs2["comparison_groups"]
        if g["comparison_group_role"] == "MANOSUBE_PRESENT"
    ]
    # A single-group list also trips the ">= 2 groups" check first -- pad with a second,
    # still-PRESENT-role group so this test isolates the role-completeness check itself.
    duplicate_present = dict(only_present[0])
    duplicate_present["comparison_group_id"] = only_present[0]["comparison_group_id"] + "-2"
    kwargs2["comparison_groups"] = [only_present[0], duplicate_present]
    with pytest.raises(ProtocolFreezeValidationError, match="MANOSUBE_ABSENT"):
        build_protocol_freeze(project_id=cb.PROJECT_ID, **kwargs2)


def test_build_protocol_freeze_rejects_a_duplicate_comparison_group_id() -> None:
    kwargs = _freeze_kwargs()
    groups = [dict(g) for g in kwargs["comparison_groups"]]
    groups[1] = dict(groups[1])
    groups[1]["comparison_group_id"] = groups[0]["comparison_group_id"]
    kwargs["comparison_groups"] = groups
    with pytest.raises(ProtocolFreezeValidationError, match="duplicate comparison_group_id"):
        build_protocol_freeze(project_id=cb.PROJECT_ID, **kwargs)


def test_build_protocol_freeze_rejects_present_absent_mechanism_identity_overlap() -> None:
    kwargs = _freeze_kwargs()
    groups = [dict(g) for g in kwargs["comparison_groups"]]
    for group in groups:
        if group["comparison_group_role"] == "MANOSUBE_ABSENT":
            group["mechanism_identity"] = dict(cb.PRESENT_MECHANISM_IDENTITY)
    kwargs["comparison_groups"] = groups
    with pytest.raises(ProtocolFreezeValidationError, match="never share a mechanism_identity"):
        build_protocol_freeze(project_id=cb.PROJECT_ID, **kwargs)


def test_commit_protocol_freeze_is_idempotent_for_an_identical_body(tmp_path: Path) -> None:
    store = _store(tmp_path)
    kwargs = _freeze_kwargs()
    first = cb_route.commit_protocol_freeze(store, project_id=cb.PROJECT_ID, **kwargs)
    second = cb_route.commit_protocol_freeze(store, project_id=cb.PROJECT_ID, **kwargs)
    assert first == second


def test_commit_protocol_freeze_refuses_a_conflicting_body_for_the_identical_identity(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    kwargs = _freeze_kwargs()
    cb_route.commit_protocol_freeze(store, project_id=cb.PROJECT_ID, **kwargs)

    conflicting = dict(kwargs)
    conflicting["metric_definitions"] = [
        {"metric_name": "conflicting_metric", "formula": "x", "denominator": "y"}
    ]
    with pytest.raises(RecordConflictError):
        cb_route.commit_protocol_freeze(store, project_id=cb.PROJECT_ID, **conflicting)


def test_commit_protocol_freeze_never_advances_canonical_state(tmp_path: Path) -> None:
    from tests.long_running_proof import cycle

    store = _store(tmp_path)
    bind_result = cycle.bind_genesis(store)
    before_revision = bind_result["committed_state"]["state_revision"]

    cb_route.commit_protocol_freeze(store, project_id=cb.PROJECT_ID, **_freeze_kwargs())

    from tests.fixtures import long_running_proof as lrp

    after = store.load_current(lrp.PROJECT_ID)
    assert after["state_revision"] == before_revision


def test_resolve_protocol_freeze_returns_none_when_never_committed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    never_committed_id = "CBPF-" + ("0" * 64)
    assert (
        cb_route.resolve_protocol_freeze(
            store, project_id=cb.PROJECT_ID, protocol_freeze_id=never_committed_id
        )
        is None
    )


# --- result bundle ------------------------------------------------------------------------------ #


def test_build_result_bundle_recomputes_metrics_and_claims_from_raw_events_alone() -> None:
    protocol_freeze = build_protocol_freeze(project_id=cb.PROJECT_ID, **_freeze_kwargs())
    raw_events = _minimal_raw_events(protocol_freeze)

    record = build_result_bundle(
        project_id=cb.PROJECT_ID,
        project_binding_ref=_PROJECT_BINDING_REF,
        protocol_freeze=protocol_freeze,
        raw_events=raw_events,
        environment_manifest=_ENVIRONMENT_MANIFEST,
        generated_at=_GENERATED_AT,
    )

    assert record["result_bundle_id"].startswith("CBRB-")
    assert record["result_bundle_id"] == result_bundle_id(record)
    for group in protocol_freeze["comparison_groups"]:
        group_id = group["comparison_group_id"]
        assert record["metrics"][group_id]["raw_event_count"] == len(
            protocol_freeze["corpus_manifest"]["task_ids"]
        )
        assert record["metrics"][group_id]["FAILED"] == len(
            protocol_freeze["corpus_manifest"]["task_ids"]
        )
    declared_claim_ids = {c["claim_id"] for c in protocol_freeze["claim_vocabulary"]}
    assert {c["claim_id"] for c in record["claims"]} == declared_claim_ids


def test_build_result_bundle_rejects_an_undeclared_comparison_group_id() -> None:
    protocol_freeze = build_protocol_freeze(project_id=cb.PROJECT_ID, **_freeze_kwargs())
    bad_events = [
        {
            "kind": "task_attempt",
            "comparison_group_id": "never-declared",
            "task_id": protocol_freeze["corpus_manifest"]["task_ids"][0],
            "outcome": "FAILED",
        }
    ]
    with pytest.raises(ResultBundleValidationError, match="never declared"):
        build_result_bundle(
            project_id=cb.PROJECT_ID,
            project_binding_ref=_PROJECT_BINDING_REF,
            protocol_freeze=protocol_freeze,
            raw_events=bad_events,
            environment_manifest=_ENVIRONMENT_MANIFEST,
            generated_at=_GENERATED_AT,
        )


def test_build_result_bundle_rejects_an_unrecognized_outcome() -> None:
    protocol_freeze = build_protocol_freeze(project_id=cb.PROJECT_ID, **_freeze_kwargs())
    bad_events = [
        {
            "kind": "task_attempt",
            "comparison_group_id": protocol_freeze["comparison_groups"][0]["comparison_group_id"],
            "task_id": protocol_freeze["corpus_manifest"]["task_ids"][0],
            "outcome": "NOT_A_REAL_OUTCOME",
        }
    ]
    with pytest.raises(ResultBundleValidationError, match="unrecognized task outcome"):
        build_result_bundle(
            project_id=cb.PROJECT_ID,
            project_binding_ref=_PROJECT_BINDING_REF,
            protocol_freeze=protocol_freeze,
            raw_events=bad_events,
            environment_manifest=_ENVIRONMENT_MANIFEST,
            generated_at=_GENERATED_AT,
        )


def test_commit_result_bundle_is_idempotent_and_conflict_refuses(tmp_path: Path) -> None:
    store = _store(tmp_path)
    protocol_freeze = cb_route.commit_protocol_freeze(
        store, project_id=cb.PROJECT_ID, **_freeze_kwargs()
    )
    raw_events = _minimal_raw_events(protocol_freeze)
    kwargs = {
        "project_binding_ref": _PROJECT_BINDING_REF,
        "protocol_freeze": protocol_freeze,
        "raw_events": raw_events,
        "environment_manifest": _ENVIRONMENT_MANIFEST,
        "generated_at": _GENERATED_AT,
    }

    first = cb_route.commit_result_bundle(store, project_id=cb.PROJECT_ID, **kwargs)
    second = cb_route.commit_result_bundle(store, project_id=cb.PROJECT_ID, **kwargs)
    assert first == second

    # result_bundle_id is derived only from (project_id, protocol_freeze_ref, raw_events) --
    # environment_manifest is outside the id but inside the semantic fingerprint, so changing
    # it alone collides at the identical already-committed id with a genuinely different body.
    conflicting = dict(kwargs)
    conflicting["environment_manifest"] = {
        **_ENVIRONMENT_MANIFEST,
        "platform": "a-different-platform",
    }
    with pytest.raises(RecordConflictError):
        cb_route.commit_result_bundle(store, project_id=cb.PROJECT_ID, **conflicting)

    resolved = cb_route.resolve_result_bundle(
        store, project_id=cb.PROJECT_ID, result_bundle_id=first["result_bundle_id"]
    )
    assert resolved == first


# --- reproduction receipt ----------------------------------------------------------------------- #


def test_build_reproduction_receipt_matches_diverges_and_is_incomparable() -> None:
    protocol_freeze = build_protocol_freeze(project_id=cb.PROJECT_ID, **_freeze_kwargs())
    raw_events = _minimal_raw_events(protocol_freeze)
    original_bundle = build_result_bundle(
        project_id=cb.PROJECT_ID,
        project_binding_ref=_PROJECT_BINDING_REF,
        protocol_freeze=protocol_freeze,
        raw_events=raw_events,
        environment_manifest=_ENVIRONMENT_MANIFEST,
        generated_at=_GENERATED_AT,
    )

    # MATCH: an honest, identical re-run.
    match_receipt = build_reproduction_receipt(
        project_id=cb.PROJECT_ID,
        project_binding_ref=_PROJECT_BINDING_REF,
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        reproducer_identity={"reproducer": "reproducer-a", "is_original_author": False},
        reproduced_raw_events=raw_events,
        generated_at=_GENERATED_AT,
    )
    assert match_receipt["agreement"] == "MATCH"
    assert match_receipt["reproduction_receipt_id"] == reproduction_receipt_id(match_receipt)

    # DIVERGENT: the identical declared comparison_group_id set, but a genuinely different
    # outcome distribution.
    divergent_events = _minimal_raw_events(protocol_freeze, outcome="TIMED_OUT")
    divergent_receipt = build_reproduction_receipt(
        project_id=cb.PROJECT_ID,
        project_binding_ref=_PROJECT_BINDING_REF,
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        reproducer_identity={"reproducer": "reproducer-b", "is_original_author": False},
        reproduced_raw_events=divergent_events,
        generated_at=_GENERATED_AT,
    )
    assert divergent_receipt["agreement"] == "DIVERGENT"

    # INCOMPARABLE: a foreign original bundle whose own metrics carry a different
    # comparison_group_id set entirely.
    foreign_bundle = {
        "result_bundle_id": "CBRB-" + ("1" * 64),
        "metrics": {"a-totally-different-group": {"raw_event_count": 0}},
    }
    incomparable_receipt = build_reproduction_receipt(
        project_id=cb.PROJECT_ID,
        project_binding_ref=_PROJECT_BINDING_REF,
        protocol_freeze=protocol_freeze,
        original_result_bundle=foreign_bundle,
        reproducer_identity={"reproducer": "reproducer-c", "is_original_author": False},
        reproduced_raw_events=raw_events,
        generated_at=_GENERATED_AT,
    )
    assert incomparable_receipt["agreement"] == "INCOMPARABLE"


def test_commit_reproduction_receipt_is_idempotent_and_resolves(tmp_path: Path) -> None:
    store = _store(tmp_path)
    protocol_freeze = cb_route.commit_protocol_freeze(
        store, project_id=cb.PROJECT_ID, **_freeze_kwargs()
    )
    raw_events = _minimal_raw_events(protocol_freeze)
    original_bundle = cb_route.commit_result_bundle(
        store,
        project_id=cb.PROJECT_ID,
        project_binding_ref=_PROJECT_BINDING_REF,
        protocol_freeze=protocol_freeze,
        raw_events=raw_events,
        environment_manifest=_ENVIRONMENT_MANIFEST,
        generated_at=_GENERATED_AT,
    )
    kwargs = {
        "project_binding_ref": _PROJECT_BINDING_REF,
        "protocol_freeze": protocol_freeze,
        "original_result_bundle": original_bundle,
        "reproducer_identity": {"reproducer": "reproducer-a", "is_original_author": False},
        "reproduced_raw_events": raw_events,
        "generated_at": _GENERATED_AT,
    }

    first = cb_route.commit_reproduction_receipt(store, project_id=cb.PROJECT_ID, **kwargs)
    second = cb_route.commit_reproduction_receipt(store, project_id=cb.PROJECT_ID, **kwargs)
    assert first == second
    assert first["agreement"] == "MATCH"

    resolved = cb_route.resolve_reproduction_receipt(
        store,
        project_id=cb.PROJECT_ID,
        reproduction_receipt_id=first["reproduction_receipt_id"],
    )
    assert resolved == first
