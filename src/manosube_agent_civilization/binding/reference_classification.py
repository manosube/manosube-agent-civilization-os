"""The one production typed reference-edge classification for Product Binding
(Phase 9, Issue #43, P9-R1-F5, extended by Phase 9 Structural Review Round 2 P9-R2-F3).

Pattern-compatible with, but organizationally separate from,
:mod:`manosube_agent_civilization.reflow.reference_registry` -- that registry is Reflow's
own, over Reflow's own Store-owned record kinds; this module is Product Binding's own, over
every record kind ``bind_project`` accepts or persists.

Round 1 (P9-R1-F5) classified only Project Binding's own three top-level reference fields.
Round 2's own independent re-observation found this incomplete: ``bind_project`` also
accepts and persists Objective Revision, Authority Rule, and genesis State bodies, each of
which carries its own reference fields that were never classified or closure-checked at
all -- a caller could declare a genesis State naming a dangling Kernel Source Snapshot, or
an Objective Revision naming the wrong Human Authority kind, and nothing here would refuse
it before ``store.initialize()``. This module now classifies **every** reference field on
**every** record kind ``bind_project`` accepts:

- ``project_binding``: ``objective_revision_ref``, ``authority_policy_ref``,
  ``human_authority_ref`` (Round 1's own three fields, unchanged).
- ``objective_revision`` (``01_SCHEMA/objective/objective.schema.json``/
  ``objective_revision.schema.json``): ``owner_authority_ref`` (``00_KERNEL/01_OBJECTIVE/
  OBJECTIVE_CONTRACT.md`` §"owner_authority_ref resolves to Human Objective Authority" --
  the existing Kernel contract already settles this as the Human Authority kind, no new
  semantics invented here), ``human_authority_ref``, ``boundary_ref``,
  ``previous_objective_ref``.
- ``authority_rule`` (``01_SCHEMA/authority/authority_rule.schema.json``): ``declared_by``.
- ``project_state`` (genesis State, ``01_SCHEMA/state/project_state.schema.json``):
  ``state_metadata.source_snapshot_refs[]``, ``state_metadata.observation_scope_refs[]``,
  ``evidence_refs[]``, ``lineage_head_ref``.

Every field is classified into exactly one of three categories:

- **Store-owned** (:data:`STORE_OWNED_REFERENCE_KINDS`): the referenced body is a real
  Store-persisted record -- resolvable against the current candidate genesis manifest (the
  ``(kind, id, body)`` records ``bind_project`` is about to stage) or an already-committed
  Store record, via :func:`resolve_binding_references`.
- **External constitutional identity** (:data:`EXTERNAL_REFERENCE_KINDS`): never a Store
  record -- ``human_authority``'s own position, unchanged by either round
  (``HUMAN_AUTHORITY_STORE_RECORD_REQUIRED=false``).
- **No Store-owned producer** (:data:`NO_PRODUCER_REFERENCE_KINDS`): a kind this Kernel's
  schemas name but that no Store-owned producer this vertical persists ever mints
  (``objective_boundary``, ``observation_scope`` -- the identical classification Reflow's
  own registry already gives these two kinds, confirmed against that module's own
  docstring). Checked for kind correctness, never resolved against the Store.

:func:`reject_wrong_kind_reference` and :func:`reference_edges` both run before any Store
lookup ever happens -- a reference whose own ``kind`` is not the one closed kind its field
permits is refused, never silently accepted or narrowed to "whatever kind happened to be
there" (``CROSS_KIND_SUBSTITUTION_ALLOWED=false``, the identical semantic decision Reflow's
own registry already enforces, over a different vocabulary). Additional genesis records
(e.g. the real Kernel Source Snapshot) delegate their own reference-edge classification to
:mod:`manosube_agent_civilization.reflow.reference_registry` when that registry already
recognizes their kind -- never a second, duplicated field/path table for a kind Reflow
already classifies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import BindingValidationError

#: Every Store-owned record kind a field classified below may name -- resolvable against the
#: current candidate genesis manifest or an already-committed Store record.
#: ``observation_evidence``/``negative_evidence`` are included here even though Binding's own
#: genesis transaction never mints either kind itself: at genesis (state_revision 0) no
#: Evidence can yet exist, so a non-empty ``evidence_refs`` entry can never legitimately
#: resolve against this genesis transaction's own candidate manifest, and treating them as
#: Store-owned is what makes that case fail closed rather than silently pass unchecked
#: (Phase 9 Structural Review Round 2, P9-R2-F2's own "missing Evidence" negative control).
STORE_OWNED_REFERENCE_KINDS: frozenset[str] = frozenset(
    {
        "objective_revision",
        "authority_rule",
        "source_snapshot",
        "observation_evidence",
        "negative_evidence",
    }
)

#: External constitutional identity kinds -- never Store records, never resolved.
EXTERNAL_REFERENCE_KINDS: frozenset[str] = frozenset({"human_authority"})

#: Kinds this Kernel's schemas name but that no Store-owned producer this vertical persists
#: ever mints (the identical classification Reflow's own registry gives them). Checked for
#: kind correctness only; never resolved against the Store.
NO_PRODUCER_REFERENCE_KINDS: frozenset[str] = frozenset({"objective_boundary", "observation_scope"})

#: ``(source_record_kind, field_path) -> the closed set of kinds that field may actually
#: carry``. Every reference field each accepted record kind's own canonical schema declares
#: is named here exactly once. ``field_path`` uses the identical dotted-locator convention
#: (``[]`` iterates a list) :mod:`manosube_agent_civilization.reflow.reference_registry`
#: already established, so a field name shared conceptually across modules stays directly
#: comparable.
FIELD_EXPECTED_TARGET_KINDS: dict[tuple[str, str], frozenset[str]] = {
    # -- project_binding (01_SCHEMA/binding/project_binding.schema.json) -- Round 1 --------
    ("project_binding", "objective_revision_ref"): frozenset({"objective_revision"}),
    ("project_binding", "authority_policy_ref"): frozenset({"authority_rule"}),
    ("project_binding", "human_authority_ref"): frozenset({"human_authority"}),
    # -- objective_revision (01_SCHEMA/objective/objective.schema.json + objective_revision
    #    .schema.json) -- Round 2 P9-R2-F3 --------------------------------------------------
    ("objective_revision", "owner_authority_ref"): frozenset({"human_authority"}),
    ("objective_revision", "human_authority_ref"): frozenset({"human_authority"}),
    ("objective_revision", "boundary_ref"): frozenset({"objective_boundary"}),
    ("objective_revision", "previous_objective_ref"): frozenset({"objective_revision"}),
    # -- authority_rule (01_SCHEMA/authority/authority_rule.schema.json) -- Round 2 ---------
    ("authority_rule", "declared_by"): frozenset({"human_authority"}),
    # -- project_state / genesis State (01_SCHEMA/state/project_state.schema.json +
    #    state_metadata.schema.json) -- Round 2 P9-R2-F2/F3 ---------------------------------
    ("project_state", "state_metadata.source_snapshot_refs[]"): frozenset({"source_snapshot"}),
    ("project_state", "state_metadata.observation_scope_refs[]"): frozenset({"observation_scope"}),
    ("project_state", "evidence_refs[]"): frozenset({"observation_evidence", "negative_evidence"}),
    ("project_state", "lineage_head_ref"): frozenset({"state_transition"}),
}


@dataclass(frozen=True)
class TypedReferenceEdge:
    """One reference edge this accepted graph declares, carrying the field provenance that
    produced it -- never merely a bare ``(kind, id)`` tuple, mirroring
    :class:`manosube_agent_civilization.reflow.reference_registry.TypedReferenceEdge`."""

    source_kind: str
    field_path: str
    target_kind: str
    target_id: str

    def __iter__(self):
        return iter((self.target_kind, self.target_id))


def reject_wrong_kind_reference(field_name: str, reference: dict[str, Any]) -> None:
    """Fail closed, before any Store lookup, unless *reference*'s own ``kind`` is exactly
    the one (or one of the) closed kind(s) *field_name* is classified to carry, on
    ``project_binding``'s own top-level fields (Round 1's own three-field surface, kept for
    the existing callers that check one bare field by name rather than a whole record).

    Raises :class:`~.errors.BindingValidationError` for an unclassified field name (a
    programming error in this module's own caller, never a caller-supplied condition), a
    malformed reference, or a reference naming any kind outside the field's own closed set.
    """

    allowed = FIELD_EXPECTED_TARGET_KINDS.get(("project_binding", field_name))
    if allowed is None:
        raise BindingValidationError(
            f"{field_name!r} is not a classified Product Binding reference field"
        )
    _check_reference(field_name, reference, allowed)


def _check_reference(diagnostic_path: str, reference: Any, allowed: frozenset[str]) -> None:
    if not isinstance(reference, dict):
        raise BindingValidationError(
            f"{diagnostic_path}: reference value is not an object: {reference!r}"
        )
    kind = reference.get("kind")
    ref_id = reference.get("id")
    if not isinstance(kind, str) or not kind:
        raise BindingValidationError(
            f"{diagnostic_path}: reference is missing a non-empty kind: {reference!r}"
        )
    if not isinstance(ref_id, str) or not ref_id:
        raise BindingValidationError(
            f"{diagnostic_path}: reference is missing a non-empty id: {reference!r}"
        )
    if kind not in allowed:
        raise BindingValidationError(
            f"{diagnostic_path}: reference kind {kind!r} is not permitted here -- expected "
            f"one of {sorted(allowed)}, CROSS_KIND_SUBSTITUTION_ALLOWED=false"
        )


def reference_edges(source_kind: str, body: dict[str, Any]) -> list[TypedReferenceEdge]:
    """Return every :class:`TypedReferenceEdge` *body* (an accepted record of *source_kind*)
    declares -- fail-closed on any reference whose shape is malformed or whose actual kind is
    not the one its own field permits, before this function ever returns one for a caller to
    resolve. ``NULL_REFERENCE=NO_EDGE``: an absent (``None``) reference is not an edge and is
    not an error -- the identical convention Reflow's own registry uses.

    Only a reference whose actual kind is both permitted for its field *and* itself
    Store-owned (:data:`STORE_OWNED_REFERENCE_KINDS`) becomes a :class:`TypedReferenceEdge`;
    a permitted-but-external or no-producer kind (``human_authority``, ``objective_boundary``,
    ``observation_scope``) is valid here and correctly produces no edge to resolve.

    Raises :class:`~.errors.BindingValidationError` if *source_kind* is not one of
    ``project_binding``/``objective_revision``/``authority_rule``/``project_state``.
    """

    edges: list[TypedReferenceEdge] = []

    def check(field_path: str, ref: Any, *, diagnostic_path: str | None = None) -> None:
        if ref is None:
            return
        diagnostic_path = diagnostic_path or field_path
        allowed = FIELD_EXPECTED_TARGET_KINDS.get((source_kind, field_path))
        if allowed is None:
            raise BindingValidationError(
                f"{source_kind}.{diagnostic_path}: no expected target kind is registered for "
                "this reference field -- UNKNOWN_CLASSIFICATION_FIELD_PATH"
            )
        _check_reference(f"{source_kind}.{diagnostic_path}", ref, allowed)
        kind = ref["kind"]
        if kind in STORE_OWNED_REFERENCE_KINDS:
            edges.append(TypedReferenceEdge(source_kind, diagnostic_path, kind, ref["id"]))

    def check_list(field_path: str, values: Any) -> None:
        base = field_path[: -len("[]")]
        for index, ref in enumerate(values or []):
            check(field_path, ref, diagnostic_path=f"{base}[{index}]")

    if source_kind == "project_binding":
        check("objective_revision_ref", body.get("objective_revision_ref"))
        check("authority_policy_ref", body.get("authority_policy_ref"))
        check("human_authority_ref", body.get("human_authority_ref"))
    elif source_kind == "objective_revision":
        check("owner_authority_ref", body.get("owner_authority_ref"))
        check("human_authority_ref", body.get("human_authority_ref"))
        check("boundary_ref", body.get("boundary_ref"))
        check("previous_objective_ref", body.get("previous_objective_ref"))
    elif source_kind == "authority_rule":
        check("declared_by", body.get("declared_by"))
    elif source_kind == "project_state":
        state_metadata = body.get("state_metadata") or {}
        check_list(
            "state_metadata.source_snapshot_refs[]",
            state_metadata.get("source_snapshot_refs"),
        )
        check_list(
            "state_metadata.observation_scope_refs[]",
            state_metadata.get("observation_scope_refs"),
        )
        check_list("evidence_refs[]", body.get("evidence_refs"))
        check("lineage_head_ref", body.get("lineage_head_ref"))
    else:
        raise BindingValidationError(
            f"{source_kind!r} is not a record kind this registry classifies -- "
            "UNKNOWN_SOURCE_RECORD_KIND"
        )

    return edges


def resolve_binding_references(
    store: Any, project_binding: dict[str, Any]
) -> dict[str, dict[str, Any] | None]:
    """Recursively resolve every Store-owned reference Product Binding's own top-level
    record declares, against *store* (a fresh instance or an established one alike).

    Returns ``{field_name: resolved_body_or_None}`` for ``objective_revision_ref``/
    ``authority_policy_ref``. ``human_authority_ref`` is never included: it is classified
    external and this module never resolves it against the Store
    (``HUMAN_AUTHORITY_STORE_RECORD_REQUIRED=false``).

    Resolves nothing itself beyond a plain :meth:`~manosube_agent_civilization.store.
    file_store.FileStateStore.resolve_record` call per field -- this function proves
    closure, it does not persist or mint anything, and is not a second Store owner.
    """

    project_id = project_binding["project_id"]
    resolved: dict[str, dict[str, Any] | None] = {}
    for field_name in ("objective_revision_ref", "authority_policy_ref"):
        reference = project_binding[field_name]
        reject_wrong_kind_reference(field_name, reference)
        resolved[field_name] = store.resolve_record(project_id, reference["kind"], reference["id"])
    return resolved
