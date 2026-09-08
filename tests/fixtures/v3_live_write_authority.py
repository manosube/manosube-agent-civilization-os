"""Genuine, canonically-issuable SHUKOU/Human Authority for V3 live-write execution
(Structural Review Round 6, Issue #62, P14-R6-F2; external trust anchor, Round 7, P14-R7-F1;
canonical issuable authority, Round 8, P14-R8-F1; Store/Boot-resolved authority routed to
execution, Round 9, P14-R9-F1; trusted Boot root and pre-issued execution authority,
Round 10, P14-R10-F1).

Round 9 replaced caller-supplied Project Binding/grant/declaration record **bodies** with
project-scoped **references** resolved against a real canonical Store -- but the *Store
itself* (its root path, ``project_id``, and ``project_binding_id``) still came from the same
caller-supplied ``references`` blob. A caller who fully and genuinely commits their own
self-consistent, attacker-controlled Store -- their own Project Binding, their own signing
key, their own genuinely-signed grants -- could simply point ``store_root`` at it and pass
Round 9's own checks: every record would genuinely resolve, every signature would genuinely
verify, because the whole universe of records was internally self-consistent by construction.
Round 9 never fixed *which* Store was trustworthy in the first place.

Round 10 (P14-R10-F1) closes that gap by splitting trust into two independently supplied
inputs this module never lets a caller conflate:

1. :class:`V3TrustedBootRoot` -- the Store root, ``project_id``, and ``project_binding_id``,
   supplied through its own environment variable
   (:data:`V3_TRUSTED_BOOT_ROOT_ENV`), entirely independent of the untrusted authority
   references below. :func:`resolve_v3_live_write_authority` never selects a Store, Project,
   or Project Binding from anything a caller's authority references carry -- there is nowhere
   in :class:`V3LiveWriteAuthorityReferences` even capable of naming one.
2. :class:`V3LiveWriteAuthorityReferences` -- now *only* grant/declaration reference lists,
   resolved exclusively **within** the trusted Store the first input already fixed.

Round 9 also let the live *execution* path mint a fresh, subject-scoped grant/declaration per
run using this repository's own test-only signing key
(:mod:`tests.fixtures.product_binding`) -- a detour Round 8's own docstring already named as
the exact defect the whole canonical-Authority-route design exists to close. Round 10 requires
every subject-specific grant, signed declaration, and Authority Decision that
``project_to_github`` actually consumes to already be externally issued, committed,
Store-resolved, and identity-recomputed from the trusted Store *before* this module is ever
asked to authorize anything -- :func:`resolve_v3_live_write_authority` resolves exactly one
pre-issued grant/declaration pair per :data:`V3_PROJECTION_KINDS`, carries them unchanged in
:class:`V3AuthorizedExecutionContext`, and never mints, signs, or commits anything itself.
This module holds no private key, imports no signing helper (repository-held or otherwise),
and opens no Store from caller-supplied data -- proven by
``tests/contract/projection/test_v3_live_write_authority_static_conformance.py``.

:func:`v3_execution_context_still_current` re-Boots the trusted Store immediately before every
adapter-reaching call and requires its ``state_revision``/``semantic_fingerprint`` to be
byte-identical to what authorization itself observed, so a Store mutation -- or any
substitution of the resolved context's own fields -- between authorization and execution is
detected and refused rather than silently accepted.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import os
from pathlib import Path
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
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.errors import StoreError

from .v3_target_configuration import V3TargetConfiguration

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

#: The environment variable carrying the independently supplied trusted runtime Store/Boot
#: root (Structural Review Round 10, P14-R10-F1) -- a Store root, ``project_id``, and
#: ``project_binding_id``, fixed entirely outside caller-controlled authority references.
V3_TRUSTED_BOOT_ROOT_ENV = "MANOSUBE_P14_V3_TRUSTED_BOOT_ROOT"

#: The environment variable carrying the complete, JSON-encoded V3 live-write authority
#: **references** -- grant/declaration reference lists only (Structural Review Round 10,
#: P14-R10-F1 narrows this further: Round 9's own shape additionally carried a Store root and
#: project/binding identity, which let a caller select an arbitrary, if fully self-consistent,
#: Store -- neither field exists in this shape at all any more).
V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV = "MANOSUBE_P14_V3_LIVE_WRITE_AUTHORITY_REFERENCES"

_GRANT_REF_KIND = "github_projection_grant"
_DECLARATION_REF_KIND = "github_projection_grant_declaration"

#: Every exception :func:`~manosube_agent_civilization.boot.boot_project` may propagate for a
#: Store/Binding it cannot restore -- Boot's own errors, plus the Store- and Binding-owned
#: errors its docstring states it forwards unchanged, never swallowed and never re-interpreted
#: here as anything but refusal.
_BOOT_FAILURE_ERRORS: tuple[type[Exception], ...] = (BootError, StoreError, BindingError)


def _schema_root() -> Path:
    from tests.state_helpers import SCHEMA_ROOT

    return SCHEMA_ROOT


@dataclass(frozen=True, slots=True)
class V3TrustedBootRoot:
    """The independently supplied trusted runtime Store/Boot root (Structural Review
    Round 10, P14-R10-F1): a Store root, ``project_id``, and ``project_binding_id``, fixed
    entirely outside any caller-supplied authority reference. Every grant/declaration
    reference :class:`V3LiveWriteAuthorityReferences` names is resolved within, and only
    within, the Store this root identifies."""

    store_root: str
    project_id: str
    project_binding_id: str


def load_v3_trusted_boot_root(env: Mapping[str, str] | None = None) -> V3TrustedBootRoot | None:
    """Read and JSON-decode :data:`V3_TRUSTED_BOOT_ROOT_ENV`, or return ``None`` if unset,
    unparseable, not a JSON object, or missing/malformed any required field -- the identical
    "malformed input is simply no authority, never an exception" discipline every other check
    here applies. *env* defaults to :data:`os.environ`; performs no filesystem or network
    access of its own."""

    source = env if env is not None else os.environ
    raw = source.get(V3_TRUSTED_BOOT_ROOT_ENV)
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None

    store_root = payload.get("store_root")
    project_id = payload.get("project_id")
    project_binding_id = payload.get("project_binding_id")
    if not (
        isinstance(store_root, str)
        and store_root
        and isinstance(project_id, str)
        and project_id
        and isinstance(project_binding_id, str)
        and project_binding_id
    ):
        return None

    return V3TrustedBootRoot(
        store_root=store_root, project_id=project_id, project_binding_id=project_binding_id
    )


def open_v3_trusted_store(trusted_root: V3TrustedBootRoot | None) -> FileStateStore | None:
    """Open the real canonical Store *trusted_root* names, or return ``None`` on any failure --
    a local filesystem open, never network access. This is the *only* function in this module
    capable of opening a Store, and it accepts only a :class:`V3TrustedBootRoot` -- never a
    :class:`V3LiveWriteAuthorityReferences`, which carries no Store-selecting field of any kind
    (Structural Review Round 10, P14-R10-F1)."""

    if trusted_root is None:
        return None
    try:
        return FileStateStore(Path(trusted_root.store_root), schema_root=_schema_root())
    except (OSError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class V3LiveWriteAuthorityReferences:
    """Project-scoped grant/declaration **references** only -- never a Store root, a
    ``project_id``, a ``project_binding_id``, or an authoritative record body (Structural
    Review Round 9, P14-R9-F1; narrowed further by Round 10, P14-R10-F1, which removes the
    Store-selecting fields Round 9's own shape still carried). Every reference here names
    *where*, within the independently trusted Store, to resolve a canonical record; none of
    them *is* a record, and none of them can select which Store to resolve from."""

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
#: Round 10, P14-R10-F1).
_FORBIDDEN_REFERENCE_KEYS = ("store_root", "project_id", "project_binding_id")


def load_v3_live_write_authority_references(
    env: Mapping[str, str] | None = None,
) -> V3LiveWriteAuthorityReferences | None:
    """Read and JSON-decode :data:`V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV`, or return ``None``
    if unset, unparseable, not a JSON object, missing/malformed any required field, or
    attempting to carry a Store-selecting field (``store_root``/``project_id``/
    ``project_binding_id``) at all -- fail closed on the exact smuggling attempt Round 10's own
    finding names, never silently drop the extra keys and proceed. *env* defaults to
    :data:`os.environ`; performs no filesystem or network access of its own -- only
    :func:`open_v3_trusted_store` and :func:`resolve_v3_live_write_authority` touch the
    Store, and only through :class:`V3TrustedBootRoot`."""

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


@dataclass(frozen=True, slots=True)
class V3PreIssuedProjectionAuthority:
    """One pre-issued, Store-resolved, identity-recomputed grant/declaration pair for exactly
    one projection kind, bound to whatever real subject the trusted Store's own pre-issued
    material already names -- never minted, signed, or committed by this module or by the live
    execution path (Structural Review Round 10, P14-R10-F1). ``subject_ref`` is read only from
    the resolved, identity-verified grant itself, never independently guessed or constructed
    here."""

    projection_kind: str
    subject_ref: Mapping[str, str]
    github_projection_grant_ref: Mapping[str, str]
    github_projection_grant_declaration_ref: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class V3AuthorizedExecutionContext:
    """The one resolved, verified authority context a genuinely authorized V3 run threads
    unchanged into the exact execution function that reaches the GitHub adapter -- never a
    detached boolean gate followed by a separately fixture-authorized projection, and never a
    live path capable of minting the subject-specific authority it consumes (Structural Review
    Round 9, P14-R9-F1; Round 10, P14-R10-F1). Every field here was independently resolved and
    reverified from the trusted Store at the moment of authorization; nothing here was ever
    accepted as a caller-supplied body. ``authorities`` carries, for each of
    :data:`V3_PROJECTION_KINDS`, the exact pre-issued grant/declaration/subject reference the
    matching ``project_to_github`` call must use -- and no other. ``decisions`` preserves the
    exact ``evaluate_projection_authorization`` result for each kind."""

    store: FileStateStore
    project_id: str
    project_binding_id: str
    github_authority_ref: Mapping[str, Any]
    authorities: Mapping[str, V3PreIssuedProjectionAuthority]
    state_revision: int
    semantic_fingerprint: Mapping[str, Any]
    decisions: Mapping[str, Mapping[str, Any]]


def _resolve_grant(
    store: FileStateStore, project_id: str, ref: Mapping[str, str]
) -> Mapping[str, Any] | None:
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
        body = store.resolve_record(project_id, _GRANT_REF_KIND, record_id)
    except _BOOT_FAILURE_ERRORS:
        return None
    if body is None:
        return None
    try:
        if github_projection_grant_id(dict(body)) != body.get("github_projection_grant_id"):
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return body


def _resolve_declaration(
    store: FileStateStore, project_id: str, ref: Mapping[str, str]
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
        body = store.resolve_record(project_id, _DECLARATION_REF_KIND, record_id)
    except _BOOT_FAILURE_ERRORS:
        return None
    if body is None:
        return None
    try:
        verify_github_projection_grant_declaration_identity(dict(body))
    except _BOOT_FAILURE_ERRORS:
        return None
    return body


def resolve_v3_live_write_authority(
    trusted_root: V3TrustedBootRoot | None,
    config: V3TargetConfiguration | None,
    references: V3LiveWriteAuthorityReferences | None,
) -> V3AuthorizedExecutionContext | None:
    """Resolve *references* -- grant/declaration reference lists only -- exclusively within the
    Store *trusted_root* independently identifies (Structural Review Round 10, P14-R10-F1),
    Boot-restore the exact Project/Binding *trusted_root* names
    (:func:`~manosube_agent_civilization.boot.boot_project`), and return one
    :class:`V3AuthorizedExecutionContext` if, and only if, exactly one resolved grant and
    exactly one anchoring declaration exist for *every* projection kind in
    :data:`V3_PROJECTION_KINDS`, each bound to *config*'s own ``target_repository``, and each
    genuinely authorizes ``MATERIALIZE_PROJECTION`` through
    :func:`~manosube_agent_civilization.authority.projection_authorization.
    evaluate_projection_authorization` -- the same function a production projection call
    already trusts. Returns ``None`` on any failure: *trusted_root*/*config*/*references*
    missing, the Store failing to open, the Project Binding failing to Boot-restore, any
    referenced grant or declaration failing to resolve or reproduce its own claimed identity,
    zero or more than one grant/declaration per kind, a grant bound to a different
    ``target_repository``, or any resolved kind's own authorization request refusing. Performs
    Store reads only -- no network access of any kind, and never raises; a malformed grant,
    declaration, or request that raises inside ``evaluate_projection_authorization`` is caught
    here as :class:`~manosube_agent_civilization.authority.errors.AuthorityError` and treated
    as refusal, since a live-write gate must never raise. Never mints, signs, or commits
    anything -- every record consumed here was already externally issued and committed before
    this call."""

    if trusted_root is None or config is None or references is None:
        return None

    store = open_v3_trusted_store(trusted_root)
    if store is None:
        return None

    try:
        boot_context = boot_project(
            store,
            project_id=trusted_root.project_id,
            project_binding_id=trusted_root.project_binding_id,
        )
    except _BOOT_FAILURE_ERRORS:
        return None

    if boot_context.project_id != trusted_root.project_id:
        return None
    if boot_context.project_binding_id != trusted_root.project_binding_id:
        return None

    human_authority_ref = boot_context.human_authority_ref
    human_authority_signing_key = boot_context.project_binding.get("human_authority_signing_key")
    if not isinstance(human_authority_signing_key, Mapping):
        return None

    grants: list[Mapping[str, Any]] = []
    for ref in references.github_projection_grant_refs:
        body = _resolve_grant(store, trusted_root.project_id, ref)
        if body is None:
            return None
        grants.append(body)

    declarations: list[Mapping[str, Any]] = []
    for ref in references.github_projection_grant_declaration_refs:
        body = _resolve_declaration(store, trusted_root.project_id, ref)
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
        subject_fingerprint = grant.get("subject_fingerprint")
        target_repository = grant.get("target_repository")
        payload_fingerprint = grant.get("payload_fingerprint")
        grant_id = grant.get("github_projection_grant_id")
        if not isinstance(subject_ref, Mapping) or not isinstance(target_repository, Mapping):
            return None
        if not isinstance(grant_id, str) or not grant_id:
            return None
        if dict(target_repository) != dict(config.target_repository):
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
            "project_id": trusted_root.project_id,
            "subject_ref": dict(subject_ref),
            "subject_fingerprint": subject_fingerprint,
            "projection_kind": projection_kind,
            "target_repository": dict(target_repository),
            "payload_fingerprint": payload_fingerprint,
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
            github_projection_grant_ref={"kind": _GRANT_REF_KIND, "id": grant_id},
            github_projection_grant_declaration_ref={
                "kind": _DECLARATION_REF_KIND,
                "id": declaration_id,
            },
        )

    current_state = boot_context.current_state
    return V3AuthorizedExecutionContext(
        store=store,
        project_id=trusted_root.project_id,
        project_binding_id=trusted_root.project_binding_id,
        github_authority_ref=human_authority_ref,
        authorities=authorities,
        state_revision=current_state["state_revision"],
        semantic_fingerprint=current_state["semantic_fingerprint"],
        decisions=decisions,
    )


def v3_execution_context_still_current(context: V3AuthorizedExecutionContext | None) -> bool:
    """Re-Boot the identical project/binding *context* already verified and require the
    Store's own ``state_revision``/``semantic_fingerprint`` to be byte-identical to what
    authorization itself observed -- refusing on any Store mutation between authorization and
    the moment *context* is actually handed to the adapter-reaching execution call. Intended to
    be called immediately before *every* adapter-reaching ``project_to_github`` call this run
    makes, not merely once at the start (Structural Review Round 10, P14-R10-F1). Returns
    ``False`` for ``context=None`` and never raises."""

    if context is None:
        return False
    try:
        boot_context = boot_project(
            context.store,
            project_id=context.project_id,
            project_binding_id=context.project_binding_id,
        )
    except _BOOT_FAILURE_ERRORS:
        return False
    current_state = boot_context.current_state
    return (
        current_state.get("state_revision") == context.state_revision
        and current_state.get("semantic_fingerprint") == context.semantic_fingerprint
    )
