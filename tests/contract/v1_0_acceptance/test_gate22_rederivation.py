"""Contract: real, full Gate 22 mechanical rederivation against this repository's own
already-accepted evidence (Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

This is the one place all eleven pytest-owned predicates are actually re-run as real
subprocesses, and the Deferred Differences register is actually read -- proving the whole
v1.0 acceptance bundle assembles end-to-end against the live repository, not a fixture.
"""

from __future__ import annotations

from pathlib import Path

from manosube_agent_civilization.v1_0_acceptance.engine import build_v1_0_acceptance_bundle
from manosube_agent_civilization.v1_0_acceptance.types import GATE_22_PREDICATES

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_full_bundle_assembles_against_the_live_repository() -> None:
    bundle = build_v1_0_acceptance_bundle(
        REPO_ROOT,
        authorized_base_main_sha="b2a5d287113d3a98e77a2212f8b89359d8e09c5d",
        delivery_head="HEAD",
        release_version_label="v1.0-candidate",
    )

    assert set(bundle["gate_22_predicate_matrix"]) == set(GATE_22_PREDICATES)

    # Every predicate whose own owning evidence already exists in this repository must
    # mechanically rederive to a real, non-UNKNOWN, non-vacuous verdict -- the missing-owner
    # UNKNOWN escape hatch exists for a repository that has not yet built the owning
    # capability, never for this one.
    for predicate, row in bundle["gate_22_predicate_matrix"].items():
        assert row["verification_result"] in ("PASS", "FAIL", "UNKNOWN"), predicate

    # Eleven of the twelve predicates are owned by already-accepted, currently-passing
    # test suites -- they must mechanically rederive PASS, never FAIL or UNKNOWN, proving
    # this repository's own accepted evidence still holds at this head.
    for predicate in set(GATE_22_PREDICATES) - {"ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED"}:
        row = bundle["gate_22_predicate_matrix"][predicate]
        assert row["verification_result"] == "PASS", (predicate, row)

    # ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED is honestly UNKNOWN at this pre-merge PR #94
    # head: SHUKOU adopted an explicit disposition for four of the five previously-open
    # records (`ADOPT_P92_V1_0_DIFFERENCE_DISPOSITION_R1_AND_FINAL_GATE22_SYNC`, Issue #92
    # comment `5755827293`), but PR #94 Structural Review Round 1 (`P94-R1-F1`, adopted
    # `ADOPT_P94_R1_F1`, comment `5760099935`) found FD-0002 had been closed prematurely --
    # its own adopted closure condition requires the README correction to exist on
    # *accepted* `main` plus post-merge after-state re-observation, neither of which has
    # happened while this PR remains open. FD-0002 was reverted to conditionally blocking,
    # so this predicate must still read UNKNOWN, never a silent PASS derived from evidence
    # the record's own text says is still pending (see blocking_differences.py). All seven
    # active records (DD-0001, DD-0002, DC-0001, FD-0001, FD-0002, FD-0003, FD-0005) are
    # still present -- records are never deleted.
    predicate_12 = bundle["gate_22_predicate_matrix"]["ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED"]
    assert predicate_12["verification_result"] == "UNKNOWN"
    assert predicate_12["disposition_count"] == 7

    assert bundle["gate_22_all_pass"] is False
    assert bundle["release_identity"]["tag_created"] is False
    assert bundle["release_identity"]["release_published"] is False
    assert len(bundle["acceptance_bundle_id"]) == 64
