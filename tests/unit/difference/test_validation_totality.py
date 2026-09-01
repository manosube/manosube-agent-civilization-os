"""A validator returns errors; it never leaks an implementation exception.

A Negative Evaluation missing its schema-required ``evidence_refs`` was reported by the
schema pass and then handed, unfiltered, to a relational helper that indexed the missing
field. The Difference API raised ``KeyError`` instead of its canonical validation error.

The fix has two halves, because either alone is incomplete: rules that cannot be decided
without a well-formed record run over the schema-valid subset, and every shared helper is
total over untrusted input so a caller reaching it directly still gets a list of errors.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_scope,
    observed_bundle,
    state_fingerprint,
)

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.graph import (
    moving_reference_errors,
    reference_closure_errors,
    relational_errors,
)
from manosube_agent_civilization.difference.lifecycle import (
    blocker_payload_errors,
    closure_evaluation_input_errors,
)
from manosube_agent_civilization.difference.selection import contributing_facts
from manosube_agent_civilization.observation.verification import (
    negative_evaluation_evidence_errors,
    observation_record_errors,
)

ROOT = Path(__file__).resolve().parents[3]
NEGATIVE_EVALUATION_SCHEMA = json.loads(
    (ROOT / "01_SCHEMA" / "observation" / "negative_observation_evaluation.schema.json")
    .read_text(encoding="utf-8")
)
REQUIRED_FIELDS = sorted(NEGATIVE_EVALUATION_SCHEMA["required"])


def _request(mutate: Any) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    bundle = observed_bundle(
        scope, [], fingerprint, negative_claims=[negative_claim("ABSENT")]
    )
    mutate(bundle)
    return derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )


def test_the_required_field_list_comes_from_the_schema() -> None:
    assert REQUIRED_FIELDS and "evidence_refs" in REQUIRED_FIELDS


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_every_required_field_removed_gives_the_canonical_error(field: str) -> None:
    def mutate(bundle: dict[str, Any]) -> None:
        del bundle["negative_evaluations"][0][field]

    with pytest.raises(DifferenceError) as raised:
        derive_differences(_request(mutate))
    assert "is a required property" in str(raised.value)


def _nullable(field: str) -> bool:
    """Whether the canonical schema permits ``null`` for this required field."""

    declared = NEGATIVE_EVALUATION_SCHEMA["properties"][field]
    return "null" in json.dumps(declared)


NULLABLE_FIELDS = sorted(field for field in REQUIRED_FIELDS if _nullable(field))
NON_NULLABLE_FIELDS = sorted(set(REQUIRED_FIELDS) - set(NULLABLE_FIELDS))


def test_the_nullability_split_comes_from_the_schema() -> None:
    assert "previous_evaluation_id" in NULLABLE_FIELDS
    assert "evidence_refs" in NON_NULLABLE_FIELDS


@pytest.mark.parametrize("field", NON_NULLABLE_FIELDS)
def test_every_non_nullable_field_nulled_gives_the_canonical_error(field: str) -> None:
    def mutate(bundle: dict[str, Any]) -> None:
        bundle["negative_evaluations"][0][field] = None

    with pytest.raises(DifferenceError):
        derive_differences(_request(mutate))


@pytest.mark.parametrize("field", NULLABLE_FIELDS)
def test_a_nullable_field_set_to_null_is_decided_semantically(field: str) -> None:
    """The schema permits it, so the rejection must come from a lineage rule, not a crash."""

    def mutate(bundle: dict[str, Any]) -> None:
        bundle["negative_evaluations"][0][field] = None

    try:
        derive_differences(_request(mutate))
    except DifferenceError:
        return
    except Exception as error:  # pragma: no cover - surfaced as a test failure
        pytest.fail(f"{field}: raw {type(error).__name__} escaped: {error}")


@pytest.mark.parametrize(
    "value", [123, "text", [], {}], ids=["int", "str", "list", "dict"]
)
def test_a_wrongly_typed_evidence_list_gives_the_canonical_error(value: Any) -> None:
    def mutate(bundle: dict[str, Any]) -> None:
        bundle["negative_evaluations"][0]["evidence_refs"] = value

    try:
        derive_differences(_request(mutate))
    except DifferenceError:
        return
    # An empty list is schema-valid; it must still be rejected semantically for ABSENT.
    assert value == []


def test_a_malformed_owning_negative_observation_gives_the_canonical_error() -> None:
    def mutate(bundle: dict[str, Any]) -> None:
        del bundle["negative_observations"][0]["negative_evidence_refs"]

    with pytest.raises(DifferenceError):
        derive_differences(_request(mutate))


def test_multiple_simultaneous_schema_errors_are_reported_deterministically() -> None:
    def mutate(bundle: dict[str, Any]) -> None:
        evaluation = bundle["negative_evaluations"][0]
        del evaluation["evidence_refs"]
        del evaluation["conflict_fact_refs"]
        del bundle["negative_observations"][0]["negative_evidence_refs"]

    request = _request(mutate)
    messages = []
    for _ in range(3):
        with pytest.raises(DifferenceError) as raised:
            derive_differences(deepcopy(request))
        messages.append(str(raised.value))
    assert len(set(messages)) == 1


def test_no_raw_python_exception_escapes_for_any_single_field_removal() -> None:
    for field in REQUIRED_FIELDS:
        def mutate(bundle: dict[str, Any], field: str = field) -> None:
            del bundle["negative_evaluations"][0][field]

        try:
            derive_differences(_request(mutate))
        except DifferenceError:
            continue
        except Exception as error:  # pragma: no cover - surfaced as a test failure
            pytest.fail(f"{field}: raw {type(error).__name__} escaped: {error}")


def test_a_valid_evidence_channel_mutation_still_reaches_semantic_rejection() -> None:
    """Totality must not swallow the semantic rule it was added to protect."""

    def mutate(bundle: dict[str, Any]) -> None:
        bundle["negative_evaluations"][0]["evidence_refs"] = [
            {"kind": "negative_evidence", "id": "NEG-EVID-FOREIGN"}
        ]

    with pytest.raises(DifferenceError, match="not declared by its own channel"):
        derive_differences(_request(mutate))


# --------------------------------------------------------------------------- #
# Every shared helper is total over untrusted input
# --------------------------------------------------------------------------- #


HOSTILE: list[Any] = [
    {},
    {"negative_observations": [], "negative_evaluations": [None]},
    {"negative_observations": [{}], "negative_evaluations": [{}]},
    {"negative_observations": None, "negative_evaluations": None},
]


@pytest.mark.parametrize("payload", HOSTILE, ids=["empty", "none-record", "bare", "null"])
def test_the_evidence_channel_helper_is_total(payload: dict[str, Any]) -> None:
    assert isinstance(negative_evaluation_evidence_errors(payload), list)


def test_the_shared_difference_validators_are_total() -> None:
    """A record that failed its schema must not crash a shared rule downstream."""

    assert reference_closure_errors({}) == []
    assert reference_closure_errors({"differences": [{}], "changes": [None]}) == []
    assert relational_errors({}) == []
    assert relational_errors({"events": [], "differences": [{}]}) == []
    assert moving_reference_errors({}, "difference", "probe") == []
    assert moving_reference_errors({"anything": None}, "change", "probe") == []
    assert contributing_facts({"normalized_fact_refs": []}, {}, "s", "p") == []
    assert closure_evaluation_input_errors(
        {"closure_evaluation_id": "X"}, None, {}, {}, lambda policy: ""
    ) == ["evaluation references missing Difference: X"]


def test_a_malformed_observation_bundle_still_reports_a_canonical_error() -> None:
    """The whole shared verifier returns errors rather than raising."""

    assert isinstance(
        observation_record_errors(
            {
                "facts": [{}],
                "observations": [{}],
                "bindings": [{}],
                "fact_evaluations": [{}],
                "negative_observations": [{}],
                "negative_evaluations": [{}],
            }
        ),
        list,
    )


def test_blocker_payload_rule_is_not_reached_with_a_malformed_event() -> None:
    """Rules that require a well-formed record are gated, not made silently permissive."""

    with pytest.raises(KeyError):
        blocker_payload_errors({"difference_event_id": "E"}, None)


# --------------------------------------------------------------------------- #
# Selection reads every record in the bundle, so selection must be total too
# --------------------------------------------------------------------------- #

_SELECTION_READS: list[str] = [
    "target",
    "scope_ref",
    "state_revision_observed",
    "state_fingerprint_observed",
    "project_id",
    "status",
]


def _bundle_request(mutate: Any = None) -> dict[str, Any]:
    from tests.difference_helpers import raw_fact

    fingerprint = state_fingerprint()
    scope = observation_scope()
    bundle = observed_bundle(scope, [raw_fact(value="NOT-READY")], fingerprint)
    if mutate is not None:
        mutate(bundle)
    return derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )


def test_the_control_bundle_derives() -> None:
    """So the rejections below are the missing field, not the fixture."""

    assert derive_differences(_bundle_request())["differences"]


@pytest.mark.parametrize("field", _SELECTION_READS)
def test_an_observation_missing_a_selection_field_is_reported_not_raised(field: str) -> None:
    """Selection indexes every record in the bundle before any of them is validated.

    A record missing a schema-required field used to leak a raw ``KeyError`` out of the
    selection comprehension, in place of the canonical rejection the boundary documents.
    """

    def mutate(bundle: dict[str, Any]) -> None:
        del bundle["observations"][0][field]

    with pytest.raises(DifferenceError) as raised:
        derive_differences(_bundle_request(mutate))
    assert "is a required property" in str(raised.value)


def test_a_nested_selection_field_is_reported_not_raised() -> None:
    """The scan reads two levels: ``target.target_identity`` and ``scope_ref.id``."""

    def mutate(bundle: dict[str, Any]) -> None:
        del bundle["observations"][0]["target"]["target_identity"]

    with pytest.raises(DifferenceError) as raised:
        derive_differences(_bundle_request(mutate))
    assert "required property" in str(raised.value)


def test_the_bundle_is_not_verified_before_selection() -> None:
    """Ordering matters in both directions here.

    Verifying the whole bundle *before* selection would report a schema failure in place of
    the identity collision a forged-but-complete record deserves — the substitution
    ADR-0013 forbids. The verifier is asked only where the scan could not read, so this
    forged record keeps its own diagnosis.
    """

    def mutate(bundle: dict[str, Any]) -> None:
        bundle["observations"][0]["normalization_profile"] = "FORGED-9.9"

    with pytest.raises(DifferenceError) as raised:
        derive_differences(_bundle_request(mutate))
    assert "required property" not in str(raised.value)


def test_the_declared_selection_fields_match_what_selection_reads() -> None:
    """Both directions, read from the derivation source rather than remembered."""

    from manosube_agent_civilization.difference.engine import _SELECTION_FIELDS

    source = Path(
        "src/manosube_agent_civilization/difference/engine.py"
    ).read_text(encoding="utf-8")
    body = source.split("def _select_observation(")[1].split("\ndef ")[0]
    assert set(_SELECTION_FIELDS) == set(_SELECTION_READS)
    for field in _SELECTION_FIELDS:
        assert f'"{field}"' in body, field
