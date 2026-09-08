"""The one public Projection route (Phase 14, Issue #62).

``PROJECTION_OWNER_COUNT=1``, ``PUBLIC_PROJECTION_ENTRY_POINT_COUNT=1``.

``project_to_github`` resolves an already-real canonical subject (an ``observation_evidence``
record through the existing Store's own read-only
:meth:`~manosube_agent_civilization.store.file_store.FileStateStore.resolve_record`, or a
caller-supplied ``difference``/``change`` record body independently schema-validated and
fingerprint-recomputed through the existing Difference/Change owners' own identity functions --
Structural Review Round 1, P14-R1-F2), re-verifies the caller's explicit ``github_authority_ref``
against the existing Boot owner's own real, re-verified ``human_authority_ref`` (the identical
pattern Independent Verification's own Structural Review Round 1, P13-R1-F2, already
established), requires a genuine, exact-binding, Store-resolved ``github_projection_grant``
Authority Decision bound to this precise operation (Structural Review Round 1, P14-R1-F1, an
extension of the existing Authority owner mirroring Independent Verification's own
``evaluate_verifier_selection``), derives a deterministic Projection Envelope, and either
reuses an already-committed Envelope at the identical projection identity or persists a
genuinely new one through the existing Store's own single sanctioned committer
(:func:`~manosube_agent_civilization.store.commit.commit_state_transition` -- the identical
primitive Reflow and Binding already share). It creates no second State, Evidence, Difference,
Authority, Store, or Closure owner, and calls into no existing owner beyond ``boot`` (Human
Authority re-verification), ``authority`` (the projection Authority Decision), the read-only
``difference.identity``/``change.identity`` fingerprint functions, and, only for the caller's
own subsequent :func:`~manosube_agent_civilization.projection.receipt_handoff.
route_observation_receipt_to_evidence` call, ``evidence``.

Canonical route (``PROJECTION_CONTRACT.md`` §5):

```text
canonical Difference / Change / Evidence subject
→ real subject resolved (or admitted, for Difference/Change) and its own fingerprint
  recomputed (never trusted from a caller)
→ deterministic Projection Envelope mapping key
→ explicit GitHub Authority check (Boot-verified human_authority_ref)
→ genuine, exact-binding Authority Decision (Structural Review Round 1, P14-R1-F1)
→ existing canonical persistence boundary (store.resolve_record) -- reuse-or-conflict lookup
→ GitHub Adapter find-by-correlation-key (Structural Review Round 1, P14-R1-F4) -- recovers an
  already-materialized artifact before ever materializing a new one
→ GitHub Adapter materialize (only when neither an Envelope nor a correlation match exists)
→ external GitHub artifact
→ bounded GitHub re-observation (GitHub Adapter observe), content-fingerprint compared against
  the real, committed payload's own observable projection (Structural Review Round 1, P14-R1-F3)
→ GitHub Observation Receipt, carrying its own originating project identity
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

**Recoverable idempotency (Structural Review Round 1, P14-R1-F4).** Even when no Envelope is
committed yet, this route calls
:meth:`~manosube_agent_civilization.projection.types.GitHubAdapter.find_by_correlation_key`
before ever calling ``materialize`` -- on every attempt, including the very first. A prior
attempt whose own response was lost or invalid, or whose Store commit failed after a genuine
external success, therefore converges on retry to the identical external artifact instead of
creating a duplicate: the deterministic mapping key *is* the correlation key, durable and
recomputable with no I/O, so it survives any crash before, during, or after the external write
without this route needing a separate persisted intent record of its own.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from manosube_agent_civilization.authority import (
    PROJECTION_AUTHORIZED,
    evaluate_projection_authorization,
)
from manosube_agent_civilization.authority.errors import AuthorityError
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.change.identity import (
    change_id as _change_id,
    change_semantic_fingerprint as _change_semantic_fingerprint,
)
from manosube_agent_civilization.difference.identity import difference_id as _difference_id
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)
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
from .observable import expected_observable_fingerprint
from .types import (
    ARTIFACT_KINDS,
    OBSERVATION_OUTCOME_KINDS,
    PROJECTION_KINDS,
    SUBJECT_REF_KINDS,
    GitHubAdapter,
    GitHubObservationReceipt,
)

_STORE_RESOLVABLE_SUBJECT_KIND = "observation_evidence"
_ENVELOPE_RECORD_KIND = "projection_envelope"
_GRANT_RECORD_KIND = "github_projection_grant"
_PERMITTED_ACTION = "MATERIALIZE_PROJECTION"
_DIFFERENCE_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "difference/"
_CHANGE_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "change/"

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


def _require_external_artifact_ref(
    value: Any, *, context: str, target_repository: dict[str, Any], projection_kind: str
) -> dict[str, Any]:
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
    # Structural Review Round 1 (P14-R1-F3): the artifact must be bound to the exact
    # requested repository and to an artifact_kind consistent with projection_kind -- an
    # adapter that returns a ref naming a different repository, or an artifact_kind the
    # requested projection_kind could never produce, is refused before it is ever committed.
    if (
        value["host"] != "github"
        or value["owner"] != target_repository["owner"]
        or (value["repo"] != target_repository["repo"])
    ):
        raise ProjectionAdapterError(
            f"{context} names a different target than requested: "
            f"{value['host']}/{value['owner']}/{value['repo']!r} != "
            f"github/{target_repository['owner']}/{target_repository['repo']}"
        )
    expected_artifact_kinds = {
        "DIFFERENCE_ISSUE": {"issue"},
        "CHANGE_PULL_REQUEST": {"pull_request"},
        "EVIDENCE_ARTIFACT": {"check_run", "review", "artifact"},
    }[projection_kind]
    if value["artifact_kind"] not in expected_artifact_kinds:
        raise ProjectionAdapterError(
            f"{context}.artifact_kind {value['artifact_kind']!r} is not valid for "
            f"projection_kind {projection_kind!r} (expected one of {sorted(expected_artifact_kinds)})"
        )
    if not value["url"].startswith(
        f"https://github.com/{target_repository['owner']}/{target_repository['repo']}/"
    ):
        raise ProjectionAdapterError(
            f"{context}.url does not name the requested repository: {value['url']!r}"
        )
    return dict(value)


def _resolve_or_refuse(
    store: Any, project_id: str, kind: str, ref: Any, *, context: str
) -> dict[str, Any]:
    """Resolve one caller-supplied ``{"kind", "id"}`` reference through the Store, refusing
    (never trusting content supplied directly) exactly as Independent Verification's own
    Structural Review Round 4 (P13-R4) already established for ``verifier_selection_grant``
    refs -- an unresolvable ref refuses before the Authority owner or the adapter is ever
    reached."""

    checked = _require_reference(ref, context=context, allowed_kinds=frozenset({kind}))
    resolved = store.resolve_record(project_id, kind, checked["id"])
    if resolved is None:
        raise ProjectionRequirementError(
            f"{context} does not resolve for project {project_id!r}: {kind}/{checked['id']}"
        )
    return dict(resolved)


def _require_project_id_match(body: dict[str, Any], project_id: str, *, context: str) -> None:
    """Refuse a subject record naming a different project than requested -- a Difference or
    Change genuinely belonging to another project must never be projectable under this
    project's own identity, exactly as every other cross-project binding in this repository
    is refused by exact reference equality rather than by trusting a caller's own framing."""

    if body.get("project_id") != project_id:
        raise ProjectionRequirementError(
            f"{context}.project_id does not match the requested project_id: "
            f"{body.get('project_id')!r} != {project_id!r}"
        )


def _require_difference_subject(
    subject_ref: dict[str, Any],
    subject_record: Mapping[str, Any] | None,
    subject_fingerprint: str | None,
    project_id: str,
) -> str:
    """Return the real, recomputed fingerprint of a ``difference`` subject (Structural Review
    Round 1, P14-R1-F2) -- never a bare caller-declared string. *subject_record* must be the
    real, canonical Difference record body; it is schema-validated, required to name
    *project_id* as its own, and its own content address
    (:func:`~manosube_agent_civilization.difference.identity.difference_id`) is recomputed and
    required to equal *subject_ref*'s own declared id.

    A Difference has no separate broader semantic fingerprint in this Kernel encoded in the
    ``sha256:`` form the Projection Envelope schema's own ``subject_fingerprint`` requires
    (``difference_id``'s own ``D-`` encoding does not match that pattern) -- this route
    further hashes the real, recomputed ``difference_id`` into that required form. The result
    remains purely a function of the real content (a further hash of an already-real,
    already-verified identity, never a caller-declared value), it is never itself trusted as
    an independent identity, and *subject_ref*'s own admission above is still checked against
    the real ``difference_id`` directly, not this derived encoding of it."""

    if subject_record is None:
        raise ProjectionRequirementError(
            "subject_record is required for a 'difference' subject -- this route does not "
            "resolve or reconstruct a Difference record itself (see the module docstring's "
            "disclosed scope boundary)"
        )
    body = dict(subject_record)
    _validate_canonical_record(body, "difference.schema.json", base=_DIFFERENCE_SCHEMA_BASE)
    _require_project_id_match(body, project_id, context="subject_record")
    real_id = _difference_id(body)
    if subject_ref["id"] != real_id:
        raise ProjectionRequirementError(
            "subject_ref does not name the real, recomputed identity of subject_record: "
            f"{subject_ref['id']!r} != {real_id!r}"
        )
    real_fingerprint = "sha256:" + hashlib.sha256(real_id.encode("utf-8")).hexdigest()
    if subject_fingerprint is not None and subject_fingerprint != real_fingerprint:
        raise ProjectionRequirementError(
            "supplied subject_fingerprint does not match the real, recomputed fingerprint of "
            f"subject_record: {subject_fingerprint!r} != {real_fingerprint!r}"
        )
    return real_fingerprint


def _require_change_subject(
    subject_ref: dict[str, Any],
    subject_record: Mapping[str, Any] | None,
    subject_fingerprint: str | None,
    project_id: str,
) -> str:
    """Return the real, recomputed semantic fingerprint of a ``change`` subject (Structural
    Review Round 1, P14-R1-F2), by the identical discipline
    :func:`_require_difference_subject` applies to a Difference subject."""

    if subject_record is None:
        raise ProjectionRequirementError(
            "subject_record is required for a 'change' subject -- this route does not "
            "resolve or reconstruct a Change record itself (see the module docstring's "
            "disclosed scope boundary)"
        )
    body = dict(subject_record)
    _validate_canonical_record(body, "change.schema.json", base=_CHANGE_SCHEMA_BASE)
    _require_project_id_match(body, project_id, context="subject_record")
    real_id = _change_id(body)
    if subject_ref["id"] != real_id:
        raise ProjectionRequirementError(
            "subject_ref does not name the real, recomputed identity of subject_record: "
            f"{subject_ref['id']!r} != {real_id!r}"
        )
    real_fingerprint = _change_semantic_fingerprint(body)
    if subject_fingerprint is not None and subject_fingerprint != real_fingerprint:
        raise ProjectionRequirementError(
            "supplied subject_fingerprint does not match the real, recomputed semantic "
            f"fingerprint of subject_record: {subject_fingerprint!r} != {real_fingerprint!r}"
        )
    return real_fingerprint


def _authorize_projection(
    store: Any,
    *,
    project_id: str,
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str,
    target_repository: dict[str, Any],
    payload_fingerprint: str,
    human_authority_ref: dict[str, Any],
    grant_refs: Any,
) -> None:
    """Require a real, exact-binding, Store-resolved ``github_projection_grant`` Authority
    Decision before any adapter call (Structural Review Round 1, P14-R1-F1) -- never merely
    equality between ``github_authority_ref`` and the real Human Authority reference, which
    proves only who owns Human Authority for the Project, not that this exact projection was
    authorized. Every :class:`~manosube_agent_civilization.authority.errors.AuthorityError`
    the evaluator itself raises for an unreadable request propagates unchanged."""

    if not isinstance(grant_refs, list | tuple):
        raise ProjectionRequirementError(
            f"github_projection_grant_refs must be an explicit list: {grant_refs!r}"
        )
    resolved_grants = [
        _resolve_or_refuse(
            store,
            project_id,
            _GRANT_RECORD_KIND,
            ref,
            context=f"github_projection_grant_refs[{position}]",
        )
        for position, ref in enumerate(grant_refs)
    ]
    request = {
        "schema_version": "0.1",
        "project_id": project_id,
        "subject_ref": subject_ref,
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": target_repository,
        "payload_fingerprint": payload_fingerprint,
        "permitted_action": _PERMITTED_ACTION,
        "human_authority_ref": human_authority_ref,
        "grants": resolved_grants,
    }
    try:
        decision = evaluate_projection_authorization(request)
    except AuthorityError:
        raise
    if decision["decision"] != PROJECTION_AUTHORIZED:
        raise ProjectionRequirementError(
            "no genuine github_projection_grant authorizes this exact projection "
            f"(project={project_id!r}, subject={subject_ref!r}, projection_kind={projection_kind!r}, "
            f"target={target_repository!r}); decision reason codes: "
            f"{decision['decision_reason_codes']}"
        )


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
    github_projection_grant_refs: list[Mapping[str, Any]],
    subject_record: Mapping[str, Any] | None = None,
    subject_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Project one canonical subject to GitHub and return
    ``{"envelope": ..., "receipt": GitHubObservationReceipt, "reused": bool}``.

    *subject_record* is required for a ``difference``/``change`` subject -- the real,
    canonical record body, independently schema-validated and fingerprint-recomputed here
    (Structural Review Round 1, P14-R1-F2) -- and ignored for an ``observation_evidence``
    subject (Store-resolved instead). *subject_fingerprint*, if supplied, is always
    cross-checked against the real, recomputed fingerprint, never trusted alone.
    *github_projection_grant_refs* is the caller's own explicit collection of
    ``{"kind": "github_projection_grant", "id": ...}`` references, resolved through the Store
    before being offered to the existing Authority owner (Structural Review Round 1,
    P14-R1-F1) -- grant content itself is never an accepted argument shape.
    *materialized_at* is a required, caller-supplied instant (this route reads no clock, the
    identical discipline Evidence's own ``derive_evidence`` already requires of its own
    "recording instant").

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
    elif checked_subject_ref["kind"] == "difference":
        real_subject_fingerprint = _require_difference_subject(
            checked_subject_ref, subject_record, subject_fingerprint, project_id
        )
    else:
        real_subject_fingerprint = _require_change_subject(
            checked_subject_ref, subject_record, subject_fingerprint, project_id
        )

    real_target_repository = {
        "host": "github",
        "owner": target_repository["owner"],
        "repo": target_repository["repo"],
    }
    mapping_key = projection_mapping_key(
        checked_subject_ref, real_subject_fingerprint, projection_kind, real_target_repository
    )
    real_payload_fingerprint = projection_payload_fingerprint(dict(projection_payload))

    # Structural Review Round 1 (P14-R1-F1): a genuine, exact-binding Authority Decision is
    # required before any adapter call, on every request -- the reuse-observe path included,
    # since it too is a real external call this Decision is meant to gate.
    _authorize_projection(
        store,
        project_id=project_id,
        subject_ref=checked_subject_ref,
        subject_fingerprint=real_subject_fingerprint,
        projection_kind=projection_kind,
        target_repository=real_target_repository,
        payload_fingerprint=real_payload_fingerprint,
        human_authority_ref=real_human_authority_ref,
        grant_refs=github_projection_grant_refs,
    )

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
            project_id=project_id,
            subject_ref=checked_subject_ref,
            external_artifact_ref=existing["external_artifact_ref"],
            github_authority_ref=real_human_authority_ref,
            projection_kind=projection_kind,
            committed_payload=dict(existing["projection_payload"]),
        )
        return {"envelope": existing, "receipt": receipt, "reused": True}

    declared_identity = getattr(adapter, "adapter_identity", None)
    if not isinstance(declared_identity, Mapping):
        raise ProjectionAdapterError(
            "adapter does not declare a readable adapter_identity attribute -- an unstated "
            "or unverifiable identity may never materialize or observe on this route's behalf"
        )

    # Structural Review Round 1 (P14-R1-F4): search before create, on every attempt --
    # recovers an artifact a prior attempt genuinely materialized but never committed an
    # Envelope for (a lost/invalid response, or a failed Store commit after a real success).
    found_ref = adapter.find_by_correlation_key(
        correlation_key=mapping_key,
        target_repository=real_target_repository,
        projection_kind=projection_kind,
        payload=dict(projection_payload),
    )
    if found_ref is not None:
        checked_artifact_ref = _require_external_artifact_ref(
            found_ref,
            context="adapter.find_by_correlation_key() return value",
            target_repository=real_target_repository,
            projection_kind=projection_kind,
        )
    else:
        external_artifact_ref = adapter.materialize(
            projection_kind=projection_kind,
            target_repository=real_target_repository,
            payload=dict(projection_payload),
            correlation_key=mapping_key,
        )
        checked_artifact_ref = _require_external_artifact_ref(
            external_artifact_ref,
            context="adapter.materialize() return value",
            target_repository=real_target_repository,
            projection_kind=projection_kind,
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
        project_id=project_id,
        subject_ref=checked_subject_ref,
        external_artifact_ref=checked_artifact_ref,
        github_authority_ref=real_human_authority_ref,
        projection_kind=projection_kind,
        committed_payload=dict(projection_payload),
    )
    return {"envelope": envelope, "receipt": receipt, "reused": False}


def _observe(
    adapter: GitHubAdapter,
    *,
    envelope_id: str,
    project_id: str,
    subject_ref: dict[str, Any],
    external_artifact_ref: dict[str, Any],
    github_authority_ref: dict[str, Any],
    projection_kind: str,
    committed_payload: dict[str, Any],
) -> GitHubObservationReceipt:
    """Call the adapter's own ``observe`` exactly once and return one immutable
    :class:`~manosube_agent_civilization.projection.types.GitHubObservationReceipt`.

    Structural Review Round 1 (P14-R1-F3): the adapter's own reported status is never
    trusted for a ``FOUND`` outcome -- this function independently recomputes the expected
    observable fingerprint from *committed_payload* and compares it against what the adapter
    reports, forcing a non-``VERIFIED`` result on any mismatch. Structural Review Round 1
    (P14-R1-F6): the adapter's own ``observation_outcome`` is required to be one of
    :data:`~manosube_agent_civilization.projection.types.OBSERVATION_OUTCOME_KINDS`; only
    ``NOT_FOUND`` establishes absence, and ``PERMISSION_DENIED``/``UNAVAILABLE`` both leave
    existence undetermined rather than being folded into a false absence or a false
    confirmation.
    """

    result = adapter.observe(external_artifact_ref=external_artifact_ref)
    if not isinstance(result, Mapping):
        raise ProjectionAdapterError(f"adapter.observe() returned {result!r}, not a mapping")
    outcome = result.get("observation_outcome")
    if outcome not in OBSERVATION_OUTCOME_KINDS:
        raise ProjectionAdapterError(
            f"adapter.observe()'s own 'observation_outcome' is not recognized: {outcome!r}"
        )
    observed_content_fingerprint = result.get("observed_content_fingerprint")
    observed_at = result.get("observed_at")

    if outcome == "FOUND":
        if not isinstance(observed_content_fingerprint, str) or not observed_content_fingerprint:
            raise ProjectionAdapterError(
                "adapter.observe() reported FOUND with no observed_content_fingerprint: "
                f"{observed_content_fingerprint!r}"
            )
        expected_fingerprint = expected_observable_fingerprint(projection_kind, committed_payload)
        exists: bool | None = True
        status = "VERIFIED" if observed_content_fingerprint == expected_fingerprint else "FAILED"
    elif outcome == "NOT_FOUND":
        exists = False
        status = "FAILED"
    else:  # PERMISSION_DENIED / UNAVAILABLE -- existence itself is undetermined
        exists = None
        status = "UNAVAILABLE"

    observations = {
        "observation_outcome": outcome,
        "exists": exists,
        "observed_content_fingerprint": observed_content_fingerprint,
        "observed_at": observed_at,
    }
    return GitHubObservationReceipt(
        status=status,
        projection_envelope_id=envelope_id,
        project_id=project_id,
        subject_ref=subject_ref,
        external_artifact_ref=external_artifact_ref,
        adapter_identity=dict(adapter.adapter_identity),
        github_authority_ref=github_authority_ref,
        input_refs=(dict(subject_ref),),
        observations=observations,
    )


__all__ = ["PROJECTION_SCHEMA_BASE", "project_to_github"]
