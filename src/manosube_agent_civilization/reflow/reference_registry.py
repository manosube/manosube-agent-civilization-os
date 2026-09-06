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

Round 4 completion repair 2 (P8-R4-C2-F1, adopted): 構造参謀's independent re-observation
found this registry's own coverage incomplete -- ``difference_event`` recognized only its
own ``previous_event_id`` self-reference, and ``closure_evaluation`` recognized only its own
``difference_event_head_ref``, leaving both records' many other genuinely Store-owned
reference fields (``closure_evaluation_ref``, ``observation_refs``, ``evidence_refs``,
``kernel_source_witness_ref``, ``after_observation_refs``, ``change_result_evidence_refs``,
``change_free_verification_evidence_refs``, ``evidence_sufficiency_ref``,
``terminal_reason_evidence_refs``, and the nested Store-owned references inside
``candidate_invariant_evaluation_bindings``/``candidate_claim_evaluation_bindings``)
unwalked by this registry -- so a persisted record whose *only* checked field resolved could
still carry an unresolved reference in any of these other fields, undetected. Closed here by
classifying every reference field every Store-owned record kind's own canonical schema
declares (``00_KERNEL/VERTICAL_PROOF_CONTRACT.md`` carries the complete classification
table this module's own code below implements). Four additional record kinds this vertical
already persists (confirmed against ``reflow/route.py``'s own admission code, never assumed)
were previously missing as recognized reference *targets* entirely --
``closure_evaluation``, ``evidence_sufficiency_result``, ``kernel_source_witness``,
``invariant_evaluation``, ``candidate_claim_evaluation_event`` and
``candidate_completion_record`` -- and are added to :data:`STORE_OWNED_REFERENCE_KINDS`.

This module enumerates edges; it resolves nothing, persists nothing, and is not a second
canonical owner of any record kind -- only a read of reference-bearing fields those owners
already produce. :data:`STORE_OWNED_REFERENCE_KINDS` is deliberately narrow: a reference
kind this Kernel names but gives no Store-owned producer of its own is out of this
registry's scope, never silently treated as resolved. Confirmed, not merely a fuzzy `*_ref`
key-suffix guess, against every referenced kind's actual production behavior (whether
``reflow/route.py`` ever calls ``store.commit``/``_merge_verified_record`` for it):

- ``difference`` -- Difference has no Reflow-Store-owned persistence of its own; Evidence's
  own ``difference_ref`` and Sufficiency/Invariant-Evaluation's own ``subject_ref``/
  ``difference_ref`` name it, but it is never a ``resolve_record`` target here.
- ``change`` -- Change is verified by canonical-reference equality against the caller's own
  already-verified input (P8-R1-F5/P8-R2-F2), never resolved from the Store.
- ``authority_decision`` -- identical: canonical-reference equality against caller input,
  never a Store record.
- ``artifact``, ``negative_evidence``, ``material_contradiction``, ``target_predicate``,
  ``objective_revision``, ``closure_policy``, ``observation_scope``, ``observation_method``,
  ``normalized_fact``, ``kernel_invariant``, ``next_observation_request``,
  ``reopen_condition``, ``reopen_condition_evaluation`` -- named by this Kernel's schemas,
  none ever persisted as an immutable record by this vertical's Reflow Store.
- ``state``/``state_transition`` -- resolved through the State/Store's own dedicated lineage
  and transaction mechanisms (``load_current``/``resolve_transaction``), never through
  ``resolve_record`` -- a different, already-established resolution surface, not this
  registry's to duplicate.
"""

from __future__ import annotations

from typing import Any

#: Every Store-owned record kind this registry recognizes as a reference *target*. A
#: reference naming any other ``kind`` is not this vertical's to resolve (no Store-owned
#: producer exists for it), so :func:`reference_edges` never emits an edge toward one.
STORE_OWNED_REFERENCE_KINDS: frozenset[str] = frozenset(
    {
        "observation",
        "observation_evidence",
        "source_snapshot",
        "difference_event",
        "closure_evaluation",
        "evidence_sufficiency_result",
        "kernel_source_witness",
        "invariant_evaluation",
        "candidate_claim_evaluation_event",
        "candidate_completion_record",
    }
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

    Covers, completely, every reference field each Store-owned record kind's own canonical
    schema declares (``00_KERNEL/VERTICAL_PROOF_CONTRACT.md``'s Reference Field
    Classification table is this function's own specification):

    - ``observation``: ``source_snapshot_refs``, ``observation_evidence_refs``.
    - ``observation_evidence``: ``observed_result.observation_ref``,
      ``lineage.derived_from`` members, ``lineage.predecessor_evidence_refs`` members, and
      each ``artifact_references`` member's own optional ``source_snapshot_ref`` (never
      populated by any producer in this vertical today, but not silently skipped merely
      because it is currently always absent).
    - ``closure_evaluation``: ``kernel_source_witness_ref``, ``difference_event_head_ref``,
      the embedded ``after_state_candidate``'s own ``source_snapshot_refs`` members (kind
      ``source_snapshot`` -- confirmed against :func:`~manosube_agent_civilization.reflow.
      closure.build_after_state_candidate`'s own producer code, never assumed from the field
      name alone), ``after_observation_refs``, ``change_result_evidence_refs``,
      ``change_free_verification_evidence_refs``, ``evidence_sufficiency_ref``,
      ``terminal_reason_evidence_refs``, ``contradiction_refs`` (target kind
      ``material_contradiction`` is not Store-owned, so this edge is classified but never
      emitted), and -- recursively, the embedded reference fields nested inside each
      ``candidate_invariant_evaluation_bindings``/``candidate_claim_evaluation_bindings``
      entry: ``invariant_evaluation_ref``/``evaluation_evidence_refs`` and
      ``evaluation_head_event_ref``/``completion_record_ref``/``evaluation_evidence_refs``
      respectively.
    - ``difference_event``: ``previous_event_id`` (a bare id string, not a ``{kind, id}``
      reference object -- the kind is always ``difference_event``, its own vocabulary's one
      self-reference), ``observation_refs``, ``evidence_refs``, ``closure_evaluation_ref``,
      ``revoked_evidence_refs``, ``invalid_evidence_refs``, ``contradiction_evidence_refs``
      (the last three are schema-conditional on reopen triggers this vertical's own
      ``reopen()`` never actually mints -- classified, always empty in production, never
      silently unwalked).
    - ``evidence_sufficiency_result``: ``evidence_refs`` members.
    - ``invariant_evaluation``: ``evidence_refs`` members.
    - ``candidate_claim_evaluation_event``: ``predecessor_event_ref``,
      ``completion_record_ref``.
    - ``candidate_completion_record``: ``required_evidence_refs`` members,
      ``invariant_evaluation_refs`` members.
    - ``source_snapshot``, ``kernel_source_witness``: leaf record kinds -- their own
      canonical schemas declare no reference field of any kind, so neither emits an edge.
    """

    edges: list[tuple[str, str]] = []

    def _add(ref: Any) -> None:
        edge = _edge(ref)
        if edge is not None:
            edges.append(edge)

    def _add_members(collection: Any) -> None:
        if not isinstance(collection, dict):
            return
        for ref in collection.get("members") or []:
            _add(ref)

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
        for artifact_ref in (body.get("artifact_references") or {}).get("members") or []:
            if isinstance(artifact_ref, dict):
                _add(artifact_ref.get("source_snapshot_ref"))
    elif kind == "closure_evaluation":
        _add(body.get("kernel_source_witness_ref"))
        _add(body.get("difference_event_head_ref"))
        after_state_candidate = body.get("after_state_candidate")
        if isinstance(after_state_candidate, dict):
            _add_members(after_state_candidate.get("source_snapshot_refs"))
        for ref in body.get("after_observation_refs") or []:
            _add(ref)
        for ref in body.get("change_result_evidence_refs") or []:
            _add(ref)
        for ref in body.get("change_free_verification_evidence_refs") or []:
            _add(ref)
        _add(body.get("evidence_sufficiency_ref"))
        for ref in body.get("terminal_reason_evidence_refs") or []:
            _add(ref)
        for ref in body.get("contradiction_refs") or []:
            _add(ref)
        for binding in body.get("candidate_invariant_evaluation_bindings") or []:
            if not isinstance(binding, dict):
                continue
            _add(binding.get("invariant_evaluation_ref"))
            _add_members(binding.get("evaluation_evidence_refs"))
        for binding in body.get("candidate_claim_evaluation_bindings") or []:
            if not isinstance(binding, dict):
                continue
            _add(binding.get("evaluation_head_event_ref"))
            _add(binding.get("completion_record_ref"))
            _add_members(binding.get("evaluation_evidence_refs"))
    elif kind == "difference_event":
        previous_event_id = body.get("previous_event_id")
        if isinstance(previous_event_id, str) and previous_event_id:
            edges.append(("difference_event", previous_event_id))
        for ref in body.get("observation_refs") or []:
            _add(ref)
        for ref in body.get("evidence_refs") or []:
            _add(ref)
        _add(body.get("closure_evaluation_ref"))
        for ref in body.get("revoked_evidence_refs") or []:
            _add(ref)
        for ref in body.get("invalid_evidence_refs") or []:
            _add(ref)
        for ref in body.get("contradiction_evidence_refs") or []:
            _add(ref)
    elif kind in ("evidence_sufficiency_result", "invariant_evaluation"):
        _add_members(body.get("evidence_refs"))
    elif kind == "candidate_claim_evaluation_event":
        _add(body.get("predecessor_event_ref"))
        _add(body.get("completion_record_ref"))
    elif kind == "candidate_completion_record":
        _add_members(body.get("required_evidence_refs"))
        _add_members(body.get("invariant_evaluation_refs"))
    return edges
