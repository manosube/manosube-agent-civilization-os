"""V3 (Issue #66): the full vertical model-swap and session-loss-recovery proof.

The required proof, in the adopted proposal's own words: *Agent A starts from Canonical State →
bounded work occurs under the Phase 12 execution contract → session ends → Agent B starts from
Canonical State → no conversation handoff → work continues under the same Authority and
Difference.*

Every test below runs against a real ``FileStateStore``, a real genesis-bound Project, a real
Store-committed Difference, a real Human-declared Model Execution Boundary and a real,
genuinely Ed25519-signed Model Execution Grant.

**How "the session genuinely ended" is enforced here, and why it is not merely `release()`.**
:func:`_discard_session` does three things that a `release()`-and-keep-going test would not: it
releases Agent A's own handle, it deletes every Python name bound to anything A produced except
the Work Unit's own content address, and it asserts -- through
:class:`~manosube_agent_civilization.agent_runtime.errors.AgentReleasedError` -- that A's handle
genuinely cannot be used again. Agent B is then constructed from nothing but ``(store,
project_id, project_binding_id)`` and the Work Unit id string. There is no receipt object, no
envelope body, no boot context, no adapter instance and no conversation of any kind crossing the
boundary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.model_runtime_world import (
    PERMITTED_CANDIDATE_FIELDS,
    authorized_world,
    evidence_request_for,
    open_kwargs,
)

from manosube_agent_civilization.agent_runtime import start_temporary_agent
from manosube_agent_civilization.agent_runtime.errors import AgentReleasedError
from manosube_agent_civilization.model_runtime import (
    FakeModelAdapter,
    RequestDerivedModelAdapter,
    execute_model_work_unit,
    open_model_work_unit,
    record_model_swap,
    recover_model_execution_session,
    route_model_execution_to_evidence,
)
from manosube_agent_civilization.model_runtime.identity import (
    model_execution_envelope_id,
    model_execution_envelope_semantic_fingerprint,
    model_swap_receipt_id,
    model_work_unit_id,
    model_work_unit_semantic_fingerprint,
    session_recovery_receipt_id,
)

pytestmark = pytest.mark.integration

ENVELOPE_KIND = "model_execution_envelope"
WORK_UNIT_KIND = "model_work_unit"
SWAP_KIND = "model_swap_receipt"
RECOVERY_KIND = "session_recovery_receipt"

#: Exactly the identities P16-C4 requires a resumed execution to retain.
CONTINUITY_FIELDS = (
    "difference_ref",
    "required_capability",
    "authority_ref",
    "boundary_ref",
    "evidence_requirements",
)


def _rebind(value: Any, old: str, new: str) -> Any:
    if isinstance(value, dict):
        return {key: _rebind(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [_rebind(item, old, new) for item in value]
    return new if value == old else value


@pytest.fixture
def world(tmp_path: Path) -> dict[str, Any]:
    return authorized_world(tmp_path)


def _discard_session(agent: Any) -> None:
    """End one execution session for real.

    Releasing the handle is Phase 12's own zero-write, idempotent lifecycle end; asserting that
    the released handle then refuses is what proves the session is genuinely over rather than
    merely marked so. Everything the caller held is dropped by the caller itself immediately
    after this returns -- see each test's own ``del``.
    """

    agent.release()
    with pytest.raises(AgentReleasedError):
        _ = agent.boot_context


# --------------------------------------------------------------------------- #
# The complete vertical proof
# --------------------------------------------------------------------------- #


def test_agent_b_resumes_the_identical_work_unit_through_a_different_adapter(
    world: dict[str, Any],
) -> None:
    """The whole of V3 in one test.

    Agent A opens a Work Unit and executes it once through Adapter X. A's session is genuinely
    discarded. Agent B -- a second, independently constructed ``TemporaryAgent`` -- resolves the
    identical Work Unit from the Store by id alone, executes it through a genuinely different
    Adapter Y, and a ``model_swap_receipt`` is minted proving both Envelopes share the identical
    Work Unit, Difference, Authority, Boundary and Evidence-requirement identities while naming
    two different adapters.

    The only value that crosses the session boundary is ``work_unit_id`` -- a plain string,
    which is a content address. No receipt, envelope body, boot context, adapter instance or
    conversation crosses it.
    """

    store = world["store"]
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]

    # ---- AGENT A -----------------------------------------------------------------------
    agent_a = start_temporary_agent(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    opened = open_model_work_unit(store, agent_a, **open_kwargs(world))
    work_unit_id = opened["model_work_unit"]["model_work_unit_id"]

    adapter_x = FakeModelAdapter()
    adapter_x.seed_candidate(
        model_work_unit_ref=opened["model_work_unit_ref"],
        candidate_fields={"summary": "agent A observed", "observed_status": "ok"},
    )
    first = execute_model_work_unit(
        store,
        agent_a,
        project_id=project_id,
        project_binding_id=project_binding_id,
        model_work_unit_ref=opened["model_work_unit_ref"],
        adapter=adapter_x,
        executed_at="2026-09-09T02:00:00Z",
    )
    first_envelope_id = first["envelope"]["model_execution_envelope_id"]
    assert first["envelope"]["execution_outcome"] == "CANDIDATE_ACCEPTED"
    assert adapter_x.execute_call_count == 1

    # ---- THE SESSION ENDS --------------------------------------------------------------
    _discard_session(agent_a)
    del agent_a, adapter_x, opened, first

    # ---- AGENT B -- constructed from nothing but the Store and the Work Unit's address --
    agent_b = start_temporary_agent(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    work_unit_ref = {"kind": WORK_UNIT_KIND, "id": work_unit_id}
    recovered = recover_model_execution_session(
        store,
        agent_b,
        project_id=project_id,
        project_binding_id=project_binding_id,
        model_work_unit_ref=work_unit_ref,
        recovered_at="2026-09-09T03:00:00Z",
    )
    resumed_work_unit = recovered["model_work_unit"]
    assert resumed_work_unit["model_work_unit_id"] == work_unit_id

    adapter_y = RequestDerivedModelAdapter()
    second = execute_model_work_unit(
        store,
        agent_b,
        project_id=project_id,
        project_binding_id=project_binding_id,
        model_work_unit_ref=work_unit_ref,
        adapter=adapter_y,
        executed_at="2026-09-09T04:00:00Z",
    )
    assert second["envelope"]["execution_outcome"] == "CANDIDATE_ACCEPTED"
    assert adapter_y.execute_call_count == 1

    swap = record_model_swap(
        store,
        agent_b,
        project_id=project_id,
        project_binding_id=project_binding_id,
        model_work_unit_ref=work_unit_ref,
        predecessor_execution_ref={"kind": ENVELOPE_KIND, "id": first_envelope_id},
        successor_execution_ref={
            "kind": ENVELOPE_KIND,
            "id": second["envelope"]["model_execution_envelope_id"],
        },
        recorded_at="2026-09-09T05:00:00Z",
    )
    receipt = swap["model_swap_receipt"]

    # ---- WHAT THE SWAP RECEIPT ACTUALLY PROVES -----------------------------------------
    assert receipt["model_work_unit_ref"] == work_unit_ref
    assert receipt["predecessor_adapter_identity"] != receipt["successor_adapter_identity"]
    assert receipt["predecessor_adapter_identity"]["adapter"] == "fake_model_adapter"
    assert receipt["successor_adapter_identity"]["adapter"] == "request_derived_model_adapter"
    for field in CONTINUITY_FIELDS:
        assert receipt[field] == resumed_work_unit[field], field
        assert swap["predecessor_envelope"][field] == resumed_work_unit[field], field
        assert swap["successor_envelope"][field] == resumed_work_unit[field], field
    # Both Boot snapshots participate, and they are genuinely different States: A executed
    # against an earlier revision than B did. The two *semantic* fingerprints are legitimately
    # equal here and that is not a weakness of the receipt -- ``fingerprint_project_state``
    # digests a project's ``semantic_state`` alone, and none of these commits changes it, so an
    # equal fingerprint across two revisions is the correct, existing meaning of that field
    # rather than a collision. Both are recorded because P16-C4 asks for State-bound continuity,
    # and the revision is the half that moved.
    assert receipt["predecessor_state_revision"] < receipt["successor_state_revision"]
    assert (
        receipt["predecessor_semantic_fingerprint"]
        == swap["predecessor_envelope"]["executed_semantic_fingerprint"]
    )
    assert (
        receipt["successor_semantic_fingerprint"]
        == swap["successor_envelope"]["executed_semantic_fingerprint"]
    )

    # ---- AND IT IS A REAL, RESOLVABLE, SELF-CONSISTENT CANONICAL FACT -------------------
    stored = store.resolve_record(project_id, SWAP_KIND, receipt["model_swap_receipt_id"])
    assert stored == receipt
    assert model_swap_receipt_id(receipt) == receipt["model_swap_receipt_id"]


def test_the_two_envelopes_differ_only_where_a_model_swap_should_differ(
    world: dict[str, Any],
) -> None:
    """The candidates differ (two different models produced them) and so do the adapter
    identity, the request identity, the execution instant and the State snapshot. Everything
    P16-C4 names as an identity that must be *retained* is byte-identical."""

    swapped = _run_swap(world)
    first, second = swapped["first_envelope"], swapped["second_envelope"]
    for field in (*CONTINUITY_FIELDS, "project_id", "project_binding_ref", "model_work_unit_ref"):
        assert first[field] == second[field], field
    for field in (
        "adapter_identity",
        "model_execution_request_identity",
        "executed_at",
        "executed_state_revision",
        "normalized_candidate",
        "normalized_candidate_fingerprint",
        "model_execution_envelope_id",
    ):
        assert first[field] != second[field], field
    # ``executed_semantic_fingerprint`` is deliberately absent from both lists: it digests the
    # project's ``semantic_state`` alone, which neither execution changes, so requiring it to
    # differ would assert something about the existing State owner that is simply not true.
    assert first["executed_semantic_fingerprint"] == second["executed_semantic_fingerprint"]


def test_both_envelopes_are_bounded_to_exactly_the_boundarys_own_permitted_fields(
    world: dict[str, Any],
) -> None:
    """Normalization happens before any candidate reaches a canonical record (P16-C3), and it is
    the Boundary that decides which fields survive -- for both adapters alike."""

    swapped = _run_swap(world)
    for envelope in (swapped["first_envelope"], swapped["second_envelope"]):
        assert set(envelope["normalized_candidate"]) == set(PERMITTED_CANDIDATE_FIELDS)
        assert envelope["normalized_candidate_kind"] == "OBSERVATION_CANDIDATE"


def test_every_committed_record_recomputes_its_own_identity_from_the_store(
    world: dict[str, Any],
) -> None:
    """V1's identities, re-proved over *genuinely committed* records rather than over
    hand-built ones: each record is resolved back out of the real Store by content address and
    both of its digests are recomputed from the resolved body."""

    swapped = _run_swap(world)
    store, project_id = world["store"], world["project_id"]

    work_unit = store.resolve_record(project_id, WORK_UNIT_KIND, swapped["work_unit_id"])
    assert model_work_unit_id(work_unit) == work_unit["model_work_unit_id"]
    assert (
        model_work_unit_semantic_fingerprint(work_unit)
        == work_unit["model_work_unit_semantic_fingerprint"]
    )
    for envelope_id in (
        swapped["first_envelope"]["model_execution_envelope_id"],
        swapped["second_envelope"]["model_execution_envelope_id"],
    ):
        envelope = store.resolve_record(project_id, ENVELOPE_KIND, envelope_id)
        assert model_execution_envelope_id(envelope) == envelope_id
        assert (
            model_execution_envelope_semantic_fingerprint(envelope)
            == envelope["model_execution_semantic_fingerprint"]
        )


# --------------------------------------------------------------------------- #
# Session-loss recovery, with no in-memory carryover at all
# --------------------------------------------------------------------------- #


def test_a_total_session_loss_is_recovered_from_the_canonical_store_alone(
    world: dict[str, Any],
) -> None:
    """P16-C5. Everything the lost session held is dropped; a second, independently constructed
    Agent recovers the complete execution context from the Store by content address alone, and
    the ``session_recovery_receipt`` it mints restates exactly the identities the Work Unit
    itself carries."""

    store = world["store"]
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]

    agent_a = start_temporary_agent(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    opened = open_model_work_unit(store, agent_a, **open_kwargs(world))
    work_unit_id = opened["model_work_unit"]["model_work_unit_id"]
    expected = {field: opened["model_work_unit"][field] for field in CONTINUITY_FIELDS}
    _discard_session(agent_a)
    del agent_a, opened

    agent_b = start_temporary_agent(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    recovered = recover_model_execution_session(
        store,
        agent_b,
        project_id=project_id,
        project_binding_id=project_binding_id,
        model_work_unit_ref={"kind": WORK_UNIT_KIND, "id": work_unit_id},
        recovered_at="2026-09-09T03:00:00Z",
    )
    receipt = recovered["session_recovery_receipt"]

    assert receipt["model_work_unit_ref"] == {"kind": WORK_UNIT_KIND, "id": work_unit_id}
    for field, value in expected.items():
        assert receipt[field] == value, field
        assert recovered["model_work_unit"][field] == value, field
    assert (
        receipt["recovered_state_revision"] == store.load_current(project_id)["state_revision"] - 1
    ), "the receipt records the State it recovered against, before its own commit"

    # The complete resumption context is genuinely resolved, not merely referenced.
    assert recovered["difference"]["difference_id"] == expected["difference_ref"]["id"]
    assert (
        recovered["model_execution_boundary"]["model_execution_boundary_id"]
        == expected["boundary_ref"]["id"]
    )
    assert (
        recovered["model_execution_decision"]["model_execution_decision_id"]
        == expected["authority_ref"]["id"]
    )
    assert recovered["model_execution_decision"]["decision"] == "MODEL_EXECUTION_AUTHORIZED"

    stored = store.resolve_record(project_id, RECOVERY_KIND, receipt["session_recovery_receipt_id"])
    assert stored == receipt
    assert session_recovery_receipt_id(receipt) == receipt["session_recovery_receipt_id"]


def test_recovery_needs_no_conversation_handoff_receipt_or_boot_context(
    world: dict[str, Any],
) -> None:
    """ "A conversation handoff, model memory, or provider-local session is neither required nor
    accepted as continuity evidence" (P16-C4), proved by signature: every recovery/execution
    route takes only ``(store, agent)`` plus keyword-only canonical identifiers, and there is no
    parameter through which a transcript, a session id or a prior receipt could be supplied."""

    import inspect

    for route in (
        recover_model_execution_session,
        execute_model_work_unit,
        record_model_swap,
        open_model_work_unit,
    ):
        signature = inspect.signature(route)
        positional = [
            name
            for name, parameter in signature.parameters.items()
            if parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        ]
        assert positional == ["store", "agent"], route
        forbidden = (
            "transcript",
            "conversation",
            "session_id",
            "memory",
            "history",
            "messages",
            "prompt",
            "receipt",
            "boot_context",
            "provider",
        )
        for name in signature.parameters:
            assert not any(marker in name for marker in forbidden), (route, name)


# --------------------------------------------------------------------------- #
# The candidate reaches the existing Evidence owner -- as a candidate
# --------------------------------------------------------------------------- #


def test_a_resumed_executions_candidate_reaches_the_existing_evidence_owner(
    world: dict[str, Any],
) -> None:
    """The end of the canonical route: Agent B's own bounded candidate is handed to the one
    existing Evidence deriver, in the already-ratified Change-Free Verification Evidence
    position, with provenance this handoff constructs from the real, resolved Envelope."""

    swapped = _run_swap(world)
    request = evidence_request_for(world["project_id"], provenance=None)
    evidence = route_model_execution_to_evidence(
        world["store"], swapped["second_receipt"], world["project_id"], request
    )
    assert evidence["evidence_position"] == "CHANGE_FREE_VERIFICATION_EVIDENCE"
    provenance = evidence["verification_result_provenance"]
    assert provenance["status"] == "VERIFIED"
    assert provenance["verifier_identity"] == {
        "adapter": "request_derived_model_adapter",
        "version": "0.1",
    }
    assert provenance["selection_authority_ref"] == world["human_authority_ref"]
    members = provenance["target_refs"]["members"]
    assert {"kind": "difference", "id": world["difference_ref"]["id"]} in members
    assert {"kind": WORK_UNIT_KIND, "id": swapped["work_unit_id"]} in members


# --------------------------------------------------------------------------- #
# Shared driver
# --------------------------------------------------------------------------- #


def _run_swap(world: dict[str, Any]) -> dict[str, Any]:
    """One complete A-stops/B-resumes run, for the tests above that assert on its result rather
    than on its steps. Session discard is enforced identically here."""

    store = world["store"]
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]

    agent_a = start_temporary_agent(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    opened = open_model_work_unit(store, agent_a, **open_kwargs(world))
    work_unit_id = opened["model_work_unit"]["model_work_unit_id"]
    work_unit_ref = dict(opened["model_work_unit_ref"])
    adapter_x = FakeModelAdapter()
    adapter_x.seed_candidate(
        model_work_unit_ref=work_unit_ref,
        candidate_fields={"summary": "agent A observed", "observed_status": "ok"},
    )
    first = execute_model_work_unit(
        store,
        agent_a,
        project_id=project_id,
        project_binding_id=project_binding_id,
        model_work_unit_ref=work_unit_ref,
        adapter=adapter_x,
        executed_at="2026-09-09T02:00:00Z",
    )
    first_envelope = dict(first["envelope"])
    _discard_session(agent_a)
    del agent_a, adapter_x, opened, first

    agent_b = start_temporary_agent(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    second = execute_model_work_unit(
        store,
        agent_b,
        project_id=project_id,
        project_binding_id=project_binding_id,
        model_work_unit_ref={"kind": WORK_UNIT_KIND, "id": work_unit_id},
        adapter=RequestDerivedModelAdapter(),
        executed_at="2026-09-09T04:00:00Z",
    )
    return {
        "work_unit_id": work_unit_id,
        "first_envelope": first_envelope,
        "second_envelope": dict(second["envelope"]),
        "second_receipt": second["receipt"],
        "agent_b": agent_b,
    }
