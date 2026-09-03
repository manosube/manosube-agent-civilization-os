"""Nothing is emitted, and nothing is consumed, without crossing a typed gate.

ADR-0009 closed the caller-supplied predecessor route. The requested Objective revision
escaped anyway, because it arrives on the current-derivation route. These proofs pin both
gates and, crucially, pin the *inventories* against the Engine's own source so a newly
emitted section or a newly consumed input cannot bypass them.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from manosube_agent_civilization.difference.conformance import (
    CARRIED_SECTIONS,
    EMITTED_SECTIONS,
    ENVELOPE_KEYS,
    INPUT_KINDS,
    RECORD_TYPES,
    UNSCHEMATIZED_SECTIONS,
)

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
ENGINE_SOURCE = (
    ROOT / "src" / "manosube_agent_civilization" / "difference" / "engine.py"
).read_text(encoding="utf-8")


def _emitted_sections_from_source() -> set[str]:
    """Every key the Engine can put in the returned bundle, read out of `_finalize`."""

    body = ENGINE_SOURCE.split("def _finalize(")[1]
    literal = body.split("bundle: dict[str, Any] = {", 1)[1]
    depth, end = 1, 0
    for index, character in enumerate(literal):
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                end = index
                break
    top_level = re.findall(r'^        "([a-z_]+)":', literal[:end], re.M)
    # `_finalize` also emits any non-empty carried dependency section not already a key.
    carried = set(
        re.findall(
            r'^\s+"([a-z_]+)": "[a-z_]+",$',
            ENGINE_SOURCE.split("_CARRIED_SECTIONS: dict[str, str] = {")[1].split("}")[0],
            re.M,
        )
    )
    return set(top_level) | carried


# --------------------------------------------------------------------------- #
# The output inventory, in both directions.
# --------------------------------------------------------------------------- #


def test_every_emitted_section_is_covered_by_the_final_gate() -> None:
    emitted = _emitted_sections_from_source()
    assert emitted, "the emitted-section inventory could not be read"
    uncovered = emitted - set(EMITTED_SECTIONS) - ENVELOPE_KEYS
    assert uncovered == set(), f"emitted without a typed validator: {sorted(uncovered)}"


def test_the_final_gate_declares_nothing_the_engine_cannot_emit() -> None:
    emitted = _emitted_sections_from_source()
    phantom = set(EMITTED_SECTIONS) - emitted
    assert phantom == set(), f"declared but never emitted: {sorted(phantom)}"


def test_the_envelope_keys_are_exactly_the_non_record_keys() -> None:
    emitted = _emitted_sections_from_source()
    assert emitted >= ENVELOPE_KEYS
    assert not (ENVELOPE_KEYS & set(EMITTED_SECTIONS))


def test_the_gate_runs_before_the_bundle_is_returned() -> None:
    body = ENGINE_SOURCE.split("def _finalize(")[1]
    assert "validate_emitted_bundle(bundle)" in body
    assert body.index("validate_emitted_bundle(bundle)") < body.index("\n    return bundle")


def test_an_unknown_emitted_section_is_rejected() -> None:
    from manosube_agent_civilization.difference.conformance import validate_emitted_bundle

    with pytest.raises(Exception, match="unknown sections"):
        validate_emitted_bundle({"smuggled_section": []})


# --------------------------------------------------------------------------- #
# The input inventory.
# --------------------------------------------------------------------------- #


def test_every_declared_input_is_validated_before_use() -> None:
    body = ENGINE_SOURCE.split("def derive_differences(")[1].split("\ndef ")[0]
    for input_name in INPUT_KINDS:
        assert f'"{input_name}")' in body, input_name
    assert 'validate_derivation_input(objective, "objective_revision")' in body
    assert 'validate_derivation_input(scope, "observation_scope")' in body
    assert 'validate_state_fingerprint(state_fingerprint, "requested State fingerprint")' in body
    # The Objective is validated before its own semantic fields are read.
    assert body.index('validate_derivation_input(objective, "objective_revision")') < body.index(
        'objective["project_id"] != project_id'
    )


def test_the_fragment_inputs_are_validated_on_the_records_they_produce() -> None:
    """Method and Policy arrive as fragments; their derived records are schema-validated."""

    assert "observation_method" not in INPUT_KINDS
    assert "closure_policy" not in INPUT_KINDS
    assert 'validate_record(method, "observation_method.schema.json")' in ENGINE_SOURCE
    assert 'validate_record(policy_record, "closure_policy.schema.json")' in ENGINE_SOURCE


# --------------------------------------------------------------------------- #
# One table, and one honest non-claim.
# --------------------------------------------------------------------------- #


def test_the_carried_and_emitted_maps_share_one_record_type_table() -> None:
    for section, type_name in {**CARRIED_SECTIONS, **EMITTED_SECTIONS}.items():
        assert type_name in RECORD_TYPES, section
    assert set(CARRIED_SECTIONS) <= set(EMITTED_SECTIONS)


def test_every_named_schema_exists_and_the_unschematized_set_is_measured() -> None:
    for type_name, canonical in RECORD_TYPES.items():
        if canonical.schema is None:
            continue
        relative = canonical.base.split("/v0.1/")[1]
        assert (ROOT / "01_SCHEMA" / relative / canonical.schema).is_file(), type_name

    assert {"changes", "reflow_transitions"} == UNSCHEMATIZED_SECTIONS
    # Measured from the registry rather than from directory emptiness. Emptiness was a proxy
    # for the claim, and Phase 5 falsified the proxy alone: `change.schema.json` governs a
    # *derived* Change, while these sections carry *predecessor-context* records of a
    # different shape. See `test_predecessor_boundary` for the full reasoning.
    for section in UNSCHEMATIZED_SECTIONS:
        assert RECORD_TYPES[CARRIED_SECTIONS[section]].schema is None, section


def test_the_output_schema_claim_is_qualified_by_the_unschematized_set() -> None:
    """`ALL_OUTPUT_SCHEMA_VALID` covers every section except the two v0.1 omits."""

    schema_backed = set(EMITTED_SECTIONS) - UNSCHEMATIZED_SECTIONS
    assert len(schema_backed) == len(EMITTED_SECTIONS) - 2
    for section in schema_backed:
        assert RECORD_TYPES[EMITTED_SECTIONS[section]].schema is not None


def test_the_record_type_table_exists_once() -> None:
    """The predecessor boundary reads the same table the output gate does."""

    from manosube_agent_civilization.difference import conformance, predecessor

    assert vars(predecessor)["RECORD_TYPES"] is conformance.RECORD_TYPES
    assert vars(predecessor)["CARRIED_SECTIONS"] is conformance.CARRIED_SECTIONS
    for section, canonical in predecessor.CARRIED_TYPES.items():
        assert canonical is conformance.RECORD_TYPES[conformance.CARRIED_SECTIONS[section]]

    # And no module re-derives a canonical identity the table already owns.
    source = (
        ROOT / "src" / "manosube_agent_civilization" / "difference" / "predecessor.py"
    ).read_text(encoding="utf-8")
    for duplicated in (
        "def _negative_observation_identity",
        "def _request_identity",
        "def _method_identity",
        "def _policy_identity",
    ):
        assert duplicated not in source, duplicated


def test_the_output_gate_rejects_a_schema_invalid_emitted_record() -> None:
    from manosube_agent_civilization.difference.conformance import validate_emitted_bundle
    from manosube_agent_civilization.difference.errors import DifferenceValidationError

    with pytest.raises(DifferenceValidationError, match="schema-invalid"):
        validate_emitted_bundle({"objective_revisions": [{"schema_version": "0.1"}]})


def test_the_output_gate_rejects_duplicate_and_contradicting_identities() -> None:
    from copy import deepcopy

    from tests.difference_helpers import single_binding_request

    from manosube_agent_civilization.difference import derive_differences
    from manosube_agent_civilization.difference.conformance import validate_emitted_bundle

    bundle = derive_differences(single_binding_request())
    validate_emitted_bundle(bundle)

    duplicated = deepcopy(bundle)
    duplicated["differences"] = [*duplicated["differences"], deepcopy(duplicated["differences"][0])]
    with pytest.raises(Exception, match="duplicate canonical record"):
        validate_emitted_bundle(duplicated)

    contradicting = deepcopy(bundle)
    forged = deepcopy(contradicting["differences"][0])
    forged["risk_class"] = "HIGH"
    contradicting["differences"] = [*contradicting["differences"], forged]
    with pytest.raises(Exception, match="same-ID different-payload"):
        validate_emitted_bundle(contradicting)
