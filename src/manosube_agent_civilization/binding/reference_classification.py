"""The one production typed reference-edge classification for Product Binding
(Phase 9, Issue #43, P9-R1-F5).

Pattern-compatible with, but organizationally separate from,
:mod:`manosube_agent_civilization.reflow.reference_registry` -- that registry is Reflow's
own, over Reflow's own Store-owned record kinds; this module is Product Binding's own, over
Product Binding's own three top-level reference fields. Neither repurposes the other, and
neither becomes a second owner of the other's record kinds: this module recognizes exactly
the reference vocabulary Product Binding's own schema (``01_SCHEMA/binding/
project_binding.schema.json``) declares, nothing Reflow persists.

Every field is classified exactly once, into exactly one of two closed categories:

- **Store-owned** (:data:`STORE_OWNED_REFERENCE_FIELDS`): the referenced body is a real,
  Store-persisted record this Binding's own genesis transaction adopts or an earlier
  transaction already committed. Resolvable via :func:`resolve_binding_references` against
  a fresh Store instance and a fresh process alike.
- **External constitutional identity** (:data:`EXTERNAL_REFERENCE_FIELDS`): the referenced
  identity is never a Store record and is never resolved against the Store --
  ``human_authority_ref``'s own position, unchanged by this Finding (SHUKOU's own adopted
  ``HUMAN_AUTHORITY_REFERENCE_CLASS=EXTERNAL_CONSTITUTIONAL_IDENTITY``,
  ``HUMAN_AUTHORITY_STORE_RECORD_REQUIRED=false``).

:func:`reject_wrong_kind_reference` runs before any Store lookup ever happens -- a
reference whose own ``kind`` is not the one closed kind its field permits is refused here,
never silently accepted or narrowed to "whatever kind happened to be there"
(``CROSS_KIND_SUBSTITUTION_ALLOWED=false``, the identical semantic decision Reflow's own
registry already enforces, over a different vocabulary).
"""

from __future__ import annotations

from typing import Any

from .errors import BindingValidationError

#: Every Store-owned record kind a Product Binding's own top-level reference field may name.
#: A kind outside this set is never resolved against the Store by this module.
STORE_OWNED_REFERENCE_KINDS: frozenset[str] = frozenset({"objective_revision", "authority_rule"})

#: External constitutional identity kinds -- never Store records, never resolved.
EXTERNAL_REFERENCE_KINDS: frozenset[str] = frozenset({"human_authority"})

#: ``field_name -> the closed set of kinds that field may actually carry``. Every Product
#: Binding top-level reference field is named here exactly once; a field name absent from
#: this table is not a reference field this module classifies.
FIELD_EXPECTED_TARGET_KINDS: dict[str, frozenset[str]] = {
    "objective_revision_ref": frozenset({"objective_revision"}),
    "authority_policy_ref": frozenset({"authority_rule"}),
    "human_authority_ref": frozenset({"human_authority"}),
}


def reject_wrong_kind_reference(field_name: str, reference: dict[str, Any]) -> None:
    """Fail closed, before any Store lookup, unless *reference*'s own ``kind`` is exactly
    the one (or one of the) closed kind(s) *field_name* is classified to carry.

    Raises :class:`~.errors.BindingValidationError` for an unclassified field name (a
    programming error in this module's own caller, never a caller-supplied condition), a
    malformed reference, or a reference naming any kind outside the field's own closed set.
    """

    allowed = FIELD_EXPECTED_TARGET_KINDS.get(field_name)
    if allowed is None:
        raise BindingValidationError(
            f"{field_name!r} is not a classified Product Binding reference field"
        )
    if not isinstance(reference, dict):
        raise BindingValidationError(f"{field_name}: reference value is not an object: {reference!r}")
    kind = reference.get("kind")
    if not isinstance(kind, str) or not kind:
        raise BindingValidationError(f"{field_name}: reference is missing a non-empty kind: {reference!r}")
    if kind not in allowed:
        raise BindingValidationError(
            f"{field_name}: reference kind {kind!r} is not permitted here -- expected one of "
            f"{sorted(allowed)}, CROSS_KIND_SUBSTITUTION_ALLOWED=false"
        )


def resolve_binding_references(store: Any, project_binding: dict[str, Any]) -> dict[str, dict[str, Any] | None]:
    """Recursively resolve every Store-owned reference this Product Binding's own accepted
    graph declares, against *store* (a fresh instance or an established one alike).

    Returns ``{field_name: resolved_body_or_None}`` for every :data:`STORE_OWNED_REFERENCE_
    KINDS` field this record carries -- ``objective_revision_ref``/``authority_policy_ref``.
    ``human_authority_ref`` is never included: it is classified external and this module
    never resolves it against the Store (``HUMAN_AUTHORITY_STORE_RECORD_REQUIRED=false``).

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
