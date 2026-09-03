"""The Evidence producer's output, back through the canonical Difference consumer.

```text
Evidence
→ Sufficiency Result
→ evidence_sufficiency_results
→ derive_differences()
→ schema, identity, reference closure, relational gates
```

Until this existed, Phase 6 was a producer whose output nothing had ever consumed. The tests
that stood in for this proved two much weaker things -- that ``_CARRIED_SECTIONS`` names the
section, and that the result carries an ``evidence_sufficiency_id`` -- and neither would have
noticed that the reference kind Evidence minted was one the Difference graph does not admit.

That is exactly what happened: ``{"kind": "evidence"}`` is neither an admitted kind for
``evidence_sufficiency_result.evidence_refs`` nor an external kind, so a real result put back
into ``derive_differences`` failed the whole-bundle reference-closure gate. A producer that
cannot round-trip is not finished, however well it validates alone.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from tests.evidence_helpers import (
    difference_round_trip_request,
    observation_evidence_request,
    sufficiency_request,
)

from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.difference.graph import EXTERNAL_KINDS, REFERENCE_EDGES
from manosube_agent_civilization.evidence import (
    EVIDENCE_REFERENCE_KIND,
    derive_evidence,
    evaluate_sufficiency,
)


@pytest.fixture(scope="module")
def produced() -> dict[str, Any]:
    result: dict[str, Any] = evaluate_sufficiency(sufficiency_request())[
        "evidence_sufficiency_result"
    ]
    return result


def _admitted(record_type: str, path: str) -> frozenset[str]:
    return next(edge.kinds for edge in REFERENCE_EDGES[record_type] if edge.path == path)


# --------------------------------------------------------------------------- #
# one vocabulary, and it is the consumer's
# --------------------------------------------------------------------------- #


def test_the_minted_kind_is_the_kind_the_difference_graph_admits() -> None:
    """Not a rename to make a test pass: it is the vocabulary the consumer already declares.

    Every slot an Evidence record can occupy in the Difference graph admits
    ``observation_evidence`` -- including ``change_result_evidence_refs``, so the Difference
    layer already refers to *both* 第27条 positions by this one kind.
    """

    assert EVIDENCE_REFERENCE_KIND == "observation_evidence"
    for record_type, path in (
        ("evidence_sufficiency_result", "evidence_refs.members[]"),
        ("difference", "observation_evidence_refs[]"),
        ("closure_evaluation", "change_result_evidence_refs[]"),
        ("closure_evaluation", "terminal_reason_evidence_refs[]"),
        ("closure_evaluation", "change_free_verification_evidence_refs[]"),
        ("invariant_evaluation", "evidence_refs.members[]"),
    ):
        assert EVIDENCE_REFERENCE_KIND in _admitted(record_type, path), (record_type, path)


def test_the_kind_is_external_so_the_record_may_live_outside_the_bundle() -> None:
    """An Evidence record lives in ``01_SCHEMA/evidence/``, not in a Difference bundle.

    ``EXTERNAL_KINDS`` is what lets a reference to it close without the record being present.
    Without that, binding Evidence into the Difference graph would have required carrying
    Evidence records inside Difference bundles -- a second owner for the same records.
    """

    assert EVIDENCE_REFERENCE_KIND in EXTERNAL_KINDS


def test_the_producer_emits_that_kind_and_nothing_else(produced: dict[str, Any]) -> None:
    members = produced["evidence_refs"]["members"]
    assert members
    assert {member["kind"] for member in members} == {EVIDENCE_REFERENCE_KIND}


def test_the_reference_resolves_to_the_evidence_record_it_names(
    produced: dict[str, Any],
) -> None:
    """Auditability, which a rename alone would not have preserved.

    The tag changed; the identity space did not. Each reference still names a content address
    that the Evidence engine reproduces from the same request.
    """

    minted = derive_evidence(observation_evidence_request())
    assert [member["id"] for member in produced["evidence_refs"]["members"]] == [
        minted["evidence_id"]
    ]
    assert minted["evidence_id"].startswith("EVIDENCE-")


# --------------------------------------------------------------------------- #
# the round trip itself
# --------------------------------------------------------------------------- #


def test_a_produced_sufficiency_result_passes_the_whole_bundle_gates(
    produced: dict[str, Any],
) -> None:
    bundle = derive_differences(difference_round_trip_request(produced))
    carried = bundle["evidence_sufficiency_results"]
    assert len(carried) == 1
    assert carried[0] == produced


def test_the_round_trip_carries_a_non_empty_result(produced: dict[str, Any]) -> None:
    """A result with no Evidence references would pass the closure gate vacuously.

    The finding was invisible to every earlier test precisely because none of them put a
    reference through the gate.
    """

    assert produced["evidence_refs"]["members"]
    assert produced["result"] == "SUFFICIENT"
    bundle = derive_differences(difference_round_trip_request(produced))
    assert bundle["evidence_sufficiency_results"][0]["evidence_refs"]["members"]


# --------------------------------------------------------------------------- #
# the negative controls
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "kind", ["evidence", "observation", "evidence_record", "change_result_evidence"]
)
def test_a_wrong_reference_kind_fails_the_closure_gate(kind: str, produced: dict[str, Any]) -> None:
    """The control. Without it, the positive test above could pass for any tag at all.

    ``evidence`` is the tag the reviewed head minted, and it is first here on purpose: this
    is the finding, reproduced as a permanent regression rather than described.
    """

    forged = deepcopy(produced)
    for member in forged["evidence_refs"]["members"]:
        member["kind"] = kind
    with pytest.raises(DifferenceError) as raised:
        derive_differences(difference_round_trip_request(forged))
    assert "reference" in str(raised.value)


def test_negative_evidence_is_the_observation_layer_s_kind_and_not_minted_here(
    produced: dict[str, Any],
) -> None:
    """``negative_evidence`` is admitted beside ``observation_evidence`` in those slots, and
    Phase 6 still does not mint it.

    It backs a Negative Observation, which the Observation layer owns and Phase 6 does not
    produce. Minting it here would be Evidence asserting a bounded absence it never observed
    -- and the tag would pass the closure gate while doing so, which is why this is stated
    rather than left to the graph.
    """

    assert "negative_evidence" in _admitted(
        "evidence_sufficiency_result", "evidence_refs.members[]"
    )
    assert EVIDENCE_REFERENCE_KIND != "negative_evidence"
    assert {member["kind"] for member in produced["evidence_refs"]["members"]} == {
        EVIDENCE_REFERENCE_KIND
    }
