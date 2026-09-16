"""Canonical commit/resolve entrypoints for the Long-Running Proof Artifact Bundle (Issue #86
section 10, P87-R1-F8).

**This is not a Change Executor, not an Evidence producer, and not a Canonical State owner.**
Every bundle this module commits goes through the Store's own orthogonal, append-only
coordination ledger -- :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.
commit_coordination_record_at_tip`, the identical mechanism ``work_time_transparency/route.py``
already established (P84-R2-F1/F4, hardened P84-R3-F1) -- never
:func:`~manosube_agent_civilization.store.commit.commit_state_transition`. A bundle commit
therefore never reads or advances ``state_revision``, never touches ``semantic_fingerprint``/
``lineage_head_ref``, and stages no Project-State transition: it cannot mutate or authorize
canonical Project State, Authority, Evidence, Reflow, or Completion, structurally, since no code
path here ever reaches ``commit_state_transition``/``store.commit`` at all (Issue #86 section 11,
restated by SHUKOU's own P87-R1-F8 adoption: "the artifact must never become a new owner of
Project Completion, Evidence sufficiency, or Canonical State").

Each bundle is committed as the single, self-chained entry of its own coordination chain
(``chain_id == artifact_bundle_id``, ``expected_predecessor=None``): a run's bundle is an
immutable, once-published fact, never a sequence of updates the way a Work Coordination's own
``open``/``update``/``terminal`` chain is. A retry that recomputes and re-commits the identical
bundle for the identical run is an idempotent replay (the Store's own existing same-id-same-body
tolerance); a second, differently-bodied bundle for the identical run's own
``artifact_bundle_id`` collides and is refused (:class:`~manosube_agent_civilization.store.
errors.RecordConflictError`) -- a run's own artifact bundle is published exactly once.

:func:`resolve_artifact_bundle` is a thin, direct wrapper over :meth:`~manosube_agent_civilization
.store.file_store.FileStateStore.resolve_coordination_record`, which is this bundle's own
required reload/tamper-refusal proof: it always re-derives the bundle's authoritative body from
the coordination ledger itself, never trusts a materialized cache file on its own, and raises
:class:`~manosube_agent_civilization.store.errors.CorruptStoreError` if a directly-edited on-disk
copy of the materialized cache diverges from that ledger fact."""

from __future__ import annotations

from typing import Any, cast

from .engine import build_artifact_bundle

RECORD_KIND = "long_running_proof_artifact_bundle"


def commit_artifact_bundle(store: Any, *, project_id: str, **build_kwargs: Any) -> dict[str, Any]:
    """Build one canonical artifact bundle for this run and durably commit it as the single
    entry of its own coordination chain, keyed by its own deterministic ``artifact_bundle_id``.

    *build_kwargs* are passed through unchanged to
    :func:`~manosube_agent_civilization.long_running_proof_artifact.engine.build_artifact_bundle`
    (every field this package's own schema requires except ``project_id``, which this route
    also threads through to the Store as the coordination ledger's own project scope)."""

    record = build_artifact_bundle(project_id=project_id, **build_kwargs)
    bundle_id = record["artifact_bundle_id"]
    return cast(
        "dict[str, Any]",
        store.commit_coordination_record_at_tip(
            project_id,
            bundle_id,
            RECORD_KIND,
            bundle_id,
            record,
            expected_predecessor=None,
        ),
    )


def resolve_artifact_bundle(
    store: Any, *, project_id: str, artifact_bundle_id: str
) -> dict[str, Any] | None:
    """The permanent, committed artifact bundle body for *artifact_bundle_id*, or ``None`` if
    no such bundle has ever been committed -- always re-derived from the coordination ledger's
    own authoritative fact, never a materialized cache file trusted on its own (this bundle's
    own required ``ARTIFACT_BUNDLE_RELOAD_PROOF``/``ARTIFACT_TAMPER_REFUSAL`` boundary)."""

    result = store.resolve_coordination_record(project_id, RECORD_KIND, artifact_bundle_id)
    return cast("dict[str, Any] | None", result)


__all__ = ["RECORD_KIND", "commit_artifact_bundle", "resolve_artifact_bundle"]
