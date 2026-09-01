"""Every raw request fragment is scanned before it becomes a canonical record.

The hostile-input gate scanned the canonical records a request carries, but not the raw
*fragments* the Engine completes into records. A declared field such as
``procedure_ref.id = "HEAD"`` was therefore copied into a content-addressed Observation
Method, and the final gate saw only the derived — stable — identity.

Two routes cover the two fragments, and the split is declared rather than incidental: the
Observation Method fragment carries the target type's declared reference locations
unchanged, so it is scanned as that type before derivation; the Closure Policy requirements
fragment materialises its descriptors during completion, so its *derived* record is swept in
``_finalize`` instead. A contract test proves the two together cover every fragment.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import (
    OBSERVATION_METHOD,
    PREDICATE_ID,
    derivation_request,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    retained_status_predecessor,
    state_fingerprint,
    target_predicate,
)

from manosube_agent_civilization.difference import derive_differences, engine as engine_module
from manosube_agent_civilization.difference.conformance import EMITTED_SECTIONS
from manosube_agent_civilization.difference.engine import (
    _BINDING_KEYS,
    _EMITTED_SWEEP_FRAGMENT_TYPES,
    _REQUEST_FRAGMENT_TYPES,
    _SCANNED_BINDING_KEYS,
    _iter_request_records,
)
from manosube_agent_civilization.difference.errors import SecurityRejectionError
from manosube_agent_civilization.difference.graph import REFERENCE_EDGES

ENGINE_SOURCE = Path(engine_module.__file__).read_text(encoding="utf-8")

#: The declared reference locations of an Observation Method, from the one registry.
METHOD_EDGES = sorted(edge.path for edge in REFERENCE_EDGES["observation_method"])


# --------------------------------------------------------------------------- #
# Inventory: every fragment the Engine completes is covered, in both directions
# --------------------------------------------------------------------------- #


def _fragments_the_engine_reads() -> set[str]:
    """The request keys the derivation converts into canonical records, read from source."""

    derivation = ENGINE_SOURCE.split("def derive_differences(")[1].split("\ndef ")[0]
    found = set()
    for match in re.finditer(r'request\.get\("([a-z_]+)"|request\["([a-z_]+)"\]', derivation):
        key = match.group(1) or match.group(2)
        if key in {"observation_method", "closure_policy_requirements"}:
            found.add(key)
    binding = re.findall(r'binding\.get\("([a-z_]+)"', derivation)
    found.update(key for key in binding if key == "closure_policy_requirements")
    return found


def test_the_fragment_inventory_matches_the_derivation_in_both_directions() -> None:
    covered = set(_REQUEST_FRAGMENT_TYPES) | set(_EMITTED_SWEEP_FRAGMENT_TYPES)
    assert covered == _fragments_the_engine_reads()
    assert not set(_REQUEST_FRAGMENT_TYPES) & set(_EMITTED_SWEEP_FRAGMENT_TYPES)


def test_every_fragment_becomes_a_declared_emitted_type() -> None:
    for type_name in {**_REQUEST_FRAGMENT_TYPES, **_EMITTED_SWEEP_FRAGMENT_TYPES}.values():
        assert type_name in set(EMITTED_SECTIONS.values())
        assert type_name in REFERENCE_EDGES


def test_the_emitted_sweep_exists_and_runs_before_the_bundle_is_returned() -> None:
    body = ENGINE_SOURCE.split("def _finalize(")[1].split("\ndef ")[0]
    assert body.count("_emitted_moving_reference_errors(bundle)") == 1
    assert body.index("_emitted_moving_reference_errors(bundle)") < body.index("return bundle")


def test_every_record_bearing_binding_key_is_scanned_in_both_directions() -> None:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    _, seeded = retained_status_predecessor("RETAINED")
    binding = {
        "target_predicate_id": PREDICATE_ID,
        "observation_scope": scope,
        "observation_bundle": observed_bundle(scope, [raw_fact()], fingerprint),
        "historical_observation_scopes": [observation_scope(scope_id="OBS-SCOPE-0002")],
        "predecessor": seeded["bindings"][0]["predecessor"],
        "closure_policy_requirements": {"minimum_evidence_level": "E1"},
    }
    request = derivation_request(objective_revision(), [binding], fingerprint)
    request["observation_method"] = deepcopy(OBSERVATION_METHOD)
    scanned = {where for _record, _type, where in _iter_request_records(request)}
    # Matched against the binding's own paths: the request carries a top-level
    # ``closure_policy_requirements`` too, so an unanchored match would pass whether or
    # not the per-binding fragment is scanned at all.
    binding_paths = {where for where in scanned if where.startswith("request.bindings[0].")}
    for key in _SCANNED_BINDING_KEYS:
        assert any(key in where for where in binding_paths), key
    # And the keys that are *not* scanned carry no canonical record and no fragment.
    # ``closure_policy_requirements`` was on this list: a binding may override the
    # derivation's Policy requirements with its own fragment, so a moving reference only
    # had to be supplied per binding rather than per request to pass the boundary.
    assert {"target_predicate_id", "risk_class"} == _BINDING_KEYS - _SCANNED_BINDING_KEYS


# --------------------------------------------------------------------------- #
# The Observation Method fragment
# --------------------------------------------------------------------------- #


def _method_request(mutate: Any = None) -> dict[str, Any]:
    _, request = retained_status_predecessor("RETAINED")
    if mutate is not None:
        mutate(request["observation_method"])
    return request


def test_the_control_route_derives_and_stays_cross_record_valid() -> None:
    bundle = derive_differences(_method_request())
    assert validate_bundle(bundle) == []
    assert bundle["observation_methods"]


@pytest.mark.parametrize("path", METHOD_EDGES)
def test_a_moving_reference_in_every_declared_method_field_fails_closed(path: str) -> None:
    """One mutation per declared reference location of the Observation Method."""

    def mutate(method: dict[str, Any]) -> None:
        if path.endswith("members[]"):
            key = path.split(".")[0]
            method[key] = {
                "collection_kind": "UNORDERED_SET",
                "members": [{"kind": "schema", "id": "HEAD"}],
            }
        else:
            method[path] = {**deepcopy(method[path]), "id": "HEAD"}

    request = _method_request(mutate)
    before = deepcopy(request)
    with pytest.raises(SecurityRejectionError, match="moving reference"):
        derive_differences(request)
    assert request == before


@pytest.mark.parametrize(
    "identity", ["HEAD", "LATEST", "CURRENT", "MAIN", "REFS-HEADS-MAIN", "THING@LATEST"]
)
def test_every_moving_identity_form_is_rejected_in_the_fragment(identity: str) -> None:
    def mutate(method: dict[str, Any]) -> None:
        method["procedure_ref"] = {**deepcopy(method["procedure_ref"]), "id": identity}

    with pytest.raises(SecurityRejectionError, match="moving reference"):
        derive_differences(_method_request(mutate))


def test_a_stable_reference_in_the_fragment_is_accepted() -> None:
    def mutate(method: dict[str, Any]) -> None:
        method["procedure_ref"] = {
            **deepcopy(method["procedure_ref"]),
            "id": "OBS-PROCEDURE-0002",
        }

    bundle = derive_differences(_method_request(mutate))
    assert "OBS-PROCEDURE-0002" in {
        item["procedure_ref"]["id"] for item in bundle["observation_methods"]
    }


def test_the_rejection_names_the_fragment_not_the_derived_record() -> None:
    def mutate(method: dict[str, Any]) -> None:
        method["procedure_ref"] = {**deepcopy(method["procedure_ref"]), "id": "HEAD"}

    with pytest.raises(SecurityRejectionError, match=r"request\.observation_method"):
        derive_differences(_method_request(mutate))


# --------------------------------------------------------------------------- #
# The Closure Policy requirements fragment, via the emitted sweep
# --------------------------------------------------------------------------- #


def _policy_request(requirements: dict[str, Any]) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope, [raw_fact(value="NOT-READY")], fingerprint
                ),
            }
        ],
        fingerprint,
    )
    request["closure_policy_requirements"] = requirements
    return request


def test_a_moving_reference_in_a_policy_requirement_fails_closed() -> None:
    """Scanning the fragment as a Closure Policy would misread it; the sweep reads the record."""

    request = _policy_request(
        {
            "minimum_evidence_level": "E1",
            "reopen_conditions": [
                {
                    "kind": "target_predicate",
                    "id": "REFS-HEADS-MAIN",
                    "predicate_semantic_fingerprint": "sha256:" + "b" * 64,
                    "objective_revision_ref": {
                        "kind": "objective_revision",
                        "id": "OBJ-REV-0001",
                    },
                }
            ],
        }
    )
    with pytest.raises(SecurityRejectionError, match="moving reference"):
        derive_differences(request)


def test_the_policy_control_route_is_accepted() -> None:
    bundle = derive_differences(_policy_request({"minimum_evidence_level": "E1"}))
    assert len(bundle["policies"]) == 1
    assert validate_bundle(bundle) == []


# --------------------------------------------------------------------------- #
# Ordinary payload is still payload
# --------------------------------------------------------------------------- #


def test_a_structured_value_shaped_like_a_moving_reference_stays_literal() -> None:
    """Fragment scanning must not reintroduce arbitrary shape traversal."""

    fingerprint = state_fingerprint()
    scope = observation_scope()
    value = {"kind": "widget", "id": "HEAD"}
    request = derivation_request(
        objective_revision([target_predicate(expected_value={"kind": "widget", "id": "X"})]),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope, [raw_fact(value=value, value_type="STRUCTURED")], fingerprint
                ),
            }
        ],
        fingerprint,
    )
    request["observation_method"] = deepcopy(OBSERVATION_METHOD)
    bundle = derive_differences(request)
    observed = bundle["differences"][0]["normalized_observed_state"]
    assert observed["value_candidates"]["members"][0]["value"] == value
    assert validate_bundle(bundle) == []


def test_a_malformed_fragment_does_not_leak_a_raw_exception() -> None:
    for fragment in ({}, {"procedure_ref": None}, {"procedure_ref": "text"}):
        request = _method_request()
        request["observation_method"] = deepcopy(fragment)
        try:
            derive_differences(request)
        except SecurityRejectionError:
            continue
        except Exception as error:
            assert type(error).__module__.startswith("manosube_agent_civilization"), (
                f"raw {type(error).__name__} escaped: {error}"
            )


# --------------------------------------------------------------------------- #
# A fragment must be a canonical object before it is materialised
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "fragment", [None, [], "text", 7, True], ids=["null", "list", "str", "int", "bool"]
)
@pytest.mark.parametrize(
    "key", ["observation_method", "closure_policy_requirements"]
)
def test_a_non_object_fragment_is_rejected_before_materialisation(
    key: str, fragment: Any
) -> None:
    """A fragment is completed by reading its keys, so its object contract comes first."""

    from manosube_agent_civilization.difference import DifferenceError

    _, request = retained_status_predecessor("RETAINED")
    request[key] = fragment
    with pytest.raises(DifferenceError, match=f"requested {key} is not a canonical object"):
        derive_differences(request)


def test_a_non_object_binding_policy_fragment_is_rejected() -> None:
    from manosube_agent_civilization.difference import DifferenceError

    _, request = retained_status_predecessor("RETAINED")
    request["bindings"][0]["closure_policy_requirements"] = ["not", "an", "object"]
    with pytest.raises(DifferenceError, match="not a canonical object"):
        derive_differences(request)
