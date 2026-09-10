"""V2 (Issue #66): the controlled Model Adapter contract.

Two genuinely distinct adapters, the **identical** canonical request, normalized
provider-neutral outcomes in the identical shape, and no provider-specific canonical
dependency anywhere.

The two adapters are structurally different in the one way that matters for this proof: one
holds a seeded world (a test declares what a model would have produced), the other holds no
world at all and derives every candidate field purely from the canonical request it was handed.
They share no base class, no helper function, no module-level state, and no notion of where a
candidate comes from -- so "both satisfy the contract" is a statement about the contract rather
than about one implementation being reused twice.

The negative half of V2 -- "no provider-specific canonical dependency" -- is additionally
proved by AST/JSON scan rather than only by example, in
``tests/contract/model_runtime/test_model_runtime_static_conformance.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from manosube_agent_civilization.model_runtime.adapter import (
    FakeModelAdapter,
    RequestDerivedModelAdapter,
)
from manosube_agent_civilization.model_runtime.types import (
    MODEL_ADAPTER_OUTCOMES,
    MODEL_ADAPTER_RESULT_KEYS,
    MODEL_EXECUTION_OUTCOMES,
    ModelAdapter,
)

pytestmark = pytest.mark.contract

WORK_UNIT_REF = {"kind": "model_work_unit", "id": "MODEL-WORK-UNIT-" + "E" * 64}
BOUNDARY = {
    "schema_version": "0.1",
    "project_id": "PRJ-MODEL-0001",
    "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-" + "A" * 64},
    "permitted_capability": "PROPOSE_EVIDENCE_CANDIDATE",
    "permitted_candidate_kinds": ["OBSERVATION_CANDIDATE"],
    "permitted_candidate_fields": ["summary", "observed_status"],
    "declared_by": {"kind": "human_authority", "id": "AUTH-0001"},
    "declared_at": "2026-09-08T00:00:00Z",
    "model_execution_boundary_id": "MODEL-EXECUTION-BOUNDARY-" + "D" * 64,
    "model_execution_boundary_semantic_fingerprint": "sha256:" + "d" * 64,
}


def canonical_request() -> dict[str, Any]:
    """One canonical, provider-neutral request in exactly the shape
    :func:`~manosube_agent_civilization.model_runtime.route._canonical_request` builds.

    Written out here rather than obtained from a live route call on purpose: V2 is about what
    an *adapter* is handed and what it must return, and constructing the request explicitly is
    what lets both adapters be handed a byte-identical one.
    """

    return {
        "model_execution_request_identity": "MODEL-EXECUTION-REQUEST-" + "F" * 64,
        "project_id": "PRJ-MODEL-0001",
        "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-" + "A" * 64},
        "state_revision": 4,
        "semantic_fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "a" * 64},
        "model_work_unit_ref": dict(WORK_UNIT_REF),
        "difference_ref": {"kind": "difference", "id": "D-" + "B" * 64},
        "required_capability": "PROPOSE_EVIDENCE_CANDIDATE",
        "authority_ref": {"kind": "model_execution_decision", "id": "MODEL-EXEC-DEC-" + "C" * 64},
        "authority_decision": "MODEL_EXECUTION_AUTHORIZED",
        "boundary_ref": {
            "kind": "model_execution_boundary",
            "id": "MODEL-EXECUTION-BOUNDARY-" + "D" * 64,
        },
        "boundary": dict(BOUNDARY),
        "evidence_requirements": {
            "evidence_position": "CHANGE_FREE_VERIFICATION_EVIDENCE",
            "required_request_keys": ["recorded_at", "schema_version"],
            "required_provenance_fields": ["observations", "status"],
        },
        "execution_contract": {
            "project_id": "PRJ-MODEL-0001",
            "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-" + "A" * 64},
            "state_revision": 4,
            "semantic_fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "a" * 64},
            "human_authority_ref": {"kind": "human_authority", "id": "AUTH-0001"},
        },
    }


def both_adapters() -> tuple[FakeModelAdapter, RequestDerivedModelAdapter]:
    seeded = FakeModelAdapter()
    seeded.seed_candidate(
        model_work_unit_ref=WORK_UNIT_REF,
        candidate_fields={"summary": "seeded summary", "observed_status": "ok"},
    )
    return seeded, RequestDerivedModelAdapter()


# --------------------------------------------------------------------------- #
# Both adapters satisfy the one Protocol
# --------------------------------------------------------------------------- #


def test_both_shipped_adapters_satisfy_the_one_model_adapter_protocol() -> None:
    """``ModelAdapter`` is the single replaceable boundary. Both shipped implementations are
    checked against it structurally rather than by inheritance -- neither subclasses anything,
    which is the point: a replacement adapter written elsewhere satisfies this contract by shape
    alone.

    The Protocol is deliberately **not** ``@runtime_checkable`` (the identical choice
    :class:`~manosube_agent_civilization.runtime.types.RuntimeAdapter` already makes): an
    ``isinstance`` check against a runtime-checkable Protocol proves only that attribute *names*
    exist, which is weaker than what is asserted here and weaker than what the type checker
    already proves statically. The two annotated bindings below are what mypy verifies against
    the real Protocol under ``strict``; the assertions are the runtime half."""

    adapters: tuple[ModelAdapter, ModelAdapter] = both_adapters()
    for adapter in adapters:
        assert isinstance(adapter.adapter_identity, dict)
        assert set(adapter.adapter_identity) == {"adapter", "version"}
        assert callable(adapter.execute)


def test_the_two_adapters_declare_genuinely_different_identities() -> None:
    """The whole model-swap proof rests on two adapters being distinguishable. If both shipped
    adapters declared the same identity, V3's own swap receipt could never be minted at all."""

    seeded, derived = both_adapters()
    assert seeded.adapter_identity != derived.adapter_identity


def test_the_two_adapters_share_no_implementation_at_all() -> None:
    """ "Two distinct adapters" (P16-C2) is proved as a fact about the classes, not asserted in
    prose: neither is a subclass of the other, neither shares a base beyond ``object``, and
    they have no method implementation in common."""

    assert not issubclass(FakeModelAdapter, RequestDerivedModelAdapter)
    assert not issubclass(RequestDerivedModelAdapter, FakeModelAdapter)
    assert FakeModelAdapter.__mro__[1:] == (object,)
    assert RequestDerivedModelAdapter.__mro__[1:] == (object,)
    # Compared by qualified name rather than by identity: mypy correctly reports an ``is not``
    # between two differently-typed bound methods as a non-overlapping identity check, and the
    # fact being pinned is that the two are distinct implementations, not that two distinct
    # objects exist.
    assert FakeModelAdapter.execute.__qualname__ != RequestDerivedModelAdapter.execute.__qualname__
    assert FakeModelAdapter.execute.__code__ is not RequestDerivedModelAdapter.execute.__code__


# --------------------------------------------------------------------------- #
# The identical canonical request produces normalized results in the identical shape
# --------------------------------------------------------------------------- #


def test_both_adapters_execute_the_identical_canonical_request() -> None:
    """P16-C2's own literal requirement: at least two controlled adapters must execute the same
    canonical request. The request object handed to each is the same value, compared for
    equality after both calls so that neither adapter can have mutated it."""

    request = canonical_request()
    before = canonical_request()
    seeded, derived = both_adapters()
    seeded.execute(request=request)
    derived.execute(request=request)
    assert request == before


def test_both_adapters_return_normalized_results_in_the_identical_shape() -> None:
    """Provider-neutral normalization: both results carry exactly the three closed result keys,
    the same value types, the same candidate kind, and candidate fields drawn from exactly the
    Boundary's own ``permitted_candidate_fields``. Only the *values* differ, which is what
    "two different models" means."""

    request = canonical_request()
    results = [adapter.execute(request=request) for adapter in both_adapters()]
    shapes = []
    for result in results:
        assert set(result) == set(MODEL_ADAPTER_RESULT_KEYS)
        assert result["adapter_outcome"] in MODEL_ADAPTER_OUTCOMES
        assert result["adapter_outcome"] == "CANDIDATE"
        assert result["candidate_kind"] in BOUNDARY["permitted_candidate_kinds"]
        assert isinstance(result["candidate_fields"], dict)
        assert set(result["candidate_fields"]) <= set(BOUNDARY["permitted_candidate_fields"])
        assert all(isinstance(value, str) for value in result["candidate_fields"].values())
        shapes.append(
            (
                sorted(result),
                result["adapter_outcome"],
                result["candidate_kind"],
                sorted(result["candidate_fields"]),
            )
        )
    assert shapes[0] == shapes[1]
    assert results[0]["candidate_fields"] != results[1]["candidate_fields"]


def test_each_adapter_is_deterministic_over_the_identical_request() -> None:
    """A replaceable boundary that answered differently on identical input would make every
    identity in this delivery unreproducible."""

    request = canonical_request()
    for adapter in both_adapters():
        assert adapter.execute(request=request) == adapter.execute(request=request)


def test_no_adapter_result_carries_a_provider_specific_field() -> None:
    """ "No provider-specific canonical dependency" at the value level: the closed result key
    set is exactly three keys, none of which names a provider, a model, a prompt, a transcript,
    or a session."""

    request = canonical_request()
    forbidden = (
        "provider",
        "model",
        "prompt",
        "transcript",
        "messages",
        "session",
        "conversation",
        "memory",
        "token",
        "usage",
    )
    for adapter in both_adapters():
        result = adapter.execute(request=request)
        for key in result:
            assert not any(marker in key.lower() for marker in forbidden), key


# --------------------------------------------------------------------------- #
# The accepting classification is not in the adapter's vocabulary at all (P16-C3)
# --------------------------------------------------------------------------- #


def test_the_accepting_classification_is_absent_from_the_adapter_vocabulary() -> None:
    """The decisive structural control behind "model output is never authoritative": there is
    no token an adapter can return that means "accepted". ``CANDIDATE_ACCEPTED`` exists only in
    the route's own outcome vocabulary, and ``CANDIDATE`` exists only in the adapter's."""

    assert "CANDIDATE_ACCEPTED" in MODEL_EXECUTION_OUTCOMES
    assert "CANDIDATE_ACCEPTED" not in MODEL_ADAPTER_OUTCOMES
    assert "CANDIDATE" in MODEL_ADAPTER_OUTCOMES
    assert "CANDIDATE" not in MODEL_EXECUTION_OUTCOMES


def test_the_two_outcome_vocabularies_differ_by_exactly_that_one_member() -> None:
    """Everything else is shared, deliberately: the six typed failures (P16-C6) are reported by
    an adapter and recorded canonically under the identical names, so none of them can be lost
    or renamed in translation."""

    assert MODEL_ADAPTER_OUTCOMES - {"CANDIDATE"} == MODEL_EXECUTION_OUTCOMES - {
        "CANDIDATE_ACCEPTED"
    }
    assert len(MODEL_ADAPTER_OUTCOMES) == len(MODEL_EXECUTION_OUTCOMES) == 7


@pytest.mark.parametrize("outcome", sorted(MODEL_ADAPTER_OUTCOMES - {"CANDIDATE"}))
def test_every_typed_failure_is_reportable_by_a_controlled_adapter(outcome: str) -> None:
    """P16-C6: adapter unavailability, refusal, malformed output, timeout, cancellation and
    incomplete evidence are *return values*, never exceptions -- so each of the six is
    genuinely reachable through the controlled adapter without raising."""

    adapter = FakeModelAdapter()
    adapter.seed_candidate(
        model_work_unit_ref=WORK_UNIT_REF,
        candidate_fields={"summary": "s"},
        adapter_outcome=outcome,
    )
    result = adapter.execute(request=canonical_request())
    assert result["adapter_outcome"] == outcome
    assert result["candidate_fields"] is None
    assert result["candidate_kind"] is None


def test_an_unseeded_fake_adapter_reports_incomplete_evidence_rather_than_a_bare_success() -> None:
    """A model that has nothing to report is not a success and is not an authoritative absence
    -- it is ``INCOMPLETE_EVIDENCE``, which maps to ``INSUFFICIENT`` and to nothing else."""

    adapter = FakeModelAdapter()
    result = adapter.execute(request=canonical_request())
    assert result["adapter_outcome"] == "INCOMPLETE_EVIDENCE"


def test_the_second_adapter_refuses_an_unimplemented_capability_rather_than_raising() -> None:
    """The second adapter's own typed refusal path, so the V4 matrix is not proved through one
    implementation alone. Its implemented-capability set is a class-level literal with no
    constructor parameter -- an adapter that could be *told* which capabilities it implements
    could be told to implement one its Boundary never permitted."""

    request = canonical_request()
    request["required_capability"] = "SOME_CAPABILITY_THIS_ADAPTER_DOES_NOT_IMPLEMENT"
    result = RequestDerivedModelAdapter().execute(request=request)
    assert result["adapter_outcome"] == "REFUSED"
    assert result["candidate_fields"] is None


def test_the_second_adapters_capability_set_is_not_settable_from_outside() -> None:
    import inspect

    signature = inspect.signature(RequestDerivedModelAdapter.__init__)
    assert set(signature.parameters) == {"self", "adapter_identity"}
    assert "IMPLEMENTED_CAPABILITIES" in vars(RequestDerivedModelAdapter)


# --------------------------------------------------------------------------- #
# The adapter never sees a provider payload, a transcript, or a session id
# --------------------------------------------------------------------------- #


def test_the_adapter_protocol_admits_exactly_one_canonical_request_argument() -> None:
    """P16-C1: provider-specific payloads, chat transcripts, hidden model memory and provider
    session ids are not canonical inputs. Proved as a fact about the signature rather than as
    prose -- ``execute`` takes exactly one keyword-only ``request`` argument, with no
    ``*args``/``**kwargs`` through which anything else could arrive, on the Protocol and on
    both implementations alike."""

    import inspect

    for function in (
        ModelAdapter.execute,
        FakeModelAdapter.execute,
        RequestDerivedModelAdapter.execute,
    ):
        signature = inspect.signature(function)
        parameters = [name for name in signature.parameters if name != "self"]
        assert parameters == ["request"], function
        assert signature.parameters["request"].kind is inspect.Parameter.KEYWORD_ONLY, function
        assert not any(
            parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            for parameter in signature.parameters.values()
        ), function


def test_the_canonical_request_carries_no_provider_specific_key() -> None:
    """The request itself is provider-neutral by construction: every key names State, the Work
    Unit, the Difference, the capability, the Authority, the Boundary, the Evidence
    requirements, or the Phase 12 execution contract -- and nothing else."""

    keys = set(canonical_request())
    assert keys == {
        "model_execution_request_identity",
        "project_id",
        "project_binding_ref",
        "state_revision",
        "semantic_fingerprint",
        "model_work_unit_ref",
        "difference_ref",
        "required_capability",
        "authority_ref",
        "authority_decision",
        "boundary_ref",
        "boundary",
        "evidence_requirements",
        "execution_contract",
    }
