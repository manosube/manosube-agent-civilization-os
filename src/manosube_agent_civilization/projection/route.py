"""The one public Projection route (Phase 14, Issue #62).

``PROJECTION_OWNER_COUNT=1``, ``PUBLIC_PROJECTION_ENTRY_POINT_COUNT=1``.

``project_to_github`` resolves an already-real canonical subject -- an ``observation_evidence``,
``difference``, or ``change`` record, each resolvable through the existing Store's own
read-only :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.resolve_record`
by reference alone, or (for ``difference``/``change`` only) a caller-supplied record body
instead -- independently schema-validated and fingerprint-recomputed through the existing
Difference/Change owners' own identity functions either way (Structural Review Round 1,
P14-R1-F2; Store-resolution extended to Difference/Change, Structural Review Round 11,
P14-R11-F1), re-verifies the caller's explicit ``github_authority_ref``
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
recomputable with no I/O.

**Atomic recoverable state machine (Structural Review Round 2, P14-R2-F2).** Search-then-
create alone is still a check-then-act race between two genuinely concurrent callers: both
can observe "nothing found" and both fall through to ``materialize``, producing two external
artifacts for the identical semantic projection. This route closes that race with two durable
Store records, both keyed by the mapping key itself and both committed through the identical
single sanctioned committer as the eventual Envelope (never a second persistence mechanism):
a ``projection_intent`` claim, committed before ``find_by_correlation_key``, and a
``projection_materialize_attempt`` marker, committed before ``materialize`` itself. The
Store's own per-project commit serialization and same-key/different-content rejection
(:class:`~manosube_agent_civilization.store.errors.RecordConflictError`) is the entire
concurrency barrier -- this route adds no lock, queue, or timeout of its own. A caller whose
own claim attempt collides with a different, already-durable claim refuses immediately, before
any adapter call, with :class:`~.errors.ProjectionConcurrentClaimError`. A caller that already
owns the claim but finds both no discoverable external artifact and an already-durable
materialize-attempt marker is in a genuinely ambiguous state (materialize may have failed
cleanly, or may have succeeded with its response lost) and refuses with
:class:`~.errors.ProjectionReconciliationRequiredError` rather than risk a real, untracked
external duplicate by calling ``materialize`` a second time.

**Explicit claim ownership (Structural Review Round 3, P14-R3-F1).** ``materialized_at``
alone is a caller-supplied instant, never a uniqueness primitive -- two genuinely distinct
concurrent callers can legitimately supply the identical value, which would otherwise make
both look like the same caller's own idempotent retry and let both reach ``materialize``.
This route therefore requires a second, explicit ``attempt_claim_token`` on every call,
included in both the ``projection_intent`` and ``projection_materialize_attempt`` record
content the Store's own same-key/different-content rejection already keys its concurrency
barrier on: two attempts sharing a timestamp but carrying distinct tokens now produce
genuinely different record content, so only whichever commit the Store admits first ever
proceeds, and the other refuses via ``ProjectionConcurrentClaimError`` before any adapter
call. A genuine retry of the identical attempt must present the identical token again.

**Terminal claim binding (Structural Review Round 4, P14-R4-F1).** Round 3's own claim token
guarded the ``projection_intent``/``projection_materialize_attempt`` records, but not the
terminal Envelope itself: a request whose mapping key already resolved to a committed
Envelope returned that Envelope unconditionally, regardless of which ``attempt_claim_token``
the caller presented, so a distinct caller could reach an already-terminal projection and be
treated identically to the attempt that actually won it. The terminal Envelope now itself
carries the winning attempt's own ``claim_token`` (:func:`~manosube_agent_civilization.
projection.engine.derive_projection_envelope`'s new required field, excluded from the
Envelope's own content-addressed identity and semantic fingerprint -- see that function's own
docstring). A request whose ``attempt_claim_token`` equals the committed Envelope's own
``claim_token`` is a genuine same-attempt retry and proceeds exactly as before. A request
whose ``attempt_claim_token`` differs refuses with :class:`~.errors.
ProjectionTerminalClaimMismatchError` unless the caller explicitly passes
``permit_semantic_reuse=True`` -- later, genuinely intended reuse of an already-completed
projection by an unrelated caller remains possible, but only as an explicitly separate,
disclosed operation, never silently conflated with "this call was the winning attempt."
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
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .engine import (
    PROJECTION_SCHEMA_BASE,
    derive_projection_envelope,
    derive_projection_intent,
    derive_projection_materialize_attempt,
)
from .errors import (
    ConflictingProjectionPayloadError,
    ProjectionAdapterError,
    ProjectionConcurrentClaimError,
    ProjectionEnvelopeIntegrityError,
    ProjectionReconciliationRequiredError,
    ProjectionRequirementError,
    ProjectionTerminalClaimMismatchError,
)
from .identity import (
    projection_envelope_semantic_fingerprint,
    projection_mapping_key,
    projection_payload_fingerprint,
)
from .observable import observe_and_classify
from .types import (
    ARTIFACT_KINDS,
    PROJECTION_KINDS,
    SUBJECT_REF_KINDS,
    GitHubAdapter,
    GitHubObservationReceipt,
)

_STORE_RESOLVABLE_SUBJECT_KIND = "observation_evidence"
_ENVELOPE_RECORD_KIND = "projection_envelope"
_GRANT_RECORD_KIND = "github_projection_grant"
_GRANT_DECLARATION_RECORD_KIND = "github_projection_grant_declaration"
_INTENT_RECORD_KIND = "projection_intent"
_MATERIALIZE_ATTEMPT_RECORD_KIND = "projection_materialize_attempt"
_PERMITTED_ACTION = "MATERIALIZE_PROJECTION"
#: Bounds the Compare-And-Swap retry loop :func:`_claim_slot` runs under genuine, ordinary
#: contention (another commit to the *same* project landing between this route's own
#: ``load_current`` and its own ``commit`` -- unrelated to this claim entirely, and resolved
#: by simply reloading and retrying). Not a timeout and not a backoff -- the Store's own
#: per-project ``fcntl`` lock (Structural Review Round 2, P14-R2-F2's own reused primitive)
#: already fully serializes the retries themselves.
_MAX_CLAIM_RETRIES = 8
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
    # Structural Review Round 2 (P14-R2-F3b): a bare prefix check only proved *some*
    # artifact under the requested repository -- never that the URL's own path identifies
    # the *same* artifact as ``artifact_kind``/``external_id`` already do. A URL whose path
    # names a different id, a different artifact kind, or that hides its real target behind
    # a query string, fragment, or embedded userinfo, previously passed unnoticed as long as
    # the literal string prefix matched.
    _require_consistent_locator(
        value["url"],
        owner=target_repository["owner"],
        repo=target_repository["repo"],
        artifact_kind=value["artifact_kind"],
        external_id=value["external_id"],
        context=f"{context}.url",
    )
    return dict(value)


#: The canonical GitHub URL path segment(s) each ``artifact_kind`` may legitimately appear
#: under (Structural Review Round 2, P14-R2-F3b). Real GitHub itself uses the plural/short
#: form (``issues``, ``pull``); this package's own controlled fake adapter (and any other
#: adapter following its documented convention) uses the literal ``artifact_kind`` value
#: instead -- both are accepted here, but nothing *outside* this closed, per-kind set is.
_ARTIFACT_KIND_LOCATOR_SEGMENTS: dict[str, frozenset[str]] = {
    "issue": frozenset({"issue", "issues"}),
    "pull_request": frozenset({"pull_request", "pull", "pulls"}),
    "check_run": frozenset({"check_run", "runs", "check-runs"}),
    "review": frozenset({"review", "reviews"}),
    "artifact": frozenset({"artifact", "artifacts"}),
}


def _require_consistent_locator(
    url: str, *, owner: str, repo: str, artifact_kind: str, external_id: str, context: str
) -> None:
    """Parse *url* against the canonical GitHub locator grammar and require every one of
    its own parts -- host, owner, repo, artifact-kind segment, and id segment -- to name the
    identical artifact ``artifact_kind``/``external_id`` already claim, with no query string,
    fragment, or embedded userinfo left unaccounted for (Structural Review Round 2, Issue
    #62, P14-R2-F3b). A URL that merely starts with the right prefix but resolves to a
    *different* artifact once actually parsed is refused here, before it is ever committed
    into a Projection Envelope."""

    # Deliberately hand-parsed with plain string operations, never ``urllib`` -- this
    # package's own static conformance test reserves every network/transport-surface import,
    # ``urllib`` included, to ``github_adapter.py`` alone
    # (``test_only_github_adapter_module_imports_a_network_or_transport_surface``), and this
    # is genuinely just locator-grammar validation, not a transport call.
    _SCHEME_PREFIX = "https://"
    if not url.startswith(_SCHEME_PREFIX):
        raise ProjectionAdapterError(f"{context} is not an https URL: {url!r}")
    remainder = url[len(_SCHEME_PREFIX) :]
    authority, _, path_and_rest = remainder.partition("/")
    if "@" in authority:
        raise ProjectionAdapterError(f"{context} carries embedded userinfo, refused: {url!r}")
    if authority != "github.com":
        raise ProjectionAdapterError(f"{context} does not name host github.com exactly: {url!r}")
    path_and_query, has_fragment, _fragment = path_and_rest.partition("#")
    if has_fragment:
        raise ProjectionAdapterError(f"{context} carries a fragment, refused: {url!r}")
    path, has_query, _query = path_and_query.partition("?")
    if has_query:
        raise ProjectionAdapterError(f"{context} carries a query string, refused: {url!r}")
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) != 4:
        raise ProjectionAdapterError(
            f"{context} does not have the canonical owner/repo/kind/id path shape: {url!r}"
        )
    path_owner, path_repo, path_kind, path_id = segments
    if path_owner != owner or path_repo != repo:
        raise ProjectionAdapterError(
            f"{context} path does not name the requested repository {owner}/{repo}: {url!r}"
        )
    allowed_segments = _ARTIFACT_KIND_LOCATOR_SEGMENTS.get(artifact_kind, frozenset())
    if path_kind not in allowed_segments:
        raise ProjectionAdapterError(
            f"{context} path names a kind segment {path_kind!r} inconsistent with "
            f"artifact_kind {artifact_kind!r} (expected one of {sorted(allowed_segments)}): {url!r}"
        )
    if path_id != external_id:
        raise ProjectionAdapterError(
            f"{context} path names a different id than external_id: {path_id!r} != "
            f"{external_id!r} ({url!r})"
        )


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
    store: Any,
    project_id: str,
    subject_ref: dict[str, Any],
    subject_record: Mapping[str, Any] | None,
    subject_fingerprint: str | None,
) -> str:
    """Return the real, recomputed fingerprint of a ``difference`` subject (Structural Review
    Round 1, P14-R1-F2; Store-resolvable by reference, Structural Review Round 11,
    P14-R11-F1). *subject_record*, when supplied directly, must be the real, canonical
    Difference record body. When left ``None``, the real body is instead resolved from
    *store* by *subject_ref* alone (:meth:`~manosube_agent_civilization.store.file_store.
    FileStateStore.resolve_record`) -- the identical Store-resolution discipline this route
    already applies to an ``observation_evidence`` subject, extended to Difference rather than
    adding a second, V3-only subject registry. Either way the resulting body is
    schema-validated, required to name *project_id* as its own, and its own content address
    (:func:`~manosube_agent_civilization.difference.identity.difference_id`) is recomputed and
    required to equal *subject_ref*'s own declared id -- a caller-supplied body is never
    trusted merely because it was supplied, and a Store-resolved body is never trusted merely
    because it resolved.

    A Difference has no separate broader semantic fingerprint in this Kernel encoded in the
    ``sha256:`` form the Projection Envelope schema's own ``subject_fingerprint`` requires
    (``difference_id``'s own ``D-`` encoding does not match that pattern) -- this route
    further hashes the real, recomputed ``difference_id`` into that required form. The result
    remains purely a function of the real content (a further hash of an already-real,
    already-verified identity, never a caller-declared value), it is never itself trusted as
    an independent identity, and *subject_ref*'s own admission above is still checked against
    the real ``difference_id`` directly, not this derived encoding of it."""

    if subject_record is None:
        resolved = store.resolve_record(project_id, "difference", subject_ref["id"])
        if resolved is None:
            raise ProjectionRequirementError(
                f"subject_ref does not resolve for project {project_id!r}: "
                f"difference/{subject_ref['id']}"
            )
        subject_record = resolved
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
    store: Any,
    project_id: str,
    subject_ref: dict[str, Any],
    subject_record: Mapping[str, Any] | None,
    subject_fingerprint: str | None,
) -> str:
    """Return the real, recomputed semantic fingerprint of a ``change`` subject (Structural
    Review Round 1, P14-R1-F2; Store-resolvable by reference, Structural Review Round 11,
    P14-R11-F1), by the identical discipline :func:`_require_difference_subject` applies to a
    Difference subject."""

    if subject_record is None:
        resolved = store.resolve_record(project_id, "change", subject_ref["id"])
        if resolved is None:
            raise ProjectionRequirementError(
                f"subject_ref does not resolve for project {project_id!r}: "
                f"change/{subject_ref['id']}"
            )
        subject_record = resolved
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
    human_authority_signing_key: dict[str, Any],
    grant_refs: Any,
    grant_declaration_refs: Any,
) -> None:
    """Require a real, exact-binding, Store-resolved ``github_projection_grant`` Authority
    Decision, anchored by a genuine, signed ``github_projection_grant_declaration``
    (Structural Review Round 1, P14-R1-F1; signed anchor, Structural Review Round 2,
    P14-R2-F1), before any adapter call -- never merely equality between
    ``github_authority_ref`` and the real Human Authority reference, which proves only who
    owns Human Authority for the Project, not that this exact projection was authorized, and
    never a grant's own Store persistence alone, which proves only that some Store-write-
    capable caller committed a self-consistent record, not that a Human declared it. Every
    :class:`~manosube_agent_civilization.authority.errors.AuthorityError` the evaluator itself
    raises for an unreadable request propagates unchanged."""

    if not isinstance(grant_refs, list | tuple):
        raise ProjectionRequirementError(
            f"github_projection_grant_refs must be an explicit list: {grant_refs!r}"
        )
    if not isinstance(grant_declaration_refs, list | tuple):
        raise ProjectionRequirementError(
            "github_projection_grant_declaration_refs must be an explicit list: "
            f"{grant_declaration_refs!r}"
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
    resolved_declarations = [
        _resolve_or_refuse(
            store,
            project_id,
            _GRANT_DECLARATION_RECORD_KIND,
            ref,
            context=f"github_projection_grant_declaration_refs[{position}]",
        )
        for position, ref in enumerate(grant_declaration_refs)
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
        "human_authority_signing_key": human_authority_signing_key,
        "grants": resolved_grants,
        "grant_declarations": resolved_declarations,
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


def _claim_slot(
    store: Any,
    project_id: str,
    record_kind: str,
    record_id: str,
    record: dict[str, Any],
    transaction_id_prefix: str,
    committed_at: str,
) -> None:
    """Durably claim (kind=*record_kind*, id=*record_id*) as one atomic Compare-And-Swap
    commit through the Store's own single sanctioned committer (Structural Review Round 2,
    Issue #62, P14-R2-F2) -- the concurrency barrier :func:`project_to_github` needs before
    ever calling ``adapter.find_by_correlation_key``/``materialize``.

    Returns normally, with zero further meaning to the caller beyond "this call now owns
    this claim", in exactly two cases: a fresh commit (nobody has claimed this slot before),
    or an idempotent replay of the *identical* claim content this exact caller already
    committed (a genuine retry presenting the identical ``claim_token`` -- Structural Review
    Round 3, P14-R3-F1 -- and the identical ``materialized_at``). Raises
    :class:`~.errors.ProjectionConcurrentClaimError` the moment the Store's own
    ``RecordConflictError`` proves a *different* attempt already durably holds this slot --
    the Store never lets two different record bodies coexist at one (kind, id), and that
    guarantee is the entire mechanism this function relies on. Two attempts sharing an
    identical ``materialized_at`` but carrying distinct ``claim_token`` values are exactly
    such a "different attempt": their record content differs, so only whichever one's own
    commit the Store admits first ever proceeds -- a caller-controlled timestamp alone can no
    longer let two genuinely distinct callers both look like the same idempotent retry.

    A :class:`~manosube_agent_civilization.store.errors.StaleStateError` means only that some
    *unrelated* commit landed on this project between this function's own ``load_current``
    and its own ``commit`` -- reloading and retrying resolves it without deciding anything
    about slot ownership one way or the other, bounded by :data:`_MAX_CLAIM_RETRIES` so
    genuine, sustained contention still surfaces as a real error rather than looping forever.

    *transaction_id_prefix* is never used verbatim as the transaction id: this function's own
    idempotency guarantee lives entirely at the (kind, id) record-content level
    (:func:`FileStateStore._stage_records`'s own same-key/different-content rejection), never
    at the transaction-id-replay level (identical *event* bytes at an identical
    ``transaction_id`` -- a much narrower guarantee than "identical record content", since the
    transition event also carries the base/target revision numbers, which genuinely differ
    between a first attempt and a later identical-content retry once *anything else* has
    since committed against this project). Reusing one fixed ``transaction_id`` across retries
    would make the Store's own transaction-replay check compare two transition events with
    different revision numbers and raise ``TransactionConflictError`` -- a real bug this
    function avoids by suffixing the *current* base revision onto the prefix on every retry,
    which is always fresh (a given project revision is used as a *base* at most once, ever).
    """

    for _ in range(_MAX_CLAIM_RETRIES):
        current_state = store.load_current(project_id)
        transaction_id = f"{transaction_id_prefix}-{current_state['state_revision']}"
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
            "committed_at": committed_at,
        }
        try:
            commit_state_transition(
                store,
                project_id,
                current_state["state_revision"],
                current_state["semantic_fingerprint"],
                next_state,
                transition,
                records=[(record_kind, record_id, record)],
            )
            return
        except RecordConflictError as error:
            raise ProjectionConcurrentClaimError(
                f"a different attempt already holds the claim on {record_kind}/{record_id} -- "
                "this attempt's own claim_token/materialized_at does not match the durably "
                "committed claim, so this request refuses rather than risk a duplicate "
                "external write"
            ) from error
        except StaleStateError:
            continue
    raise ProjectionConcurrentClaimError(
        f"could not durably claim {record_kind}/{record_id} after {_MAX_CLAIM_RETRIES} "
        "Compare-And-Swap retries -- sustained unrelated contention on this project's own "
        "State; this request refuses rather than materialize without a durable claim"
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
    github_projection_grant_declaration_refs: list[Mapping[str, Any]],
    attempt_claim_token: str,
    subject_record: Mapping[str, Any] | None = None,
    subject_fingerprint: str | None = None,
    permit_semantic_reuse: bool = False,
) -> dict[str, Any]:
    """Project one canonical subject to GitHub and return
    ``{"envelope": ..., "receipt": GitHubObservationReceipt, "reused": bool, "same_attempt":
    bool}``.

    *subject_record*, for a ``difference``/``change`` subject, is either the real, canonical
    record body directly (independently schema-validated and fingerprint-recomputed here --
    Structural Review Round 1, P14-R1-F2) or ``None``, in which case the real body is instead
    Store-resolved by *subject_ref* alone, through the identical
    :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.resolve_record` surface
    an ``observation_evidence`` subject already uses (Structural Review Round 11, P14-R11-F1) --
    and is always ignored (Store-resolved unconditionally) for an ``observation_evidence``
    subject. *subject_fingerprint*, if supplied, is always cross-checked against the real,
    recomputed fingerprint, never trusted alone.
    *github_projection_grant_refs* is the caller's own explicit collection of
    ``{"kind": "github_projection_grant", "id": ...}`` references, resolved through the Store
    before being offered to the existing Authority owner (Structural Review Round 1,
    P14-R1-F1) -- grant content itself is never an accepted argument shape.
    *github_projection_grant_declaration_refs* is the caller's own explicit collection of
    ``{"kind": "github_projection_grant_declaration", "id": ...}`` references, resolved
    through the Store the identical way (Structural Review Round 2, P14-R2-F1) -- a
    Store-resolved grant alone, with no matching signed Human declaration anchoring it,
    authorizes zero adapter calls.
    *materialized_at* is a required, caller-supplied instant (this route reads no clock, the
    identical discipline Evidence's own ``derive_evidence`` already requires of its own
    "recording instant"). *attempt_claim_token* (Structural Review Round 3, P14-R3-F1) is a
    required, caller-supplied, canonical-identity-shaped attempt token -- never a timestamp,
    which two genuinely distinct callers may legitimately share. A genuine retry of the exact
    same attempt must present the exact same ``attempt_claim_token`` again; a different
    caller, even one that happens to supply the identical ``materialized_at``, must supply a
    different one, and loses the durable claim race the moment its own commit lands second.
    *permit_semantic_reuse* (Structural Review Round 4, P14-R4-F1) governs only the case where
    the mapping key already resolves to a *terminally committed* Envelope whose own
    ``claim_token`` differs from this call's ``attempt_claim_token`` -- a distinct caller
    reaching an already-completed projection. Left ``False`` (the default), such a call
    refuses with :class:`~.errors.ProjectionTerminalClaimMismatchError` rather than silently
    masquerading as the winning attempt. Passing ``True`` explicitly requests the separate,
    disclosed "later semantic reuse" operation instead: the existing Envelope is still
    returned and freshly re-observed, but the returned ``"same_attempt"`` key is ``False``,
    recording that this call was not the attempt that won the mapping slot. A genuine
    same-attempt retry (identical ``attempt_claim_token``) always proceeds regardless of this
    flag, with ``"same_attempt": True``.

    See ``09_PROJECTION/PROJECTION_CONTRACT.md`` §5 for the full canonical route this function
    implements, step by step.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    _require_canonical_identity("attempt_claim_token", attempt_claim_token)

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
    real_human_authority_signing_key = dict(
        boot_context.project_binding["human_authority_signing_key"]
    )
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
            store, project_id, checked_subject_ref, subject_record, subject_fingerprint
        )
    else:
        real_subject_fingerprint = _require_change_subject(
            store, project_id, checked_subject_ref, subject_record, subject_fingerprint
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
        human_authority_signing_key=real_human_authority_signing_key,
        grant_declaration_refs=github_projection_grant_declaration_refs,
    )

    existing = store.resolve_record(project_id, _ENVELOPE_RECORD_KIND, mapping_key)
    if existing is not None:
        # Structural Review Round 5 (Issue #62, P14-R5-F1): never trust a resolved Envelope's
        # own fields -- including claim_token, now that it is part of SEMANTIC_FIELDS -- until
        # this route has independently recomputed and compared its own semantic fingerprint.
        # This is a domain-owned check, never merely inherited as a side effect of the Store's
        # own lower-level byte-comparison tamper detection; see ProjectionEnvelopeIntegrityError.
        if projection_envelope_semantic_fingerprint(existing) != existing.get(
            "projection_envelope_semantic_fingerprint"
        ):
            raise ProjectionEnvelopeIntegrityError(
                f"projection identity {mapping_key!r} resolved a committed Envelope whose own "
                "recomputed projection_envelope_semantic_fingerprint does not equal its own "
                "declared value -- refusing to trust any of its fields, claim_token included"
            )
        if existing["projection_payload_fingerprint"] != real_payload_fingerprint:
            raise ConflictingProjectionPayloadError(
                f"projection identity {mapping_key!r} already resolves to a committed "
                "Envelope with a different projection_payload_fingerprint: "
                f"{existing['projection_payload_fingerprint']!r} != {real_payload_fingerprint!r}"
            )
        # Structural Review Round 4 (P14-R4-F1): the committed Envelope's own claim_token
        # names the attempt that actually won this mapping slot. A request whose own
        # attempt_claim_token differs is not that attempt -- it must not be silently folded
        # into the same-attempt retry path merely because a matching Envelope exists.
        same_attempt = existing.get("claim_token") == attempt_claim_token
        if not same_attempt and not permit_semantic_reuse:
            raise ProjectionTerminalClaimMismatchError(
                f"projection identity {mapping_key!r} is already terminally committed under "
                f"a different attempt's own claim_token ({existing.get('claim_token')!r} != "
                f"{attempt_claim_token!r}) -- pass permit_semantic_reuse=True to explicitly "
                "request later semantic reuse of this already-completed projection as a "
                "distinct, disclosed operation"
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
        return {
            "envelope": existing,
            "receipt": receipt,
            "reused": True,
            "same_attempt": same_attempt,
        }

    declared_identity = getattr(adapter, "adapter_identity", None)
    if not isinstance(declared_identity, Mapping):
        raise ProjectionAdapterError(
            "adapter does not declare a readable adapter_identity attribute -- an unstated "
            "or unverifiable identity may never materialize or observe on this route's behalf"
        )

    # Structural Review Round 2 (Issue #62, P14-R2-F2): a durable claim on this exact mapping
    # slot, committed *before* either adapter call, closes the race a bare "search, then
    # create if not found" leaves open -- two concurrent callers reaching this point with the
    # identical mapping_key but different materialized_at can no longer both fall through to
    # materialize; only the one whose own claim the Store's single per-project commit lock
    # admits first proceeds, and the other refuses via ProjectionConcurrentClaimError before
    # calling the adapter at all. Same caller, same materialized_at (a genuine process retry)
    # commits idempotently and proceeds identically to the first attempt.
    intent = derive_projection_intent(
        subject_ref=checked_subject_ref,
        subject_fingerprint=real_subject_fingerprint,
        projection_kind=projection_kind,
        target_repository=real_target_repository,
        project_id=project_id,
        materialized_at=materialized_at,
        claim_token=attempt_claim_token,
    )
    _claim_slot(
        store,
        project_id,
        _INTENT_RECORD_KIND,
        mapping_key,
        intent,
        f"TX-PROJECTION-INTENT-{mapping_key}",
        materialized_at,
    )

    # Structural Review Round 1 (P14-R1-F4): search before create, on every attempt --
    # recovers an artifact a prior attempt genuinely materialized but never committed an
    # Envelope for (a lost/invalid response, or a failed Store commit after a real success).
    # Every caller reaches this lookup regardless of who owns the intent claim above: a
    # caller that lost the claim race may still legitimately *observe* an artifact the claim
    # owner already created, it simply may never *materialize* one of its own.
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
        # Structural Review Round 2 (P14-R2-F2): a second durable claim, committed before
        # ``materialize`` itself -- its presence with no discoverable artifact and no
        # committed Envelope is the genuinely ambiguous "did a prior materialize call under
        # this identical claim actually reach GitHub or not" state that must never resolve
        # itself by blindly calling materialize a second time (see
        # ProjectionReconciliationRequiredError).
        attempt_already_claimed = (
            store.resolve_record(project_id, _MATERIALIZE_ATTEMPT_RECORD_KIND, mapping_key)
            is not None
        )
        if attempt_already_claimed:
            raise ProjectionReconciliationRequiredError(
                f"projection identity {mapping_key!r} already recorded a materialize attempt "
                "under this identical claim, and no external artifact is discoverable and no "
                "Envelope is committed -- refusing to call materialize again rather than risk "
                "an untracked duplicate; this requires operator reconciliation"
            )
        attempt = derive_projection_materialize_attempt(
            subject_ref=checked_subject_ref,
            subject_fingerprint=real_subject_fingerprint,
            projection_kind=projection_kind,
            target_repository=real_target_repository,
            project_id=project_id,
            materialized_at=materialized_at,
            claim_token=attempt_claim_token,
        )
        _claim_slot(
            store,
            project_id,
            _MATERIALIZE_ATTEMPT_RECORD_KIND,
            mapping_key,
            attempt,
            f"TX-PROJECTION-ATTEMPT-{mapping_key}",
            materialized_at,
        )
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
        claim_token=attempt_claim_token,
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
    return {"envelope": envelope, "receipt": receipt, "reused": False, "same_attempt": True}


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
    """Call the adapter's own ``observe`` exactly once, via the shared
    :func:`~manosube_agent_civilization.projection.observable.observe_and_classify` body, and
    return one immutable :class:`~manosube_agent_civilization.projection.types.
    GitHubObservationReceipt`.

    Structural Review Round 1 (P14-R1-F3/F6) and Structural Review Round 3 (P14-R3-F2):
    :func:`~manosube_agent_civilization.projection.observable.observe_and_classify` is the
    single owner of the adapter-report-to-status classification, shared with
    :mod:`~manosube_agent_civilization.projection.receipt_handoff`'s own independent
    re-observation at handoff, so both call sites can only ever disagree over a genuine
    content mismatch, never over classification logic drift between the two.
    """

    classified = observe_and_classify(
        adapter,
        external_artifact_ref=external_artifact_ref,
        projection_kind=projection_kind,
        committed_payload=committed_payload,
    )
    observations = {
        "observation_outcome": classified["observation_outcome"],
        "exists": classified["exists"],
        "observed_content_fingerprint": classified["observed_content_fingerprint"],
        "observed_at": classified["observed_at"],
    }
    return GitHubObservationReceipt(
        status=classified["status"],
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
