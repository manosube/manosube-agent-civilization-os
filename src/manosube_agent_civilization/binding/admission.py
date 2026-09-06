"""The one shared pre-commit admission for Product Binding (Phase 9 Structural Review
Round 2, P9-R2-F1/F2/F3/F5, extended Round 3, P9-R3-F1/F3).

``admit_genesis_transaction`` is the single place every body a genesis
:meth:`~manosube_agent_civilization.store.file_store.FileStateStore.initialize` call is
about to stage -- Objective Revision, Authority Rule, Project Binding, genesis State, and
every ``additional_genesis_records`` member -- is checked before any Store write:

0. closed-kind allowlist + schema/identity reverification for every ``additional_genesis_
   records`` member (P9-R3-F3 -- an unrecognized kind, or a recognized kind whose body does
   not actually recompute its own declared identity, was previously trusted verbatim and
   persisted with no check of any kind);
1. duplicate ``(kind, id)`` detection across the candidate manifest -- the SECOND appearance
   of any key is refused, whether its body is identical to or differs from the first
   (P9-R3-F1: Round 2 treated an identical duplicate as a silently-fine no-op);
2. secret-value and moving-reference scanning over the **whole** candidate manifest
   (P9-R2-F1 -- Round 1 only scanned the Project Binding record itself);
3. typed reference-edge classification and closure over the **whole** candidate manifest,
   scoped to this same candidate manifest only, never an existing Store record (P9-R2-F2/F3,
   scope ratified Round 3 P9-R3-F5 -- Round 1 only classified Project Binding's own three
   top-level fields).

:func:`bind_project` is the one caller; a real AST call-graph test
(``tests/contract/binding/test_project_binding_schema_conformance.py``) proves every public
route reaching ``store.initialize`` also reaches this one function
(``CANONICAL_BINDING_PRECOMMIT_ADMISSION_OWNER_COUNT=1``).
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.difference.canonical import reject_secret_material, walk_references
from manosube_agent_civilization.observation.schemas import (
    OBSERVATION_SCHEMA_BASE,
    validators as _observation_validators,
)
from manosube_agent_civilization.observation.source_snapshot import source_snapshot_identity
from manosube_agent_civilization.reflow import reference_registry as reflow_reference_registry
from manosube_agent_civilization.reflow.errors import ReflowValidationError

from .errors import BindingIdentityError, BindingValidationError
from .reference_classification import TypedReferenceEdge, reference_edges


def _verify_source_snapshot_body(record_id: str, body: dict[str, Any]) -> None:
    """Schema-validate and identity-reverify one ``additional_genesis_records`` member
    declared as ``source_snapshot`` -- reusing Observation's own real schema registry and
    real content-addressed identity function
    (:func:`~manosube_agent_civilization.observation.source_snapshot.source_snapshot_identity`),
    never a second, Binding-invented identity algorithm for this kind (P9-R3-F3)."""

    validator = _observation_validators()[OBSERVATION_SCHEMA_BASE + "source_snapshot.schema.json"]
    errors = list(validator.iter_errors(body))
    if errors:
        raise BindingValidationError(
            f"additional genesis record source_snapshot/{record_id} is schema-invalid: "
            f"{errors[0].message}"
        )
    recomputed = source_snapshot_identity(body)
    if body.get("source_snapshot_id") != recomputed:
        raise BindingIdentityError(
            f"additional genesis record source_snapshot/{record_id}: the body's own "
            f"source_snapshot_id does not recompute from its own content: "
            f"{body.get('source_snapshot_id')!r} != {recomputed!r}"
        )
    if record_id != recomputed:
        raise BindingIdentityError(
            f"additional genesis record source_snapshot/{record_id}: the supplied record_id "
            f"does not match the body's own recomputed identity: {record_id!r} != "
            f"{recomputed!r}"
        )


#: Closed allowlist of kinds ``additional_genesis_records`` may carry
#: (``ADDITIONAL_GENESIS_RECORD_KIND_SET=CLOSED``, P9-R3-F3). Every entry's own verifier
#: reuses that kind's real, existing schema owner and real, existing identity function --
#: never a second identity algorithm invented here. ``source_snapshot`` is the only kind any
#: real Phase 9 genesis fixture or existing State contract actually requires (genesis
#: State's own ``state_metadata.source_snapshot_refs`` is the sole reference genesis closure
#: needs an additional record for -- confirmed against ``tests/state_helpers.py::
#: genesis_source_snapshot_records``, the one real producer of this list every Product
#: Binding fixture in this repository uses); a kind outside this set is refused outright,
#: before it can ever reach secret scanning, reference classification, or Store persistence.
ADDITIONAL_GENESIS_RECORD_KIND_VERIFIERS: dict[str, Any] = {
    "source_snapshot": _verify_source_snapshot_body,
}


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

    # 0. Closed additional-genesis-record kind allowlist + schema/identity reverification
    #    (P9-R3-F3). An unrecognized kind is refused outright -- CALLER_SUPPLIED_BODY_
    #    TRUSTED_VERBATIM=false -- before it can ever reach duplicate detection, secret
    #    scanning, reference classification, or Store persistence. A recognized kind's body
    #    is schema-validated and its own real, content-addressed identity recomputed through
    #    that kind's real, existing owner, then cross-checked against both the caller-
    #    supplied tuple record_id and the body's own declared id field.
    for kind, record_id, body in additional_genesis_records:
        verifier = ADDITIONAL_GENESIS_RECORD_KIND_VERIFIERS.get(kind)
        if verifier is None:
            raise BindingValidationError(
                f"{kind!r} is not an allowed additional genesis record kind -- "
                "ADDITIONAL_GENESIS_RECORD_KIND_SET=CLOSED"
            )
        verifier(record_id, body)

    # 1. Duplicate (kind, id) detection across the whole candidate manifest (Phase 9
    #    Structural Review Round 3, P9-R3-F1): SHUKOU's own ratified semantics --
    #    DUPLICATE_DEFINITION=SAME_KIND_AND_ID_APPEARS_MORE_THAN_ONCE,
    #    IDENTICAL_DUPLICATE_ALLOWED=false, DUPLICATE_BODY_EQUALITY_IRRELEVANT=true -- reject
    #    the SECOND appearance of any (kind, id), whether its body is identical to or differs
    #    from the first. This is walked as an ordered list before any set/dict normalization
    #    (MANIFEST_MULTIPLICITY_MUST_BE_VALIDATED_BEFORE_SET_NORMALIZATION=true): `seen` below
    #    exists only to detect the second occurrence, never to silently collapse it.
    seen: set[tuple[str, str]] = set()
    for kind, record_id, _body in candidate:
        key = (kind, record_id)
        if key in seen:
            raise BindingValidationError(
                f"duplicate candidate genesis manifest member (even if identical): "
                f"{kind}/{record_id}"
            )
        seen.add(key)

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
    candidate_keys = seen
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
