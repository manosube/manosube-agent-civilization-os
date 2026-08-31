"""Deterministic identities for canonical Observation records."""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

_DOMAIN = b"MANOSUBE_AGENT_CIVILIZATION_OS\x00OBSERVATION\x000.1\x00"


def deterministic_id(prefix: str, value: Any) -> str:
    """Return a stable, domain-separated identity for canonical *value*."""

    digest = hashlib.sha256(_DOMAIN + canonical_json_bytes(value)).hexdigest().upper()
    return f"{prefix}-{digest}"


FACT_SEMANTIC_FIELDS = (
    "project_id",
    "subject",
    "predicate",
    "value",
    "value_type",
    "unit",
    "effective_boundary",
    "normalization_profile",
)


def fact_semantic_projection(fact: dict[str, Any]) -> dict[str, Any]:
    """Return the closed semantic identity input of a Normalized Fact."""

    return {key: fact[key] for key in FACT_SEMANTIC_FIELDS}


def fact_identity(fact: dict[str, Any]) -> str:
    """Return the canonical identity a Normalized Fact's own payload implies."""

    return deterministic_id("FACT", fact_semantic_projection(fact))


def binding_identity(binding: dict[str, Any]) -> str:
    """Return the canonical identity a Fact Observation Binding's payload implies."""

    return deterministic_id(
        "BIND",
        {
            key: binding[key]
            for key in ("fact_id", "observation_id", "source_occurrence_id")
        },
    )


def fact_evaluation_identity(evaluation: dict[str, Any]) -> str:
    """Return the canonical identity a Fact evaluation's payload implies."""

    return deterministic_id(
        "FACT-EVAL",
        {
            "fact_id": evaluation["fact_id"],
            "evaluation_revision": evaluation["evaluation_revision"],
        },
    )


OBSERVATION_SEMANTIC_FIELDS = (
    "project_id",
    "state_revision_observed",
    "state_fingerprint_observed",
    "target_identity",
    "scope_id",
    "method_ref",
    "time_boundary",
    "source_snapshot_refs",
    "normalization_profile",
)


def observation_semantic_projection(observation: dict[str, Any]) -> dict[str, Any]:
    """Return the closed semantic identity input of an Observation record.

    The projection is read from the record itself, so the Observation Engine that mints an
    identity and any consumer that re-derives one use a single closed algorithm. ``status``,
    ``normalized_fact_refs``, ``blind_spots``, ``attempts`` and the Evidence channel are
    deliberately outside it: they are the Observation's findings, not its identity.
    """

    return {
        "project_id": observation["project_id"],
        "state_revision_observed": observation["state_revision_observed"],
        "state_fingerprint_observed": observation["state_fingerprint_observed"],
        "target_identity": observation["target"]["target_identity"],
        "scope_id": observation["scope_ref"]["id"],
        "method_ref": observation["method_ref"],
        "time_boundary": observation["time_boundary"],
        "source_snapshot_refs": observation["source_snapshot_refs"],
        "normalization_profile": observation["normalization_profile"],
    }


def observation_identity(observation: dict[str, Any]) -> str:
    """Return the canonical identity an Observation record's own payload implies."""

    return deterministic_id("OBS", observation_semantic_projection(observation))
