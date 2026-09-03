"""The Change contract, asserted where it is enforced rather than where it is written.

Every recurring defect in this repository has had one shape: **a rule asserted in one place
and enforced in another drifts, and the drift is invisible from either side.** These tests
compare the two sides directly -- the schema against the engine, the engine against the
contract's acceptance flags, and the fixtures against the record the engine actually emits --
so a future edit to one of them fails here instead of silently disagreeing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tests.authority_helpers import action, approval, scope
from tests.change_helpers import derived_difference, route

from manosube_agent_civilization.change import derive_change
from manosube_agent_civilization.change.engine import (
    AUTHORIZED,
    DECISION_REQUIRED_KEYS,
    REQUIRED_REQUEST_KEYS,
    SCHEMA_VERSION,
)
from manosube_agent_civilization.change.identity import CHANGE_SEMANTIC_FIELDS

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = ROOT / "01_SCHEMA"
CONTRACT = ROOT / "00_KERNEL" / "06_CHANGE" / "CHANGE_CONTRACT.md"
FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "schema"

CHANGE_SCHEMA_ID = (
    "https://schemas.manosube.org/agent-civilization-os/v0.1/change/change.schema.json"
)


def _schema(relative: str) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((SCHEMA_ROOT / relative).read_text(encoding="utf-8"))
    return document


CHANGE_SCHEMA = _schema("change/change.schema.json")
AUTHORITY_SCHEMA = _schema("authority/authority.schema.json")


@pytest.fixture(scope="module")
def change() -> dict[str, Any]:
    difference = derived_difference()
    requested, where = action("MERGE"), scope()
    _, _, request = route(
        difference, requested, where, approvals=[approval(difference, requested, where)]
    )
    return derive_change(request)


# --------------------------------------------------------------------------- #
# 1. the schema and the engine describe the same record
# --------------------------------------------------------------------------- #


def test_the_engine_emits_exactly_the_fields_the_schema_requires(change: dict[str, Any]) -> None:
    assert set(change) == set(CHANGE_SCHEMA["required"])


def test_the_schema_declares_a_property_for_every_required_field() -> None:
    assert set(CHANGE_SCHEMA["required"]) == set(CHANGE_SCHEMA["properties"])


def test_the_record_is_closed() -> None:
    assert CHANGE_SCHEMA["additionalProperties"] is False


def test_the_bound_decision_key_set_is_the_authority_schemas_own() -> None:
    """The engine's closed decision key set is not a remembered copy of the schema's.

    If Authority adds a field, this fails rather than the engine silently refusing every
    decision Authority now emits.
    """

    assert frozenset(AUTHORITY_SCHEMA["required"]) == DECISION_REQUIRED_KEYS


def test_the_change_schema_reuses_authoritys_action_and_scope_definitions() -> None:
    """One definition of an action and of a scope, referenced rather than restated."""

    assert CHANGE_SCHEMA["properties"]["action"]["$ref"].endswith(
        "authority/authority.schema.json#/$defs/action"
    )
    assert CHANGE_SCHEMA["properties"]["scope"]["$ref"].endswith(
        "authority/authority.schema.json#/$defs/scope"
    )


# --------------------------------------------------------------------------- #
# 2. 第24条 / 第25条: every constitutional field, and only one status
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "constitutional_field,record_field",
    [
        ("change_id", "change_id"),
        ("difference_id", "difference_ref"),
        ("before_state_fingerprint", "before_state_fingerprint"),
        ("expected_state_revision", "expected_state_revision"),
        ("authority_ref", "authority_ref"),
        ("action", "action"),
        ("idempotency_key", "idempotency_key"),
        ("execution_result", "execution_result"),
        ("status", "status"),
    ],
)
def test_every_article_24_field_is_covered(
    change: dict[str, Any], constitutional_field: str, record_field: str
) -> None:
    """第24条's nine, each mapped to the field that carries it.

    ``difference_id`` is carried by ``difference_ref.id``: v0.1 follows the ``{kind, id}``
    convention Authority already established rather than adding a second spelling for one
    relationship (``CHANGE_CONTRACT.md`` §2).
    """

    assert record_field in change
    if constitutional_field == "difference_id":
        assert change["difference_ref"]["kind"] == "difference"
        assert change["difference_ref"]["id"].startswith("D-")


def test_the_status_vocabulary_is_closed_to_the_one_value_the_engine_emits() -> None:
    assert CHANGE_SCHEMA["$defs"]["status"]["enum"] == [AUTHORIZED]


@pytest.mark.parametrize("forbidden", ["COMPLETED", "CLOSED"])
def test_the_statuses_article_25_forbids_are_not_in_the_vocabulary(forbidden: str) -> None:
    assert forbidden not in CHANGE_SCHEMA["$defs"]["status"]["enum"]


def test_execution_result_is_pinned_null_rather_than_conditionally_null() -> None:
    """The pairing is structural, and it is not guarded by a predicate nothing can reach.

    ``CHANGE_CONTRACT.md`` §4: with ``status`` closed to one value and ``execution_result``
    typed ``null``, a conditional between them has no reachable false branch. A guard no
    input can exercise reads as a check and checks nothing.
    """

    assert CHANGE_SCHEMA["properties"]["execution_result"] == {"type": "null"}
    assert "allOf" not in CHANGE_SCHEMA


# --------------------------------------------------------------------------- #
# 3. 第24条's prohibitions have no field to be said in
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "forbidden",
    [
        "after_state_fingerprint",
        "after_state_revision",
        "closes_difference",
        "difference_closure",
        "objective_completed",
        "completion",
        "evidence_ref",
        "evidence_refs",
    ],
)
def test_a_change_cannot_declare_after_state_closure_or_completion(forbidden: str) -> None:
    assert forbidden not in CHANGE_SCHEMA["properties"]
    assert forbidden not in CHANGE_SCHEMA["required"]


# --------------------------------------------------------------------------- #
# 4. identity is derived over a closed projection
# --------------------------------------------------------------------------- #


def test_every_semantic_field_is_a_field_of_the_record() -> None:
    assert set(CHANGE_SEMANTIC_FIELDS) <= set(CHANGE_SCHEMA["required"])


@pytest.mark.parametrize(
    "excluded", ["change_id", "status", "execution_result", "idempotency_key", "schema_version"]
)
def test_lifecycle_and_derived_fields_are_outside_the_identity_projection(excluded: str) -> None:
    """A Change that is later executed is the same Change. Its address must not move."""

    assert excluded not in CHANGE_SEMANTIC_FIELDS


def test_the_idempotency_key_and_the_semantic_fingerprint_are_one_computation(
    change: dict[str, Any]
) -> None:
    """``IDEMPOTENCY_KEY_DERIVED``: one answer to 'is this the same change', not two."""

    assert change["idempotency_key"] == change["change_semantic_fingerprint"]


def test_the_request_declares_no_entry_for_any_derived_field() -> None:
    """``PREEXISTING_CHANGE_ID_REQUIRED=false``, asserted against the closed key set."""

    for derived in ("change_id", "idempotency_key", "change_semantic_fingerprint", "status"):
        assert derived not in REQUIRED_REQUEST_KEYS


def test_the_engine_and_the_schema_agree_on_the_supported_version(change: dict[str, Any]) -> None:
    assert CHANGE_SCHEMA["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    assert change["schema_version"] == SCHEMA_VERSION


# --------------------------------------------------------------------------- #
# 5. the fixtures are the record the engine actually emits
# --------------------------------------------------------------------------- #


def _cases(kind: str) -> list[dict[str, Any]]:
    document: list[dict[str, Any]] = json.loads(
        (FIXTURE_ROOT / kind / "change_cases.json").read_text(encoding="utf-8")
    )
    return document


def test_every_valid_fixture_is_a_record_the_engine_could_emit() -> None:
    """A hand-edited fixture would let the schema pass over a record no engine produces."""

    cases = _cases("valid")
    assert len(cases) >= 3, len(cases)
    for case in cases:
        instance = case["instance"]
        assert case["schema_id"] == CHANGE_SCHEMA_ID
        assert set(instance) == set(CHANGE_SCHEMA["required"])
        assert instance["status"] == AUTHORIZED
        assert instance["execution_result"] is None
        assert instance["idempotency_key"] == instance["change_semantic_fingerprint"]


def test_the_invalid_fixtures_cover_each_refusal_the_contract_names() -> None:
    names = {case["name"] for case in _cases("invalid")}
    assert len(names) == len(_cases("invalid"))
    for required in (
        "change_declaring_after_state_fingerprint",
        "change_declaring_difference_closure",
        "change_declaring_objective_completion",
        "change_with_status_completed",
        "change_with_status_closed",
        "change_reporting_an_execution_result_while_authorized",
        "change_id_with_a_trailing_newline",
        "change_at_an_unsupported_schema_version",
    ):
        assert required in names, required


# --------------------------------------------------------------------------- #
# 6. the contract's acceptance flags are backed by something
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "flag",
    [
        "CHANGE_CONTRACT_DEFINED=true",
        "CHANGE_SCHEMA_IMPLEMENTED=true",
        "CHANGE_ENGINE_IMPLEMENTED=true",
        "CANONICAL_CHANGE_OWNER_COUNT=1",
        "DERIVED_CHANGE_STATUS=AUTHORIZED",
        "IDEMPOTENCY_KEY_DERIVED=true",
        "PREEXISTING_CHANGE_ID_REQUIRED=false",
        "STATE_BINDING_DERIVED_FROM_AUTHORITY=true",
        "CHANGE_INTENT_FINGERPRINT_REMAINS_BINDING=true",
        "SEVEN_STATUS_VALUES_EMITTED=false",
        "VACUOUS_CONDITIONAL_GUARD=false",
        "AUTHORITY_SCOPE_SCHEMA_REJECTS_PATH_EXPRESSIONS=false",
        "DERIVED_CHANGE_IS_SCHEMA_BACKED=true",
        "CARRIED_CHANGE_CONTEXT_IS_SCHEMA_BACKED=false",
        "CALLER_SELF_ASSERTED_AUTONOMOUS_DECISION_ACCEPTED=false",
        "AUTHORITY_PROVENANCE_RESOLVED=true",
        "SINGLE_AUTHORITY_OWNER_PRESERVED=true",
        "CHANGE_REDECIDES_AUTHORITY=false",
        "HASH_CONSISTENCY_IS_NOT_PROVENANCE=true",
    ],
)
def test_the_contract_records_each_ratified_flag(flag: str) -> None:
    """The five ratified interpretations and the two non-claims, present where they are read."""

    assert flag in CONTRACT.read_text(encoding="utf-8"), flag


def test_the_authority_contract_records_its_obligation_as_discharged() -> None:
    """``AUTHORITY_CONTRACT.md`` §7.2 left Phase 5 an obligation. It is no longer open."""

    text = (ROOT / "00_KERNEL" / "05_AUTHORITY" / "AUTHORITY_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    assert "CHANGE_ENGINE_IMPLEMENTED=true" in text
    assert "CHANGE_ENGINE_IMPLEMENTED=false" not in text
    assert "OPERATION_FINGERPRINT_OBLIGATION_DISCHARGED=true" in text


# --------------------------------------------------------------------------- #
# 7. provenance is structural, not a check that could be forgotten
# --------------------------------------------------------------------------- #


def test_the_request_carries_the_authority_inputs_and_the_claim_and_nothing_else() -> None:
    """The closed key set is the fix, stated where it is enforced.

    There is no entry for the Difference, the action, the scope or the project. Every one of
    those is read from the decision the canonical evaluator returned, so a caller-supplied
    value cannot disagree with it -- the disagreement is not refused, it is inexpressible.
    """

    assert frozenset(
        {"schema_version", "authority_request", "authority_decision"}
    ) == REQUIRED_REQUEST_KEYS


@pytest.mark.parametrize(
    "absent", ["difference", "project_id", "requested_action", "requested_scope"]
)
def test_the_request_has_no_second_source_for_any_bound_value(absent: str) -> None:
    assert absent not in REQUIRED_REQUEST_KEYS


def test_change_calls_the_one_evaluator_and_implements_no_second_one() -> None:
    """``SINGLE_AUTHORITY_OWNER_PRESERVED``: read from the module, not asserted about it.

    Change must reach permission by calling ``evaluate_authority``. A module that reached it
    any other way -- its own rule matching, its own prohibition check, its own approval
    resolution -- would be a second Authority, and a second Authority is one that can
    disagree with the first.
    """

    source = (
        ROOT / "src" / "manosube_agent_civilization" / "change" / "engine.py"
    ).read_text(encoding="utf-8")
    assert "evaluate_authority(shaped[\"authority_request\"])" in source
    for second_authority in (
        "is_contained(",
        "overlaps(",
        "most_restrictive(",
        "at_least_as_restrictive_as(",
        "exceeds_reversibility(",
        "HUMAN_ONLY",
    ):
        assert second_authority not in source, second_authority


def test_the_engine_compares_the_whole_decision_not_only_its_address() -> None:
    """An address is a digest over a projection, and a projection is not the record."""

    source = (
        ROOT / "src" / "manosube_agent_civilization" / "change" / "engine.py"
    ).read_text(encoding="utf-8")
    assert "claimed != reproduced" in source
