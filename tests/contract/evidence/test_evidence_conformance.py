"""What every Evidence record must say, and what none may say.

The three ratified Phase 6 semantics are each asserted here against the real engines rather
than described:

```text
Q1-A + Q1-ii   every minimum field present; state bound, never embedded
Q2-A           E0..E3 derived; E4..E6 in the vocabulary and refused
Q3-A           Change Result Evidence only where a re-observation grounds it
```
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import pytest
from tests.evidence_helpers import (
    after_observation_request,
    before_observation_request,
    change_result_evidence_request,
    observation_evidence_request,
    real_change_request,
)

from manosube_agent_civilization.evidence import (
    CHANGE_RESULT_EVIDENCE,
    OBSERVATION_EVIDENCE,
    EvidenceError,
    UngroundedChangeResultEvidenceError,
    UnsupportedEvidenceLevelError,
    derive_evidence,
)
from manosube_agent_civilization.evidence.engine import REQUIRED_REQUEST_KEYS
from manosube_agent_civilization.evidence.identity import EVIDENCE_SEMANTIC_FIELDS

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONSTITUTION = REPOSITORY_ROOT / "00_KERNEL" / "KERNEL_CONSTITUTION.md"
EVIDENCE_SCHEMA = REPOSITORY_ROOT / "01_SCHEMA" / "evidence" / "evidence.schema.json"

#: 第28条's list, in the order the article writes it. Held as data so the assertion below
#: compares against the article rather than against a memory of it.
ARTICLE_28_MINIMUM_FIELDS: tuple[str, ...] = (
    "evidence_id",
    "timestamp",
    "target",
    "before_state",
    "observation_method",
    "change_identity",
    "authority_used",
    "after_state",
    "expected_result",
    "observed_result",
    "status",
    "artifact_references",
    "lineage",
    "remaining_differences",
)


@pytest.fixture(scope="module")
def observation_evidence() -> dict[str, Any]:
    return derive_evidence(observation_evidence_request())


@pytest.fixture(scope="module")
def change_result_evidence() -> dict[str, Any]:
    return derive_evidence(change_result_evidence_request())


# --------------------------------------------------------------------------- #
# 第28条 -- the minimum fields, and Q1-A
# --------------------------------------------------------------------------- #


def test_article_28_lists_exactly_the_fields_this_module_holds_it_to() -> None:
    """The positive control on the list above: it is the article's, not a paraphrase.

    第28条 writes its minimum as a fenced block of bare field names. If the article were
    edited, the list here would keep passing every other test in this file while measuring
    the wrong thing -- which is the failure mode this control exists for.
    """

    text = CONSTITUTION.read_text(encoding="utf-8")
    block = re.search(r"## 第28条 Evidence Contract.*?```text\n(.*?)```", text, re.DOTALL)
    assert block is not None, "第28条 no longer declares its minimum fields as a text block"
    declared = tuple(line.strip() for line in block.group(1).splitlines() if line.strip())
    assert declared == ARTICLE_28_MINIMUM_FIELDS


@pytest.mark.parametrize("field", ARTICLE_28_MINIMUM_FIELDS)
def test_every_minimum_field_is_present_on_both_positions(
    field: str, observation_evidence: dict[str, Any], change_result_evidence: dict[str, Any]
) -> None:
    """Q1-A: present on every record, ``null`` where it does not apply, never absent."""

    assert field in observation_evidence
    assert field in change_result_evidence


def test_the_schema_requires_every_minimum_field_rather_than_admitting_its_absence() -> None:
    schema = json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
    assert set(ARTICLE_28_MINIMUM_FIELDS) <= set(schema["required"])
    assert schema["additionalProperties"] is False


def test_observation_evidence_nulls_the_change_side_rather_than_omitting_it(
    observation_evidence: dict[str, Any],
) -> None:
    assert observation_evidence["evidence_position"] == OBSERVATION_EVIDENCE
    assert observation_evidence["change_identity"] is None
    assert observation_evidence["authority_used"] is None
    assert observation_evidence["expected_result"] is None


def test_observation_evidence_does_not_read_after_state_as_equal_to_before_state(
    observation_evidence: dict[str, Any],
) -> None:
    """Q1-C is not taken, and this is where it would show if it were.

    "Nothing changed" is a claim about a second point in time. An Observation Evidence
    record has one observation, so the honest value is ``null`` -- copying ``before_state``
    across would assert an unobserved absence of change, which is exactly the collapse
    ``NO_RESULT != PROVEN_ABSENCE`` forbids.
    """

    assert observation_evidence["after_state"] is None
    assert observation_evidence["before_state"] is not None


# --------------------------------------------------------------------------- #
# Q1-ii -- state bound, never embedded
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("position", ["before_state", "after_state"])
def test_state_is_bound_by_revision_and_fingerprint_only(
    position: str, change_result_evidence: dict[str, Any]
) -> None:
    binding = change_result_evidence[position]
    assert set(binding) == {"state_revision", "semantic_fingerprint"}
    assert isinstance(binding["state_revision"], int)
    assert set(binding["semantic_fingerprint"]) == {"profile", "digest"}


def test_no_canonical_state_body_is_copied_into_an_evidence_record(
    change_result_evidence: dict[str, Any],
) -> None:
    """A State body inside Evidence would be a second State that can disagree with the first.

    ``semantic_state`` is the key a canonical State record carries; its absence anywhere in
    the record -- at any depth -- is what "bound, not embedded" means operationally.
    """

    serialized = json.dumps(change_result_evidence, sort_keys=True)
    assert "semantic_state" not in serialized


# --------------------------------------------------------------------------- #
# Q2-A -- derived levels, refused levels
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("method_class", "expected"),
    [
        ("DECLARATION", "E0"),
        ("STATIC_INSPECTION", "E1"),
        ("UNIT_TEST", "E2"),
        ("INTEGRATION_TEST", "E3"),
    ],
)
def test_derivable_levels_come_from_the_method_class(method_class: str, expected: str) -> None:
    record = derive_evidence(observation_evidence_request(method_class=method_class))
    assert record["evidence_level"] == expected


@pytest.mark.parametrize(
    "method_class",
    ["NATURAL_PATH_EXECUTION", "TARGET_RUNTIME_PROOF", "REPEATED_INDEPENDENT_RUNTIME_PROOF"],
)
def test_e4_to_e6_are_refused_rather_than_minted(method_class: str) -> None:
    with pytest.raises(UnsupportedEvidenceLevelError) as raised:
        derive_evidence(observation_evidence_request(method_class=method_class))
    assert "Phase 6 cannot derive" in str(raised.value)


def test_the_vocabulary_keeps_e4_to_e6_even_though_the_derivation_stops_at_e3() -> None:
    """Q2-A keeps the constitutional vocabulary and narrows only what may be *produced*."""

    schema = json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["evidence_level"]["enum"] == [
        "E0",
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "E6",
    ]


def test_a_level_cannot_exceed_what_the_record_contains() -> None:
    """``E-005``: an integration test that carries no artifact and ran nothing is a claim."""

    record = derive_evidence(
        observation_evidence_request(method_class="INTEGRATION_TEST", artifact_references=[])
    )
    assert record["evidence_level"] == "E3"

    empty = before_observation_request()
    empty["attempts"] = []
    empty["source_occurrences"] = []
    lowered = derive_evidence(
        observation_evidence_request(
            method_class="INTEGRATION_TEST", observation=empty, artifact_references=[]
        )
    )
    assert lowered["evidence_level"] == "E0"


def test_there_is_no_request_key_through_which_a_level_could_be_supplied() -> None:
    assert "evidence_level" not in REQUIRED_REQUEST_KEYS
    assert "status" not in REQUIRED_REQUEST_KEYS
    assert "evidence_position" not in REQUIRED_REQUEST_KEYS


# --------------------------------------------------------------------------- #
# Q3-A -- grounded Change Result Evidence, or none
# --------------------------------------------------------------------------- #


def test_change_result_evidence_without_a_post_change_observation_is_refused() -> None:
    request = change_result_evidence_request()
    request["post_change_observation_request"] = None
    with pytest.raises(UngroundedChangeResultEvidenceError) as raised:
        derive_evidence(request)
    assert "post-change Observation" in str(raised.value)


def test_the_same_situation_is_recordable_as_observation_evidence() -> None:
    """The refusal above is not a dead end, and that matters: a route that only refuses
    would push a caller toward mislabelling rather than toward the truthful record."""

    record = derive_evidence(observation_evidence_request())
    assert record["evidence_position"] == OBSERVATION_EVIDENCE
    assert record["status"] in {
        "COMPLETE",
        "INCOMPLETE",
        "EMPTY",
        "UNKNOWN",
        "UNOBSERVED",
        "BLOCKED",
        "FAILED",
        "INVALID",
        "CONFLICTED",
    }


def test_change_result_evidence_claims_neither_execution_nor_causality(
    change_result_evidence: dict[str, Any],
) -> None:
    assert change_result_evidence["evidence_position"] == CHANGE_RESULT_EVIDENCE
    assert change_result_evidence["change_identity"]["execution_result"] is None
    assert change_result_evidence["change_identity"]["causality_claimed"] is False
    assert change_result_evidence["expected_result"]["causality_claimed"] is False
    assert change_result_evidence["expected_result"]["execution_receipt_present"] is False


def test_the_schema_pins_both_non_claims_so_no_record_can_carry_the_opposite() -> None:
    schema = json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
    expected = schema["$defs"]["expected_result"]["properties"]
    assert expected["causality_claimed"] == {"const": False}
    assert expected["execution_receipt_present"] == {"const": False}
    assert schema["$defs"]["change_binding"]["properties"]["execution_result"] == {"type": "null"}


def test_a_post_change_observation_without_a_change_is_refused() -> None:
    request = observation_evidence_request()
    request["post_change_observation_request"] = after_observation_request()
    with pytest.raises(EvidenceError) as raised:
        derive_evidence(request)
    assert "without a Change" in str(raised.value)


def test_the_before_picture_cannot_stand_as_its_own_re_observation() -> None:
    request = change_result_evidence_request(post_change_observation=before_observation_request())
    with pytest.raises(EvidenceError) as raised:
        derive_evidence(request)
    assert "second observation" in str(raised.value)


def test_a_re_observation_of_an_earlier_revision_is_refused() -> None:
    stale = before_observation_request()
    stale["state_revision_observed"] = 0
    request = change_result_evidence_request(post_change_observation=stale)
    with pytest.raises(EvidenceError) as raised:
        derive_evidence(request)
    assert "earlier than" in str(raised.value)


def test_a_before_observation_of_another_state_is_refused() -> None:
    request = change_result_evidence_request(observation=after_observation_request())
    with pytest.raises(EvidenceError) as raised:
        derive_evidence(request)
    assert "authorized against" in str(raised.value)


# --------------------------------------------------------------------------- #
# identity and immutability
# --------------------------------------------------------------------------- #


def test_the_address_covers_the_whole_meaning_not_a_projection_of_it() -> None:
    """``E-003``: immutability is only enforceable if a rewritten record gets a new address.

    Every field except the two derived digests and the schema version is in the projection.
    A field left out would be one a record could be rewritten in while keeping its identity.
    """

    schema = json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
    addressed = set(EVIDENCE_SEMANTIC_FIELDS)
    unaddressed = set(schema["required"]) - addressed
    assert unaddressed == {"schema_version", "evidence_id", "evidence_semantic_fingerprint"}


def test_the_same_grounded_observation_produces_the_same_address() -> None:
    first = derive_evidence(observation_evidence_request())
    second = derive_evidence(observation_evidence_request())
    assert first == second


def test_a_different_recorded_instant_is_a_different_record() -> None:
    first = derive_evidence(observation_evidence_request())
    later = derive_evidence(observation_evidence_request(recorded_at="2026-08-30T12:00:00Z"))
    assert first["evidence_id"] != later["evidence_id"]


def test_the_request_is_never_mutated() -> None:
    request = change_result_evidence_request()
    before = json.dumps(request, sort_keys=True)
    derive_evidence(request)
    assert json.dumps(request, sort_keys=True) == before


# --------------------------------------------------------------------------- #
# the admitted instant
# --------------------------------------------------------------------------- #


def test_evidence_cannot_be_recorded_before_the_observation_it_records_ended() -> None:
    with pytest.raises(EvidenceError) as raised:
        derive_evidence(observation_evidence_request(recorded_at="2026-08-30T09:00:00Z"))
    assert "precedes the end of the Observation" in str(raised.value)


def test_the_recording_instant_is_required_rather_than_read() -> None:
    request = observation_evidence_request()
    request["recorded_at"] = None
    with pytest.raises(EvidenceError) as raised:
        derive_evidence(request)
    assert "explicit canonical UTC timestamp" in str(raised.value)


# --------------------------------------------------------------------------- #
# artifact integrity
# --------------------------------------------------------------------------- #


def test_an_artifact_reference_carrying_a_mutable_locator_is_refused() -> None:
    with pytest.raises(EvidenceError):
        derive_evidence(
            observation_evidence_request(
                artifact_references=[
                    {
                        "kind": "artifact",
                        "id": "ARTIFACT-0002",
                        "content_sha256": "b" * 64,
                        "byte_length": 1,
                        "media_type": "text/plain",
                        "url": "https://example.test/artifact",
                    }
                ]
            )
        )


def test_an_artifact_reference_carrying_a_secret_is_refused() -> None:
    with pytest.raises(EvidenceError):
        derive_evidence(
            observation_evidence_request(
                artifact_references=[
                    {
                        "kind": "artifact",
                        "id": "ARTIFACT-0003",
                        "content_sha256": "c" * 64,
                        "byte_length": 1,
                        "media_type": "text/plain",
                        "authorization": "Bearer token",
                    }
                ]
            )
        )


def test_two_different_artifacts_under_one_identity_are_refused() -> None:
    with pytest.raises(EvidenceError) as raised:
        derive_evidence(
            observation_evidence_request(
                artifact_references=[
                    {
                        "kind": "artifact",
                        "id": "ARTIFACT-0004",
                        "content_sha256": "d" * 64,
                        "byte_length": 1,
                        "media_type": "text/plain",
                    },
                    {
                        "kind": "artifact",
                        "id": "ARTIFACT-0004",
                        "content_sha256": "e" * 64,
                        "byte_length": 2,
                        "media_type": "text/plain",
                    },
                ]
            )
        )
    assert "two different artifacts" in str(raised.value)


# --------------------------------------------------------------------------- #
# the boundary's error vocabulary
# --------------------------------------------------------------------------- #


def test_no_predecessor_owner_error_escapes_the_evidence_boundary() -> None:
    """A caller of Evidence must not have to catch an Observation error to learn its own
    request was malformed. The decisions are delegated; the vocabulary is not."""

    broken = before_observation_request()
    broken["normalization_profile"] = "NOT-A-PROFILE-9.9"
    with pytest.raises(EvidenceError):
        derive_evidence(observation_evidence_request(observation=broken))

    unauthorized = real_change_request()
    unauthorized["authority_request"]["authority_rules"] = []
    with pytest.raises(EvidenceError):
        derive_evidence(change_result_evidence_request(change_request=unauthorized))


def test_a_fractional_second_after_the_observation_is_accepted() -> None:
    """The regression a lexicographic comparison silently gets wrong.

    ``common/timestamp.schema.json`` admits optional fractional seconds, and ``...00.5Z``
    sorts *before* ``...00Z`` as text while being half a second later. Comparing the strings
    would reject this record, so this case is the difference between a guard that orders
    instants and one that orders bytes.
    """

    record = derive_evidence(observation_evidence_request(recorded_at="2026-08-30T09:01:00.5Z"))
    assert record["timestamp"] == "2026-08-30T09:01:00.5Z"


def test_a_fractional_second_before_the_observation_is_still_refused() -> None:
    """The other direction, so the fix above is not simply the guard giving up."""

    with pytest.raises(EvidenceError) as raised:
        derive_evidence(observation_evidence_request(recorded_at="2026-08-30T09:00:59.9Z"))
    assert "precedes the end of the Observation" in str(raised.value)


def test_provenance_is_structural_and_therefore_has_no_error_class() -> None:
    """An exported error nothing raises advertises a check that does not exist.

    The predecessors are reproduced rather than admitted, so there is no provenance
    comparison to fail -- and nothing in the package should suggest otherwise.
    """

    import manosube_agent_civilization.evidence as package

    assert not hasattr(package, "EvidenceProvenanceError")
    for name in package.__all__:
        assert not name.endswith("ProvenanceError")


def test_the_observation_layer_s_evidence_reference_kind_is_reported_not_changed() -> None:
    """A seam between the phases, pinned here rather than resolved by Evidence.

    ``observation/engine.py`` requires an Observation's ``observation_evidence_refs`` to
    carry ``kind == "observation_evidence"``. Phase 6 mints records addressed
    ``EVIDENCE-...`` and refers to them as ``kind == "evidence"``, so an Observation cannot
    presently cite one.

    Difference is unaffected: ``difference.schema.json`` leaves the kind of
    ``observation_evidence_refs`` open, so a Difference may cite a Phase 6 Evidence record
    today. The narrower constraint is the Observation Engine's, and widening a predecessor's
    reference vocabulary is that phase's decision, not this one's -- taking it here would be
    Evidence editing Observation's contract to make its own output fit.

    This test states the seam so it is visible and so a future change to either side is
    caught rather than discovered.
    """

    from manosube_agent_civilization.difference.validation import validators
    from manosube_agent_civilization.observation import engine as observation_engine

    source = Path(observation_engine.__file__).read_text(encoding="utf-8")
    assert '_require_ref_kind(reference, "observation_evidence", "observation_evidence_refs")' in (
        source
    )

    difference_schema = validators()[
        "https://schemas.manosube.org/agent-civilization-os/v0.1/difference/difference.schema.json"
    ].schema
    open_kind = difference_schema["properties"]["observation_evidence_refs"]["items"]
    assert open_kind == {"$ref": "../common/reference.schema.json"}

    record = derive_evidence(observation_evidence_request())
    assert record["evidence_id"].startswith("EVIDENCE-")
