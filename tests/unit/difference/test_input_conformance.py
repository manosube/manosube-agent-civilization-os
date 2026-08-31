"""Every current-derivation input is validated before any semantic field is read.

Covers the independent review finding on `2eae0b7`: the requested Objective revision was
checked only for `schema_version`, so a record missing a required field could be consumed
and copied into a returned bundle that violates its own canonical schema.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import observation_scope, single_binding_request

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.conformance import (
    OBJECTIVE_BASE,
    validate_typed_record,
)
from manosube_agent_civilization.difference.validation import validate_record
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[3]
_OBJECTIVE_SCHEMA = json.loads(
    (ROOT / "01_SCHEMA" / "objective" / "objective_revision.schema.json").read_text(
        encoding="utf-8"
    )
)
_OBJECTIVE_FIELDS_SCHEMA = json.loads(
    (ROOT / "01_SCHEMA" / "objective" / "objective.schema.json").read_text(encoding="utf-8")
)


def _required_objective_fields() -> list[str]:
    """Read the required set out of the composed schema, both halves of the allOf."""

    required: set[str] = set()
    for clause in _OBJECTIVE_SCHEMA["allOf"]:
        required |= set(clause.get("required", []))
    required |= set(_OBJECTIVE_FIELDS_SCHEMA["$defs"]["fields"].get("required", []))
    return sorted(required)


_REQUIRED_OBJECTIVE_FIELDS = _required_objective_fields()


def test_the_schema_really_requires_the_fields_under_test() -> None:
    assert "recorded_at" in _REQUIRED_OBJECTIVE_FIELDS
    assert len(_REQUIRED_OBJECTIVE_FIELDS) >= 15


@pytest.mark.parametrize("field", _REQUIRED_OBJECTIVE_FIELDS)
def test_every_required_objective_field_removed_one_at_a_time_fails_closed(field: str) -> None:
    request = single_binding_request()
    del request["objective_revision"][field]
    with pytest.raises(DifferenceError):
        derive_differences(request)


_OBJECTIVE_MUTATIONS: list[tuple[str, Any]] = [
    # identity-bearing / semantic
    ("objective_revision_id", 17),
    ("objective_id", None),
    ("revision", "zero"),
    ("target_predicates", "not-a-list"),
    ("completion_policy", {"mode": "NOT_A_MODE", "contradiction_policy": "BLOCK"}),
    # non-identity required fields
    ("recorded_at", "not-a-timestamp"),
    ("status", "NOT_A_STATUS"),
    ("change_reason", 17),
    ("owner_authority_ref", "not-a-reference"),
    ("semantic_change_summary", []),
]


@pytest.mark.parametrize(
    ("field", "value"), _OBJECTIVE_MUTATIONS, ids=[case[0] for case in _OBJECTIVE_MUTATIONS]
)
def test_a_malformed_objective_field_fails_closed(field: str, value: Any) -> None:
    request = single_binding_request()
    request["objective_revision"][field] = deepcopy(value)
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_an_undeclared_objective_field_fails_closed() -> None:
    request = single_binding_request()
    request["objective_revision"]["smuggled_field"] = "x"
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_a_wrong_objective_schema_version_fails_closed() -> None:
    request = single_binding_request()
    request["objective_revision"]["schema_version"] = "0.2"
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_the_valid_objective_is_accepted_and_returned_unchanged() -> None:
    request = single_binding_request()
    original = deepcopy(request["objective_revision"])
    bundle = derive_differences(request)
    returned = bundle["objective_revisions"]
    assert len(returned) == 1
    assert canonical_json_bytes(returned[0]) == canonical_json_bytes(original)


def test_the_returned_objective_always_passes_its_own_schema() -> None:
    """The defect was a returned bundle whose Objective violated its canonical schema."""

    bundle = derive_differences(single_binding_request())
    for revision in bundle["objective_revisions"]:
        validate_record(revision, "objective_revision.schema.json", base=OBJECTIVE_BASE)
        validate_typed_record(revision, "objective_revision", "returned objective")
    assert validate_bundle(bundle) == []


# --------------------------------------------------------------------------- #
# The Observation Scope input, and the State fingerprint input.
# --------------------------------------------------------------------------- #

_SCOPE_MUTATIONS: list[tuple[str, Any]] = [
    ("scope_id", 17),
    ("scope_status", "NOT_A_STATUS"),
    ("freshness_limit_seconds", "300"),
    ("cutoff", "not-a-timestamp"),
    ("included_subjects", "not-a-list"),
]


@pytest.mark.parametrize(
    ("field", "value"), _SCOPE_MUTATIONS, ids=[case[0] for case in _SCOPE_MUTATIONS]
)
def test_a_malformed_observation_scope_fails_closed(field: str, value: Any) -> None:
    request = single_binding_request()
    request["bindings"][0]["observation_scope"][field] = deepcopy(value)
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_a_scope_missing_a_required_field_fails_closed() -> None:
    request = single_binding_request()
    del request["bindings"][0]["observation_scope"]["cutoff"]
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_an_undeclared_scope_field_fails_closed() -> None:
    request = single_binding_request()
    request["bindings"][0]["observation_scope"]["smuggled_field"] = "x"
    with pytest.raises(DifferenceError):
        derive_differences(request)


_FINGERPRINT_MUTATIONS: list[tuple[str, Any]] = [
    ("digest", "short"),
    ("digest", 17),
    ("profile", "NOT-A-PROFILE"),
]


@pytest.mark.parametrize(
    ("field", "value"), _FINGERPRINT_MUTATIONS, ids=[f"{c[0]}={c[1]}" for c in _FINGERPRINT_MUTATIONS]
)
def test_a_malformed_state_fingerprint_fails_closed(field: str, value: Any) -> None:
    request = single_binding_request()
    request["state_fingerprint"][field] = deepcopy(value)
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_a_state_fingerprint_missing_a_required_field_fails_closed() -> None:
    request = single_binding_request()
    del request["state_fingerprint"]["digest"]
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_the_valid_scope_is_returned_unchanged() -> None:
    request = single_binding_request()
    original = deepcopy(request["bindings"][0]["observation_scope"])
    bundle = derive_differences(request)
    returned = [
        item for item in bundle["observation_scopes"] if item["scope_id"] == original["scope_id"]
    ]
    assert len(returned) == 1
    assert canonical_json_bytes(returned[0]) == canonical_json_bytes(original)


def test_the_helper_scope_is_the_one_under_test() -> None:
    assert observation_scope()["scope_id"] == "OBS-SCOPE-0001"
