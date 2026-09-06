"""The one public Product Binding entry point (Phase 9, Issue #43).

``bind_project`` is the sole public route: it validates a Human-declared Project Binding
(:mod:`.engine`), accepts and schema-validates the real Objective Revision body the Binding
names (Objective's own schema, never restated here), produces genesis State through the
existing State owner (:func:`~manosube_agent_civilization.state.fingerprint.
fingerprint_project_state`), and atomically adopts all three -- Objective Revision, Project
Binding, genesis State -- through the existing, generic
:meth:`~manosube_agent_civilization.store.file_store.FileStateStore.initialize`.

``PRODUCT_BINDING_OWNER_COUNT=1``, ``PUBLIC_PRODUCT_BINDING_ENTRY_POINT_COUNT=1``:
no second State, Store, Lineage, Recovery, Objective, Boundary, or Authority owner is
created anywhere in this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.errors import AlreadyInitializedError

from .engine import assemble_project_binding
from .errors import BindingIdentityError, BindingValidationError
from .validation import validate_against_schema_id

#: Objective's own schema -- this module accepts and persists an Objective Revision body,
#: but never mints its identity and never restates its schema (Issue #43 §4.1/§4.9: Product
#: Binding is not a second Objective Revision producer).
OBJECTIVE_REVISION_SCHEMA_ID = "https://schemas.manosube.org/agent-civilization-os/v0.1/objective/objective_revision.schema.json"


def bind_project(
    store: Any,
    *,
    project_id: str,
    objective_revision: dict[str, Any],
    boundary: dict[str, Any],
    authority_policy_ref: dict[str, Any],
    source_registrations: list[dict[str, Any]],
    command_policy: dict[str, Any],
    secret_exclusion_policy: dict[str, Any],
    human_authority_ref: dict[str, Any],
    bound_at: str,
    genesis_state: dict[str, Any],
    additional_genesis_records: list[tuple[str, str, dict[str, Any]]] | None = None,
    schema_root: Path | None = None,
    fault: Any | None = None,
) -> dict[str, Any]:
    """Validate, identify, and atomically adopt one Human-declared Project Binding.

    *objective_revision* is the real, Human-Authority-declared Objective Revision body
    (schema-owned by Objective, validated here against that same schema, never a second
    producer's restatement of it). *genesis_state* is a fully assembled ``project_state``
    dict -- ``project_id``, ``objective_revision_id``, ``state_revision`` (must be ``0``),
    ``previous_state_fingerprint``/``lineage_head_ref`` (must be ``None``), ``semantic_
    state``, ``state_metadata``, ``evidence_refs`` -- everything the existing State owner's
    real producer (:func:`fingerprint_project_state`) needs; this function computes and
    fills in ``semantic_fingerprint`` itself, the one step that function performs, exactly
    as every other genesis-building caller in this repository already does (see
    ``tests/reflow_helpers.py::store_ready_for_closure``).

    *additional_genesis_records* carries any further immutable ``(kind, id, body)`` records
    *genesis_state* itself references (its own real Kernel Source Snapshot, in particular --
    see ``tests/state_helpers.py::genesis_source_snapshot_records``) and that must therefore
    close to a real, canonical, Store-adopted predecessor from the moment genesis exists,
    the identical ``GENESIS_DANGLING_CANONICAL_REFERENCE_ALLOWED=false`` invariant R10-F1
    already established for Reflow's own genesis path -- staged into the same one atomic
    transaction as the Objective Revision and Project Binding records below, never a second
    genesis-record surface.

    Cross-checks *project_id*/*objective_revision*'s own id against *genesis_state*'s own
    matching fields before any write -- Issue #43's required "project-id mismatch across
    Binding and genesis State" and "wrong Objective Revision identity" negative controls.

    An identical replay (byte-identical Objective Revision, Project Binding, and genesis
    State) is accepted as a no-op, returning the already-committed result; any other replay
    against an already-initialized *project_id* is rejected before anything new is written
    (Issue #43's required "stale or already-initialized Store"/"conflicting replay" proofs) --
    the Store's own :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.
    initialize` treats genesis as strictly one-shot, so this distinction is drawn here, over
    its own existing, generic read surfaces (:meth:`load_current`/:meth:`resolve_record`),
    never a second persistence mechanism.
    """

    objective_revision_id = objective_revision.get("objective_revision_id")
    if not isinstance(objective_revision_id, str) or not objective_revision_id:
        raise BindingValidationError("objective_revision has no objective_revision_id")
    validate_against_schema_id(
        objective_revision, OBJECTIVE_REVISION_SCHEMA_ID, schema_root=schema_root
    )

    if genesis_state.get("project_id") != project_id:
        raise BindingIdentityError(
            "genesis State's own project_id does not match the declared Project Binding "
            f"project_id: {genesis_state.get('project_id')!r} != {project_id!r}"
        )
    if genesis_state.get("objective_revision_id") != objective_revision_id:
        raise BindingIdentityError(
            "genesis State's own objective_revision_id does not match the declared "
            f"Objective Revision: {genesis_state.get('objective_revision_id')!r} != "
            f"{objective_revision_id!r}"
        )
    if genesis_state.get("state_revision") != 0:
        raise BindingValidationError("genesis State must be revision 0")
    if genesis_state.get("previous_state_fingerprint") is not None:
        raise BindingValidationError("genesis State must carry no previous_state_fingerprint")
    if genesis_state.get("lineage_head_ref") is not None:
        raise BindingValidationError("genesis State must carry no lineage_head_ref")

    objective_revision_ref = {"kind": "objective_revision", "id": objective_revision_id}

    project_binding = assemble_project_binding(
        project_id=project_id,
        objective_revision_ref=objective_revision_ref,
        boundary=boundary,
        authority_policy_ref=authority_policy_ref,
        source_registrations=source_registrations,
        command_policy=command_policy,
        secret_exclusion_policy=secret_exclusion_policy,
        human_authority_ref=human_authority_ref,
        bound_at=bound_at,
        schema_root=schema_root,
    )

    genesis_state = dict(genesis_state)
    genesis_state["semantic_fingerprint"] = fingerprint_project_state(
        genesis_state, schema_root=schema_root
    ).as_dict()

    records: list[tuple[str, str, dict[str, Any]]] = [
        ("objective_revision", objective_revision_id, objective_revision),
        ("project_binding", project_binding["project_binding_id"], project_binding),
        *(additional_genesis_records or []),
    ]

    try:
        committed_state = store.initialize(project_id, genesis_state, records=records, fault=fault)
    except AlreadyInitializedError:
        existing_current = store.load_current(project_id)
        existing_binding = store.resolve_record(
            project_id, "project_binding", project_binding["project_binding_id"]
        )
        existing_objective_revision = store.resolve_record(
            project_id, "objective_revision", objective_revision_id
        )
        if (
            existing_current == genesis_state
            and existing_binding == project_binding
            and existing_objective_revision == objective_revision
        ):
            return {
                "project_binding": project_binding,
                "project_binding_id": project_binding["project_binding_id"],
                "objective_revision": objective_revision,
                "committed_state": existing_current,
            }
        raise

    return {
        "project_binding": project_binding,
        "project_binding_id": project_binding["project_binding_id"],
        "objective_revision": objective_revision,
        "committed_state": committed_state,
    }
