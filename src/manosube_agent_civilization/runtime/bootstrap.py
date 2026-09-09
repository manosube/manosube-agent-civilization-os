"""The trusted runtime bootstrap: production Phase 14 capability provisioning (Phase 15, Issue
#64, V5).

Structural Review Round 12/13 of Phase 14 (Issue #62, P14-R12-F1, P14-R13-F1/F2) drew the
Phase 14/Phase 15 boundary at a formal execution *interface* -- :class:`~manosube_agent_civilization.
projection.ProjectionExecutionCapability`, consuming an already-resolved, opaque
:class:`~manosube_agent_civilization.projection.ProjectionExecutionContext` -- while explicitly
deferring *provisioning* that context from canonical Store/Boot state to Phase 15. This module
is that deferred provisioning: :func:`bootstrap_projection_execution_capability` is a
production-general adaptation of Phase 14's own V3 test-fixture layer's live-write-authority
resolver (``tests/fixtures/`` -- deliberately not named literally here; see this package's own
static conformance test, which forbids this shipped module from naming that test-only module
even in prose) -- the identical Store-resolve/identity-recompute/
``evaluate_projection_authorization``-once/one-grant-one-declaration-per-kind discipline,
reused rather than reinvented -- with two deliberate differences appropriate to shipped
production code rather than a test-only live-write gate:

- **Dynamic kind set.** The V3 fixture requires exactly the three fixed kinds in its own
  ``V3_PROJECTION_KINDS``. A real deployment may authorize any subset of the closed
  :data:`~manosube_agent_civilization.projection.types.PROJECTION_KINDS` vocabulary a caller's
  own supplied grant references actually name -- this function derives the kind set from the
  resolved grants themselves, never a fixed constant.
- **Raises rather than returns ``None``.** The V3 fixture is deliberately a fail-closed gate
  that *never raises*, appropriate to a test harness deciding whether to attempt a live write at
  all. This function is an ordinary production route, like every other canonical route in this
  repository (``boot.boot_project``, ``projection.route.project_to_github``): it raises
  :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError` (or lets
  ``boot_project``'s/``evaluate_projection_authorization``'s own errors propagate unchanged) on
  any refusal, so a real caller can see *why* provisioning failed.

**Structural Review Round 1 (P15-R1-F4): the trust root is a type, not a parameter list.**
As first delivered, :func:`bootstrap_projection_execution_capability` took ``store``,
``project_id``, and ``project_binding_id`` as its own free parameters and proved only that the
world *inside* that caller-selected Store was internally self-consistent. That is not a
control: an attacker can assemble an entirely separate Store -- its own Human Authority signing
key, its own project_binding, its own grants, declarations, and subjects, every one of them
genuinely valid on its own terms -- hand it in, and receive a real
:class:`~manosube_agent_civilization.projection.ProjectionExecutionCapability`, because nothing
in the function's own signature distinguished "the canonical adopted Store" from "any
internally consistent Store a caller happens to pass". Adding an environment digest, a
hardcoded repository key, or any other anchor a caller can also select would only move the
same problem one level out.

The correction is structural rather than evidential: provisioning is now two steps, and the
function no longer has *any* parameter through which an alternate Store, Project, or Binding
could be named at all.

```text
provision_trusted_runtime_root(store, project_id=..., project_binding_id=...)
    -> TrustedRuntimeRoot            an opaque, frozen, type-checked handle fixing which
                                     Store/Project/Binding are in play; constructible only
                                     through this function (a module-private sentinel is a
                                     required constructor argument), and deliberately
                                     performing no Boot of its own -- Boot happens fresh
                                     inside the bootstrap call, so a root can never carry a
                                     stale "was verified once, long ago" verdict

bootstrap_projection_execution_capability(trusted_runtime_root, *, grant refs, declaration refs)
    -> ProjectionExecutionCapability  reads the store/project/binding from the root alone,
                                      and resolves every reference exclusively within it
```

Deciding *which* root is the canonical one remains, correctly, the deployment's own
responsibility -- exactly as choosing which Store to open always was. What changed is that the
decision now happens once, visibly, at a dedicated provisioning boundary, instead of being
re-offered as an ordinary keyword argument on every capability request.

This module imports no ``tests.*`` module (proved by static conformance -- the identical
discipline ``projection/execution.py``'s own static conformance test already establishes),
constructs no :class:`~manosube_agent_civilization.store.file_store.FileStateStore` of its own
(``store`` is always the caller-injected, already-open object -- the identical discipline
Phase 14 Round 11, P14-R11-F1, already established), mints no Authority record of any kind
(it only resolves and independently reverifies grants/declarations a Human Authority already
issued and a Store already committed), and accepts no authoritative record body directly --
only ``{"kind", "id"}`` references, resolved exclusively within the injected *store*. It makes
zero live network calls of its own; the adapter that later reaches a network at all is supplied
by :meth:`~manosube_agent_civilization.projection.ProjectionExecutionCapability.execute`'s own
caller, never by this module.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from typing import Any

from manosube_agent_civilization.authority import (
    PROJECTION_AUTHORIZED,
    evaluate_projection_authorization,
)
from manosube_agent_civilization.authority.identity import github_projection_grant_id
from manosube_agent_civilization.binding.identity import (
    verify_github_projection_grant_declaration_identity,
)
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.change.identity import (
    change_id as _change_id,
    change_semantic_fingerprint as _change_semantic_fingerprint,
)
from manosube_agent_civilization.difference.identity import difference_id as _difference_id
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as _CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)
from manosube_agent_civilization.evidence.identity import (
    evidence_semantic_fingerprint as _evidence_semantic_fingerprint,
)
from manosube_agent_civilization.projection import (
    PreIssuedProjectionAuthority,
    ProjectionExecutionCapability,
    ProjectionExecutionContext,
)

from .errors import RuntimeRequirementError

_GRANT_RECORD_KIND = "github_projection_grant"
_DECLARATION_RECORD_KIND = "github_projection_grant_declaration"
_PERMITTED_ACTION = "MATERIALIZE_PROJECTION"
_DIFFERENCE_SCHEMA_BASE = _CANONICAL_SCHEMA_BASE + "difference/"
_CHANGE_SCHEMA_BASE = _CANONICAL_SCHEMA_BASE + "change/"

#: Which real canonical subject kind each projection kind's own pre-issued grant must name --
#: the identical pairing :mod:`~manosube_agent_civilization.projection.route` itself enforces.
_SUBJECT_KIND_FOR_PROJECTION_KIND: dict[str, str] = {
    "DIFFERENCE_ISSUE": "difference",
    "CHANGE_PULL_REQUEST": "change",
    "EVIDENCE_ARTIFACT": "observation_evidence",
}


#: The one object :class:`TrustedRuntimeRoot` accepts as proof that
#: :func:`provision_trusted_runtime_root` -- and nothing else -- built it. Module-private and
#: never exported, so no caller outside this module holds a reference to it; a constructed
#: root does not retain it either (see :meth:`TrustedRuntimeRoot.__post_init__`), so holding a
#: legitimate root grants no ability to forge a second one naming a different Store.
_PROVISIONING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class TrustedRuntimeRoot:
    """One opaque, immutable handle naming exactly which Store, Project, and Project Binding a
    trusted runtime provisioning call operates within (P15-R1-F4).

    Constructible only through :func:`provision_trusted_runtime_root`: *provisioning_sentinel*
    is a required constructor argument, so direct construction raises ``TypeError`` for
    omitting it and :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError`
    for supplying anything that is not the module-private sentinel. This is what makes the type
    unforgeable *by shape alone* -- a caller cannot satisfy
    :func:`bootstrap_projection_execution_capability`'s own ``isinstance`` check merely by
    passing some other object carrying ``store``/``project_id``/``project_binding_id``
    attributes.

    This type verifies nothing about the world it names, deliberately: it holds no Boot
    verdict, no resolved record, and no fingerprint, so it can never be a stale attestation
    that something *was* valid at provisioning time. Every verification happens fresh inside
    the bootstrap call that consumes it.
    """

    store: Any
    project_id: str
    project_binding_id: str
    provisioning_sentinel: Any

    def __post_init__(self) -> None:
        if self.provisioning_sentinel is not _PROVISIONING_SENTINEL:
            raise RuntimeRequirementError(
                "TrustedRuntimeRoot may only be constructed through "
                "provision_trusted_runtime_root -- a directly constructed root would be "
                "exactly the caller-selected trust anchor this type exists to remove"
            )
        # Do not retain the sentinel: a legitimately provisioned root must not become a
        # capability to mint further roots naming some other Store.
        object.__setattr__(self, "provisioning_sentinel", None)


def _require_canonical_identity(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeRequirementError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise RuntimeRequirementError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def provision_trusted_runtime_root(
    store: Any, *, project_id: str, project_binding_id: str
) -> TrustedRuntimeRoot:
    """Return the one :class:`TrustedRuntimeRoot` naming *store*/*project_id*/
    *project_binding_id* -- the single, explicit place a deployment decides which world its
    trusted runtime provisioning operates within (P15-R1-F4).

    *store* is always the caller's own already-open object; this function opens, selects, and
    constructs no Store of its own (the identical discipline Phase 14 Round 11, P14-R11-F1,
    already established), calls no Boot, resolves no record, and commits nothing. It only
    fixes, once and opaquely, *which* root is in play, so that every later capability request
    reads that root instead of re-offering the same choice as an ordinary keyword argument.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    return TrustedRuntimeRoot(store, project_id, project_binding_id, _PROVISIONING_SENTINEL)


def _require_reference(value: Any, *, context: str, kind: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise RuntimeRequirementError(f"{context} must be an explicit reference object: {value!r}")
    if value.get("kind") != kind:
        raise RuntimeRequirementError(f"{context} does not name kind={kind!r}: {value!r}")
    record_id = value.get("id")
    if not isinstance(record_id, str) or not record_id:
        raise RuntimeRequirementError(f"{context} carries no readable id: {value!r}")
    return {"kind": kind, "id": record_id}


def _resolve_grant(store: Any, project_id: str, ref: Any, *, context: str) -> dict[str, Any]:
    checked = _require_reference(ref, context=context, kind=_GRANT_RECORD_KIND)
    resolved = store.resolve_record(project_id, _GRANT_RECORD_KIND, checked["id"])
    if resolved is None:
        raise RuntimeRequirementError(
            f"{context} does not resolve for project {project_id!r}: {checked}"
        )
    body = dict(resolved)
    if github_projection_grant_id(body) != body.get("github_projection_grant_id"):
        raise RuntimeRequirementError(
            f"{context} resolved a grant whose own recomputed identity does not match its "
            "declared value -- refusing to trust it"
        )
    return body


def _resolve_declaration(store: Any, project_id: str, ref: Any, *, context: str) -> dict[str, Any]:
    checked = _require_reference(ref, context=context, kind=_DECLARATION_RECORD_KIND)
    resolved = store.resolve_record(project_id, _DECLARATION_RECORD_KIND, checked["id"])
    if resolved is None:
        raise RuntimeRequirementError(
            f"{context} does not resolve for project {project_id!r}: {checked}"
        )
    body = dict(resolved)
    verify_github_projection_grant_declaration_identity(body)
    return body


def _resolve_subject(
    store: Any, project_id: str, subject_ref: Mapping[str, Any]
) -> tuple[dict[str, Any], str]:
    kind = subject_ref.get("kind")
    record_id = subject_ref.get("id")
    if kind not in _SUBJECT_KIND_FOR_PROJECTION_KIND.values():
        raise RuntimeRequirementError(f"subject_ref names an unrecognized kind: {subject_ref!r}")
    if not isinstance(record_id, str) or not record_id:
        raise RuntimeRequirementError(f"subject_ref carries no readable id: {subject_ref!r}")
    resolved = store.resolve_record(project_id, kind, record_id)
    if resolved is None:
        raise RuntimeRequirementError(
            f"subject_ref does not resolve for project {project_id!r}: {kind}/{record_id}"
        )
    body = dict(resolved)

    if kind == "difference":
        if body.get("project_id") != project_id:
            raise RuntimeRequirementError("subject_record.project_id does not match project_id")
        _validate_canonical_record(body, "difference.schema.json", base=_DIFFERENCE_SCHEMA_BASE)
        real_id = _difference_id(body)
        if record_id != real_id:
            raise RuntimeRequirementError(
                "subject_ref does not name the real, recomputed identity of subject_record"
            )
        real_fingerprint = "sha256:" + hashlib.sha256(real_id.encode("utf-8")).hexdigest()
    elif kind == "change":
        if body.get("project_id") != project_id:
            raise RuntimeRequirementError("subject_record.project_id does not match project_id")
        _validate_canonical_record(body, "change.schema.json", base=_CHANGE_SCHEMA_BASE)
        real_id = _change_id(body)
        if record_id != real_id:
            raise RuntimeRequirementError(
                "subject_ref does not name the real, recomputed identity of subject_record"
            )
        real_fingerprint = _change_semantic_fingerprint(body)
    else:
        real_fingerprint = _evidence_semantic_fingerprint(body)

    return body, real_fingerprint


def bootstrap_projection_execution_capability(
    trusted_runtime_root: TrustedRuntimeRoot,
    *,
    github_projection_grant_refs: list[Mapping[str, str]] | tuple[Mapping[str, str], ...],
    github_projection_grant_declaration_refs: list[Mapping[str, str]]
    | tuple[Mapping[str, str], ...],
) -> ProjectionExecutionCapability:
    """Resolve *github_projection_grant_refs*/*github_projection_grant_declaration_refs* --
    references only, never record bodies -- exclusively within *trusted_runtime_root*'s own
    Store, the already-open object a deployment fixed once through
    :func:`provision_trusted_runtime_root` and which this function never opens, selects, or
    constructs itself.

    **This signature carries no ``store``, ``project_id``, or ``project_binding_id``
    parameter at all** (P15-R1-F4): there is no call shape through which a caller could name
    an alternate, internally self-consistent world -- only a pre-vetted opaque root, plus
    grant/declaration *references* resolved exclusively within it. A first argument that is
    not a genuine :class:`TrustedRuntimeRoot` is refused at the type check, before Boot is
    reached at all.

    Boot-restores the exact Project/Binding the root names
    (:func:`~manosube_agent_civilization.boot.boot_project`, called fresh here rather than at
    provisioning time, so no root can ever carry a stale verdict), and returns one
    :class:`~manosube_agent_civilization.projection.ProjectionExecutionCapability` bound to a
    freshly constructed :class:`~manosube_agent_civilization.projection.
    ProjectionExecutionContext` -- if, and only if, exactly one resolved grant and exactly one
    anchoring declaration exist for each distinct ``projection_kind`` the resolved grants
    themselves name, each grant's own ``subject_ref`` resolves to a real subject record within
    that same root's own Store whose independently recomputed identity/fingerprint matches both
    *subject_ref* and the grant's own claimed ``subject_fingerprint``, and each genuinely
    authorizes ``MATERIALIZE_PROJECTION`` through
    :func:`~manosube_agent_civilization.authority.evaluate_projection_authorization` -- the
    same function a production projection call already trusts.

    Raises :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError` on any
    malformed input or refusal; every :class:`~manosube_agent_civilization.boot.errors.BootError`/
    :class:`~manosube_agent_civilization.store.errors.StoreError`/
    :class:`~manosube_agent_civilization.binding.errors.BindingError`/
    :class:`~manosube_agent_civilization.authority.errors.AuthorityError` any resolved owner
    itself raises propagates unchanged. Never mints, signs, or commits anything, and never
    accepts a caller-supplied subject or grant/declaration body of any kind -- every record
    consumed here was already externally issued, committed, and Store-resolved before this
    call.
    """

    # The type check is the whole control (P15-R1-F4) -- it runs before every other check,
    # including before Boot, so a caller who tried to hand in a bare Store, a look-alike
    # object, or an alternate world's own handle never reaches any resolution at all.
    if not isinstance(trusted_runtime_root, TrustedRuntimeRoot):
        raise RuntimeRequirementError(
            "bootstrap_projection_execution_capability requires a TrustedRuntimeRoot obtained "
            "from provision_trusted_runtime_root, never a bare store or a look-alike object: "
            f"{type(trusted_runtime_root)!r}"
        )
    store = trusted_runtime_root.store
    project_id = trusted_runtime_root.project_id
    project_binding_id = trusted_runtime_root.project_binding_id

    if not github_projection_grant_refs:
        raise RuntimeRequirementError("github_projection_grant_refs must name at least one grant")

    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    human_authority_ref = boot_context.human_authority_ref
    human_authority_signing_key = boot_context.project_binding.get("human_authority_signing_key")
    if not isinstance(human_authority_signing_key, Mapping):
        raise RuntimeRequirementError(
            "the Boot-restored project_binding carries no readable human_authority_signing_key"
        )

    grants = [
        _resolve_grant(store, project_id, ref, context=f"github_projection_grant_refs[{position}]")
        for position, ref in enumerate(github_projection_grant_refs)
    ]
    declarations = [
        _resolve_declaration(
            store, project_id, ref, context=f"github_projection_grant_declaration_refs[{position}]"
        )
        for position, ref in enumerate(github_projection_grant_declaration_refs)
    ]

    # Dynamic kind set (this module's own deliberate divergence from the V3 test fixture's
    # fixed three-kind requirement -- see this module's own docstring): whatever
    # projection_kind values the resolved grants themselves name, each still requiring exactly
    # one grant and exactly one anchoring declaration.
    distinct_projection_kinds: set[str] = set()
    for grant in grants:
        kind = grant.get("projection_kind")
        if not isinstance(kind, str) or not kind:
            raise RuntimeRequirementError(
                f"a resolved grant carries no readable projection_kind: {grant!r}"
            )
        distinct_projection_kinds.add(kind)
    projection_kinds = sorted(distinct_projection_kinds)

    decisions: dict[str, Mapping[str, Any]] = {}
    authorities: dict[str, PreIssuedProjectionAuthority] = {}
    for projection_kind in projection_kinds:
        if projection_kind not in _SUBJECT_KIND_FOR_PROJECTION_KIND:
            raise RuntimeRequirementError(
                f"a resolved grant names an unrecognized projection_kind: {projection_kind!r}"
            )
        matching_grants = [g for g in grants if g.get("projection_kind") == projection_kind]
        if len(matching_grants) != 1:
            raise RuntimeRequirementError(
                f"exactly one grant is required per projection_kind, found "
                f"{len(matching_grants)} for {projection_kind!r}"
            )
        grant = matching_grants[0]

        subject_ref = grant.get("subject_ref")
        target_repository = grant.get("target_repository")
        grant_id = grant.get("github_projection_grant_id")
        if not isinstance(subject_ref, Mapping) or not isinstance(target_repository, Mapping):
            raise RuntimeRequirementError(
                f"grant {grant_id!r} carries no readable subject_ref/target_repository"
            )
        if subject_ref.get("kind") != _SUBJECT_KIND_FOR_PROJECTION_KIND[projection_kind]:
            raise RuntimeRequirementError(
                f"grant {grant_id!r} subject_ref names a kind inconsistent with its own "
                f"projection_kind: {subject_ref.get('kind')!r}"
            )
        if not isinstance(grant_id, str) or not grant_id:
            raise RuntimeRequirementError("grant carries no readable github_projection_grant_id")

        subject_record, real_subject_fingerprint = _resolve_subject(store, project_id, subject_ref)
        if grant.get("subject_fingerprint") != real_subject_fingerprint:
            raise RuntimeRequirementError(
                f"grant {grant_id!r} own subject_fingerprint does not match the real, "
                "recomputed subject fingerprint"
            )

        matching_declarations = [
            d
            for d in declarations
            if isinstance(d.get("grant_ref"), Mapping) and d["grant_ref"].get("id") == grant_id
        ]
        if len(matching_declarations) != 1:
            raise RuntimeRequirementError(
                f"exactly one anchoring declaration is required per grant, found "
                f"{len(matching_declarations)} for grant {grant_id!r}"
            )
        declaration = matching_declarations[0]
        declaration_id = declaration.get("github_projection_grant_declaration_id")
        if not isinstance(declaration_id, str) or not declaration_id:
            raise RuntimeRequirementError("declaration carries no readable identity")

        request = {
            "schema_version": "0.1",
            "project_id": project_id,
            "subject_ref": dict(subject_ref),
            "subject_fingerprint": real_subject_fingerprint,
            "projection_kind": projection_kind,
            "target_repository": dict(target_repository),
            "payload_fingerprint": grant.get("payload_fingerprint"),
            "permitted_action": _PERMITTED_ACTION,
            "human_authority_ref": dict(human_authority_ref),
            "human_authority_signing_key": dict(human_authority_signing_key),
            "grants": [grant],
            "grant_declarations": [declaration],
        }
        decision = evaluate_projection_authorization(request)
        if decision.get("decision") != PROJECTION_AUTHORIZED:
            raise RuntimeRequirementError(
                f"no genuine github_projection_grant authorizes projection_kind={projection_kind!r} "
                f"for project {project_id!r}; decision reason codes: {decision.get('decision_reason_codes')}"
            )

        decisions[projection_kind] = decision
        authorities[projection_kind] = PreIssuedProjectionAuthority(
            projection_kind=projection_kind,
            subject_ref=dict(subject_ref),
            subject_record=subject_record,
            github_projection_grant_ref={"kind": _GRANT_RECORD_KIND, "id": grant_id},
            github_projection_grant_declaration_ref={
                "kind": _DECLARATION_RECORD_KIND,
                "id": declaration_id,
            },
        )

    current_state = boot_context.current_state
    context = ProjectionExecutionContext(
        store=store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        github_authority_ref=human_authority_ref,
        authorities=authorities,
        state_revision=current_state["state_revision"],
        semantic_fingerprint=current_state["semantic_fingerprint"],
        decisions=decisions,
    )
    return ProjectionExecutionCapability(context)


__all__ = [
    "TrustedRuntimeRoot",
    "bootstrap_projection_execution_capability",
    "provision_trusted_runtime_root",
]
