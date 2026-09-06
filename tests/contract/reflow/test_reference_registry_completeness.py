"""Independent completeness proof for the production reference-edge registry
(:mod:`manosube_agent_civilization.reflow.reference_registry`).

SHUKOU Phase 8 final-closure round 4 completion repair 2 (P8-R4-C2-F1, adopted): 構造参謀's
independent re-observation found the registry's own *coverage* incomplete -- it recognized
only ``difference_event.previous_event_id`` and ``closure_evaluation.difference_event_head_
ref``, leaving both records' many other genuinely Store-owned reference fields unwalked.
Every test that merely calls ``reference_edges`` and checks the result against a real
committed transaction (as ``test_vertical_proof_reference_closure.py`` already does) proves
the registry is *self-consistent*, never that it is *complete* -- a field the registry never
even looks at can never appear as an "unresolved" failure, so a real fixture world that
happens to keep every field resolvable anyway would pass regardless of the gap
(``GREEN_TESTS_ALONE_DO_NOT_PROVE_REGISTRY_COMPLETENESS=true``).

SHUKOU Phase 8 final-closure round 4 completion repair 3 (P8-R4-C3-F1, adopted): 構造参謀's
own further independent re-observation found this file's own *sentinel design* was itself
one uniform kind (``observation_evidence``) for every field, including fields whose real
production semantics require a different kind (``difference_event.observation_refs`` must
always name an ``observation``, never an ``observation_evidence``) -- and the production
registry itself trusted a reference's own self-declared ``kind`` rather than checking it
against the field's own expected kind, so this file's own uniform sentinel silently never
exercised that distinction at all. Both are closed together: the production registry now
carries a field-path-keyed table of each field's own closed set of permitted kinds
(:data:`~manosube_agent_civilization.reflow.reference_registry.FIELD_EXPECTED_TARGET_KINDS`),
and this file's own :data:`_EXPECTED_TARGET_KINDS` is an *independently hand-authored* copy of
that same knowledge -- cross-cited against :mod:`manosube_agent_civilization.difference.graph`
(an already-adopted, schema-cross-validated typed reference registry for Difference's own
emitted bundle, sharing several field names with this vertical's Reflow Store-commit records)
and directly against ``evidence/engine.py``'s own producer code where ``difference.graph``
does not describe the field -- never derived by importing or trusting this repository's own
production table. :func:`test_every_expected_target_kind_matches_the_production_registry`
proves the two agree, in both directions.

This file proves completeness three ways:

1. It re-derives, straight from each Store-owned record kind's own canonical schema file on
   disk (never by importing or trusting this registry's own code), the *complete*
   ``required`` field set every such record must carry, classifies every one of those fields
   by hand into this module's own :data:`_REQUIRED_FIELD_CLASSIFICATION` table, and asserts
   that table's own key set equals each schema's live ``required`` list
   (``UNCLASSIFIED_REFERENCE_FIELD_COUNT=0``).
2. It exercises ``reference_edges`` with one distinct synthetic sentinel reference per
   Store-owned (classification ``A``) field, proving both that every such field actually
   contributes its own edge (an *omitted* field would leave its sentinel unwalked) and that
   no unclassified or non-Store-owned field is walked by mistake (an *extra*, over-eager
   field would produce an edge this test never planted).
3. It proves the production registry's own *kind* expectation for every classification-A
   field is exactly what real schema/producer code allows -- a right-kind, right-id
   reference produces the edge; a *wrong*-kind reference naming a real, existing Store-owned
   kind this field does not permit is refused before this function ever returns an edge for
   it, never silently accepted (the exact shape of P8-R4-C3-F1 itself).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from manosube_agent_civilization.reflow import reference_registry
from manosube_agent_civilization.reflow.errors import ReflowValidationError
from manosube_agent_civilization.reflow.reference_registry import (
    STORE_OWNED_REFERENCE_KINDS,
    reference_edges,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPOSITORY_ROOT / "01_SCHEMA"

#: Every Store-owned record kind this vertical's Reflow Store actually persists (confirmed,
#: not assumed, against ``reflow/route.py``'s own admission code -- every ``records[...] =``/
#: ``_merge_verified_record`` call site this repository's ``reflow`` module makes), together
#: with the on-disk schema file that defines its ``required`` field set.
_SCHEMA_FILE_FOR_KIND: dict[str, str] = {
    "observation": "observation/observation.schema.json",
    "observation_evidence": "evidence/evidence.schema.json",
    "source_snapshot": "observation/source_snapshot.schema.json",
    "difference_event": "difference/difference_lifecycle_event.schema.json",
    "closure_evaluation": "difference/closure_evaluation.schema.json",
    "evidence_sufficiency_result": "difference/evidence_sufficiency_result.schema.json",
    "kernel_source_witness": "reflow/kernel_source_witness.schema.json",
    "invariant_evaluation": "difference/invariant_evaluation.schema.json",
    "candidate_claim_evaluation_event": "difference/candidate_claim_evaluation_event.schema.json",
    "candidate_completion_record": "difference/candidate_completion_record.schema.json",
}

#: Every schema field each persisted record kind's own canonical schema *requires*,
#: classified by hand:
#:   A = Store-owned resolvable reference (this registry must, and does, walk it)
#:   B = State/transaction reference, resolved via a different established mechanism
#:       (``load_current``/``resolve_transaction``), never through ``resolve_record``
#:   C = external or non-Store-owned reference (no Store-owned producer exists for its
#:       target kind in this vertical -- confirmed by grep, never assumed)
#:   D = nullable/conditionally-absent reference that no production code path in this
#:       vertical currently ever populates (a deferred reopen trigger's own fields) --
#:       classified A in shape, D in practice, so its absence is never silently mistaken
#:       for "not a reference field at all"
#:   E = a field whose own value is itself a list of embedded objects, each carrying further
#:       reference fields that must be recursively classified (walked out separately, below)
#:   N = not a reference field of any kind (an enum, a scalar, a fingerprint, a timestamp, a
#:       nested object with no Store-owned reference anywhere inside it)
_REQUIRED_FIELD_CLASSIFICATION: dict[str, dict[str, str]] = {
    "observation": {
        "schema_version": "N",
        "observation_id": "N",
        "project_id": "N",
        "state_revision_observed": "N",
        "state_fingerprint_observed": "N",
        "target": "N",
        "scope_ref": "C",  # kind observation_scope -- never Store-persisted
        "method_ref": "C",  # kind observation_method -- never Store-persisted
        "time_boundary": "N",
        "source_snapshot_refs": "A",
        "normalization_profile": "N",
        "normalized_fact_refs": "C",  # kind normalized_fact -- never Store-persisted
        "status": "N",
        "blind_spots": "N",
        "attempts": "N",  # each carries its own method_ref, kind observation_method -- C
        "observation_evidence_refs": "A",
    },
    "observation_evidence": {
        "schema_version": "N",
        "evidence_id": "N",
        "evidence_position": "N",
        "timestamp": "N",
        "target": "N",
        "difference_ref": "C",  # kind difference -- never Store-persisted
        "before_state": "N",
        "observation_method": "N",  # embeds method_ref, kind observation_method -- C
        "change_identity": "C",  # kind change -- never Store-persisted
        "authority_used": "C",  # kind authority_decision -- never Store-persisted
        "after_state": "N",
        "expected_result": "N",
        "observed_result": "E",  # observation_ref (A), normalized_fact_refs (C)
        "status": "N",
        "artifact_references": "E",  # each member's own optional source_snapshot_ref (A)
        "lineage": "E",  # derived_from (A), predecessor_evidence_refs (A)
        "remaining_differences": "C",  # kind difference -- never Store-persisted
        "evidence_level": "N",
        "evidence_semantic_fingerprint": "N",
    },
    "source_snapshot": {
        "schema_version": "N",
        "source_snapshot_id": "N",
        "source_locator": "N",
        "content_digest": "N",
        "captured_at": "N",
        "git_provenance": "N",
    },
    "difference_event": {
        "schema_version": "N",
        "difference_event_id": "N",
        "difference_id": "N",
        "event_kind": "N",
        "event_revision": "N",
        "previous_event_id": "A",
        "from_status": "N",
        "to_status": "N",
        "state_revision_evaluated": "N",
        "state_fingerprint_evaluated": "N",
        "reason_code": "N",
        "reason": "N",
        "blocker_kind": "N",
        "blocker_scope": "N",  # affected_subject_refs is kind difference -- C, not Store-owned
        "blocker_resolution_condition": "N",  # verification_request_ref: next_observation_request -- C
        "observation_refs": "A",
        "evidence_refs": "A",
        "authority_ref": "C",  # kind authority_decision -- never Store-persisted
        "change_refs": "C",  # kind change -- never Store-persisted
        "closure_evaluation_ref": "A",
        "reflow_transition_ref": "B",
        "next_observation_ref": "C",  # kind next_observation_request -- never Store-persisted
        "reopen_trigger": "N",
        # P8-R4-C3-F1: reclassified from D to C -- unlike revoked/invalid/contradiction_
        # evidence_refs (which resolve to Store-owned observation_evidence once populated),
        # these two fields' own target kinds (target_predicate/reopen_condition_evaluation,
        # difference.graph's own REFERENCE_EDGES confirms both) are never Store-owned
        # regardless of population, so "D" (would-be-A-if-populated) does not describe them.
        "reopen_condition_ref": "C",  # kind target_predicate -- never Store-persisted
        "reopen_condition_evaluation_ref": "C",  # kind reopen_condition_evaluation -- never Store-persisted
        "revoked_evidence_refs": "D",  # CLOSURE_EVIDENCE_REVOKED never implemented
        "invalid_evidence_refs": "D",  # CLOSURE_EVIDENCE_INVALID never implemented
        "contradiction_evidence_refs": "A",  # MATERIAL_CONTRADICTION/OBSERVATION_CONTRADICTION
    },
    "closure_evaluation": {
        "schema_version": "N",
        "closure_evaluation_id": "N",
        "difference_id": "N",
        "evaluation_mode": "N",
        "base_kernel_source_ref_evaluated": "N",  # git_tree_ref -- not reference.schema.json-shaped
        "kernel_source_ref_evaluated": "N",  # same
        "kernel_source_witness_ref": "A",
        "difference_event_head_ref": "A",
        "target_predicate_ref": "C",  # kind target_predicate -- never Store-persisted
        "objective_revision_ref_evaluated": "C",  # kind objective_revision -- never Store-persisted
        "objective_semantic_fingerprint_evaluated": "N",
        "before_state_ref": "B",
        "resolution_mode": "N",
        "change_refs": "C",  # kind change -- never Store-persisted
        "policy_ref": "C",  # kind closure_policy -- never Store-persisted
        "evaluated_state_revision": "N",
        "evaluated_state_fingerprint": "N",
        "after_state_candidate": "E",  # its own source_snapshot_refs (A), producing_change_refs (C)
        "after_observation_refs": "A",
        "change_result_evidence_refs": "A",
        "change_free_verification_evidence_refs": "A",
        "verification_independence_ref": "N",  # schema const null, always absent
        "evidence_sufficiency_ref": "A",
        "terminal_reason_evidence_refs": "A",
        "candidate_invariant_evaluation_bindings": "E",
        "candidate_claim_evaluation_bindings": "E",
        "contradiction_refs": "C",  # kind material_contradiction/normalized_fact -- never Store-persisted
        "evaluated_at": "N",
        "evaluation_expires_at": "N",
        "policy_version_evaluated": "N",
        "policy_semantic_fingerprint_evaluated": "N",
        "proposed_terminal_status": "N",
        "gate_results": "N",
        "result": "N",
        "failure_reasons": "N",
        "reflow_transition_ref": "B",
    },
    "evidence_sufficiency_result": {
        "schema_version": "N",
        "evidence_sufficiency_id": "N",
        "difference_ref": "C",  # kind difference -- never Store-persisted
        "policy_ref": "C",  # kind closure_policy -- never Store-persisted
        "evidence_level": "N",
        "evidence_refs": "A",
        "result": "N",
        "evaluated_at": "N",
    },
    "kernel_source_witness": {
        "schema_version": "N",
        "kernel_source_witness_id": "N",
        "commit_sha": "N",
        "tree_sha": "N",
        "blob_sha": "N",
        "path": "N",
        "commit_object": "N",
        "tree_objects": "N",
        "blob_object": "N",
    },
    "invariant_evaluation": {
        "schema_version": "N",
        "evaluation_id": "N",
        "invariant_id": "N",
        "subject_ref": "C",  # kind difference/objective_revision/state -- never Store-persisted
        "state_revision": "N",
        "state_fingerprint": "N",
        "candidate_id": "N",
        "candidate_semantic_fingerprint": "N",
        "verification_stage": "N",
        "method": "N",
        "expected": "N",
        "observed": "N",
        "status": "N",
        "evaluated_at": "N",
        "evaluator_capability": "N",
        "authority_ref": "C",  # kind authority_decision -- never Store-persisted (always null)
        "evidence_refs": "A",
        "remaining_differences": "C",  # kind difference -- never Store-persisted
    },
    "candidate_claim_evaluation_event": {
        "schema_version": "N",
        "kind": "N",
        "event_id": "N",
        "evaluation_series_id": "N",
        "event_revision": "N",
        "predecessor_event_ref": "A",
        "difference_id": "N",
        "policy_ref": "C",  # kind closure_policy -- never Store-persisted
        "candidate_id": "N",
        "required_claim_ref": "C",  # kind completion_claim -- never Store-persisted
        "completion_record_ref": "A",
        "completion_record_fingerprint": "N",
        "evaluation_status": "N",
        "recorded_at": "N",
    },
    "candidate_completion_record": {
        "schema_version": "N",
        "completion_id": "N",
        "subject_type": "N",
        "subject_ref": "C",  # kind difference/objective_revision -- never Store-persisted
        "claim": "N",
        "target_state_ref": "B",
        "observed_state_ref": "B",
        "closure_policy_ref": "C",  # kind closure_policy -- never Store-persisted
        "required_evidence_refs": "A",
        "invariant_evaluation_refs": "A",
        "material_contradiction_refs": "C",  # kind material_contradiction -- never Store-persisted
        "evaluation_status": "N",
        "evaluated_state_revision": "N",
        "evaluated_state_fingerprint": "N",
        "evaluated_at": "N",
        "reflow_transition_ref": "B",
    },
}


def _schema_required_fields(kind: str) -> set[str]:
    path = SCHEMA_ROOT / _SCHEMA_FILE_FOR_KIND[kind]
    document = json.loads(path.read_text(encoding="utf-8"))
    return set(document["required"])


@pytest.mark.parametrize("kind", sorted(_SCHEMA_FILE_FOR_KIND))
def test_every_schema_required_field_is_classified_exactly_once(kind: str) -> None:
    """The classification table's own key set for *kind* is exactly the live schema's own
    ``required`` field set -- neither missing a field the schema actually declares
    (``UNCLASSIFIED_REFERENCE_FIELD_COUNT=0``) nor carrying a stale one the schema no longer
    requires."""

    assert set(_REQUIRED_FIELD_CLASSIFICATION[kind]) == _schema_required_fields(kind)


def _edge_pairs(edges: Any) -> set[tuple[str, str]]:
    """``reference_edges`` returns :class:`~manosube_agent_civilization.reflow.
    reference_registry.TypedReferenceEdge` objects, not bare ``(kind, id)`` tuples
    (``BARE_KIND_ID_TUPLE_SUFFICIENT=false``) -- this converts a batch to the pair set every
    test below that only cares about *which* edges were produced compares against."""

    return {(edge.target_kind, edge.target_id) for edge in edges}


def test_every_persisted_record_kind_is_inventoried() -> None:
    """Every kind this repository's Reflow ``route.py`` actually persists (confirmed above,
    against real ``records[...] =``/``_merge_verified_record`` call sites, never assumed) is
    covered by this file's own inventory, and the production registry's own
    ``STORE_OWNED_REFERENCE_KINDS`` recognizes exactly this same set as valid reference
    *targets* -- the same ten kinds, both directions."""

    assert set(_SCHEMA_FILE_FOR_KIND) == STORE_OWNED_REFERENCE_KINDS


# --- P8-R4-C3-F1: independent field -> expected-target-kind(s) table --------------------- #
#
# Hand-authored, cross-cited against manosube_agent_civilization.difference.graph's own
# REFERENCE_EDGES (an already-adopted, schema-cross-validated typed registry for the
# identical field names on difference_lifecycle_event/closure_evaluation -- the same schema
# shapes this vertical's own difference_event/closure_evaluation persist) and, where that
# module does not describe the field (observation_evidence's own lineage/artifact_references,
# owned by the Evidence element rather than Difference's emitted bundle), directly against
# evidence/engine.py's own producer code (its _lineage() call sites, EVIDENCE_REFERENCE_KIND,
# and the schema's own const-pinned evidence_reference/artifact_reference shapes) -- never
# derived from, or by trusting, reference_registry.py's own table.
_EXPECTED_TARGET_KINDS: dict[tuple[str, str], frozenset[str]] = {
    ("observation", "source_snapshot_refs[]"): frozenset({"source_snapshot"}),
    ("observation", "observation_evidence_refs[]"): frozenset({"observation_evidence"}),
    ("observation_evidence", "observed_result.observation_ref"): frozenset({"observation"}),
    ("observation_evidence", "lineage.derived_from.members[]"): frozenset(
        {"observation", "difference", "change", "authority_decision"}
    ),
    ("observation_evidence", "lineage.predecessor_evidence_refs.members[]"): frozenset(
        {"observation_evidence"}
    ),
    ("observation_evidence", "artifact_references.members[].source_snapshot_ref"): frozenset(
        {"source_snapshot"}
    ),
    ("closure_evaluation", "kernel_source_witness_ref"): frozenset({"kernel_source_witness"}),
    ("closure_evaluation", "difference_event_head_ref"): frozenset({"difference_event"}),
    ("closure_evaluation", "after_state_candidate.source_snapshot_refs.members[]"): frozenset(
        {"source_snapshot"}
    ),
    ("closure_evaluation", "after_observation_refs[]"): frozenset({"observation"}),
    ("closure_evaluation", "change_result_evidence_refs[]"): frozenset({"observation_evidence"}),
    ("closure_evaluation", "change_free_verification_evidence_refs[]"): frozenset(
        {"observation_evidence"}
    ),
    ("closure_evaluation", "evidence_sufficiency_ref"): frozenset({"evidence_sufficiency_result"}),
    ("closure_evaluation", "terminal_reason_evidence_refs[]"): frozenset({"observation_evidence"}),
    ("closure_evaluation", "contradiction_refs[]"): frozenset(
        {"material_contradiction", "normalized_fact"}
    ),
    (
        "closure_evaluation",
        "candidate_invariant_evaluation_bindings[].invariant_evaluation_ref",
    ): frozenset({"invariant_evaluation"}),
    (
        "closure_evaluation",
        "candidate_invariant_evaluation_bindings[].evaluation_evidence_refs.members[]",
    ): frozenset({"observation_evidence", "negative_evidence"}),
    (
        "closure_evaluation",
        "candidate_claim_evaluation_bindings[].evaluation_head_event_ref",
    ): frozenset({"candidate_claim_evaluation_event"}),
    (
        "closure_evaluation",
        "candidate_claim_evaluation_bindings[].completion_record_ref",
    ): frozenset({"candidate_completion_record"}),
    (
        "closure_evaluation",
        "candidate_claim_evaluation_bindings[].evaluation_evidence_refs.members[]",
    ): frozenset({"observation_evidence", "negative_evidence"}),
    ("difference_event", "previous_event_id"): frozenset({"difference_event"}),
    ("difference_event", "observation_refs[]"): frozenset({"observation"}),
    ("difference_event", "evidence_refs[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    ("difference_event", "closure_evaluation_ref"): frozenset({"closure_evaluation"}),
    ("difference_event", "revoked_evidence_refs[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    ("difference_event", "invalid_evidence_refs[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    ("difference_event", "contradiction_evidence_refs[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    ("evidence_sufficiency_result", "evidence_refs.members[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    ("invariant_evaluation", "evidence_refs.members[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    ("candidate_claim_evaluation_event", "predecessor_event_ref"): frozenset(
        {"candidate_claim_evaluation_event"}
    ),
    ("candidate_claim_evaluation_event", "completion_record_ref"): frozenset(
        {"candidate_completion_record"}
    ),
    ("candidate_completion_record", "required_evidence_refs.members[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    ("candidate_completion_record", "invariant_evaluation_refs.members[]"): frozenset(
        {"invariant_evaluation"}
    ),
}


def test_every_expected_target_kind_matches_the_production_registry() -> None:
    """This file's own independently-authored :data:`_EXPECTED_TARGET_KINDS` agrees with the
    production registry's own ``FIELD_EXPECTED_TARGET_KINDS``, in both directions --
    ``REGISTRY_FIELD_PATH_COUNT_EQUALS_CLASSIFICATION_A_PATH_COUNT=true``,
    ``REGISTRY_OMITTED_TYPED_FIELD_COUNT=0``, ``REGISTRY_EXTRA_TYPED_FIELD_COUNT=0``."""

    production = reference_registry.FIELD_EXPECTED_TARGET_KINDS
    omitted = set(_EXPECTED_TARGET_KINDS) - set(production)
    extra = set(production) - set(_EXPECTED_TARGET_KINDS)
    assert omitted == set(), f"production registry omits: {sorted(omitted)}"
    assert extra == set(), f"production registry carries undeclared extra fields: {sorted(extra)}"
    mismatched = {
        key: (_EXPECTED_TARGET_KINDS[key], production[key])
        for key in _EXPECTED_TARGET_KINDS
        if _EXPECTED_TARGET_KINDS[key] != production[key]
    }
    assert mismatched == {}, f"kind-set disagreement: {mismatched}"


def test_every_classification_a_field_has_an_expected_target_kind_entry() -> None:
    """Every classification-A (or A-in-shape, D-in-practice) top-level field named by
    :data:`_REQUIRED_FIELD_CLASSIFICATION` is the root of at least one
    :data:`_EXPECTED_TARGET_KINDS` entry (an E-classified field satisfies this through its
    own recursively-classified leaf paths), and every ``_EXPECTED_TARGET_KINDS`` entry's own
    root field is classified A/D/E (never a C/N/B field that should carry no expected kind at
    all) -- ``EVERY_CLASSIFICATION_A_FIELD_HAS_EXPECTED_TARGET_KIND=true``,
    ``UNCLASSIFIED_EXPECTED_TARGET_KIND_COUNT=0``."""

    def root(field_path: str) -> str:
        for sep in (".", "["):
            index = field_path.find(sep)
            if index != -1:
                field_path = field_path[:index]
        return field_path

    for kind, fields in _REQUIRED_FIELD_CLASSIFICATION.items():
        for field, classification in fields.items():
            if classification not in ("A", "D", "E"):
                continue
            assert any(sk == kind and root(fp) == field for sk, fp in _EXPECTED_TARGET_KINDS), (
                f"{kind}.{field} is classified {classification} but has no expected-target-kind entry"
            )
    for source_kind, field_path in _EXPECTED_TARGET_KINDS:
        field = root(field_path)
        classification = _REQUIRED_FIELD_CLASSIFICATION[source_kind].get(field)
        # "C" is included deliberately: closure_evaluation.contradiction_refs is a field this
        # registry structurally walks (checking every reference's own kind against its
        # permitted set) even though every permitted kind is external -- classified-and-
        # checked, not merely classified. Only B (a different resolution mechanism entirely)
        # and N (not a reference at all) may never carry an expected-target-kind entry.
        assert classification in ("A", "C", "D", "E"), (
            f"{source_kind}.{field_path} has an expected-target-kind entry but its own "
            f"top-level field is classified {classification!r}, not A/C/D/E"
        )


def _owned_kind_for(source_kind: str, field_path: str) -> str:
    """The one Store-owned kind this field's own allowed set contains -- every field this is
    called for has exactly one (fields with zero, e.g. ``contradiction_refs[]``, are tested
    separately below, never through this positive-edge helper)."""

    owned = sorted(
        kind
        for kind in _EXPECTED_TARGET_KINDS[(source_kind, field_path)]
        if kind in STORE_OWNED_REFERENCE_KINDS
    )
    assert len(owned) == 1, (
        f"{source_kind}.{field_path} has {len(owned)} Store-owned kinds in its allowed set, "
        "expected exactly one for this helper"
    )
    return owned[0]


def _place(source_kind: str, field_path: str, ref: Any) -> dict[str, Any]:
    """Build the minimal record body of *source_kind* that carries *ref* at *field_path* --
    the same path convention :data:`_EXPECTED_TARGET_KINDS` and the production registry both
    use. Every other field is simply absent; ``reference_edges`` treats an absent field as
    empty/``None`` throughout, so a minimal single-field body is a true, uncontaminated
    minimal pair for the one field under test."""

    placers: dict[tuple[str, str], Any] = {
        ("observation", "source_snapshot_refs[]"): lambda r: {"source_snapshot_refs": [r]},
        ("observation", "observation_evidence_refs[]"): lambda r: {
            "observation_evidence_refs": [r]
        },
        ("observation_evidence", "observed_result.observation_ref"): lambda r: {
            "observed_result": {"observation_ref": r}
        },
        ("observation_evidence", "lineage.derived_from.members[]"): lambda r: {
            "lineage": {"derived_from": {"members": [r]}}
        },
        ("observation_evidence", "lineage.predecessor_evidence_refs.members[]"): lambda r: {
            "lineage": {"predecessor_evidence_refs": {"members": [r]}}
        },
        (
            "observation_evidence",
            "artifact_references.members[].source_snapshot_ref",
        ): lambda r: {"artifact_references": {"members": [{"source_snapshot_ref": r}]}},
        ("closure_evaluation", "kernel_source_witness_ref"): lambda r: {
            "kernel_source_witness_ref": r
        },
        ("closure_evaluation", "difference_event_head_ref"): lambda r: {
            "difference_event_head_ref": r
        },
        (
            "closure_evaluation",
            "after_state_candidate.source_snapshot_refs.members[]",
        ): lambda r: {"after_state_candidate": {"source_snapshot_refs": {"members": [r]}}},
        ("closure_evaluation", "after_observation_refs[]"): lambda r: {
            "after_observation_refs": [r]
        },
        ("closure_evaluation", "change_result_evidence_refs[]"): lambda r: {
            "change_result_evidence_refs": [r]
        },
        ("closure_evaluation", "change_free_verification_evidence_refs[]"): lambda r: {
            "change_free_verification_evidence_refs": [r]
        },
        ("closure_evaluation", "evidence_sufficiency_ref"): lambda r: {
            "evidence_sufficiency_ref": r
        },
        ("closure_evaluation", "terminal_reason_evidence_refs[]"): lambda r: {
            "terminal_reason_evidence_refs": [r]
        },
        ("closure_evaluation", "contradiction_refs[]"): lambda r: {"contradiction_refs": [r]},
        (
            "closure_evaluation",
            "candidate_invariant_evaluation_bindings[].invariant_evaluation_ref",
        ): lambda r: {"candidate_invariant_evaluation_bindings": [{"invariant_evaluation_ref": r}]},
        (
            "closure_evaluation",
            "candidate_invariant_evaluation_bindings[].evaluation_evidence_refs.members[]",
        ): lambda r: {
            "candidate_invariant_evaluation_bindings": [
                {"evaluation_evidence_refs": {"members": [r]}}
            ]
        },
        (
            "closure_evaluation",
            "candidate_claim_evaluation_bindings[].evaluation_head_event_ref",
        ): lambda r: {"candidate_claim_evaluation_bindings": [{"evaluation_head_event_ref": r}]},
        (
            "closure_evaluation",
            "candidate_claim_evaluation_bindings[].completion_record_ref",
        ): lambda r: {"candidate_claim_evaluation_bindings": [{"completion_record_ref": r}]},
        (
            "closure_evaluation",
            "candidate_claim_evaluation_bindings[].evaluation_evidence_refs.members[]",
        ): lambda r: {
            "candidate_claim_evaluation_bindings": [{"evaluation_evidence_refs": {"members": [r]}}]
        },
        ("difference_event", "observation_refs[]"): lambda r: {"observation_refs": [r]},
        ("difference_event", "evidence_refs[]"): lambda r: {"evidence_refs": [r]},
        ("difference_event", "closure_evaluation_ref"): lambda r: {"closure_evaluation_ref": r},
        ("difference_event", "revoked_evidence_refs[]"): lambda r: {"revoked_evidence_refs": [r]},
        ("difference_event", "invalid_evidence_refs[]"): lambda r: {"invalid_evidence_refs": [r]},
        ("difference_event", "contradiction_evidence_refs[]"): lambda r: {
            "contradiction_evidence_refs": [r]
        },
        ("evidence_sufficiency_result", "evidence_refs.members[]"): lambda r: {
            "evidence_refs": {"members": [r]}
        },
        ("invariant_evaluation", "evidence_refs.members[]"): lambda r: {
            "evidence_refs": {"members": [r]}
        },
        ("candidate_claim_evaluation_event", "predecessor_event_ref"): lambda r: {
            "predecessor_event_ref": r
        },
        ("candidate_claim_evaluation_event", "completion_record_ref"): lambda r: {
            "completion_record_ref": r
        },
        ("candidate_completion_record", "required_evidence_refs.members[]"): lambda r: {
            "required_evidence_refs": {"members": [r]}
        },
        ("candidate_completion_record", "invariant_evaluation_refs.members[]"): lambda r: {
            "invariant_evaluation_refs": {"members": [r]}
        },
    }
    placer = placers.get((source_kind, field_path))
    assert placer is not None, f"no minimal-body placer registered for {source_kind}.{field_path}"
    return placer(ref)


#: previous_event_id is excluded from the generic per-field kind tests below: it is a bare
#: id string, not a {kind, id} reference -- its own field semantics fix the target kind to
#: difference_event unconditionally, with no self-declared kind to substitute a wrong one
#: into. Its own dedicated coverage is in the difference_event edge-coverage test further
#: down.
_GENERIC_FIELD_PATHS = sorted(
    k for k in _EXPECTED_TARGET_KINDS if k != ("difference_event", "previous_event_id")
)
#: The subset with at least one Store-owned permitted kind -- the only ones a positive,
#: edge-producing sentinel can be built for. ``closure_evaluation.contradiction_refs[]`` is
#: the one field whose entire permitted set is external; its own positive (accepted, no edge)
#: proof is a dedicated test below.
_POSITIVE_FIELD_PATHS = [
    key
    for key in _GENERIC_FIELD_PATHS
    if any(kind in STORE_OWNED_REFERENCE_KINDS for kind in _EXPECTED_TARGET_KINDS[key])
]


@pytest.mark.parametrize("source_kind,field_path", _POSITIVE_FIELD_PATHS)
def test_right_kind_right_id_produces_exactly_that_edge(source_kind: str, field_path: str) -> None:
    """SHUKOU section 7.2's first minimal pair: a reference naming this field's own real,
    permitted, Store-owned kind and a real id produces exactly that edge."""

    owned_kind = _owned_kind_for(source_kind, field_path)
    ref = {"kind": owned_kind, "id": f"RIGHT-{field_path}"}
    body = _place(source_kind, field_path, ref)
    edges = reference_edges(source_kind, body)
    assert (owned_kind, ref["id"]) in {(edge.target_kind, edge.target_id) for edge in edges}


@pytest.mark.parametrize("source_kind,field_path", _GENERIC_FIELD_PATHS)
def test_wrong_kind_same_id_fails_closed(source_kind: str, field_path: str) -> None:
    """SHUKOU section 7.2's second minimal pair, and P8-R4-C3-F1's own exact shape: a
    reference naming a real, existing Store-owned kind this field does not permit is refused
    before ``reference_edges`` ever returns an edge for it -- never silently accepted merely
    because the kind is real and Store-owned *somewhere*."""

    allowed = _EXPECTED_TARGET_KINDS[(source_kind, field_path)]
    wrong_kind = sorted(STORE_OWNED_REFERENCE_KINDS - allowed)[0]
    ref = {"kind": wrong_kind, "id": "WRONG-KIND-SAME-ID"}
    body = _place(source_kind, field_path, ref)
    with pytest.raises(ReflowValidationError, match="not permitted here"):
        reference_edges(source_kind, body)


@pytest.mark.parametrize(
    "source_kind,field_path",
    [key for key in _GENERIC_FIELD_PATHS if len(_EXPECTED_TARGET_KINDS[key]) > 1],
)
def test_allowed_but_external_kind_is_accepted_and_emits_no_edge(
    source_kind: str, field_path: str
) -> None:
    """A field admitting more than one kind (e.g. ``evidence_refs``'s own
    ``observation_evidence``/``negative_evidence`` pair) accepts every kind its own allowed
    set names -- including the one(s) that are not Store-owned, which are valid there and
    correctly produce no edge, never a raise."""

    allowed = _EXPECTED_TARGET_KINDS[(source_kind, field_path)]
    external_kinds = sorted(allowed - STORE_OWNED_REFERENCE_KINDS)
    assert external_kinds, f"{source_kind}.{field_path} has no external kind to test"
    for external_kind in external_kinds:
        ref = {"kind": external_kind, "id": f"EXTERNAL-{field_path}"}
        body = _place(source_kind, field_path, ref)
        edges = reference_edges(source_kind, body)
        assert ref["id"] not in {edge.target_id for edge in edges}


def test_previous_event_id_is_bare_and_always_expects_difference_event() -> None:
    """The one field this module's generic per-field tests above deliberately exclude: a
    bare id string, not a ``{kind, id}`` object -- its own field semantics fix the target
    kind unconditionally, so there is no self-declared kind to substitute a wrong one into."""

    body = {"previous_event_id": "D-EVT-" + "1" * 64}
    edges = reference_edges("difference_event", body)
    assert ("difference_event", body["previous_event_id"]) in {
        (edge.target_kind, edge.target_id) for edge in edges
    }


def _sentinel(field: str, index: int = 0) -> dict[str, str]:
    """One distinct, syntactically valid ``observation_evidence`` reference for building
    whole-record base bodies below -- a unique id per *field* (and *index*, for a field
    admitting more than one member)."""

    return {"kind": "observation_evidence", "id": f"EVIDENCE-{field.upper()}-{index:02d}"}


def _members(field: str, count: int = 1) -> dict[str, Any]:
    return {
        "collection_kind": "UNORDERED_SET",
        "members": [_sentinel(field, index) for index in range(count)],
    }


# --- difference_event: every classification-A field actually contributes its own edge ---- #


def _base_difference_event_body() -> dict[str, Any]:
    """A body naming a syntactically valid, non-Store-owned or scalar value for every
    classification-C/D/N field (so mutating one classification-A field at a time is a true
    minimal pair, never coincidentally satisfied by a neighboring field), and the real
    genesis self-reference plus every other classification-A field's own field-correct
    sentinel."""

    return {
        "previous_event_id": "D-EVT-" + "1" * 64,
        "observation_refs": [{"kind": "observation", "id": "OBS-" + "3" * 64}],
        "evidence_refs": [_sentinel("evidence_refs")],
        "authority_ref": {"kind": "authority_decision", "id": "AUTH-DEC-1"},
        "change_refs": [{"kind": "change", "id": "CHANGE-" + "2" * 64}],
        "closure_evaluation_ref": {"kind": "closure_evaluation", "id": "CLOSURE-EVAL-0001"},
        "reflow_transition_ref": {"kind": "state_transition", "id": "TX-0001"},
        "next_observation_ref": {"kind": "next_observation_request", "id": "OBS-REQ-1"},
        "reopen_condition_ref": None,
        "reopen_condition_evaluation_ref": None,
        "revoked_evidence_refs": [],
        "invalid_evidence_refs": [],
        "contradiction_evidence_refs": [_sentinel("contradiction_evidence_refs")],
    }


def test_difference_event_edges_cover_every_classification_a_field_and_nothing_else() -> None:
    body = _base_difference_event_body()
    edges = _edge_pairs(reference_edges("difference_event", body))
    assert edges == {
        ("difference_event", body["previous_event_id"]),
        ("observation", body["observation_refs"][0]["id"]),
        ("observation_evidence", body["evidence_refs"][0]["id"]),
        ("closure_evaluation", body["closure_evaluation_ref"]["id"]),
        ("observation_evidence", body["contradiction_evidence_refs"][0]["id"]),
    }
    # Removing any one classification-A field's own sentinel removes exactly its own edge,
    # never any other -- proving each field is independently load-bearing, not merely
    # coincidentally covered by another field's own scan.
    for field in (
        "observation_refs",
        "evidence_refs",
        "closure_evaluation_ref",
        "contradiction_evidence_refs",
    ):
        mutated = dict(body)
        if isinstance(mutated[field], list):
            mutated[field] = []
        else:
            mutated[field] = None
        reduced = _edge_pairs(reference_edges("difference_event", mutated))
        assert reduced == edges - {edge for edge in edges if edge[1] in json.dumps(body[field])}


def test_difference_event_never_walks_a_classification_c_or_d_field() -> None:
    """A syntactically Store-owned-*shaped* reference planted on a classification-C field
    (``authority_ref``/``change_refs``/``next_observation_ref``) is never walked -- proving
    the exclusion is deliberate (a real kind this registry recognizes, simply never reached
    from this field), not an accident of the sentinel target kind chosen above."""

    body = _base_difference_event_body()
    body["authority_ref"] = _sentinel("authority_ref")
    body["change_refs"] = [_sentinel("change_refs")]
    body["next_observation_ref"] = _sentinel("next_observation_ref")
    edges = _edge_pairs(reference_edges("difference_event", body))
    assert ("observation_evidence", "EVIDENCE-AUTHORITY_REF-00") not in edges
    assert ("observation_evidence", "EVIDENCE-CHANGE_REFS-00") not in edges
    assert ("observation_evidence", "EVIDENCE-NEXT_OBSERVATION_REF-00") not in edges


def test_difference_event_deferred_reopen_fields_resolve_when_present() -> None:
    """``revoked_evidence_refs``/``invalid_evidence_refs`` are classification A *in shape*
    (D only because no production code path currently populates them) -- if a future reopen
    extension ever does, this proves the registry already walks them correctly today, not
    only after some future change."""

    body = _base_difference_event_body()
    body["revoked_evidence_refs"] = [_sentinel("revoked_evidence_refs")]
    body["invalid_evidence_refs"] = [_sentinel("invalid_evidence_refs")]
    edges = _edge_pairs(reference_edges("difference_event", body))
    assert ("observation_evidence", "EVIDENCE-REVOKED_EVIDENCE_REFS-00") in edges
    assert ("observation_evidence", "EVIDENCE-INVALID_EVIDENCE_REFS-00") in edges


# --- closure_evaluation: every classification-A field, including recursive E fields ------- #


def _base_closure_evaluation_body() -> dict[str, Any]:
    return {
        "kernel_source_witness_ref": {"kind": "kernel_source_witness", "id": "KSW-0001"},
        "difference_event_head_ref": {"kind": "difference_event", "id": "D-EVT-" + "9" * 64},
        "after_state_candidate": {
            "source_snapshot_refs": {
                "collection_kind": "UNORDERED_SET",
                "members": [
                    {"kind": "source_snapshot", "id": "SRC-SNAP-" + "3" * 64},
                ],
            },
            "producing_change_refs": {
                "collection_kind": "UNORDERED_SET",
                "members": [{"kind": "change", "id": "CHANGE-" + "4" * 64}],
            },
        },
        "after_observation_refs": [{"kind": "observation", "id": "OBS-" + "5" * 64}],
        "change_result_evidence_refs": [_sentinel("change_result_evidence_refs")],
        "change_free_verification_evidence_refs": [
            _sentinel("change_free_verification_evidence_refs")
        ],
        "evidence_sufficiency_ref": {"kind": "evidence_sufficiency_result", "id": "EVID-SUFF-0001"},
        "terminal_reason_evidence_refs": [_sentinel("terminal_reason_evidence_refs")],
        "contradiction_refs": [{"kind": "material_contradiction", "id": "CONTRA-1"}],
        "candidate_invariant_evaluation_bindings": [
            {
                "invariant_ref": {"kind": "kernel_invariant", "id": "K-001"},
                "invariant_evaluation_ref": {"kind": "invariant_evaluation", "id": "INV-EVAL-0001"},
                "evaluation_evidence_refs": _members("cand_inv_evidence_refs"),
            }
        ],
        "candidate_claim_evaluation_bindings": [
            {
                "required_claim_ref": {"kind": "completion_claim", "id": "CLAIM-0001"},
                "evaluation_head_event_ref": {
                    "kind": "candidate_claim_evaluation_event",
                    "id": "CAND-CLAIM-EVT-0001",
                },
                "completion_record_ref": {
                    "kind": "candidate_completion_record",
                    "id": "CMP-0001",
                },
                "evaluation_evidence_refs": _members("cand_claim_evidence_refs"),
            }
        ],
    }


def test_closure_evaluation_edges_cover_every_classification_a_field() -> None:
    body = _base_closure_evaluation_body()
    edges = _edge_pairs(reference_edges("closure_evaluation", body))
    assert edges == {
        ("kernel_source_witness", body["kernel_source_witness_ref"]["id"]),
        ("difference_event", body["difference_event_head_ref"]["id"]),
        ("source_snapshot", "SRC-SNAP-" + "3" * 64),
        ("observation", body["after_observation_refs"][0]["id"]),
        ("observation_evidence", body["change_result_evidence_refs"][0]["id"]),
        ("observation_evidence", body["change_free_verification_evidence_refs"][0]["id"]),
        ("evidence_sufficiency_result", body["evidence_sufficiency_ref"]["id"]),
        ("observation_evidence", body["terminal_reason_evidence_refs"][0]["id"]),
        (
            "invariant_evaluation",
            body["candidate_invariant_evaluation_bindings"][0]["invariant_evaluation_ref"]["id"],
        ),
        (
            "observation_evidence",
            body["candidate_invariant_evaluation_bindings"][0]["evaluation_evidence_refs"][
                "members"
            ][0]["id"],
        ),
        (
            "candidate_claim_evaluation_event",
            body["candidate_claim_evaluation_bindings"][0]["evaluation_head_event_ref"]["id"],
        ),
        (
            "candidate_completion_record",
            body["candidate_claim_evaluation_bindings"][0]["completion_record_ref"]["id"],
        ),
        (
            "observation_evidence",
            body["candidate_claim_evaluation_bindings"][0]["evaluation_evidence_refs"]["members"][
                0
            ]["id"],
        ),
    }


def test_closure_evaluation_never_walks_a_classification_c_field() -> None:
    """``contradiction_refs`` names ``material_contradiction``/``normalized_fact`` records in
    real production output -- neither is a kind this registry recognizes as Store-owned. A
    real, correctly-kinded ``material_contradiction`` reference planted there must never
    resolve to an edge, proving the exclusion is live, not merely untested."""

    body = _base_closure_evaluation_body()
    body["contradiction_refs"] = [{"kind": "material_contradiction", "id": "CONTRA-EXTRA"}]
    edges = _edge_pairs(reference_edges("closure_evaluation", body))
    assert ("material_contradiction", "CONTRA-EXTRA") not in edges
    assert not any(ref_id == "CONTRA-EXTRA" for _, ref_id in edges)


def test_closure_evaluation_missing_after_state_candidate_does_not_crash() -> None:
    """A ``TERMINAL_POLICY_ONLY`` evaluation's own ``after_state_candidate`` is schema-null
    -- the recursive walk must tolerate that shape, not assume a dict."""

    body = _base_closure_evaluation_body()
    body["after_state_candidate"] = None
    body["candidate_invariant_evaluation_bindings"] = []
    body["candidate_claim_evaluation_bindings"] = []
    edges = _edge_pairs(reference_edges("closure_evaluation", body))
    assert ("source_snapshot", "SRC-SNAP-" + "3" * 64) not in edges


# --- the four newly-recognized leaf/near-leaf Store-owned target kinds -------------------- #


def test_evidence_sufficiency_result_walks_its_evidence_refs_members() -> None:
    body = {"evidence_refs": _members("sufficiency_evidence_refs", count=2)}
    edges = _edge_pairs(reference_edges("evidence_sufficiency_result", body))
    assert edges == {
        ("observation_evidence", "EVIDENCE-SUFFICIENCY_EVIDENCE_REFS-00"),
        ("observation_evidence", "EVIDENCE-SUFFICIENCY_EVIDENCE_REFS-01"),
    }


def test_invariant_evaluation_walks_its_evidence_refs_members() -> None:
    body = {"evidence_refs": _members("invariant_evidence_refs")}
    edges = _edge_pairs(reference_edges("invariant_evaluation", body))
    assert edges == {("observation_evidence", "EVIDENCE-INVARIANT_EVIDENCE_REFS-00")}


def test_candidate_claim_evaluation_event_walks_predecessor_and_completion_record() -> None:
    body = {
        "predecessor_event_ref": {
            "kind": "candidate_claim_evaluation_event",
            "id": "CAND-CLAIM-EVT-" + "5" * 64,
        },
        "completion_record_ref": {
            "kind": "candidate_completion_record",
            "id": "CMP-" + "6" * 64,
        },
    }
    edges = _edge_pairs(reference_edges("candidate_claim_evaluation_event", body))
    assert edges == {
        ("candidate_claim_evaluation_event", "CAND-CLAIM-EVT-" + "5" * 64),
        ("candidate_completion_record", "CMP-" + "6" * 64),
    }


def test_candidate_claim_evaluation_event_genesis_has_a_null_predecessor() -> None:
    """Revision 0's own ``predecessor_event_ref`` is schema-null -- tolerated, not walked."""

    body = {
        "predecessor_event_ref": None,
        "completion_record_ref": {"kind": "candidate_completion_record", "id": "CMP-" + "7" * 64},
    }
    edges = _edge_pairs(reference_edges("candidate_claim_evaluation_event", body))
    assert edges == {("candidate_completion_record", "CMP-" + "7" * 64)}


def test_candidate_completion_record_walks_both_evidence_reference_collections() -> None:
    body = {
        "required_evidence_refs": _members("completion_required_evidence_refs"),
        "invariant_evaluation_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [{"kind": "invariant_evaluation", "id": "INV-EVAL-" + "8" * 64}],
        },
        "material_contradiction_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [{"kind": "material_contradiction", "id": "CONTRA-2"}],
        },
    }
    edges = _edge_pairs(reference_edges("candidate_completion_record", body))
    assert edges == {
        ("observation_evidence", "EVIDENCE-COMPLETION_REQUIRED_EVIDENCE_REFS-00"),
        ("invariant_evaluation", "INV-EVAL-" + "8" * 64),
    }


@pytest.mark.parametrize("kind", ["source_snapshot", "kernel_source_witness"])
def test_leaf_kinds_never_emit_an_edge(kind: str) -> None:
    """Neither ``source_snapshot`` nor ``kernel_source_witness``'s own canonical schema
    declares any reference field at all -- a maximal, schema-required-only body must
    produce zero edges, proving this is a deliberate leaf classification, not merely an
    unimplemented ``elif`` branch that happens to fall through to an empty default."""

    body = {field: f"irrelevant-{field}" for field in _schema_required_fields(kind)}
    assert reference_edges(kind, body) == []


def test_unknown_source_record_kind_fails_closed_rather_than_returning_no_edges() -> None:
    """A *leaf* kind's legitimate zero-edge result (above) must never be confused with an
    unrecognized kind silently falling through the same way -- ``UNKNOWN_SOURCE_RECORD_KIND``
    is refused before this function returns anything at all."""

    with pytest.raises(ReflowValidationError, match="UNKNOWN_SOURCE_RECORD_KIND"):
        reference_edges("banana", {})


# --- negative control: an intentionally narrowed registry fails this file's own proof ----- #


def test_narrowing_store_owned_reference_kinds_breaks_the_closure_evaluation_edge_proof() -> None:
    """SHUKOU's own required negative control (section 6.1): deliberately excluding one
    Store-owned target kind from ``STORE_OWNED_REFERENCE_KINDS`` -- exactly the shape of
    omission P8-R4-C2-F1 itself found -- must make
    ``test_closure_evaluation_edges_cover_every_classification_a_field``'s own assertion
    fail. Proven here directly against the real, unmodified ``reference_edges`` function
    (never a second, hand-maintained reimplementation) by temporarily narrowing the one
    module-level set that function's own kind-membership check consults, and restoring it
    unconditionally afterward.
    """

    original = reference_registry.STORE_OWNED_REFERENCE_KINDS
    narrowed = original - {"invariant_evaluation"}
    reference_registry.STORE_OWNED_REFERENCE_KINDS = narrowed
    try:
        body = _base_closure_evaluation_body()
        edges = _edge_pairs(reference_edges("closure_evaluation", body))
        expected_invariant_edge = (
            "invariant_evaluation",
            body["candidate_invariant_evaluation_bindings"][0]["invariant_evaluation_ref"]["id"],
        )
        # The omitted kind's own edge silently disappears -- exactly the undetected gap
        # P8-R4-C2-F1 found in production, reproduced here on demand against the real code.
        assert expected_invariant_edge not in edges
    finally:
        reference_registry.STORE_OWNED_REFERENCE_KINDS = original
    # Restored: the full proof passes again, unmodified.
    edges_restored = _edge_pairs(
        reference_edges("closure_evaluation", _base_closure_evaluation_body())
    )
    assert expected_invariant_edge in edges_restored
