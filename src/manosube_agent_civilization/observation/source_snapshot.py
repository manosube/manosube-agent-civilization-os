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

from manosube_agent_civilization.schema_context import CanonicalSchemaContext

from .errors import ObservationError, ObservationValidationError
from .identity import deterministic_id
from .schemas import OBSERVATION_SCHEMA_BASE, observation_schema_errors
from .scope import validate_source_locator

#: The one canonical Source Snapshot schema ``$id``, named once here. Every Source Snapshot
#: schema validation anywhere in this repository -- this module's own producer and resolver,
#: and ``binding.admission``'s own pre-commit reverification of an ``additional_genesis_
#: records`` member -- goes through :func:`validate_source_snapshot_body` below rather than
#: restating this id and re-deriving a validator of its own
#: (``SOURCE_SNAPSHOT_IDENTITY_OWNER_COUNT=1``,
#: ``BINDING_INVENTED_OBSERVATION_VALIDATION=false``, Issue #75 KSI-C3).
SOURCE_SNAPSHOT_SCHEMA_ID = OBSERVATION_SCHEMA_BASE + "source_snapshot.schema.json"

_SOURCE_SNAPSHOT_SCALARS: tuple[str, ...] = (
    "source_locator",
    "content_digest",
    "captured_at",
    "git_provenance",
)

#: The five fields a real Git provenance claim carries -- R9-F2 (Phase 7 structural-review
#: round 9): "Source Snapshotはimmutableまたはcontent-addressed であり、少なくとも該当する
#: Git provenanceを再検証できなければならない" (SHUKOU's own text). A ``None`` value keeps
#: every existing, non-Kernel-sourced Source Snapshot use schema-valid unchanged; a
#: Kernel-source-provenance use (``reflow/route.py``'s own G4 resolution) requires it
#: present, checked there against the exact same real Git object witness
#: (:mod:`~manosube_agent_civilization.reflow.git_witness`) the candidate side already
#: verifies -- this module never re-implements that verification a second time.
_GIT_PROVENANCE_FIELDS: tuple[str, ...] = ("repository", "commit_sha", "tree_sha", "path", "blob_sha")


def source_snapshot_identity(record: dict[str, Any]) -> str:
    """Return the content address a Source Snapshot's own payload implies."""

    return deterministic_id("SRC-SNAP", {key: record[key] for key in _SOURCE_SNAPSHOT_SCALARS})


def validate_source_snapshot_body(
    record: dict[str, Any],
    *,
    context_label: str,
    schema_context: CanonicalSchemaContext | None = None,
) -> None:
    """Schema-validate one Source Snapshot body against Observation's own schema, or raise
    :class:`~manosube_agent_civilization.observation.errors.ObservationValidationError`.

    The one Source Snapshot schema validation in this repository (Issue #75 KSI-C3). Both of
    this module's own callers and ``binding.admission``'s own pre-commit reverification of an
    ``additional_genesis_records`` member reach the identical schema id, the identical
    validator resolution, and the identical fail-closed semantics through here -- Binding
    receives and passes a validation context but never reimplements the Source Snapshot
    schema, identity, or validation semantics.

    *context_label* names the body being rejected in the raised message ("generated
    source_snapshot", "resolved source_snapshot", "additional genesis record
    source_snapshot/<id>"), so each caller keeps its own precise diagnostic without owning a
    second copy of the validation itself.

    With *schema_context* supplied, the captured, digest-verified bytes that context already
    parsed are the bytes that validate -- never a later filesystem read.
    """

    errors = observation_schema_errors(
        record, SOURCE_SNAPSHOT_SCHEMA_ID, schema_context=schema_context
    )
    if errors:
        raise ObservationValidationError(f"{context_label} is schema-invalid: {errors[0].message}")


def build_source_snapshot(
    *,
    source_locator: str,
    content_digest: str,
    captured_at: str,
    git_provenance: dict[str, str] | None = None,
    schema_context: CanonicalSchemaContext | None = None,
) -> dict[str, Any]:
    """Return one schema-conformant, content-addressed ``source_snapshot`` record.

    *source_locator* is validated the same way an Observation's own source occurrences
    already are (:func:`~manosube_agent_civilization.observation.scope.validate_source_locator`)
    -- a relative, non-secret-bearing locator, never an absolute path or URL standing in for
    identity on its own. *content_digest* must be an explicit ``sha256:`` digest of the
    snapshotted content bytes: the one field that makes this record's identity actually bind
    to content rather than to a caller's bare say-so about what a locator contained.

    *git_provenance*, when supplied, is the ``{repository, commit_sha, tree_sha, path,
    blob_sha}`` claim R9-F2 adds -- itself part of this record's own content address (a
    caller cannot silently attach a different Git claim to an otherwise-identical
    snapshot), independently re-verifiable by a real Git object witness at the point this
    record is used for Kernel-source provenance, never trusted here as a bare assertion.

    *schema_context* (Issue #75 KSI-C2), when supplied, is the one Kernel-owned
    :class:`~manosube_agent_civilization.schema_context.CanonicalSchemaContext` whose own
    captured, digest-verified bytes validate the generated record -- this function then
    resolves no schema root and reads no ``*.schema.json`` file of any kind.
    """

    validate_source_locator(source_locator)
    if not isinstance(content_digest, str) or not content_digest.startswith("sha256:"):
        raise ObservationError("source_snapshot content_digest must be an explicit sha256: digest")
    if git_provenance is not None and set(git_provenance) != set(_GIT_PROVENANCE_FIELDS):
        raise ObservationError(
            f"source_snapshot git_provenance must carry exactly {sorted(_GIT_PROVENANCE_FIELDS)}"
        )
    record: dict[str, Any] = {
        "schema_version": "0.1",
        "source_snapshot_id": "",
        "source_locator": source_locator,
        "content_digest": content_digest,
        "captured_at": captured_at,
        "git_provenance": dict(git_provenance) if git_provenance is not None else None,
    }
    record["source_snapshot_id"] = source_snapshot_identity(record)
    validate_source_snapshot_body(
        record, context_label="generated source_snapshot", schema_context=schema_context
    )
    return record


def resolve_source_snapshot(
    ref: dict[str, Any],
    pool: list[dict[str, Any]],
    *,
    schema_context: CanonicalSchemaContext | None = None,
) -> dict[str, Any]:
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

    *schema_context* (Issue #75 KSI-C2), when supplied, is the one Kernel-owned
    :class:`~manosube_agent_civilization.schema_context.CanonicalSchemaContext` whose own
    captured, digest-verified bytes validate the resolved record -- so a resolution that
    happens arbitrarily long after capture still validates against the bytes that were
    verified, never against whatever the schema directory holds at resolution time.
    """

    ref_id = ref.get("id")
    record = next((item for item in pool if item.get("source_snapshot_id") == ref_id), None)
    if record is None:
        raise ObservationError(
            f"source_snapshot ref does not resolve to any supplied record: {ref_id!r}"
        )
    validate_source_snapshot_body(
        record, context_label="resolved source_snapshot", schema_context=schema_context
    )
    if record["source_snapshot_id"] != ref_id:
        raise ObservationError("resolved source_snapshot record's own id does not match its ref")
    if record["source_snapshot_id"] != source_snapshot_identity(record):
        raise ObservationError("resolved source_snapshot record's id does not recompute")
    validate_source_locator(record["source_locator"])
    return record
