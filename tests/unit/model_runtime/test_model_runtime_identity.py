"""V1 (Issue #66): deterministic identities, and identity-sensitivity of every
authority-bearing and reference field.

Issue #66's own V1 row names four identities -- "provider-neutral request, model result,
model-swap receipt, and recovery receipt". All four are proved here, together with the
State-bound Model Work Unit identity all four of them hang from and the Model Execution
Boundary identity a Work Unit references, so the complete set this delivery mints is:

```text
model_execution_boundary_id / _semantic_fingerprint      what the output may be used for
model_work_unit_id / _semantic_fingerprint               V1's own State-bound anchor
model_execution_request_identity                         V1's "provider-neutral request"
model_execution_envelope_id / _semantic_fingerprint      V1's "model result"
model_swap_receipt_id / _semantic_fingerprint            V1's "model-swap receipt"
session_recovery_receipt_id / _semantic_fingerprint      V1's "recovery receipt"
```

Every test below is a **pure** function test: no Store, no Boot, no adapter, no clock. The
proof that these same identities recompute over *genuinely committed* records lives in the V3
vertical proof, which resolves each record back out of a real Store and recomputes it there.

The identity-sensitivity proofs tamper each semantic field **independently** and require both
digests to move. That is stronger than "the id changes": a record whose id moved but whose
semantic fingerprint did not would be detectable only by whoever recomputed the id, which is
exactly the split ``runtime/identity.py``'s own module docstring warns about.
"""

from __future__ import annotations

from typing import Any

import pytest

from manosube_agent_civilization.model_runtime.errors import ModelRuntimeRequirementError
from manosube_agent_civilization.model_runtime.identity import (
    BOUNDARY_SEMANTIC_FIELDS,
    ENVELOPE_SEMANTIC_FIELDS,
    RECOVERY_RECEIPT_SEMANTIC_FIELDS,
    SWAP_RECEIPT_SEMANTIC_FIELDS,
    WORK_UNIT_SEMANTIC_FIELDS,
    model_candidate_fingerprint,
    model_execution_boundary_id,
    model_execution_boundary_semantic_fingerprint,
    model_execution_envelope_id,
    model_execution_envelope_semantic_fingerprint,
    model_execution_request_identity,
    model_swap_receipt_id,
    model_swap_receipt_semantic_fingerprint,
    model_work_unit_id,
    model_work_unit_semantic_fingerprint,
    session_recovery_receipt_id,
    session_recovery_receipt_semantic_fingerprint,
)

PROJECT_ID = "PRJ-MODEL-0001"
BINDING_REF = {"kind": "project_binding", "id": "PROJBIND-" + "A" * 64}
DIFFERENCE_REF = {"kind": "difference", "id": "D-" + "B" * 64}
AUTHORITY_REF = {"kind": "model_execution_decision", "id": "MODEL-EXEC-DEC-" + "C" * 64}
BOUNDARY_REF = {"kind": "model_execution_boundary", "id": "MODEL-EXECUTION-BOUNDARY-" + "D" * 64}
WORK_UNIT_REF = {"kind": "model_work_unit", "id": "MODEL-WORK-UNIT-" + "E" * 64}
HUMAN_AUTHORITY_REF = {"kind": "human_authority", "id": "AUTH-0001"}
PREDECESSOR_REF = {"kind": "model_execution_envelope", "id": "MODEL-EXECUTION-" + "1" * 64}
SUCCESSOR_REF = {"kind": "model_execution_envelope", "id": "MODEL-EXECUTION-" + "2" * 64}
FINGERPRINT = {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "a" * 64}
OTHER_FINGERPRINT = {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "b" * 64}
EVIDENCE_REQUIREMENTS = {
    "evidence_position": "CHANGE_FREE_VERIFICATION_EVIDENCE",
    "required_request_keys": ["change_request", "recorded_at", "schema_version"],
    "required_provenance_fields": ["observations", "project_id", "status"],
}
ADAPTER_X = {"adapter": "fake_model_adapter", "version": "0.1"}
ADAPTER_Y = {"adapter": "request_derived_model_adapter", "version": "0.1"}


def boundary_record() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "project_id": PROJECT_ID,
        "project_binding_ref": dict(BINDING_REF),
        "permitted_capability": "PROPOSE_EVIDENCE_CANDIDATE",
        "permitted_candidate_kinds": ["OBSERVATION_CANDIDATE"],
        "permitted_candidate_fields": ["summary", "observed_status"],
        "declared_by": dict(HUMAN_AUTHORITY_REF),
        "declared_at": "2026-09-08T00:00:00Z",
    }


def work_unit_record() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "project_id": PROJECT_ID,
        "project_binding_ref": dict(BINDING_REF),
        "opened_state_revision": 3,
        "opened_semantic_fingerprint": dict(FINGERPRINT),
        "difference_ref": dict(DIFFERENCE_REF),
        "required_capability": "PROPOSE_EVIDENCE_CANDIDATE",
        "authority_ref": dict(AUTHORITY_REF),
        "boundary_ref": dict(BOUNDARY_REF),
        "evidence_requirements": dict(EVIDENCE_REQUIREMENTS),
        "opened_at": "2026-09-09T01:00:00Z",
    }


def envelope_record() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "project_id": PROJECT_ID,
        "project_binding_ref": dict(BINDING_REF),
        "model_work_unit_ref": dict(WORK_UNIT_REF),
        "model_execution_request_identity": "MODEL-EXECUTION-REQUEST-" + "F" * 64,
        "executed_state_revision": 4,
        "executed_semantic_fingerprint": dict(FINGERPRINT),
        "adapter_identity": dict(ADAPTER_X),
        "executed_at": "2026-09-09T02:00:00Z",
        "execution_outcome": "CANDIDATE_ACCEPTED",
        "normalized_candidate_kind": "OBSERVATION_CANDIDATE",
        "normalized_candidate": {"summary": "s", "observed_status": "ok"},
        "normalized_candidate_fingerprint": "sha256:" + "c" * 64,
        "difference_ref": dict(DIFFERENCE_REF),
        "required_capability": "PROPOSE_EVIDENCE_CANDIDATE",
        "authority_ref": dict(AUTHORITY_REF),
        "boundary_ref": dict(BOUNDARY_REF),
        "evidence_requirements": dict(EVIDENCE_REQUIREMENTS),
        "human_authority_ref": dict(HUMAN_AUTHORITY_REF),
    }


def swap_receipt_record() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "project_id": PROJECT_ID,
        "project_binding_ref": dict(BINDING_REF),
        "model_work_unit_ref": dict(WORK_UNIT_REF),
        "predecessor_execution_ref": dict(PREDECESSOR_REF),
        "predecessor_adapter_identity": dict(ADAPTER_X),
        "predecessor_state_revision": 4,
        "predecessor_semantic_fingerprint": dict(FINGERPRINT),
        "successor_execution_ref": dict(SUCCESSOR_REF),
        "successor_adapter_identity": dict(ADAPTER_Y),
        "successor_state_revision": 6,
        "successor_semantic_fingerprint": dict(OTHER_FINGERPRINT),
        "difference_ref": dict(DIFFERENCE_REF),
        "required_capability": "PROPOSE_EVIDENCE_CANDIDATE",
        "authority_ref": dict(AUTHORITY_REF),
        "boundary_ref": dict(BOUNDARY_REF),
        "evidence_requirements": dict(EVIDENCE_REQUIREMENTS),
        "recorded_at": "2026-09-09T05:00:00Z",
    }


def recovery_receipt_record() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "project_id": PROJECT_ID,
        "project_binding_ref": dict(BINDING_REF),
        "model_work_unit_ref": dict(WORK_UNIT_REF),
        "recovered_state_revision": 5,
        "recovered_semantic_fingerprint": dict(FINGERPRINT),
        "difference_ref": dict(DIFFERENCE_REF),
        "required_capability": "PROPOSE_EVIDENCE_CANDIDATE",
        "authority_ref": dict(AUTHORITY_REF),
        "boundary_ref": dict(BOUNDARY_REF),
        "evidence_requirements": dict(EVIDENCE_REQUIREMENTS),
        "recovered_at": "2026-09-09T03:00:00Z",
    }


def _mutate(value: Any) -> Any:
    """A genuinely different value of the same rough shape -- never merely `None`, which a
    careless implementation could special-case, and never a value that would be equal after
    canonical serialization."""

    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        return value + "-TAMPERED"
    if isinstance(value, list):
        return [*value, "TAMPERED"]
    if isinstance(value, dict):
        mutated = dict(value)
        first = next(iter(mutated))
        mutated[first] = _mutate(mutated[first])
        return mutated
    return "TAMPERED"


#: Every record kind this package mints, with the closed semantic-field tuple its own two
#: digests are computed over and the two functions that compute them. Parametrizing over this
#: table -- rather than writing five near-identical test bodies -- is what makes a new semantic
#: field impossible to add without it being tamper-proved here too.
_RECORDS = (
    ("model_execution_boundary", boundary_record, BOUNDARY_SEMANTIC_FIELDS,
     model_execution_boundary_id, model_execution_boundary_semantic_fingerprint),
    ("model_work_unit", work_unit_record, WORK_UNIT_SEMANTIC_FIELDS,
     model_work_unit_id, model_work_unit_semantic_fingerprint),
    ("model_execution_envelope", envelope_record, ENVELOPE_SEMANTIC_FIELDS,
     model_execution_envelope_id, model_execution_envelope_semantic_fingerprint),
    ("model_swap_receipt", swap_receipt_record, SWAP_RECEIPT_SEMANTIC_FIELDS,
     model_swap_receipt_id, model_swap_receipt_semantic_fingerprint),
    ("session_recovery_receipt", recovery_receipt_record, RECOVERY_RECEIPT_SEMANTIC_FIELDS,
     session_recovery_receipt_id, session_recovery_receipt_semantic_fingerprint),
)

_TAMPER_CASES = [
    pytest.param(builder, identity, fingerprint, field, id=f"{kind}.{field}")
    for kind, builder, fields, identity, fingerprint in _RECORDS
    for field in fields
]

_PREFIXES = {
    "model_execution_boundary": "MODEL-EXECUTION-BOUNDARY-",
    "model_work_unit": "MODEL-WORK-UNIT-",
    "model_execution_envelope": "MODEL-EXECUTION-",
    "model_swap_receipt": "MODEL-SWAP-",
    "session_recovery_receipt": "MODEL-SESSION-RECOVERY-",
}


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("kind", "builder", "identity", "fingerprint"),
    [
        pytest.param(kind, builder, identity, fingerprint, id=kind)
        for kind, builder, _fields, identity, fingerprint in _RECORDS
    ],
)
def test_identity_and_fingerprint_are_deterministic_over_content(
    kind: str, builder: Any, identity: Any, fingerprint: Any
) -> None:
    """The same record content always produces the same two digests, and both carry this record
    kind's own literal prefix -- so no two record kinds can ever collide at one address."""

    first, second = builder(), builder()
    assert identity(first) == identity(second)
    assert fingerprint(first) == fingerprint(second)
    assert identity(first).startswith(_PREFIXES[kind])
    assert len(identity(first)) == len(_PREFIXES[kind]) + 64
    assert fingerprint(first).startswith("sha256:")


@pytest.mark.parametrize(
    ("kind", "builder", "identity", "fingerprint"),
    [
        pytest.param(kind, builder, identity, fingerprint, id=kind)
        for kind, builder, _fields, identity, fingerprint in _RECORDS
    ],
)
def test_identity_ignores_key_order_of_the_record_it_is_given(
    kind: str, builder: Any, identity: Any, fingerprint: Any
) -> None:
    """Canonical serialization has one owner, and it orders keys itself -- so a record built in
    a different key order is the same record, not a second one."""

    original = builder()
    reordered = dict(reversed(list(original.items())))
    assert list(reordered) != list(original)
    assert identity(reordered) == identity(original)
    assert fingerprint(reordered) == fingerprint(original)


@pytest.mark.parametrize(
    ("kind", "builder", "identity", "fingerprint"),
    [
        pytest.param(kind, builder, identity, fingerprint, id=kind)
        for kind, builder, _fields, identity, fingerprint in _RECORDS
    ],
)
def test_a_records_own_digest_fields_do_not_participate_in_its_own_identity(
    kind: str, builder: Any, identity: Any, fingerprint: Any
) -> None:
    """An identity cannot be computed over itself: planting arbitrary declared digest fields on
    the record moves neither digest, which is exactly what makes "declared != recomputed" a
    usable tamper check rather than a circular one."""

    original = builder()
    planted = dict(original)
    planted[f"{kind}_id"] = "PLANTED-" + "0" * 64
    planted[f"{kind}_semantic_fingerprint"] = "sha256:" + "0" * 64
    assert identity(planted) == identity(original)
    assert fingerprint(planted) == fingerprint(original)


# --------------------------------------------------------------------------- #
# Identity sensitivity: every authority-bearing and reference field, independently
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("builder", "identity", "fingerprint", "field"), _TAMPER_CASES)
def test_tampering_any_single_semantic_field_moves_both_digests(
    builder: Any, identity: Any, fingerprint: Any, field: str
) -> None:
    """Every field in every record kind's own closed semantic projection is tampered
    independently here -- ``authority_ref``, ``difference_ref``, ``boundary_ref``,
    ``model_work_unit_ref``, both execution refs, ``project_binding_ref``,
    ``human_authority_ref``, ``required_capability``, ``evidence_requirements``, every State
    revision/fingerprint, every adapter identity and every outcome included -- and both digests
    must move. A field that could be edited without moving them would be a field the record's
    own address does not see."""

    original = builder()
    tampered = dict(original)
    tampered[field] = _mutate(original[field])
    assert tampered[field] != original[field]
    assert identity(tampered) != identity(original)
    assert fingerprint(tampered) != fingerprint(original)


@pytest.mark.parametrize(
    ("kind", "builder", "fields"),
    [pytest.param(kind, builder, fields, id=kind) for kind, builder, fields, _i, _f in _RECORDS],
)
def test_the_semantic_projection_is_exactly_the_record_minus_its_own_two_digest_fields(
    kind: str, builder: Any, fields: tuple[str, ...]
) -> None:
    """The harness before its subject: the tamper table above proves only as much as the field
    tuple it iterates. This pins that tuple to the real record body, so a field added to a
    record without being added to its own semantic projection fails here rather than silently
    escaping every tamper proof above."""

    assert set(builder()) == set(fields)


@pytest.mark.parametrize(
    ("kind", "builder", "fields", "identity"),
    [pytest.param(kind, builder, fields, identity, id=kind) for kind, builder, fields, identity, _f in _RECORDS],
)
def test_a_record_missing_any_semantic_field_refuses_rather_than_addressing_a_partial_body(
    kind: str, builder: Any, fields: tuple[str, ...], identity: Any
) -> None:
    """A partial body has no identity here: refusing is what stops two genuinely different
    records from sharing one address because a field was absent from both."""

    for field in fields:
        partial = {key: value for key, value in builder().items() if key != field}
        with pytest.raises(ModelRuntimeRequirementError):
            identity(partial)


# --------------------------------------------------------------------------- #
# V1's own "provider-neutral request" identity
# --------------------------------------------------------------------------- #


def _request_identity(**overrides: Any) -> str:
    payload: dict[str, Any] = {
        "model_work_unit_id_value": WORK_UNIT_REF["id"],
        "state_revision": 4,
        "semantic_fingerprint": dict(FINGERPRINT),
        "adapter_identity": dict(ADAPTER_X),
    }
    payload.update(overrides)
    return model_execution_request_identity(**payload)


def test_the_provider_neutral_request_identity_is_deterministic_and_prefixed() -> None:
    assert _request_identity() == _request_identity()
    assert _request_identity().startswith("MODEL-EXECUTION-REQUEST-")
    assert len(_request_identity()) == len("MODEL-EXECUTION-REQUEST-") + 64


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_work_unit_id_value", "MODEL-WORK-UNIT-" + "9" * 64),
        ("state_revision", 5),
        ("semantic_fingerprint", dict(OTHER_FINGERPRINT)),
        ("adapter_identity", dict(ADAPTER_Y)),
    ],
)
def test_every_input_to_the_provider_neutral_request_identity_is_identity_sensitive(
    field: str, value: Any
) -> None:
    """P16-C1 binds a model invocation to the exact State revision and semantic fingerprint, the
    Work Unit identity, and the specific adapter. Each of those four moves this identity
    independently -- so two invocations differing in any one of them can never share a request
    identity."""

    assert _request_identity(**{field: value}) != _request_identity()


def test_the_request_identity_is_transitively_sensitive_to_every_bound_reference() -> None:
    """The decisive half of P16-C1's own binding list. ``difference_ref``,
    ``required_capability``, ``authority_ref``, ``boundary_ref`` and ``evidence_requirements``
    do not appear in the request identity's own payload *directly* -- they appear through the
    Work Unit id, which is a content address over exactly those fields. This proves the chain
    actually holds: tampering any one of them moves the Work Unit id, which moves the request
    identity."""

    original = work_unit_record()
    baseline = _request_identity(model_work_unit_id_value=model_work_unit_id(original))
    for field in (
        "difference_ref",
        "required_capability",
        "authority_ref",
        "boundary_ref",
        "evidence_requirements",
        "opened_state_revision",
        "opened_semantic_fingerprint",
        "project_binding_ref",
    ):
        tampered = dict(original)
        tampered[field] = _mutate(original[field])
        assert (
            _request_identity(model_work_unit_id_value=model_work_unit_id(tampered)) != baseline
        ), field


def test_the_request_identity_carries_no_provider_specific_input_at_all() -> None:
    """P16-C1: provider-specific payloads, chat transcripts, hidden model memory and provider
    session ids are not canonical inputs. This is proved structurally rather than by example --
    the function is keyword-only and its complete parameter set is exactly the four
    provider-neutral inputs above, so there is no parameter through which one could arrive."""

    import inspect

    signature = inspect.signature(model_execution_request_identity)
    assert set(signature.parameters) == {
        "model_work_unit_id_value",
        "state_revision",
        "semantic_fingerprint",
        "adapter_identity",
    }
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


# --------------------------------------------------------------------------- #
# The normalized candidate's own fingerprint
# --------------------------------------------------------------------------- #


def test_the_candidate_fingerprint_is_deterministic_and_content_sensitive() -> None:
    candidate = {"summary": "s", "observed_status": "ok"}
    assert model_candidate_fingerprint(candidate) == model_candidate_fingerprint(dict(candidate))
    assert model_candidate_fingerprint(candidate).startswith("sha256:")
    assert model_candidate_fingerprint({"summary": "s", "observed_status": "not-ok"}) != (
        model_candidate_fingerprint(candidate)
    )
    assert model_candidate_fingerprint({"summary": "s"}) != model_candidate_fingerprint(candidate)
