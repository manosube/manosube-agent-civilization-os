"""The single canonical cross-record Observation verification authority.

Schema conformance, identity recomputation, evaluation lineage, binding provenance and
conflict symmetry for a canonical Observation bundle are one ruleset. It is owned here by
the Observation element and reused by every downstream consumer -- the Observation Engine
itself and the Difference Engine -- so that no second, drifting ruleset can exist.

Reference lookup and identity recomputation alone are not payload validation: a retained
identity says only that the identity-bearing projection is unchanged. The rules here are
what decide whether the record's *whole* payload is admissible.
"""

from __future__ import annotations

import json
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .identity import deterministic_id, observation_identity
from .schemas import OBSERVATION_SCHEMA_BASE, validators

RECORD_SCHEMAS: dict[str, str] = {
    "facts": "normalized_fact.schema.json",
    "observations": "observation.schema.json",
    "bindings": "fact_observation_binding.schema.json",
    "fact_evaluations": "fact_evaluation.schema.json",
    "negative_observations": "negative_observation.schema.json",
    "negative_evaluations": "negative_observation_evaluation.schema.json",
}


#: Negative statuses whose conclusion is only canonical while bounded Negative Evidence
#: proves it. ``NO_RESULT`` and ``UNOBSERVED`` are the opposite case -- they assert that
#: nothing was concluded -- so no Evidence is required for them and none is invented here.
EVIDENCE_BOUND_NEGATIVE_STATUSES: frozenset[str] = frozenset({"ABSENT", "EMPTY"})

#: The one status whose Evidence is *not* the bounded negative channel. A ``CONFLICTED``
#: evaluation concludes that a positive Fact contradicts the negative claim, and what
#: proves that is the Observation Evidence which produced the Fact -- the bounded Negative
#: Evidence proves absence, which is precisely what is being contradicted. Both channels
#: are admissible there, and only there.
CONTRADICTION_NEGATIVE_STATUS = "CONFLICTED"


def negative_evaluation_evidence_errors(bundle: dict[str, Any]) -> list[str]:
    """Return every Negative Evaluation Evidence binding violation in *bundle*.

    A Negative Observation Evaluation identity is derived from its owning record and its
    revision alone, so a caller can retain ``evaluation_id`` while replacing the Evidence
    list entirely. Nothing downstream questioned it: consumers trusted the evaluation's
    status and checked only that the owning record carried *some* Evidence.

    Bounded Negative Evidence is a channel, not a bag. An evaluation asserting a negative
    conclusion may only cite Evidence its own Negative Observation declared -- otherwise a
    proven ``ABSENT`` rests on proof belonging to a different observation, or on
    Observation Evidence, collapsing two provenance channels the contract keeps distinct.

    ``CONFLICTED`` is the one exception, and it is not a relaxation: that status concludes
    the negative claim was contradicted by an observed Fact, so it cites the Observation
    Evidence of its own Observation. It is still bound -- to that Observation's declared
    Evidence -- rather than free.

    Owned here, in the Observation element that owns Negative Observation semantics, so
    both Engines and both independent validators decide it one way.
    """

    errors: list[str] = []
    owners = {
        record["negative_observation_id"]: record
        for record in bundle["negative_observations"]
    }
    observations = {
        record["observation_id"]: record for record in bundle.get("observations", [])
    }
    for evaluation in bundle["negative_evaluations"]:
        identity = evaluation["evaluation_id"]
        owner = owners.get(evaluation["negative_observation_id"])
        if owner is None:
            # Ownership is unresolvable, so no Evidence claim it makes can be decided.
            errors.append(f"Negative evaluation has no resolvable owner: {identity}")
            continue
        declared = {canonical_json_bytes(item) for item in owner["negative_evidence_refs"]}
        if evaluation["evaluation_status"] == CONTRADICTION_NEGATIVE_STATUS:
            observation = observations.get(owner["observation_id"])
            if observation is not None:
                declared |= {
                    canonical_json_bytes(item)
                    for item in observation["observation_evidence_refs"]
                }
        for reference in evaluation["evidence_refs"]:
            if canonical_json_bytes(reference) not in declared:
                errors.append(
                    "Negative evaluation Evidence is not declared by its own channel: "
                    f"{identity}"
                )
        if (
            evaluation["evaluation_status"] in EVIDENCE_BOUND_NEGATIVE_STATUSES
            and not evaluation["evidence_refs"]
        ):
            errors.append(
                f"{evaluation['evaluation_status']} Negative evaluation carries no bounded "
                f"Evidence: {identity}"
            )
    return errors


def observation_record_errors(bundle: dict[str, Any]) -> list[str]:
    """Return every cross-record Observation violation, without mutating *bundle*."""

    schema_validators = validators()
    record_groups = RECORD_SCHEMAS
    errors: list[str] = []
    # A record that fails its canonical schema is already reported inadmissible; its
    # identity is not recomputed, because a projection over a malformed payload would
    # raise instead of returning a verdict.
    schema_valid: dict[str, list[dict[str, Any]]] = {}
    for group, schema_name in record_groups.items():
        validator = schema_validators[OBSERVATION_SCHEMA_BASE + schema_name]
        valid: list[dict[str, Any]] = []
        for record in bundle[group]:
            record_errors = [error.message for error in validator.iter_errors(record)]
            errors.extend(record_errors)
            if not record_errors:
                valid.append(record)
        schema_valid[group] = valid
    fact_ids = {fact["fact_id"] for fact in bundle["facts"]}
    for fact in schema_valid["facts"]:
        semantic = {
            key: value for key, value in fact.items() if key not in {"schema_version", "fact_id"}
        }
        if fact["fact_id"] != deterministic_id("FACT", semantic):
            errors.append(f"Fact identity mismatch: {fact['fact_id']}")
        if semantic != json.loads(canonical_json_bytes(semantic)):
            errors.append(f"Fact payload is not canonical: {fact['fact_id']}")
    for observation in schema_valid["observations"]:
        # An Observation identity is derived from its project, State binding, Target,
        # Scope, method, time boundary, source snapshots and normalization profile. A
        # caller may retain the id while altering any of them, and every reference still
        # resolves, so the identity is recomputed rather than trusted.
        if observation["observation_id"] != observation_identity(observation):
            errors.append(f"Observation identity mismatch: {observation['observation_id']}")
    bound_fact_ids = {binding["fact_id"] for binding in bundle["bindings"]}
    if fact_ids != bound_fact_ids:
        errors.append("every Fact must have one or more provenance Bindings")
    binding_keys = {
        (binding["fact_id"], binding["observation_id"], binding["source_occurrence_id"])
        for binding in bundle["bindings"]
    }
    if len(binding_keys) != len(bundle["bindings"]):
        errors.append("duplicate Fact/Observation/source occurrence Binding")
    identity_fields = {
        "facts": "fact_id",
        "observations": "observation_id",
        "bindings": "binding_id",
        "fact_evaluations": "evaluation_id",
        "negative_observations": "negative_observation_id",
        "negative_evaluations": "evaluation_id",
    }
    for group, field in identity_fields.items():
        identities = [record[field] for record in bundle[group]]
        if len(identities) != len(set(identities)):
            errors.append(f"duplicate {field}")
    bindings_by_id = {record["binding_id"]: record for record in bundle["bindings"]}
    observations_by_id = {record["observation_id"]: record for record in bundle["observations"]}
    for binding in bundle["bindings"]:
        expected_binding_id = deterministic_id(
            "BIND",
            {
                "fact_id": binding["fact_id"],
                "observation_id": binding["observation_id"],
                "source_occurrence_id": binding["source_occurrence_id"],
            },
        )
        if binding["binding_id"] != expected_binding_id:
            errors.append(f"Binding identity mismatch: {binding['binding_id']}")
        bound: dict[str, Any] | None = observations_by_id.get(binding["observation_id"])
        if bound is None:
            errors.append(f"binding references missing Observation: {binding['binding_id']}")
        elif (
            binding["state_revision_observed"] != bound["state_revision_observed"]
            or binding["state_fingerprint_observed"] != bound["state_fingerprint_observed"]
        ):
            errors.append(f"binding State mismatch: {binding['binding_id']}")
    for fact_id in fact_ids:
        evaluations = sorted(
            (item for item in bundle["fact_evaluations"] if item["fact_id"] == fact_id),
            key=lambda item: item["evaluation_revision"],
        )
        for revision, evaluation in enumerate(evaluations):
            if evaluation["evaluation_revision"] != revision:
                errors.append(f"Fact evaluation revision gap: {fact_id}")
            expected = None if revision == 0 else evaluations[revision - 1]["evaluation_id"]
            if evaluation["previous_evaluation_id"] != expected:
                errors.append(f"Fact evaluation predecessor mismatch: {fact_id}")
            for reference in evaluation["binding_refs"]:
                binding = bindings_by_id.get(reference["id"])
                if (
                    reference["kind"] != "fact_observation_binding"
                    or not binding
                    or binding["fact_id"] != fact_id
                ):
                    errors.append(f"cross-Fact or missing binding: {fact_id}")
    negative_ids = {item["negative_observation_id"] for item in bundle["negative_observations"]}
    for evaluation in bundle["fact_evaluations"]:
        if evaluation["fact_id"] not in fact_ids:
            errors.append(f"evaluation references missing Fact: {evaluation['fact_id']}")
    for evaluation in bundle["negative_evaluations"]:
        if evaluation["negative_observation_id"] not in negative_ids:
            errors.append(
                "evaluation references missing Negative Observation: "
                f"{evaluation['negative_observation_id']}"
            )
    for negative_id in negative_ids:
        evaluations = sorted(
            (
                item
                for item in bundle["negative_evaluations"]
                if item["negative_observation_id"] == negative_id
            ),
            key=lambda item: item["evaluation_revision"],
        )
        if not evaluations or evaluations[0]["evaluation_revision"] != 0:
            errors.append(f"Negative Observation has no revision zero evaluation: {negative_id}")
        else:
            negative = next(
                item
                for item in bundle["negative_observations"]
                if item["negative_observation_id"] == negative_id
            )
            initial = evaluations[0]
            if initial["evaluation_status"] != negative["negative_status"]:
                errors.append(f"Negative revision zero status mismatch: {negative_id}")
            if {item["id"] for item in initial["conflict_fact_refs"]} != {
                item["id"] for item in negative["positive_fact_refs"]
            }:
                errors.append(f"Negative revision zero conflict mismatch: {negative_id}")
        for revision, evaluation in enumerate(evaluations):
            expected = None if revision == 0 else evaluations[revision - 1]["evaluation_id"]
            if (
                evaluation["evaluation_revision"] != revision
                or evaluation["previous_evaluation_id"] != expected
            ):
                errors.append(f"Negative evaluation lineage invalid: {negative_id}")
    latest_fact_evaluations = {
        fact_id: max(
            (item for item in bundle["fact_evaluations"] if item["fact_id"] == fact_id),
            key=lambda item: item["evaluation_revision"],
            default=None,
        )
        for fact_id in fact_ids
    }
    latest_negative_evaluations = {
        negative_id: max(
            (
                item
                for item in bundle["negative_evaluations"]
                if item["negative_observation_id"] == negative_id
            ),
            key=lambda item: item["evaluation_revision"],
            default=None,
        )
        for negative_id in negative_ids
    }
    for fact_id, fact_evaluation in latest_fact_evaluations.items():
        if fact_evaluation is None:
            continue
        for reference in fact_evaluation["conflict_negative_observation_refs"]:
            negative_evaluation = latest_negative_evaluations.get(reference["id"])
            if negative_evaluation is None or fact_id not in {
                item["id"] for item in negative_evaluation["conflict_fact_refs"]
            }:
                errors.append(f"one-sided Fact/Negative conflict: {fact_id} -> {reference['id']}")
    for negative_id, negative_evaluation in latest_negative_evaluations.items():
        if negative_evaluation is None:
            continue
        for reference in negative_evaluation["conflict_fact_refs"]:
            fact_evaluation = latest_fact_evaluations.get(reference["id"])
            if fact_evaluation is None or negative_id not in {
                item["id"] for item in fact_evaluation["conflict_negative_observation_refs"]
            }:
                errors.append(
                    f"one-sided Negative/Fact conflict: {negative_id} -> {reference['id']}"
                )
    # Bounded Negative Evidence is a channel: an evaluation may only cite Evidence its own
    # Negative Observation declared. Decided by the one authority both auditors import.
    errors.extend(negative_evaluation_evidence_errors(bundle))
    return errors
