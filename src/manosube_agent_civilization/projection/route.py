"""The one public Projection route (Phase 14, Issue #62).

``PROJECTION_OWNER_COUNT=1``, ``PUBLIC_PROJECTION_ENTRY_POINT_COUNT=1``.

``project_to_github`` resolves an already-real canonical subject (an ``observation_evidence``
record through the existing Store's own read-only
:meth:`~manosube_agent_civilization.store.file_store.FileStateStore.resolve_record` -- the
identical surface Boot and Independent Verification already call, never a second one),
re-verifies the caller's explicit ``github_authority_ref`` against the existing Boot owner's
own real, re-verified ``human_authority_ref`` (the identical pattern Independent
Verification's own Structural Review Round 1, P13-R1-F2, already established), derives a
deterministic Projection Envelope, and either reuses an already-committed Envelope at the
identical projection identity or persists a genuinely new one through the existing Store's
own single sanctioned committer
(:func:`~manosube_agent_civilization.store.commit.commit_state_transition` -- the identical
primitive Reflow and Binding already share). It creates no second State, Evidence, Difference,
Authority, Store, or Closure owner, and calls into no existing owner beyond ``boot`` (Human
Authority re-verification) and, only for the caller's own subsequent
:func:`~manosube_agent_civilization.projection.receipt_handoff.
route_observation_receipt_to_evidence` call, ``evidence``.

Canonical route (``PROJECTION_CONTRACT.md`` §5):

```text
canonical Difference / Change / Evidence subject
→ real subject resolved and its own fingerprint recomputed (never trusted from a caller)
→ deterministic Projection Envelope mapping key
→ existing canonical persistence boundary (store.resolve_record) -- reuse-or-conflict lookup
→ explicit GitHub Authority check (Boot-verified human_authority_ref)
→ GitHub Adapter materialize (only on a genuinely new mapping key)
→ external GitHub artifact
→ bounded GitHub re-observation (GitHub Adapter observe)
→ GitHub Observation Receipt
→ existing canonical persistence boundary (commit_state_transition) -- the new Envelope
→ caller's own subsequent hand-off to the existing Evidence owner
```

Idempotency and conflict semantics (Issue #62's own minimum-acceptable-after-state items 5-6):
a request whose (subject, subject fingerprint, projection kind, target repository) already
resolves to a committed Envelope never calls
:meth:`~manosube_agent_civilization.projection.types.GitHubAdapter.materialize` again -- it
calls :meth:`~manosube_agent_civilization.projection.types.GitHubAdapter.observe` against the
already-recorded ``external_artifact_ref`` instead, and returns the existing Envelope
unmodified, provided the caller's own ``projection_payload_fingerprint`` (always recomputed
here, never trusted from a caller) exactly matches what that Envelope already committed. A
mismatch raises :class:`~manosube_agent_civilization.projection.errors.
ConflictingProjectionPayloadError` before any adapter call and with zero Store writes.

**Disclosed scope boundary.** Only an ``observation_evidence`` subject is resolved and
fingerprinted by this route itself -- ``difference`` and ``change`` are never Store-owned
record kinds in this vertical (``reflow/reference_registry.py``'s own documented
classification; Independent Verification's own route already carries the identical
boundary for its own ``target_refs``), so a ``difference``/``change`` subject's
*subject_fingerprint* must be supplied by the caller, who already holds the real record it
was derived from. Deriving a Difference/Change subject fingerprint independently within this
route would require a second State/Difference reconstruction this route does not perform and
Issue #62's own prohibitions forbid inventing (``PARALLEL_CANONICAL_OWNER=false``); it is
recorded here as a disclosed boundary, not silently narrowed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.evidence.identity import (
    evidence_semantic_fingerprint as _evidence_semantic_fingerprint,
)
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition

from .engine import PROJECTION_SCHEMA_BASE, derive_projection_envelope
from .errors import (
    ConflictingProjectionPayloadError,
    ProjectionAdapterError,
    ProjectionRequirementError,
)
from .identity import projection_mapping_key, projection_payload_fingerprint
from .types import (
    ARTIFACT_KINDS,
    PROJECTION_KINDS,
    SUBJECT_REF_KINDS,
    GitHubAdapter,
    GitHubObservationReceipt,
)

_STORE_RESOLVABLE_SUBJECT_KIND = "observation_evidence"
_ENVELOPE_RECORD_KIND = "projection_envelope"

#: Which subject kind each projection kind requires (Issue #62 §"Canonical route": Difference
#: projects to an Issue, Change projects to a Pull Request, Evidence projects to a check/
#: review/artifact).
_REQUIRED_SUBJECT_KIND: dict[str, str] = {
    "DIFFERENCE_ISSUE": "difference",
    "CHANGE_PULL_REQUEST": "change",
    "EVIDENCE_ARTIFACT": "observation_evidence",
}


def _require_canonical_identity(name: str, value: Any) -> str:
    """Fail closed unless *value* is a plain, non-empty canonical identity string -- the
    identical convention Boot and Independent Verification's own routes already use."""

    if not isinstance(value, str) or not value:
        raise ProjectionRequirementError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise ProjectionRequirementError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def _require_reference(
    value: Any, *, context: str, allowed_kinds: frozenset[str] | None = None
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProjectionRequirementError(
            f"{context} must be an explicit reference object: {value!r}"
        )
    kind = value.get("kind")
    identity = value.get("id")
    if not isinstance(kind, str) or not kind:
        raise ProjectionRequirementError(f"{context} carries no readable kind: {value!r}")
    if not isinstance(identity, str) or not identity:
        raise ProjectionRequirementError(f"{context} carries no readable id: {value!r}")
    if allowed_kinds is not None and kind not in allowed_kinds:
        raise ProjectionRequirementError(
            f"{context} names a kind outside its permitted set: {kind!r} not in {sorted(allowed_kinds)}"
        )
    return dict(value)


def _canonical_reference_equal(left: Any, right: Any, *, context: str) -> None:
    if dict(left) != dict(right):
        raise ProjectionRequirementError(f"{context}: {dict(left)!r} != {dict(right)!r}")


def _require_external_artifact_ref(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProjectionAdapterError(f"{context} must be an explicit mapping, not {value!r}")
    for key in ("host", "owner", "repo", "artifact_kind", "external_id", "url"):
        if not isinstance(value.get(key), str) or not value[key]:
            raise ProjectionAdapterError(
                f"{context}.{key} must be a non-empty string: {value.get(key)!r}"
            )
    if value["artifact_kind"] not in ARTIFACT_KINDS:
        raise ProjectionAdapterError(
            f"{context}.artifact_kind is unrecognized: {value['artifact_kind']!r}"
        )
    return dict(value)


def project_to_github(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    subject_ref: Mapping[str, Any],
    projection_kind: str,
    target_repository: Mapping[str, Any],
    projection_payload: Mapping[str, Any],
    github_authority_ref: Mapping[str, Any],
    materialized_at: str,
    adapter: GitHubAdapter,
    subject_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Project one canonical subject to GitHub and return
    ``{"envelope": ..., "receipt": GitHubObservationReceipt, "reused": bool}``.

    *subject_fingerprint* is required (and, if given for an ``observation_evidence`` subject,
    cross-checked rather than trusted) only for a ``difference``/``change`` subject -- see the
    module docstring's disclosed scope boundary. *materialized_at* is a required, caller-
    supplied instant (this route reads no clock, the identical discipline Evidence's own
    ``derive_evidence`` already requires of its own "recording instant").

    See ``09_PROJECTION/PROJECTION_CONTRACT.md`` §5 for the full canonical route this function
    implements, step by step.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)

    checked_subject_ref = _require_reference(
        subject_ref, context="subject_ref", allowed_kinds=SUBJECT_REF_KINDS
    )
    if projection_kind not in PROJECTION_KINDS:
        raise ProjectionRequirementError(
            f"projection_kind is not a recognized kind: {projection_kind!r}"
        )
    if checked_subject_ref["kind"] != _REQUIRED_SUBJECT_KIND[projection_kind]:
        raise ProjectionRequirementError(
            f"projection_kind {projection_kind!r} requires a "
            f"{_REQUIRED_SUBJECT_KIND[projection_kind]!r} subject, not "
            f"{checked_subject_ref['kind']!r}"
        )
    if not isinstance(target_repository, Mapping) or target_repository.get("host") != "github":
        raise ProjectionRequirementError(
            f"target_repository must declare host='github': {target_repository!r}"
        )
    for key in ("owner", "repo"):
        if not isinstance(target_repository.get(key), str) or not target_repository[key]:
            raise ProjectionRequirementError(f"target_repository.{key} must be a non-empty string")
    if not isinstance(projection_payload, Mapping):
        raise ProjectionRequirementError(
            f"projection_payload must be an explicit mapping: {projection_payload!r}"
        )

    # P13-R1-F2's own pattern: the caller's github_authority_ref is trusted only once it
    # canonical-reference-equals the real, independently re-verified Human Authority
    # reference the existing Boot owner returns for this exact project/binding. Every
    # boot_project failure propagates unchanged; this route calls the adapter zero times on
    # any such rejection.
    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    real_human_authority_ref = dict(boot_context.human_authority_ref)
    _canonical_reference_equal(
        github_authority_ref,
        real_human_authority_ref,
        context="github_authority_ref vs the real, Boot-verified Human Authority reference",
    )

    if checked_subject_ref["kind"] == _STORE_RESOLVABLE_SUBJECT_KIND:
        resolved_subject = store.resolve_record(
            project_id, checked_subject_ref["kind"], checked_subject_ref["id"]
        )
        if resolved_subject is None:
            raise ProjectionRequirementError(
                f"subject_ref does not resolve for project {project_id!r}: "
                f"{checked_subject_ref['kind']}/{checked_subject_ref['id']}"
            )
        real_subject_fingerprint = _evidence_semantic_fingerprint(resolved_subject)
        if subject_fingerprint is not None and subject_fingerprint != real_subject_fingerprint:
            raise ProjectionRequirementError(
                "supplied subject_fingerprint does not match the real, recomputed fingerprint "
                f"of the resolved subject: {subject_fingerprint!r} != {real_subject_fingerprint!r}"
            )
    else:
        if not isinstance(subject_fingerprint, str) or not subject_fingerprint:
            raise ProjectionRequirementError(
                f"subject_fingerprint is required for a {checked_subject_ref['kind']!r} "
                "subject -- this route does not resolve or reconstruct a difference/change "
                "record itself (see the module docstring's disclosed scope boundary)"
            )
        real_subject_fingerprint = subject_fingerprint

    real_target_repository = {
        "host": "github",
        "owner": target_repository["owner"],
        "repo": target_repository["repo"],
    }
    mapping_key = projection_mapping_key(
        checked_subject_ref, real_subject_fingerprint, projection_kind, real_target_repository
    )
    real_payload_fingerprint = projection_payload_fingerprint(dict(projection_payload))

    existing = store.resolve_record(project_id, _ENVELOPE_RECORD_KIND, mapping_key)
    if existing is not None:
        if existing["projection_payload_fingerprint"] != real_payload_fingerprint:
            raise ConflictingProjectionPayloadError(
                f"projection identity {mapping_key!r} already resolves to a committed "
                "Envelope with a different projection_payload_fingerprint: "
                f"{existing['projection_payload_fingerprint']!r} != {real_payload_fingerprint!r}"
            )
        receipt = _observe(
            adapter,
            envelope_id=mapping_key,
            subject_ref=checked_subject_ref,
            external_artifact_ref=existing["external_artifact_ref"],
            github_authority_ref=real_human_authority_ref,
        )
        return {"envelope": existing, "receipt": receipt, "reused": True}

    declared_identity = getattr(adapter, "adapter_identity", None)
    if not isinstance(declared_identity, Mapping):
        raise ProjectionAdapterError(
            "adapter does not declare a readable adapter_identity attribute -- an unstated "
            "or unverifiable identity may never materialize or observe on this route's behalf"
        )

    external_artifact_ref = adapter.materialize(
        projection_kind=projection_kind,
        target_repository=real_target_repository,
        payload=dict(projection_payload),
    )
    checked_artifact_ref = _require_external_artifact_ref(
        external_artifact_ref, context="adapter.materialize() return value"
    )

    envelope = derive_projection_envelope(
        subject_ref=checked_subject_ref,
        subject_fingerprint=real_subject_fingerprint,
        projection_kind=projection_kind,
        target_repository=real_target_repository,
        projection_payload=dict(projection_payload),
        projection_payload_fingerprint=real_payload_fingerprint,
        external_artifact_ref=checked_artifact_ref,
        github_authority_ref=real_human_authority_ref,
        materialized_at=materialized_at,
    )
    if envelope["projection_envelope_id"] != mapping_key:
        raise ProjectionRequirementError(
            "newly derived envelope's own identity does not equal the mapping key computed "
            f"before materialization: {envelope['projection_envelope_id']!r} != {mapping_key!r}"
        )

    current_state = store.load_current(project_id)
    transaction_id = f"TX-PROJECTION-ENVELOPE-{envelope['projection_envelope_id']}"
    next_state = dict(current_state)
    next_state["state_revision"] = current_state["state_revision"] + 1
    next_state["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
    next_state["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
    next_state["semantic_fingerprint"] = fingerprint_project_state(next_state).as_dict()
    transition = {
        "schema_version": "0.1",
        "transaction_id": transaction_id,
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": current_state["state_revision"],
        "to_revision": next_state["state_revision"],
        "before_fingerprint": current_state["semantic_fingerprint"],
        "after_fingerprint": next_state["semantic_fingerprint"],
        "after_state": next_state,
        "evidence_refs": [],
        "committed_at": materialized_at,
    }
    commit_state_transition(
        store,
        project_id,
        current_state["state_revision"],
        current_state["semantic_fingerprint"],
        next_state,
        transition,
        records=[(_ENVELOPE_RECORD_KIND, envelope["projection_envelope_id"], envelope)],
    )

    receipt = _observe(
        adapter,
        envelope_id=envelope["projection_envelope_id"],
        subject_ref=checked_subject_ref,
        external_artifact_ref=checked_artifact_ref,
        github_authority_ref=real_human_authority_ref,
    )
    return {"envelope": envelope, "receipt": receipt, "reused": False}


def _observe(
    adapter: GitHubAdapter,
    *,
    envelope_id: str,
    subject_ref: dict[str, Any],
    external_artifact_ref: dict[str, Any],
    github_authority_ref: dict[str, Any],
) -> GitHubObservationReceipt:
    """Call the adapter's own ``observe`` exactly once and return one immutable
    :class:`~manosube_agent_civilization.projection.types.GitHubObservationReceipt`."""

    result = adapter.observe(external_artifact_ref=external_artifact_ref)
    if not isinstance(result, Mapping):
        raise ProjectionAdapterError(f"adapter.observe() returned {result!r}, not a mapping")
    exists = result.get("exists")
    if not isinstance(exists, bool):
        raise ProjectionAdapterError(f"adapter.observe()'s own 'exists' must be a bool: {exists!r}")
    status: str
    if exists is False:
        status = "FAILED"
    else:
        reported_status = result.get("status")
        if not isinstance(reported_status, str):
            raise ProjectionAdapterError(
                f"adapter.observe()'s own 'status' must be a string: {reported_status!r}"
            )
        status = reported_status
    observations = {
        "exists": exists,
        "observed_content_fingerprint": result.get("observed_content_fingerprint"),
        "observed_at": result.get("observed_at"),
    }
    return GitHubObservationReceipt(
        status=status,
        projection_envelope_id=envelope_id,
        subject_ref=subject_ref,
        external_artifact_ref=external_artifact_ref,
        adapter_identity=dict(adapter.adapter_identity),
        github_authority_ref=github_authority_ref,
        input_refs=(dict(subject_ref),),
        observations=observations,
    )


__all__ = ["PROJECTION_SCHEMA_BASE", "project_to_github"]
