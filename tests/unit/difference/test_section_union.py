"""Every canonical section enters the bundle through one collision-safe union.

A plain ``target[identity] = record`` cannot detect that it is replacing a record; it just
drops the earlier one. That is how two individually valid Observation Scopes sharing a
``scope_id`` reached a returned bundle with only the later payload in it. The union is now
the only insertion path, and this suite holds it to the three-way rule on *every* emitted
section: a new identity inserts, an identical duplicate is idempotent, and a
same-identity/different-payload pair fails closed -- in either insertion order, without
mutating the inputs.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import (
    PREDICATE_ID,
    PROJECT_ID,
    SCOPE_ID,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    retained_status_predecessor,
    state_fingerprint,
    target_predicate,
)

from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.conformance import (
    EMITTED_SECTIONS,
    RECORD_TYPES,
    merge_records,
)
from manosube_agent_civilization.difference.errors import IdentityCollisionError

_SUBJECTS = ["kernel.state", "kernel.other"]


def _rich_bundle() -> dict[str, Any]:
    """A returned bundle carrying as many canonical sections as this phase can produce."""

    _, request = retained_status_predecessor(
        "BLOCKED", negative_claims=[negative_claim("NO_RESULT")], facts=[]
    )
    return derive_differences(request)


def _conflicting(record: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a copy that keeps the canonical identity but differs somewhere else."""

    forged = deepcopy(record)
    for field, value in sorted(record.items()):
        if field == key:
            continue
        if isinstance(value, str) and field != "schema_version":
            forged[field] = value + "-FORGED"
            return forged
        if isinstance(value, bool):
            forged[field] = not value
            return forged
        if isinstance(value, int):
            forged[field] = value + 1
            return forged
    for field, value in sorted(record.items()):
        if field == key:
            continue
        if isinstance(value, list):
            forged[field] = [*value, {"kind": "observation_evidence", "id": "EVID-FORGED"}]
            return forged
        if isinstance(value, dict):
            forged[field] = {**value, "forged_field": True}
            return forged
    raise AssertionError(f"no non-identity field to alter: {key}")


def _superseding_bundle() -> dict[str, Any]:
    """A material change, so the Supersession Relation section is populated too."""

    _, seeded = retained_status_predecessor("BLOCKED")
    fingerprint = state_fingerprint("KNOWN")
    scope = observation_scope()
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope, [raw_fact(value="DEGRADED")], fingerprint, state_revision=3
                ),
            }
        ],
        fingerprint,
        state_revision=3,
    )
    request["observation_method"] = seeded["observation_method"]
    request["bindings"][0]["predecessor"] = seeded["bindings"][0]["predecessor"]
    return derive_differences(request)


def _section_records() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for bundle in (_rich_bundle(), _superseding_bundle()):
        for section, holder in bundle.items():
            if section in EMITTED_SECTIONS and holder and section not in records:
                records[section] = holder[0]
    return records


_SECTION_RECORDS = _section_records()
_POPULATED = sorted(_SECTION_RECORDS)


def test_the_bundle_under_test_populates_most_canonical_sections() -> None:
    """The parametrisation below is not vacuous."""

    assert set(_POPULATED) >= {
        "differences",
        "events",
        "policies",
        "supersession_relations",
        "next_observation_requests",
        "observation_methods",
        "observation_scopes",
        "observations",
        "negative_observations",
        "negative_observation_evaluations",
        "objective_revisions",
        "evaluations",
    }


@pytest.mark.parametrize("section", _POPULATED)
def test_a_new_identity_inserts_and_an_identical_duplicate_is_idempotent(
    section: str,
) -> None:
    key = RECORD_TYPES[EMITTED_SECTIONS[section]].key
    record = deepcopy(_SECTION_RECORDS[section])
    original = deepcopy(record)
    target: dict[str, dict[str, Any]] = {}
    merge_records(target, [record], key)
    merge_records(target, [deepcopy(record)], key)
    assert list(target) == [record[key]]
    assert target[record[key]] == original
    # The union stores a copy: mutating what it holds never reaches the caller's record.
    target[record[key]]["schema_version"] = "MUTATED"
    assert record == original


@pytest.mark.parametrize("section", _POPULATED)
def test_a_same_id_different_payload_pair_fails_closed_in_either_order(
    section: str,
) -> None:
    key = RECORD_TYPES[EMITTED_SECTIONS[section]].key
    record = deepcopy(_SECTION_RECORDS[section])
    forged = _conflicting(record, key)
    for first, second in ((record, forged), (forged, record)):
        target: dict[str, dict[str, Any]] = {}
        merge_records(target, [deepcopy(first)], key)
        with pytest.raises(IdentityCollisionError, match=record[key]):
            merge_records(target, [deepcopy(second)], key)
        # The conflict is rejected *before* the target is mutated.
        assert target[record[key]] == first


@pytest.mark.parametrize("section", _POPULATED)
def test_one_call_carrying_both_payloads_also_fails_closed(section: str) -> None:
    key = RECORD_TYPES[EMITTED_SECTIONS[section]].key
    record = deepcopy(_SECTION_RECORDS[section])
    forged = _conflicting(record, key)
    with pytest.raises(IdentityCollisionError):
        merge_records({}, [deepcopy(record), deepcopy(forged)], key)


def _two_scope_request(scope_ids: tuple[str, str]) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scopes = [
        observation_scope(
            included=_SUBJECTS, scope_id=scope_ids[index], target_identity=f"TP-000{index + 1}"
        )
        for index in range(2)
    ]
    bundles = [
        observed_bundle(scopes[index], [raw_fact(subject=_SUBJECTS[index])], fingerprint)
        for index in range(2)
    ]
    objective = objective_revision(
        [
            target_predicate(predicate_id="TP-0001", subject=_SUBJECTS[0]),
            target_predicate(predicate_id="TP-0002", subject=_SUBJECTS[1]),
        ]
    )
    return derivation_request(
        objective,
        [
            {
                "target_predicate_id": f"TP-000{index + 1}",
                "observation_scope": scopes[index],
                "observation_bundle": bundles[index],
            }
            for index in range(2)
        ],
        fingerprint,
    )


def test_two_bindings_reusing_one_scope_id_fail_closed() -> None:
    """The reviewed defect: each Scope is valid alone, and one silently replaced the other."""

    request = _two_scope_request((SCOPE_ID, SCOPE_ID))
    before = deepcopy(request)
    with pytest.raises(IdentityCollisionError, match=SCOPE_ID):
        derive_differences(request)
    assert request == before


def test_distinct_scope_ids_still_derive_and_stay_cross_record_valid() -> None:
    """The rule rejects the conflict, not the legitimate two-Scope derivation."""

    bundle = derive_differences(_two_scope_request(("OBS-SCOPE-0001", "OBS-SCOPE-0002")))
    assert {scope["scope_id"] for scope in bundle["observation_scopes"]} == {
        "OBS-SCOPE-0001",
        "OBS-SCOPE-0002",
    }
    assert len(bundle["differences"]) == 2
    assert validate_bundle(bundle) == []
    assert all(scope["project_id"] == PROJECT_ID for scope in bundle["observation_scopes"])
