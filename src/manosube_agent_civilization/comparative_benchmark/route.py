"""Canonical commit/resolve entrypoints for the Comparative Benchmark package (Issue #89,
`ADOPT_PHASE_21_COMPARATIVE_BENCHMARK`).

**This is not a Change Executor, not an Evidence producer, and not a Canonical State owner.**
Every record this module commits goes through the Store's own orthogonal, append-only
coordination ledger -- `FileStateStore.commit_coordination_record_at_tip`, the identical
mechanism `long_running_proof_artifact/route.py` and `work_time_transparency/route.py` already
establish -- never `commit_state_transition`. A commit here therefore never reads or advances
`state_revision`, and stages no Project-State transition: this package structurally cannot
mutate or authorize canonical Project State, Authority, Evidence, Reflow, or Completion, since
no code path here ever reaches `commit_state_transition`/`store.commit` at all (Issue #89
section 7: "the benchmark must never become a new owner of Canonical State, Authority, Evidence
sufficiency, Reflow closure, or Project Completion"). MANOSUBE's own timing/WTT/artifact records
likewise never become Completion Evidence through this package -- there is deliberately no
`evidence_handoff.py` here.

Each of the three record kinds (protocol freeze, result bundle, reproduction receipt) is
committed as the single, self-chained entry of its own coordination chain
(`chain_id == <record>_id`, `expected_predecessor=None`): a same-id-same-body re-commit is an
idempotent replay; a same-id-different-body re-commit collides and is refused
(`RecordConflictError`) -- exactly the discipline that makes `POST_HOC_PROTOCOL_MUTATION_
ALLOWED=false` and `RAW_RESULT_DELETION_ALLOWED=false` structural facts, not merely stated
policy: a protocol freeze or a result bundle, once committed, is immutable at that identity.

Every `resolve_*` function is a thin, direct wrapper over `FileStateStore.
resolve_coordination_record`, which always re-derives the record's authoritative body from the
coordination ledger itself, never trusting a materialized cache file on its own."""

from __future__ import annotations

from typing import Any, cast

from .engine import build_protocol_freeze, build_reproduction_receipt, build_result_bundle

PROTOCOL_FREEZE_RECORD_KIND = "comparative_benchmark_protocol_freeze"
RESULT_BUNDLE_RECORD_KIND = "comparative_benchmark_result_bundle"
REPRODUCTION_RECEIPT_RECORD_KIND = "comparative_benchmark_reproduction_receipt"


def commit_protocol_freeze(store: Any, *, project_id: str, **build_kwargs: Any) -> dict[str, Any]:
    """Build and durably commit one protocol freeze -- must be called, and its return value's
    `protocol_freeze_id` bound into every later result bundle, before any benchmark result is
    executed or observed (`PROTOCOL_FROZEN_BEFORE_RESULTS=true`)."""

    record = build_protocol_freeze(project_id=project_id, **build_kwargs)
    freeze_id = record["protocol_freeze_id"]
    return cast(
        "dict[str, Any]",
        store.commit_coordination_record_at_tip(
            project_id,
            freeze_id,
            PROTOCOL_FREEZE_RECORD_KIND,
            freeze_id,
            record,
            expected_predecessor=None,
        ),
    )


def resolve_protocol_freeze(
    store: Any, *, project_id: str, protocol_freeze_id: str
) -> dict[str, Any] | None:
    result = store.resolve_coordination_record(
        project_id, PROTOCOL_FREEZE_RECORD_KIND, protocol_freeze_id
    )
    return cast("dict[str, Any] | None", result)


def commit_result_bundle(store: Any, *, project_id: str, **build_kwargs: Any) -> dict[str, Any]:
    """Build and durably commit one result bundle against an already-committed protocol
    freeze. *build_kwargs* must include `protocol_freeze` -- the caller's own already-resolved
    freeze body, never a freshly-rebuilt one -- so a result bundle can only ever bind to a
    freeze that genuinely exists in the ledger."""

    record = build_result_bundle(project_id=project_id, **build_kwargs)
    bundle_id = record["result_bundle_id"]
    return cast(
        "dict[str, Any]",
        store.commit_coordination_record_at_tip(
            project_id,
            bundle_id,
            RESULT_BUNDLE_RECORD_KIND,
            bundle_id,
            record,
            expected_predecessor=None,
        ),
    )


def resolve_result_bundle(
    store: Any, *, project_id: str, result_bundle_id: str
) -> dict[str, Any] | None:
    result = store.resolve_coordination_record(
        project_id, RESULT_BUNDLE_RECORD_KIND, result_bundle_id
    )
    return cast("dict[str, Any] | None", result)


def commit_reproduction_receipt(
    store: Any, *, project_id: str, **build_kwargs: Any
) -> dict[str, Any]:
    """Build and durably commit one independent reproduction receipt against an
    already-committed original result bundle. *build_kwargs* must include
    `original_result_bundle` -- the caller's own already-resolved bundle body, never a
    freshly-rebuilt one -- so a reproduction receipt can only ever bind to a bundle that
    genuinely exists in the ledger, and this route's own `engine.build_reproduction_receipt`
    always recomputes `agreement` itself rather than trusting any caller-supplied verdict."""

    record = build_reproduction_receipt(project_id=project_id, **build_kwargs)
    receipt_id = record["reproduction_receipt_id"]
    return cast(
        "dict[str, Any]",
        store.commit_coordination_record_at_tip(
            project_id,
            receipt_id,
            REPRODUCTION_RECEIPT_RECORD_KIND,
            receipt_id,
            record,
            expected_predecessor=None,
        ),
    )


def resolve_reproduction_receipt(
    store: Any, *, project_id: str, reproduction_receipt_id: str
) -> dict[str, Any] | None:
    result = store.resolve_coordination_record(
        project_id, REPRODUCTION_RECEIPT_RECORD_KIND, reproduction_receipt_id
    )
    return cast("dict[str, Any] | None", result)


__all__ = [
    "PROTOCOL_FREEZE_RECORD_KIND",
    "REPRODUCTION_RECEIPT_RECORD_KIND",
    "RESULT_BUNDLE_RECORD_KIND",
    "commit_protocol_freeze",
    "commit_reproduction_receipt",
    "commit_result_bundle",
    "resolve_protocol_freeze",
    "resolve_reproduction_receipt",
    "resolve_result_bundle",
]
