"""The one shared pre-commit admission for Product Binding (Phase 9 Structural Review
Round 2, P9-R2-F1/F2/F3/F5).

``admit_genesis_transaction`` is the single place every body a genesis
:meth:`~manosube_agent_civilization.store.file_store.FileStateStore.initialize` call is
about to stage -- Objective Revision, Authority Rule, Project Binding, genesis State, and
every ``additional_genesis_records`` member -- is checked before any Store write:

1. secret-value and moving-reference scanning over the **whole** candidate manifest
   (P9-R2-F1 -- Round 1 only scanned the Project Binding record itself);
2. typed reference-edge classification and closure over the **whole** candidate manifest
   (P9-R2-F2/F3 -- Round 1 only classified Project Binding's own three top-level fields);
3. duplicate ``(kind, id)`` detection across the candidate manifest, distinguishing an
   identical duplicate (silently fine) from a conflicting one (same key, different body --
   refused).

:func:`bind_project` is the one caller; a real AST call-graph test
(``tests/contract/binding/test_project_binding_schema_conformance.py``) proves every public
route reaching ``store.initialize`` also reaches this one function
(``CANONICAL_BINDING_PRECOMMIT_ADMISSION_OWNER_COUNT=1``).
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.difference.canonical import reject_secret_material, walk_references
from manosube_agent_civilization.reflow import reference_registry as reflow_reference_registry
from manosube_agent_civilization.reflow.errors import ReflowValidationError

from .errors import BindingIdentityError, BindingValidationError
from .reference_classification import TypedReferenceEdge, reference_edges


def admit_genesis_transaction(
    *,
    project_id: str,
    objective_revision: dict[str, Any],
    authority_rule: dict[str, Any],
    project_binding: dict[str, Any],
    genesis_state: dict[str, Any],
    additional_genesis_records: list[tuple[str, str, dict[str, Any]]],
) -> None:
    """Admit one candidate genesis transaction, or raise before anything is persisted.

    *genesis_state* is scanned and reference-checked here as ``project_state`` even though
    it is never itself resolved through :meth:`~manosube_agent_civilization.store.
    file_store.FileStateStore.resolve_record` (State has its own dedicated
    ``load_current``/``resolve_transaction`` surface, per Reflow's own registry inventory) --
    this function only checks *its own declared references*, never claims to be State's
    persistence or resolution owner.
    """

    candidate: list[tuple[str, str, dict[str, Any]]] = [
        ("objective_revision", objective_revision["objective_revision_id"], objective_revision),
        ("authority_rule", authority_rule["authority_rule_id"], authority_rule),
        ("project_binding", project_binding["project_binding_id"], project_binding),
        *additional_genesis_records,
    ]

    # 1. Duplicate (kind, id) detection across the whole candidate manifest -- an identical
    #    duplicate body is silently fine (the same member named twice changes nothing); a
    #    conflicting duplicate (same key, different body) is refused before anything else
    #    runs (P9-R2-F4's own "duplicate-aware, not merely order-independent" requirement,
    #    checked here too since a caller could supply a self-conflicting candidate on the
    #    very first call, not only on replay).
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for kind, record_id, body in candidate:
        key = (kind, record_id)
        if key in seen and seen[key] != body:
            raise BindingValidationError(
                f"conflicting candidate genesis manifest member: {kind}/{record_id}"
            )
        seen[key] = body

    # 2. Secret-value and moving-reference scan over the WHOLE candidate manifest and genesis
    #    State (P9-R2-F1) -- Round 1 scanned only the Project Binding record itself
    #    (`assemble_project_binding`'s own internal scan, still the correct place for that
    #    record's own fields). Diagnostic context names only the record kind/id, never the
    #    scanned value itself (`reject_secret_material`'s own error message already omits the
    #    secret value; only the offending key name or a generic "secret-bearing value at"
    #    context reaches the exception).
    for kind, record_id, body in candidate:
        reject_secret_material(body, f"{kind}/{record_id}")
        walk_references(body, f"{kind}/{record_id}")
    reject_secret_material(genesis_state, "project_state/genesis")
    walk_references(genesis_state, "project_state/genesis")

    # 3. Typed reference-edge classification and closure over the whole candidate manifest
    #    (P9-R2-F2/F3). Every accepted record kind's own reference fields are checked for
    #    kind correctness before any Store lookup, and every Store-owned edge must resolve
    #    against this same candidate manifest -- there is nothing else to resolve against,
    #    since genesis means no record for this project_id exists in the Store yet.
    candidate_keys = set(seen.keys())
    edges: list[TypedReferenceEdge] = []
    edges.extend(reference_edges("objective_revision", objective_revision))
    edges.extend(reference_edges("authority_rule", authority_rule))
    edges.extend(reference_edges("project_binding", project_binding))
    edges.extend(reference_edges("project_state", genesis_state))
    for kind, record_id, body in additional_genesis_records:
        if kind in reflow_reference_registry.STORE_OWNED_REFERENCE_KINDS:
            try:
                edges.extend(reflow_reference_registry.reference_edges(kind, body))
            except ReflowValidationError as exc:
                raise BindingValidationError(str(exc)) from exc

    unresolved = [
        edge for edge in edges if (edge.target_kind, edge.target_id) not in candidate_keys
    ]
    if unresolved:
        first = unresolved[0]
        raise BindingIdentityError(
            f"{first.source_kind}.{first.field_path}: reference to "
            f"{first.target_kind}/{first.target_id} does not resolve against this genesis "
            "transaction's own candidate manifest -- GENESIS_DANGLING_CANONICAL_REFERENCE_"
            "ALLOWED=false"
        )
