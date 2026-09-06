"""The one public Boot entry point (Phase 10, Issue #45).

``BOOT_OWNER_COUNT=1``, ``PUBLIC_BOOT_ENTRY_POINT_COUNT=1``.

``boot_project`` restores one already-bound Project from an existing, already-initialized
Store: it resolves and reverifies the Project Binding through the existing Phase 9 identity
owner (:func:`~manosube_agent_civilization.binding.verify_project_binding_identity`), resolves
its Store-owned references through the existing Phase 9 reference-resolution owner
(:func:`~manosube_agent_civilization.binding.resolve_binding_references`), reverifies the
Authority Rule through the existing Authority identity owner
(:func:`~manosube_agent_civilization.authority.identity.rule_id`), reconstructs current State
through the existing append-only lineage owner
(:meth:`~manosube_agent_civilization.store.file_store.FileStateStore.reconstruct`), and
checks the cross-record project/Objective/Authority/reference invariants Issue #45 assigns to
this route itself (``BOOT_CONTRACT.md`` §6). It creates no second State, Store, Binding,
Objective, Authority, or reference-resolution owner, and never calls ``store.initialize``,
``store.commit``, or ``store.recover`` -- Boot is restoration, never initialization, adoption,
or repair (frozen semantic decisions 1, 3, 8). A Store that indicates corruption, an
interrupted transaction, or an uninitialized project propagates its own typed Store error
unchanged; this route neither swallows nor "repairs" it.

Phase 10 Structural Review Round 1 correction (P10-R1-F2): ``FileStateStore.load_current``
materializes a missing ``current.json`` view via a real write when the committed lineage is
otherwise sound, which is not a read-only operation -- a successful Boot must never mutate
the Store (frozen semantic decision 8). This route now reconstructs current State exclusively
through :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.reconstruct`,
which replays the committed append-only lineage and returns a value with no Store write of
any kind, materialized-view included.
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.authority.identity import rule_id
from manosube_agent_civilization.binding import (
    reject_wrong_kind_reference,
    resolve_binding_references,
    verify_project_binding_identity,
)

from .context import BootContext
from .errors import BootConsistencyError, BootNotFoundError

#: The one record kind a Product Binding is ever persisted under -- never a Development
#: Binding (pinned in code, never a Store record) and never any other kind.
_PRODUCT_BINDING_RECORD_KIND = "project_binding"


def _require_canonical_identity(name: str, value: Any) -> str:
    """Fail closed unless *value* is a plain, non-empty canonical identity string -- never a
    filesystem path, URL, or directory name (frozen semantic decision 2: Boot is not
    discovery, the caller must supply an explicit canonical identity, never a locator)."""

    if not isinstance(value, str) or not value:
        raise BootNotFoundError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise BootNotFoundError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def _canonical_reference_equal(left: Any, right: Any, *, context: str) -> None:
    """Fail closed unless *left* and *right* are the identical ``{"kind": ..., "id": ...}``
    canonical reference -- the same exact-equality convention Product Binding's own route
    already uses for this identical four-way Human Authority check."""

    if left != right:
        raise BootConsistencyError(f"{context}: {left!r} != {right!r}")


def boot_project(store: Any, *, project_id: str, project_binding_id: str) -> BootContext:
    """Restore one already-bound Project from *store* into one immutable Boot Context.

    See ``04_BOOT/BOOT_CONTRACT.md`` §5 for the full canonical route this function
    implements, step by step.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)

    project_binding = store.resolve_record(
        project_id, _PRODUCT_BINDING_RECORD_KIND, project_binding_id
    )
    if project_binding is None:
        raise BootNotFoundError(
            f"project_binding/{project_binding_id} does not resolve for project {project_id!r}"
        )
    if project_binding.get("project_binding_id") != project_binding_id:
        raise BootConsistencyError(
            "the resolved project_binding record's own declared id does not match the "
            f"requested project_binding_id: {project_binding.get('project_binding_id')!r} "
            f"!= {project_binding_id!r}"
        )
    verify_project_binding_identity(project_binding)
    if project_binding.get("project_id") != project_id:
        raise BootConsistencyError(
            "project_binding.project_id does not match the requested project_id: "
            f"{project_binding.get('project_id')!r} != {project_id!r}"
        )
    for field_name in ("objective_revision_ref", "authority_policy_ref", "human_authority_ref"):
        reject_wrong_kind_reference(field_name, project_binding[field_name])

    resolved = resolve_binding_references(store, project_binding)
    objective_revision = resolved["objective_revision_ref"]
    if objective_revision is None:
        raise BootNotFoundError(
            f"objective_revision/{project_binding['objective_revision_ref']['id']} does not resolve"
        )
    # P10-R1-F3: Objective Revision carries no content-addressed identity of its own, so the
    # Store-owned resolution above only proves *a* body resolved under the requested lookup
    # key -- it never proved that body's own declared objective_revision_id agrees with that
    # key. A Store (or adapter) that returns a self-inconsistent body for a given key must
    # fail closed here, before that declared id is ever trusted as ctx.objective_revision_id.
    objective_revision_ref_id = project_binding["objective_revision_ref"]["id"]
    if objective_revision.get("objective_revision_id") != objective_revision_ref_id:
        raise BootConsistencyError(
            "the resolved objective_revision's own declared objective_revision_id does not "
            "match project_binding.objective_revision_ref.id: "
            f"{objective_revision.get('objective_revision_id')!r} != "
            f"{objective_revision_ref_id!r}"
        )
    authority_rule = resolved["authority_policy_ref"]
    if authority_rule is None:
        raise BootNotFoundError(
            f"authority_rule/{project_binding['authority_policy_ref']['id']} does not resolve"
        )

    recomputed_rule_id = rule_id(authority_rule)
    if authority_rule.get("authority_rule_id") != recomputed_rule_id:
        raise BootConsistencyError(
            "authority_rule's own authority_rule_id does not reproduce from its own body: "
            f"{authority_rule.get('authority_rule_id')!r} != {recomputed_rule_id!r}"
        )
    if project_binding["authority_policy_ref"]["id"] != recomputed_rule_id:
        raise BootConsistencyError(
            "project_binding.authority_policy_ref.id does not equal the resolved "
            f"authority_rule's own recomputed identity: "
            f"{project_binding['authority_policy_ref']['id']!r} != {recomputed_rule_id!r}"
        )
    if authority_rule.get("project_id") != project_id:
        raise BootConsistencyError(
            "authority_rule.project_id does not match the requested project_id: "
            f"{authority_rule.get('project_id')!r} != {project_id!r}"
        )
    if objective_revision.get("project_id") != project_id:
        raise BootConsistencyError(
            "objective_revision.project_id does not match the requested project_id: "
            f"{objective_revision.get('project_id')!r} != {project_id!r}"
        )

    human_authority_ref = project_binding["human_authority_ref"]
    _canonical_reference_equal(
        objective_revision.get("owner_authority_ref"),
        human_authority_ref,
        context="objective_revision.owner_authority_ref vs project_binding.human_authority_ref",
    )
    _canonical_reference_equal(
        objective_revision.get("human_authority_ref"),
        human_authority_ref,
        context="objective_revision.human_authority_ref vs project_binding.human_authority_ref",
    )
    _canonical_reference_equal(
        authority_rule.get("declared_by"),
        human_authority_ref,
        context="authority_rule.declared_by vs project_binding.human_authority_ref",
    )

    # P10-R1-F2: reconstructed exclusively through the existing append-only lineage owner's
    # pure replay (store.reconstruct) -- never a materialized current.json body, a caller-
    # supplied State, a cache, and never store.load_current(), which performs a real write to
    # materialize a missing current.json even when the caller only asked to read. A Store
    # still carrying an interrupted transaction, missing genesis institution, or any other
    # lineage-authority failure propagates its own typed Store error unchanged (frozen
    # semantic decision 8); this route never calls store.recover() to complete it.
    current_state = store.reconstruct(project_id)
    if current_state.get("project_id") != project_id:
        raise BootConsistencyError(
            "reconstructed current State's own project_id does not match the requested "
            f"project_id: {current_state.get('project_id')!r} != {project_id!r}"
        )
    objective_revision_id = project_binding["objective_revision_ref"]["id"]
    if current_state.get("objective_revision_id") != objective_revision_id:
        raise BootConsistencyError(
            "reconstructed current State's own objective_revision_id does not match "
            "project_binding.objective_revision_ref.id: "
            f"{current_state.get('objective_revision_id')!r} != {objective_revision_id!r}"
        )

    return BootContext(
        project_id=project_id,
        project_binding=project_binding,
        project_binding_id=project_binding_id,
        objective_revision=objective_revision,
        objective_revision_id=objective_revision_id,
        authority_rule=authority_rule,
        authority_rule_id=recomputed_rule_id,
        current_state=current_state,
        human_authority_ref=human_authority_ref,
    )
