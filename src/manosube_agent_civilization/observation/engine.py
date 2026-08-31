"""Deterministic, adapter-free Observation Engine for the v0.1 fixture route."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from .boundary import fact_boundary_observed, instant, time_boundary_within_scope
from .errors import ObservationError, ObservationValidationError
from .identity import deterministic_id, observation_identity
from .normalization import PREDICATE_VOCABULARY, SUPPORTED_PROFILE, normalize_fact
from .schemas import OBSERVATION_SCHEMA_BASE, validators
from .scope import subject_in_scope, validate_scope, validate_source_locator
from .verification import observation_record_errors

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


def _ref(kind: str, identity: str) -> dict[str, str]:
    return {"kind": kind, "id": identity}


def _require_ref_kind(reference: dict[str, str], expected: str, context: str) -> None:
    if reference.get("kind") != expected:
        raise ObservationError(
            f"reference kind mismatch at {context}: expected={expected} "
            f"actual={reference.get('kind')}"
        )


def _boundary_observed(boundary: dict[str, Any], observation: dict[str, Any]) -> bool:
    """Delegate to the single canonical Fact boundary authority."""

    return fact_boundary_observed(boundary, observation)


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


def _completion(
    status: str,
    observation: dict[str, Any],
    scope: dict[str, Any],
    collection_complete: bool,
    claim: dict[str, Any] | None = None,
    facts: list[dict[str, Any]] | None = None,
) -> dict[str, bool]:
    attempts = observation["attempts"]
    observation_start = instant(observation["time_boundary"]["observation_started_at"])
    observation_end = instant(observation["time_boundary"]["observation_ended_at"])
    attempts_complete = (
        bool(attempts)
        and all(
            attempt["result"] in {"COMPLETE", "EMPTY"}
            and attempt["method_ref"] == observation["method_ref"]
            and observation_start
            <= instant(attempt["started_at"])
            <= instant(attempt["ended_at"])
            <= observation_end
            for attempt in attempts
        )
        and len(attempts) <= scope["attempt_policy"]["max_attempts"]
        and all(
            (instant(attempt["ended_at"]) - instant(attempt["started_at"])).total_seconds()
            <= scope["attempt_policy"]["timeout_seconds"]
            for attempt in attempts
        )
    )
    method_complete = attempts_complete and observation["status"] in {"COMPLETE", "EMPTY"}
    no_blocking_blind_spot = all(
        item["impact"] != "BLOCKS_COMPLETION"
        and not (
            item["impact"] == "BLOCKS_ABSENCE"
            and claim is not None
            and (claim["subject"] in item["affected_subjects"] or "*" in item["affected_subjects"])
        )
        for item in observation["blind_spots"]["items"]
    )
    base: dict[str, bool] = {
        "target_defined": True,
        "scope_complete": scope["scope_status"] == "COMPLETE",
        "method_complete": method_complete,
        "time_boundary_complete": time_boundary_within_scope(observation, scope),
        "source_snapshots_identified": bool(observation["source_snapshot_refs"]),
        "required_attempts_completed": method_complete,
        "no_blocking_blind_spot": no_blocking_blind_spot,
        "no_conflicting_positive_fact": True,
    }
    if status == "EMPTY":
        matching_fact_exists = bool(
            claim
            and facts
            and any(
                fact["subject"] == claim["subject"]
                and fact["predicate"] == claim["predicate"]
                and fact["effective_boundary"] == claim["effective_boundary"]
                for fact in facts
            )
        )
        base["collection_defined"] = collection_complete
        base["enumeration_complete"] = collection_complete
        base["zero_valid_members"] = collection_complete and not matching_fact_exists
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
    if claim.get("predicate") not in PREDICATE_VOCABULARY:
        raise ObservationError(f"unknown predicate: {claim.get('predicate')!r}")
    boundary = claim["effective_boundary"]
    if not _boundary_observed(boundary, observation):
        raise ObservationError("Negative claim effective boundary was not observed")
    requested_status = status
    requested_completion = _completion(
        requested_status,
        observation,
        scope,
        collection_complete,
        claim=claim,
        facts=facts,
    )
    if requested_status == "ABSENT" and not all(requested_completion.values()):
        raise ObservationError("ABSENT requires a complete bounded absence gate")
    if requested_status == "EMPTY" and not all(requested_completion.values()):
        raise ObservationError("EMPTY requires complete zero-member enumeration")
    if requested_status in {"ABSENT", "EMPTY"} and not evidence_refs:
        raise ObservationError(f"{requested_status} requires bounded negative Evidence")
    conflicts = [
        fact
        for fact in facts
        if fact["subject"] == claim["subject"]
        and fact["predicate"] == claim["predicate"]
        and fact["effective_boundary"] == claim["effective_boundary"]
    ]
    if conflicts:
        status = "CONFLICTED"
    completion = _completion(
        status, observation, scope, collection_complete, claim=claim, facts=facts
    )
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
    """Apply the single canonical cross-record Observation verification authority."""

    errors = observation_record_errors(bundle)
    if errors:
        raise ObservationValidationError(sorted(errors)[0])


def _validate_scope_record(scope: dict[str, Any]) -> None:
    validator = validators()[OBSERVATION_SCHEMA_BASE + "observation_scope.schema.json"]
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
    canonical_source_refs = sorted(
        deepcopy(request["source_snapshot_refs"]),
        key=lambda reference: (reference["kind"], reference["id"]),
    )
    for reference in canonical_source_refs:
        _require_ref_kind(reference, "source_snapshot", "source_snapshot_refs")
    canonical_observation_evidence_refs = sorted(
        deepcopy(request.get("observation_evidence_refs", [])),
        key=lambda reference: (reference["kind"], reference["id"]),
    )
    for reference in canonical_observation_evidence_refs:
        _require_ref_kind(reference, "observation_evidence", "observation_evidence_refs")
    for reference in request.get("negative_evidence_refs", []):
        _require_ref_kind(reference, "negative_evidence", "negative_evidence_refs")
    scope_sources = {
        (reference["kind"], reference["id"]) for reference in scope["source_snapshot_refs"]
    }
    declared_sources = {(reference["kind"], reference["id"]) for reference in canonical_source_refs}
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

    # The identity-bearing half of the Observation record is built first, so the identity
    # is minted through the same single projection any consumer re-derives it with.
    observation_identity_payload = {
        "project_id": request["project_id"],
        "state_revision_observed": state_revision,
        "state_fingerprint_observed": state_fingerprint,
        "target": {"target_identity": request["target_identity"], "kind": request["target_kind"]},
        "scope_ref": _ref("observation_scope", scope["scope_id"]),
        "method_ref": deepcopy(request["method_ref"]),
        "time_boundary": deepcopy(request["time_boundary"]),
        "source_snapshot_refs": canonical_source_refs,
        "normalization_profile": profile,
    }
    observation_id = observation_identity(observation_identity_payload)
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
            raw_boundary = raw["effective_boundary"]
            if (
                raw_boundary["kind"] == "SOURCE_SNAPSHOT"
                and raw_boundary["identity"] != occurrence["source_ref"]["id"]
            ):
                raise ObservationError("Fact source boundary does not match its source occurrence")
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
        **deepcopy(observation_identity_payload),
        "normalized_fact_refs": [
            _ref("normalized_fact", fact["fact_id"]) for fact in observed_facts
        ],
        "status": status,
        "blind_spots": {
            "status": "KNOWN_BLIND_SPOTS_PRESENT" if blind_spots else "NONE_KNOWN",
            "items": blind_spots,
        },
        "attempts": attempts,
        "observation_evidence_refs": canonical_observation_evidence_refs,
    }
    base_observation_status = observation["status"]
    for fact in observed_facts:
        if not _boundary_observed(fact["effective_boundary"], observation):
            raise ObservationError("Fact effective boundary was not observed")
    coordinates: dict[str, int] = {}
    for fact in facts:
        coordinate = json.dumps(
            [fact["subject"], fact["predicate"], fact["effective_boundary"]],
            sort_keys=True,
            separators=(",", ":"),
        )
        coordinates[coordinate] = coordinates.get(coordinate, 0) + 1
    observed_coordinates = {
        json.dumps(
            [fact["subject"], fact["predicate"], fact["effective_boundary"]],
            sort_keys=True,
            separators=(",", ":"),
        )
        for fact in observed_facts
    }
    has_retry_conflict = any(
        count > 1 and coordinate in observed_coordinates
        for coordinate, count in coordinates.items()
    ) or any(
        fact["subject"] == negative["subject"]
        and fact["predicate"] == negative["predicate"]
        and fact["effective_boundary"] == negative["effective_boundary"]
        for fact in observed_facts
        for negative in prior["negative_observations"]
    )
    if has_retry_conflict:
        observation["status"] = "CONFLICTED"
    existing_observation = next(
        (item for item in prior["observations"] if item["observation_id"] == observation_id), None
    )
    prior_binding_ids = {item["binding_id"] for item in prior["bindings"]}
    if existing_observation is not None:
        retry_fact_ids = {
            item["fact_id"] for item in bindings if item["observation_id"] == observation_id
        }
        retry_facts = [fact for fact in facts if fact["fact_id"] in retry_fact_ids]
        retry_coordinates: dict[str, int] = {}
        for fact in retry_facts:
            coordinate = json.dumps(
                [fact["subject"], fact["predicate"], fact["effective_boundary"]],
                sort_keys=True,
                separators=(",", ":"),
            )
            retry_coordinates[coordinate] = retry_coordinates.get(coordinate, 0) + 1
        retry_has_conflict = any(count > 1 for count in retry_coordinates.values()) or any(
            fact["subject"] == negative["subject"]
            and fact["predicate"] == negative["predicate"]
            and fact["effective_boundary"] == negative["effective_boundary"]
            for fact in retry_facts
            for negative in prior["negative_observations"]
            if negative["observation_id"] == observation_id
        )
        observation["status"] = "CONFLICTED" if retry_has_conflict else status
        requested_negative_ids = {
            deterministic_id(
                "NEG",
                {
                    "observation_id": observation_id,
                    "subject": claim["subject"],
                    "predicate": claim["predicate"],
                    "effective_boundary": claim["effective_boundary"],
                },
            )
            for claim in request.get("negative_claims", [])
        }
        prior_negatives_for_observation = {
            item["negative_observation_id"]
            for item in prior["negative_observations"]
            if item["observation_id"] == observation_id
        }
        retry_negative_equivalent = True
        prior_negative_index = {
            item["negative_observation_id"]: item
            for item in prior["negative_observations"]
            if item["observation_id"] == observation_id
        }
        for claim in request.get("negative_claims", []):
            negative_id = deterministic_id(
                "NEG",
                {
                    "observation_id": observation_id,
                    "subject": claim["subject"],
                    "predicate": claim["predicate"],
                    "effective_boundary": claim["effective_boundary"],
                },
            )
            existing_negative = prior_negative_index.get(negative_id)
            retry_observation = deepcopy(observation)
            retry_observation["status"] = base_observation_status
            expected_negative, _, _ = _negative_records(
                claim=claim,
                observation=retry_observation,
                scope=scope,
                facts=retry_facts,
                evidence_refs=request.get("negative_evidence_refs", []),
                collection_complete=collection_complete,
            )
            if existing_negative != expected_negative:
                retry_negative_equivalent = False
        if (
            existing_observation != observation
            or not new_binding_ids <= prior_binding_ids
            or requested_negative_ids != prior_negatives_for_observation
            or not retry_negative_equivalent
        ):
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
        fact["fact_id"]: {
            other["fact_id"] for other in group if other["fact_id"] != fact["fact_id"]
        }
        for group in coordinate_groups.values()
        if len(group) > 1 and any(item["fact_id"] in observed_fact_ids for item in group)
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
                _ref("fact_observation_binding", binding["binding_id"]) for binding in fact_bindings
            ],
            "evaluation_status": "CONFLICTED"
            if prior_negative_conflicts or conflict_fact_ids
            else "SUPPORTED",
            "conflict_fact_refs": [
                _ref("normalized_fact", item) for item in sorted(conflict_fact_ids)
            ],
            "conflict_negative_observation_refs": prior_negative_conflicts,
            "evidence_refs": deepcopy(canonical_observation_evidence_refs),
        }
        fact_evaluations.append(new_evaluation)
        appended_fact_evaluations[fact["fact_id"]] = new_evaluation
    for fact_id, conflict_ids in positive_conflicts.items():
        if fact_id in appended_fact_evaluations:
            continue
        previous = sorted(
            (item for item in fact_evaluations if item["fact_id"] == fact_id),
            key=lambda item: item["evaluation_revision"],
        )
        revision = len(previous)
        new_evaluation = {
            "schema_version": "0.1",
            "evaluation_id": deterministic_id(
                "FACT-EVAL", {"fact_id": fact_id, "evaluation_revision": revision}
            ),
            "fact_id": fact_id,
            "evaluation_revision": revision,
            "previous_evaluation_id": previous[-1]["evaluation_id"] if previous else None,
            "binding_refs": [],
            "evaluation_status": "CONFLICTED",
            "conflict_fact_refs": [_ref("normalized_fact", item) for item in sorted(conflict_ids)],
            "conflict_negative_observation_refs": (
                deepcopy(previous[-1]["conflict_negative_observation_refs"]) if previous else []
            ),
            "evidence_refs": deepcopy(canonical_observation_evidence_refs),
        }
        fact_evaluations.append(new_evaluation)
        appended_fact_evaluations[fact_id] = new_evaluation
    negatives = deepcopy(prior["negative_observations"])
    negative_evaluations = deepcopy(prior["negative_evaluations"])
    conflict_found = False
    for negative in prior["negative_observations"]:
        matching = [
            fact
            for fact in observed_facts
            if fact["subject"] == negative["subject"]
            and fact["predicate"] == negative["predicate"]
            and fact["effective_boundary"] == negative["effective_boundary"]
        ]
        if not matching:
            continue
        conflict_found = True
        prior_negative_evaluations = sorted(
            (
                item
                for item in negative_evaluations
                if item["negative_observation_id"] == negative["negative_observation_id"]
            ),
            key=lambda item: item["evaluation_revision"],
        )
        revision = len(prior_negative_evaluations)
        negative_evaluations.append(
            {
                "schema_version": "0.1",
                "evaluation_id": deterministic_id(
                    "NEG-EVAL",
                    {
                        "negative_observation_id": negative["negative_observation_id"],
                        "evaluation_revision": revision,
                    },
                ),
                "negative_observation_id": negative["negative_observation_id"],
                "evaluation_revision": revision,
                "previous_evaluation_id": prior_negative_evaluations[-1]["evaluation_id"],
                "evaluation_status": "CONFLICTED",
                "conflict_fact_refs": sorted(
                    {
                        reference["id"]: reference
                        for reference in [
                            *prior_negative_evaluations[-1]["conflict_fact_refs"],
                            *[_ref("normalized_fact", fact["fact_id"]) for fact in matching],
                        ]
                    }.values(),
                    key=lambda reference: reference["id"],
                ),
                "evidence_refs": deepcopy(canonical_observation_evidence_refs),
            }
        )
        for fact in matching:
            fact_evaluation = appended_fact_evaluations[fact["fact_id"]]
            reference = _ref("negative_observation", negative["negative_observation_id"])
            fact_evaluation["evaluation_status"] = "CONFLICTED"
            if reference not in fact_evaluation["conflict_negative_observation_refs"]:
                fact_evaluation["conflict_negative_observation_refs"].append(reference)
                fact_evaluation["conflict_negative_observation_refs"].sort(
                    key=lambda item: item["id"]
                )
    for claim in request.get("negative_claims", []):
        if not subject_in_scope(claim["subject"], scope):
            raise ObservationError(f"Negative claim subject is outside scope: {claim['subject']}")
        claim_observation = deepcopy(observation)
        claim_observation["status"] = base_observation_status
        negative, evaluation, conflict = _negative_records(
            claim=claim,
            observation=claim_observation,
            scope=scope,
            facts=facts,
            evidence_refs=request.get("negative_evidence_refs", []),
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
                        "evaluation_id": deterministic_id(
                            "FACT-EVAL", {"fact_id": fact_id, "evaluation_revision": revision}
                        ),
                        "fact_id": fact_id,
                        "evaluation_revision": revision,
                        "previous_evaluation_id": previous[-1]["evaluation_id"]
                        if previous
                        else None,
                        "binding_refs": [],
                        "evaluation_status": "CONFLICTED",
                        "conflict_fact_refs": deepcopy(previous[-1]["conflict_fact_refs"])
                        if previous
                        else [],
                        "conflict_negative_observation_refs": deepcopy(
                            previous[-1]["conflict_negative_observation_refs"]
                        )
                        if previous
                        else [],
                        "evidence_refs": deepcopy(canonical_observation_evidence_refs),
                    }
                    fact_evaluations.append(fact_evaluation)
                    appended_fact_evaluations[fact_id] = fact_evaluation
                fact_evaluation["evaluation_status"] = "CONFLICTED"
                reference = _ref("negative_observation", conflict["negative_id"])
                if reference not in fact_evaluation["conflict_negative_observation_refs"]:
                    fact_evaluation["conflict_negative_observation_refs"].append(
                        _ref("negative_observation", conflict["negative_id"])
                    )
                fact_evaluation["conflict_negative_observation_refs"].sort(
                    key=lambda reference: reference["id"]
                )
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
