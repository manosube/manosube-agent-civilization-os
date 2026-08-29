"""Deterministic fixture normalization for Observation v0.1."""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .errors import ObservationError, UnsupportedProfileError
from .identity import deterministic_id

SUPPORTED_PROFILE = "FIXTURE-0.1"
VALUE_TYPES = {
    "NULL",
    "BOOLEAN",
    "INTEGER",
    "DECIMAL",
    "STRING",
    "TIMESTAMP",
    "DURATION",
    "IDENTITY_REFERENCE",
    "ORDERED_COLLECTION",
    "UNORDERED_COLLECTION",
    "STRUCTURED",
}


def normalize_fact(raw: dict[str, Any], project_id: str, profile: str) -> dict[str, Any]:
    if profile != SUPPORTED_PROFILE:
        raise UnsupportedProfileError(f"unsupported normalization profile: {profile}")
    value_type = raw.get("value_type")
    if value_type not in VALUE_TYPES:
        raise ObservationError(f"unknown value_type: {value_type!r}")
    semantic = {
        "project_id": project_id,
        "subject": raw["subject"],
        "predicate": raw["predicate"],
        "value": raw["value"],
        "value_type": value_type,
        "unit": raw.get("unit"),
        "effective_boundary": raw["effective_boundary"],
        "normalization_profile": profile,
    }
    canonical_json_bytes(semantic)
    return {
        "schema_version": "0.1",
        "fact_id": deterministic_id("FACT", semantic),
        **semantic,
    }
