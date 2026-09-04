"""Canonical Source Snapshot -- owned by Observation (R6-F1a, Phase 7 structural-review
round 6).

``00_KERNEL/02_STATE/STATE_METADATA.md`` section 5 gives ``source_snapshot_refs`` the only
constraint the frozen contract states anywhere for this reference kind: it must carry an
"immutable or content-addressed reference", never a mutable URL or branch name treated as a
complete snapshot identity ("Mutable URLやbranch名だけを完全なsnapshot identityとして扱わない"). It
defers the exact body schema to a later schema rather than let one be guessed. This module is
that later schema's producer: before it existed, every layer that carried a
``source_snapshot`` reference (Observation's own engine included) treated it as a permanently
opaque ``{kind, id}`` pair with no body anywhere to resolve it against -- structurally
indistinguishable from a caller stamping an arbitrary label on an unverifiable claim.

The identity is minted through the same domain-separated, content-addressed scheme every
other Observation-owned identity already uses (:func:`~manosube_agent_civilization.
observation.identity.deterministic_id`), not a second convention invented for this one kind:
``source_locator``/``content_digest``/``captured_at`` are the closed payload, so two snapshots
naming the same source, of the same content, captured at the same instant, are the same
record -- and any caller who does not actually hold that content cannot mint its id.
"""

from __future__ import annotations

from typing import Any

from .errors import ObservationError, ObservationValidationError
from .identity import deterministic_id
from .schemas import OBSERVATION_SCHEMA_BASE, validators
from .scope import validate_source_locator

_SOURCE_SNAPSHOT_SCALARS: tuple[str, ...] = ("source_locator", "content_digest", "captured_at")


def source_snapshot_identity(record: dict[str, Any]) -> str:
    """Return the content address a Source Snapshot's own payload implies."""

    return deterministic_id("SRC-SNAP", {key: record[key] for key in _SOURCE_SNAPSHOT_SCALARS})


def build_source_snapshot(
    *, source_locator: str, content_digest: str, captured_at: str
) -> dict[str, Any]:
    """Return one schema-conformant, content-addressed ``source_snapshot`` record.

    *source_locator* is validated the same way an Observation's own source occurrences
    already are (:func:`~manosube_agent_civilization.observation.scope.validate_source_locator`)
    -- a relative, non-secret-bearing locator, never an absolute path or URL standing in for
    identity on its own. *content_digest* must be an explicit ``sha256:`` digest of the
    snapshotted content bytes: the one field that makes this record's identity actually bind
    to content rather than to a caller's bare say-so about what a locator contained.
    """

    validate_source_locator(source_locator)
    if not isinstance(content_digest, str) or not content_digest.startswith("sha256:"):
        raise ObservationError("source_snapshot content_digest must be an explicit sha256: digest")
    record: dict[str, Any] = {
        "schema_version": "0.1",
        "source_snapshot_id": "",
        "source_locator": source_locator,
        "content_digest": content_digest,
        "captured_at": captured_at,
    }
    record["source_snapshot_id"] = source_snapshot_identity(record)
    validator = validators()[OBSERVATION_SCHEMA_BASE + "source_snapshot.schema.json"]
    errors = list(validator.iter_errors(record))
    if errors:
        raise ObservationValidationError(
            f"generated source_snapshot is schema-invalid: {errors[0].message}"
        )
    return record


def resolve_source_snapshot(ref: dict[str, Any], pool: list[dict[str, Any]]) -> dict[str, Any]:
    """Resolve *ref* (a ``{"kind": "source_snapshot", "id": ...}`` reference) against *pool*
    -- the caller-supplied Source Snapshot records for this Evaluation -- by exact id, then
    verify the resolved record is schema-valid and its own identity recomputes, failing
    closed on any mismatch. ID-only matching is refused by construction: a caller cannot
    supply a record under one id and reference it by another, nor supply a record whose own
    content does not actually produce the id it is filed under.

    R7-F6: schema validity and content-addressed identity alone do not prove
    ``source_locator`` is the "immutable or content-addressed reference"
    ``STATE_METADATA.md`` section 5 requires -- a caller who assembles a record directly
    (rather than through :func:`build_source_snapshot`) and recomputes its id correctly could
    otherwise carry a mutable URL, an absolute path, a parent-traversal locator, or one
    embedding a credential, and still resolve. The producer and the resolver now apply the
    identical locator semantics (:func:`~manosube_agent_civilization.observation.scope.
    validate_source_locator`), so a resolved record's ``source_locator`` is re-validated
    here exactly as it was at construction, never validated only once and then trusted
    forever after.
    """

    ref_id = ref.get("id")
    record = next((item for item in pool if item.get("source_snapshot_id") == ref_id), None)
    if record is None:
        raise ObservationError(
            f"source_snapshot ref does not resolve to any supplied record: {ref_id!r}"
        )
    validator = validators()[OBSERVATION_SCHEMA_BASE + "source_snapshot.schema.json"]
    errors = list(validator.iter_errors(record))
    if errors:
        raise ObservationValidationError(
            f"resolved source_snapshot is schema-invalid: {errors[0].message}"
        )
    if record["source_snapshot_id"] != ref_id:
        raise ObservationError("resolved source_snapshot record's own id does not match its ref")
    if record["source_snapshot_id"] != source_snapshot_identity(record):
        raise ObservationError("resolved source_snapshot record's id does not recompute")
    validate_source_locator(record["source_locator"])
    return record
