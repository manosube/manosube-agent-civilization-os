"""Deterministic, adapter-free Observation Engine for the v0.1 fixture route."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .errors import ObservationError, ObservationValidationError
from .identity import deterministic_id
from .normalization import SUPPORTED_PROFILE, normalize_fact
from .scope import subject_in_scope, validate_scope, validate_source_locator

OBSERVATION_SCHEMA_BASE = "https://schemas.manosube.org/agent-civilization-os/v0.1/observation/"
_STATUS_CANDIDATE = {
    "ABSENT": "ABSENT",
    "EMPTY": "EMPTY",
    "NO_RESULT": "UNKNOWN",
    "UNKNOWN": "UNKNOWN",
    "UNOBSERVED": "UNOBSERVED",
    "BLOCKED": "BLOCKED",
    "INCOMPLETE": "INCOMPLETE",
    "FAILED": "UNKNOWN",
    "INVALID": "REJECT_OR_QUARANTINE",
    "CONFLICTED": "CONFLICTED",
}


def _schema_root() -> Path:
    module_path = Path(__file__).resolve()
    for candidate in (
        module_path.parents[3] / "01_SCHEMA",
        module_path.parents[2] / "01_SCHEMA",
        Path.cwd() / "01_SCHEMA",
    ):
        if candidate.is_dir():
            return candidate
    raise ObservationValidationError("canonical schema root is unavailable")


def _validators() -> dict[str, Draft202012Validator]:
    schemas = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(_schema_root().rglob("*.schema.json"))
    ]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    return {
        schema["$id"]: Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        )
        for schema in schemas
    }


def _ref(kind: str, identity: str) -> dict[str, str]:
    return {"kind": kind, "id": identity}


def _require_ref_kind(reference: dict[str, str], expected: str, context: str) -> None:
    if reference.get("kind") != expected:
        raise ObservationError(
            f"reference kind mismatch at {context}: expected={expected} "
            f"actual={reference.get('kind')}"
        )


def _binding(
    fact: dict[str, Any],
    observation_id: str,
    state_revision: int,
    state_fingerprint: dict[str, str],
    occurrence: dict[str, Any],
    quality: str,
) -> dict[str, Any]:
    source_occurrence_id = deterministic_id(
        "SOURCE-OCC",
        {
            "source_ref": occurrence["source_ref"],
            "source_locator": occurrence["source_locator"],
        },
    )
    identity_input = {
        "fact_id": fact["fact_id"],
        "observation_id": observation_id,
        "source_occurrence_id": source_occurrence_id,
    }
    return {
        "schema_version": "0.1",
        "binding_id": deterministic_id("BIND", identity_input),
        **identity_input,
        "state_revision_observed": state_revision,
        "state_fingerprint_observed": deepcopy(state_fingerprint),
        "source_ref": deepcopy(occurrence["source_ref"]),
        "source_locator": occurrence["source_locator"],
        "observed_quality_status": "INCOMPLETE" if quality == "PARTIAL" else quality,
    }


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _time_boundary_complete(observation: dict[str, Any], scope: dict[str, Any]) -> bool:
    boundary = observation["time_boundary"]
    try:
        observed_start = _instant(boundary["observation_started_at"])
        observed_end = _instant(boundary["observation_ended_at"])
        effective_start = _instant(boundary["target_effective_start"])
        effective_end = _instant(boundary["target_effective_end"])
        snapshot = _instant(boundary["source_snapshot_time"])
        scope_observed_start = _instant(scope["observation_window"]["start"])
        scope_observed_end = _instant(scope["observation_window"]["end"])
        scope_effective_start = _instant(scope["target_effective_window"]["start"])
        scope_effective_end = _instant(scope["target_effective_window"]["end"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        observed_start <= observed_end
        and effective_start <= effective_end
        and scope_observed_start <= observed_start <= observed_end <= scope_observed_end
        and scope_effective_start <= effective_start <= effective_end <= scope_effective_end
        and effective_start <= snapshot <= observed_end
    )


def _completion(
    status: str,
    observation: dict[str, Any],
    scope: dict[str, Any],
    collection_complete: bool,
) -> dict[str, bool]:
    attempts = observation["attempts"]
    attempts_complete = bool(attempts) and all(
        attempt["result"] in {"COMPLETE", "EMPTY"}
        and attempt["method_ref"] == observation["method_ref"]
        and _instant(attempt["started_at"]) <= _instant(attempt["ended_at"])
        for attempt in attempts
    )
    method_complete = attempts_complete and observation["status"] in {"COMPLETE", "EMPTY"}
    no_blocking_blind_spot = all(
        item["impact"] not in {"BLOCKS_COMPLETION", "BLOCKS_ABSENCE"}
        for item in observation["blind_spots"]["items"]
    )
    base: dict[str, bool] = {
        "target_defined": True,
        "scope_complete": scope["scope_status"] == "COMPLETE",
        "method_complete": method_complete,
        "time_boundary_complete": _time_boundary_complete(observation, scope),
        "source_snapshots_identified": bool(observation["source_snapshot_refs"]),
        "required_attempts_completed": method_complete,
        "no_blocking_blind_spot": no_blocking_blind_spot,
        "no_conflicting_positive_fact": True,
    }
    if status == "EMPTY":
        base["collection_defined"] = collection_complete
        base["enumeration_complete"] = collection_complete
        base["zero_valid_members"] = collection_complete and not observation["normalized_fact_refs"]
    return base


def _negative_records(
    *,
    claim: dict[str, Any],
    observation: dict[str, Any],
    scope: dict[str, Any],
    facts: list[dict[str, Any]],
    evidence_refs: list[dict[str, str]],
    collection_complete: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    status = claim["negative_status"]
    if status not in _STATUS_CANDIDATE:
        raise ObservationError(f"unknown negative status: {status!r}")
    conflicts = [
        fact
        for fact in facts
        if fact["subject"] == claim["subject"]
        and fact["predicate"] == claim["predicate"]
        and fact["effective_boundary"] == claim["effective_boundary"]
    ]
    if conflicts:
        status = "CONFLICTED"
    completion = _completion(status, observation, scope, collection_complete)
    if status == "ABSENT" and not all(completion.values()):
        raise ObservationError("ABSENT requires a complete bounded absence gate")
    if status == "EMPTY" and not all(
        completion.get(key) is True
        for key in (
            "collection_defined",
            "enumeration_complete",
            "zero_valid_members",
            "no_blocking_blind_spot",
        )
    ):
        raise ObservationError("EMPTY requires complete zero-member enumeration")
    identity_input = {
        "observation_id": observation["observation_id"],
        "subject": claim["subject"],
        "predicate": claim["predicate"],
        "effective_boundary": claim["effective_boundary"],
    }
    negative_id = deterministic_id("NEG", identity_input)
    positive_refs = [_ref("normalized_fact", fact["fact_id"]) for fact in conflicts]
    record = {
        "schema_version": "0.1",
        "negative_observation_id": negative_id,
        "observation_id": observation["observation_id"],
        "project_id": observation["project_id"],
        "target_identity": observation["target"]["target_identity"],
        "subject": claim["subject"],
        "predicate": claim["predicate"],
        "effective_boundary": deepcopy(claim["effective_boundary"]),
        "negative_status": status,
        "scope_ref": deepcopy(observation["scope_ref"]),
        "method_ref": deepcopy(observation["method_ref"]),
        "time_boundary": deepcopy(observation["time_boundary"]),
        "source_snapshot_refs": deepcopy(observation["source_snapshot_refs"]),
        "attempt_refs": [
            _ref("observation_attempt", attempt["attempt_id"])
            for attempt in observation["attempts"]
        ],
        "completion_evaluation": completion,
        "blind_spot_refs": [
            _ref("blind_spot", blind_spot["blind_spot_id"])
            for blind_spot in observation["blind_spots"]["items"]
        ],
        "negative_evidence_refs": deepcopy(evidence_refs),
        "positive_fact_refs": positive_refs,
        "conclusion": {
            "state_candidate": _STATUS_CANDIDATE[status],
            "reason": claim.get("reason", "bounded negative observation evaluation"),
        },
    }
    evaluation_id = deterministic_id(
        "NEG-EVAL", {"negative_observation_id": negative_id, "evaluation_revision": 0}
    )
    evaluation = {
        "schema_version": "0.1",
        "evaluation_id": evaluation_id,
        "negative_observation_id": negative_id,
        "evaluation_revision": 0,
        "previous_evaluation_id": None,
        "evaluation_status": status,
        "conflict_fact_refs": positive_refs,
        "evidence_refs": deepcopy(evidence_refs),
    }
    conflict_update = None
    if conflicts:
        conflict_update = {
            "negative_id": negative_id,
            "fact_ids": {f["fact_id"] for f in conflicts},
        }
    return record, evaluation, conflict_update


def _validate_records(bundle: dict[str, Any]) -> None:
    validators = _validators()
    record_groups = {
        "facts": "normalized_fact.schema.json",
        "observations": "observation.schema.json",
        "bindings": "fact_observation_binding.schema.json",
        "fact_evaluations": "fact_evaluation.schema.json",
        "negative_observations": "negative_observation.schema.json",
        "negative_evaluations": "negative_observation_evaluation.schema.json",
    }
    errors: list[str] = []
    for group, schema_name in record_groups.items():
        validator = validators[OBSERVATION_SCHEMA_BASE + schema_name]
        for record in bundle[group]:
            errors.extend(error.message for error in validator.iter_errors(record))
    fact_ids = {fact["fact_id"] for fact in bundle["facts"]}
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
                if reference["kind"] != "fact_observation_binding" or not binding or binding["fact_id"] != fact_id:
                    errors.append(f"cross-Fact or missing binding: {fact_id}")
    negative_ids = {item["negative_observation_id"] for item in bundle["negative_observations"]}
    for negative_id in negative_ids:
        evaluations = sorted(
            (item for item in bundle["negative_evaluations"] if item["negative_observation_id"] == negative_id),
            key=lambda item: item["evaluation_revision"],
        )
        if not evaluations or evaluations[0]["evaluation_revision"] != 0:
            errors.append(f"Negative Observation has no revision zero evaluation: {negative_id}")
        for revision, evaluation in enumerate(evaluations):
            expected = None if revision == 0 else evaluations[revision - 1]["evaluation_id"]
            if evaluation["evaluation_revision"] != revision or evaluation["previous_evaluation_id"] != expected:
                errors.append(f"Negative evaluation lineage invalid: {negative_id}")
    if errors:
        raise ObservationValidationError(sorted(errors)[0])


def _validate_scope_record(scope: dict[str, Any]) -> None:
    validator = _validators()[OBSERVATION_SCHEMA_BASE + "observation_scope.schema.json"]
    errors = sorted(
        validator.iter_errors(scope),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        location = "/".join(str(part) for part in errors[0].absolute_path) or "<root>"
        raise ObservationValidationError(
            f"scope schema validation failed at {location}: {errors[0].message}"
        )


def _observation_status(
    scope: dict[str, Any],
    attempts: list[dict[str, Any]],
    blind_spots: list[dict[str, Any]],
    occurrence_outcomes: list[str],
    has_facts: bool,
    collection_complete: bool,
) -> str:
    scope_status = scope["scope_status"]
    if scope_status in {"INVALID", "CONFLICTED", "BLOCKED", "UNOBSERVED"}:
        return scope_status
    results = [attempt["result"] for attempt in attempts]
    combined = [*occurrence_outcomes, *results]
    if "FAILED" in combined:
        return "FAILED"
    if "BLOCKED" in combined:
        return "BLOCKED"
    if (
        scope_status == "INCOMPLETE"
        or "INCOMPLETE" in combined
        or "PARTIAL" in combined
        or any(item["impact"] == "BLOCKS_COMPLETION" for item in blind_spots)
    ):
        return "INCOMPLETE"
    if "UNKNOWN" in combined:
        return "UNKNOWN"
    if has_facts:
        return "COMPLETE"
    if (
        collection_complete
        and attempts
        and all(attempt["result"] in {"COMPLETE", "EMPTY"} for attempt in attempts)
    ):
        return "EMPTY"
    return "UNKNOWN"


def observe(request: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Execute one deterministic Observation over explicit immutable fixture inputs."""

    profile = request["normalization_profile"]
    if profile != SUPPORTED_PROFILE:
        raise ObservationError(f"unsupported normalization profile: {profile}")
    scope = deepcopy(request["scope"])
    _validate_scope_record(scope)
    validate_scope(scope, request["project_id"], request["target_identity"])
    state_revision = request["state_revision_observed"]
    if (
        not isinstance(state_revision, int)
        or isinstance(state_revision, bool)
        or state_revision < 0
    ):
        raise ObservationError("State revision must be a non-negative integer")
    state_fingerprint = deepcopy(request["state_fingerprint_observed"])
    if state_fingerprint.get("profile") != "MANOSUBE-STATE-SHA256-0.1":
        raise ObservationError("unsupported State fingerprint profile")
    _require_ref_kind(request["method_ref"], "observation_method", "method_ref")
    if request["method_ref"] != scope["method_ref"]:
        raise ObservationError("Observation method is outside the declared Scope")
    for reference in request["source_snapshot_refs"]:
        _require_ref_kind(reference, "source_snapshot", "source_snapshot_refs")
    for reference in request.get("observation_evidence_refs", []):
        _require_ref_kind(reference, "observation_evidence", "observation_evidence_refs")
    scope_sources = {(reference["kind"], reference["id"]) for reference in scope["source_snapshot_refs"]}
    declared_sources = {
        (reference["kind"], reference["id"]) for reference in request["source_snapshot_refs"]
    }
    if declared_sources != scope_sources:
        raise ObservationError("Observation sources must exactly match the declared Scope")
    prior = deepcopy(
        request.get(
            "prior_bundle",
            {
                "facts": [],
                "observations": [],
                "bindings": [],
                "fact_evaluations": [],
                "negative_observations": [],
                "negative_evaluations": [],
            },
        )
    )
    _validate_records(prior)

    observation_identity = {
        "project_id": request["project_id"],
        "state_revision_observed": state_revision,
        "state_fingerprint_observed": state_fingerprint,
        "target_identity": request["target_identity"],
        "scope_id": scope["scope_id"],
        "method_ref": request["method_ref"],
        "time_boundary": request["time_boundary"],
        "source_snapshot_refs": request["source_snapshot_refs"],
        "normalization_profile": profile,
    }
    observation_id = deterministic_id("OBS", observation_identity)
    facts_by_id = {fact["fact_id"]: fact for fact in prior["facts"]}
    bindings_by_id = {binding["binding_id"]: binding for binding in prior["bindings"]}
    observed_fact_ids: set[str] = set()
    new_binding_ids: set[str] = set()
    occurrence_outcomes: list[str] = []
    for occurrence in sorted(
        request.get("source_occurrences", []),
        key=lambda item: (item["source_ref"]["id"], item["source_locator"]),
    ):
        validate_source_locator(occurrence["source_locator"])
        _require_ref_kind(occurrence["source_ref"], "source_snapshot", "source_occurrence")
        if (
            occurrence["source_ref"]["kind"],
            occurrence["source_ref"]["id"],
        ) not in declared_sources:
            raise ObservationError("source occurrence is not declared by the Observation")
        outcome = occurrence.get("outcome", "COMPLETE")
        occurrence_outcomes.append(outcome)
        for raw in occurrence.get("facts", []):
            if not subject_in_scope(raw["subject"], scope):
                raise ObservationError(f"Fact subject is outside scope: {raw['subject']}")
            fact = normalize_fact(raw, request["project_id"], profile)
            existing = facts_by_id.get(fact["fact_id"])
            if existing is not None and existing != fact:
                raise ObservationError(f"Fact identity collision: {fact['fact_id']}")
            facts_by_id[fact["fact_id"]] = fact
            observed_fact_ids.add(fact["fact_id"])
            binding = _binding(
                fact,
                observation_id,
                state_revision,
                state_fingerprint,
                occurrence,
                "SUPPORTED" if outcome == "COMPLETE" else outcome,
            )
            existing_binding = bindings_by_id.get(binding["binding_id"])
            if existing_binding is not None and existing_binding != binding:
                raise ObservationError(f"Binding identity collision: {binding['binding_id']}")
            bindings_by_id[binding["binding_id"]] = binding
            new_binding_ids.add(binding["binding_id"])

    facts = sorted(facts_by_id.values(), key=lambda item: item["fact_id"])
    bindings = sorted(bindings_by_id.values(), key=lambda item: item["binding_id"])
    observed_facts = [fact for fact in facts if fact["fact_id"] in observed_fact_ids]
    attempts = deepcopy(request.get("attempts", []))
    for attempt in attempts:
        _require_ref_kind(attempt["method_ref"], "observation_method", "attempt.method_ref")
        if attempt["method_ref"] != request["method_ref"]:
            raise ObservationError("Observation attempt uses an undeclared method")
    blind_spots_by_id: dict[str, dict[str, Any]] = {}
    for blind_spot in [*scope["blind_spots"], *request.get("blind_spots", [])]:
        existing = blind_spots_by_id.get(blind_spot["blind_spot_id"])
        if existing is not None and existing != blind_spot:
            raise ObservationError(f"Blind spot identity collision: {blind_spot['blind_spot_id']}")
        blind_spots_by_id[blind_spot["blind_spot_id"]] = deepcopy(blind_spot)
    blind_spots = sorted(blind_spots_by_id.values(), key=lambda item: item["blind_spot_id"])
    collection_complete = request.get("collection_complete") is True
    status = _observation_status(
        scope,
        attempts,
        blind_spots,
        occurrence_outcomes,
        bool(observed_facts),
        collection_complete,
    )
    observation = {
        "schema_version": "0.1",
        "observation_id": observation_id,
        "project_id": request["project_id"],
        "state_revision_observed": state_revision,
        "state_fingerprint_observed": state_fingerprint,
        "target": {"target_identity": request["target_identity"], "kind": request["target_kind"]},
        "scope_ref": _ref("observation_scope", scope["scope_id"]),
        "method_ref": deepcopy(request["method_ref"]),
        "time_boundary": deepcopy(request["time_boundary"]),
        "source_snapshot_refs": deepcopy(request["source_snapshot_refs"]),
        "normalization_profile": profile,
        "normalized_fact_refs": [
            _ref("normalized_fact", fact["fact_id"]) for fact in observed_facts
        ],
        "status": status,
        "blind_spots": {
            "status": "KNOWN_BLIND_SPOTS_PRESENT" if blind_spots else "NONE_KNOWN",
            "items": blind_spots,
        },
        "attempts": attempts,
        "observation_evidence_refs": deepcopy(request.get("observation_evidence_refs", [])),
    }
    existing_observation = next(
        (item for item in prior["observations"] if item["observation_id"] == observation_id), None
    )
    prior_binding_ids = {item["binding_id"] for item in prior["bindings"]}
    if existing_observation is not None:
        if existing_observation != observation or not new_binding_ids <= prior_binding_ids:
            raise ObservationError("Observation identity collision on non-identical retry")
        return prior

    fact_evaluations = deepcopy(prior["fact_evaluations"])
    coordinate_groups: dict[str, list[dict[str, Any]]] = {}
    for fact in facts:
        coordinate = json.dumps(
            [fact["subject"], fact["predicate"], fact["effective_boundary"]],
            sort_keys=True,
            separators=(",", ":"),
        )
        coordinate_groups.setdefault(coordinate, []).append(fact)
    positive_conflicts = {
        fact["fact_id"]: {other["fact_id"] for other in group if other["fact_id"] != fact["fact_id"]}
        for group in coordinate_groups.values() if len(group) > 1
        for fact in group
    }
    appended_fact_evaluations: dict[str, dict[str, Any]] = {}
    for fact in observed_facts:
        previous = sorted(
            (
                evaluation
                for evaluation in fact_evaluations
                if evaluation["fact_id"] == fact["fact_id"]
            ),
            key=lambda evaluation: evaluation["evaluation_revision"],
        )
        evaluation_revision = len(previous)
        previous_evaluation_id = previous[-1]["evaluation_id"] if previous else None
        prior_negative_conflicts = (
            deepcopy(previous[-1]["conflict_negative_observation_refs"]) if previous else []
        )
        fact_bindings = [
            binding
            for binding in bindings
            if binding["fact_id"] == fact["fact_id"] and binding["binding_id"] in new_binding_ids
        ]
        conflict_fact_ids = positive_conflicts.get(fact["fact_id"], set())
        new_evaluation = {
                "schema_version": "0.1",
                "evaluation_id": deterministic_id(
                    "FACT-EVAL",
                    {
                        "fact_id": fact["fact_id"],
                        "evaluation_revision": evaluation_revision,
                    },
                ),
                "fact_id": fact["fact_id"],
                "evaluation_revision": evaluation_revision,
                "previous_evaluation_id": previous_evaluation_id,
                "binding_refs": [
                    _ref("fact_observation_binding", binding["binding_id"])
                    for binding in fact_bindings
                ],
                "evaluation_status": "CONFLICTED" if prior_negative_conflicts or conflict_fact_ids else "SUPPORTED",
                "conflict_fact_refs": [_ref("normalized_fact", item) for item in sorted(conflict_fact_ids)],
                "conflict_negative_observation_refs": prior_negative_conflicts,
                "evidence_refs": deepcopy(request.get("observation_evidence_refs", [])),
            }
        fact_evaluations.append(new_evaluation)
        appended_fact_evaluations[fact["fact_id"]] = new_evaluation
    negatives = deepcopy(prior["negative_observations"])
    negative_evaluations = deepcopy(prior["negative_evaluations"])
    conflict_found = False
    for claim in request.get("negative_claims", []):
        if not subject_in_scope(claim["subject"], scope):
            raise ObservationError(f"Negative claim subject is outside scope: {claim['subject']}")
        negative, evaluation, conflict = _negative_records(
            claim=claim,
            observation=observation,
            scope=scope,
            facts=facts,
            evidence_refs=request.get("observation_evidence_refs", []),
            collection_complete=collection_complete,
        )
        negatives.append(negative)
        negative_evaluations.append(evaluation)
        if conflict:
            conflict_found = True
            for fact_id in conflict["fact_ids"]:
                fact_evaluation = appended_fact_evaluations.get(fact_id)
                if fact_evaluation is None:
                    previous = sorted(
                        (item for item in fact_evaluations if item["fact_id"] == fact_id),
                        key=lambda item: item["evaluation_revision"],
                    )
                    revision = len(previous)
                    fact_evaluation = {
                        "schema_version": "0.1",
                        "evaluation_id": deterministic_id("FACT-EVAL", {"fact_id": fact_id, "evaluation_revision": revision}),
                        "fact_id": fact_id,
                        "evaluation_revision": revision,
                        "previous_evaluation_id": previous[-1]["evaluation_id"] if previous else None,
                        "binding_refs": [],
                        "evaluation_status": "CONFLICTED",
                        "conflict_fact_refs": deepcopy(previous[-1]["conflict_fact_refs"]) if previous else [],
                        "conflict_negative_observation_refs": deepcopy(previous[-1]["conflict_negative_observation_refs"]) if previous else [],
                        "evidence_refs": deepcopy(request.get("observation_evidence_refs", [])),
                    }
                    fact_evaluations.append(fact_evaluation)
                    appended_fact_evaluations[fact_id] = fact_evaluation
                fact_evaluation["evaluation_status"] = "CONFLICTED"
                reference = _ref("negative_observation", conflict["negative_id"])
                if reference not in fact_evaluation["conflict_negative_observation_refs"]:
                    fact_evaluation["conflict_negative_observation_refs"].append(
                        _ref("negative_observation", conflict["negative_id"])
                    )
                fact_evaluation["conflict_negative_observation_refs"].sort(key=lambda reference: reference["id"])
    if positive_conflicts:
        conflict_found = True
    if conflict_found:
        observation["status"] = "CONFLICTED"
    bundle = {
        "facts": facts,
        "observations": [*deepcopy(prior["observations"]), observation],
        "bindings": bindings,
        "fact_evaluations": fact_evaluations,
        "negative_observations": sorted(
            negatives, key=lambda item: item["negative_observation_id"]
        ),
        "negative_evaluations": sorted(
            negative_evaluations, key=lambda item: item["negative_observation_id"]
        ),
    }
    _validate_records(bundle)
    return bundle
