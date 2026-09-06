"""Phase 13 (Issue #51) Independent Verification: the one public route
(``run_independent_verification``), end-to-end, over a real ``FileStateStore``.

Proves the canonical successful route (``VERIFICATION_CONTRACT.md`` §5), the required
rejection proofs (§6), and that no rejection or successful call ever mutates canonical
Store visibility -- the verifier is the only call this route ever makes past its own
admission gate, and it is called exactly once on the successful route and exactly zero
times on every rejection.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.vertical_proof import PROJECT_ID
from tests.natural_cycle.proof import run_vertical_proof

from manosube_agent_civilization.independent_verification import (
    VerificationRequirement,
    VerificationRequirementError,
    VerificationResult,
    VerifierOutputError,
    VerifierSelection,
    run_independent_verification,
)
from manosube_agent_civilization.store import FileStateStore


def _snapshot(store_root: Path, project_id: str) -> dict[str, str]:
    project_dir = store_root / "projects" / project_id
    if not project_dir.is_dir():
        return {}
    return {
        str(path.relative_to(project_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(project_dir.rglob("*"))
        if path.is_file()
    }


@pytest.fixture(scope="module")
def _real_route(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Run the full natural cycle exactly once, in a module-scoped temp dir, so every test
    in this file shares one real committed ``observation_evidence`` record and one real
    ``FileStateStore`` -- proving Store resolution against genuine, canonically-produced
    content rather than a hand-built fixture this module would otherwise have to trust."""

    tmp_path = tmp_path_factory.mktemp("independent-verification-natural-cycle")
    result = run_vertical_proof(tmp_path)
    return {
        "store": result["store"],
        "project_id": PROJECT_ID,
        "evidence_id": result["identity_ledger"]["change_result_evidence_id"],
        "difference_id": result["identity_ledger"]["difference_id"],
    }


def _requirement(evidence_id: str, difference_id: str, **overrides: Any) -> VerificationRequirement:
    fields: dict[str, Any] = {
        "requirement_id": "VREQ-0001",
        "project_id": PROJECT_ID,
        "target_refs": [
            {"kind": "observation_evidence", "id": evidence_id},
            {"kind": "difference", "id": difference_id},
        ],
        "verification_boundary": {"scope": "repository", "boundary_id": "VB-0001"},
        "required_conditions": {"minimum_distinctness": "DISTINCT_LINEAGE"},
        "selection_authority_ref": {"kind": "human_authority", "id": "HA-SHUKOU"},
    }
    fields.update(overrides)
    return VerificationRequirement(**fields)


def _selection(**overrides: Any) -> VerifierSelection:
    fields: dict[str, Any] = {
        "selection_id": "VSEL-0001",
        "project_id": PROJECT_ID,
        "requirement_id": "VREQ-0001",
        "status": "ACTIVE",
        "selection_authority_ref": {"kind": "human_authority", "id": "HA-SHUKOU"},
        "verifier_identity": {"kind": "deterministic_test_runner", "id": "VERIFIER-0001"},
        "permitted_boundary": {"scope": "repository", "boundary_id": "VB-0001"},
    }
    fields.update(overrides)
    return VerifierSelection(**fields)


def _counting_verifier(payload: dict[str, Any]) -> tuple[list[int], Any]:
    calls: list[int] = []

    def verifier(*, requirement: VerificationRequirement, selection: VerifierSelection) -> Any:
        calls.append(1)
        return payload

    return calls, verifier


# --- the canonical successful route --------------------------------------------------- #


def test_successful_route_returns_a_verified_result_with_zero_store_mutation(
    _real_route: dict[str, Any],
) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(_real_route["evidence_id"], _real_route["difference_id"])
    selection = _selection()
    calls, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-INDEPENDENT-0001"}],
            "observations": {"summary": "independently reproduced the reported outcome"},
        }
    )

    result = run_independent_verification(
        store,
        project_id=project_id,
        verification_requirement=requirement,
        verifier_selection=selection,
        verifier=verifier,
    )

    assert isinstance(result, VerificationResult)
    assert result.status == "VERIFIED"
    assert result.requirement_id == "VREQ-0001"
    assert result.selection_id == "VSEL-0001"
    assert result.project_id == project_id
    assert dict(result.target_refs[0]) == {
        "kind": "observation_evidence",
        "id": _real_route["evidence_id"],
    }
    assert dict(result.verifier_identity) == {
        "kind": "deterministic_test_runner",
        "id": "VERIFIER-0001",
    }
    assert dict(result.selection_authority_ref) == {"kind": "human_authority", "id": "HA-SHUKOU"}
    assert dict(result.verification_boundary) == {"scope": "repository", "boundary_id": "VB-0001"}
    assert dict(result.input_refs[0]) == {"kind": "source_snapshot", "id": "SS-INDEPENDENT-0001"}
    assert dict(result.observations) == {"summary": "independently reproduced the reported outcome"}
    assert calls == [1]
    assert _snapshot(store.root, project_id) == before


def test_result_fields_are_immutable(_real_route: dict[str, Any]) -> None:
    store = _real_route["store"]
    requirement = _requirement(_real_route["evidence_id"], _real_route["difference_id"])
    selection = _selection()
    _, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-INDEPENDENT-0001"}],
            "observations": {},
        }
    )
    result = run_independent_verification(
        store,
        project_id=_real_route["project_id"],
        verification_requirement=requirement,
        verifier_selection=selection,
        verifier=verifier,
    )
    with pytest.raises(AttributeError):
        result.status = "FAILED"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.target_refs[0]["kind"] = "tampered"  # type: ignore[index]


def test_requirement_and_selection_fields_are_immutable() -> None:
    requirement = _requirement("EVIDENCE-1", "D-1")
    with pytest.raises(AttributeError):
        requirement.project_id = "OTHER"  # type: ignore[misc]
    with pytest.raises(TypeError):
        requirement.verification_boundary["scope"] = "tampered"  # type: ignore[index]

    selection = _selection()
    with pytest.raises(AttributeError):
        selection.status = "REVOKED"  # type: ignore[misc]
    with pytest.raises(TypeError):
        selection.verifier_identity["kind"] = "tampered"  # type: ignore[index]


# --- required rejection proofs: requirement/selection/boundary/target admission ------- #


def test_wrong_requested_project_id_is_rejected(_real_route: dict[str, Any]) -> None:
    store = _real_route["store"]
    requirement = _requirement(_real_route["evidence_id"], _real_route["difference_id"])
    selection = _selection()
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        run_independent_verification(
            store,
            project_id="OTHER-PROJECT",
            verification_requirement=requirement,
            verifier_selection=selection,
            verifier=verifier,
        )
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
            "selection_authority_ref",
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
    store = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = mutate_requirement(
        _requirement(_real_route["evidence_id"], _real_route["difference_id"])
    )
    selection = mutate_selection(_selection())
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match=expected_message_fragment):
        run_independent_verification(
            store,
            project_id=project_id,
            verification_requirement=requirement,
            verifier_selection=selection,
            verifier=verifier,
        )
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
    store = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], target_refs=target_refs
    )
    selection = _selection()
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        run_independent_verification(
            store,
            project_id=project_id,
            verification_requirement=requirement,
            verifier_selection=selection,
            verifier=verifier,
        )
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_unresolvable_evidence_target_is_rejected_and_never_reaches_the_verifier(
    _real_route: dict[str, Any],
) -> None:
    store = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        "EVIDENCE-DOES-NOT-EXIST",
        _real_route["difference_id"],
        target_refs=[{"kind": "observation_evidence", "id": "EVIDENCE-DOES-NOT-EXIST"}],
    )
    selection = _selection()
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match="does not resolve"):
        run_independent_verification(
            store,
            project_id=project_id,
            verification_requirement=requirement,
            verifier_selection=selection,
            verifier=verifier,
        )
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_a_difference_or_change_target_is_never_resolved_against_the_store(
    _real_route: dict[str, Any],
) -> None:
    """Difference and Change are never Store-owned record kinds in this vertical -- a
    fabricated ``difference``/``change`` id must not be rejected by Store resolution (only
    an ``observation_evidence`` target is ever resolved here)."""

    store = _real_route["store"]
    requirement = _requirement(
        _real_route["evidence_id"],
        _real_route["difference_id"],
        target_refs=[
            {"kind": "difference", "id": "D-DOES-NOT-EXIST"},
            {"kind": "change", "id": "CHG-DOES-NOT-EXIST"},
        ],
    )
    selection = _selection()
    calls, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-1"}],
            "observations": {},
        }
    )

    result = run_independent_verification(
        store,
        project_id=_real_route["project_id"],
        verification_requirement=requirement,
        verifier_selection=selection,
        verifier=verifier,
    )
    assert calls == [1]
    assert result.status == "VERIFIED"


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
    store = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(_real_route["evidence_id"], _real_route["difference_id"])
    selection = _selection()

    def verifier(*, requirement: VerificationRequirement, selection: VerifierSelection) -> Any:
        return payload

    with pytest.raises(VerifierOutputError):
        run_independent_verification(
            store,
            project_id=project_id,
            verification_requirement=requirement,
            verifier_selection=selection,
            verifier=verifier,
        )
    assert _snapshot(store.root, project_id) == before


def test_verifier_citing_no_input_at_all_is_rejected_unless_unavailable(
    _real_route: dict[str, Any],
) -> None:
    store = _real_route["store"]
    requirement = _requirement(_real_route["evidence_id"], _real_route["difference_id"])
    selection = _selection()

    def empty_input_verifier(
        *, requirement: VerificationRequirement, selection: VerifierSelection
    ) -> Any:
        return {"status": "VERIFIED", "input_refs": [], "observations": {}}

    with pytest.raises(VerifierOutputError, match="no input_refs"):
        run_independent_verification(
            store,
            project_id=_real_route["project_id"],
            verification_requirement=requirement,
            verifier_selection=selection,
            verifier=empty_input_verifier,
        )


def test_verifier_citing_only_the_target_refs_is_rejected_as_indistinguishable_provenance(
    _real_route: dict[str, Any],
) -> None:
    store = _real_route["store"]
    requirement = _requirement(_real_route["evidence_id"], _real_route["difference_id"])
    selection = _selection()

    def echo_verifier(*, requirement: VerificationRequirement, selection: VerifierSelection) -> Any:
        return {
            "status": "VERIFIED",
            "input_refs": [dict(ref) for ref in requirement.target_refs],
            "observations": {},
        }

    with pytest.raises(VerifierOutputError, match="implementation-indistinguishable"):
        run_independent_verification(
            store,
            project_id=_real_route["project_id"],
            verification_requirement=requirement,
            verifier_selection=selection,
            verifier=echo_verifier,
        )


@pytest.mark.parametrize("status", ["FAILED", "INSUFFICIENT"])
def test_a_non_unavailable_negative_result_still_requires_distinguishable_input(
    _real_route: dict[str, Any], status: str
) -> None:
    store = _real_route["store"]
    requirement = _requirement(_real_route["evidence_id"], _real_route["difference_id"])
    selection = _selection()

    def echo_verifier(*, requirement: VerificationRequirement, selection: VerifierSelection) -> Any:
        return {"status": status, "input_refs": [], "observations": {}}

    with pytest.raises(VerifierOutputError):
        run_independent_verification(
            store,
            project_id=_real_route["project_id"],
            verification_requirement=requirement,
            verifier_selection=selection,
            verifier=echo_verifier,
        )


def test_unavailable_status_is_exempt_from_the_independence_check(
    _real_route: dict[str, Any],
) -> None:
    """Disclosed interpretation (VERIFICATION_CONTRACT.md §9): UNAVAILABLE asserts the
    verifier could not evaluate at all, so it is not required to cite distinguishable
    input -- unlike VERIFIED/FAILED/INSUFFICIENT, which are all real evaluations."""

    store = _real_route["store"]
    requirement = _requirement(_real_route["evidence_id"], _real_route["difference_id"])
    selection = _selection()

    def unavailable_verifier(
        *, requirement: VerificationRequirement, selection: VerifierSelection
    ) -> Any:
        return {"status": "UNAVAILABLE", "input_refs": [], "observations": {"reason": "offline"}}

    result = run_independent_verification(
        store,
        project_id=_real_route["project_id"],
        verification_requirement=requirement,
        verifier_selection=selection,
        verifier=unavailable_verifier,
    )
    assert result.status == "UNAVAILABLE"
    assert result.input_refs == ()


@pytest.mark.parametrize("status", ["FAILED", "INSUFFICIENT", "UNAVAILABLE"])
def test_every_real_negative_outcome_is_representable_with_distinguishable_input(
    _real_route: dict[str, Any], status: str
) -> None:
    """The failure statuses are ordinary results this route returns unmodified -- it never
    substitutes a status, and a negative outcome with genuine independent input is accepted
    exactly as a VERIFIED one is."""

    store = _real_route["store"]
    requirement = _requirement(_real_route["evidence_id"], _real_route["difference_id"])
    selection = _selection()

    def verifier(*, requirement: VerificationRequirement, selection: VerifierSelection) -> Any:
        return {
            "status": status,
            "input_refs": [{"kind": "source_snapshot", "id": "SS-INDEPENDENT-0002"}],
            "observations": {"reason_code": "OBSERVED_MISMATCH"},
        }

    result = run_independent_verification(
        store,
        project_id=_real_route["project_id"],
        verification_requirement=requirement,
        verifier_selection=selection,
        verifier=verifier,
    )
    assert result.status == status


# --- construction-time input type checks ----------------------------------------------- #


def test_non_instance_requirement_or_selection_is_rejected(_real_route: dict[str, Any]) -> None:
    store = _real_route["store"]
    selection = _selection()
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        run_independent_verification(
            store,
            project_id=_real_route["project_id"],
            verification_requirement={"not": "a requirement instance"},  # type: ignore[arg-type]
            verifier_selection=selection,
            verifier=verifier,
        )
    assert calls == []


def test_non_canonical_project_id_is_rejected(_real_route: dict[str, Any]) -> None:
    store = _real_route["store"]
    requirement = _requirement(_real_route["evidence_id"], _real_route["difference_id"])
    selection = _selection()
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        run_independent_verification(
            store,
            project_id="../escape",
            verification_requirement=requirement,
            verifier_selection=selection,
            verifier=verifier,
        )
    assert calls == []
