"""Phase 8 Vertical Proof -- Reflow canonical-reference provenance matrix (P8-R2-F2,
SHUKOU Phase 8 structural-review round 2).

P8-R1-F5 proved ``reflow()``'s own ``authority_ref``/``change_refs``/``observation_refs``
are re-verified against the real records an Evaluation is already bound to, before commit.
SHUKOU's own finding on that check: ``REFERENCE_ID_ONLY_EQUALITY_SUFFICIENT=false`` -- the
check compared only ``{ref["id"], ...}`` Python sets, which silently accepts a reference
naming the right id under the *wrong* ``kind``, collapses a genuine duplicate reference into
one, and cannot distinguish "missing" from "extra" once only ids are compared.

Each test below mutates exactly one already-real ``reflow()``/``closure_request`` provenance
argument from a real assembled route (never a hand-built substitute) and asserts the route
fails closed, before ``_admitted_records``/commit ever runs -- proven, not merely asserted,
by confirming the Store's own committed State never advanced past genesis afterward.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.fixtures import vertical_proof as fx
from tests.natural_cycle.proof import assemble_vertical_proof_route
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.reflow.errors import ReflowValidationError, StaleReflowError
from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.store import FileStateStore


def _assert_store_never_advanced(assembly: dict[str, object]) -> None:
    """``NO_STATE_MUTATION_ON_FAILURE``/``NO_LINEAGE_MUTATION_ON_FAILURE``/``NO_RECORD_
    MUTATION_ON_FAILURE``/``NO_TRANSACTION_MANIFEST_MUTATION_ON_FAILURE`` (all ``=true``):
    a refused provenance check leaves the Store's committed State exactly at the genesis
    revision this route began from -- proven from a *fresh* Store instance over only the
    persisted backend."""

    store = assembly["store"]
    genesis_state = assembly["genesis_state"]
    fresh = FileStateStore(store.root, schema_root=SCHEMA_ROOT)
    current = fresh.load_current(fx.PROJECT_ID)
    assert current["state_revision"] == genesis_state["state_revision"]
    reconstructed = fresh.reconstruct(fx.PROJECT_ID)
    assert reconstructed == current


def _wrong_id(real_id: str) -> str:
    """A different, still schema-shaped identity: real content-addressed ids here are
    ``<PREFIX>-<64 uppercase hex>``, so replacing the trailing hex digit is guaranteed to
    name a different, never-produced identity without breaking the id's own shape."""

    assert real_id[-1] in "0123456789ABCDEF"
    replacement = "0" if real_id[-1] != "0" else "1"
    return real_id[:-1] + replacement


# --- change_refs / closure_request.producing_change_refs (UNORDERED_SET) ------------------ #


def test_change_refs_right_id_wrong_kind_fails_closed(tmp_path: Path) -> None:
    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    real_id = assembly["change_ref"]["id"]
    kwargs["change_refs"] = [{"kind": "not_a_change", "id": real_id}]
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_change_refs_duplicate_reference_fails_closed(tmp_path: Path) -> None:
    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["change_refs"] = [dict(assembly["change_ref"]), dict(assembly["change_ref"])]
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_change_refs_missing_reference_fails_closed(tmp_path: Path) -> None:
    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["change_refs"] = []
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_change_refs_extra_reference_fails_closed(tmp_path: Path) -> None:
    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    extra = {"kind": "change", "id": _wrong_id(assembly["change_ref"]["id"])}
    kwargs["change_refs"] = [dict(assembly["change_ref"]), extra]
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_change_refs_wrong_reference_id_fails_closed(tmp_path: Path) -> None:
    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["change_refs"] = [{"kind": "change", "id": _wrong_id(assembly["change_ref"]["id"])}]
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


# --- observation_refs / closure_request.reobservation.after_observation_refs (UNORDERED_SET)


def test_observation_refs_right_id_wrong_kind_fails_closed(tmp_path: Path) -> None:
    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    real_id = assembly["verification_observation_id"]
    kwargs["observation_refs"] = [{"kind": "not_an_observation", "id": real_id}]
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_observation_refs_duplicate_reference_fails_closed(tmp_path: Path) -> None:
    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    real_ref = {"kind": "observation", "id": assembly["verification_observation_id"]}
    kwargs["observation_refs"] = [dict(real_ref), dict(real_ref)]
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_observation_refs_missing_reference_fails_closed(tmp_path: Path) -> None:
    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["observation_refs"] = []
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_observation_refs_extra_reference_fails_closed(tmp_path: Path) -> None:
    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    real_ref = {"kind": "observation", "id": assembly["verification_observation_id"]}
    extra = {"kind": "observation", "id": _wrong_id(real_ref["id"])}
    kwargs["observation_refs"] = [dict(real_ref), extra]
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_observation_refs_wrong_reference_id_fails_closed(tmp_path: Path) -> None:
    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["observation_refs"] = [
        {"kind": "observation", "id": _wrong_id(assembly["verification_observation_id"])}
    ]
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


# --- authority_ref (SINGLE_REFERENCE) ------------------------------------------------------ #


def test_authority_ref_right_id_wrong_kind_fails_closed(tmp_path: Path) -> None:
    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    real_id = assembly["authority"]["decision"]["authority_decision_id"]
    kwargs["authority_ref"] = {"kind": "not_an_authority_decision", "id": real_id}
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_authority_ref_wrong_reference_id_fails_closed(tmp_path: Path) -> None:
    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    real_id = assembly["authority"]["decision"]["authority_decision_id"]
    kwargs["authority_ref"] = {"kind": "authority_decision", "id": _wrong_id(real_id)}
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_authority_ref_unknown_field_fails_closed(tmp_path: Path) -> None:
    """``REFERENCE_KIND_IS_SEMANTIC``/no-unknown-field discipline also refuses an
    otherwise-correct reference carrying a field this Kernel's own reference contract does
    not name here."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    real_id = assembly["authority"]["decision"]["authority_decision_id"]
    kwargs["authority_ref"] = {
        "kind": "authority_decision",
        "id": real_id,
        "decision": "AUTONOMOUS",
    }
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


# --- reflow_instant causal-order semantics (P8-R2 Reflow Instant semantic decision) -------- #
#
# ``REFLOW_INSTANT_IS_TRANSITION_TIME=true``, ``REFLOW_INSTANT_EXACTLY_EQUALS_EVALUATED_AT=
# false``, ``REFLOW_INSTANT_MUST_NOT_PRECEDE_CLOSURE_EVALUATION=true``, ``LATER_VALID_
# REFLOW_INSTANT_ALLOWED=true``, ``REFLOW_INSTANT_INCLUDED_IN_TRANSACTION_ID=true``,
# ``DIFFERENT_VALID_REFLOW_INSTANT_MAY_PRODUCE_DIFFERENT_TRANSACTION_ID=true``. "Wrong
# instant" is fixed as ``INVALID_TIMESTAMP OR REFLOW_INSTANT_BEFORE_CLOSURE_EVALUATION``,
# never merely "differs from the fixture's own pinned value" -- P8-R1-F5's own
# ``test_p8r1f4_reflow_instant_fails_the_route_closed`` already proves one case of the
# second disjunct; the tests below prove the remaining required rows.


def test_reflow_instant_invalid_timestamp_is_rejected(tmp_path: Path) -> None:
    """INVALID_REFLOW_INSTANT_REJECTED=true: a value that is not even a real timestamp
    fails closed with this Kernel's own typed error, not a bare, uncaught ``ValueError``
    escaping from timestamp parsing."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["reflow_instant"] = "not-a-timestamp"
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_reflow_instant_before_evaluation_is_rejected(tmp_path: Path) -> None:
    """REFLOW_BEFORE_EVALUATION_REJECTED=true: a well-formed instant that still precedes
    the Closure Evaluation's own ``evaluated_at`` fails closed -- ``CAUSALLY_EARLY_REFLOW_
    INSTANT_FAILS_CLOSED=true``."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["reflow_instant"] = "2020-01-01T00:00:00Z"
    with pytest.raises(StaleReflowError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_reflow_instant_equal_to_evaluation_is_allowed(tmp_path: Path) -> None:
    """REFLOW_EQUAL_TO_EVALUATION_ALLOWED=true: ``REFLOW_INSTANT_EXACTLY_EQUALS_EVALUATED_
    AT=false`` is a claim about identity (the two need not be the same field), not about
    ordering -- an instant exactly equal to ``evaluated_at`` is not "before" it, and is
    admitted through to a real, committed ``CLOSED`` route."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["reflow_instant"] = fx.SUFFICIENCY_EVALUATED_AT
    result = reflow(assembly["store"], **kwargs)
    assert result["decision"]["to_status"] == "CLOSED"


def test_reflow_instant_after_evaluation_is_allowed(tmp_path: Path) -> None:
    """REFLOW_AFTER_EVALUATION_ALLOWED=true: the fixture's own pinned ``REFLOW_INSTANT``
    (already strictly after ``SUFFICIENCY_EVALUATED_AT``) commits a real ``CLOSED`` route --
    the unmodified positive route already proves this; re-asserted here, explicitly, as this
    matrix's own required row."""

    assembly = assemble_vertical_proof_route(tmp_path)
    result = reflow(assembly["store"], **assembly["reflow_kwargs"])
    assert result["decision"]["to_status"] == "CLOSED"


def test_valid_changed_reflow_instant_changes_the_transaction_id(tmp_path: Path) -> None:
    """VALID_CHANGED_REFLOW_INSTANT_CHANGES_TRANSACTION_ID=true:
    ``reflow.identity.transaction_id`` folds ``reflow_instant`` into the transaction's own
    content address, so two otherwise-identical routes committed at two different, both
    causally-valid instants real a genuinely different ``state_transition_ref``/transaction
    identity -- proven here over two real, independent routes, never asserted from reading
    the identity function's own source alone."""

    first = assemble_vertical_proof_route(tmp_path / "first")
    second = assemble_vertical_proof_route(tmp_path / "second")

    first_kwargs = dict(first["reflow_kwargs"])
    second_kwargs = dict(second["reflow_kwargs"])
    second_kwargs["reflow_instant"] = "2026-09-05T10:00:00Z"
    assert second_kwargs["reflow_instant"] != first_kwargs["reflow_instant"]

    first_result = reflow(first["store"], **first_kwargs)
    second_result = reflow(second["store"], **second_kwargs)

    assert first_result["decision"]["to_status"] == "CLOSED"
    assert second_result["decision"]["to_status"] == "CLOSED"
    assert first_result["state_transition_ref"]["id"] != second_result["state_transition_ref"]["id"]
