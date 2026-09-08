"""Genuine, canonically-issuable SHUKOU/Human Authority for V3 live-write execution
(Structural Review Round 6, Issue #62, P14-R6-F2; external trust anchor, Round 7, P14-R7-F1;
canonical issuable authority, Round 8, P14-R8-F1; Store/Boot-resolved authority routed to
execution, Round 9, P14-R9-F1).

Round 6 replaced a caller-computable digest with a genuinely Ed25519-signed record, but kept
the matching private key in the same importable module as the verifier. Round 7 removed that
private key entirely, replacing it with a fixed public trust anchor that could never actually
be issued. Round 8 corrected both defects by reusing the existing canonical Project Binding /
Human Authority / signed Grant Declaration / Authority Decision route
(:func:`~manosube_agent_civilization.authority.projection_authorization.
evaluate_projection_authorization`) -- but still let a caller hand this module the complete
``project_binding``/``grants``/``grant_declarations`` record **bodies** directly, as one
JSON-encoded blob. A caller who could fabricate a self-consistent, correctly-signed set of
bodies -- without ever actually committing any of it to the real canonical Store -- could
still mint material this module would accept.

Structural Review Round 9 (P14-R9-F1) closes that gap: this module now consumes only
project-scoped **references** (:class:`V3LiveWriteAuthorityReferences` -- a Store root, a
``project_id``, a ``project_binding_id``, and lists of ``{"kind", "id"}`` grant/declaration
references), never authoritative record bodies. :func:`resolve_v3_live_write_authority`
resolves the Project Binding through the identical canonical Boot route a real GitHub
projection call already uses (:func:`~manosube_agent_civilization.boot.boot_project`),
resolves each referenced grant/declaration through the Store's own ``resolve_record`` surface,
and only then asks :func:`~manosube_agent_civilization.authority.projection_authorization.
evaluate_projection_authorization` whether the resolved bodies authorize ``MATERIALIZE_
PROJECTION`` for a V3-configuration-shaped subject, independently for each of the three
projection kinds the V3 harness exercises. A fully self-consistent, correctly-signed but never
-committed set of bodies therefore authorizes nothing: ``store.resolve_record`` returns
``None`` for any reference that was never actually committed, and this module refuses before
ever reaching ``evaluate_projection_authorization``.

On success, :func:`resolve_v3_live_write_authority` returns one immutable
:class:`V3AuthorizedExecutionContext` -- the Store, the exact resolved references, the
verified Human Authority reference, and the Store's own ``state_revision``/
``semantic_fingerprint`` at the moment of authorization -- which the caller must thread
unchanged into the exact execution function that reaches the GitHub adapter. There is no
detached boolean gate: a caller cannot authorize against one set of Store-resolved references
and then execute against a different one, because the execution function accepts only this one
opaque context, never a separately assembled project_id/refs tuple of its own.
:func:`v3_execution_context_still_current` re-Boots the identical project/binding a context
already verified and requires the Store's own revision/fingerprint to be byte-identical to what
authorization itself observed, so a Store mutation between authorization and the moment
execution actually reaches the adapter is detected and refused rather than silently ignored.

No new Authority owner, private-key registry, signing service, token owner, or hidden
persistence surface is created here: the only concept this module still owns is *what subject*
is being authorized (the V3 target configuration itself, addressed by its own
``configuration_fingerprint``), never *how* that authorization is verified, and never *where*
its Project Binding, grants, or declarations are resolved from -- that remains the real
canonical Store and Boot, exactly as a production GitHub projection call already uses
(:func:`~manosube_agent_civilization.projection.route.project_to_github`, whose own
``_authorize_projection`` resolves caller-supplied grant/declaration **references** through the
Store in the identical shape this module now mirrors).

This module is deliberately test/harness-only, exactly as :mod:`tests.fixtures.
v3_target_configuration` already is for the configuration it binds -- a genuine live grant
must still be issued entirely outside this repository, by whoever genuinely holds the real
Project Binding's Human Authority private key, committed to the real canonical Store by
whatever process SHUKOU authorizes for that Store.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from manosube_agent_civilization.authority.errors import AuthorityError
from manosube_agent_civilization.authority.projection_authorization import (
    evaluate_projection_authorization,
)
from manosube_agent_civilization.binding.errors import BindingError
from manosube_agent_civilization.boot import BootError, boot_project
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.errors import StoreError

from .v3_target_configuration import V3TargetConfiguration

#: The one closed permitted-action literal every real GitHub projection operation already uses
#: (``authority/projection_authorization.py``'s own ``_PERMITTED_ACTIONS``) -- V3's own live
#: execution authorizes ``MATERIALIZE_PROJECTION`` exactly as a production projection call
#: does. No V3-specific action literal exists, and none is introduced here.
V3_PERMITTED_ACTION = "MATERIALIZE_PROJECTION"

#: The subject kind this module's own V3-configuration-shaped ``subject_ref`` names --
#: distinct from ``"difference"``/``"change"``/``"observation_evidence"``, the subject kinds a
#: *production* projection's own ``subject_ref`` names, so a V3 harness's own grant/
#: declaration/decision can never be mistaken for -- or substituted into -- a production
#: projection's own authorization, and vice versa.
V3_CONFIGURATION_SUBJECT_KIND = "v3_target_configuration"

#: Every projection kind the V3 harness exercises. An authorized V3 execution requires an
#: independent ``evaluate_projection_authorization`` ``PROJECTION_AUTHORIZED`` decision for
#: *each* of these -- one grant standing in for all three is never sufficient.
V3_PROJECTION_KINDS: tuple[str, ...] = (
    "DIFFERENCE_ISSUE",
    "CHANGE_PULL_REQUEST",
    "EVIDENCE_ARTIFACT",
)

#: The environment variable carrying the complete, JSON-encoded V3 live-write authority
#: **references** -- a Store root plus a ``project_id``/``project_binding_id``/grant and
#: declaration reference list, never record bodies (Structural Review Round 9, P14-R9-F1,
#: superseding Round 8's own now-removed ``V3_LIVE_WRITE_AUTHORITY_MATERIAL_ENV``, which
#: carried embedded bodies directly).
V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV = "MANOSUBE_P14_V3_LIVE_WRITE_AUTHORITY_REFERENCES"

_GRANT_REF_KIND = "github_projection_grant"
_DECLARATION_REF_KIND = "github_projection_grant_declaration"

#: Every exception :func:`~manosube_agent_civilization.boot.boot_project` may propagate for a
#: Store/Binding it cannot restore -- Boot's own errors, plus the Store- and Binding-owned
#: errors its docstring states it forwards unchanged, never swallowed and never re-interpreted
#: here as anything but refusal.
_BOOT_FAILURE_ERRORS: tuple[type[Exception], ...] = (BootError, StoreError, BindingError)


def v3_configuration_subject_ref(config: V3TargetConfiguration) -> dict[str, str]:
    """The V3-configuration-shaped ``subject_ref`` every grant/declaration/decision this
    module consumes must name -- content-addressed by the configuration's own
    ``configuration_fingerprint`` (already covering every bound field: repository, refs, SHA,
    artifact kinds/count, naming, cleanup, no-merge -- see ``v3_target_configuration.py``)."""

    return {"kind": V3_CONFIGURATION_SUBJECT_KIND, "id": config.configuration_fingerprint}


def v3_projection_authorization_request(
    config: V3TargetConfiguration,
    *,
    projection_kind: str,
    project_id: str,
    human_authority_ref: Mapping[str, Any],
    human_authority_signing_key: Mapping[str, Any],
    grants: list[Any],
    grant_declarations: list[Any],
) -> dict[str, Any]:
    """One exact ``evaluate_projection_authorization`` request binding *config* and
    *projection_kind* -- the identical request shape a production projection call builds,
    applied here to the V3-configuration subject instead of a Difference/Change/Evidence one.
    *grants*/*grant_declarations* are already Store-resolved bodies by the time this is called
    -- this function itself never resolves or trusts anything, it only shapes the request."""

    return {
        "schema_version": "0.1",
        "project_id": project_id,
        "subject_ref": v3_configuration_subject_ref(config),
        "subject_fingerprint": config.configuration_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": dict(config.target_repository),
        "payload_fingerprint": config.configuration_fingerprint,
        "permitted_action": V3_PERMITTED_ACTION,
        "human_authority_ref": dict(human_authority_ref),
        "human_authority_signing_key": dict(human_authority_signing_key),
        "grants": list(grants),
        "grant_declarations": list(grant_declarations),
    }


@dataclass(frozen=True, slots=True)
class V3LiveWriteAuthorityReferences:
    """Project-scoped **references** only -- never an authoritative Project Binding, grant,
    declaration, or Authority Decision body (Structural Review Round 9, P14-R9-F1). Every
    field here names *where* to resolve a canonical record from the real Store; none of them
    *is* a record."""

    store_root: str
    project_id: str
    project_binding_id: str
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


def load_v3_live_write_authority_references(
    env: Mapping[str, str] | None = None,
) -> V3LiveWriteAuthorityReferences | None:
    """Read and JSON-decode :data:`V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV`, or return ``None``
    if unset, unparseable, not a JSON object, or missing/malformed any required field --
    identical "malformed input is simply no authority, never an exception" discipline every
    other check here applies. *env* defaults to :data:`os.environ`; performs no filesystem or
    network access of its own -- only :func:`open_v3_live_write_store` and
    :func:`resolve_v3_live_write_authority` touch the Store."""

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

    grant_refs = _parse_ref_list(payload.get("github_projection_grant_refs"), kind=_GRANT_REF_KIND)
    declaration_refs = _parse_ref_list(
        payload.get("github_projection_grant_declaration_refs"), kind=_DECLARATION_REF_KIND
    )
    if grant_refs is None or declaration_refs is None:
        return None

    return V3LiveWriteAuthorityReferences(
        store_root=store_root,
        project_id=project_id,
        project_binding_id=project_binding_id,
        github_projection_grant_refs=grant_refs,
        github_projection_grant_declaration_refs=declaration_refs,
    )


def _schema_root() -> Path:
    from tests.state_helpers import SCHEMA_ROOT

    return SCHEMA_ROOT


def open_v3_live_write_store(
    references: V3LiveWriteAuthorityReferences | None,
) -> FileStateStore | None:
    """Open the real canonical Store *references* names, or return ``None`` on any failure --
    a local filesystem open, never network access. This is the one additional I/O boundary
    this module has beyond reading the environment (Structural Review Round 9, P14-R9-F1):
    this module resolves records FROM a Store, it never accepts one constructed from
    caller-supplied bodies."""

    if references is None:
        return None
    try:
        return FileStateStore(Path(references.store_root), schema_root=_schema_root())
    except (OSError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class V3AuthorizedExecutionContext:
    """The one resolved, verified authority context a genuinely authorized V3 run threads
    unchanged into the exact execution function that reaches the GitHub adapter (Structural
    Review Round 9, P14-R9-F1) -- never a detached boolean gate followed by a separately
    fixture-authorized projection. Every field here was independently resolved and reverified
    from the real canonical Store at the moment of authorization; nothing here was ever
    accepted as a caller-supplied body. ``decisions`` preserves the exact
    ``evaluate_projection_authorization`` result for each projection kind this context
    authorized, keyed by projection kind."""

    store: FileStateStore
    project_id: str
    project_binding_id: str
    github_authority_ref: Mapping[str, Any]
    github_projection_grant_refs: tuple[Mapping[str, str], ...]
    github_projection_grant_declaration_refs: tuple[Mapping[str, str], ...]
    state_revision: int
    semantic_fingerprint: Mapping[str, Any]
    decisions: Mapping[str, Mapping[str, Any]]


def _resolve_ref(
    store: FileStateStore, project_id: str, ref: Mapping[str, str], *, kind: str
) -> Mapping[str, Any] | None:
    """Resolve exactly the record *ref* names, through the Store's own single by-(kind, id)
    lookup surface -- never a caller-supplied body, and refused outright if *ref* does not even
    name the expected kind."""

    if ref.get("kind") != kind:
        return None
    record_id = ref.get("id")
    if not isinstance(record_id, str) or not record_id:
        return None
    try:
        return store.resolve_record(project_id, kind, record_id)
    except _BOOT_FAILURE_ERRORS:
        return None


def resolve_v3_live_write_authority(
    store: FileStateStore | None,
    config: V3TargetConfiguration | None,
    references: V3LiveWriteAuthorityReferences | None,
) -> V3AuthorizedExecutionContext | None:
    """Resolve *references* against *store* -- the real canonical Store, via the identical
    canonical Boot route a real GitHub projection call already uses
    (:func:`~manosube_agent_civilization.boot.boot_project`) -- and return one
    :class:`V3AuthorizedExecutionContext` if, and only if, every resolved grant/declaration
    genuinely authorizes ``MATERIALIZE_PROJECTION`` for *config*'s own V3-configuration
    subject, independently for *every* projection kind in :data:`V3_PROJECTION_KINDS`, through
    :func:`~manosube_agent_civilization.authority.projection_authorization.
    evaluate_projection_authorization` -- the same function a production projection call
    already trusts. Returns ``None`` on any failure: *store*/*config*/*references* missing,
    the Project Binding failing to Boot-restore, any referenced grant or declaration failing
    to resolve from the Store (Structural Review Round 9, P14-R9-F1's own required control: a
    fully self-consistent, correctly-signed, but never-committed record must never authorize),
    or any resolved projection kind's own authorization request refusing. Performs Store reads
    only -- no network access of any kind, and never raises; a malformed grant, declaration, or
    request that raises inside ``evaluate_projection_authorization`` is caught here as
    :class:`~manosube_agent_civilization.authority.errors.AuthorityError` and treated as
    refusal, since a live-write gate must never raise."""

    if store is None or config is None or references is None:
        return None

    try:
        boot_context = boot_project(
            store,
            project_id=references.project_id,
            project_binding_id=references.project_binding_id,
        )
    except _BOOT_FAILURE_ERRORS:
        return None

    if boot_context.project_id != references.project_id:
        return None
    if boot_context.project_binding_id != references.project_binding_id:
        return None

    human_authority_ref = boot_context.human_authority_ref
    human_authority_signing_key = boot_context.project_binding.get("human_authority_signing_key")
    if not isinstance(human_authority_signing_key, Mapping):
        return None

    grants: list[Mapping[str, Any]] = []
    for ref in references.github_projection_grant_refs:
        body = _resolve_ref(store, references.project_id, ref, kind=_GRANT_REF_KIND)
        if body is None:
            return None
        grants.append(body)

    declarations: list[Mapping[str, Any]] = []
    for ref in references.github_projection_grant_declaration_refs:
        body = _resolve_ref(store, references.project_id, ref, kind=_DECLARATION_REF_KIND)
        if body is None:
            return None
        declarations.append(body)

    decisions: dict[str, Mapping[str, Any]] = {}
    for projection_kind in V3_PROJECTION_KINDS:
        request = v3_projection_authorization_request(
            config,
            projection_kind=projection_kind,
            project_id=references.project_id,
            human_authority_ref=human_authority_ref,
            human_authority_signing_key=human_authority_signing_key,
            grants=grants,
            grant_declarations=declarations,
        )
        try:
            decision = evaluate_projection_authorization(request)
        except AuthorityError:
            return None
        if decision.get("decision") != "PROJECTION_AUTHORIZED":
            return None
        decisions[projection_kind] = decision

    current_state = boot_context.current_state
    return V3AuthorizedExecutionContext(
        store=store,
        project_id=references.project_id,
        project_binding_id=references.project_binding_id,
        github_authority_ref=human_authority_ref,
        github_projection_grant_refs=references.github_projection_grant_refs,
        github_projection_grant_declaration_refs=(
            references.github_projection_grant_declaration_refs
        ),
        state_revision=current_state["state_revision"],
        semantic_fingerprint=current_state["semantic_fingerprint"],
        decisions=decisions,
    )


def v3_execution_context_still_current(context: V3AuthorizedExecutionContext | None) -> bool:
    """Re-Boot the identical project/binding *context* already verified and require the
    Store's own ``state_revision``/``semantic_fingerprint`` to be byte-identical to what
    authorization itself observed -- refusing on any Store mutation between authorization and
    the moment *context* is actually handed to the adapter-reaching execution call
    (Structural Review Round 9, P14-R9-F1: fail closed on Store revision drift). Returns
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
