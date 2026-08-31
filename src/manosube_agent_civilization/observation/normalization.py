"""Deterministic fixture normalization for Observation v0.1."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
import re
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .errors import ObservationError, UnsupportedProfileError
from .identity import fact_identity, fact_semantic_projection

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
PREDICATE_VOCABULARY = frozenset({"equals@v1", "exists@v1", "members@v1"})
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_DURATION = re.compile(r"^P(?=\d|T\d)(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?$")


def _validate_value_type(value: Any, value_type: str) -> None:
    valid = {
        "NULL": value is None,
        "BOOLEAN": isinstance(value, bool),
        "INTEGER": isinstance(value, int) and not isinstance(value, bool),
        "DECIMAL": isinstance(value, str) and bool(_DECIMAL.fullmatch(value)),
        "STRING": isinstance(value, str),
        "TIMESTAMP": isinstance(value, str),
        "DURATION": isinstance(value, str) and bool(_DURATION.fullmatch(value)),
        "IDENTITY_REFERENCE": isinstance(value, dict)
        and set(value) == {"kind", "id"}
        and all(isinstance(item, str) and item for item in value.values()),
        "ORDERED_COLLECTION": isinstance(value, list),
        "UNORDERED_COLLECTION": isinstance(value, list),
        "STRUCTURED": isinstance(value, dict),
    }[value_type]
    if value_type == "TIMESTAMP" and valid:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            valid = False
    if not valid:
        raise ObservationError(f"value does not conform to declared type {value_type}")


def normalize_fact(raw: dict[str, Any], project_id: str, profile: str) -> dict[str, Any]:
    if profile != SUPPORTED_PROFILE:
        raise UnsupportedProfileError(f"unsupported normalization profile: {profile}")
    value_type = raw.get("value_type")
    if value_type not in VALUE_TYPES:
        raise ObservationError(f"unknown value_type: {value_type!r}")
    if raw.get("predicate") not in PREDICATE_VOCABULARY:
        raise ObservationError(f"unknown predicate: {raw.get('predicate')!r}")
    value = deepcopy(raw["value"])
    _validate_value_type(value, value_type)
    if value_type == "TIMESTAMP":
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ObservationError("TIMESTAMP requires an explicit UTC offset")
        value = instant.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if value_type == "UNORDERED_COLLECTION":
        if not isinstance(value, list):
            raise ObservationError("UNORDERED_COLLECTION value must be an array")
        encoded = [canonical_json_bytes(item) for item in value]
        if len(encoded) != len(set(encoded)):
            raise ObservationError("UNORDERED_COLLECTION contains duplicate canonical members")
        value = [item for _, item in sorted(zip(encoded, value, strict=True))]
    value = json.loads(canonical_json_bytes(value))
    semantic = fact_semantic_projection(
        {
            "project_id": project_id,
            "subject": raw["subject"],
            "predicate": raw["predicate"],
            "value": value,
            "value_type": value_type,
            "unit": raw.get("unit"),
            "effective_boundary": raw["effective_boundary"],
            "normalization_profile": profile,
        }
    )
    semantic = json.loads(canonical_json_bytes(semantic))
    return {
        "schema_version": "0.1",
        "fact_id": fact_identity(semantic),
        **semantic,
    }
