"""Validate cross-record Observation contract invariants for conformance fixtures."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _index(records: list[dict[str, Any]], key: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        identity = record[key]
        if identity in result:
            errors.append(f"duplicate {key}: {identity}")
        result[identity] = record
    return result


def _ids(refs: list[dict[str, Any]]) -> set[str]:
    return {ref["id"] for ref in refs}


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    """Return deterministic cross-record violations without mutating the bundle."""
    errors: list[str] = []
    facts = _index(bundle["facts"], "fact_id", errors)
    observations = _index(bundle["observations"], "observation_id", errors)
    bindings = _index(bundle["bindings"], "binding_id", errors)
    negatives = _index(bundle["negative_observations"], "negative_observation_id", errors)

    occurrence_keys: set[tuple[str, str]] = set()
    for binding in bindings.values():
        fact_id = binding["fact_id"]
        observation_id = binding["observation_id"]
        if fact_id not in facts:
            errors.append(f"binding references missing Fact: {binding['binding_id']}")
        observation = observations.get(observation_id)
        if observation is None:
            errors.append(f"binding references missing Observation: {binding['binding_id']}")
        else:
            if binding["state_revision_observed"] != observation["state_revision_observed"]:
                errors.append(f"binding State revision mismatch: {binding['binding_id']}")
            if binding["state_fingerprint_observed"] != observation["state_fingerprint_observed"]:
                errors.append(f"binding State fingerprint mismatch: {binding['binding_id']}")
        occurrence_key = (observation_id, binding["source_occurrence_id"])
        if occurrence_key in occurrence_keys:
            errors.append(
                f"duplicate source occurrence: {observation_id}/{binding['source_occurrence_id']}"
            )
        occurrence_keys.add(occurrence_key)

    fact_evaluations: dict[str, list[dict[str, Any]]] = {}
    for evaluation in bundle["fact_evaluations"]:
        fact_evaluations.setdefault(evaluation["fact_id"], []).append(evaluation)
    latest_fact: dict[str, dict[str, Any]] = {}
    for fact_id, records in fact_evaluations.items():
        records.sort(key=lambda item: item["evaluation_revision"])
        if fact_id not in facts:
            errors.append(f"evaluation references missing Fact: {fact_id}")
        for expected_revision, evaluation in enumerate(records):
            if evaluation["evaluation_revision"] != expected_revision:
                errors.append(f"Fact evaluation revision gap: {fact_id}")
                continue
            expected_previous = (
                None if expected_revision == 0 else records[expected_revision - 1]["evaluation_id"]
            )
            if evaluation["previous_evaluation_id"] != expected_previous:
                errors.append(
                    f"Fact evaluation predecessor mismatch: {evaluation['evaluation_id']}"
                )
            for binding_id in _ids(evaluation["binding_refs"]):
                binding = bindings.get(binding_id)
                if binding is None or binding["fact_id"] != fact_id:
                    errors.append(
                        f"cross-Fact or missing binding: {evaluation['evaluation_id']}/{binding_id}"
                    )
        latest_fact[fact_id] = records[-1]

    negative_evaluations: dict[str, list[dict[str, Any]]] = {}
    for evaluation in bundle["negative_evaluations"]:
        negative_evaluations.setdefault(evaluation["negative_observation_id"], []).append(
            evaluation
        )
    latest_negative: dict[str, dict[str, Any]] = {}
    for negative_id, records in negative_evaluations.items():
        records.sort(key=lambda item: item["evaluation_revision"])
        base = negatives.get(negative_id)
        if base is None:
            errors.append(f"evaluation references missing Negative Observation: {negative_id}")
            continue
        for expected_revision, evaluation in enumerate(records):
            if evaluation["evaluation_revision"] != expected_revision:
                errors.append(f"Negative evaluation revision gap: {negative_id}")
                continue
            expected_previous = (
                None if expected_revision == 0 else records[expected_revision - 1]["evaluation_id"]
            )
            if evaluation["previous_evaluation_id"] != expected_previous:
                errors.append(
                    f"Negative evaluation predecessor mismatch: {evaluation['evaluation_id']}"
                )
        initial = records[0]
        if initial["evaluation_status"] != base["negative_status"]:
            errors.append(f"Negative revision zero status mismatch: {negative_id}")
        if _ids(initial["conflict_fact_refs"]) != _ids(base["positive_fact_refs"]):
            errors.append(f"Negative revision zero conflict mismatch: {negative_id}")
        latest_negative[negative_id] = records[-1]

    for fact_id, evaluation in latest_fact.items():
        negative_ids = _ids(evaluation["conflict_negative_observation_refs"])
        if negative_ids and evaluation["evaluation_status"] != "CONFLICTED":
            errors.append(f"Fact conflict refs without CONFLICTED status: {fact_id}")
        for negative_id in negative_ids:
            negative_evaluation = latest_negative.get(negative_id)
            if negative_evaluation is None or fact_id not in _ids(
                negative_evaluation["conflict_fact_refs"]
            ):
                errors.append(f"one-sided Fact/Negative conflict: {fact_id}/{negative_id}")
    for negative_id, evaluation in latest_negative.items():
        fact_ids = _ids(evaluation["conflict_fact_refs"])
        if fact_ids and evaluation["evaluation_status"] != "CONFLICTED":
            errors.append(f"Negative conflict refs without CONFLICTED status: {negative_id}")
        for fact_id in fact_ids:
            fact_evaluation = latest_fact.get(fact_id)
            if fact_evaluation is None or negative_id not in _ids(
                fact_evaluation["conflict_negative_observation_refs"]
            ):
                errors.append(f"one-sided Negative/Fact conflict: {negative_id}/{fact_id}")
    return sorted(set(errors))


def apply_mutation(bundle: dict[str, Any], path: list[str | int], value: Any) -> dict[str, Any]:
    mutated = deepcopy(bundle)
    target: Any = mutated
    for segment in path[:-1]:
        target = target[segment]
    target[path[-1]] = value
    return mutated


def validate_fixture_suite(root: Path) -> tuple[int, int, list[str], list[str]]:
    valid_bundle = load_json(root / "valid" / "bundle.json")
    invalid_cases = load_json(root / "invalid" / "cases.json")
    valid_errors = validate_bundle(valid_bundle)
    invalid_escapes: list[str] = []
    for case in invalid_cases:
        mutated = apply_mutation(valid_bundle, case["path"], case["value"])
        if not validate_bundle(mutated):
            invalid_escapes.append(case["name"])
    return 1, len(invalid_cases), valid_errors, invalid_escapes
