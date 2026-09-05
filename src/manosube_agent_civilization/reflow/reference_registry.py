"""The one production reference-edge registry for Store-owned record kinds.

SHUKOU Phase 8 final-closure round 4 (P8-R4-F1/F2): Round 3's own Reference Closure gate
(``route.py``'s ``_admitted_records``) was scoped to one field on one record kind
(``observation.observation_evidence_refs``) and gated on a caller opting in. Round 4 makes
Reference Closure an unconditional ``reflow()`` invariant covering every Store-owned
reference edge this vertical persists -- which first requires exactly one place naming what
those edges *are*, so the production gate and any test proving
``UNRESOLVED_STORE_OWNED_REFERENCE_COUNT=0`` walk the identical vocabulary
(``PRODUCTION_AND_TEST_REFERENCE_VOCABULARY_MUST_MATCH=true``,
``DUPLICATE_TEST_REFERENCE_REGISTRY=false``, ``FUZZY_KEY_SUFFIX_SCAN=false``).

This module enumerates edges; it resolves nothing, persists nothing, and is not a second
canonical owner of any record kind -- only a read of reference-bearing fields those owners
already produce. :data:`STORE_OWNED_REFERENCE_KINDS` is deliberately narrow: a reference
kind this Kernel names but gives no Store-owned producer of its own (``difference``,
``change``, ``authority_decision``, ``artifact``, ``negative_evidence``, ...) is out of this
registry's scope, never silently treated as resolved.
"""

from __future__ import annotations

from typing import Any

#: Every Store-owned record kind this registry recognizes as a reference *target*. A
#: reference naming any other ``kind`` is not this vertical's to resolve (no Store-owned
#: producer exists for it), so :func:`reference_edges` never emits an edge toward one.
STORE_OWNED_REFERENCE_KINDS: frozenset[str] = frozenset(
    {"observation", "observation_evidence", "source_snapshot", "difference_event"}
)


def _edge(ref: Any) -> tuple[str, str] | None:
    if (
        isinstance(ref, dict)
        and isinstance(ref.get("kind"), str)
        and ref["kind"] in STORE_OWNED_REFERENCE_KINDS
        and isinstance(ref.get("id"), str)
        and ref["id"]
    ):
        return (ref["kind"], ref["id"])
    return None


def reference_edges(kind: str, body: dict[str, Any]) -> list[tuple[str, str]]:
    """Return every ``(ref_kind, ref_id)`` edge *body* (an admitted record of *kind*)
    declares toward another Store-owned record.

    Covers, minimally (P8-R4 section 6.2): an ``observation`` record's own
    ``source_snapshot_refs`` and ``observation_evidence_refs``; an ``observation_evidence``
    record's own ``observed_result.observation_ref``, ``lineage.derived_from`` members and
    ``lineage.predecessor_evidence_refs`` members; a ``closure_evaluation`` record's own
    ``difference_event_head_ref``; and a ``difference_event`` record's own
    ``previous_event_id`` (a bare id string, not a ``{kind, id}`` reference object -- the
    kind is always ``difference_event``, its own vocabulary's one self-reference).
    """

    edges: list[tuple[str, str]] = []

    def _add(ref: Any) -> None:
        edge = _edge(ref)
        if edge is not None:
            edges.append(edge)

    if kind == "observation":
        for ref in body.get("source_snapshot_refs") or []:
            _add(ref)
        for ref in body.get("observation_evidence_refs") or []:
            _add(ref)
    elif kind == "observation_evidence":
        observed_result = body.get("observed_result") or {}
        _add(observed_result.get("observation_ref"))
        lineage = body.get("lineage") or {}
        for ref in (lineage.get("derived_from") or {}).get("members") or []:
            _add(ref)
        for ref in (lineage.get("predecessor_evidence_refs") or {}).get("members") or []:
            _add(ref)
    elif kind == "closure_evaluation":
        _add(body.get("difference_event_head_ref"))
    elif kind == "difference_event":
        previous_event_id = body.get("previous_event_id")
        if isinstance(previous_event_id, str) and previous_event_id:
            edges.append(("difference_event", previous_event_id))
    return edges
