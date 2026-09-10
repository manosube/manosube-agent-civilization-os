"""V4 (Issue #66): the complete failure / tamper / provenance proof matrix.

Every scenario the adopted text names, over a real ``FileStateStore``:

```text
stale State                       ..... section 1
substituted references            ..... section 2  (work unit / Difference / Authority / Boundary)
cross-project / cross-Store       ..... section 3
malformed adapter output          ..... section 4
unavailable / timeout / cancelled ..... section 5  (with the other three typed outcomes too)
attempted model self-authorization ..... section 6
```

**Where each check runs, and why the distinction matters.** Every test's own docstring opens by
naming which of these four it proves, exactly as the Phase 15 suite's own docstrings do:

```text
ZERO-CALL   the check runs BEFORE the adapter exists, so `execute_call_count == 0` and the
            project's own State revision is unchanged. Nothing was executed and nothing
            committed.
TYPED       the check runs AFTER the adapter has honestly reported something, so the result is
            one of the six typed non-accepting outcomes, committed as itself -- never promoted
            to CANDIDATE_ACCEPTED and never recorded as an authoritative absence.
DEFECT      the adapter's own return value is structurally unreadable, claims a classification
            only the route may compute, or exceeds its own Boundary. That is an adapter defect,
            not an outcome: it raises `ModelAdapterError`, and nothing is committed at all.
INERT       nothing is refused at all -- the execution genuinely succeeds -- and the point is
            what the adapter's own extra claims did NOT do. Used for the model
            self-authorization control, where a refusal would be the *weaker* result: the keys
            those claims arrive under are never read by anyone, so there is nothing to refuse.
```
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.evidence_helpers import change_free_verification_evidence_request
from tests.fixtures.model_runtime_world import (
    SECOND_PROJECT_ID,
    authorized_world,
    bind_into,
    boundary_for,
    commit_boundary,
    commit_difference,
    commit_grant,
    decision_for,
    foreign_signing_key,
    foreign_signing_private_key,
    open_kwargs,
    plant_records,
    touch_state,
    work_unit_body,
)

from manosube_agent_civilization.agent_runtime import TemporaryAgent, start_temporary_agent
from manosube_agent_civilization.boot import BootContext
from manosube_agent_civilization.model_runtime import (
    FakeModelAdapter,
    ModelAdapterError,
    ModelRecordIntegrityError,
    ModelReleasedAgentError,
    ModelRuntimeAuthorityFreshnessError,
    ModelRuntimeRequirementError,
    ModelRuntimeStaleStateError,
    RequestDerivedModelAdapter,
    execute_model_work_unit,
    open_model_work_unit,
    record_model_swap,
    recover_model_execution_session,
    route_model_execution_to_evidence,
)
from manosube_agent_civilization.model_runtime.identity import model_execution_envelope_id
from manosube_agent_civilization.model_runtime.types import (
    MODEL_ADAPTER_OUTCOMES,
    MODEL_OUTCOME_TO_RECEIPT_STATUS,
)
from manosube_agent_civilization.store.errors import RecordConflictError

pytestmark = pytest.mark.integration

WORK_UNIT_KIND = "model_work_unit"
ENVELOPE_KIND = "model_execution_envelope"
DECISION_KIND = "model_execution_decision"
BOUNDARY_KIND = "model_execution_boundary"


def _rebind(value: Any, old: str, new: str) -> Any:
    if isinstance(value, dict):
        return {key: _rebind(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [_rebind(item, old, new) for item in value]
    return new if value == old else value


@pytest.fixture
def world(tmp_path: Path) -> dict[str, Any]:
    return authorized_world(tmp_path)


def _agent(world: dict[str, Any]) -> TemporaryAgent:
    return start_temporary_agent(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
    )


def _revision(world: dict[str, Any]) -> int:
    return int(world["store"].load_current(world["project_id"])["state_revision"])


def _open(world: dict[str, Any], agent: TemporaryAgent | None = None, **overrides: Any) -> Any:
    kwargs = open_kwargs(world)
    kwargs.update(overrides)
    return open_model_work_unit(world["store"], agent or _agent(world), **kwargs)


def _seeded_adapter(work_unit_ref: dict[str, Any], **seed: Any) -> FakeModelAdapter:
    adapter = FakeModelAdapter()
    adapter.seed_candidate(
        model_work_unit_ref=work_unit_ref,
        candidate_fields={"summary": "s", "observed_status": "ok"},
        **seed,
    )
    return adapter


def _execute(
    world: dict[str, Any],
    work_unit_ref: dict[str, Any],
    adapter: Any,
    *,
    agent: TemporaryAgent | None = None,
    executed_at: str = "2026-09-09T02:00:00Z",
    project_id: str | None = None,
) -> Any:
    return execute_model_work_unit(
        world["store"],
        agent or _agent(world),
        project_id=project_id or world["project_id"],
        project_binding_id=world["project_binding_id"],
        model_work_unit_ref=work_unit_ref,
        adapter=adapter,
        executed_at=executed_at,
    )


class _DoctoredAgent(TemporaryAgent):
    """A live Temporary Agent holding a deliberately doctored Boot Context.

    ``TemporaryAgent`` is a public ``abc.ABC``, so anything in this process can implement it --
    which is exactly the threat the route's own freshness gates exist for, and exactly why this
    control implements it rather than monkeypatching around it. This is not a claim that Phase 12
    is cryptographically sandboxed (its own docstring already disclaims that); it is the honest
    construction of an Agent whose held contract does not match the Store.
    """

    def __init__(self, boot_context: BootContext) -> None:
        self._boot_context = boot_context

    @property
    def boot_context(self) -> BootContext:
        return self._boot_context

    def release(self) -> None:  # pragma: no cover - nothing to release
        return None


def _doctored(world: dict[str, Any], **state_overrides: Any) -> _DoctoredAgent:
    genuine = _agent(world).boot_context
    current_state = dict(genuine.current_state)
    current_state.update(state_overrides)
    return _DoctoredAgent(
        BootContext(
            project_id=genuine.project_id,
            project_binding=dict(genuine.project_binding),
            project_binding_id=genuine.project_binding_id,
            objective_revision=dict(genuine.objective_revision),
            objective_revision_id=genuine.objective_revision_id,
            authority_rule=dict(genuine.authority_rule),
            authority_rule_id=genuine.authority_rule_id,
            current_state=current_state,
            human_authority_ref=dict(genuine.human_authority_ref),
        )
    )


# =========================================================================== #
# 1. Stale State
# =========================================================================== #


def test_opening_under_a_contract_that_is_no_longer_current_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL. A Work Unit binds the exact State snapshot it was opened against, so genesis
    requires a fully current execution contract. Booting an Agent, then letting an unrelated
    commit land, then opening under that Agent refuses -- and no Work Unit exists afterwards."""

    agent = _agent(world)
    touch_state(world["store"], world["project_id"])
    before = _revision(world)
    with pytest.raises(ModelRuntimeStaleStateError):
        _open(world, agent)
    assert _revision(world) == before


def test_executing_under_a_contract_older_than_the_work_unit_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL. This is the definition of "stale" that execution actually uses: an Agent whose
    own contract predates the revision the Work Unit was opened against is operating on a view of
    the world in which this Work Unit does not exist. The adapter is never constructed with a
    seeded world here because it is never called at all."""

    stale_agent = _agent(world)
    touch_state(world["store"], world["project_id"])
    opened = _open(world)
    adapter = _seeded_adapter(opened["model_work_unit_ref"])
    before = _revision(world)
    with pytest.raises(ModelRuntimeStaleStateError):
        _execute(world, opened["model_work_unit_ref"], adapter, agent=stale_agent)
    assert adapter.execute_call_count == 0
    assert _revision(world) == before


def test_a_contract_claiming_a_revision_this_store_never_reached_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL. A contract from the future is not a view of this Store at all."""

    opened = _open(world)
    adapter = _seeded_adapter(opened["model_work_unit_ref"])
    impossible = _doctored(world, state_revision=_revision(world) + 500)
    before = _revision(world)
    with pytest.raises(ModelRuntimeStaleStateError):
        _execute(world, opened["model_work_unit_ref"], adapter, agent=impossible)
    assert adapter.execute_call_count == 0
    assert _revision(world) == before


def test_a_contract_from_a_different_world_at_the_same_revision_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL. The substituted-Store control: a contract claiming this Store's own current
    revision must carry this Store's own current semantic fingerprint. An internally
    self-consistent contract established against a *different* Store at the same revision number
    is refused here, before anything it names is even resolved."""

    opened = _open(world)
    adapter = _seeded_adapter(opened["model_work_unit_ref"])
    genuine = world["store"].load_current(world["project_id"])
    other_world = _doctored(
        world,
        semantic_fingerprint={
            "profile": genuine["semantic_fingerprint"]["profile"],
            "digest": "f" * 64,
        },
    )
    before = _revision(world)
    with pytest.raises(ModelRuntimeStaleStateError):
        _execute(world, opened["model_work_unit_ref"], adapter, agent=other_world)
    assert adapter.execute_call_count == 0
    assert _revision(world) == before


def test_a_work_unit_claiming_a_state_revision_this_store_never_reached_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL. The wrong-State-revision *material* control (P16-C5): a fully self-consistent,
    genuinely re-computable Work Unit is planted directly into the Store claiming it was opened
    against revision 9999. It recomputes perfectly; it is still refused, because no such State
    ever existed here."""

    genuine = _open(world)["model_work_unit"]
    planted = work_unit_body(
        world["project_id"],
        world["project_binding_id"],
        opened_state_revision=9999,
        opened_semantic_fingerprint=genuine["opened_semantic_fingerprint"],
        difference_ref=genuine["difference_ref"],
        authority_ref=genuine["authority_ref"],
        boundary_ref=genuine["boundary_ref"],
    )
    plant_records(
        world["store"],
        world["project_id"],
        [(WORK_UNIT_KIND, planted["model_work_unit_id"], planted)],
    )
    reference = {"kind": WORK_UNIT_KIND, "id": planted["model_work_unit_id"]}
    adapter = _seeded_adapter(reference)
    before = _revision(world)
    with pytest.raises(ModelRuntimeStaleStateError):
        _execute(world, reference, adapter)
    assert adapter.execute_call_count == 0
    assert _revision(world) == before


def test_an_unrelated_commit_between_open_and_execute_does_not_block_a_fresh_agent(
    world: dict[str, Any],
) -> None:
    """The control for every test above. Staleness must refuse a stale *contract*, never
    resumption itself -- a Work Unit that became unusable the moment any unrelated commit landed
    would be the opposite of what P16-C4 asks to prove."""

    opened = _open(world)
    touch_state(world["store"], world["project_id"], transaction_id="TX-MODEL-UNRELATED-0002")
    adapter = _seeded_adapter(opened["model_work_unit_ref"])
    result = _execute(world, opened["model_work_unit_ref"], adapter)
    assert result["envelope"]["execution_outcome"] == "CANDIDATE_ACCEPTED"


# =========================================================================== #
# 1b. The Phase 12 execution contract itself
# =========================================================================== #


def test_a_released_temporary_agent_cannot_execute(world: dict[str, Any]) -> None:
    """ZERO-CALL. Phase 12's own frozen semantic decision 6: a released handle cannot be
    restarted or resumed. Phase 12's own error is chained, never swallowed."""

    opened = _open(world)
    agent = _agent(world)
    agent.release()
    adapter = _seeded_adapter(opened["model_work_unit_ref"])
    before = _revision(world)
    with pytest.raises(ModelReleasedAgentError):
        _execute(world, opened["model_work_unit_ref"], adapter, agent=agent)
    assert adapter.execute_call_count == 0
    assert _revision(world) == before


def test_an_object_that_is_not_a_temporary_agent_cannot_execute(world: dict[str, Any]) -> None:
    """ZERO-CALL. There is no second execution contract: an object that merely *looks* like one
    is refused by type, so nothing can stand in for Phase 12's own handle."""

    opened = _open(world)

    class _NotAnAgent:
        boot_context = None

    adapter = _seeded_adapter(opened["model_work_unit_ref"])
    with pytest.raises(ModelRuntimeRequirementError):
        execute_model_work_unit(
            world["store"],
            _NotAnAgent(),  # type: ignore[arg-type]
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            model_work_unit_ref=opened["model_work_unit_ref"],
            adapter=adapter,
            executed_at="2026-09-09T02:00:00Z",
        )
    assert adapter.execute_call_count == 0


def test_an_agent_naming_a_different_project_cannot_execute(
    tmp_path: Path, world: dict[str, Any]
) -> None:
    """ZERO-CALL. The Agent's own contract must name the exact project and Binding being asked
    for -- an Agent Booted for another project is refused before anything is resolved."""

    opened = _open(world)
    second = bind_into(world["store"], project_id=SECOND_PROJECT_ID)
    foreign_agent = start_temporary_agent(
        world["store"],
        project_id=second["project_id"],
        project_binding_id=second["project_binding_id"],
    )
    adapter = _seeded_adapter(opened["model_work_unit_ref"])
    with pytest.raises(ModelRuntimeRequirementError):
        _execute(world, opened["model_work_unit_ref"], adapter, agent=foreign_agent)
    assert adapter.execute_call_count == 0


# =========================================================================== #
# 2. Substituted references
# =========================================================================== #


def test_a_work_unit_reference_that_resolves_to_nothing_refuses(world: dict[str, Any]) -> None:
    """ZERO-CALL. A reference with no canonical record behind it is a caller string."""

    adapter = FakeModelAdapter()
    with pytest.raises(ModelRuntimeRequirementError):
        _execute(world, {"kind": WORK_UNIT_KIND, "id": "MODEL-WORK-UNIT-" + "0" * 64}, adapter)
    assert adapter.execute_call_count == 0


def test_a_work_unit_naming_a_difference_that_resolves_to_nothing_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL. The substituted-Difference control. The planted Work Unit is fully
    self-consistent -- it recomputes both of its own digests perfectly -- and is still refused,
    because the Difference it points at was never committed."""

    genuine = _open(world)["model_work_unit"]
    planted = work_unit_body(
        world["project_id"],
        world["project_binding_id"],
        opened_state_revision=genuine["opened_state_revision"],
        opened_semantic_fingerprint=genuine["opened_semantic_fingerprint"],
        difference_ref={"kind": "difference", "id": "D-" + "0" * 64},
        authority_ref=genuine["authority_ref"],
        boundary_ref=genuine["boundary_ref"],
    )
    plant_records(
        world["store"],
        world["project_id"],
        [(WORK_UNIT_KIND, planted["model_work_unit_id"], planted)],
    )
    reference = {"kind": WORK_UNIT_KIND, "id": planted["model_work_unit_id"]}
    adapter = _seeded_adapter(reference)
    with pytest.raises(ModelRuntimeRequirementError):
        _execute(world, reference, adapter)
    assert adapter.execute_call_count == 0


def test_a_work_unit_naming_a_real_but_different_difference_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL. The wrong-Difference control, and deliberately the *hard* version: the
    Difference the planted Work Unit names is genuinely committed and genuinely valid -- it is
    simply not the one this Work Unit's own Authority Decision was made about."""

    genuine = _open(world)["model_work_unit"]
    other_ref, _other = commit_difference(
        world["store"],
        world["project_id"],
        fact_value="A-DIFFERENT-FACT",
        transaction_id="TX-MODEL-DIFFERENCE-0002",
    )
    assert other_ref["id"] != genuine["difference_ref"]["id"]
    planted = work_unit_body(
        world["project_id"],
        world["project_binding_id"],
        opened_state_revision=genuine["opened_state_revision"],
        opened_semantic_fingerprint=genuine["opened_semantic_fingerprint"],
        difference_ref=other_ref,
        authority_ref=genuine["authority_ref"],
        boundary_ref=genuine["boundary_ref"],
    )
    plant_records(
        world["store"],
        world["project_id"],
        [(WORK_UNIT_KIND, planted["model_work_unit_id"], planted)],
    )
    reference = {"kind": WORK_UNIT_KIND, "id": planted["model_work_unit_id"]}
    adapter = _seeded_adapter(reference)
    with pytest.raises(ModelRuntimeRequirementError):
        _execute(world, reference, adapter)
    assert adapter.execute_call_count == 0


def test_a_work_unit_naming_a_real_but_different_boundary_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL. The substituted-Boundary control. The Boundary named is genuinely committed,
    genuinely Human-declared, genuinely identity-consistent and permits the identical capability
    -- but the Work Unit's own Authority Decision does not name it, so it authorizes nothing
    here. A model cannot be given a wider Boundary by pointing at a different one."""

    genuine = _open(world)["model_work_unit"]
    wider_ref, _wider = commit_boundary(
        world["store"],
        world["project_id"],
        world["project_binding_id"],
        transaction_id="TX-MODEL-BOUNDARY-0002",
        permitted_candidate_fields=("summary", "observed_status", "anything_else"),
    )
    assert wider_ref["id"] != genuine["boundary_ref"]["id"]
    planted = work_unit_body(
        world["project_id"],
        world["project_binding_id"],
        opened_state_revision=genuine["opened_state_revision"],
        opened_semantic_fingerprint=genuine["opened_semantic_fingerprint"],
        difference_ref=genuine["difference_ref"],
        authority_ref=genuine["authority_ref"],
        boundary_ref=wider_ref,
    )
    plant_records(
        world["store"],
        world["project_id"],
        [(WORK_UNIT_KIND, planted["model_work_unit_id"], planted)],
    )
    reference = {"kind": WORK_UNIT_KIND, "id": planted["model_work_unit_id"]}
    adapter = _seeded_adapter(reference)
    with pytest.raises(ModelRuntimeRequirementError):
        _execute(world, reference, adapter)
    assert adapter.execute_call_count == 0


def test_a_work_unit_naming_an_authority_decision_that_resolves_to_nothing_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL. The substituted-Authority control: a Work Unit whose ``authority_ref`` names
    nothing committed carries no Authority at all, however self-consistent it is."""

    genuine = _open(world)["model_work_unit"]
    planted = work_unit_body(
        world["project_id"],
        world["project_binding_id"],
        opened_state_revision=genuine["opened_state_revision"],
        opened_semantic_fingerprint=genuine["opened_semantic_fingerprint"],
        difference_ref=genuine["difference_ref"],
        authority_ref={"kind": DECISION_KIND, "id": "MODEL-EXEC-DEC-" + "0" * 64},
        boundary_ref=genuine["boundary_ref"],
    )
    plant_records(
        world["store"],
        world["project_id"],
        [(WORK_UNIT_KIND, planted["model_work_unit_id"], planted)],
    )
    reference = {"kind": WORK_UNIT_KIND, "id": planted["model_work_unit_id"]}
    adapter = _seeded_adapter(reference)
    with pytest.raises(ModelRuntimeRequirementError):
        _execute(world, reference, adapter)
    assert adapter.execute_call_count == 0


def test_a_work_unit_naming_a_genuine_but_refusing_authority_decision_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL. A genuinely minted, genuinely committed Authority Decision that actually says
    MODEL_EXECUTION_REFUSED authorizes nothing -- so a Work Unit pointing at one is refused even
    though every reference resolves and every identity recomputes."""

    genuine = _open(world)["model_work_unit"]
    refusing = decision_for(
        world["project_id"], world["difference_ref"], world["boundary_ref"], grants=[]
    )
    assert refusing["decision"] == "MODEL_EXECUTION_REFUSED"
    planted = work_unit_body(
        world["project_id"],
        world["project_binding_id"],
        opened_state_revision=genuine["opened_state_revision"],
        opened_semantic_fingerprint=genuine["opened_semantic_fingerprint"],
        difference_ref=genuine["difference_ref"],
        authority_ref={"kind": DECISION_KIND, "id": refusing["model_execution_decision_id"]},
        boundary_ref=genuine["boundary_ref"],
    )
    plant_records(
        world["store"],
        world["project_id"],
        [
            (DECISION_KIND, refusing["model_execution_decision_id"], refusing),
            (WORK_UNIT_KIND, planted["model_work_unit_id"], planted),
        ],
    )
    reference = {"kind": WORK_UNIT_KIND, "id": planted["model_work_unit_id"]}
    adapter = _seeded_adapter(reference)
    with pytest.raises(ModelRuntimeRequirementError):
        _execute(world, reference, adapter)
    assert adapter.execute_call_count == 0


def test_a_work_unit_body_that_does_not_reproduce_its_own_declared_identity_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL. The tamper control, and the two independent layers it proves.

    The first layer is the Store's own: a record's address is a pure content address, and the
    Store refuses to hold two different bodies at one address -- so editing an
    already-committed Work Unit *in place* is not a move an attacker with Store write access
    has at all, and this test asserts that directly.

    What such an attacker can still do is plant an edited body under a *fresh* key while
    keeping the declared identity fields of the record it was copied from. That is the second
    layer, and it is this package's own: the route recomputes the resolved body's identity and
    refuses on the mismatch, with a distinct integrity error, before any adapter exists.
    """

    genuine = _open(world)["model_work_unit"]
    tampered = dict(genuine)
    tampered["opened_at"] = "2026-12-31T23:59:59Z"
    fresh_key = "MODEL-WORK-UNIT-" + "7" * 64
    plant_records(
        world["store"],
        world["project_id"],
        [(WORK_UNIT_KIND, fresh_key, tampered)],
        transaction_id="TX-MODEL-TAMPERED-WORK-UNIT",
    )
    adapter = FakeModelAdapter()
    with pytest.raises(ModelRecordIntegrityError):
        _execute(world, {"kind": WORK_UNIT_KIND, "id": fresh_key}, adapter)
    assert adapter.execute_call_count == 0


def test_a_committed_work_unit_cannot_be_edited_in_place_at_all(
    world: dict[str, Any],
) -> None:
    """The first of the two layers above, asserted on its own -- and deliberately as its own
    test, because a refused commit leaves the Store's own transaction pending, so nothing may
    follow it in the same test.

    A Work Unit's address is a pure content address over its complete body, so an edited body
    has a different address and the Store refuses to hold it at the original one. Editing an
    already-committed Work Unit in place is not a move an attacker with Store write access has.
    """

    genuine = _open(world)["model_work_unit"]
    tampered = dict(genuine)
    tampered["opened_at"] = "2026-12-31T23:59:59Z"
    with pytest.raises(RecordConflictError):
        plant_records(
            world["store"],
            world["project_id"],
            [(WORK_UNIT_KIND, genuine["model_work_unit_id"], tampered)],
            transaction_id="TX-MODEL-TAMPERED-IN-PLACE",
        )


def test_a_reference_of_the_wrong_kind_refuses(world: dict[str, Any]) -> None:
    """ZERO-CALL. Every reference this package accepts is kind-pinned: a genuine Boundary id
    presented as a Work Unit reference is refused on shape, before any resolution."""

    adapter = FakeModelAdapter()
    with pytest.raises(ModelRuntimeRequirementError):
        _execute(world, dict(world["boundary_ref"]), adapter)
    assert adapter.execute_call_count == 0


# =========================================================================== #
# 2b. Authority at open time
# =========================================================================== #


def test_opening_with_no_grant_at_all_refuses(world: dict[str, Any]) -> None:
    """ZERO-CALL, and no Work Unit exists afterwards."""

    before = _revision(world)
    with pytest.raises(ModelRuntimeRequirementError):
        _open(world, model_execution_grant_refs=[])
    assert _revision(world) == before


def test_opening_with_a_revoked_grant_refuses(world: dict[str, Any]) -> None:
    """ZERO-CALL. A grant that binds on every field but is not ACTIVE withholds authorization
    exactly as an excluding Approval withholds a Change."""

    revoked_ref, _revoked = commit_grant(
        world["store"],
        world["project_id"],
        world["difference_ref"],
        world["boundary_ref"],
        transaction_id="TX-MODEL-GRANT-REVOKED",
        status="REVOKED",
    )
    before = _revision(world)
    with pytest.raises(ModelRuntimeRequirementError):
        _open(world, model_execution_grant_refs=[revoked_ref])
    assert _revision(world) == before


def test_opening_with_a_grant_signed_by_the_wrong_key_refuses(world: dict[str, Any]) -> None:
    """ZERO-CALL. A grant inserted directly into the Store, self-consistent and correctly
    ``granted_by``-shaped, authorizes nothing without a genuine signature by the exact
    ``human_authority_signing_key`` this call's own Boot restored.

    The forged grant declares a different ``granted_at`` than the world's genuine one, and that
    is not incidental: ``granted_at`` participates in the grant's own adopted semantic fields, so
    a forged grant that differed from a genuine one *only* in its signature would share the
    genuine one's exact content address -- and the Store would refuse to hold both, which is a
    control in its own right rather than a gap. Varying the declared instant gives the forgery
    its own address, so this test reaches the signature check rather than stopping at the Store.
    """

    forged_ref, _forged = commit_grant(
        world["store"],
        world["project_id"],
        world["difference_ref"],
        world["boundary_ref"],
        transaction_id="TX-MODEL-GRANT-FORGED",
        granted_at="2026-09-08T02:00:00Z",
        signer=foreign_signing_private_key(),
    )
    assert forged_ref["id"] != world["grant_ref"]["id"]
    before = _revision(world)
    with pytest.raises(ModelRuntimeRequirementError):
        _open(world, model_execution_grant_refs=[forged_ref])
    assert _revision(world) == before


def test_a_forged_signature_cannot_even_be_planted_beside_a_genuine_grant(
    world: dict[str, Any],
) -> None:
    """The Store-level half of the control above, asserted on its own: re-signing a genuine
    grant with an attacker's key produces a body with the *identical* content address, and the
    Store refuses to hold two different bodies at one address. So the forged body cannot be
    substituted for the genuine one at all."""

    from tests.fixtures.model_runtime_world import grant_for

    forged = grant_for(
        world["project_id"],
        world["difference_ref"],
        world["boundary_ref"],
        signer=foreign_signing_private_key(),
    )
    assert forged["model_execution_grant_id"] == world["grant_ref"]["id"]
    assert forged["signature"] != world["grant"]["signature"]
    with pytest.raises(RecordConflictError):
        plant_records(
            world["store"],
            world["project_id"],
            [("model_execution_grant", forged["model_execution_grant_id"], forged)],
            transaction_id="TX-MODEL-GRANT-SUBSTITUTION",
        )


def test_opening_with_a_grant_for_a_different_difference_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL. A genuine, ACTIVE, correctly signed grant for one Difference never authorizes
    a different one."""

    other_ref, _other = commit_difference(
        world["store"],
        world["project_id"],
        fact_value="A-DIFFERENT-FACT",
        transaction_id="TX-MODEL-DIFFERENCE-0003",
    )
    elsewhere_ref, _elsewhere = commit_grant(
        world["store"],
        world["project_id"],
        other_ref,
        world["boundary_ref"],
        transaction_id="TX-MODEL-GRANT-ELSEWHERE",
    )
    before = _revision(world)
    with pytest.raises(ModelRuntimeRequirementError):
        _open(world, model_execution_grant_refs=[elsewhere_ref])
    assert _revision(world) == before


def test_opening_against_a_boundary_declared_by_another_human_authority_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL, and a *distinct* typed refusal: a Boundary declared under a Human Authority
    other than the one this call's own fresh Boot restored is never carried forward silently."""

    foreign_ref, _foreign = commit_boundary(
        world["store"],
        world["project_id"],
        world["project_binding_id"],
        transaction_id="TX-MODEL-BOUNDARY-FOREIGN",
        declared_by={"kind": "human_authority", "id": "AUTH-SOMEONE-ELSE"},
    )
    before = _revision(world)
    with pytest.raises(ModelRuntimeAuthorityFreshnessError):
        _open(world, boundary_ref=foreign_ref)
    assert _revision(world) == before


def test_a_work_unit_whose_authority_decision_names_another_human_authority_refuses(
    world: dict[str, Any],
) -> None:
    """ZERO-CALL, and a distinct typed refusal. This is the decisive Authority-freshness control:
    the planted Decision is genuinely minted by the shipped evaluator and genuinely AUTHORIZED --
    by an entirely different Human Authority, holding its own genuinely different signing key,
    over its own genuinely signed grant. Everything about it is internally legitimate; it is
    still refused, because it is not this Project Binding's own Authority."""

    genuine = _open(world)["model_work_unit"]
    other_authority = {"kind": "human_authority", "id": "AUTH-SOMEONE-ELSE"}
    foreign_boundary = boundary_for(
        world["project_id"],
        world["project_binding_id"],
        declared_by=other_authority,
    )
    foreign_boundary_ref = {
        "kind": BOUNDARY_KIND,
        "id": foreign_boundary["model_execution_boundary_id"],
    }
    from tests.fixtures.model_runtime_world import grant_for

    foreign_grant = grant_for(
        world["project_id"],
        world["difference_ref"],
        foreign_boundary_ref,
        granted_by=other_authority,
        signer=foreign_signing_private_key(),
    )
    authorized_elsewhere = decision_for(
        world["project_id"],
        world["difference_ref"],
        foreign_boundary_ref,
        grants=[foreign_grant],
        human_authority_ref=other_authority,
        human_authority_signing_key_value=foreign_signing_key(),
    )
    assert authorized_elsewhere["decision"] == "MODEL_EXECUTION_AUTHORIZED"
    planted = work_unit_body(
        world["project_id"],
        world["project_binding_id"],
        opened_state_revision=genuine["opened_state_revision"],
        opened_semantic_fingerprint=genuine["opened_semantic_fingerprint"],
        difference_ref=world["difference_ref"],
        authority_ref={
            "kind": DECISION_KIND,
            "id": authorized_elsewhere["model_execution_decision_id"],
        },
        boundary_ref=foreign_boundary_ref,
    )
    plant_records(
        world["store"],
        world["project_id"],
        [
            (
                BOUNDARY_KIND,
                foreign_boundary["model_execution_boundary_id"],
                foreign_boundary,
            ),
            (
                DECISION_KIND,
                authorized_elsewhere["model_execution_decision_id"],
                authorized_elsewhere,
            ),
            (WORK_UNIT_KIND, planted["model_work_unit_id"], planted),
        ],
        transaction_id="TX-MODEL-FOREIGN-AUTHORITY",
    )
    reference = {"kind": WORK_UNIT_KIND, "id": planted["model_work_unit_id"]}
    adapter = _seeded_adapter(reference)
    with pytest.raises(ModelRuntimeAuthorityFreshnessError):
        _execute(world, reference, adapter)
    assert adapter.execute_call_count == 0


# =========================================================================== #
# 3. Cross-project / cross-Store material
# =========================================================================== #


def test_a_work_unit_from_a_wholly_different_store_refuses(tmp_path: Path) -> None:
    """ZERO-CALL. Two genuinely separate Stores, each internally complete and internally valid.
    A Work Unit genuinely opened in the second is presented to the first: it does not resolve
    there, so it authorizes nothing, however genuine it is where it came from."""

    first = authorized_world(tmp_path, subdir="store-a")
    second = authorized_world(tmp_path, subdir="store-b")
    foreign = _open(second)
    adapter = _seeded_adapter(foreign["model_work_unit_ref"])
    before = _revision(first)
    with pytest.raises(ModelRuntimeRequirementError):
        _execute(first, foreign["model_work_unit_ref"], adapter)
    assert adapter.execute_call_count == 0
    assert _revision(first) == before


def test_a_work_unit_belonging_to_a_different_project_in_the_same_store_refuses(
    tmp_path: Path,
) -> None:
    """ZERO-CALL. The cross-*project* control, in one Store: two genuinely bound projects, and a
    Work Unit genuinely opened under the second presented as the first project's own."""

    world = authorized_world(tmp_path)
    second = bind_into(world["store"], project_id=SECOND_PROJECT_ID)
    difference_ref, _difference = commit_difference(world["store"], second["project_id"])
    boundary_ref, _boundary = commit_boundary(
        world["store"], second["project_id"], second["project_binding_id"]
    )
    grant_ref, _grant = commit_grant(
        world["store"], second["project_id"], difference_ref, boundary_ref
    )
    second_world = {
        "store": world["store"],
        "project_id": second["project_id"],
        "project_binding_id": second["project_binding_id"],
        "difference_ref": difference_ref,
        "boundary_ref": boundary_ref,
        "grant_ref": grant_ref,
    }
    foreign = _open(second_world)
    adapter = _seeded_adapter(foreign["model_work_unit_ref"])
    with pytest.raises(ModelRuntimeRequirementError):
        _execute(world, foreign["model_work_unit_ref"], adapter)
    assert adapter.execute_call_count == 0


def test_a_receipt_cannot_be_relabelled_across_projects_at_evidence_handoff(
    tmp_path: Path,
) -> None:
    """The hand-off's own cross-project control: a receipt genuinely produced for one project
    cannot be presented as Evidence for another, because the Envelope it names does not resolve
    there."""

    first = authorized_world(tmp_path, subdir="store-a")
    second = authorized_world(tmp_path, subdir="store-b")
    opened = _open(second)
    result = _execute(
        second, opened["model_work_unit_ref"], _seeded_adapter(opened["model_work_unit_ref"])
    )
    request = _rebind(
        change_free_verification_evidence_request(provenance=None),
        "PRJ-0001",
        first["project_id"],
    )
    with pytest.raises(ModelRuntimeRequirementError):
        route_model_execution_to_evidence(
            first["store"], result["receipt"], first["project_id"], request
        )


# =========================================================================== #
# 4. Malformed adapter output (DEFECT, never an outcome)
# =========================================================================== #


@pytest.mark.parametrize(
    ("label", "forced"),
    [
        ("not_a_mapping", ["not", "a", "mapping"]),
        (
            "unknown_outcome",
            {"adapter_outcome": "SOMETHING_ELSE", "candidate_kind": None, "candidate_fields": None},
        ),
        (
            "route_only_accepting_outcome",
            {
                "adapter_outcome": "CANDIDATE_ACCEPTED",
                "candidate_kind": "OBSERVATION_CANDIDATE",
                "candidate_fields": {"summary": "s"},
            },
        ),
        (
            "candidate_without_fields",
            {
                "adapter_outcome": "CANDIDATE",
                "candidate_kind": "OBSERVATION_CANDIDATE",
                "candidate_fields": None,
            },
        ),
        (
            "candidate_kind_outside_the_boundary",
            {
                "adapter_outcome": "CANDIDATE",
                "candidate_kind": "CLOSURE_DECLARATION",
                "candidate_fields": {"summary": "s"},
            },
        ),
        (
            "field_outside_the_boundary",
            {
                "adapter_outcome": "CANDIDATE",
                "candidate_kind": "OBSERVATION_CANDIDATE",
                "candidate_fields": {"summary": "s", "exfiltrated_credential": "hunter2"},
            },
        ),
    ],
)
def test_a_structurally_defective_adapter_result_is_refused_and_nothing_is_committed(
    world: dict[str, Any], label: str, forced: Any
) -> None:
    """DEFECT. Each of these is an adapter *defect*, never a typed outcome: an unreadable return
    value, an outcome token outside the adapter vocabulary, the route-only accepting
    classification claimed by the adapter itself, a CANDIDATE with no readable fields, a
    candidate kind the Boundary never permitted, and a field the Boundary never permitted. All
    six raise, and none of them is silently dropped or recorded as any outcome at all -- the
    project's State revision is unchanged afterwards."""

    opened = _open(world)
    adapter = FakeModelAdapter()
    adapter.force_result(forced)
    before = _revision(world)
    with pytest.raises(ModelAdapterError):
        _execute(world, opened["model_work_unit_ref"], adapter)
    assert adapter.execute_call_count == 1
    assert _revision(world) == before


def test_an_adapter_without_a_readable_identity_never_executes(world: dict[str, Any]) -> None:
    """ZERO-CALL. An unstated or unverifiable adapter identity may never execute on this route's
    behalf -- the identity participates in the request identity and in the committed Envelope, so
    an adapter that declares none could not be attributed at all."""

    opened = _open(world)

    class _Anonymous:
        def execute(self, *, request: Any) -> Any:  # pragma: no cover - never reached
            raise AssertionError("an anonymous adapter must never be executed")

    with pytest.raises(ModelAdapterError):
        _execute(world, opened["model_work_unit_ref"], _Anonymous())


# =========================================================================== #
# 5. Every typed outcome, distinct and terminal (P16-C6)
# =========================================================================== #


@pytest.mark.parametrize("outcome", sorted(MODEL_ADAPTER_OUTCOMES - {"CANDIDATE"}))
def test_each_typed_failure_is_committed_as_itself_and_never_as_success(
    world: dict[str, Any], outcome: str
) -> None:
    """TYPED. Unavailability, refusal, malformed output, timeout, cancellation and incomplete
    evidence each survive to the canonical Envelope under their own name, each carry no candidate
    at all, and each map to their own receipt status. None is converted into
    ``CANDIDATE_ACCEPTED``, and none is recorded as an authoritative absence of a result -- the
    Envelope exists and says exactly what happened."""

    opened = _open(world)
    adapter = _seeded_adapter(opened["model_work_unit_ref"], adapter_outcome=outcome)
    result = _execute(world, opened["model_work_unit_ref"], adapter)
    envelope = result["envelope"]
    assert envelope["execution_outcome"] == outcome
    assert envelope["normalized_candidate"] is None
    assert envelope["normalized_candidate_kind"] is None
    assert envelope["normalized_candidate_fingerprint"] is None
    assert result["receipt"].status == MODEL_OUTCOME_TO_RECEIPT_STATUS[outcome]
    assert result["receipt"].status != "VERIFIED"
    resolved = world["store"].resolve_record(
        world["project_id"], ENVELOPE_KIND, envelope["model_execution_envelope_id"]
    )
    assert resolved == envelope


def test_the_six_typed_failures_map_to_four_distinct_statuses_and_never_collapse() -> None:
    """P16-C6's own "none may be converted into another" requirement, at the mapping table
    itself: incomplete evidence maps to INSUFFICIENT and to nothing else, refusal maps to
    FAILED, and the accepting outcome is the only one that maps to VERIFIED."""

    assert MODEL_OUTCOME_TO_RECEIPT_STATUS["INCOMPLETE_EVIDENCE"] == "INSUFFICIENT"
    assert MODEL_OUTCOME_TO_RECEIPT_STATUS["REFUSED"] == "FAILED"
    assert [
        outcome
        for outcome, status in MODEL_OUTCOME_TO_RECEIPT_STATUS.items()
        if status == "VERIFIED"
    ] == ["CANDIDATE_ACCEPTED"]
    assert set(MODEL_OUTCOME_TO_RECEIPT_STATUS.values()) == {
        "VERIFIED",
        "FAILED",
        "UNAVAILABLE",
        "INSUFFICIENT",
    }


def test_a_candidate_that_survives_the_boundary_empty_is_incomplete_not_accepted(
    world: dict[str, Any],
) -> None:
    """TYPED, and the one route-level downgrade this delivery takes. An adapter reporting
    CANDIDATE whose bounded projection retains no permitted field at all has not produced a
    candidate this Boundary can carry: it is recorded as INCOMPLETE_EVIDENCE, never as an
    accepted candidate over an empty object. The direction is the only one taken anywhere -- no
    failure is ever converted into success."""

    opened = _open(world)
    adapter = FakeModelAdapter()
    adapter.force_result(
        {
            "adapter_outcome": "CANDIDATE",
            "candidate_kind": "OBSERVATION_CANDIDATE",
            "candidate_fields": {},
        }
    )
    result = _execute(world, opened["model_work_unit_ref"], adapter)
    assert result["envelope"]["execution_outcome"] == "INCOMPLETE_EVIDENCE"
    assert result["envelope"]["normalized_candidate"] is None
    assert result["receipt"].status == "INSUFFICIENT"


def test_a_typed_failure_still_reaches_the_existing_evidence_owner_honestly(
    world: dict[str, Any],
) -> None:
    """TYPED. A failed execution is not hidden: it hands off to the same Evidence owner with the
    honest status its own outcome maps to, so an unavailable model can never be mistaken for a
    verified one."""

    opened = _open(world)
    adapter = _seeded_adapter(opened["model_work_unit_ref"], adapter_outcome="UNAVAILABLE")
    result = _execute(world, opened["model_work_unit_ref"], adapter)
    request = _rebind(
        change_free_verification_evidence_request(provenance=None),
        "PRJ-0001",
        world["project_id"],
    )
    evidence = route_model_execution_to_evidence(
        world["store"], result["receipt"], world["project_id"], request
    )
    assert evidence["verification_result_provenance"]["status"] == "UNAVAILABLE"
    assert (
        evidence["verification_result_provenance"]["observations"][
            "normalized_candidate_fingerprint"
        ]
        is None
    )


# =========================================================================== #
# 6. Attempted model self-authorization
# =========================================================================== #


def test_an_adapter_claiming_authority_evidence_and_closure_changes_nothing(
    world: dict[str, Any],
) -> None:
    """INERT, and the decisive behavioural half of P16-C3 -- deliberately not a refusal.

    The adapter returns a perfectly valid CANDIDATE *and* attaches every claim it could possibly
    make: a forged Authority reference, a forged decision record, a forged Evidence record, a
    forged accepting provenance, a declaration that the Difference is closed, a wider Boundary,
    an escalated capability, the route-only accepting classification, and a commit instruction.
    The execution then **succeeds**, exactly as it would have without any of them.

    That is a stronger result than a refusal would be. A refusal would mean the route read those
    claims and decided against them, which is a control that can be forgotten, mis-ordered or
    weakened later. Here the route reads exactly three keys, so every one of those claims arrives
    under a key that is never read by anyone, at any point -- proved structurally in
    ``tests/contract/model_runtime/test_model_runtime_static_conformance.py``'s own
    ``test_the_route_reads_exactly_three_keys_out_of_an_adapter_result``.

    What this test asserts, therefore, is absence of effect: the committed Envelope carries the
    real Work Unit's own Authority, Boundary, capability, Difference and Evidence requirements
    and none of the forged keys; the Work Unit itself is byte-identical to what was opened; and
    no Authority, Evidence or Closure record of any kind came into existence."""

    opened = _open(world)
    work_unit = opened["model_work_unit"]
    adapter = FakeModelAdapter()
    adapter.force_result(
        {
            "adapter_outcome": "CANDIDATE",
            "candidate_kind": "OBSERVATION_CANDIDATE",
            "candidate_fields": {"summary": "s", "observed_status": "ok"},
            # Everything below is invisible to the route: no key here is ever read.
            "authority_ref": {"kind": DECISION_KIND, "id": "MODEL-EXEC-DEC-" + "9" * 64},
            "model_execution_decision": {"decision": "MODEL_EXECUTION_AUTHORIZED"},
            "evidence": {"evidence_id": "EVIDENCE-" + "9" * 64, "status": "VERIFIED"},
            "verification_result_provenance": {"status": "VERIFIED"},
            "difference_closed": True,
            "closure_evaluation": {"closed": True},
            "boundary_ref": {"kind": BOUNDARY_KIND, "id": "MODEL-EXECUTION-BOUNDARY-" + "9" * 64},
            "permitted_candidate_fields": ["anything", "at", "all"],
            "required_capability": "DO_ANYTHING",
            "execution_outcome": "CANDIDATE_ACCEPTED",
            "commit": True,
        }
    )
    result = _execute(world, opened["model_work_unit_ref"], adapter)
    envelope = result["envelope"]

    assert envelope["authority_ref"] == work_unit["authority_ref"]
    assert envelope["boundary_ref"] == work_unit["boundary_ref"]
    assert envelope["required_capability"] == work_unit["required_capability"]
    assert envelope["difference_ref"] == work_unit["difference_ref"]
    assert envelope["evidence_requirements"] == work_unit["evidence_requirements"]
    assert set(envelope["normalized_candidate"]) == {"summary", "observed_status"}
    for forged in (
        "evidence",
        "verification_result_provenance",
        "difference_closed",
        "closure_evaluation",
        "commit",
        "model_execution_decision",
        "permitted_candidate_fields",
    ):
        assert forged not in envelope

    store, project_id = world["store"], world["project_id"]
    assert store.resolve_record(project_id, WORK_UNIT_KIND, work_unit["model_work_unit_id"]) == (
        work_unit
    )
    assert store.resolve_record(project_id, DECISION_KIND, "MODEL-EXEC-DEC-" + "9" * 64) is None
    assert store.resolve_record(project_id, "evidence", "EVIDENCE-" + "9" * 64) is None
    assert store.resolve_record(project_id, "observation_evidence", "EVIDENCE-" + "9" * 64) is None


def test_an_adapters_own_output_can_never_supply_the_provenance_that_would_accept_it(
    world: dict[str, Any],
) -> None:
    """P16-C3's "cannot self-accept its own Evidence", at the hand-off. An Evidence request that
    already carries a ``verification_result_provenance`` is refused outright, so the accepting
    provenance is always the one this handoff constructs from the real, resolved Envelope."""

    opened = _open(world)
    result = _execute(
        world, opened["model_work_unit_ref"], _seeded_adapter(opened["model_work_unit_ref"])
    )
    request = _rebind(change_free_verification_evidence_request(), "PRJ-0001", world["project_id"])
    assert request["verification_result_provenance"] is not None
    with pytest.raises(ModelRuntimeRequirementError):
        route_model_execution_to_evidence(
            world["store"], result["receipt"], world["project_id"], request
        )


def test_a_change_bearing_evidence_request_is_refused_at_the_handoff(
    world: dict[str, Any],
) -> None:
    """A model execution never executes or grounds a Change (P16-C3): the hand-off produces the
    Change-free position and refuses anything else."""

    opened = _open(world)
    result = _execute(
        world, opened["model_work_unit_ref"], _seeded_adapter(opened["model_work_unit_ref"])
    )
    request = _rebind(
        change_free_verification_evidence_request(provenance=None),
        "PRJ-0001",
        world["project_id"],
    )
    request["change_request"] = {"anything": "at all"}
    with pytest.raises(ModelRuntimeRequirementError):
        route_model_execution_to_evidence(
            world["store"], result["receipt"], world["project_id"], request
        )


def test_a_forged_receipt_is_refused_against_the_real_committed_envelope(
    world: dict[str, Any],
) -> None:
    """The receipt is a publicly constructible dataclass, so it is never trusted: every one of
    its fields must equal the real, Store-resolved Envelope's own content. A receipt forged in a
    single field -- here, its own claimed adapter identity -- refuses, even with every other
    field genuine."""

    from dataclasses import replace

    opened = _open(world)
    result = _execute(
        world, opened["model_work_unit_ref"], _seeded_adapter(opened["model_work_unit_ref"])
    )
    forged = replace(
        result["receipt"],
        adapter_identity={"adapter": "a_model_that_never_ran", "version": "9.9"},
    )
    request = _rebind(
        change_free_verification_evidence_request(provenance=None),
        "PRJ-0001",
        world["project_id"],
    )
    with pytest.raises(ModelRuntimeRequirementError):
        route_model_execution_to_evidence(world["store"], forged, world["project_id"], request)


def test_an_envelope_edited_after_commitment_refuses_at_the_handoff(
    world: dict[str, Any],
) -> None:
    """The tamper control at the hand-off boundary: the resolved Envelope's own recomputed
    semantic fingerprint must equal its own declared value before any of its fields is trusted.

    The forged Envelope is planted at its own genuinely recomputed content address -- so the
    Store accepts it, exactly as it would accept any new record -- and carries a deliberately
    wrong *declared* semantic fingerprint. Nothing about it is refused by the Store; it is
    refused here, by this package's own re-verification, which is the point."""

    from dataclasses import replace

    opened = _open(world)
    result = _execute(
        world, opened["model_work_unit_ref"], _seeded_adapter(opened["model_work_unit_ref"])
    )
    forged = dict(result["envelope"])
    forged["execution_outcome"] = "REFUSED"
    forged["normalized_candidate"] = None
    forged["normalized_candidate_kind"] = None
    forged["normalized_candidate_fingerprint"] = None
    forged["model_execution_envelope_id"] = model_execution_envelope_id(forged)
    forged["model_execution_semantic_fingerprint"] = "sha256:" + "f" * 64
    plant_records(
        world["store"],
        world["project_id"],
        [(ENVELOPE_KIND, forged["model_execution_envelope_id"], forged)],
        transaction_id="TX-MODEL-TAMPERED-ENVELOPE",
    )
    receipt = replace(
        result["receipt"],
        model_execution_envelope_id=forged["model_execution_envelope_id"],
    )
    request = _rebind(
        change_free_verification_evidence_request(provenance=None),
        "PRJ-0001",
        world["project_id"],
    )
    with pytest.raises(ModelRecordIntegrityError):
        route_model_execution_to_evidence(world["store"], receipt, world["project_id"], request)


# =========================================================================== #
# 7. The swap receipt's own refusals
# =========================================================================== #


def test_a_swap_receipt_is_refused_when_both_envelopes_name_the_same_adapter(
    world: dict[str, Any],
) -> None:
    """A model swap receipt states that a *different* Adapter resumed this Work Unit. Two
    executions by the identical adapter identity are not a swap, and this route never records a
    continuity claim it cannot prove."""

    opened = _open(world)
    reference = opened["model_work_unit_ref"]
    first = _execute(world, reference, _seeded_adapter(reference))
    second = _execute(
        world, reference, _seeded_adapter(reference), executed_at="2026-09-09T03:00:00Z"
    )
    assert (
        first["envelope"]["model_execution_envelope_id"]
        != second["envelope"]["model_execution_envelope_id"]
    )
    before = _revision(world)
    with pytest.raises(ModelRuntimeRequirementError):
        record_model_swap(
            world["store"],
            _agent(world),
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            model_work_unit_ref=reference,
            predecessor_execution_ref={
                "kind": ENVELOPE_KIND,
                "id": first["envelope"]["model_execution_envelope_id"],
            },
            successor_execution_ref={
                "kind": ENVELOPE_KIND,
                "id": second["envelope"]["model_execution_envelope_id"],
            },
            recorded_at="2026-09-09T05:00:00Z",
        )
    assert _revision(world) == before


def test_a_swap_receipt_is_refused_when_the_two_envelopes_are_the_same_one(
    world: dict[str, Any],
) -> None:
    """One execution recorded twice is not a model swap."""

    opened = _open(world)
    reference = opened["model_work_unit_ref"]
    only = _execute(world, reference, _seeded_adapter(reference))
    envelope_ref = {
        "kind": ENVELOPE_KIND,
        "id": only["envelope"]["model_execution_envelope_id"],
    }
    with pytest.raises(ModelRuntimeRequirementError):
        record_model_swap(
            world["store"],
            _agent(world),
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            model_work_unit_ref=reference,
            predecessor_execution_ref=envelope_ref,
            successor_execution_ref=dict(envelope_ref),
            recorded_at="2026-09-09T05:00:00Z",
        )


def test_a_swap_receipt_is_refused_when_an_envelope_belongs_to_a_different_work_unit(
    tmp_path: Path,
) -> None:
    """A continuity claim across two *different* Work Units is not continuity at all."""

    world = authorized_world(tmp_path)
    first_open = _open(world)
    other_difference_ref, _other = commit_difference(
        world["store"],
        world["project_id"],
        fact_value="A-DIFFERENT-FACT",
        transaction_id="TX-MODEL-DIFFERENCE-0004",
    )
    other_grant_ref, _other_grant = commit_grant(
        world["store"],
        world["project_id"],
        other_difference_ref,
        world["boundary_ref"],
        transaction_id="TX-MODEL-GRANT-OTHER",
    )
    second_open = _open(
        world,
        difference_ref=other_difference_ref,
        model_execution_grant_refs=[other_grant_ref],
    )
    first = _execute(
        world, first_open["model_work_unit_ref"], _seeded_adapter(first_open["model_work_unit_ref"])
    )
    second = _execute(
        world,
        second_open["model_work_unit_ref"],
        RequestDerivedModelAdapter(),
        executed_at="2026-09-09T03:00:00Z",
    )
    with pytest.raises(ModelRuntimeRequirementError):
        record_model_swap(
            world["store"],
            _agent(world),
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            model_work_unit_ref=first_open["model_work_unit_ref"],
            predecessor_execution_ref={
                "kind": ENVELOPE_KIND,
                "id": first["envelope"]["model_execution_envelope_id"],
            },
            successor_execution_ref={
                "kind": ENVELOPE_KIND,
                "id": second["envelope"]["model_execution_envelope_id"],
            },
            recorded_at="2026-09-09T05:00:00Z",
        )


def test_recovery_of_a_work_unit_that_does_not_resolve_refuses(world: dict[str, Any]) -> None:
    """P16-C5's own refusal surface: recovery refuses substituted material before any adapter
    could ever be reached, because recovery reaches no adapter at all."""

    before = _revision(world)
    with pytest.raises(ModelRuntimeRequirementError):
        recover_model_execution_session(
            world["store"],
            _agent(world),
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            model_work_unit_ref={"kind": WORK_UNIT_KIND, "id": "MODEL-WORK-UNIT-" + "0" * 64},
            recovered_at="2026-09-09T03:00:00Z",
        )
    assert _revision(world) == before
