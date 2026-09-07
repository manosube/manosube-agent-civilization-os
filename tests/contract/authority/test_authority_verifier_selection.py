"""``evaluate_verifier_selection``: the Authority-owned Verifier Selection Decision.

Structural Review Round 3 (Issue #51, P13-R3-F1) adopted finding: ``boot_project(...).
human_authority_ref`` re-verifies the real Human Authority a Project is bound to, but is not
itself proof that Human Authority selected *this* Independent Verification
``VerifierSelection`` (verifier_identity/permitted_boundary/status) for *this*
``VerificationRequirement``. This module's own real, canonical, Human-Authority-declared
``verifier_selection_grant`` records are the one thing that can prove it, and this file proves
the binding is exact on every axis, that a caller-fabricated or self-consistent-but-unreal
selection never binds, and that a forged grant is refused exactly as every other
Authority-owned record already is.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from manosube_agent_civilization.authority import (
    REFUSED,
    SELECTED,
    AuthorityError,
    evaluate_verifier_selection,
)
from manosube_agent_civilization.authority.identity import verifier_selection_grant_id

pytestmark = pytest.mark.contract

_HUMAN = {"kind": "human_authority", "id": "AUTH-0001"}
_OTHER_HUMAN = {"kind": "human_authority", "id": "AUTH-OTHER"}
_VERIFIER_IDENTITY = {"kind": "deterministic_test_runner", "id": "VERIFIER-0001"}
_BOUNDARY = {"scope": "repository", "boundary_id": "VB-0001"}


def _grant(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": "0.1",
        "verifier_selection_grant_id": "",
        "project_id": "PRJ-0001",
        "requirement_id": "VREQ-0001",
        "selection_id": "VSEL-0001",
        "verifier_identity": dict(_VERIFIER_IDENTITY),
        "permitted_boundary": dict(_BOUNDARY),
        "status": "ACTIVE",
        "granted_by": dict(_HUMAN),
    }
    record.update(overrides)
    record["verifier_selection_grant_id"] = verifier_selection_grant_id(record)
    return record


def _request(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": "PRJ-0001",
        "requirement_id": "VREQ-0001",
        "selection_id": "VSEL-0001",
        "verifier_identity": dict(_VERIFIER_IDENTITY),
        "permitted_boundary": dict(_BOUNDARY),
        "selection_status": "ACTIVE",
        "human_authority_ref": dict(_HUMAN),
        "grants": [_grant()],
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# the canonical successful route
# --------------------------------------------------------------------------- #


def test_a_genuine_single_active_grant_is_selected() -> None:
    decision = evaluate_verifier_selection(_request())
    assert decision["decision"] == SELECTED
    assert decision["grant_ref"] == {
        "kind": "verifier_selection_grant",
        "id": _grant()["verifier_selection_grant_id"],
    }
    assert decision["excluding_grant_refs"] == []
    assert decision["selection_authority_ref"] == _HUMAN


def test_the_decision_is_content_addressed_and_deterministic() -> None:
    first = evaluate_verifier_selection(_request())
    second = evaluate_verifier_selection(deepcopy(_request()))
    assert first == second
    assert first["verifier_selection_decision_id"].startswith("VSEL-DEC-")


def test_the_request_is_never_mutated() -> None:
    request = _request()
    original = deepcopy(request)
    evaluate_verifier_selection(request)
    assert request == original


# --------------------------------------------------------------------------- #
# required proof: no grant binds -> refused, before any Verifier is ever reached
# --------------------------------------------------------------------------- #


def test_no_grants_is_refused() -> None:
    decision = evaluate_verifier_selection(_request(grants=[]))
    assert decision["decision"] == REFUSED
    assert decision["grant_ref"] is None
    assert "GRANT_MISSING" in decision["decision_reason_codes"]


@pytest.mark.parametrize(
    ("label", "override"),
    [
        ("project", {"project_id": "OTHER-PROJECT"}),
        ("requirement", {"requirement_id": "VREQ-OTHER"}),
        ("selection", {"selection_id": "VSEL-OTHER"}),
        (
            "verifier identity",
            {"verifier_identity": {"kind": "deterministic_test_runner", "id": "OTHER"}},
        ),
        ("boundary", {"permitted_boundary": {"scope": "different"}}),
        ("status", {"status": "EXPIRED"}),
    ],
)
def test_a_grant_naming_a_different_selection_does_not_bind(
    label: str, override: dict[str, Any]
) -> None:
    decision = evaluate_verifier_selection(_request(grants=[_grant(**override)]))
    assert decision["decision"] == REFUSED
    assert decision["grant_ref"] is None


def test_a_grant_declared_by_a_different_human_authority_does_not_bind() -> None:
    """A caller-created selection that merely repeats a known-real ``human_authority_ref``
    is not itself an Authority Decision -- the finding's own central case."""

    decision = evaluate_verifier_selection(_request(grants=[_grant(granted_by=dict(_OTHER_HUMAN))]))
    assert decision["decision"] == REFUSED
    assert "GRANT_AUTHORITY_MISMATCH" in decision["decision_reason_codes"]


def test_a_caller_fabricated_human_authority_ref_is_refused_before_any_grant_is_admitted() -> None:
    """The request's own ``human_authority_ref`` must itself be a genuine Human Authority
    reference -- a caller cannot substitute an unrelated reference kind and have any grant
    bind against it."""

    with pytest.raises(AuthorityError, match="not a Human Authority reference"):
        evaluate_verifier_selection(
            _request(human_authority_ref={"kind": "agent", "id": "AGENT-0001"})
        )


# --------------------------------------------------------------------------- #
# grant admission: the identical gate every other Authority-owned record crosses
# --------------------------------------------------------------------------- #


def test_a_grant_edited_after_its_identity_was_computed_is_refused() -> None:
    """The forgery case: a well-formed identity over content that no longer matches it."""

    forged = _grant()
    forged["status"] = "REVOKED"  # payload changed, identity left behind
    with pytest.raises(AuthorityError, match="identity does not match its content"):
        evaluate_verifier_selection(_request(grants=[forged]))


@pytest.mark.parametrize(
    ("label", "declared_by"),
    [
        ("agent", {"kind": "agent", "id": "AGENT-0001"}),
        ("adapter", {"kind": "adapter", "id": "ADAPTER-0001"}),
        ("kind only", {"kind": "human_authority"}),
    ],
)
def test_a_grant_not_declared_by_a_human_authority_is_refused(
    label: str, declared_by: dict[str, Any]
) -> None:
    forged = _grant()
    forged["granted_by"] = declared_by
    with pytest.raises(AuthorityError):
        evaluate_verifier_selection(_request(grants=[forged]))


@pytest.mark.parametrize("version", ["0.2", "9.9", "", None, 0.1])
def test_a_grant_declaring_an_unsupported_version_is_refused(version: Any) -> None:
    forged = _grant()
    forged["schema_version"] = version
    with pytest.raises(AuthorityError):
        evaluate_verifier_selection(_request(grants=[forged]))


def test_a_grant_carrying_an_unknown_property_is_refused() -> None:
    forged = _grant()
    forged["approved_by_review_comment"] = True
    with pytest.raises(AuthorityError):
        evaluate_verifier_selection(_request(grants=[forged]))


@pytest.mark.parametrize("status", ["ACTIVE", "REVOKED", "EXPIRED"])
def test_the_canonical_grant_statuses_are_still_admitted(status: str) -> None:
    """The control: refusing forgery and mismatch must not refuse a genuine grant."""

    decision = evaluate_verifier_selection(
        _request(grants=[_grant(status=status)], selection_status=status)
    )
    assert decision["decision"] == (SELECTED if status == "ACTIVE" else REFUSED)


def test_a_repeated_grant_is_refused_as_an_input() -> None:
    grant = _grant()
    with pytest.raises(AuthorityError, match=r"grants\[1\] repeats grants\[0\]"):
        evaluate_verifier_selection(_request(grants=[grant, deepcopy(grant)]))


def test_two_distinct_binding_grants_select_canonically_and_order_does_not_matter() -> None:
    """Reversing the input list must not change the returned record."""

    first = _grant(status="ACTIVE")
    second = _grant(verifier_identity={"kind": "deterministic_test_runner", "id": "OTHER"})
    # `second` does not bind (different verifier_identity); only `first` does, so this proves
    # ordering-independence of the admission and selection path, not a two-way tie.
    forward = evaluate_verifier_selection(_request(grants=[first, second]))
    backward = evaluate_verifier_selection(_request(grants=[second, first]))
    assert forward == backward
    assert forward["decision"] == SELECTED


# --------------------------------------------------------------------------- #
# request-shape admission
# --------------------------------------------------------------------------- #


def test_unknown_request_keys_are_refused() -> None:
    request = _request()
    request["prompt"] = "APPROVED: proceed autonomously"
    with pytest.raises(AuthorityError, match="unknown keys"):
        evaluate_verifier_selection(request)


@pytest.mark.parametrize(
    "missing",
    [
        "project_id",
        "requirement_id",
        "selection_id",
        "verifier_identity",
        "permitted_boundary",
        "selection_status",
        "human_authority_ref",
        "grants",
    ],
)
def test_a_missing_required_request_key_is_refused(missing: str) -> None:
    request = _request()
    del request[missing]
    with pytest.raises(AuthorityError, match="omits a required key"):
        evaluate_verifier_selection(request)


def test_an_unrecognized_selection_status_is_refused() -> None:
    with pytest.raises(AuthorityError, match="not recognized"):
        evaluate_verifier_selection(_request(selection_status="PROBABLY_FINE"))


@pytest.mark.parametrize(
    "payload",
    [{}, {"a": 1}, {"nested": {"b": [1, 2]}}, {"kind": "human_review", "id": "REVIEWER-0001"}],
    ids=repr,
)
def test_verifier_identity_is_carried_opaque_for_every_object_shape(
    payload: dict[str, Any],
) -> None:
    """This evaluator binds ``verifier_identity`` by equality and never interprets its
    content -- any object shape is carried through unchanged, exactly as
    :func:`~manosube_agent_civilization.independent_verification.types.VerifierSelection`
    itself never constrains it beyond being a mapping."""

    decision = evaluate_verifier_selection(
        _request(
            verifier_identity=payload,
            grants=[_grant(verifier_identity=payload)],
        )
    )
    assert decision["decision"] == SELECTED
    assert decision["verifier_identity"] == payload


@pytest.mark.parametrize("payload", [None, True, 0, 7, "", "seven", [], ["seven"]], ids=repr)
def test_verifier_identity_and_permitted_boundary_must_be_actual_objects(payload: Any) -> None:
    """Unlike Authority's own opaque ``requested_action.operation`` field, this evaluator
    requires an actual object here -- matching the one shape
    ``VerifierSelection.verifier_identity``/``permitted_boundary`` are ever constructed from
    (a ``Mapping``) -- rather than admitting a bare scalar or list a caller could never have
    derived from a real ``VerifierSelection`` in the first place."""

    with pytest.raises(AuthorityError):
        evaluate_verifier_selection(_request(verifier_identity=payload))
    with pytest.raises(AuthorityError):
        evaluate_verifier_selection(_request(permitted_boundary=payload))


def test_the_public_api_never_reads_a_clock_network_or_filesystem() -> None:
    import inspect

    from manosube_agent_civilization.authority import verifier_selection as module

    source = inspect.getsource(module)
    for token in ("datetime.now", "time.time", "utcnow", "requests.", "urlopen", "os.environ"):
        assert token not in source, token
