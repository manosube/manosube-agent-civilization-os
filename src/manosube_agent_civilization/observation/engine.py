"""Deterministic, adapter-free Observation Engine for the v0.1 fixture route."""

from __future__ import annotations

from copy import deepcopy
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
        "observed_quality_status": quality,
    }


def _completion(status: str, supplied: dict[str, Any] | None) -> dict[str, bool]:
    base = {
        "target_defined": True,
        "scope_complete": False,
        "method_complete": False,
        "time_boundary_complete": True,
        "source_snapshots_identified": True,
        "required_attempts_completed": False,
        "no_blocking_blind_spot": False,
        "no_conflicting_positive_fact": True,
    }
    if supplied:
        base.update(supplied)
    if status == "EMPTY":
        base.setdefault("collection_defined", False)
        base.setdefault("enumeration_complete", False)
        base.setdefault("zero_valid_members", False)
    return base


def _negative_records(
    *,
    claim: dict[str, Any],
    observation: dict[str, Any],
    facts: list[dict[str, Any]],
    evidence_refs: list[dict[str, str]],
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
    completion = _completion(status, claim.get("completion_evaluation"))
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
    for reference in request["source_snapshot_refs"]:
        _require_ref_kind(reference, "source_snapshot", "source_snapshot_refs")
    for reference in request.get("observation_evidence_refs", []):
        _require_ref_kind(reference, "observation_evidence", "observation_evidence_refs")
    declared_sources = {
        (reference["kind"], reference["id"]) for reference in request["source_snapshot_refs"]
    }

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
    facts_by_id: dict[str, dict[str, Any]] = {}
    bindings_by_id: dict[str, dict[str, Any]] = {}
    failure_status: str | None = None
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
        if outcome in {"FAILED", "BLOCKED", "INCOMPLETE", "UNKNOWN"}:
            failure_status = outcome
        for raw in occurrence.get("facts", []):
            if not subject_in_scope(raw["subject"], scope):
                raise ObservationError(f"Fact subject is outside scope: {raw['subject']}")
            fact = normalize_fact(raw, request["project_id"], profile)
            existing = facts_by_id.get(fact["fact_id"])
            if existing is not None and existing != fact:
                raise ObservationError(f"Fact identity collision: {fact['fact_id']}")
            facts_by_id[fact["fact_id"]] = fact
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

    facts = sorted(facts_by_id.values(), key=lambda item: item["fact_id"])
    bindings = sorted(bindings_by_id.values(), key=lambda item: item["binding_id"])
    attempts = deepcopy(request.get("attempts", []))
    blind_spots = deepcopy(request.get("blind_spots", []))
    if failure_status:
        status = failure_status
    elif facts:
        status = "COMPLETE"
    elif request.get("collection_complete") is True:
        status = "EMPTY"
    else:
        status = "UNKNOWN"
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
        "normalized_fact_refs": [_ref("normalized_fact", fact["fact_id"]) for fact in facts],
        "status": status,
        "blind_spots": {
            "status": "KNOWN_BLIND_SPOTS_PRESENT" if blind_spots else "NONE_KNOWN",
            "items": blind_spots,
        },
        "attempts": attempts,
        "observation_evidence_refs": deepcopy(request.get("observation_evidence_refs", [])),
    }
    fact_evaluations = []
    for fact in facts:
        fact_bindings = [binding for binding in bindings if binding["fact_id"] == fact["fact_id"]]
        fact_evaluations.append(
            {
                "schema_version": "0.1",
                "evaluation_id": deterministic_id(
                    "FACT-EVAL", {"fact_id": fact["fact_id"], "evaluation_revision": 0}
                ),
                "fact_id": fact["fact_id"],
                "evaluation_revision": 0,
                "previous_evaluation_id": None,
                "binding_refs": [
                    _ref("fact_observation_binding", binding["binding_id"])
                    for binding in fact_bindings
                ],
                "evaluation_status": "SUPPORTED",
                "conflict_fact_refs": [],
                "conflict_negative_observation_refs": [],
                "evidence_refs": deepcopy(request.get("observation_evidence_refs", [])),
            }
        )
    negatives: list[dict[str, Any]] = []
    negative_evaluations: list[dict[str, Any]] = []
    conflict_found = False
    for claim in request.get("negative_claims", []):
        negative, evaluation, conflict = _negative_records(
            claim=claim,
            observation=observation,
            facts=facts,
            evidence_refs=request.get("observation_evidence_refs", []),
        )
        negatives.append(negative)
        negative_evaluations.append(evaluation)
        if conflict:
            conflict_found = True
            for fact_evaluation in fact_evaluations:
                if fact_evaluation["fact_id"] in conflict["fact_ids"]:
                    fact_evaluation["evaluation_status"] = "CONFLICTED"
                    fact_evaluation["conflict_negative_observation_refs"].append(
                        _ref("negative_observation", conflict["negative_id"])
                    )
                    fact_evaluation["conflict_negative_observation_refs"].sort(
                        key=lambda reference: reference["id"]
                    )
    if conflict_found:
        observation["status"] = "CONFLICTED"
    bundle = {
        "facts": facts,
        "observations": [observation],
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
