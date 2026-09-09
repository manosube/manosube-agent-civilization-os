"""The shipped Phase 14 projection execution interface (Structural Review Round 13, Issue #62,
P14-R13-F1/F2, ``ADOPT_P14_R13_SHIPPED_BOUND_PROJECTION_EXECUTION_CAPABILITY``).

Round 12 (P14-R12-F1) drew the Phase 14/Phase 15 boundary at a *formal* execution interface --
one that consumes an already-resolved, opaque execution context and carries it through to
:func:`~manosube_agent_civilization.projection.route.project_to_github` -- but left that
interface itself, and the opaque context type it consumes, living only in this repository's own
V3 test-harness fixture layer (never shipped -- proved by static conformance). A "formal,
source-edit-free interface" that a real deployment could call unchanged, once Phase 15 exists,
cannot itself live there: production code that will one day call it would have to import a test
module to do so. Round 13 corrects that: :class:`ProjectionExecutionContext`, :class:`
PreIssuedProjectionAuthority`, :func:`execution_context_still_current`, and
:class:`ProjectionExecutionCapability` now live in this shipped package, importable from the
installed Kernel wheel without importing that fixture layer (or any other test module) at all.
Resolving *how* a genuine :class:`ProjectionExecutionContext` gets built -- reading V3 target
configuration, resolving untrusted grant/declaration references, simulating a real deployment's
own runtime bootstrap -- remains exactly what it always was, this repository's own test-only
concern: this module accepts a :class:`ProjectionExecutionContext` as an opaque, already-resolved
value. It never builds, selects, or opens a Store, a Project, a Binding, a grant, a declaration,
or a subject of its own -- that provisioning is Phase 15's own explicitly deferred
responsibility.

Round 12's own execution entry point was a plain, stateless function accepting *context* fresh
on every call -- adequate to prove the interface itself closed, but structurally insufficient as
a *bound* capability: nothing prevented a caller from passing a *different* context object on
each call, so "this run is bound to one trusted context" was a discipline every caller had to
maintain by hand, never something the interface itself enforced. Round 13 (P14-R13-F2) closes
that: :class:`ProjectionExecutionCapability` is constructed exactly once from one verified
:class:`ProjectionExecutionContext`; its own adapter-reaching method,
:meth:`ProjectionExecutionCapability.execute`, accepts no ``context``, ``store``, ``project_id``,
``project_binding_id``, subject body, grant/declaration body, or any other replacement Authority
material of any kind -- it is not a parameter its signature carries at all, provably by
introspection, never merely refused at runtime. Every call this capability ever makes threads
only the exact context bound at construction; after a successful projection, it updates only its
own internally held freshness snapshot (the Store's own ``state_revision``/
``semantic_fingerprint``, re-observed immediately after that call's own commit) so a legitimate
run of several sequential calls survives its own prior commits, while any *external* Store
mutation -- a substitution, a revocation, an unrelated concurrent write -- is still detected and
refused, fail-closed, before the controlled adapter is ever reached again.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from manosube_agent_civilization.binding.errors import BindingError
from manosube_agent_civilization.boot import BootError, boot_project
from manosube_agent_civilization.store.errors import StoreError

from .errors import ProjectionRequirementError
from .route import project_to_github

#: Every exception :func:`~manosube_agent_civilization.boot.boot_project` may propagate for a
#: Store/Binding it cannot restore -- Boot's, Store's, and Binding's own errors, forwarded
#: unchanged, never swallowed and never re-interpreted here as anything but refusal.
_BOOT_FAILURE_ERRORS: tuple[type[Exception], ...] = (BootError, StoreError, BindingError)


@dataclass(frozen=True, slots=True)
class PreIssuedProjectionAuthority:
    """One pre-issued, already-resolved grant/declaration pair for exactly one projection kind,
    bound to the real subject the trusted context's own caller already resolved -- never
    minted, signed, or committed by this module or by the capability that consumes it.
    ``subject_ref``/``subject_record`` are the real subject's own resolved identity and body;
    :meth:`ProjectionExecutionCapability.execute` threads both straight into
    ``project_to_github``, so that route never needs, and this interface never offers, a
    caller-supplied subject body or a separate subject mapping of any kind."""

    projection_kind: str
    subject_ref: Mapping[str, str]
    subject_record: Mapping[str, Any]
    github_projection_grant_ref: Mapping[str, str]
    github_projection_grant_declaration_ref: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class ProjectionExecutionContext:
    """One resolved, verified authority context an authorized projection run threads, opaque
    and unchanged, into :class:`ProjectionExecutionCapability` -- never a detached boolean gate,
    and never itself capable of minting the subject-specific authority it carries or of
    accepting a caller-supplied subject body. Every field here was independently resolved and
    reverified by this context's own caller (this repository's own trusted bootstrap fixture
    today; a real deployment's own runtime bootstrap, once Phase 15 exists) *before* this
    context was ever constructed -- nothing here is ever accepted as a caller-supplied body by
    anything in this module. ``store`` is the exact Store object/handle that caller injected --
    never one this module, or :class:`ProjectionExecutionCapability`, opened or selected itself.
    ``authorities`` carries, for each projection kind this context authorizes, the exact
    pre-issued subject/grant/declaration reference (and the resolved subject body itself) the
    matching ``project_to_github`` call must use -- and no other. ``decisions`` preserves the
    exact Authority Decision evaluated for each kind."""

    store: Any
    project_id: str
    project_binding_id: str
    github_authority_ref: Mapping[str, Any]
    authorities: Mapping[str, PreIssuedProjectionAuthority]
    state_revision: int
    semantic_fingerprint: Mapping[str, Any]
    decisions: Mapping[str, Mapping[str, Any]]


def execution_context_still_current(context: ProjectionExecutionContext | None) -> bool:
    """Re-Boot the identical project/binding *context* already verified, within the identical
    injected Store *context* itself carries, and require the Store's own
    ``state_revision``/``semantic_fingerprint`` to be byte-identical to what *context* itself
    already records -- refusing on any Store mutation since *context* was last observed as
    current, whether a genuine external substitution/revocation or an unrelated concurrent
    write. Intended to be called immediately before every adapter-reaching call, not merely
    once. Returns ``False`` for ``context=None`` and never raises."""

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


class ProjectionExecutionCapability:
    """The shipped, bound-once Phase 14 projection execution capability (Structural Review
    Round 13, P14-R13-F2) -- the sole boundary through which any caller, present or future, may
    thread an already-resolved :class:`ProjectionExecutionContext` into ``project_to_github``
    and, through it, the controlled adapter.

    Constructed exactly once from *context*, an opaque, already-verified, currently-fresh
    :class:`ProjectionExecutionContext` -- this class never builds, selects, or opens one of its
    own, and raises :class:`~manosube_agent_civilization.projection.errors.
    ProjectionRequirementError` at construction for ``context=None`` or a *context* that is
    already stale. Every later call this capability makes uses only the exact *context* bound
    here; there is no public method, property, or parameter anywhere on this class through which
    a caller could ever substitute a different Store, Project, Binding, subject, grant,
    declaration, or Authority material for the one bound at construction.

    :meth:`execute` is this capability's own single adapter-reaching method. Its signature
    accepts no ``context``, ``store``, ``project_id``, ``project_binding_id``, subject body,
    grant/declaration body, or Authority assembler of any kind -- provably by
    :func:`inspect.signature`, not merely refused if supplied. It revalidates the bound
    context's own freshness (:func:`execution_context_still_current`) immediately before every
    call reaches ``project_to_github``, so any Store mutation, revision, fingerprint, Binding,
    subject, grant, declaration, decision, target, payload, or action substitution since
    construction (or since this capability's own last successful call) refuses here, before the
    adapter is ever reached again.

    On a successful call, this capability replaces only its own internally held freshness
    snapshot (``state_revision``/``semantic_fingerprint``, re-observed from the same Store
    immediately after that call's own commit) -- never the trust root itself (``store``,
    ``project_id``, ``project_binding_id``, ``authorities``, ``github_authority_ref``), and never
    through any parameter or attribute a caller can reach. A legitimate run of several
    sequential calls therefore survives its own prior commits (this call's own commit
    necessarily advances the Store's ``state_revision``, which a naive freshness check could
    otherwise mistake for an external mutation), while an external Store mutation between two
    calls is still detected and refused, fail-closed, before the controlled adapter is ever
    reached again.

    This is Phase 14's own owned interface; it does not select, open, or provision the Store,
    Project, or Binding the bound *context* itself names -- that is Phase 15's own explicitly
    deferred responsibility (Structural Review Round 12, P14-R12-F1; Round 13,
    P14-R13-F1/F2). Phase 14 proves this exact class complete and correct against a genuinely
    resolved context this repository's own trusted bootstrap fixture supplies; a real
    deployment's own runtime bootstrap, once Phase 15 exists, constructs this exact class
    unchanged -- no further source edit to this module is required for that later activation."""

    __slots__ = ("_context",)

    def __init__(self, context: ProjectionExecutionContext | None) -> None:
        if context is None or not execution_context_still_current(context):
            raise ProjectionRequirementError(
                "cannot construct a projection execution capability from a missing or "
                "already-stale execution context -- refusing before any binding to a trust "
                "root is ever made"
            )
        self._context = context

    def execute(
        self,
        *,
        projection_kind: str,
        target_repository: Mapping[str, Any],
        projection_payload: Mapping[str, Any],
        adapter: Any,
        materialized_at: str,
        attempt_claim_token: str,
    ) -> dict[str, Any]:
        """Project *projection_kind* to GitHub via *adapter*, using only the Store, Project,
        Binding, and pre-issued subject/grant/declaration authority bound to this capability at
        construction. Raises :class:`~manosube_agent_civilization.projection.errors.
        ProjectionRequirementError` for a *projection_kind* with no pre-issued authority in the
        bound context, or for a bound context that is no longer current -- both refused before
        the controlled adapter is ever reached."""

        context = self._context
        if not execution_context_still_current(context):
            raise ProjectionRequirementError(
                "the trusted execution context bound to this capability no longer reflects "
                "the current Store state -- refusing before the controlled adapter is ever "
                "reached"
            )
        if projection_kind not in context.authorities:
            raise ProjectionRequirementError(
                f"projection_kind {projection_kind!r} has no pre-issued authority within the "
                "context bound to this capability -- refusing before the controlled adapter is "
                "ever reached"
            )

        authority = context.authorities[projection_kind]
        result = dict(
            project_to_github(
                context.store,
                project_id=context.project_id,
                project_binding_id=context.project_binding_id,
                subject_ref=authority.subject_ref,
                projection_kind=projection_kind,
                target_repository=target_repository,
                projection_payload=projection_payload,
                github_authority_ref=dict(context.github_authority_ref),
                materialized_at=materialized_at,
                adapter=adapter,
                github_projection_grant_refs=[authority.github_projection_grant_ref],
                github_projection_grant_declaration_refs=[
                    authority.github_projection_grant_declaration_ref
                ],
                attempt_claim_token=attempt_claim_token,
                subject_record=authority.subject_record,
            )
        )
        refreshed_boot_context = boot_project(
            context.store,
            project_id=context.project_id,
            project_binding_id=context.project_binding_id,
        )
        refreshed_state = refreshed_boot_context.current_state
        self._context = replace(
            context,
            state_revision=refreshed_state["state_revision"],
            semantic_fingerprint=refreshed_state["semantic_fingerprint"],
        )
        return result
