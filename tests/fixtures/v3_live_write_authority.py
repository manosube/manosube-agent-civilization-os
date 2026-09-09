"""Genuine, canonically-issuable SHUKOU/Human Authority for V3 live-write execution
(Structural Review Round 6, Issue #62, P14-R6-F2; external trust anchor, Round 7, P14-R7-F1;
canonical issuable authority, Round 8, P14-R8-F1; Store/Boot-resolved authority routed to
execution, Round 9, P14-R9-F1; trusted Boot root and pre-issued execution authority, Round 10,
P14-R10-F1; frozen trusted runtime context to adapter chain, Round 11, P14-R11-F1; runtime
injection interface and the Phase 15 provisioning boundary, Round 12, P14-R12-F1).

Round 12 (P14-R12-F1, ``ADOPT_P14_R12_RUNTIME_INJECTION_INTERFACE_AND_PHASE15_PROVISIONING_
BOUNDARY``) redrew the Phase 14/Phase 15 boundary: Phase 14 owns and must prove complete the
*interface* that consumes an already-resolved, opaque execution context and carries it through
to the controlled adapter; Phase 14 does not own selecting/opening the real Store, producing the
real runtime Boot Context, or injecting it -- that provisioning is Phase 15's own explicitly
deferred responsibility. A prior round's collection-time, no-argument live-authorized-context
gate (``_v3_live_authorized_context()``) claimed a future runtime caller could activate it
without source edits while it had no actual injection point and always returned ``None`` -- a
permanently-false claim Round 12 removed outright, along with the one pytest assertion that
depended on it, rather than leaving a dead entry point a later reader could mistake for real.

Round 13 (P14-R13-F1/F2, ``ADOPT_P14_R13_SHIPPED_BOUND_PROJECTION_EXECUTION_CAPABILITY``) moves
the opaque context types and the adapter-reaching execution interface itself out of this
test-fixture module entirely: :class:`~manosube_agent_civilization.projection.
ProjectionExecutionContext`, :class:`~manosube_agent_civilization.projection.
PreIssuedProjectionAuthority`, :func:`~manosube_agent_civilization.projection.
execution_context_still_current`, and :class:`~manosube_agent_civilization.projection.
ProjectionExecutionCapability` now live in the shipped ``manosube_agent_civilization.projection``
package, importable from the installed Kernel wheel without importing ``tests`` at all -- a
"formal, source-edit-free interface" cannot itself live in ``tests``, since production code that
will one day call it would otherwise have to import a test module to do so. This module's own
``V3AuthorizedExecutionContext``/``V3PreIssuedProjectionAuthority``/
``v3_execution_context_still_current`` names below are now plain aliases for those shipped
types/function -- retained under their historical names so this module's own callers need not
change, but no longer separate definitions. :func:`resolve_v3_live_write_authority` still does
exactly what it always did: resolve untrusted, project-scoped grant/declaration **references**
and each projection kind's own subject, exclusively within the caller-injected trusted Store,
into one genuine :class:`~manosube_agent_civilization.projection.ProjectionExecutionContext`.
Round 12's own module-level ``execute_v3_authorized_projection`` -- a plain, stateless function
re-accepting *context* fresh on every call -- is removed outright: Round 13 (P14-R13-F2) found it
structurally insufficient as a *bound* capability, since nothing in its own shape prevented a
caller from threading a *different* context object into each call. The shipped
:class:`~manosube_agent_civilization.projection.ProjectionExecutionCapability` replaces it,
constructed exactly once from a genuine context and exposing no ``context``-accepting parameter
of any kind on its own adapter-reaching method.

Round 10 (P14-R10-F1) split trust into a Store/Project/Binding root, supplied through its own
environment variable, and a narrower set of grant/declaration references resolved only within
that root's own Store. Round 11 (P14-R11-F1) removes the environment variable entirely: *any*
environment variable a caller-controlling entity can set is, structurally, still caller input,
regardless of how narrowly scoped its own JSON shape is. The live V3 route now receives its
Store as a plain, already-open Python object -- a capability injected by whichever code
legitimately calls :func:`resolve_v3_live_write_authority` (the real deployment's own runtime
bootstrap; this repository's own test harness, simulating that role directly in Python for its
required controls) -- never opened, selected, or constructed by this module from any string,
path, or environment variable. This module imports no ``FileStateStore`` at all any more
(proven by static conformance): it has no capability to open one under any circumstance,
caller-supplied or otherwise. ``project_id``/``project_binding_id`` remain ordinary parameters
here, exactly as every other canonical route in this repository already accepts them
(:func:`~manosube_agent_civilization.boot.boot_project`,
:func:`~manosube_agent_civilization.projection.route.project_to_github`) -- Boot's own
identity/content-address verification is what makes an arbitrary string incapable of naming
anything but a real, already-legitimately-committed Project Binding within whichever Store was
actually injected; the Store object itself, never a string, is the one thing that could
redirect *which* universe of records ever gets consulted at all, and it is never
caller-selectable here.

Round 9 also let the live *execution* path mint a fresh, subject-scoped grant/declaration per
run using this repository's own test-only signing key (:mod:`tests.fixtures.product_binding`).
Round 10 closed that by requiring every subject-specific grant/declaration/decision to already
be externally issued, committed, Store-resolved, and identity-recomputed before execution --
but still let the *subject* itself (the actual Difference/Change/Evidence record body
``project_to_github`` needs for a Difference/Change subject) arrive as a caller-supplied body
or a side-channel ``subjects`` mapping the harness threaded in separately from this module's
own resolution. Round 11 closes that too: :func:`resolve_v3_live_write_authority` now resolves
each projection kind's own subject **by exact reference alone**, from the identical trusted
Store the grant/declaration references are resolved within, using the identical canonical
Difference/Change/Evidence identity and schema-validation owners
(:mod:`~manosube_agent_civilization.difference.identity`,
:mod:`~manosube_agent_civilization.change.identity`,
:mod:`~manosube_agent_civilization.evidence.identity`,
:mod:`~manosube_agent_civilization.difference.validation`) that
:func:`~manosube_agent_civilization.projection.route.project_to_github` itself now also uses
for this same Store-resolution (extended there this round, P14-R11-F1 §3, rather than a second,
V3-only subject registry). The resolved, identity-verified subject record is preserved inside
the immutable :class:`V3AuthorizedExecutionContext` this function returns
(:class:`V3PreIssuedProjectionAuthority.subject_record`) -- the live execution path therefore
never accepts a caller-supplied subject body and never receives a separate ``subjects`` mapping
of any kind; everything ``project_to_github`` needs already lives inside the one frozen context
this function alone produces.

This module holds no private key, imports no signing helper (repository-held or otherwise), and
cannot construct a Store under any circumstance -- proven by
``tests/contract/projection/test_v3_live_write_authority_static_conformance.py``.

:func:`v3_execution_context_still_current` re-Boots the injected Store immediately before every
adapter-reaching call and requires its ``state_revision``/``semantic_fingerprint`` to be
byte-identical to what authorization itself observed. Since every subject, grant, and
declaration this module ever resolves is itself a record inside that same Store, and every
commit to that Store necessarily advances its ``state_revision``, an unchanged
``state_revision``/``semantic_fingerprint`` is a sufficient proxy for "every individually
resolved field -- subject identity, grant/declaration identity and status, Authority Decision
-- is still exactly what authorization observed": nothing reachable from an unchanged Store
could itself have changed. A Store mutation of any kind between authorization and execution is
therefore detected and refused, never silently accepted.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from typing import Any

from manosube_agent_civilization.authority.errors import AuthorityError
from manosube_agent_civilization.authority.identity import github_projection_grant_id
from manosube_agent_civilization.authority.projection_authorization import (
    evaluate_projection_authorization,
)
from manosube_agent_civilization.binding.errors import BindingError
from manosube_agent_civilization.binding.identity import (
    verify_github_projection_grant_declaration_identity,
)
from manosube_agent_civilization.boot import BootError, boot_project
from manosube_agent_civilization.change.identity import (
    change_id as _change_id,
    change_semantic_fingerprint as _change_semantic_fingerprint,
)
from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.identity import difference_id as _difference_id
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as _CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)
from manosube_agent_civilization.evidence.identity import (
    evidence_semantic_fingerprint as _evidence_semantic_fingerprint,
)
from manosube_agent_civilization.projection import (
    PreIssuedProjectionAuthority as V3PreIssuedProjectionAuthority,
    ProjectionExecutionContext as V3AuthorizedExecutionContext,
)
from manosube_agent_civilization.projection.execution import (
    execution_context_still_current as v3_execution_context_still_current,
)
from manosube_agent_civilization.store.errors import StoreError

from .v3_target_configuration import V3TargetConfiguration

#: Structural Review Round 13 (P14-R13-F1): ``V3AuthorizedExecutionContext``,
#: ``V3PreIssuedProjectionAuthority``, and ``v3_execution_context_still_current`` (imported
#: above) are now plain aliases for the shipped, production opaque context types and freshness
#: function -- retained under their historical names so this module's own callers need not
#: change, but no longer separate definitions of their own. See
#: ``manosube_agent_civilization.projection.execution`` for the real definitions. Listed
#: explicitly in ``__all__`` below (required for ``mypy --namespace-packages``'s own
#: ``no_implicit_reexport`` check to recognize a *renamed* import as a genuine re-export, not an
#: accidental one) alongside every other name this module intends as public.
__all__ = [
    "V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV",
    "V3_PERMITTED_ACTION",
    "V3_PROJECTION_KINDS",
    "V3AuthorizedExecutionContext",
    "V3LiveWriteAuthorityReferences",
    "V3PreIssuedProjectionAuthority",
    "load_v3_live_write_authority_references",
    "resolve_v3_live_write_authority",
    "v3_execution_context_still_current",
]

#: The one closed permitted-action literal every real GitHub projection operation already uses
#: (``authority/projection_authorization.py``'s own ``_PERMITTED_ACTIONS``) -- V3's own live
#: execution authorizes ``MATERIALIZE_PROJECTION`` exactly as a production projection call
#: does. No V3-specific action literal exists, and none is introduced here.
V3_PERMITTED_ACTION = "MATERIALIZE_PROJECTION"

#: Every projection kind the V3 harness exercises. An authorized V3 execution requires an
#: independent, pre-issued grant/declaration pair and ``PROJECTION_AUTHORIZED`` decision for
#: *each* of these -- one grant standing in for all three is never sufficient.
V3_PROJECTION_KINDS: tuple[str, ...] = (
    "DIFFERENCE_ISSUE",
    "CHANGE_PULL_REQUEST",
    "EVIDENCE_ARTIFACT",
)

#: Which real canonical subject kind each projection kind's own pre-issued grant must name --
#: the identical pairing :mod:`~manosube_agent_civilization.projection.route` itself enforces
#: via ``_REQUIRED_SUBJECT_KIND``, duplicated here only as a small, denotational constant (not
#: owner logic) so this module can validate it before ever reaching that route.
_SUBJECT_KIND_FOR_PROJECTION_KIND: dict[str, str] = {
    "DIFFERENCE_ISSUE": "difference",
    "CHANGE_PULL_REQUEST": "change",
    "EVIDENCE_ARTIFACT": "observation_evidence",
}

#: The environment variable carrying the complete, JSON-encoded V3 live-write authority
#: **references** -- grant/declaration reference lists only. Never a Store root, a
#: ``project_id``, or a ``project_binding_id`` (Structural Review Round 10, P14-R10-F1;
#: unchanged by Round 11, P14-R11-F1, which removes the *separate* trusted-root environment
#: variable Round 10 still read -- see the module docstring).
V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV = "MANOSUBE_P14_V3_LIVE_WRITE_AUTHORITY_REFERENCES"

_GRANT_REF_KIND = "github_projection_grant"
_DECLARATION_REF_KIND = "github_projection_grant_declaration"
_DIFFERENCE_SCHEMA_BASE = _CANONICAL_SCHEMA_BASE + "difference/"
_CHANGE_SCHEMA_BASE = _CANONICAL_SCHEMA_BASE + "change/"

#: Every exception :func:`~manosube_agent_civilization.boot.boot_project` may propagate for a
#: Store/Binding it cannot restore, plus :class:`DifferenceValidationError` for a subject that
#: fails canonical schema validation -- Boot's, Store's, Binding's, and Difference's own
#: errors, forwarded unchanged, never swallowed and never re-interpreted here as anything but
#: refusal.
_BOOT_FAILURE_ERRORS: tuple[type[Exception], ...] = (
    BootError,
    StoreError,
    BindingError,
    DifferenceValidationError,
)


@dataclass(frozen=True, slots=True)
class V3LiveWriteAuthorityReferences:
    """Project-scoped grant/declaration **references** only -- never a Store root, a
    ``project_id``, a ``project_binding_id``, a subject body, or any other authoritative record
    body (Structural Review Round 9, P14-R9-F1; narrowed by Round 10, P14-R10-F1; unchanged in
    shape by Round 11, P14-R11-F1, which removes the *separate* trusted-root type Round 10
    introduced rather than adding anything to this one). Every reference here names *where*,
    within the caller-injected trusted Store, to resolve a canonical record; none of them *is*
    a record, and none of them can select which Store to resolve from."""

    github_projection_grant_refs: tuple[Mapping[str, str], ...]
    github_projection_grant_declaration_refs: tuple[Mapping[str, str], ...]


def _parse_ref_list(raw: Any, *, kind: str) -> tuple[dict[str, str], ...] | None:
    """Parse *raw* as a non-empty list of ``{"kind": kind, "id": <non-empty str>}`` mappings,
    or return ``None`` on any other shape -- malformed input is simply no reference, never an
    exception."""

    if not isinstance(raw, list) or not raw:
        return None
    refs: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            return None
        if item.get("kind") != kind:
            return None
        record_id = item.get("id")
        if not isinstance(record_id, str) or not record_id:
            return None
        refs.append({"kind": kind, "id": record_id})
    return tuple(refs)


#: Keys that would signal a caller attempting to smuggle a Store-selecting field into the
#: authority-references channel -- refused outright, never silently ignored (Structural Review
#: Round 10, P14-R10-F1; retained unchanged by Round 11, P14-R11-F1, since this channel could
#: never select a Store regardless -- Store selection is not an environment-variable-reachable
#: concept in this module at all any more).
_FORBIDDEN_REFERENCE_KEYS = ("store_root", "project_id", "project_binding_id")


def load_v3_live_write_authority_references(
    env: Mapping[str, str] | None = None,
) -> V3LiveWriteAuthorityReferences | None:
    """Read and JSON-decode :data:`V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV`, or return ``None``
    if unset, unparseable, not a JSON object, missing/malformed any required field, or
    attempting to carry a Store-selecting field (``store_root``/``project_id``/
    ``project_binding_id``) at all -- fail closed on the exact smuggling attempt Round 10's own
    finding names, never silently drop the extra keys and proceed. *env* defaults to
    :data:`os.environ`; performs no filesystem or network access of its own -- this module
    touches no Store at all; only :func:`resolve_v3_live_write_authority` does, and only
    through its own caller-injected *store* parameter, never anything this function returns."""

    source = env if env is not None else os.environ
    raw = source.get(V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV)
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if any(key in payload for key in _FORBIDDEN_REFERENCE_KEYS):
        return None

    grant_refs = _parse_ref_list(payload.get("github_projection_grant_refs"), kind=_GRANT_REF_KIND)
    declaration_refs = _parse_ref_list(
        payload.get("github_projection_grant_declaration_refs"), kind=_DECLARATION_REF_KIND
    )
    if grant_refs is None or declaration_refs is None:
        return None

    return V3LiveWriteAuthorityReferences(
        github_projection_grant_refs=grant_refs,
        github_projection_grant_declaration_refs=declaration_refs,
    )


def _resolve_grant(store: Any, project_id: str, ref: Mapping[str, str]) -> Mapping[str, Any] | None:
    """Resolve exactly the ``github_projection_grant`` *ref* names, then independently
    recompute its own content-addressed id and require it to reproduce -- "identity-recomputed"
    (Structural Review Round 10, P14-R10-F1), never a resolved body trusted on Store lookup
    alone."""

    if ref.get("kind") != _GRANT_REF_KIND:
        return None
    record_id = ref.get("id")
    if not isinstance(record_id, str) or not record_id:
        return None
    try:
        resolved: Mapping[str, Any] | None = store.resolve_record(
            project_id, _GRANT_REF_KIND, record_id
        )
    except _BOOT_FAILURE_ERRORS:
        return None
    if resolved is None:
        return None
    try:
        if github_projection_grant_id(dict(resolved)) != resolved.get("github_projection_grant_id"):
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return resolved


def _resolve_declaration(
    store: Any, project_id: str, ref: Mapping[str, str]
) -> Mapping[str, Any] | None:
    """Resolve exactly the ``github_projection_grant_declaration`` *ref* names, then
    independently reverify its own content-addressed identity via the existing canonical
    verifier -- "identity-recomputed" (Structural Review Round 10, P14-R10-F1)."""

    if ref.get("kind") != _DECLARATION_REF_KIND:
        return None
    record_id = ref.get("id")
    if not isinstance(record_id, str) or not record_id:
        return None
    try:
        resolved: Mapping[str, Any] | None = store.resolve_record(
            project_id, _DECLARATION_REF_KIND, record_id
        )
    except _BOOT_FAILURE_ERRORS:
        return None
    if resolved is None:
        return None
    try:
        verify_github_projection_grant_declaration_identity(dict(resolved))
    except _BOOT_FAILURE_ERRORS:
        return None
    return resolved


def _resolve_subject(
    store: Any, project_id: str, subject_ref: Mapping[str, Any]
) -> tuple[dict[str, Any], str] | None:
    """Resolve *subject_ref*'s own real canonical record from the caller-injected trusted Store
    alone, then independently recompute its identity/semantic fingerprint through the existing
    Difference/Change/Evidence owner -- the identical discipline
    :func:`~manosube_agent_civilization.projection.route.project_to_github` itself now also
    applies at execution time (extended there this round for Store-resolved Difference/Change,
    Structural Review Round 11, P14-R11-F1 §3), performed here too so a resolved-but-tampered
    or mismatched subject is refused before authorization is ever granted, not merely at the
    moment ``project_to_github`` later happens to catch it. Returns ``(subject_record,
    real_subject_fingerprint)`` on success, ``None`` on any failure; never raises."""

    kind = subject_ref.get("kind")
    record_id = subject_ref.get("id")
    if kind not in _SUBJECT_KIND_FOR_PROJECTION_KIND.values():
        return None
    if not isinstance(record_id, str) or not record_id:
        return None
    try:
        resolved = store.resolve_record(project_id, kind, record_id)
    except _BOOT_FAILURE_ERRORS:
        return None
    if resolved is None:
        return None
    body = dict(resolved)

    try:
        if kind == "difference":
            if body.get("project_id") != project_id:
                return None
            _validate_canonical_record(body, "difference.schema.json", base=_DIFFERENCE_SCHEMA_BASE)
            real_id = _difference_id(body)
            if record_id != real_id:
                return None
            real_fingerprint = "sha256:" + hashlib.sha256(real_id.encode("utf-8")).hexdigest()
        elif kind == "change":
            if body.get("project_id") != project_id:
                return None
            _validate_canonical_record(body, "change.schema.json", base=_CHANGE_SCHEMA_BASE)
            real_id = _change_id(body)
            if record_id != real_id:
                return None
            real_fingerprint = _change_semantic_fingerprint(body)
        else:
            real_fingerprint = _evidence_semantic_fingerprint(body)
    except _BOOT_FAILURE_ERRORS:
        return None
    except (KeyError, TypeError, ValueError):
        return None

    return body, real_fingerprint


def resolve_v3_live_write_authority(
    store: Any,
    project_id: str | None,
    project_binding_id: str | None,
    config: V3TargetConfiguration | None,
    references: V3LiveWriteAuthorityReferences | None,
) -> V3AuthorizedExecutionContext | None:
    """Resolve *references* -- grant/declaration reference lists only -- and every projection
    kind's own subject, exclusively within *store*, the already-open, caller-injected trusted
    Store this function never opens, selects, or constructs itself (Structural Review
    Round 11, P14-R11-F1). Boot-restores the exact Project/Binding *project_id*/
    *project_binding_id* name within *store*
    (:func:`~manosube_agent_civilization.boot.boot_project` -- the existing canonical runtime/
    bootstrap owner, never a second one), and returns one :class:`V3AuthorizedExecutionContext`
    if, and only if, exactly one resolved grant and exactly one anchoring declaration exist for
    *every* projection kind in :data:`V3_PROJECTION_KINDS`, each bound to *config*'s own
    ``target_repository``, each grant's own ``subject_ref`` resolves to a real subject record
    within *store* whose independently recomputed identity/fingerprint exactly matches both
    *subject_ref* and the grant's own claimed ``subject_fingerprint``, and each genuinely
    authorizes ``MATERIALIZE_PROJECTION`` through
    :func:`~manosube_agent_civilization.authority.projection_authorization.
    evaluate_projection_authorization` -- the same function a production projection call
    already trusts. Returns ``None`` on any failure: *store*/*project_id*/
    *project_binding_id*/*config*/*references* missing, the Project Binding failing to
    Boot-restore, any referenced grant, declaration, or subject failing to resolve or reproduce
    its own claimed identity, zero or more than one grant/declaration per kind, a grant bound
    to a different ``target_repository``, or any resolved kind's own authorization request
    refusing. Performs Store reads only -- no network access of any kind, and never raises; a
    malformed grant, declaration, or request that raises inside
    ``evaluate_projection_authorization`` is caught here as
    :class:`~manosube_agent_civilization.authority.errors.AuthorityError` and treated as
    refusal, since a live-write gate must never raise. Never mints, signs, or commits anything,
    and never accepts a caller-supplied subject body or a separate subject mapping of any kind
    -- every record consumed here, subjects included, was already externally issued, committed,
    and Store-resolved before this call."""

    if (
        store is None
        or project_id is None
        or project_binding_id is None
        or config is None
        or references is None
    ):
        return None

    try:
        boot_context = boot_project(
            store, project_id=project_id, project_binding_id=project_binding_id
        )
    except _BOOT_FAILURE_ERRORS:
        return None

    if (
        boot_context.project_id != project_id
        or boot_context.project_binding_id != project_binding_id
    ):
        return None

    human_authority_ref = boot_context.human_authority_ref
    human_authority_signing_key = boot_context.project_binding.get("human_authority_signing_key")
    if not isinstance(human_authority_signing_key, Mapping):
        return None

    grants: list[Mapping[str, Any]] = []
    for ref in references.github_projection_grant_refs:
        body = _resolve_grant(store, project_id, ref)
        if body is None:
            return None
        grants.append(body)

    declarations: list[Mapping[str, Any]] = []
    for ref in references.github_projection_grant_declaration_refs:
        body = _resolve_declaration(store, project_id, ref)
        if body is None:
            return None
        declarations.append(body)

    decisions: dict[str, Mapping[str, Any]] = {}
    authorities: dict[str, V3PreIssuedProjectionAuthority] = {}
    for projection_kind in V3_PROJECTION_KINDS:
        matching_grants = [g for g in grants if g.get("projection_kind") == projection_kind]
        if len(matching_grants) != 1:
            return None
        grant = matching_grants[0]

        subject_ref = grant.get("subject_ref")
        target_repository = grant.get("target_repository")
        grant_id = grant.get("github_projection_grant_id")
        if not isinstance(subject_ref, Mapping) or not isinstance(target_repository, Mapping):
            return None
        if subject_ref.get("kind") != _SUBJECT_KIND_FOR_PROJECTION_KIND[projection_kind]:
            return None
        if not isinstance(grant_id, str) or not grant_id:
            return None
        if dict(target_repository) != dict(config.target_repository):
            return None

        resolved_subject = _resolve_subject(store, project_id, subject_ref)
        if resolved_subject is None:
            return None
        subject_record, real_subject_fingerprint = resolved_subject
        if grant.get("subject_fingerprint") != real_subject_fingerprint:
            return None

        matching_declarations = [
            d
            for d in declarations
            if isinstance(d.get("grant_ref"), Mapping) and d["grant_ref"].get("id") == grant_id
        ]
        if len(matching_declarations) != 1:
            return None
        declaration = matching_declarations[0]
        declaration_id = declaration.get("github_projection_grant_declaration_id")
        if not isinstance(declaration_id, str) or not declaration_id:
            return None

        request = {
            "schema_version": "0.1",
            "project_id": project_id,
            "subject_ref": dict(subject_ref),
            "subject_fingerprint": real_subject_fingerprint,
            "projection_kind": projection_kind,
            "target_repository": dict(target_repository),
            "payload_fingerprint": grant.get("payload_fingerprint"),
            "permitted_action": V3_PERMITTED_ACTION,
            "human_authority_ref": dict(human_authority_ref),
            "human_authority_signing_key": dict(human_authority_signing_key),
            "grants": [grant],
            "grant_declarations": [declaration],
        }
        try:
            decision = evaluate_projection_authorization(request)
        except AuthorityError:
            return None
        if decision.get("decision") != "PROJECTION_AUTHORIZED":
            return None

        decisions[projection_kind] = decision
        authorities[projection_kind] = V3PreIssuedProjectionAuthority(
            projection_kind=projection_kind,
            subject_ref=dict(subject_ref),
            subject_record=subject_record,
            github_projection_grant_ref={"kind": _GRANT_REF_KIND, "id": grant_id},
            github_projection_grant_declaration_ref={
                "kind": _DECLARATION_REF_KIND,
                "id": declaration_id,
            },
        )

    current_state = boot_context.current_state
    return V3AuthorizedExecutionContext(
        store=store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        github_authority_ref=human_authority_ref,
        authorities=authorities,
        state_revision=current_state["state_revision"],
        semantic_fingerprint=current_state["semantic_fingerprint"],
        decisions=decisions,
    )


#: Structural Review Round 13 (P14-R13-F1): the freshness re-validation function is now
#: ``manosube_agent_civilization.projection.execution_context_still_current``, imported above as
#: ``v3_execution_context_still_current`` -- a plain alias, not a separate definition. Round 12's
#: own module-level ``execute_v3_authorized_projection`` (a plain, stateless function
#: re-accepting *context* fresh on every call) is removed outright: Round 13 (P14-R13-F2) found
#: it structurally insufficient as a *bound* capability, since nothing in its own shape
#: prevented a caller from threading a *different* context object into each call. Callers now
#: construct ``manosube_agent_civilization.projection.ProjectionExecutionCapability`` directly
#: from the ``ProjectionExecutionContext`` this module's own ``resolve_v3_live_write_authority``
#: returns -- never through this test-fixture module, which defines no capability-constructing
#: function of its own.
