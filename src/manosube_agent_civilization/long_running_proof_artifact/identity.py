"""Deterministic identity and content-addressing for the Long-Running Proof Artifact Bundle
(Issue #86 section 10, P87-R1-F8).

Reads the single canonical serializer, :func:`~manosube_agent_civilization.state.canonicalize.
canonical_json_bytes`, exactly as every other package's own ``identity.py`` does -- see
``work_time_transparency/identity.py``'s module docstring for why this repository never lets a
second serializer exist.

Two distinct hashes, deliberately kept apart (P87-R1-F9's own lesson: never mix real-time
nondeterminism into a corpus's deterministic identity):

* :func:`artifact_bundle_id` is a pure function of *which run this bundle is for* --
  ``project_id``, ``project_binding_ref``, ``tier``, and the run's own committed lineage
  identity (``lineage_refs``) -- deliberately excluding ``generated_at`` and every other
  genuinely nondeterministic observation, so two commit attempts describing the identical
  completed run collide at the identical Store coordination-ledger slot (idempotent replay),
  while two runs whose corpora actually diverged (different lineage identity) never share a
  slot.
* :func:`artifact_bundle_semantic_fingerprint` is a full content address over every field of
  the bundle, deliberately including ``generated_at``/``raw_events``/``metrics`` -- the actual
  content-address the bundle's own reload/tamper-refusal proof (F8) checks, not a
  reproducibility key.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

#: The fields that identify *which run* a bundle describes -- see the module docstring.
BUNDLE_ID_FIELDS: tuple[str, ...] = (
    "project_id",
    "project_binding_ref",
    "tier",
    "lineage_refs",
)

#: Every field of the committed bundle body except the two self-referential identity fields
#: (``artifact_bundle_id``, ``artifact_bundle_semantic_fingerprint`` themselves) -- the full
#: content this bundle's own fingerprint addresses.
BUNDLE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "tier",
    "run_outcome",
    "corpus_manifest",
    "lineage_refs",
    "raw_events",
    "metrics",
    "session_loss_receipts",
    "agent_swap_refs",
    "runtime_observation_refs",
    "environment_manifest",
    "reproduction_procedure",
    "generated_at",
)


def _projection(record: Mapping[str, Any], fields: tuple[str, ...], *, kind: str) -> dict[str, Any]:
    missing = [field for field in fields if field not in record]
    if missing:
        raise KeyError(
            f"{kind} carries no readable {', '.join(missing)} -- its own identity cannot be "
            "recomputed"
        )
    return {field: record[field] for field in fields}


def artifact_bundle_id(record: Mapping[str, Any]) -> str:
    """The one deterministic id this run's artifact bundle ever has -- see the module
    docstring for exactly which fields this excludes and why."""

    payload = _projection(record, BUNDLE_ID_FIELDS, kind="long_running_proof_artifact_bundle")
    return "LRPA-" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def artifact_bundle_semantic_fingerprint(record: Mapping[str, Any]) -> str:
    """A full content address over every field of *record* except its own two identity
    fields -- the bundle's own ``ARTIFACT_TAMPER_REFUSAL`` proof recomputes this after reload
    and requires it to still match the embedded value."""

    projection = _projection(
        record, BUNDLE_SEMANTIC_FIELDS, kind="long_running_proof_artifact_bundle"
    )
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


__all__ = [
    "BUNDLE_ID_FIELDS",
    "BUNDLE_SEMANTIC_FIELDS",
    "artifact_bundle_id",
    "artifact_bundle_semantic_fingerprint",
]
