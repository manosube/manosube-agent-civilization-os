"""Phase 11 (Issue #47) CLI Boot adapter: the one public command (``boot``), end-to-end,
over a real ``FileStateStore``.

Proves the canonical successful route (``CLI_CONTRACT.md`` §5) and the required rejection
proofs (§6), and that no rejection ever mutates canonical Binding, State, Lineage, record, or
transaction-manifest visibility.

Every test here invokes ``cli.main.run`` in-process (the identical function the console
script itself calls, capturing the same ``sys.stdout.buffer``/``sys.stderr.buffer`` writes via
pytest's ``capsysbinary``), so the full matrix stays fast without weakening any proof -- every
assertion is about ``run``'s own return value and byte-exact stdout/stderr, not about process
mechanics a subprocess would add nothing to check. The primary positive-route and determinism
proofs against the real, installed ``manosube`` console-script executable (frozen semantic
decision 9, Structural Review Round 1) live in
``tests/integration/cli/test_cli_installed_command.py``, which is the only place a wheel is
built and a fresh virtual environment is created -- doing that once there, not per-test here,
keeps this file's own rejection matrix fast.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any

import pytest
from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.cli.main import run
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import STAGES, FileStateStore
from manosube_agent_civilization.store.errors import SimulatedCrash

# ``importlib.import_module`` (never ``import package.main as alias``): cli/__init__.py's own
# ``from .main import main, run`` rebinds the package attribute ``cli.main`` to the *function*
# ``main``, so a plain ``import ... as cli_main`` would silently hand this module the function
# instead of the module (see tests/contract/cli/test_cli_static_conformance.py for the same
# gotcha).
cli_main = importlib.import_module("manosube_agent_civilization.cli.main")


def _bound(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    store_root = tmp_path / "backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store_root, kwargs, result


def _snapshot(store_root: Path, project_id: str) -> dict[str, str]:
    project_dir = store_root / "projects" / project_id
    if not project_dir.is_dir():
        return {}
    return {
        str(path.relative_to(project_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(project_dir.rglob("*"))
        if path.is_file()
    }


def _argv(
    store_root: Path, schema_root: Path, project_id: str, project_binding_id: str
) -> list[str]:
    return [
        "boot",
        "--store-root",
        str(store_root),
        "--schema-root",
        str(schema_root),
        "--project-id",
        project_id,
        "--project-binding-id",
        project_binding_id,
    ]


def _advance(
    store: FileStateStore, project_id: str, genesis_state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a real second State transition -- shared by every later-transaction rejection
    test below, mirroring the identical shape ``tests/integration/boot/
    test_boot_project_route.py::_advance`` already builds for Boot's own equivalent tests."""

    successor = deepcopy(genesis_state)
    successor["state_revision"] = genesis_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = genesis_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": "TX-ADVANCE-0001"}
    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": "TX-ADVANCE-0001",
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


# --- canonical successful route, in-process (missing/present current view) --------------- #


def test_cli_boots_successfully_when_the_materialized_current_view_is_missing(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    current_path = store_root / "projects" / project_id / "state" / "current.json"
    current_path.unlink()

    exit_code = run(_argv(store_root, SCHEMA_ROOT, project_id, result["project_binding_id"]))
    out, err = capsysbinary.readouterr()

    assert exit_code == 0
    assert err == b""
    assert json.loads(out)["current_state"] == result["committed_state"]
    assert not current_path.is_file()


def test_cli_success_writes_nothing_anywhere_in_the_store(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    before = _snapshot(store_root, project_id)

    exit_code = run(_argv(store_root, SCHEMA_ROOT, project_id, result["project_binding_id"]))
    capsysbinary.readouterr()

    assert exit_code == 0
    assert _snapshot(store_root, project_id) == before


# --- required rejection proofs (§6) ------------------------------------------------------- #


def test_cli_rejects_missing_required_arguments(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    exit_code = run(["boot", "--store-root", str(tmp_path)])
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    document = json.loads(err)
    assert document["error"] == "CLIArgumentError"
    assert b"Traceback" not in err


def test_cli_rejects_an_unknown_subcommand(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    exit_code = run(["not-a-real-command"])
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    assert json.loads(err)["error"] == "CLIArgumentError"


def test_cli_rejects_a_non_directory_store_root(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    plain_file = tmp_path / "not-a-directory"
    plain_file.write_text("x", encoding="utf-8")

    exit_code = run(_argv(plain_file, SCHEMA_ROOT, "PRJ-X", "PROJBIND-X"))
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    assert json.loads(err)["error"] == "CLIInvalidRootError"


def test_cli_rejects_a_missing_store_root(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    exit_code = run(_argv(tmp_path / "does-not-exist", SCHEMA_ROOT, "PRJ-X", "PROJBIND-X"))
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    assert json.loads(err)["error"] == "CLIInvalidRootError"


def test_cli_rejects_a_non_directory_schema_root(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    plain_file = tmp_path / "schema-not-a-directory"
    plain_file.write_text("x", encoding="utf-8")

    exit_code = run(_argv(tmp_path, plain_file, "PRJ-X", "PROJBIND-X"))
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    assert json.loads(err)["error"] == "CLIInvalidRootError"


def test_cli_rejects_an_unusable_schema_root_with_no_traceback(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    """An existing but empty ``--schema-root`` passes this adapter's own directory check, so
    the failure surfaces later, deep inside schema loading, as an entirely unclassified
    exception -- proving this adapter's own top-level safety net still turns it into a single
    typed, traceback-free stderr document rather than letting a raw traceback leak."""

    store_root, kwargs, result = _bound(tmp_path)
    empty_schema_root = tmp_path / "empty-schema-root"
    empty_schema_root.mkdir()

    exit_code = run(
        _argv(store_root, empty_schema_root, kwargs["project_id"], result["project_binding_id"])
    )
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    document = json.loads(err)
    assert "error" in document and "message" in document
    assert b"Traceback" not in err


def test_cli_rejects_a_project_id_locator_shaped_substitution(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    store_root, _kwargs, result = _bound(tmp_path)

    exit_code = run(_argv(store_root, SCHEMA_ROOT, "../etc/passwd", result["project_binding_id"]))
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    assert json.loads(err)["error"] == "BootNotFoundError"


def test_cli_rejects_a_missing_project_or_binding(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    store_root, kwargs, _result = _bound(tmp_path)
    before = _snapshot(store_root, kwargs["project_id"])

    exit_code = run(_argv(store_root, SCHEMA_ROOT, kwargs["project_id"], "PROJBIND-DOES-NOT-EXIST"))
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    assert json.loads(err)["error"] == "BootNotFoundError"
    assert _snapshot(store_root, kwargs["project_id"]) == before


def _record_path(store_root: Path, project_id: str, kind: str, record_id: str) -> Path:
    return store_root / "projects" / project_id / "records" / kind / f"{record_id}.json"


def test_cli_rejects_a_tampered_persisted_project_binding(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    """A persisted-record tamper is caught by the Store's own generic manifest-claimant
    detection (``resolve_record``) before Boot's own identity reverification ever runs --
    the identical, already-established behavior ``tests/integration/boot/
    test_boot_project_route.py::test_a_tampered_persisted_project_binding_is_detected_on_
    resolution`` proves directly against ``boot_project`` itself, proven here only through
    the CLI's own additional boundary."""

    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    pbid = result["project_binding_id"]
    record_path = _record_path(store_root, project_id, "project_binding", pbid)
    body = json.loads(record_path.read_text(encoding="utf-8"))
    body["command_policy"]["max_commands_per_change"] = 999
    record_path.write_text(json.dumps(body), encoding="utf-8")

    exit_code = run(_argv(store_root, SCHEMA_ROOT, project_id, pbid))
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    assert json.loads(err)["error"] == "CorruptStoreError"


def test_cli_rejects_a_malformed_present_current_view(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    current_path = store_root / "projects" / project_id / "state" / "current.json"
    current_path.write_text("not-json", encoding="utf-8")
    before = _snapshot(store_root, project_id)

    exit_code = run(_argv(store_root, SCHEMA_ROOT, project_id, result["project_binding_id"]))
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    assert json.loads(err)["error"] == "CorruptStoreError"
    assert _snapshot(store_root, project_id) == before


@pytest.mark.parametrize("stage", [STAGES[0], STAGES[4], STAGES[-1]])
def test_cli_rejects_a_representative_interrupted_later_transaction(
    stage: str, tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    genesis_state = result["committed_state"]
    successor, event = _advance(store, project_id, genesis_state)

    def fault(current: str, _stage: str = stage) -> None:
        if current == _stage:
            raise SimulatedCrash(_stage)

    with pytest.raises(SimulatedCrash):
        store.commit(
            project_id,
            genesis_state["state_revision"],
            genesis_state["semantic_fingerprint"],
            successor,
            event,
            fault=fault,
        )
    before = _snapshot(store_root, project_id)

    exit_code = run(_argv(store_root, SCHEMA_ROOT, project_id, result["project_binding_id"]))
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    assert json.loads(err)["error"] == "CorruptStoreError"
    assert _snapshot(store_root, project_id) == before


def test_cli_rejects_a_later_transactions_journal_replaced_by_a_non_directory_entry(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    """P10-R4-F1's own scenario, proven through the CLI boundary: a real, committed later
    transition whose own recovery journal directory is destroyed and replaced by a plain
    regular file at the identical path, while the prior, matching ``current.json`` is left
    untouched."""

    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    genesis_state = result["committed_state"]
    successor, event = _advance(store, project_id, genesis_state)
    store.commit(
        project_id,
        genesis_state["state_revision"],
        genesis_state["semantic_fingerprint"],
        successor,
        event,
    )
    current_path = store_root / "projects" / project_id / "state" / "current.json"
    current_path.write_text(json.dumps(genesis_state), encoding="utf-8")
    journal = store_root / "projects" / project_id / "state" / "recovery" / "TX-ADVANCE-0001"
    shutil.rmtree(journal)
    journal.write_text("not-a-journal-directory", encoding="utf-8")
    before = _snapshot(store_root, project_id)

    exit_code = run(_argv(store_root, SCHEMA_ROOT, project_id, result["project_binding_id"]))
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    assert json.loads(err)["error"] == "CorruptStoreError"
    assert _snapshot(store_root, project_id) == before


# --- Structural Review Round 1 (P11-R1-F2/F3/F4) ------------------------------------------ #


@pytest.mark.parametrize(
    "abbreviated_flag",
    ["--store", "--schema", "--project-i", "--project-b"],
)
def test_cli_rejects_an_abbreviated_long_flag(
    abbreviated_flag: str, tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    """``allow_abbrev=False`` on the ``boot`` subparser: none of the four required flags may
    be spelled as an unambiguous abbreviation (P11-R1-F2)."""

    exit_code = run(["boot", abbreviated_flag, str(tmp_path), "--project-id", "PRJ-X"])
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    assert json.loads(err)["error"] == "CLIArgumentError"
    assert b"Traceback" not in err


@pytest.mark.parametrize("argv", [["--help"], ["-h"], ["boot", "--help"], ["boot", "-h"]])
def test_cli_rejects_a_help_flag_through_the_json_run_contract(
    argv: list[str], capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    """``add_help=False`` on both parsers: argparse's own automatic help action is never
    registered, so a help flag is simply an unrecognized argument -- rejected with the
    identical typed-JSON, non-zero-exit, no-traceback contract as any other malformed command
    line, never argparse's own plain-text help dump plus ``SystemExit(0)`` (P11-R1-F3)."""

    exit_code = run(argv)
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    document = json.loads(err)
    assert document["error"] == "CLIArgumentError"
    assert b"Traceback" not in err
    assert b"show this help message" not in err


def test_cli_keeps_success_emission_inside_the_failure_boundary(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Projection, canonical serialization, and the stdout write itself all run inside the
    same top-level ``try`` as ``boot_project`` -- so a failure while producing the success
    document (e.g. a downstream pipe closing mid-write) still surfaces through the identical
    typed-JSON stderr/non-zero-exit contract, never a leaked traceback, and the successful
    Boot it followed still made zero Store mutation (P11-R1-F4)."""

    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    before = _snapshot(store_root, project_id)

    real_emit = cli_main._emit

    def faulty_emit(stream: Any, payload: bytes) -> None:
        if stream is sys.stdout:
            raise BrokenPipeError("simulated broken output pipe")
        real_emit(stream, payload)

    monkeypatch.setattr(cli_main, "_emit", faulty_emit)

    exit_code = run(_argv(store_root, SCHEMA_ROOT, project_id, result["project_binding_id"]))
    out, err = capsysbinary.readouterr()

    assert exit_code != 0
    assert out == b""
    document = json.loads(err)
    assert document["error"] == "BrokenPipeError"
    assert b"Traceback" not in err
    assert _snapshot(store_root, project_id) == before
