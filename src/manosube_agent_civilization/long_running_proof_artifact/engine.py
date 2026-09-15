"""Pure record builder for the Long-Running Proof Artifact Bundle (Issue #86 section 10,
P87-R1-F8).

Performs no Store I/O, reads no clock, and trusts every input as already assembled and
verified by its own caller -- the identical discipline every other package's own ``engine.py``
module docstring states (see ``work_time_transparency/engine.py``). In particular, this module
never imports from ``tests.long_running_proof`` -- the raw event log, the derived metric
dataset, and every other input below are computed by that test-only orchestrator and handed in
here as plain, already-canonical data, so this production package stays reusable and
independent of any one test harness's own internal shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as _CANONICAL_SCHEMA_BASE,
    validate_record as _validate_record,
)

from .errors import ArtifactBundleValidationError
from .identity import artifact_bundle_id, artifact_bundle_semantic_fingerprint

SCHEMA_VERSION = "0.1"
LONG_RUNNING_PROOF_ARTIFACT_SCHEMA_BASE = _CANONICAL_SCHEMA_BASE + "long_running_proof_artifact/"


def _detach(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _detach(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_detach(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_detach(item) for item in value)
    return value


def stringify_floats(value: Any) -> Any:
    """Recursively replace every ``float`` in *value* with ``repr(value)`` -- Python's own
    shortest round-tripping decimal representation -- leaving every other JSON-representable
    value untouched.

    :mod:`~manosube_agent_civilization.state.canonicalize`'s own ``MANOSUBE-CANONICAL-JSON-0.1``
    profile prohibits floating-point values outright (this repository's own
    ``UnsupportedValueError``), so :mod:`~tests.long_running_proof.metrics`'s own rate/duration
    floats can never be embedded in this bundle's content-addressed body as-is. This is the one
    deterministic, lossless (``float(repr(x)) == x`` for every finite ``x`` Python can produce)
    encoding this package uses -- callers proving raw-to-summary derivation equality after reload
    must apply this identical function to a freshly recomputed metric dataset before comparing it
    to the reloaded bundle's own ``metrics`` field, never compare raw floats to this field
    directly."""

    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, Mapping):
        return {key: stringify_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [stringify_floats(item) for item in value]
    return value


def _validate(record: dict[str, Any], schema_name: str, context: str) -> None:
    try:
        _validate_record(record, schema_name, base=LONG_RUNNING_PROOF_ARTIFACT_SCHEMA_BASE)
    except DifferenceValidationError as error:
        raise ArtifactBundleValidationError(f"{context}: {error}") from error


def build_artifact_bundle(
    *,
    project_id: str,
    project_binding_ref: Mapping[str, str],
    tier: int,
    corpus_manifest: Mapping[str, Any],
    lineage_refs: Mapping[str, Any],
    raw_events: list[Mapping[str, Any]],
    metrics: Mapping[str, Any],
    session_loss_receipts: list[Mapping[str, Any]],
    agent_swap_refs: list[Mapping[str, Any]],
    runtime_observation_refs: list[Mapping[str, Any]],
    environment_manifest: Mapping[str, Any],
    reproduction_procedure: Mapping[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Build one canonical ``long_running_proof_artifact_bundle`` record -- Issue #86 section
    10's own required canonical outputs, gathered into one immutable, content-addressed,
    schema-validated bundle.

    This builder never becomes a new owner of Canonical State, Authority, Evidence, Reflow, or
    Completion (Issue #86 section 11, restated by SHUKOU's own P87-R1-F8 adoption): it commits
    no Project State transition itself (see ``route.py``), and every fact embedded here is
    already-committed data this bundle only republishes for durable, versioned, tamper-evident
    reading -- never a second, competing source of truth for any of it."""

    project_id = str(project_id)
    project_binding_ref = _detach(project_binding_ref)
    corpus_manifest = _detach(corpus_manifest)
    lineage_refs = _detach(lineage_refs)
    raw_events = _detach(raw_events)
    metrics = stringify_floats(_detach(metrics))
    session_loss_receipts = _detach(session_loss_receipts)
    agent_swap_refs = _detach(agent_swap_refs)
    runtime_observation_refs = _detach(runtime_observation_refs)
    environment_manifest = _detach(environment_manifest)
    reproduction_procedure = _detach(reproduction_procedure)

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_bundle_id": "",
        "artifact_bundle_semantic_fingerprint": "",
        "project_id": project_id,
        "project_binding_ref": project_binding_ref,
        "tier": tier,
        "corpus_manifest": corpus_manifest,
        "lineage_refs": lineage_refs,
        "raw_events": raw_events,
        "metrics": metrics,
        "session_loss_receipts": session_loss_receipts,
        "agent_swap_refs": agent_swap_refs,
        "runtime_observation_refs": runtime_observation_refs,
        "environment_manifest": environment_manifest,
        "reproduction_procedure": reproduction_procedure,
        "generated_at": generated_at,
    }
    record["artifact_bundle_id"] = artifact_bundle_id(record)
    record["artifact_bundle_semantic_fingerprint"] = artifact_bundle_semantic_fingerprint(record)
    _validate(
        record,
        "long_running_proof_artifact_bundle.schema.json",
        "generated long_running_proof_artifact_bundle",
    )
    return record


__all__ = [
    "LONG_RUNNING_PROOF_ARTIFACT_SCHEMA_BASE",
    "SCHEMA_VERSION",
    "build_artifact_bundle",
    "stringify_floats",
]
