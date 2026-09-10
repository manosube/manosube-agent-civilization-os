"""The Model Execution Decision evaluator, on its own (Phase 16, Issue #66).

Phase 16's V4 matrix exercises this evaluator end to end, through the route that calls it. This
file proves the properties that belong to the *evaluator itself* and that a route-level test can
only observe indirectly:

```text
never raises for a readable-but-unauthorized request   -- it answers MODEL_EXECUTION_REFUSED
always raises for an unreadable one                    -- AuthorityError, never a TypeError
deterministic and content-addressed                    -- the same question, the same id
distinctness before activeness                         -- a grant for another question is not
                                                          this question's grant, whatever its
                                                          own status says
the signature is what makes a grant bind               -- a Store-committed, correctly
                                                          `granted_by`-shaped grant with a
                                                          wrong-key signature binds nothing
```

Every grant here is genuinely Ed25519-signed by this repository's own test-only signing helper,
against the canonical payload the record's own content address is computed over. A real Human's
private key never touches this system; shipped code only ever verifies.
"""

from __future__ import annotations

import hashlib
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest
from tests.fixtures.model_runtime_world import (
    PROJECT_ID,
    canonical_signing_private_key,
    foreign_signing_private_key,
    grant_for,
    human_authority_signing_key,
)
from tests.fixtures.product_binding import human_authority_ref

from manosube_agent_civilization.authority import (
    AuthorityError,
    evaluate_model_execution_authorization,
)
from manosube_agent_civilization.authority.model_execution_authorization import (
    AUTHORIZED,
    DECISIONS,
    REFUSED,
    REQUIRED_REQUEST_KEYS,
)

pytestmark = pytest.mark.contract

DIFFERENCE_REF = {"kind": "difference", "id": "D-" + "B" * 64}
OTHER_DIFFERENCE_REF = {"kind": "difference", "id": "D-" + "C" * 64}
BOUNDARY_REF = {"kind": "model_execution_boundary", "id": "MODEL-EXECUTION-BOUNDARY-" + "D" * 64}
OTHER_BOUNDARY_REF = {
    "kind": "model_execution_boundary",
    "id": "MODEL-EXECUTION-BOUNDARY-" + "E" * 64,
}
CAPABILITY = "PROPOSE_EVIDENCE_CANDIDATE"


def request_for(**overrides: Any) -> dict[str, Any]:
    """One complete, readable Model Execution request -- deep enough to be answered, closed
    enough that an unknown key is refused rather than ignored."""

    body: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": PROJECT_ID,
        "difference_ref": dict(DIFFERENCE_REF),
        "required_capability": CAPABILITY,
        "boundary_ref": dict(BOUNDARY_REF),
        "human_authority_ref": dict(human_authority_ref()),
        "human_authority_signing_key": dict(human_authority_signing_key()),
        "grants": [],
    }
    body.update(overrides)
    return body


def binding_grant(**overrides: Any) -> dict[str, Any]:
    return grant_for(PROJECT_ID, DIFFERENCE_REF, BOUNDARY_REF, **overrides)


# --------------------------------------------------------------------------- #
# The positive path
# --------------------------------------------------------------------------- #


def test_a_genuine_active_signed_grant_authorizes_this_exact_question() -> None:
    grant = binding_grant()
    decision = evaluate_model_execution_authorization(request_for(grants=[grant]))
    assert decision["decision"] == AUTHORIZED
    assert decision["decision_reason_codes"] == ["GRANT_EXACT"]
    assert decision["grant_ref"] == {
        "kind": "model_execution_grant",
        "id": grant["model_execution_grant_id"],
    }
    assert decision["excluding_grant_refs"] == []
    assert decision["difference_ref"] == DIFFERENCE_REF
    assert decision["boundary_ref"] == BOUNDARY_REF
    assert decision["required_capability"] == CAPABILITY
    assert decision["selection_authority_ref"] == human_authority_ref()


def test_the_same_question_always_produces_the_same_decision_identity() -> None:
    """Content-addressed: two evaluations of one question are one decision, so a Work Unit's
    ``authority_ref`` names a stable address rather than a per-call artifact."""

    grant = binding_grant()
    first = evaluate_model_execution_authorization(request_for(grants=[grant]))
    second = evaluate_model_execution_authorization(request_for(grants=[dict(grant)]))
    assert first == second


def test_the_request_is_never_mutated() -> None:
    request = request_for(grants=[binding_grant()])
    before = dict(request)
    evaluate_model_execution_authorization(request)
    assert request == before


def test_the_decision_is_independent_of_the_order_grants_arrive_in() -> None:
    """Chosen by identity, not by input position -- the same determinism every other evaluator
    in this package already guarantees for its own grant selection."""

    first = binding_grant()
    second = binding_grant(granted_at="2026-09-08T02:00:00Z")
    assert first["model_execution_grant_id"] != second["model_execution_grant_id"]
    forwards = evaluate_model_execution_authorization(request_for(grants=[first, second]))
    backwards = evaluate_model_execution_authorization(request_for(grants=[second, first]))
    assert forwards == backwards
    assert forwards["decision"] == AUTHORIZED


# --------------------------------------------------------------------------- #
# Readable-but-unauthorized is a decision, never an exception
# --------------------------------------------------------------------------- #


def test_a_request_naming_no_grant_at_all_is_refused_rather_than_raising() -> None:
    decision = evaluate_model_execution_authorization(request_for(grants=[]))
    assert decision["decision"] == REFUSED
    assert decision["decision_reason_codes"] == ["GRANT_MISSING"]
    assert decision["grant_ref"] is None


@pytest.mark.parametrize("status", ["REVOKED", "EXPIRED"])
def test_a_core_clean_but_inactive_grant_withholds_authorization(status: str) -> None:
    """A grant that binds on every field but is not ACTIVE withholds authorization exactly as an
    excluding Approval withholds a Change -- and is *named* in the decision, as an excluding
    grant, rather than silently ignored."""

    grant = binding_grant(status=status)
    decision = evaluate_model_execution_authorization(request_for(grants=[grant]))
    assert decision["decision"] == REFUSED
    assert decision["decision_reason_codes"] == [f"GRANT_{status}"]
    assert decision["excluding_grant_refs"] == [
        {"kind": "model_execution_grant", "id": grant["model_execution_grant_id"]}
    ]


def test_a_grant_signed_by_the_wrong_key_binds_nothing() -> None:
    """The decisive control: a Store-committable, self-consistent, correctly ``granted_by``-shaped
    grant authorizes zero model executions unless its signature genuinely verifies against the
    exact key a real Project Binding holds."""

    grant = binding_grant(signer=foreign_signing_private_key())
    decision = evaluate_model_execution_authorization(request_for(grants=[grant]))
    assert decision["decision"] == REFUSED
    assert decision["decision_reason_codes"] == ["GRANT_SIGNATURE_INVALID"]


def test_an_unsigned_grant_binds_nothing() -> None:
    grant = binding_grant()
    del grant["signature"]
    with pytest.raises(AuthorityError):
        # The schema requires `signature`; an absent one is an unreadable record, not a
        # differently-decided one -- the admission gate refuses it before any decision exists.
        evaluate_model_execution_authorization(request_for(grants=[grant]))


def test_a_grant_signed_under_a_key_id_the_binding_does_not_hold_binds_nothing() -> None:
    """Algorithm and ``key_id`` must both match the Project Binding's own declared key before the
    Ed25519 primitive is even reached -- the identical four-line composition Runtime's own signed
    record kind already uses."""

    grant = binding_grant(signing_key_id="AUTH-KEY-SOMEONE-ELSE")
    decision = evaluate_model_execution_authorization(request_for(grants=[grant]))
    assert decision["decision"] == REFUSED
    assert decision["decision_reason_codes"] == ["GRANT_SIGNATURE_INVALID"]


@pytest.mark.parametrize(
    ("label", "grant_kwargs", "reason"),
    [
        (
            "difference",
            {"difference_ref": OTHER_DIFFERENCE_REF},
            "GRANT_DIFFERENCE_MISMATCH",
        ),
        ("boundary", {"boundary_ref": OTHER_BOUNDARY_REF}, "GRANT_BOUNDARY_MISMATCH"),
        (
            "authority",
            {"granted_by": {"kind": "human_authority", "id": "AUTH-SOMEONE-ELSE"}},
            "GRANT_AUTHORITY_MISMATCH",
        ),
    ],
)
def test_a_grant_for_a_different_question_is_not_this_questions_grant(
    label: str, grant_kwargs: dict[str, Any], reason: str
) -> None:
    """Distinctness before activeness: a grant naming a different Difference, Boundary or Human
    Authority is not *this* question's grant at all, whatever its own status is -- so it is
    reported as a core mismatch rather than as an excluding grant."""

    grant = grant_for(
        PROJECT_ID,
        grant_kwargs.pop("difference_ref", DIFFERENCE_REF),
        grant_kwargs.pop("boundary_ref", BOUNDARY_REF),
        **grant_kwargs,
    )
    decision = evaluate_model_execution_authorization(request_for(grants=[grant]))
    assert decision["decision"] == REFUSED
    assert reason in decision["decision_reason_codes"]
    assert decision["excluding_grant_refs"] == []


def test_a_grant_belonging_to_a_different_project_is_not_this_projects_grant() -> None:
    grant = grant_for("PRJ-BIND-0002", DIFFERENCE_REF, BOUNDARY_REF)
    decision = evaluate_model_execution_authorization(request_for(grants=[grant]))
    assert decision["decision"] == REFUSED
    assert "GRANT_PROJECT_MISMATCH" in decision["decision_reason_codes"]


# --------------------------------------------------------------------------- #
# Unreadable is an exception, never a decision
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("key", sorted(REQUIRED_REQUEST_KEYS))
def test_a_request_omitting_any_required_key_is_refused_as_unreadable(key: str) -> None:
    request = request_for(grants=[binding_grant()])
    del request[key]
    with pytest.raises(AuthorityError):
        evaluate_model_execution_authorization(request)


def test_a_request_carrying_an_unknown_key_is_refused_rather_than_ignored() -> None:
    """The key set is closed, and that is the security property rather than a tidiness one: an
    ignored extra key is still a key a caller can believe was considered."""

    request = request_for(grants=[binding_grant()])
    request["agent_conclusion"] = "the model says this is fine"
    with pytest.raises(AuthorityError):
        evaluate_model_execution_authorization(request)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("schema_version", "0.2"),
        ("required_capability", "DO_ANYTHING"),
        ("difference_ref", {"kind": "model_work_unit", "id": "MODEL-WORK-UNIT-" + "0" * 64}),
        ("boundary_ref", {"kind": "difference", "id": "D-" + "0" * 64}),
        ("human_authority_ref", {"kind": "agent", "id": "AGENT-0001"}),
        ("difference_ref", {"kind": "difference"}),
        ("grants", "not-a-collection"),
    ],
)
def test_an_unreadable_or_out_of_vocabulary_input_raises_rather_than_deciding(
    key: str, value: Any
) -> None:
    with pytest.raises(AuthorityError):
        evaluate_model_execution_authorization(request_for(**{key: value}))


def test_a_grant_whose_declared_identity_does_not_match_its_content_is_refused() -> None:
    """The admission gate's own third question, which every per-record check forgets: an identity
    is a claim about content, and recomputing it is the only thing that makes forgery visible."""

    grant = binding_grant()
    grant["model_execution_grant_id"] = "MODEL-EXEC-GRANT-" + "0" * 64
    with pytest.raises(AuthorityError):
        evaluate_model_execution_authorization(request_for(grants=[grant]))


def test_a_grant_not_declared_by_a_human_authority_is_refused() -> None:
    """``CAPABILITY_AUTHORITY_SEPARATION.md`` §2: no model, adapter, agent or Kernel component may
    occupy ``granted_by``."""

    grant = binding_grant(granted_by={"kind": "human_authority", "id": "AUTH-0001"})
    grant["granted_by"] = {"kind": "agent", "id": "AGENT-0001"}
    with pytest.raises(AuthorityError):
        evaluate_model_execution_authorization(request_for(grants=[grant]))


def test_the_same_grant_supplied_twice_is_refused_rather_than_folded_away() -> None:
    """A canonical record supplied twice is one record, not two -- the identical refusal
    ``admit_all`` already applies to every other Authority-owned collection."""

    grant = binding_grant()
    with pytest.raises(AuthorityError):
        evaluate_model_execution_authorization(request_for(grants=[grant, dict(grant)]))


# --------------------------------------------------------------------------- #
# The vocabulary itself
# --------------------------------------------------------------------------- #


def test_the_decision_vocabulary_is_closed_to_exactly_two_members() -> None:
    assert {AUTHORIZED, REFUSED} == DECISIONS
    assert AUTHORIZED == "MODEL_EXECUTION_AUTHORIZED"
    assert REFUSED == "MODEL_EXECUTION_REFUSED"


def test_every_decision_this_evaluator_can_produce_is_inside_that_vocabulary() -> None:
    produced = set()
    for grants in (
        [],
        [binding_grant()],
        [binding_grant(status="REVOKED")],
        [binding_grant(signer=foreign_signing_private_key())],
        [grant_for(PROJECT_ID, OTHER_DIFFERENCE_REF, BOUNDARY_REF)],
    ):
        produced.add(evaluate_model_execution_authorization(request_for(grants=grants))["decision"])
    assert produced == DECISIONS


def test_the_test_signing_keys_are_genuinely_different_key_pairs() -> None:
    """The harness before its subject: every negative control above rests on the foreign key
    actually being a different key, so that is asserted rather than assumed."""

    canonical: Ed25519PrivateKey = canonical_signing_private_key()
    foreign: Ed25519PrivateKey = foreign_signing_private_key()
    canonical_digest = hashlib.sha256(canonical.public_key().public_bytes_raw()).hexdigest()
    foreign_digest = hashlib.sha256(foreign.public_key().public_bytes_raw()).hexdigest()
    assert canonical_digest != foreign_digest
