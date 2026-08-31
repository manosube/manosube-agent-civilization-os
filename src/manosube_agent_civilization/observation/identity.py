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
