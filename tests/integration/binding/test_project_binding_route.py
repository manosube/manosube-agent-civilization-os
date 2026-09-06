"""Phase 9 (Issue #43) Product Binding: the one public route (``bind_project``),
end-to-end, over a real ``FileStateStore``.

Proves the canonical successful route (Issue #43 §6, items 1-8), the required negative and
interruption proofs (§7), and that no rejection ever advances canonical Binding, State,
Lineage, record, or transaction-manifest visibility.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Any

import pytest
from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding import (
    BindingIdentityError,
    BindingValidationError,
    bind_project,
)
from manosube_agent_civilization.difference.errors import SecurityRejectionError
from manosube_agent_civilization.store import STAGES, FileStateStore
from manosube_agent_civilization.store.errors import (
    AlreadyInitializedError,
    BoundaryError,
    CorruptStoreError,
    SimulatedCrash,
    StateNotFoundError,
)


def _kwargs() -> dict[str, Any]:
    return bind_project_kwargs()


def _bind(store: FileStateStore, **overrides: Any) -> dict[str, Any]:
    kwargs = _kwargs()
    kwargs.update(overrides)
    return bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )


# --- canonical successful route ------------------------------------------------------------- #


def test_bind_project_atomically_adopts_binding_objective_revision_and_genesis_state(
    tmp_path: Path,
) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    result = _bind(store)

    assert result["committed_state"]["state_revision"] == 0
    assert result["committed_state"]["project_id"] == kwargs["project_id"]

    resolved_binding = store.resolve_record(
        kwargs["project_id"], "project_binding", result["project_binding_id"]
    )
    assert resolved_binding == result["project_binding"]
    resolved_objective = store.resolve_record(
        kwargs["project_id"],
        "objective_revision",
        result["objective_revision"]["objective_revision_id"],
    )
    assert resolved_objective == result["objective_revision"]

    # No fake Observation/Evidence/Difference/Change/Closure/Reflow record is introduced.
    for forbidden_kind in (
        "observation",
        "observation_evidence",
        "difference_event",
        "closure_evaluation",
        "change",
    ):
        assert store.resolve_record(kwargs["project_id"], forbidden_kind, "anything") is None


def test_fresh_file_state_store_reconstructs_the_identical_project_binding(
    tmp_path: Path,
) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    result = _bind(store)

    fresh = FileStateStore(store.root, schema_root=SCHEMA_ROOT)
    assert fresh.reconstruct(kwargs["project_id"]) == fresh.load_current(kwargs["project_id"])
    assert (
        fresh.resolve_record(kwargs["project_id"], "project_binding", result["project_binding_id"])
        == result["project_binding"]
    )


def test_a_fresh_python_process_reconstructs_the_identical_project_binding(
    tmp_path: Path,
) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    result = _bind(store)
    store_root = str(store.root)
    project_id = kwargs["project_id"]
    binding_id = result["project_binding_id"]

    script = textwrap.dedent(
        f"""
        import json, pathlib, sys
        sys.path.insert(0, {str(Path.cwd())!r})
        from manosube_agent_civilization.store import FileStateStore
        from tests.state_helpers import SCHEMA_ROOT
        store = FileStateStore(pathlib.Path({store_root!r}), schema_root=SCHEMA_ROOT)
        current = store.load_current({project_id!r})
        binding = store.resolve_record({project_id!r}, "project_binding", {binding_id!r})
        print(json.dumps({{
            "state_revision": current["state_revision"],
            "binding_present": binding is not None,
            "binding_id": binding["project_binding_id"] if binding else None,
        }}))
        """
    )
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(Path.cwd()),
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["state_revision"] == 0
    assert payload["binding_present"] is True
    assert payload["binding_id"] == binding_id


def test_identical_replay_is_accepted_as_a_no_op(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    first = _bind(store)
    second = _bind(store)
    assert second["project_binding_id"] == first["project_binding_id"]
    assert second["committed_state"] == first["committed_state"]


def test_conflicting_replay_is_rejected_before_any_mutation(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    first = _bind(store)
    before = store.load_current(_kwargs()["project_id"])

    conflicting = _kwargs()
    conflicting["command_policy"]["max_commands_per_change"] = 999
    with pytest.raises(AlreadyInitializedError):
        bind_project(
            store,
            **conflicting,
            additional_genesis_records=genesis_records(),
            schema_root=SCHEMA_ROOT,
        )

    after = store.load_current(conflicting["project_id"])
    assert after == before == first["committed_state"]


def test_stale_already_initialized_store_is_rejected_by_a_second_distinct_binding(
    tmp_path: Path,
) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    _bind(store)
    other = _kwargs()
    other["boundary"]["include_patterns"] = ["*.md"]
    with pytest.raises(AlreadyInitializedError):
        bind_project(
            store, **other, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )


# --- P9-R1-F4: full-manifest replay comparison ------------------------------------------------- #


def test_identical_full_manifest_replay_with_different_member_order_is_still_a_no_op(
    tmp_path: Path,
) -> None:
    """The comparison walks the full ``TX-GENESIS`` manifest as a set, never a positional
    list -- supplying ``additional_genesis_records`` in a different order than the first call
    must still resolve as the identical no-op."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    first = _bind(store)
    second = bind_project(
        store,
        **_kwargs(),
        additional_genesis_records=list(reversed(genesis_records())),
        schema_root=SCHEMA_ROOT,
    )
    assert second["committed_state"] == first["committed_state"]
    assert second["authority_rule"] == first["authority_rule"]


def test_replay_with_a_different_additional_genesis_record_body_is_rejected(
    tmp_path: Path,
) -> None:
    """P9-R1-F4 scenario: an ``additional_genesis_records``-only change (Objective Revision,
    Authority Rule and Project Binding all byte-identical) is still a conflicting replay --
    the prior 3-record-only comparison would have missed this."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    _bind(store)
    before = store.load_current(_kwargs()["project_id"])

    real_records = genesis_records()
    kind, record_id, body = real_records[0]
    tampered_records = [(kind, record_id, {**body, "captured_at": "2099-01-01T00:00:00Z"})]
    with pytest.raises(AlreadyInitializedError):
        bind_project(
            store, **_kwargs(), additional_genesis_records=tampered_records, schema_root=SCHEMA_ROOT
        )
    assert store.load_current(_kwargs()["project_id"]) == before


def test_replay_missing_a_previously_adopted_additional_genesis_record_is_rejected(
    tmp_path: Path,
) -> None:
    """P9-R1-F4 scenario: a replay that simply drops a member the first call adopted is a
    conflicting replay, not a smaller no-op."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    _bind(store)
    before = store.load_current(_kwargs()["project_id"])

    # Dropping the fixture's only additional_genesis_records member also breaks genesis
    # State's own declared source_snapshot_refs closure (Phase 9 Round 2 P9-R2-F2) -- an
    # even earlier admission gate than the replay comparison this test was originally
    # written to prove, and a legitimate rejection of the same bad input either way.
    with pytest.raises((AlreadyInitializedError, BindingIdentityError)):
        bind_project(store, **_kwargs(), additional_genesis_records=[], schema_root=SCHEMA_ROOT)
    assert store.load_current(_kwargs()["project_id"]) == before


def test_replay_with_an_extra_additional_genesis_record_is_rejected(tmp_path: Path) -> None:
    """P9-R1-F4 scenario: a replay that adds a member the first call never adopted is a
    conflicting replay, not a superset no-op."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    _bind(store)
    before = store.load_current(_kwargs()["project_id"])

    extra_records = [
        *genesis_records(),
        ("source_snapshot", "SNAP-EXTRA-0001", {"extra": "record"}),
    ]
    with pytest.raises(AlreadyInitializedError):
        bind_project(
            store, **_kwargs(), additional_genesis_records=extra_records, schema_root=SCHEMA_ROOT
        )
    assert store.load_current(_kwargs()["project_id"]) == before


def test_replay_with_a_right_id_wrong_kind_additional_record_is_rejected(tmp_path: Path) -> None:
    """P9-R1-F4 scenario: a replay member sharing a real, previously-adopted record's own id
    but declaring a different ``kind`` is both a missing member (the real kind/id pair is now
    absent) and an extra one (a new kind/id pair appears) -- rejected either way."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    _bind(store)
    before = store.load_current(_kwargs()["project_id"])

    kind, record_id, body = genesis_records()[0]
    wrong_kind_records = [("not_" + kind, record_id, body)]
    # Relabeling the fixture's only additional_genesis_records member also breaks genesis
    # State's own declared source_snapshot_refs closure (Phase 9 Round 2 P9-R2-F2) -- an
    # even earlier admission gate than the replay comparison this test was originally
    # written to prove, and a legitimate rejection of the same bad input either way.
    with pytest.raises((AlreadyInitializedError, BindingIdentityError)):
        bind_project(
            store,
            **_kwargs(),
            additional_genesis_records=wrong_kind_records,
            schema_root=SCHEMA_ROOT,
        )
    assert store.load_current(_kwargs()["project_id"]) == before


def test_replay_with_an_authority_rule_only_body_change_is_rejected(tmp_path: Path) -> None:
    """P9-R1-F4 scenario: Objective Revision, Project Binding, and every
    ``additional_genesis_records`` member all byte-identical to the first call -- only the
    Authority Rule's own body differs. The prior 3-record comparison already covered
    ``authority_rule`` incidentally only once it became a named record; this proves it
    explicitly."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    _bind(store)
    before = store.load_current(_kwargs()["project_id"])

    from manosube_agent_civilization.authority.identity import rule_id as _rule_id

    kwargs = _kwargs()
    kwargs["authority_rule"]["scope"]["subjects"] = ["a-different-subject"]
    kwargs["authority_rule"]["authority_rule_id"] = _rule_id(
        {k: v for k, v in kwargs["authority_rule"].items() if k != "authority_rule_id"}
    )
    kwargs["authority_policy_ref"]["id"] = kwargs["authority_rule"]["authority_rule_id"]
    with pytest.raises(AlreadyInitializedError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    assert store.load_current(_kwargs()["project_id"]) == before


def test_replay_with_an_objective_revision_only_body_change_is_rejected(tmp_path: Path) -> None:
    """P9-R1-F4 scenario: only the Objective Revision's own body differs from the first
    call -- everything else byte-identical."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    _bind(store)
    before = store.load_current(_kwargs()["project_id"])

    kwargs = _kwargs()
    kwargs["objective_revision"]["statement"] = "a materially different statement"
    with pytest.raises(AlreadyInitializedError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    assert store.load_current(_kwargs()["project_id"]) == before


# --- project_id substitution negative controls ---------------------------------------------- #


@pytest.mark.parametrize(
    "bad_project_id",
    [
        "/home/user/project",
        "https://github.com/example/repo",
        "123456789",
        "my-lowercase-project",
        "../escape",
    ],
)
def test_project_id_locator_shaped_substitution_is_rejected(
    bad_project_id: str, tmp_path: Path
) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["project_id"] = bad_project_id
    kwargs["genesis_state"]["project_id"] = bad_project_id
    # The fixture's own objective_revision/authority_rule bodies still declare the real
    # PROJECT_ID, so Phase 9 Round 1's own new cross-binding checks (P9-R1-F1/F2) now trip
    # -- correctly, an even earlier fail-closed gate -- before ever reaching the schema-shape
    # rejection this test was originally written to prove; either is a legitimate rejection
    # of this same bad, locator-shaped project_id, so both are accepted here.
    with pytest.raises((BindingValidationError, BindingIdentityError)):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    # Nothing was ever initialized under this identity -- confirmed via the Store's own
    # generic reads, whichever fail-closed guard trips first: its own project_id boundary
    # check (a "/" or ".." locator is refused before any project directory is even touched)
    # for a path-shaped id, or CorruptStoreError ("lineage has no genesis") for one merely
    # unrecognized.
    with pytest.raises((BoundaryError, CorruptStoreError)):
        store.load_current(bad_project_id)


# --- Binding/genesis-State cross-consistency negative controls ------------------------------ #


def test_project_id_mismatch_between_binding_and_genesis_state_is_rejected(
    tmp_path: Path,
) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["genesis_state"]["project_id"] = "PRJ-DIFFERENT-0001"
    with pytest.raises(BindingIdentityError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_objective_revision_id_mismatch_between_binding_and_genesis_state_is_rejected(
    tmp_path: Path,
) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["genesis_state"]["objective_revision_id"] = "OBJ-REV-DIFFERENT-0001"
    with pytest.raises(BindingIdentityError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )


def test_missing_objective_revision_id_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    del kwargs["objective_revision"]["objective_revision_id"]
    with pytest.raises(BindingValidationError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )


def test_objective_revision_missing_a_required_field_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    del kwargs["objective_revision"]["statement"]
    with pytest.raises(BindingValidationError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )


def test_genesis_state_at_a_nonzero_revision_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["genesis_state"]["state_revision"] = 1
    with pytest.raises(BindingValidationError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )


# --- Authority policy reference negative controls -------------------------------------------- #


def test_missing_authority_policy_reference_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    del kwargs["authority_policy_ref"]
    with pytest.raises(TypeError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )


def test_wrong_kind_authority_policy_reference_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["authority_policy_ref"] = {"kind": "authority_decision", "id": "AUTH-DEC-" + "1" * 64}
    with pytest.raises(BindingValidationError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )


def test_ambiguous_authority_policy_reference_missing_its_kind_is_rejected(
    tmp_path: Path,
) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["authority_policy_ref"] = {"id": kwargs["authority_policy_ref"]["id"]}
    with pytest.raises(BindingValidationError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )


# --- P9-R1-F1: real Authority Rule body negative controls ------------------------------------ #


def test_authority_rule_missing_a_required_field_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    del kwargs["authority_rule"]["decision"]
    with pytest.raises(BindingValidationError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_authority_policy_ref_not_reproducing_from_the_declared_authority_rule_is_rejected(
    tmp_path: Path,
) -> None:
    """A caller-declared ``authority_policy_ref`` that does not equal the real recomputed
    ``rule_id`` of the accompanying ``authority_rule`` body is refused -- a merely well-formed
    but unbacked reference is not enough (Issue #43 P9-R1-F1)."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["authority_policy_ref"] = {"kind": "authority_rule", "id": "AUTH-RULE-" + "9" * 64}
    with pytest.raises(BindingIdentityError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_authority_rule_own_id_not_reproducing_from_its_own_body_is_rejected(
    tmp_path: Path,
) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["authority_rule"]["authority_rule_id"] = "AUTH-RULE-" + "8" * 64
    with pytest.raises(BindingIdentityError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_authority_rule_project_id_mismatch_is_rejected(tmp_path: Path) -> None:
    from manosube_agent_civilization.authority.identity import rule_id as _rule_id

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["authority_rule"]["project_id"] = "PRJ-DIFFERENT-0002"
    kwargs["authority_rule"]["authority_rule_id"] = _rule_id(
        {k: v for k, v in kwargs["authority_rule"].items() if k != "authority_rule_id"}
    )
    kwargs["authority_policy_ref"]["id"] = kwargs["authority_rule"]["authority_rule_id"]
    with pytest.raises(BindingIdentityError, match="authority_rule"):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_authority_rule_declared_by_mismatch_with_human_authority_ref_is_rejected(
    tmp_path: Path,
) -> None:
    """Issue #43 P9-R1-F1/F2's three-way Human Authority cross-match: the Authority Rule's
    own ``declared_by`` must canonically equal the Binding's own ``human_authority_ref``."""

    from manosube_agent_civilization.authority.identity import rule_id as _rule_id

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["authority_rule"]["declared_by"] = {"kind": "human_authority", "id": "AUTH-OTHER-0001"}
    kwargs["authority_rule"]["authority_rule_id"] = _rule_id(
        {k: v for k, v in kwargs["authority_rule"].items() if k != "authority_rule_id"}
    )
    kwargs["authority_policy_ref"]["id"] = kwargs["authority_rule"]["authority_rule_id"]
    with pytest.raises(BindingIdentityError, match="declared_by"):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_objective_revision_human_authority_ref_mismatch_is_rejected(tmp_path: Path) -> None:
    """Issue #43 P9-R1-F2's three-way Human Authority cross-match, second leg: the Objective
    Revision's own ``human_authority_ref`` must canonically equal the Binding's own
    ``human_authority_ref`` too."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["objective_revision"]["human_authority_ref"] = {
        "kind": "human_authority",
        "id": "AUTH-OTHER-0002",
    }
    with pytest.raises(BindingIdentityError, match="human_authority_ref"):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_authority_rule_resolves_from_a_fresh_store_and_a_fresh_process(tmp_path: Path) -> None:
    """Issue #43 P9-R1-F1: ``authority_policy_ref`` must resolve to a real canonical body from
    a fresh Store instance and a fresh process alike -- not merely within the process that
    minted it."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    result = _bind(store)

    fresh = FileStateStore(store.root, schema_root=SCHEMA_ROOT)
    resolved = fresh.resolve_record(
        kwargs["project_id"], "authority_rule", kwargs["authority_policy_ref"]["id"]
    )
    assert resolved == result["authority_rule"]

    store_root = str(store.root)
    project_id = kwargs["project_id"]
    rule_id_value = kwargs["authority_policy_ref"]["id"]
    script = textwrap.dedent(
        f"""
        import json, pathlib, sys
        sys.path.insert(0, {str(Path.cwd())!r})
        from manosube_agent_civilization.store import FileStateStore
        from tests.state_helpers import SCHEMA_ROOT
        store = FileStateStore(pathlib.Path({store_root!r}), schema_root=SCHEMA_ROOT)
        rule = store.resolve_record({project_id!r}, "authority_rule", {rule_id_value!r})
        print(json.dumps({{"authority_rule_present": rule is not None}}))
        """
    )
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(Path.cwd()),
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["authority_rule_present"] is True


# --- a rejected declaration never touches the Store ------------------------------------------ #


def test_a_boundary_escape_never_initializes_the_store(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["boundary"]["root_paths"] = ["../escape"]
    kwargs["source_registrations"][0]["locator"] = "../escape/src"
    with pytest.raises(BindingValidationError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


# --- persisted-record tamper detection -------------------------------------------------------- #


def test_a_tampered_persisted_project_binding_is_detected_on_resolution(
    tmp_path: Path,
) -> None:
    """The same generic manifest-claimant mechanism every other domain's persisted records
    already rely on (``FileStateStore._record_committed_by_any_transaction``) -- a direct
    on-disk edit after commit diverges from the transaction's own still-present staged copy,
    detected the moment anything asks the Store to resolve it, with no domain-specific
    content-address logic required in this module."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    result = _bind(store)
    binding_id = result["project_binding_id"]

    record_path = (
        store.root
        / "projects"
        / kwargs["project_id"]
        / "records"
        / "project_binding"
        / f"{binding_id}.json"
    )
    assert record_path.is_file()
    body = json.loads(record_path.read_text(encoding="utf-8"))
    body["command_policy"]["max_commands_per_change"] = 999999
    record_path.write_text(json.dumps(body), encoding="utf-8")

    fresh = FileStateStore(store.root, schema_root=SCHEMA_ROOT)
    with pytest.raises(CorruptStoreError):
        fresh.resolve_record(kwargs["project_id"], "project_binding", binding_id)


# --- crash-injection: joint visibility or joint absence -------------------------------------- #


@pytest.mark.parametrize("stage", STAGES)
def test_crash_at_every_initialize_stage_never_exposes_partial_binding_visibility(
    stage: str, tmp_path: Path
) -> None:
    def fault(current: str, _stage: str = stage) -> None:
        if current == _stage:
            raise SimulatedCrash(_stage)

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()

    with pytest.raises(SimulatedCrash):
        bind_project(
            store,
            **kwargs,
            additional_genesis_records=genesis_records(),
            schema_root=SCHEMA_ROOT,
            fault=fault,
        )

    # Precompute the identity the crashed attempt would have minted, to check joint absence.
    from manosube_agent_civilization.binding.engine import assemble_project_binding

    would_be_binding = assemble_project_binding(
        project_id=kwargs["project_id"],
        objective_revision_ref={
            "kind": "objective_revision",
            "id": kwargs["objective_revision"]["objective_revision_id"],
        },
        boundary=kwargs["boundary"],
        authority_policy_ref=kwargs["authority_policy_ref"],
        source_registrations=kwargs["source_registrations"],
        command_policy=kwargs["command_policy"],
        secret_exclusion_policy=kwargs["secret_exclusion_policy"],
        human_authority_ref=kwargs["human_authority_ref"],
        bound_at=kwargs["bound_at"],
        schema_root=SCHEMA_ROOT,
    )
    binding_id = would_be_binding["project_binding_id"]

    project_id = kwargs["project_id"]
    authority_rule_id = kwargs["authority_policy_ref"]["id"]
    assert store.resolve_record(project_id, "project_binding", binding_id) is None
    assert store.resolve_record(project_id, "authority_rule", authority_rule_id) is None
    assert store.resolve_transaction(project_id, "TX-GENESIS") is None
    with pytest.raises(CorruptStoreError, match="lineage has no genesis"):
        store.reconstruct(project_id)
    with pytest.raises(CorruptStoreError, match="lineage has no genesis"):
        store.load_current(project_id)

    early_stage = stage in STAGES[: STAGES.index("AFTER_COMMIT_INTENT")]
    if early_stage:
        # Abandoned, not completed: retrying the identical bind_project from scratch succeeds.
        with pytest.raises(StateNotFoundError):
            store.recover(project_id)
        result = _bind(store)
        assert result["project_binding_id"] == binding_id
    else:
        store.recover(project_id)
        resolved = store.resolve_record(project_id, "project_binding", binding_id)
        assert resolved is not None
        assert resolved["project_binding_id"] == binding_id
        resolved_rule = store.resolve_record(project_id, "authority_rule", authority_rule_id)
        assert resolved_rule is not None
        assert resolved_rule["authority_rule_id"] == authority_rule_id
        transaction = store.resolve_transaction(project_id, "TX-GENESIS")
        assert transaction is not None
        current = store.load_current(project_id)
        assert current["state_revision"] == 0
        assert store.reconstruct(project_id) == current


# --- P9-R1-F5: typed reference classification / closure ---------------------------------------- #


def test_every_store_owned_binding_reference_resolves_from_a_fresh_store_and_process(
    tmp_path: Path,
) -> None:
    """Recursively walk the accepted Binding graph's Store-owned references
    (``objective_revision_ref``, ``authority_policy_ref``) via :func:`~manosube_agent_
    civilization.binding.resolve_binding_references`, proving zero unresolved from both a
    fresh Store instance and a fresh process (Issue #43 P9-R1-F5)."""

    from manosube_agent_civilization.binding import resolve_binding_references

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    result = _bind(store)

    fresh = FileStateStore(store.root, schema_root=SCHEMA_ROOT)
    resolved = resolve_binding_references(fresh, result["project_binding"])
    unresolved = [field for field, body in resolved.items() if body is None]
    assert unresolved == []
    assert resolved["objective_revision_ref"] == result["objective_revision"]
    assert resolved["authority_policy_ref"] == result["authority_rule"]

    store_root = str(store.root)
    binding_json = json.dumps(result["project_binding"])
    script = textwrap.dedent(
        f"""
        import json, pathlib, sys
        sys.path.insert(0, {str(Path.cwd())!r})
        from manosube_agent_civilization.binding import resolve_binding_references
        from manosube_agent_civilization.store import FileStateStore
        from tests.state_helpers import SCHEMA_ROOT
        store = FileStateStore(pathlib.Path({store_root!r}), schema_root=SCHEMA_ROOT)
        project_binding = json.loads({binding_json!r})
        resolved = resolve_binding_references(store, project_binding)
        print(json.dumps({{
            "unresolved_count": sum(1 for body in resolved.values() if body is None),
        }}))
        """
    )
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(Path.cwd()),
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["unresolved_count"] == 0


def test_resolve_binding_references_rejects_a_wrong_kind_reference_before_store_lookup(
    tmp_path: Path,
) -> None:
    from manosube_agent_civilization.binding import (
        BindingValidationError as _BVE,
        resolve_binding_references,
    )

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    result = _bind(store)
    tampered = deepcopy(result["project_binding"])
    tampered["authority_policy_ref"] = {"kind": "objective_revision", "id": "OBJ-REV-FAKE-0001"}
    with pytest.raises(_BVE, match="CROSS_KIND_SUBSTITUTION_ALLOWED"):
        resolve_binding_references(store, tampered)


# --- P9-R2-F1: secret scan across the WHOLE accepted/persisted graph -------------------------- #


def _fake_secret() -> str:
    return "ghp_" + "C" * 36


def test_secret_shaped_value_in_authority_rule_is_rejected(tmp_path: Path) -> None:
    from manosube_agent_civilization.authority.identity import rule_id as _rule_id

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["authority_rule"]["scope"]["subjects"] = [_fake_secret()]
    # Recompute the Authority Rule's own content-addressed id so identity reverification
    # (P9-R1-F1) does not preempt the secret scan this test means to prove.
    kwargs["authority_rule"]["authority_rule_id"] = _rule_id(
        {k: v for k, v in kwargs["authority_rule"].items() if k != "authority_rule_id"}
    )
    kwargs["authority_policy_ref"]["id"] = kwargs["authority_rule"]["authority_rule_id"]
    with pytest.raises(SecurityRejectionError, match="secret-bearing value"):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_secret_shaped_value_in_genesis_state_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["genesis_state"]["state_metadata"]["producer"] = _fake_secret()
    with pytest.raises(SecurityRejectionError, match="secret-bearing value"):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_secret_shaped_value_in_an_additional_genesis_record_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    tampered_records = deepcopy(genesis_records())
    kind, record_id, body = tampered_records[0]
    body = {**body, "source_locator": _fake_secret()}
    tampered_records[0] = (kind, record_id, body)
    with pytest.raises(SecurityRejectionError, match="secret-bearing value"):
        bind_project(
            store, **kwargs, additional_genesis_records=tampered_records, schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_secret_scan_error_never_echoes_the_secret_value_itself(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    secret = _fake_secret()
    kwargs["objective_revision"]["semantic_change_summary"] = secret
    with pytest.raises(SecurityRejectionError) as excinfo:
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    assert secret not in str(excinfo.value)


# --- P9-R2-F2: genesis State's own Store-owned reference closure ------------------------------ #


def test_genesis_state_dangling_source_snapshot_ref_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["genesis_state"]["state_metadata"]["source_snapshot_refs"] = [
        {"kind": "source_snapshot", "id": "SNAP-DOES-NOT-EXIST-0001"}
    ]
    with pytest.raises(BindingIdentityError, match="GENESIS_DANGLING_CANONICAL_REFERENCE"):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_genesis_state_wrong_kind_source_snapshot_ref_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    real_snapshot_id = kwargs["genesis_state"]["state_metadata"]["source_snapshot_refs"][0]["id"]
    kwargs["genesis_state"]["state_metadata"]["source_snapshot_refs"] = [
        {"kind": "observation_evidence", "id": real_snapshot_id}
    ]
    with pytest.raises(BindingValidationError, match="CROSS_KIND_SUBSTITUTION_ALLOWED"):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_genesis_state_dangling_evidence_ref_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["genesis_state"]["evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVID-DOES-NOT-EXIST-0001"}
    ]
    with pytest.raises(BindingIdentityError, match="GENESIS_DANGLING_CANONICAL_REFERENCE"):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_genesis_state_source_snapshot_ref_resolves_via_additional_genesis_records(
    tmp_path: Path,
) -> None:
    """Positive control: the real fixture's own genesis State resolves its declared
    ``source_snapshot_refs`` against the candidate ``additional_genesis_records`` member --
    proving the closure check does not merely reject everything."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    result = _bind(store)
    assert result["committed_state"]["state_revision"] == 0


# --- P9-R2-F3: full accepted-graph reference classification ----------------------------------- #


def test_objective_revision_wrong_kind_owner_authority_ref_is_rejected(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["objective_revision"]["owner_authority_ref"] = {
        "kind": "authority_rule",
        "id": kwargs["authority_policy_ref"]["id"],
    }
    with pytest.raises(BindingValidationError, match="CROSS_KIND_SUBSTITUTION_ALLOWED"):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_authority_rule_wrong_kind_declared_by_is_rejected(tmp_path: Path) -> None:
    """Authority's own existing schema (``authority.schema.json#/$defs/human_authority_ref``)
    already forecloses a wrong-kind ``declared_by`` with a ``const`` -- this reference field
    is still classified in ``reference_classification.py`` (P9-R2-F3) for the table's own
    completeness, but the real rejection observed here is schema validation, not the
    classification layer, and that is the correct division of labor (schema owns shape,
    this module owns cross-record closure)."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["authority_rule"]["declared_by"] = {
        "kind": "objective_revision",
        "id": kwargs["objective_revision"]["objective_revision_id"],
    }
    with pytest.raises(BindingValidationError, match="declared_by"):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_reference_edges_rejects_an_unclassified_source_kind() -> None:
    from manosube_agent_civilization.binding.reference_classification import reference_edges

    with pytest.raises(BindingValidationError, match="UNKNOWN_SOURCE_RECORD_KIND"):
        reference_edges("not_a_classified_kind", {})


def test_reference_edges_classifies_every_field_on_every_accepted_record_kind() -> None:
    """A real, positive-control walk over each accepted record kind's own real fixture body
    -- every declared reference field resolves without a classification error, proving no
    accepted record kind carries an unclassified reference field in practice."""

    from manosube_agent_civilization.binding.reference_classification import reference_edges

    kwargs = _kwargs()
    # Objective Revision, Authority Rule and genesis State are exercised directly here;
    # Project Binding's own three fields were already proven in Round 1's own identity
    # tests. None of these calls should raise -- every reference field on each real fixture
    # body is classified.
    reference_edges("objective_revision", kwargs["objective_revision"])
    reference_edges("authority_rule", kwargs["authority_rule"])
    reference_edges("project_state", kwargs["genesis_state"])


# --- P9-R2-F4: duplicate-aware full-manifest replay -------------------------------------------- #


def test_replay_with_an_identical_duplicate_additional_record_is_a_no_op(tmp_path: Path) -> None:
    """An identical duplicate ``(kind, id, body)`` supplied twice in one replay's own
    ``additional_genesis_records`` is silently fine -- the same member named twice changes
    nothing (P9-R2-F4's own "duplicate-aware, not merely order-independent" requirement)."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    first = _bind(store)
    real_records = genesis_records()
    doubled_records = [*real_records, *real_records]
    second = bind_project(
        store, **_kwargs(), additional_genesis_records=doubled_records, schema_root=SCHEMA_ROOT
    )
    assert second["committed_state"] == first["committed_state"]


def test_replay_with_a_conflicting_duplicate_additional_record_is_rejected(tmp_path: Path) -> None:
    """Two different bodies claimed under the same ``(kind, id)`` in one replay's own
    ``additional_genesis_records`` is a conflict, never silently resolved to the last one
    supplied."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    _bind(store)
    before = store.load_current(_kwargs()["project_id"])

    real_records = genesis_records()
    kind, record_id, body = real_records[0]
    conflicting = [(kind, record_id, body), (kind, record_id, {**body, "captured_at": "X"})]
    with pytest.raises(BindingValidationError, match="conflicting"):
        bind_project(
            store, **_kwargs(), additional_genesis_records=conflicting, schema_root=SCHEMA_ROOT
        )
    assert store.load_current(_kwargs()["project_id"]) == before


# --- P9-R2-F5: single shared admission -- zero Store mutation on any rejection ----------------- #


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda k: k["objective_revision"].__setitem__("statement", ""),
            id="objective_revision_invalid_schema",
        ),
        pytest.param(
            lambda k: k["authority_rule"].__setitem__("decision", "NOT_A_REAL_DECISION"),
            id="authority_rule_invalid_schema",
        ),
        pytest.param(
            lambda k: k["genesis_state"]["state_metadata"].__setitem__("producer", _fake_secret()),
            id="genesis_state_secret",
        ),
        pytest.param(
            lambda k: k["boundary"].__setitem__("root_paths", ["../escape"]),
            id="project_binding_boundary_escape",
        ),
    ],
)
def test_every_rejected_body_type_leaves_zero_store_mutation(mutate, tmp_path: Path) -> None:
    """P9-R2-F5: whichever accepted body type is malformed, the shared admission rejects it
    before ``store.initialize`` -- proven here by exact-count assertions, not merely "an
    exception was raised"."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    mutate(kwargs)
    with pytest.raises(Exception):  # noqa: B017 -- deliberately kind-agnostic across mutations
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError, match="lineage has no genesis"):
        store.load_current(kwargs["project_id"])
    assert store.resolve_transaction(kwargs["project_id"], "TX-GENESIS") is None
    # A project that never reached `store.initialize` at all is indistinguishable, by the
    # Store's own documented bare-genesis convention, from one whose bare genesis legitimately
    # adopted zero records -- both report an empty manifest here, never a real record.
    assert store.resolve_transaction_manifest(kwargs["project_id"], "TX-GENESIS") == []
    assert store.resolve_record(kwargs["project_id"], "project_binding", "anything") is None


# --- Development Binding / Phase 8 fixture substitution --------------------------------------- #


def test_development_binding_policy_shape_is_refused_as_a_project_binding(
    tmp_path: Path,
) -> None:
    """Development Binding's own policy artifact must never pass as a Product Binding
    component -- it carries an entirely different, unrecognized shape."""

    from manosube_agent_civilization.binding.validation import validate_record

    development_binding_shaped = {
        "doc_type": "REPOSITORY_BINDING",
        "kernel_element": None,
        "roles": {},
    }
    with pytest.raises(BindingValidationError):
        validate_record(
            development_binding_shaped, "project_binding.schema.json", schema_root=SCHEMA_ROOT
        )


def _kwargs_for_project(alt_project_id: str) -> dict[str, Any]:
    """A fully self-consistent ``bind_project`` kwargs set for an alternate *alt_project_id*
    -- every embedded ``project_id`` cross-check (P9-R1-F1/F2) re-satisfied, the Authority
    Rule's own content-addressed identity recomputed to match."""

    from manosube_agent_civilization.authority.identity import rule_id as _rule_id

    kwargs = _kwargs()
    kwargs["project_id"] = alt_project_id
    kwargs["genesis_state"]["project_id"] = alt_project_id
    kwargs["objective_revision"]["project_id"] = alt_project_id
    rule = kwargs["authority_rule"]
    rule["project_id"] = alt_project_id
    rule["authority_rule_id"] = _rule_id(
        {k: v for k, v in rule.items() if k != "authority_rule_id"}
    )
    kwargs["authority_policy_ref"]["id"] = rule["authority_rule_id"]
    return kwargs


def test_phase_8_project_id_reuse_is_legitimate_not_substitution(tmp_path: Path) -> None:
    """Reusing Phase 8's own bare ``PROJECT_ID`` string as a genuinely new Product Binding's
    own declared identity is legitimate identity reuse -- schema-shaped identity strings are
    not scarce, and this is not the "Phase 8 fixture substitution" Issue #43 forbids
    (Phase 9 Round 1 P9-R1-F6: ``PHASE_8_PROJECT_ID_REUSE_FORBIDDEN=false``). What the
    Finding actually forbids is substituting a real, categorically different Phase 8 record
    *body* for a Product Binding component -- proven, case by case, in the tests below."""

    from tests.fixtures import vertical_proof as phase_8_fixtures

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs_for_project(phase_8_fixtures.PROJECT_ID)
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    assert result["committed_state"]["project_id"] == phase_8_fixtures.PROJECT_ID


def _real_phase_8_observation_and_difference() -> tuple[dict[str, Any], dict[str, Any]]:
    """A real Observation body and a real Difference body, both minted through their own
    real production owners over Phase 8's own real fixture inputs (``tests/fixtures/
    vertical_proof.py``) -- no Store required, since neither :func:`~manosube_agent_
    civilization.observation.observe`/:func:`~manosube_agent_civilization.difference.
    derive_differences` nor the fixture's own ``genesis_project_state`` touch one."""

    from tests.fixtures import vertical_proof as phase_8_fixtures
    from tests.natural_cycle.proof import genesis_project_state

    from manosube_agent_civilization.difference import derive_differences
    from manosube_agent_civilization.observation import observe

    current_state = genesis_project_state()
    observation_request = phase_8_fixtures.before_observation_request(
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    bundle = observe(observation_request)
    real_observation = bundle["observations"][-1]

    difference_request = phase_8_fixtures.derivation_request(
        observation_bundle=bundle,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    real_difference = derive_differences(difference_request)["differences"][0]
    return real_observation, real_difference


def test_a_real_phase_8_observation_body_is_refused_as_an_objective_revision(
    tmp_path: Path,
) -> None:
    """P9-R1-F6 case (a): a real, schema-valid Phase 8 Observation body -- minted through the
    real Observation owner, never hand-authored -- carries none of Objective Revision's own
    required fields and must be refused before any Store write."""

    real_observation, _ = _real_phase_8_observation_and_difference()
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["objective_revision"] = real_observation
    with pytest.raises(BindingValidationError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_a_real_phase_8_difference_body_is_refused_as_an_authority_rule(tmp_path: Path) -> None:
    """P9-R1-F6 case (b): a real, schema-valid Phase 8 Difference body -- minted through the
    real Difference owner -- carries none of Authority Rule's own required fields and must be
    refused before any Store write."""

    _, real_difference = _real_phase_8_observation_and_difference()
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["authority_rule"] = real_difference
    with pytest.raises(BindingValidationError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_phase_8_fixture_observation_scope_is_refused_as_a_product_boundary(
    tmp_path: Path,
) -> None:
    """P9-R1-F6 case (c): Phase 8's own real, schema-valid Observation Scope (embedded in its
    own fixture Observation Request) carries none of Product Boundary's own required fields
    (``root_paths``, ``include_patterns``, ``exclude_patterns``) and must be refused before
    any Store write."""

    from tests.fixtures import vertical_proof as phase_8_fixtures
    from tests.natural_cycle.proof import genesis_project_state

    current_state = genesis_project_state()
    phase_8_scope = phase_8_fixtures.before_observation_request(
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )["scope"]

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["boundary"] = phase_8_scope
    with pytest.raises(BindingValidationError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_a_real_phase_8_source_snapshot_body_is_refused_as_a_source_registration(
    tmp_path: Path,
) -> None:
    """P9-R1-F6 case (d): Phase 8's own real, content-addressed Source Snapshot record
    (``tests/fixtures/vertical_proof.py::BEFORE_SOURCE_SNAPSHOT``, built through the real
    ``observation.source_snapshot.build_source_snapshot`` owner) carries none of Source
    Registration's own required fields and must be refused before any Store write."""

    from tests.fixtures import vertical_proof as phase_8_fixtures

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["source_registrations"] = [phase_8_fixtures.BEFORE_SOURCE_SNAPSHOT]
    with pytest.raises(BindingValidationError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])


def test_a_phase_8_derived_wrong_kind_reference_is_refused_as_the_authority_policy_ref(
    tmp_path: Path,
) -> None:
    """P9-R1-F6 case (e): a real, Phase-8-fixture-derived id (its own real, content-addressed
    Source Snapshot id) named with its own real, honestly-declared ``source_snapshot`` kind
    is still refused as an ``authority_policy_ref`` -- Product Binding's own typed reference
    classification (P9-R1-F5) accepts only ``authority_rule`` there, and never resolves the
    kind a caller merely declares as authoritative (``CROSS_KIND_SUBSTITUTION_ALLOWED=false``)."""

    from tests.fixtures import vertical_proof as phase_8_fixtures

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["authority_policy_ref"] = {
        "kind": "source_snapshot",
        "id": phase_8_fixtures.BEFORE_SOURCE_SNAPSHOT["source_snapshot_id"],
    }
    with pytest.raises(BindingValidationError):
        bind_project(
            store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
        )
    with pytest.raises(CorruptStoreError):
        store.load_current(kwargs["project_id"])
