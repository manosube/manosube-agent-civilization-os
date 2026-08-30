"""Deterministic fixture normalization for Observation v0.1."""

from __future__ import annotations

from copy import deepcopy
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
    value = deepcopy(raw["value"])
    if value_type == "UNORDERED_COLLECTION":
        if not isinstance(value, list):
            raise ObservationError("UNORDERED_COLLECTION value must be an array")
        encoded = [canonical_json_bytes(item) for item in value]
        if len(encoded) != len(set(encoded)):
            raise ObservationError("UNORDERED_COLLECTION contains duplicate canonical members")
        value = [item for _, item in sorted(zip(encoded, value, strict=True))]
    semantic = {
        "project_id": project_id,
        "subject": raw["subject"],
        "predicate": raw["predicate"],
        "value": value,
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
