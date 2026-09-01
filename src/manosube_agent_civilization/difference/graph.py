"""The typed reference-edge registry and the whole-bundle relational gate.

Four review rounds found the same shape of defect one layer further out: a record reached
the returned bundle because the check that would have caught it covered a *different*
route. ADR-0009 closed caller-supplied predecessor context; ADR-0010 closed derivation
inputs and emitted sections. Both are per-record gates: they decide a record against its
own schema and its own identity, and say nothing about the edges between records.

This module closes that last gap. It states, once, what a reference *is* in the emitted
graph, and applies the rule to every record in every section -- not only to the active
Difference lineage:

```text
RESOLVABLE_KINDS   reference kind -> the emitted section it must resolve in
EXTERNAL_KINDS     reference kinds whose owner is outside this phase (explicit non-claim)
REFERENCE_EDGES    record type -> its named reference fields and their permitted kinds
```

Two passes run over the same registry:

*Structural closure* walks every record and finds every reference-shaped object, wherever
it is nested. A reference kind that is neither resolvable nor declared external fails
closed, so a new reference kind cannot enter the graph unreviewed, and a resolvable kind
must name exactly one record of that kind in its section. Completeness is by construction:
no field list can omit a field, because no field list is consulted.

*Typed edges* pin the kinds a named field may carry, so a schema-valid reference cannot be
substituted with a well-formed reference of the wrong kind -- which structural closure
alone would accept.

The independent contract validator imports this module, so the producer and the auditor
cannot hold two drifting maps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Reference kind -> the returned-bundle section a reference of that kind must resolve in.
#: A kind listed here makes the emitted graph closed under it: every reference carrying the
#: kind must name exactly one record of that kind in that section.
RESOLVABLE_KINDS: dict[str, str] = {
    "difference": "differences",
    "difference_event": "events",
    "supersession_relation": "supersession_relations",
    "closure_policy": "policies",
    "closure_evaluation": "evaluations",
    "next_observation_request": "next_observation_requests",
    "objective_revision": "objective_revisions",
    "observation_scope": "observation_scopes",
    "observation": "observations",
    "normalized_fact": "normalized_facts",
    "fact_observation_binding": "fact_observation_bindings",
    "negative_observation": "negative_observations",
    "reopen_condition_evaluation": "reopen_condition_evaluations",
    "candidate_completion_record": "candidate_completion_records",
    "candidate_claim_evaluation_event": "candidate_claim_evaluation_events",
    "invariant_evaluation": "invariant_evaluations",
    "evidence_sufficiency_result": "evidence_sufficiency_results",
    "change": "changes",
    "reflow_transition": "reflow_transitions",
    "state_transition": "reflow_transitions",
}

#: Reference kinds whose canonical owner is outside the Difference phase. The kind itself
#: is still checked wherever a typed edge pins it, but no record is claimed for it and none
#: is required to travel with the bundle. This is an explicit non-claim, enumerated here so
#: it can be reviewed rather than discovered:
#:
#: * Evidence, source snapshots, State revisions, kernel sources and Change/Reflow subjects
#:   belong to elements this phase does not implement.
#: * ``observation_method`` resolves only where the lifecycle authority requires it (a
#:   Next Observation Request); a Scope's or an Observation's own declared method is the
#:   Observation element's record and is not carried here.
#: * ``target_predicate`` is ambiguous by contract -- it names an Objective Target
#:   Predicate in some fields and a Closure Policy reopen condition in others -- so it is
#:   not resolved structurally. The unambiguous case is decided by the relational rules.
EXTERNAL_KINDS: frozenset[str] = frozenset(
    {
        "observation_evidence",
        "negative_evidence",
        "source_snapshot",
        "observation_method",
        "target_predicate",
        "human_authority",
        "authority",
        "boundary",
        "objective_boundary",
        "objective",
        "execution_boundary",
        "schema",
        "observer_procedure",
        "enumeration_rule",
        "completion_predicate",
        "kernel_source",
        "state",
        "git_blob",
        "git_tree",
        "observation_attempt",
        "blind_spot",
        "invariant",
        "invariant_definition",
        "verification_independence",
        "completion_claim",
        "material_contradiction",
    }
)


@dataclass(frozen=True)
class ReferenceEdge:
    """One named reference field of one record type.

    *path* is a dotted locator; the segment ``[]`` iterates a list and ``members`` reads an
    explicit collection wrapper. *kinds* is the closed set of reference kinds the contract
    permits in that field. *resolve* overrides the structural decision: it forces
    resolution for a field whose kind is otherwise external, and it is never used to
    weaken a resolvable kind -- a contract test proves that.
    """

    path: str
    kinds: frozenset[str]
    resolve: bool | None = None


def _edges(*rows: tuple[Any, ...]) -> tuple[ReferenceEdge, ...]:
    built: list[ReferenceEdge] = []
    for row in rows:
        path, kinds = str(row[0]), frozenset(row[1])
        resolve = row[2] if len(row) == 3 else None
        built.append(ReferenceEdge(path, kinds, resolve))
    return tuple(built)


#: Canonical record type -> its named reference fields. Every emitted and carryable record
#: type appears exactly once; a contract test proves this key set equals the emitted record
#: kinds in both directions, so a newly emitted type cannot enter the graph untyped.
REFERENCE_EDGES: dict[str, tuple[ReferenceEdge, ...]] = {
    "difference": _edges(
        ("objective_revision_ref", ("objective_revision",)),
        ("target_predicate_ref", ("target_predicate",)),
        ("observation_refs[]", ("observation",)),
        ("observation_evidence_refs[]", ("observation_evidence", "negative_evidence")),
        ("genesis_event_ref", ("difference_event",)),
        ("closure_policy", ("closure_policy",)),
        ("objective_scope_binding.scope_ref", ("observation_scope",)),
        ("effective_boundary.scope_ref", ("observation_scope",)),
        ("effective_boundary.source_snapshot_refs.members[]", ("source_snapshot",)),
    ),
    "difference_lifecycle_event": _edges(
        ("observation_refs[]", ("observation",)),
        ("evidence_refs[]", ("observation_evidence", "negative_evidence")),
        ("revoked_evidence_refs[]", ("observation_evidence", "negative_evidence")),
        ("invalid_evidence_refs[]", ("observation_evidence", "negative_evidence")),
        ("contradiction_evidence_refs[]", ("observation_evidence", "negative_evidence")),
        ("authority_ref", ("authority", "human_authority")),
        ("change_refs[]", ("change",)),
        ("closure_evaluation_ref", ("closure_evaluation",)),
        ("next_observation_ref", ("next_observation_request",)),
        ("reflow_transition_ref", ("reflow_transition", "state_transition")),
        ("reopen_condition_ref", ("target_predicate",)),
        ("reopen_condition_evaluation_ref", ("reopen_condition_evaluation",)),
        ("blocker_scope.effective_boundary.scope_ref", ("observation_scope",)),
        (
            "blocker_scope.effective_boundary.source_snapshot_refs.members[]",
            ("source_snapshot",),
        ),
        ("blocker_scope.affected_subject_refs.members[]", ("difference",)),
        ("blocker_resolution_condition.subject_ref", ("difference",)),
        (
            "blocker_resolution_condition.verification_request_ref",
            ("next_observation_request",),
        ),
    ),
    "difference_supersession_relation": _edges(
        ("old_difference_ref", ("difference",)),
        ("new_difference_ref", ("difference",)),
        ("old_terminal_event_ref", ("difference_event",)),
        ("new_genesis_event_ref", ("difference_event",)),
        ("evidence_refs[]", ("observation_evidence", "negative_evidence")),
    ),
    "closure_policy": _edges(
        ("subject_difference_ref", ("difference",)),
        ("target_predicate_ref", ("target_predicate",)),
        ("reopen_conditions[].objective_revision_ref", ("objective_revision",)),
        ("invariant_requirements[].contract_source_ref", ("git_blob",)),
        ("required_completion_claims[].subject_ref", ("difference", "completion_claim")),
        ("required_completion_claims[].target_state_ref", ("state",)),
    ),
    "closure_evaluation": _edges(
        ("difference_event_head_ref", ("difference_event",)),
        ("target_predicate_ref", ("target_predicate",)),
        ("objective_revision_ref_evaluated", ("objective_revision",)),
        ("policy_ref", ("closure_policy",)),
        ("before_state_ref", ("state",)),
        ("kernel_source_ref_evaluated", ("kernel_source", "git_blob", "git_tree")),
        ("after_observation_refs[]", ("observation",)),
        ("change_refs[]", ("change",)),
        ("contradiction_refs[]", ("material_contradiction", "normalized_fact")),
        ("terminal_reason_evidence_refs[]", ("observation_evidence",)),
        ("change_result_evidence_refs[]", ("observation_evidence",)),
        ("change_free_verification_evidence_refs[]", ("observation_evidence",)),
        ("evidence_sufficiency_ref", ("evidence_sufficiency_result",)),
        ("verification_independence_ref", ("verification_independence",)),
        ("reflow_transition_ref", ("reflow_transition", "state_transition")),
        ("after_state_candidate.kernel_source_ref", ("kernel_source", "git_blob", "git_tree")),
        ("after_state_candidate.base_state_ref", ("state",)),
        ("after_state_candidate.source_snapshot_refs.members[]", ("source_snapshot",)),
        ("after_state_candidate.producing_change_refs.members[]", ("change",)),
        ("candidate_claim_bindings[].completion_record_ref", ("candidate_completion_record",)),
        ("candidate_claim_bindings[].required_claim_ref", ("completion_claim",)),
        ("candidate_claim_bindings[].policy_ref", ("closure_policy",)),
        ("candidate_claim_bindings[].base_state_ref", ("state",)),
        (
            "candidate_claim_bindings[].evaluation_head_event_ref",
            ("candidate_claim_evaluation_event",),
        ),
        ("candidate_claim_bindings[].evaluation_evidence_refs[]", ("observation_evidence",)),
        ("candidate_invariant_bindings[].invariant_ref", ("invariant",)),
        ("candidate_invariant_bindings[].invariant_definition_ref", ("invariant_definition",)),
        ("candidate_invariant_bindings[].invariant_evaluation_ref", ("invariant_evaluation",)),
        ("candidate_invariant_bindings[].base_state_ref", ("state",)),
        (
            "candidate_invariant_bindings[].evaluation_evidence_refs[]",
            ("observation_evidence",),
        ),
    ),
    "next_observation_request": _edges(
        ("difference_ref", ("difference",)),
        ("derived_from_event_ref", ("difference_event",)),
        ("target_ref", ("target_predicate",)),
        ("scope_ref", ("observation_scope",)),
        ("method_ref", ("observation_method",), True),
    ),
    "observation_method": _edges(
        ("procedure_ref", ("observer_procedure",)),
        ("execution_boundary_ref", ("execution_boundary",)),
        ("input_contract_ref", ("schema",)),
        ("output_contract_refs.members[]", ("schema",)),
    ),
    "objective_revision": _edges(
        ("owner_authority_ref", ("human_authority",)),
        ("human_authority_ref", ("human_authority",)),
        ("boundary_ref", ("boundary", "objective_boundary")),
        ("previous_objective_ref", ("objective", "objective_revision")),
    ),
    "observation": _edges(
        ("scope_ref", ("observation_scope",)),
        ("method_ref", ("observation_method",)),
        ("normalized_fact_refs[]", ("normalized_fact",)),
        ("observation_evidence_refs[]", ("observation_evidence",)),
        ("source_snapshot_refs[]", ("source_snapshot",)),
        ("attempts[].method_ref", ("observation_method",)),
    ),
    "observation_scope": _edges(
        ("method_ref", ("observation_method",)),
        ("source_snapshot_refs[]", ("source_snapshot",)),
        ("enumeration_rule", ("enumeration_rule",)),
        ("completion_predicate", ("completion_predicate",)),
    ),
    "normalized_fact": _edges(),
    "fact_observation_binding": _edges(
        ("source_ref", ("source_snapshot",)),
    ),
    "fact_evaluation": _edges(
        ("binding_refs[]", ("fact_observation_binding",)),
        ("evidence_refs[]", ("observation_evidence",)),
        ("conflict_fact_refs[]", ("normalized_fact",)),
        ("conflict_negative_observation_refs[]", ("negative_observation",)),
    ),
    "negative_observation": _edges(
        ("scope_ref", ("observation_scope",)),
        ("method_ref", ("observation_method",)),
        ("negative_evidence_refs[]", ("negative_evidence",)),
        ("positive_fact_refs[]", ("normalized_fact",)),
        ("source_snapshot_refs[]", ("source_snapshot",)),
        ("attempt_refs[]", ("observation_attempt",)),
        ("blind_spot_refs[]", ("blind_spot",)),
    ),
    "negative_observation_evaluation": _edges(
        ("evidence_refs[]", ("negative_evidence", "observation_evidence")),
        ("conflict_fact_refs[]", ("normalized_fact",)),
    ),
    "reopen_condition_evaluation": _edges(
        ("difference_ref", ("difference",)),
        ("policy_ref", ("closure_policy",)),
        ("condition_ref", ("target_predicate",)),
        ("evidence_refs.members[]", ("observation_evidence",)),
    ),
    "candidate_completion_record": _edges(
        ("subject_ref", ("difference", "objective_revision")),
        ("closure_policy_ref", ("closure_policy",)),
        ("observed_state_ref", ("state",)),
        ("target_state_ref", ("state",)),
        ("reflow_transition_ref", ("reflow_transition", "state_transition")),
        ("invariant_evaluation_refs[]", ("invariant_evaluation",)),
        ("material_contradiction_refs[]", ("material_contradiction",)),
        ("required_evidence_refs[]", ("observation_evidence",)),
    ),
    "candidate_claim_evaluation_event": _edges(
        ("completion_record_ref", ("candidate_completion_record",)),
        ("required_claim_ref", ("completion_claim",)),
        ("policy_ref", ("closure_policy",)),
        ("predecessor_event_ref", ("candidate_claim_evaluation_event",)),
    ),
    "invariant_evaluation": _edges(
        ("subject_ref", ("difference", "objective_revision", "state")),
        ("authority_ref", ("authority", "human_authority")),
        ("evidence_refs[]", ("observation_evidence",)),
    ),
    "evidence_sufficiency_result": _edges(
        ("difference_ref", ("difference",)),
        ("policy_ref", ("closure_policy",)),
        ("evidence_refs[]", ("observation_evidence",)),
    ),
    # 01_SCHEMA/change/ and 01_SCHEMA/reflow/ are empty in v0.1. No canonical schema names
    # these records' fields, so no typed edge can be declared for them without inventing
    # semantics. Structural closure still applies to whatever references they do carry.
    "change": _edges(),
    "reflow_transaction": _edges(),
}


#: Record type -> its bare foreign-key fields and the section each must resolve in.
#:
#: Not every reference in the canonical record set is reference-shaped. A Closure
#: Evaluation names its subject Difference as a plain ``difference_id`` string, and a Fact
#: Observation Binding names its Fact and its Observation the same way. Structural closure
#: cannot see those -- there is no ``kind`` to read -- so they are declared here and
#: resolved by the same gate. ``project_id`` and the identifiers of records this phase does
#: not own (``invariant_id``, ``candidate_id``, ``source_occurrence_id``,
#: ``evaluation_series_id``) are deliberately absent: they name no record the bundle
#: carries, and inventing an owner for them would be inventing semantics.
IDENTITY_EDGES: dict[str, tuple[tuple[str, str], ...]] = {
    "difference": (),
    "difference_lifecycle_event": (
        ("difference_id", "differences"),
        ("previous_event_id", "events"),
    ),
    "difference_supersession_relation": (),
    "closure_policy": (),
    "closure_evaluation": (("difference_id", "differences"),),
    "next_observation_request": (),
    "observation_method": (),
    "objective_revision": (),
    "observation": (),
    "observation_scope": (),
    "normalized_fact": (),
    "fact_observation_binding": (
        ("fact_id", "normalized_facts"),
        ("observation_id", "observations"),
    ),
    "fact_evaluation": (
        ("fact_id", "normalized_facts"),
        ("previous_evaluation_id", "fact_evaluations"),
    ),
    "negative_observation": (("observation_id", "observations"),),
    "negative_observation_evaluation": (
        ("negative_observation_id", "negative_observations"),
        ("previous_evaluation_id", "negative_observation_evaluations"),
    ),
    "reopen_condition_evaluation": (),
    "candidate_completion_record": (),
    "candidate_claim_evaluation_event": (("difference_id", "differences"),),
    "invariant_evaluation": (),
    "evidence_sufficiency_result": (),
    # No canonical schema names these records' fields in v0.1, so no foreign key can be
    # declared for them without inventing semantics.
    "change": (),
    "reflow_transaction": (),
}


def _is_reference(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("kind"), str)
        and isinstance(value.get("id"), str)
    )


def _walk_path(record: Any, segments: list[str]) -> list[Any]:
    """Return every value the dotted locator *segments* selects, skipping absent branches."""

    current: list[Any] = [record]
    for segment in segments:
        expand = segment.endswith("[]")
        key = segment[:-2] if expand else segment
        nxt: list[Any] = []
        for item in current:
            if key:
                if not isinstance(item, dict) or item.get(key) is None:
                    continue
                item = item[key]
            if expand:
                if isinstance(item, list):
                    nxt.extend(item)
            else:
                nxt.append(item)
        current = nxt
    return current


def _index(bundle: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Count the records each emitted section holds, by identity, for exactly-one checks."""

    from .conformance import EMITTED_SECTIONS, RECORD_TYPES

    counted: dict[str, dict[str, int]] = {}
    for section, type_name in EMITTED_SECTIONS.items():
        key = RECORD_TYPES[type_name].key
        holder = counted.setdefault(section, {})
        for record in bundle.get(section, []) or []:
            if isinstance(record, dict) and isinstance(record.get(key), str):
                holder[record[key]] = holder.get(record[key], 0) + 1
    return counted


def _resolution_error(
    reference: dict[str, Any], counted: dict[str, dict[str, int]], where: str
) -> str | None:
    kind = reference["kind"]
    section = RESOLVABLE_KINDS.get(kind)
    if section is None:
        if kind in EXTERNAL_KINDS:
            return None
        return f"unknown reference kind: {where} -> {kind}"
    found = counted.get(section, {}).get(reference["id"], 0)
    if found == 0:
        return f"reference does not resolve: {where} -> {section}:{reference['id']}"
    if found > 1:
        return f"reference is ambiguous: {where} -> {section}:{reference['id']}"
    return None


def reference_closure_errors(bundle: dict[str, Any]) -> list[str]:
    """Return every reference violation anywhere in the emitted graph.

    Both passes run over every record of every emitted section, not only over the active
    Difference lineage: structural closure decides resolution and rejects an undeclared
    reference kind, and the typed edges decide which kinds a named field may carry.
    """

    from .conformance import EMITTED_SECTIONS, RECORD_TYPES

    counted = _index(bundle)
    errors: list[str] = []
    for section, type_name in sorted(EMITTED_SECTIONS.items()):
        canonical = RECORD_TYPES[type_name]
        for record in bundle.get(section, []) or []:
            if not isinstance(record, dict):
                continue
            identity = record.get(canonical.key)
            where = f"{section}[{identity}]"
            errors.extend(_structural_errors(record, counted, where))
            for field, target in IDENTITY_EDGES[type_name]:
                value = record.get(field)
                if value is None:
                    continue
                if not isinstance(value, str):
                    errors.append(f"foreign key is not an identity: {where}.{field}")
                    continue
                found = counted.get(target, {}).get(value, 0)
                if found == 0:
                    errors.append(
                        f"foreign key does not resolve: {where}.{field} -> {target}:{value}"
                    )
                elif found > 1:
                    errors.append(
                        f"foreign key is ambiguous: {where}.{field} -> {target}:{value}"
                    )
            for edge in REFERENCE_EDGES[type_name]:
                for value in _walk_path(record, edge.path.split(".")):
                    if not isinstance(value, dict) or not isinstance(value.get("kind"), str):
                        errors.append(
                            f"reference field is not a canonical reference: "
                            f"{where}.{edge.path}"
                        )
                        continue
                    if value["kind"] not in edge.kinds:
                        errors.append(
                            f"reference kind is not permitted here: {where}.{edge.path} -> "
                            f"{value['kind']}"
                        )
                        continue
                    resolves_in: str | None = (
                        RESOLVABLE_KINDS.get(value["kind"]) or _FORCED_SECTIONS[value["kind"]]
                        if edge.resolve
                        else RESOLVABLE_KINDS.get(value["kind"])
                    )
                    if resolves_in is None:
                        continue
                    if not isinstance(value.get("id"), str):
                        errors.append(
                            f"resolvable reference carries no identity: {where}.{edge.path}"
                        )
                        continue
                    found = counted.get(resolves_in, {}).get(value["id"], 0)
                    if found == 0:
                        errors.append(
                            f"reference does not resolve: {where}.{edge.path} -> "
                            f"{resolves_in}:{value['id']}"
                        )
                    elif found > 1:
                        errors.append(
                            f"reference is ambiguous: {where}.{edge.path} -> "
                            f"{resolves_in}:{value['id']}"
                        )
    return sorted(set(errors))


#: Sections an edge-level ``resolve`` override targets for a kind that is external by
#: default. Declared here so the override cannot silently invent a section name.
_FORCED_SECTIONS: dict[str, str] = {
    "observation_method": "observation_methods",
}


def _structural_errors(
    node: Any, counted: dict[str, dict[str, int]], where: str
) -> list[str]:
    errors: list[str] = []
    if _is_reference(node):
        error = _resolution_error(node, counted, where)
        if error is not None:
            errors.append(error)
        return errors
    if isinstance(node, dict):
        for key, value in node.items():
            errors.extend(_structural_errors(value, counted, f"{where}.{key}"))
    elif isinstance(node, list):
        for position, value in enumerate(node):
            errors.extend(_structural_errors(value, counted, f"{where}[{position}]"))
    return errors


def relational_errors(bundle: dict[str, Any]) -> list[str]:
    """Return every cross-record relational violation the emitted graph carries.

    Schema conformance, identity recomputation and reference closure each decide a record
    or an edge in isolation. What is left is the relations *between* records that no
    single record can prove: whether a lifecycle event's blocker payload, Next Observation
    Request and Closure Evaluation are actually bound to the Difference, the event head,
    the Closure Policy and the evaluated State they claim.

    Every one of those rules is owned by :mod:`difference.lifecycle`, which the independent
    contract validator also imports, so the producer and the auditor cannot drift. This
    function only applies them to *every* event in the returned bundle, rather than to the
    lineage root the narrower per-route checks happened to cover.
    """

    from .canonical import content_address
    from .identity import policy_semantic_fingerprint
    from .lifecycle import (
        blocker_payload_errors,
        closure_evaluation_binding_errors,
        next_observation_binding_errors,
    )

    differences = {
        record["difference_id"]: record for record in bundle.get("differences", []) or []
    }
    evaluations = {
        record["closure_evaluation_id"]: record for record in bundle.get("evaluations", []) or []
    }
    policies = {
        record["closure_policy_id"]: record for record in bundle.get("policies", []) or []
    }
    requests = {
        record["observation_request_id"]: record
        for record in bundle.get("next_observation_requests", []) or []
    }
    methods = {
        record["observation_method_id"]: record
        for record in bundle.get("observation_methods", []) or []
    }
    chains: dict[str, list[dict[str, Any]]] = {}
    for event in bundle.get("events", []) or []:
        chains.setdefault(event["difference_id"], []).append(event)

    errors: list[str] = []
    for difference_id, chain in sorted(chains.items()):
        chain.sort(key=lambda item: item["event_revision"])
        difference = differences.get(difference_id)
        for position, event in enumerate(chain):
            previous = chain[position - 1] if position > 0 else None
            errors.extend(blocker_payload_errors(event, difference))
            errors.extend(
                next_observation_binding_errors(
                    event, difference, requests, methods, content_address
                )
            )
            errors.extend(
                closure_evaluation_binding_errors(
                    event,
                    previous,
                    difference,
                    evaluations,
                    policies,
                    policy_semantic_fingerprint,
                )
            )
    return sorted(set(errors))
