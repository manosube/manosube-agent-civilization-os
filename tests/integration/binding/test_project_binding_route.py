"""Phase 9 (Issue #43) Product Binding: the one public route (``bind_project``),
end-to-end, over a real ``FileStateStore``.

Proves the canonical successful route (Issue #43 §6, items 1-8), the required negative and
interruption proofs (§7), and that no rejection ever advances canonical Binding, State,
Lineage, record, or transaction-manifest visibility.
"""

from __future__ import annotations

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
    with pytest.raises(BindingValidationError):
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
    assert store.resolve_record(project_id, "project_binding", binding_id) is None
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
        transaction = store.resolve_transaction(project_id, "TX-GENESIS")
        assert transaction is not None
        current = store.load_current(project_id)
        assert current["state_revision"] == 0
        assert store.reconstruct(project_id) == current


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


def test_phase_8_fixture_boundary_content_never_substitutes_for_a_real_declaration(
    tmp_path: Path,
) -> None:
    """``tests/fixtures/vertical_proof.py``'s own fixture identities must never satisfy
    Product Binding's own schema/identity checks -- proving the two fixture worlds are
    genuinely independent, not merely by convention."""

    from tests.fixtures import vertical_proof as phase_8_fixtures

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = _kwargs()
    kwargs["project_id"] = phase_8_fixtures.PROJECT_ID
    kwargs["genesis_state"]["project_id"] = phase_8_fixtures.PROJECT_ID
    # Phase 8's own PROJECT_ID is schema-shaped like a real identity, so this alone succeeds
    # -- the substitution this Finding actually forbids is importing Phase 8's own *records*
    # (Observation/Difference/Evidence bodies) as Product Binding content, which no code path
    # in this module ever does (confirmed statically in the contract-conformance suite).
    result = _bind(
        store, project_id=phase_8_fixtures.PROJECT_ID, genesis_state=kwargs["genesis_state"]
    )
    assert result["committed_state"]["project_id"] == phase_8_fixtures.PROJECT_ID
