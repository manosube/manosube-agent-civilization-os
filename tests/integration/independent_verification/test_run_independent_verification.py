"""Phase 13 (Issue #51) Independent Verification: the one public route
(``run_independent_verification``), end-to-end, over a real ``FileStateStore``.

Proves the canonical successful route (``VERIFICATION_CONTRACT.md`` §5), the required
rejection proofs (§6), and that no rejection or successful call ever mutates canonical
Store visibility -- the verifier is the only call this route ever makes past its own
admission gate, and it is called exactly once on the successful route and exactly zero
times on every rejection.

Structural Review Round 1 (P13-R1-F1/F2/F3): the fixture below binds a real Project
Binding (through the existing Phase 9 Binding owner) so ``boot_project`` -- the real
Authority-owner surface this route now re-verifies ``selection_authority_ref`` through --
succeeds, and commits one real, Store-resolvable ``observation_evidence`` record directly
through the Store's own public ``commit`` (the identical low-level surface Reflow's own
route calls), rather than the pre-Binding ``tests.natural_cycle`` fixture world this file
used before Round 1 (which never binds a Project and therefore cannot boot).
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.product_binding import PROJECT_ID, bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.boot.errors import BootNotFoundError
from manosube_agent_civilization.independent_verification import (
    VerificationRequirement,
    VerificationRequirementError,
    VerificationResult,
    VerificationValueError,
    VerifierOutputError,
    VerifierSelection,
    run_independent_verification,
)
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

_DEFAULT_VERIFIER_IDENTITY = {"kind": "deterministic_test_runner", "id": "VERIFIER-0001"}


def _snapshot(store_root: Path, project_id: str) -> dict[str, str]:
    project_dir = store_root / "projects" / project_id
    if not project_dir.is_dir():
        return {}
    return {
        str(path.relative_to(project_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(project_dir.rglob("*"))
        if path.is_file()
    }


def _bound(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    store_root = tmp_path / "backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store_root, kwargs, result


def _advance(
    store: FileStateStore, project_id: str, genesis_state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a real second State transition -- the identical shape
    ``tests/integration/agent_runtime/test_temporary_agent_lifecycle.py::_advance`` already
    builds for its own equivalent proof."""

    successor = deepcopy(genesis_state)
    successor["state_revision"] = genesis_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = genesis_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {
        "kind": "state_transition",
        "id": "TX-INDEPENDENT-VERIFICATION-0001",
    }
    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": "TX-INDEPENDENT-VERIFICATION-0001",
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": genesis_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": genesis_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-09-06T10:00:00Z",
    }
    return successor, event


@pytest.fixture(scope="module")
def _real_route(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """A real bound Project (Phase 9 Binding), with one real, Store-committed
    ``observation_evidence`` record, and the real Human Authority reference Boot
    independently re-verifies for it -- everything Round 1's corrected route needs to
    admit a genuine, authorized selection."""

    tmp_path = tmp_path_factory.mktemp("independent-verification-bound-project")
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    project_binding_id = result["project_binding_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)

    genesis_state = result["committed_state"]
    evidence_id = "EVID-INDEPENDENT-VERIFICATION-TEST-0001"
    successor, event = _advance(store, project_id, genesis_state)
    store.commit(
        project_id,
        genesis_state["state_revision"],
        genesis_state["semantic_fingerprint"],
        successor,
        event,
        records=[
            (
                "observation_evidence",
                evidence_id,
                {"kind": "observation_evidence", "note": "Phase 13 test fixture record"},
            )
        ],
    )

    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)

    return {
        "store": store,
        "project_id": project_id,
        "project_binding_id": project_binding_id,
        "evidence_id": evidence_id,
        "difference_id": "D-INDEPENDENT-VERIFICATION-TEST-0001",
        "human_authority_ref": dict(boot_context.human_authority_ref),
    }


def _requirement(
    evidence_id: str, difference_id: str, human_authority_ref: dict[str, Any], **overrides: Any
) -> VerificationRequirement:
    fields: dict[str, Any] = {
        "requirement_id": "VREQ-0001",
        "project_id": PROJECT_ID,
        "target_refs": [
            {"kind": "observation_evidence", "id": evidence_id},
            {"kind": "difference", "id": difference_id},
        ],
        "verification_boundary": {"scope": "repository", "boundary_id": "VB-0001"},
        "required_conditions": {"minimum_distinctness": "DISTINCT_LINEAGE"},
        "selection_authority_ref": dict(human_authority_ref),
    }
    fields.update(overrides)
    return VerificationRequirement(**fields)


def _selection(human_authority_ref: dict[str, Any], **overrides: Any) -> VerifierSelection:
    fields: dict[str, Any] = {
        "selection_id": "VSEL-0001",
        "project_id": PROJECT_ID,
        "requirement_id": "VREQ-0001",
        "status": "ACTIVE",
        "selection_authority_ref": dict(human_authority_ref),
        "verifier_identity": dict(_DEFAULT_VERIFIER_IDENTITY),
        "permitted_boundary": {"scope": "repository", "boundary_id": "VB-0001"},
    }
    fields.update(overrides)
    return VerifierSelection(**fields)


def _identified(func: Any, identity: dict[str, Any] | None = None) -> Any:
    """Attach the ``verifier_identity`` attribute Round 1's route now requires (P13-R1-F1)
    before invocation -- a plain function is a real Python object and may carry one."""

    func.verifier_identity = dict(identity if identity is not None else _DEFAULT_VERIFIER_IDENTITY)
    return func


def _counting_verifier(
    payload: dict[str, Any], identity: dict[str, Any] | None = None
) -> tuple[list[int], Any]:
    calls: list[int] = []

    def verifier(*, requirement: VerificationRequirement, selection: VerifierSelection) -> Any:
        calls.append(1)
        return payload

    return calls, _identified(verifier, identity)


def _run(
    fx: dict[str, Any],
    requirement: VerificationRequirement,
    selection: VerifierSelection,
    verifier: Any,
    *,
    project_id: str | None = None,
) -> VerificationResult:
    return run_independent_verification(
        fx["store"],
        project_id=project_id if project_id is not None else fx["project_id"],
        project_binding_id=fx["project_binding_id"],
        verification_requirement=requirement,
        verifier_selection=selection,
        verifier=verifier,
    )


# --- the canonical successful route --------------------------------------------------- #


def test_successful_route_returns_a_verified_result_with_zero_store_mutation(
    _real_route: dict[str, Any],
) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-INDEPENDENT-0001"}],
            "observations": {"summary": "independently reproduced the reported outcome"},
        }
    )

    result = _run(_real_route, requirement, selection, verifier)

    assert isinstance(result, VerificationResult)
    assert result.status == "VERIFIED"
    assert result.requirement_id == "VREQ-0001"
    assert result.selection_id == "VSEL-0001"
    assert result.project_id == project_id
    assert dict(result.target_refs[0]) == {
        "kind": "observation_evidence",
        "id": _real_route["evidence_id"],
    }
    assert dict(result.verifier_identity) == _DEFAULT_VERIFIER_IDENTITY
    assert dict(result.selection_authority_ref) == _real_route["human_authority_ref"]
    assert dict(result.verification_boundary) == {"scope": "repository", "boundary_id": "VB-0001"}
    assert dict(result.input_refs[0]) == {"kind": "source_snapshot", "id": "SS-INDEPENDENT-0001"}
    assert dict(result.observations) == {"summary": "independently reproduced the reported outcome"}
    assert calls == [1]
    assert _snapshot(store.root, project_id) == before


def test_result_fields_are_immutable(_real_route: dict[str, Any]) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    _, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-INDEPENDENT-0001"}],
            "observations": {},
        }
    )
    result = _run(_real_route, requirement, selection, verifier)
    with pytest.raises(AttributeError):
        result.status = "FAILED"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.target_refs[0]["kind"] = "tampered"  # type: ignore[index]


def test_requirement_and_selection_fields_are_immutable(_real_route: dict[str, Any]) -> None:
    requirement = _requirement("EVIDENCE-1", "D-1", _real_route["human_authority_ref"])
    with pytest.raises(AttributeError):
        requirement.project_id = "OTHER"  # type: ignore[misc]
    with pytest.raises(TypeError):
        requirement.verification_boundary["scope"] = "tampered"  # type: ignore[index]

    selection = _selection(_real_route["human_authority_ref"])
    with pytest.raises(AttributeError):
        selection.status = "REVOKED"  # type: ignore[misc]
    with pytest.raises(TypeError):
        selection.verifier_identity["kind"] = "tampered"  # type: ignore[index]


def test_deep_freeze_rejects_a_set_and_other_unsupported_mutable_values(
    _real_route: dict[str, Any],
) -> None:
    """Structural Review Round 1 (P13-R1-F3): a ``set`` (or any other value that is
    neither a Mapping, Sequence, nor JSON-compatible scalar) must never be silently
    accepted as though it were frozen."""

    with pytest.raises(VerificationValueError):
        _requirement(
            _real_route["evidence_id"],
            _real_route["difference_id"],
            _real_route["human_authority_ref"],
            required_conditions={"tags": {"a", "b"}},
        )
    with pytest.raises(VerificationValueError):
        _selection(_real_route["human_authority_ref"], verifier_identity={"nested": object()})


# --- required rejection proofs: requirement/selection/boundary/target admission ------- #


def test_wrong_requested_project_id_is_rejected(_real_route: dict[str, Any]) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        _run(_real_route, requirement, selection, verifier, project_id="OTHER-PROJECT")
    assert calls == []


@pytest.mark.parametrize(
    "mutate_requirement,mutate_selection,expected_message_fragment",
    [
        (lambda req: replace(req, project_id="OTHER"), lambda sel: sel, "project_id"),
        (lambda req: req, lambda sel: replace(sel, project_id="OTHER"), "project_id"),
        (lambda req: req, lambda sel: replace(sel, requirement_id="OTHER-REQ"), "does not apply"),
        (lambda req: req, lambda sel: replace(sel, status="REVOKED"), "not ACTIVE"),
        (lambda req: req, lambda sel: replace(sel, status="EXPIRED"), "not ACTIVE"),
        (lambda req: req, lambda sel: replace(sel, status="BOGUS"), "not a recognized"),
        (
            lambda req: req,
            lambda sel: replace(
                sel, selection_authority_ref={"kind": "human_authority", "id": "OTHER"}
            ),
            "Human Authority",
        ),
        (
            lambda req: req,
            lambda sel: replace(sel, permitted_boundary={"scope": "different"}),
            "permitted_boundary",
        ),
    ],
)
def test_requirement_selection_mismatches_are_rejected_before_the_verifier_runs(
    _real_route: dict[str, Any],
    mutate_requirement: Any,
    mutate_selection: Any,
    expected_message_fragment: str,
) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = mutate_requirement(
        _requirement(
            _real_route["evidence_id"],
            _real_route["difference_id"],
            _real_route["human_authority_ref"],
        )
    )
    selection = mutate_selection(_selection(_real_route["human_authority_ref"]))
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match=expected_message_fragment):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_a_fabricated_but_self_consistent_authority_ref_is_rejected(
    _real_route: dict[str, Any],
) -> None:
    """Structural Review Round 1 (P13-R1-F2): both ``selection_authority_ref`` values
    agreeing with *each other* is not authorization -- they must agree with the real,
    Boot-verified Human Authority reference. Two caller-fabricated, mutually-equal but
    fake references must still be refused, and the verifier must never be called."""

    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    fake_ref = {"kind": "human_authority", "id": "FABRICATED-BY-CALLER"}
    requirement = _requirement(
        _real_route["evidence_id"],
        _real_route["difference_id"],
        _real_route["human_authority_ref"],
        selection_authority_ref=dict(fake_ref),
    )
    selection = _selection(
        _real_route["human_authority_ref"], selection_authority_ref=dict(fake_ref)
    )
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match="Human Authority"):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_an_empty_authority_ref_agreed_by_both_callers_is_rejected(
    _real_route: dict[str, Any],
) -> None:
    """The exact malformed case Codex's real review named: ``selection_authority_ref={}``
    on both sides must still be refused -- equality between two malformed values is not
    Authority."""

    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"],
        _real_route["difference_id"],
        _real_route["human_authority_ref"],
        selection_authority_ref={},
    )
    selection = _selection(_real_route["human_authority_ref"], selection_authority_ref={})
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []
    assert _snapshot(store.root, project_id) == before


@pytest.mark.parametrize(
    "target_refs",
    [
        [],
        [{"kind": "observation_evidence"}],
        [{"id": "EVID-0001"}],
        [{"kind": "authority_decision", "id": "AUTH-1"}],
        [{"kind": "state", "id": "S-1"}],
    ],
)
def test_malformed_or_out_of_vocabulary_target_refs_are_rejected(
    _real_route: dict[str, Any], target_refs: list[dict[str, Any]]
) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"],
        _real_route["difference_id"],
        _real_route["human_authority_ref"],
        target_refs=target_refs,
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_unresolvable_evidence_target_is_rejected_and_never_reaches_the_verifier(
    _real_route: dict[str, Any],
) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        "EVIDENCE-DOES-NOT-EXIST",
        _real_route["difference_id"],
        _real_route["human_authority_ref"],
        target_refs=[{"kind": "observation_evidence", "id": "EVIDENCE-DOES-NOT-EXIST"}],
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match="does not resolve"):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_a_difference_or_change_target_is_never_resolved_against_the_store(
    _real_route: dict[str, Any],
) -> None:
    """Difference and Change are never Store-owned record kinds in this vertical -- a
    fabricated ``difference``/``change`` id must not be rejected by Store resolution (only
    an ``observation_evidence`` target is ever resolved here)."""

    requirement = _requirement(
        _real_route["evidence_id"],
        _real_route["difference_id"],
        _real_route["human_authority_ref"],
        target_refs=[
            {"kind": "difference", "id": "D-DOES-NOT-EXIST"},
            {"kind": "change", "id": "CHG-DOES-NOT-EXIST"},
        ],
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-1"}],
            "observations": {},
        }
    )

    result = _run(_real_route, requirement, selection, verifier)
    assert calls == [1]
    assert result.status == "VERIFIED"


# --- required rejection proofs: verifier identity binding (P13-R1-F1) ----------------- #


def test_a_callable_whose_declared_identity_mismatches_the_selection_is_never_invoked(
    _real_route: dict[str, Any],
) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}},
        identity={"kind": "deterministic_test_runner", "id": "A-DIFFERENT-VERIFIER"},
    )

    with pytest.raises(VerificationRequirementError):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_a_callable_with_no_declared_identity_is_never_invoked(
    _real_route: dict[str, Any],
) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls: list[int] = []

    def bare_verifier(*, requirement: VerificationRequirement, selection: VerifierSelection) -> Any:
        calls.append(1)
        return {"status": "VERIFIED", "input_refs": [], "observations": {}}

    with pytest.raises(VerificationRequirementError, match="verifier_identity"):
        _run(_real_route, requirement, selection, bare_verifier)
    assert calls == []


def test_a_callable_with_an_unreadable_declared_identity_is_never_invoked(
    _real_route: dict[str, Any],
) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )
    verifier.verifier_identity = "not-a-mapping"

    with pytest.raises(VerificationRequirementError, match="verifier_identity"):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []


def test_only_the_correctly_identified_verifier_is_invoked_and_attributed(
    _real_route: dict[str, Any],
) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-1"}],
            "observations": {},
        }
    )

    result = _run(_real_route, requirement, selection, verifier)
    assert calls == [1]
    assert dict(result.verifier_identity) == _DEFAULT_VERIFIER_IDENTITY


# --- required rejection proofs: the verifier's own output shape ---------------------- #


@pytest.mark.parametrize(
    "payload",
    [
        "not-a-mapping",
        {"status": "MAYBE", "input_refs": [], "observations": {}},
        {"status": "VERIFIED", "input_refs": "not-a-list", "observations": {}},
        {"status": "VERIFIED", "input_refs": [{"kind": "source_snapshot"}], "observations": {}},
        {"status": "VERIFIED", "input_refs": [{"id": "SS-1"}], "observations": {}},
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-1"}],
            "observations": "not-a-mapping",
        },
    ],
)
def test_malformed_verifier_output_is_rejected(_real_route: dict[str, Any], payload: Any) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    _, verifier = _counting_verifier(payload)

    with pytest.raises(VerifierOutputError):
        _run(_real_route, requirement, selection, verifier)
    assert _snapshot(store.root, project_id) == before


def test_verifier_citing_no_input_at_all_is_rejected_unless_unavailable(
    _real_route: dict[str, Any],
) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    _, empty_input_verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerifierOutputError, match="no input_refs"):
        _run(_real_route, requirement, selection, empty_input_verifier)


def test_verifier_citing_only_the_target_refs_is_rejected_as_indistinguishable_provenance(
    _real_route: dict[str, Any],
) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])

    def echo_verifier(*, requirement: VerificationRequirement, selection: VerifierSelection) -> Any:
        return {
            "status": "VERIFIED",
            "input_refs": [dict(ref) for ref in requirement.target_refs],
            "observations": {},
        }

    _identified(echo_verifier)

    with pytest.raises(VerifierOutputError, match="implementation-indistinguishable"):
        _run(_real_route, requirement, selection, echo_verifier)


@pytest.mark.parametrize("status", ["FAILED", "INSUFFICIENT"])
def test_a_non_unavailable_negative_result_still_requires_distinguishable_input(
    _real_route: dict[str, Any], status: str
) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    _, verifier = _counting_verifier({"status": status, "input_refs": [], "observations": {}})

    with pytest.raises(VerifierOutputError):
        _run(_real_route, requirement, selection, verifier)


def test_unavailable_status_is_exempt_from_the_independence_check(
    _real_route: dict[str, Any],
) -> None:
    """Disclosed interpretation (VERIFICATION_CONTRACT.md §9): UNAVAILABLE asserts the
    verifier could not evaluate at all, so it is not required to cite distinguishable
    input -- unlike VERIFIED/FAILED/INSUFFICIENT, which are all real evaluations."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    _, unavailable_verifier = _counting_verifier(
        {"status": "UNAVAILABLE", "input_refs": [], "observations": {"reason": "offline"}}
    )

    result = _run(_real_route, requirement, selection, unavailable_verifier)
    assert result.status == "UNAVAILABLE"
    assert result.input_refs == ()


@pytest.mark.parametrize("status", ["FAILED", "INSUFFICIENT", "UNAVAILABLE"])
def test_every_real_negative_outcome_is_representable_with_distinguishable_input(
    _real_route: dict[str, Any], status: str
) -> None:
    """The failure statuses are ordinary results this route returns unmodified -- it never
    substitutes a status, and a negative outcome with genuine independent input is accepted
    exactly as a VERIFIED one is."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    _, verifier = _counting_verifier(
        {
            "status": status,
            "input_refs": [{"kind": "source_snapshot", "id": "SS-INDEPENDENT-0002"}],
            "observations": {"reason_code": "OBSERVED_MISMATCH"},
        }
    )

    result = _run(_real_route, requirement, selection, verifier)
    assert result.status == status


# --- construction-time input type checks ----------------------------------------------- #


def test_non_instance_requirement_or_selection_is_rejected(_real_route: dict[str, Any]) -> None:
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        run_independent_verification(
            _real_route["store"],
            project_id=_real_route["project_id"],
            project_binding_id=_real_route["project_binding_id"],
            verification_requirement={"not": "a requirement instance"},  # type: ignore[arg-type]
            verifier_selection=selection,
            verifier=verifier,
        )
    assert calls == []


def test_non_canonical_project_id_is_rejected(_real_route: dict[str, Any]) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        _run(_real_route, requirement, selection, verifier, project_id="../escape")
    assert calls == []


def test_boot_project_failure_propagates_unchanged_and_never_calls_the_verifier(
    _real_route: dict[str, Any],
) -> None:
    """A wrong ``project_binding_id`` makes ``boot_project`` itself fail closed -- that
    failure propagates unchanged (frozen semantic decision 6/9), and the verifier is never
    reached."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(BootNotFoundError):
        run_independent_verification(
            _real_route["store"],
            project_id=_real_route["project_id"],
            project_binding_id="PB-DOES-NOT-EXIST",
            verification_requirement=requirement,
            verifier_selection=selection,
            verifier=verifier,
        )
    assert calls == []
