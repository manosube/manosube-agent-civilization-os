"""The two public Product Binding entry points (Phase 9, Issue #43; second entry point added
Phase 13, Issue #51, Structural Review Round 5, P13-R5).

``bind_project`` is the one genesis route: it validates a Human-declared Project Binding
(:mod:`.engine`), accepts and schema-validates the real Objective Revision body the Binding
names (Objective's own schema, never restated here), accepts and schema-validates the real
Authority Rule body the Binding's ``authority_policy_ref`` names (Authority's own schema and
:func:`~manosube_agent_civilization.authority.identity.rule_id`, never restated here --
Phase 9 Round 1 P9-R1-F1), produces genesis State through the existing State owner
(:func:`~manosube_agent_civilization.state.fingerprint.fingerprint_project_state`), and
atomically adopts all four -- Objective Revision, Authority Rule, Project Binding, genesis
State -- through the existing, generic
:meth:`~manosube_agent_civilization.store.file_store.FileStateStore.initialize`. It remains
the only route this module ever calls ``.initialize`` from
(``PUBLIC_COMMITTING_ROUTE_COUNT=1`` for genesis, unaffected by the second entry point below).

``declare_human_grant`` (P13-R5) is a second, independent public route, committing a new
post-genesis record kind (``human_grant_declaration``) through the Store's ordinary
``.commit`` -- never ``.initialize`` -- into an already-bound project, arbitrarily long after
genesis. See ``08_VERIFICATION/VERIFICATION_CONTRACT.md`` §12 and ``03_BINDING/
PROJECT_BINDING.md`` §11 for what it exists to prove.

``PRODUCT_BINDING_OWNER_COUNT=1``, ``PUBLIC_PRODUCT_BINDING_ENTRY_POINT_COUNT=2``:
no second State, Store, Lineage, Recovery, Objective, Boundary, or Authority owner is
created anywhere in this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from manosube_agent_civilization.authority.identity import rule_id
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.errors import AlreadyInitializedError

from .admission import admit_genesis_transaction
from .engine import assemble_human_grant_declaration, assemble_project_binding
from .errors import BindingIdentityError, BindingValidationError
from .reference_classification import reject_wrong_kind_reference
from .validation import validate_against_schema_id

#: Objective's own schema -- this module accepts and persists an Objective Revision body,
#: but never mints its identity and never restates its schema (Issue #43 §4.1/§4.9: Product
#: Binding is not a second Objective Revision producer).
OBJECTIVE_REVISION_SCHEMA_ID = "https://schemas.manosube.org/agent-civilization-os/v0.1/objective/objective_revision.schema.json"

#: Authority's own schema -- this module accepts and persists an Authority Rule body, but
#: never mints its identity (:func:`~manosube_agent_civilization.authority.identity.rule_id`
#: is the one reused identity function) and never restates its schema (Issue #43 Phase 9
#: Round 1 P9-R1-F1: Product Binding is not a second Authority Rule producer or a second
#: identity algorithm).
AUTHORITY_RULE_SCHEMA_ID = (
    "https://schemas.manosube.org/agent-civilization-os/v0.1/authority/authority_rule.schema.json"
)

#: The one genesis transaction identity every ``FileStateStore.initialize`` call with
#: ``records`` stages and promotes under -- read-only here, to recover the full committed
#: manifest membership on replay (see :func:`_read_committed_genesis_manifest_keys`).
_GENESIS_TRANSACTION_ID = "TX-GENESIS"


def _canonical_reference_equal(left: Any, right: Any, *, context: str) -> None:
    """Fail closed unless *left* and *right* are the identical ``{"kind": ..., "id": ...}``
    canonical reference -- the exact-equality convention this repository's provenance checks
    already use (P8-R1-F5/P8-R2-F2), never a looser id-only or kind-only comparison."""

    if left != right:
        raise BindingIdentityError(f"{context}: {left!r} != {right!r}")


def _read_committed_genesis_manifest_keys(
    store: Any, project_id: str
) -> set[tuple[str, str]] | None:
    """Read ``TX-GENESIS``'s own already-committed manifest membership through the Store's
    own public, generic, Binding-agnostic
    :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.
    resolve_transaction_manifest` (Phase 9 Structural Review Round 2 P9-R2-F4 -- Round 1's
    own version of this function read the Store's private on-disk recovery-journal layout
    directly, which this module has no business knowing). All *comparison* semantics (what
    counts as identical, additional-record handling, order-independence, duplicate-awareness)
    still stay here in the Binding route layer; the Store method itself carries none.

    Returns ``None`` if the transaction is unresolvable -- ``bind_project`` never reaches
    this function unless a prior genesis for *project_id* already exists (an
    ``AlreadyInitializedError`` was just caught), so ``None`` here means some other,
    non-Binding caller initialized this project without ``records`` at all -- itself a real
    conflict this function's own caller must reject, never silently accept as a no-op.

    Phase 9 Structural Review Round 3 (P9-R3-F1): the returned list is walked member-by-
    member -- proving shape and multiplicity (no ``(kind, id)`` claimed twice) -- *before*
    ever being folded into the returned set, rather than handed straight to ``set(...)``,
    which would silently collapse a tampered manifest's own duplicate claim without ever
    revealing it (the Store's own ``resolve_transaction_manifest`` already fails closed on
    this same tamper independently; this is defense in depth at the layer that actually
    performs the set-normalization, not a substitute for that check).
    """

    manifest = store.resolve_transaction_manifest(project_id, _GENESIS_TRANSACTION_ID)
    if manifest is None:
        return None
    keys: set[tuple[str, str]] = set()
    for kind, record_id in manifest:
        key = (kind, record_id)
        if key in keys:
            raise BindingIdentityError(
                f"committed genesis manifest names {kind}/{record_id} more than once"
            )
        keys.add(key)
    return keys


def bind_project(
    store: Any,
    *,
    project_id: str,
    objective_revision: dict[str, Any],
    boundary: dict[str, Any],
    authority_policy_ref: dict[str, Any],
    authority_rule: dict[str, Any],
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
    producer's restatement of it). *authority_rule* is the real Authority Rule body
    *authority_policy_ref* names (schema-owned by Authority, identity-owned by
    :func:`~manosube_agent_civilization.authority.identity.rule_id`, both reused here rather
    than restated -- Issue #43 Phase 9 Round 1 P9-R1-F1). *genesis_state* is a fully
    assembled ``project_state`` dict -- ``project_id``, ``objective_revision_id``,
    ``state_revision`` (must be ``0``), ``previous_state_fingerprint``/``lineage_head_ref``
    (must be ``None``), ``semantic_state``, ``state_metadata``, ``evidence_refs`` --
    everything the existing State owner's real producer (:func:`fingerprint_project_state`)
    needs; this function computes and fills in ``semantic_fingerprint`` itself, the one step
    that function performs, exactly as every other genesis-building caller in this
    repository already does (see ``tests/reflow_helpers.py::store_ready_for_closure``).

    *additional_genesis_records* carries any further immutable ``(kind, id, body)`` records
    *genesis_state* itself references (its own real Kernel Source Snapshot, in particular --
    see ``tests/state_helpers.py::genesis_source_snapshot_records``) and that must therefore
    close to a real, canonical, Store-adopted predecessor from the moment genesis exists, the
    identical ``GENESIS_DANGLING_CANONICAL_REFERENCE_ALLOWED=false`` invariant R10-F1 already
    established for Reflow's own genesis path -- staged into the same one atomic transaction
    as the Objective Revision, Authority Rule and Project Binding records below, never a
    second genesis-record surface.

    Cross-checks (Issue #43 §4/§7, Phase 9 Round 1 P9-R1-F1/P9-R1-F2), all before any write:

    - *project_id*/*objective_revision*'s own id against *genesis_state*'s own matching
      fields ("project-id mismatch across Binding and genesis State", "wrong Objective
      Revision identity");
    - *objective_revision*'s own ``project_id`` field against the declared *project_id*
      (P9-R1-F2 -- previously unchecked: a Binding could declare one project while carrying
      an Objective Revision that names a different one);
    - *authority_rule*'s own recomputed :func:`rule_id` against *authority_policy_ref*'s own
      ``id``, its own ``project_id`` against the declared *project_id*, and its own
      ``declared_by`` against *human_authority_ref* (P9-R1-F1);
    - a three-way Human Authority cross-match: *human_authority_ref* ==
      *objective_revision*'s own ``human_authority_ref`` == *authority_rule*'s own
      ``declared_by``, every one a canonical-reference exact match (P9-R1-F2). Human
      Authority itself is never a Store record here (``HUMAN_AUTHORITY_STORE_RECORD_
      REQUIRED=false``, SHUKOU's own adopted, non-negotiable-without-escalation position) --
      only cross-consistency between its three declared appearances is enforced.

    An identical replay (byte-identical Objective Revision, Authority Rule, Project Binding,
    genesis State, and every ``additional_genesis_records`` member) is accepted as a no-op,
    returning the already-committed result; any other replay against an already-initialized
    *project_id* is rejected before anything new is written (Issue #43's required "stale or
    already-initialized Store"/"conflicting replay" proofs, Phase 9 Round 1 P9-R1-F4: the
    comparison now covers the FULL atomic manifest -- every member the genesis transaction
    ever adopted, not merely three named records -- order-independent, duplicate-aware, and
    rejecting a missing, extra, or wrong-kind member exactly as it rejects a same-kind/id
    body divergence) -- the Store's own :meth:`~manosube_agent_civilization.store.
    file_store.FileStateStore.initialize` treats genesis as strictly one-shot, so this
    distinction is drawn here, over its own existing, generic read surfaces
    (:meth:`load_current`/:meth:`resolve_record`) plus a direct, read-only reproduction of
    its own recovery journal's ``manifest.json`` (never a second persistence mechanism, and
    never any Binding-specific comparison logic added to the Store itself).
    """

    objective_revision_id = objective_revision.get("objective_revision_id")
    if not isinstance(objective_revision_id, str) or not objective_revision_id:
        raise BindingValidationError("objective_revision has no objective_revision_id")
    validate_against_schema_id(
        objective_revision, OBJECTIVE_REVISION_SCHEMA_ID, schema_root=schema_root
    )

    reject_wrong_kind_reference("authority_policy_ref", authority_policy_ref)
    validate_against_schema_id(authority_rule, AUTHORITY_RULE_SCHEMA_ID, schema_root=schema_root)
    recomputed_rule_id = rule_id(authority_rule)
    if authority_policy_ref.get("id") != recomputed_rule_id:
        raise BindingIdentityError(
            "authority_policy_ref does not reproduce from the declared authority_rule body: "
            f"{authority_policy_ref.get('id')!r} != {recomputed_rule_id!r}"
        )
    if authority_rule.get("authority_rule_id") != recomputed_rule_id:
        raise BindingIdentityError(
            "authority_rule's own authority_rule_id does not reproduce from its own body: "
            f"{authority_rule.get('authority_rule_id')!r} != {recomputed_rule_id!r}"
        )
    if authority_rule.get("project_id") != project_id:
        raise BindingIdentityError(
            "authority_rule's own project_id does not match the declared Project Binding "
            f"project_id: {authority_rule.get('project_id')!r} != {project_id!r}"
        )
    _canonical_reference_equal(
        authority_rule.get("declared_by"),
        human_authority_ref,
        context="authority_rule.declared_by vs human_authority_ref",
    )

    if objective_revision.get("project_id") != project_id:
        raise BindingIdentityError(
            "objective_revision's own project_id does not match the declared Project "
            f"Binding project_id: {objective_revision.get('project_id')!r} != {project_id!r}"
        )
    _canonical_reference_equal(
        objective_revision.get("human_authority_ref"),
        human_authority_ref,
        context="objective_revision.human_authority_ref vs human_authority_ref",
    )
    # Phase 9 Structural Review Round 3, P9-R3-F4: kind-correctness alone
    # (`reference_classification`'s own closed-kind check) never proved *identity*
    # equality -- a caller could declare a different, but still correctly-kinded,
    # human_authority id here and nothing rejected it. The four-way canonical exact
    # match: project_binding.human_authority_ref == objective_revision.owner_authority_ref
    # == objective_revision.human_authority_ref == authority_rule.declared_by.
    _canonical_reference_equal(
        objective_revision.get("owner_authority_ref"),
        human_authority_ref,
        context="objective_revision.owner_authority_ref vs human_authority_ref",
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
        ("authority_rule", recomputed_rule_id, authority_rule),
        ("project_binding", project_binding["project_binding_id"], project_binding),
        *(additional_genesis_records or []),
    ]

    # The one shared pre-commit admission (Phase 9 Structural Review Round 2 P9-R2-F1/F2/
    # F3/F5): secret-value scanning and typed reference-edge closure over the WHOLE
    # candidate genesis manifest -- every body above, not merely the Project Binding record
    # `assemble_project_binding` already scanned on its own. Runs before `store.initialize`
    # is ever called, so a rejection here never advances Store visibility.
    admit_genesis_transaction(
        project_id=project_id,
        objective_revision=objective_revision,
        authority_rule=authority_rule,
        project_binding=project_binding,
        genesis_state=genesis_state,
        additional_genesis_records=additional_genesis_records or [],
    )

    try:
        committed_state = store.initialize(project_id, genesis_state, records=records, fault=fault)
    except AlreadyInitializedError as already_initialized:
        existing_current = store.load_current(project_id)
        if existing_current != genesis_state:
            raise

        # P9-R3-F1: admit_genesis_transaction (above) already rejects any duplicate
        # (kind, id) in *records* -- identical or conflicting -- before this point is ever
        # reached, so no duplicate should survive to here. This walk still builds the
        # expected-body map explicitly (never `dict(...)`-collapsing silently) and re-raises
        # the identical failure defensively should that invariant ever be violated.
        expected_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for kind, record_id, body in records:
            key = (kind, record_id)
            if key in expected_by_key:
                raise BindingValidationError(
                    f"duplicate genesis manifest member supplied twice in this one replay "
                    f"attempt (even if identical): {kind}/{record_id}"
                ) from already_initialized
            expected_by_key[key] = body

        existing_keys = _read_committed_genesis_manifest_keys(store, project_id)
        if existing_keys is None or set(expected_by_key.keys()) != existing_keys:
            raise

        for (kind, record_id), body in expected_by_key.items():
            if store.resolve_record(project_id, kind, record_id) != body:
                raise

        return {
            "project_binding": project_binding,
            "project_binding_id": project_binding["project_binding_id"],
            "objective_revision": objective_revision,
            "authority_rule": authority_rule,
            "committed_state": existing_current,
        }

    return {
        "project_binding": project_binding,
        "project_binding_id": project_binding["project_binding_id"],
        "objective_revision": objective_revision,
        "authority_rule": authority_rule,
        "committed_state": committed_state,
    }


def declare_human_grant(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    grant_ref: dict[str, Any],
    status: str,
    declared_at: str,
    schema_root: Path | None = None,
    fault: Any | None = None,
) -> dict[str, Any]:
    """Declare and atomically adopt one Human Grant Declaration (Structural Review Round 5,
    Issue #51, P13-R5) -- the canonical, read-only-reverifiable anchor SHUKOU's own adoption
    (``ADOPT_P13_R5_CANONICAL_HUMAN_GRANT_DECLARATION_ANCHOR``) requires before a
    ``verifier_selection_grant`` may ever reach ``VERIFIER_SELECTION_SELECTED``: proof that a
    Human -- not merely a caller who wrote a self-consistent record -- declared *this exact*
    grant, independent of that grant's own self-asserted ``granted_by`` field.

    This is the *second* public Product Binding entry point (:func:`bind_project` is the
    first, and remains the only route ever calling
    :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.initialize` --
    ``PUBLIC_COMMITTING_ROUTE_COUNT`` for genesis is unaffected). Unlike genesis, an already-
    bound project's declaration is adopted through the Store's ordinary, generic
    :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.commit` -- a real,
    minimal State transition (the identical "advance the revision to add records" shape every
    other post-genesis record-adding caller in this repository already uses) that changes no
    semantic State content, only the lineage head and the one new record.

    The declaring Human identity is never a caller-supplied argument here at all -- unlike a
    ``verifier_selection_grant``'s own caller-asserted ``granted_by`` field, this function
    independently resolves the real, already-committed ``project_binding`` (fail closed if
    unresolvable) and reads its own ``human_authority_ref`` directly; a caller cannot declare
    a grant on behalf of a Human identity other than the one this project is genuinely bound
    to. Likewise, *grant_ref* is resolved against the real, already-committed
    ``verifier_selection_grant`` (fail closed if unresolvable, or if *grant_ref* does not
    itself name that kind) -- this function never accepts grant content, only a reference,
    the identical caller-asserted-content-is-not-provenance discipline Structural Review
    Round 4 (P13-R4) already established for the grant's own resolution in
    ``independent_verification/route.py``.

    Because :func:`~manosube_agent_civilization.binding.identity.human_grant_declaration_id`
    binds ``grant_ref`` -- itself a content address over the grant's own project/requirement/
    selection/verifier/boundary/status -- this one declaration, once resolved, anchors every
    one of those fields completely; no second, redundant copy of them is ever declared here.
    """

    real_project_binding = store.resolve_record(project_id, "project_binding", project_binding_id)
    if real_project_binding is None:
        raise BindingValidationError(
            f"project_binding does not resolve for project {project_id!r}: {project_binding_id!r}"
        )
    if grant_ref.get("kind") != "verifier_selection_grant":
        raise BindingValidationError(
            f"grant_ref does not name a verifier_selection_grant: {grant_ref.get('kind')!r}"
        )
    grant_id = grant_ref.get("id")
    if not isinstance(grant_id, str) or not grant_id:
        raise BindingValidationError(f"grant_ref carries no readable id: {grant_ref!r}")
    real_grant = store.resolve_record(project_id, "verifier_selection_grant", grant_id)
    if real_grant is None:
        raise BindingValidationError(
            f"verifier_selection_grant does not resolve for project {project_id!r}: {grant_id!r}"
        )

    declaration = assemble_human_grant_declaration(
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref={"kind": "verifier_selection_grant", "id": grant_id},
        declared_by=real_project_binding["human_authority_ref"],
        status=status,
        declared_at=declared_at,
        schema_root=schema_root,
    )
    declaration_id = declaration["human_grant_declaration_id"]

    current_state = store.load_current(project_id)
    transaction_id = f"TX-GRANT-DECLARATION-{declaration_id}"
    next_state = dict(current_state)
    next_state["state_revision"] = current_state["state_revision"] + 1
    next_state["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
    next_state["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
    next_state["semantic_fingerprint"] = fingerprint_project_state(
        next_state, schema_root=schema_root
    ).as_dict()
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
        "committed_at": declared_at,
    }

    committed_state = store.commit(
        project_id,
        current_state["state_revision"],
        current_state["semantic_fingerprint"],
        next_state,
        transition,
        records=[("human_grant_declaration", declaration_id, declaration)],
        fault=fault,
    )

    return {
        "human_grant_declaration": declaration,
        "human_grant_declaration_id": declaration_id,
        "committed_state": committed_state,
    }
