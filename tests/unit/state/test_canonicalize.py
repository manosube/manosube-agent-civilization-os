from __future__ import annotations

from copy import deepcopy

import pytest

from manosube_agent_civilization.state.canonicalize import (
    canonical_json_bytes,
    canonical_semantic_state_bytes,
)
from manosube_agent_civilization.state.errors import (
    AmbiguousCollectionError,
    InvalidUnicodeError,
    NonStringKeyError,
    SchemaValidationError,
    SecretFieldError,
    UnsupportedValueError,
)
from tests.state_helpers import SCHEMA_ROOT, initial_state


def test_object_key_order_is_not_semantic() -> None:
    assert canonical_json_bytes({"b": 2, "a": 1}) == canonical_json_bytes({"a": 1, "b": 2})


def test_unicode_is_normalized_to_nfc() -> None:
    assert canonical_json_bytes({"label": "e\u0301"}) == canonical_json_bytes({"label": "é"})


def test_declared_set_input_order_is_not_semantic() -> None:
    left = initial_state()
    right = deepcopy(left)
    refs = [
        {"kind": "difference", "id": "DIFF-0002"},
        {"kind": "difference", "id": "DIFF-0001"},
    ]
    left["semantic_state"]["open_differences"] = refs
    right["semantic_state"]["open_differences"] = list(reversed(refs))
    assert canonical_semantic_state_bytes(left, schema_root=SCHEMA_ROOT) == (
        canonical_semantic_state_bytes(right, schema_root=SCHEMA_ROOT)
    )


def test_ordered_sequence_order_is_semantic() -> None:
    assert canonical_json_bytes({"ordered": [1, 2]}) != canonical_json_bytes(
        {"ordered": [2, 1]}
    )


def test_metadata_is_excluded_from_semantic_bytes() -> None:
    left = initial_state()
    right = deepcopy(left)
    right["state_metadata"]["observed_at"] = "2026-08-30T00:00:00Z"
    right["state_metadata"]["producer"] = "different-agent"
    right["state_metadata"]["execution_context"]["session_id"] = "different-session"
    assert canonical_semantic_state_bytes(left, schema_root=SCHEMA_ROOT) == (
        canonical_semantic_state_bytes(right, schema_root=SCHEMA_ROOT)
    )


def test_input_is_not_mutated() -> None:
    state = initial_state()
    before = deepcopy(state)
    canonical_semantic_state_bytes(state, schema_root=SCHEMA_ROOT)
    assert state == before


@pytest.mark.parametrize("value", [1.5, float("nan"), float("inf"), -0.0])
def test_float_values_are_rejected(value: float) -> None:
    with pytest.raises(UnsupportedValueError):
        canonical_json_bytes(value)


@pytest.mark.parametrize("value", [b"bytes", (1, 2), {1, 2}, object()])
def test_non_json_values_are_rejected(value: object) -> None:
    with pytest.raises(UnsupportedValueError):
        canonical_json_bytes(value)


def test_non_string_key_is_rejected() -> None:
    with pytest.raises(NonStringKeyError):
        canonical_json_bytes({1: "value"})


def test_unpaired_surrogate_is_rejected() -> None:
    with pytest.raises(InvalidUnicodeError):
        canonical_json_bytes({"value": "\ud800"})


@pytest.mark.parametrize("key", ["password", "api-key", "Authorization Header", "token"])
def test_secret_bearing_key_is_rejected(key: str) -> None:
    with pytest.raises(SecretFieldError):
        canonical_json_bytes({key: "redacted"})


def test_duplicate_set_element_is_rejected() -> None:
    with pytest.raises(AmbiguousCollectionError):
        canonical_json_bytes({"evidence_refs": [{"kind": "evidence", "id": "EVID-1"}] * 2})


def test_unknown_schema_field_fails_closed() -> None:
    state = initial_state()
    state["semantic_state"]["observed_at"] = "2026-08-29T00:00:00Z"
    with pytest.raises(SchemaValidationError):
        canonical_semantic_state_bytes(state, schema_root=SCHEMA_ROOT)


def test_unknown_schema_version_fails_closed() -> None:
    state = initial_state()
    state["schema_version"] = "9.9"
    with pytest.raises(SchemaValidationError):
        canonical_semantic_state_bytes(state, schema_root=SCHEMA_ROOT)
